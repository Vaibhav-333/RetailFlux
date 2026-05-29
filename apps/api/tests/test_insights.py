"""Insights endpoint tests — Gemini client and summary service mocked."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.analytics import DailyRevenue

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


def _fake_user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.email = "ceo@acme.com"
    u.name = "CEO"
    u.role = UserRole.CEO
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


def _make_summary(**overrides):
    from app.schemas.analytics import DashboardSummaryOut
    defaults = dict(
        total_revenue=50000.0, top_sku="BLZ-BLK-M",
        roas=4.5, marketing_spend=10000.0,
        skus_below_reorder=3, active_warehouses=4,
        gross_margin=38.0, total_gross_profit=19000.0,
        procurement_spend=15000.0, unique_suppliers=8, avg_lead_days=6.5,
        daily_revenue=[
            DailyRevenue(date="2024-01-14", revenue=500.0),
            DailyRevenue(date="2024-01-15", revenue=50000.0),  # spike
            DailyRevenue(date="2024-01-16", revenue=480.0),
        ],
    )
    defaults.update(overrides)
    return DashboardSummaryOut(**defaults)


# ─── /insights/summary ───────────────────────────────────────────────────────

async def test_insights_summary_gemini_response():
    """Gemini JSON response is parsed into InsightsOut correctly."""
    gemini_json = (
        '{"summary": "Strong revenue performance with healthy margins.", '
        '"insights": ['
        '{"dept": "sales", "text": "Revenue up 12% MoM."}, '
        '{"dept": "marketing", "text": "ROAS above target."}, '
        '{"dept": "operations", "text": "3 SKUs need restock."}, '
        '{"dept": "finance", "text": "Gross margin stable at 38%."}, '
        '{"dept": "procurement", "text": "Lead times within SLA."}'
        ']}'
    )

    with (
        patch("app.domains.insights.insight_service.get_dashboard_summary",
              new=AsyncMock(return_value=_make_summary())),
        patch("app.domains.insights.insight_service.generate_text",
              new=AsyncMock(return_value=(gemini_json, "gemini"))),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/insights/summary")

    assert r.status_code == 200
    data = r.json()
    assert data["generated_by"] == "gemini"
    assert "Strong revenue" in data["summary"]
    assert len(data["insights"]) == 5
    assert data["insights"][0] == {"dept": "sales", "text": "Revenue up 12% MoM."}


async def test_insights_summary_fallback_on_bad_json():
    """If LLM returns non-JSON text, summary falls back to raw text with empty insights."""
    with (
        patch("app.domains.insights.insight_service.get_dashboard_summary",
              new=AsyncMock(return_value=_make_summary())),
        patch("app.domains.insights.insight_service.generate_text",
              new=AsyncMock(return_value=("Not valid JSON at all.", "groq"))),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/insights/summary")

    assert r.status_code == 200
    data = r.json()
    assert data["generated_by"] == "groq"
    assert data["summary"] == "Not valid JSON at all."
    assert data["insights"] == []


async def test_insights_summary_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/insights/summary")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── /insights/anomalies ─────────────────────────────────────────────────────

async def test_anomalies_empty_when_insufficient_data():
    """Returns empty list when fewer than 3 data points exist."""
    summary = _make_summary(daily_revenue=[DailyRevenue(date="2024-01-15", revenue=500.0)])

    with patch("app.domains.insights.anomaly_service.get_dashboard_summary",
               new=AsyncMock(return_value=summary)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/insights/anomalies")

    assert r.status_code == 200
    assert r.json() == []


async def test_anomalies_spike_flagged():
    """A single revenue spike > 2σ is detected and returned with correct z-score sign."""
    # 10 normal days at 500 + spike at 50000: z ≈ 3.2 (> 2σ threshold)
    normal_days = [DailyRevenue(date=f"2024-01-{i:02d}", revenue=500.0) for i in range(1, 11)]
    spike_day = DailyRevenue(date="2024-01-15", revenue=50000.0)
    summary = _make_summary(daily_revenue=[*normal_days, spike_day])

    with patch("app.domains.insights.anomaly_service.get_dashboard_summary",
               new=AsyncMock(return_value=summary)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/insights/anomalies")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["date"] == "2024-01-15"
    assert data[0]["revenue"] == 50000.0
    assert data[0]["z_score"] > 2.0


async def test_anomalies_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/insights/anomalies")

    app.dependency_overrides.clear()
    assert r.status_code == 403
