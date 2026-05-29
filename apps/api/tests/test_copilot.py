"""Copilot endpoint tests — LLM mocked, DB mocked for explanation cache."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import Row

from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


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


# ── /copilot/ask ───────────────────────────────────────────────────────────────

async def test_copilot_ask_basic():
    """Ask endpoint calls handle_chat_message and returns answer."""
    from app.schemas.chat import ChatResponse

    mock_result = ChatResponse(
        answer="Gross margin is 44% this month.",
        tool_used="get_finance_kpis",
        data=None,
        provider="gemini",
    )
    with patch(
        "app.api.v1.endpoints.copilot.handle_chat_message",
        new=AsyncMock(return_value=mock_result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/ask",
                json={"message": "What is the gross margin?"},
            )

    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "Gross margin is 44% this month."
    assert data["tool_used"] == "get_finance_kpis"
    assert data["provider"] == "gemini"


async def test_copilot_ask_with_page_context():
    """Page context is prepended to the message before calling chat service."""
    from app.schemas.chat import ChatResponse

    captured_message: list[str] = []

    async def _mock_chat(company_id: str, role: str, message: str):
        captured_message.append(message)
        return ChatResponse(answer="OK", tool_used=None, data=None, provider="gemini")

    with patch("app.api.v1.endpoints.copilot.handle_chat_message", new=_mock_chat):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/ask",
                json={
                    "message": "Why is revenue down?",
                    "page_context": {"page": "Sales", "date_range": "28d"},
                },
            )

    assert r.status_code == 200
    assert len(captured_message) == 1
    assert "Page context" in captured_message[0]
    assert "Sales" in captured_message[0]
    assert "Why is revenue down?" in captured_message[0]


async def test_copilot_ask_requires_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/copilot/ask", json={"message": "hello"})

    app.dependency_overrides.clear()
    assert r.status_code == 403


async def test_copilot_ask_rejects_empty_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/copilot/ask", json={"message": ""})
    assert r.status_code == 422


# ── /copilot/explain ───────────────────────────────────────────────────────────

async def test_explain_returns_cached_result():
    """If the DB has a cached explanation, it is returned without calling the LLM."""
    from app.core.database import get_db
    from app.domains.copilot.explain_service import EXPLAIN_VERSION

    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, i: "Revenue is the total money earned." if i == 0 else None

    mock_result = MagicMock()
    mock_result.fetchone = MagicMock(return_value=mock_row)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.domains.copilot.explain_service.generate_text") as mock_llm:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/explain/metric/total_revenue",
                json={"context": {"value": 1234567}},
            )

    assert r.status_code == 200
    data = r.json()
    assert data["body"] == "Revenue is the total money earned."
    assert data["cached"] is True
    assert data["resource"] == "metric"
    assert data["resource_id"] == "total_revenue"
    mock_llm.assert_not_called()

    app.dependency_overrides.pop(get_db, None)


async def test_explain_generates_and_caches():
    """On a cache miss the LLM is called and the result is stored."""
    from app.core.database import get_db

    # Cache miss → fetchone returns None
    mock_miss = MagicMock()
    mock_miss.fetchone = MagicMock(return_value=None)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_miss)
    mock_db.commit = AsyncMock()

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.domains.copilot.explain_service.generate_text",
        new=AsyncMock(return_value=("Gross margin represents profitability.", "gemini")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/explain/metric/gross_margin",
                json={"context": {"value": 44.5}},
            )

    assert r.status_code == 200
    data = r.json()
    assert data["body"] == "Gross margin represents profitability."
    assert data["cached"] is False

    # Commit was called (cache write attempted)
    mock_db.commit.assert_called_once()

    app.dependency_overrides.pop(get_db, None)


async def test_explain_requires_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/copilot/explain/metric/revenue",
            json={},
        )

    app.dependency_overrides.clear()
    assert r.status_code == 403


async def test_explain_llm_fallback_on_error():
    """If the LLM throws, a graceful fallback body is returned (no 500)."""
    from app.core.database import get_db

    mock_miss = MagicMock()
    mock_miss.fetchone = MagicMock(return_value=None)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_miss)
    mock_db.rollback = AsyncMock()

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.domains.copilot.explain_service.generate_text",
        new=AsyncMock(side_effect=Exception("LLM timeout")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/copilot/explain/anomaly/spike-2024-01-15",
                json={},
            )

    assert r.status_code == 200
    data = r.json()
    assert "Unable to generate" in data["body"] or len(data["body"]) > 0

    app.dependency_overrides.pop(get_db, None)
