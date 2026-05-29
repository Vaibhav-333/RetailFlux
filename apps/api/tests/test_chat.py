"""Chat endpoint tests — LLM client mocked, analytics services mocked."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

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


def _mock_sales_kpis():
    from app.schemas.analytics import SalesKpisOut
    return SalesKpisOut(
        total_revenue=50000.0, order_count=120, aov=416.67, total_units=150, top_sku="BLZ-BLK-M",
        top_skus=[], revenue_by_region=[], daily_revenue=[],
    )


async def test_chat_selects_tool_and_answers():
    """LLM selects a tool, service returns data, LLM generates an answer."""
    import app.domains.chat.chat_service as cs_mod
    mock_fn = AsyncMock(return_value=_mock_sales_kpis())
    with (
        patch("app.domains.chat.chat_service.generate_text",
              new=AsyncMock(side_effect=[
                  ('{"tool": "get_sales_kpis"}', "gemini"),
                  ("Revenue is strong at $50k with 120 orders.", "gemini"),
              ])),
        patch.dict(cs_mod.TOOL_REGISTRY, {
            "get_sales_kpis": {**cs_mod.TOOL_REGISTRY["get_sales_kpis"], "fn": mock_fn}
        }),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat/message", json={"message": "How are sales doing?"})

    assert r.status_code == 200
    data = r.json()
    assert data["tool_used"] == "get_sales_kpis"
    assert data["provider"] == "gemini"
    assert "50k" in data["answer"] or "50000" in data["answer"] or "Revenue" in data["answer"]
    assert data["data"]["total_revenue"] == 50000.0


async def test_chat_direct_answer_when_no_tool():
    """When LLM returns no tool, the direct response is passed through."""
    with patch("app.domains.chat.chat_service.generate_text",
               new=AsyncMock(return_value=('{"tool": null, "direct_answer": "I can help with sales, marketing, operations, finance, and procurement data."}', "groq"))):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat/message", json={"message": "What can you do?"})

    assert r.status_code == 200
    data = r.json()
    assert data["tool_used"] is None
    assert "sales" in data["answer"].lower()


async def test_chat_role_scoped_access():
    """Sales-role user can only access sales-related tools."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _fake_user(UserRole.SALES)

    with (
        patch("app.domains.chat.chat_service.generate_text",
              new=AsyncMock(return_value=('{"tool": "get_finance_kpis"}', "gemini"))),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat/message", json={"message": "Show me finance data"})

    assert r.status_code == 200
    data = r.json()
    assert data["tool_used"] is None
    assert "access" in data["answer"].lower() or "don't" in data["answer"].lower()


async def test_chat_handles_malformed_llm_response():
    """Malformed LLM JSON is handled gracefully as a direct answer."""
    with patch("app.domains.chat.chat_service.generate_text",
               new=AsyncMock(return_value=("This is not JSON at all", "fallback"))):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat/message", json={"message": "Hello"})

    assert r.status_code == 200
    data = r.json()
    assert data["tool_used"] is None
    assert data["provider"] == "fallback"
    assert len(data["answer"]) > 0


async def test_chat_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/chat/message", json={"message": "Hi"})

    app.dependency_overrides.clear()
    assert r.status_code == 403


async def test_chat_rejects_empty_message():
    """Empty messages are rejected by Pydantic validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/chat/message", json={"message": ""})

    assert r.status_code == 422
