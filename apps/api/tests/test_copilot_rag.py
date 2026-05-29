"""Session 34 — Executive AI Copilot tests.

Covers:
  - Embedding store / retrieval (mocked pgvector)
  - Tool routing golden cases
  - SSE streaming endpoint
  - Daily token cap enforcement
  - Conversation memory (create, list, messages, delete)
  - Usage stats endpoint
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()
FAKE_CONV_ID = str(uuid.uuid4())


def _fake_user(role: UserRole = UserRole.CEO) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.email = "ceo@acme.com"
    u.name = "CEO"
    u.role = role
    u.company_id = FAKE_CID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


# ── Embedding helpers ─────────────────────────────────────────────────────────

async def test_embed_text_returns_zero_vec_without_key():
    """Without GEMINI_API_KEY, embed_text returns a zero vector."""
    from app.core.embeddings import _zero_vec, embed_text
    from app.core.config import settings

    orig_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    try:
        vec = await embed_text("hello world")
        assert vec == _zero_vec()
        assert len(vec) == settings.COPILOT_EMBED_DIM
    finally:
        settings.GEMINI_API_KEY = orig_key


async def test_vec_to_pg_format():
    """_vec_to_pg produces pgvector bracket notation."""
    from app.core.embeddings import _vec_to_pg

    vec = [0.1, -0.2, 0.333]
    result = _vec_to_pg(vec)
    assert result.startswith("[")
    assert result.endswith("]")
    assert "0.10000000" in result
    assert "-0.20000000" in result


async def test_search_similar_returns_empty_on_zero_vec():
    """search_similar returns [] when query embedding is all zeros (no API key)."""
    from app.core.embeddings import search_similar
    from app.core.config import settings
    from app.core.database import get_db

    mock_db = AsyncMock()
    settings_orig = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    try:
        result = await search_similar(
            mock_db,
            query_text="test query",
            company_id=str(FAKE_CID),
        )
        assert result == []
        mock_db.execute.assert_not_called()
    finally:
        settings.GEMINI_API_KEY = settings_orig


async def test_store_embedding_upserts_and_commits():
    """store_embedding calls db.execute and db.commit on success."""
    from app.core.embeddings import store_embedding

    mock_db = AsyncMock()

    with patch("app.core.embeddings.embed_text", new=AsyncMock(return_value=[0.1] * 768)):
        await store_embedding(
            mock_db,
            company_id=str(FAKE_CID),
            entity_type="task",
            entity_id="task-001",
            content="Investigate sales drop in Q1",
        )

    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


# ── Tool router ────────────────────────────────────────────────────────────────

async def test_tool_router_ceo_gets_all_tools():
    """CEO role has access to all tools in the registry."""
    from app.domains.copilot.tool_router import get_tools_for_role, TOOL_REGISTRY

    tools = get_tools_for_role("ceo")
    assert set(tools.keys()) == set(TOOL_REGISTRY.keys())


async def test_tool_router_sales_restricted():
    """Sales role can only access sales-relevant tools."""
    from app.domains.copilot.tool_router import get_tools_for_role

    tools = get_tools_for_role("sales")
    assert "get_sales_kpis" in tools
    assert "get_finance_kpis" not in tools
    assert "get_inventory_overview" not in tools


async def test_tool_router_operations_includes_inventory():
    """Operations role has access to inventory tools."""
    from app.domains.copilot.tool_router import get_tools_for_role

    tools = get_tools_for_role("operations")
    assert "get_inventory_overview" in tools
    assert "get_reorder_queue" in tools
    assert "get_abc_xyz_matrix" in tools


async def test_tool_router_finance_has_valuation():
    """Finance role can access inventory valuation tool."""
    from app.domains.copilot.tool_router import get_tools_for_role

    tools = get_tools_for_role("finance")
    assert "get_finance_kpis" in tools
    assert "get_inventory_valuation" in tools
    assert "get_sales_kpis" not in tools


async def test_build_tool_menu_contains_all_descriptions():
    """build_tool_menu returns a string listing all tool names and descriptions."""
    from app.domains.copilot.tool_router import build_tool_menu, get_tools_for_role

    tools = get_tools_for_role("ceo")
    menu = build_tool_menu(tools)
    assert "get_sales_kpis" in menu
    assert "get_inventory_overview" in menu
    assert "get_task_summary" in menu


# ── SSE streaming endpoint ────────────────────────────────────────────────────

async def test_copilot_stream_returns_event_stream():
    """POST /copilot/stream returns Content-Type text/event-stream."""
    from app.core.database import get_db

    mock_db = AsyncMock()

    async def _mock_stream(*args, **kwargs):
        yield 'data: {"type": "token", "content": "Hello "}\n\n'
        yield 'data: {"type": "token", "content": "world"}\n\n'
        yield 'data: {"type": "done", "message_id": null, "provider": "gemini"}\n\n'

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.copilot.stream_copilot_response",
        return_value=_mock_stream(),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/stream",
                json={"message": "What is revenue?"},
            )

    app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text
    assert '"type": "token"' in body
    assert "Hello" in body


async def test_copilot_stream_requires_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/copilot/stream", json={"message": "test"})

    app.dependency_overrides[get_current_user] = _fake_user
    assert r.status_code == 403


async def test_copilot_stream_rejects_empty_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/copilot/stream", json={"message": ""})
    assert r.status_code == 422


# ── Token cap ─────────────────────────────────────────────────────────────────

async def test_usage_check_blocks_when_over_cap():
    """check_and_record_usage returns (False, message) when cap exceeded."""
    from app.domains.copilot.usage import check_and_record_usage

    mock_db = AsyncMock()
    mock_result = MagicMock()
    # Simulate tokens_used > cap (2_000_000 > 100_000)
    mock_result.fetchone = MagicMock(return_value=(2_000_000,))
    mock_db.execute = AsyncMock(return_value=mock_result)

    allowed, msg = await check_and_record_usage(mock_db, company_id=str(FAKE_CID))

    assert allowed is False
    assert msg is not None
    assert "limit" in msg.lower()


async def test_usage_check_allows_when_under_cap():
    """check_and_record_usage returns (True, None) when under cap."""
    from app.domains.copilot.usage import check_and_record_usage

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone = MagicMock(return_value=(100,))  # 100 tokens << 100_000 cap
    mock_db.execute = AsyncMock(return_value=mock_result)

    allowed, msg = await check_and_record_usage(mock_db, company_id=str(FAKE_CID))

    assert allowed is True
    assert msg is None


async def test_usage_check_graceful_on_db_error():
    """check_and_record_usage allows request if DB call fails (never block user)."""
    from app.domains.copilot.usage import check_and_record_usage

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB down"))
    mock_db.rollback = AsyncMock()

    allowed, msg = await check_and_record_usage(mock_db, company_id=str(FAKE_CID))

    assert allowed is True  # graceful degradation


# ── Conversation management ────────────────────────────────────────────────────

async def test_list_conversations_endpoint():
    """GET /copilot/conversations returns a list."""
    from app.core.database import get_db

    mock_db = AsyncMock()

    with patch(
        "app.api.v1.endpoints.copilot.list_conversations",
        new=AsyncMock(return_value=[
            {
                "id": FAKE_CONV_ID,
                "title": "Q1 Revenue Review",
                "summary": None,
                "message_count": 4,
                "total_tokens": 1500,
                "last_message_at": "2026-05-24T10:00:00Z",
                "created_at": "2026-05-24T09:00:00Z",
            }
        ]),
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/copilot/conversations")
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    data = r.json()
    assert "conversations" in data
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["title"] == "Q1 Revenue Review"


async def test_get_conversation_detail():
    """GET /copilot/conversations/{id} returns messages."""
    from app.core.database import get_db

    mock_db = AsyncMock()

    with patch(
        "app.api.v1.endpoints.copilot.get_conversation_messages",
        new=AsyncMock(return_value=[
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": "What is gross margin?",
                "tool_used": None,
                "rag_sources": [],
                "proposed_actions": [],
                "token_estimate": 10,
                "provider": None,
                "created_at": "2026-05-24T09:01:00Z",
            }
        ]),
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/copilot/conversations/{FAKE_CONV_ID}")
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert data["messages"][0]["role"] == "user"


async def test_delete_conversation_not_found():
    """DELETE /copilot/conversations/{id} returns 404 when not found."""
    from app.core.database import get_db

    mock_db = AsyncMock()

    with patch(
        "app.api.v1.endpoints.copilot.delete_conversation",
        new=AsyncMock(return_value=False),
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v1/copilot/conversations/{FAKE_CONV_ID}")
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 404


async def test_copilot_usage_endpoint():
    """GET /copilot/usage returns usage stats."""
    from app.core.database import get_db

    mock_db = AsyncMock()

    with patch(
        "app.api.v1.endpoints.copilot.get_usage_today",
        new=AsyncMock(return_value={
            "tokens_used": 1500,
            "request_count": 3,
            "cap": 100000,
            "pct_used": 1.5,
        }),
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/copilot/usage")
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    data = r.json()
    assert data["tokens_used"] == 1500
    assert data["cap"] == 100000
    assert data["pct_used"] == 1.5


# ── Retriever ─────────────────────────────────────────────────────────────────

async def test_retrieve_context_returns_empty_on_no_hits():
    """retrieve_context returns ('', []) when no embeddings match."""
    from app.domains.copilot.retriever import retrieve_context

    mock_db = AsyncMock()

    with patch("app.domains.copilot.retriever.search_similar", new=AsyncMock(return_value=[])):
        ctx, sources = await retrieve_context(
            mock_db,
            query="revenue question",
            company_id=str(FAKE_CID),
        )

    assert ctx == ""
    assert sources == []


async def test_retrieve_context_formats_hits():
    """retrieve_context returns formatted context string from hits."""
    from app.domains.copilot.retriever import retrieve_context

    mock_db = AsyncMock()
    hits = [
        {
            "entity_type": "insight",
            "entity_id": "abc123",
            "content": "Gross margin declined 2pp due to supplier price increases.",
            "metadata": {},
            "distance": 0.12,
        }
    ]

    with patch("app.domains.copilot.retriever.search_similar", new=AsyncMock(return_value=hits)):
        ctx, sources = await retrieve_context(
            mock_db,
            query="why did margin drop",
            company_id=str(FAKE_CID),
        )

    assert "INSIGHT" in ctx
    assert "Gross margin" in ctx
    assert len(sources) == 1
