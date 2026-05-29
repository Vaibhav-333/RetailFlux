"""Forecasting endpoint tests (MongoDB + Prophet mocked)."""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.forecast import ForecastOut, ForecastPoint, SkuForecast

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


def _cursor(docs: list) -> MagicMock:
    c = MagicMock()
    c.to_list = AsyncMock(return_value=docs)
    return c


def _fake_points(n: int = 30) -> list[ForecastPoint]:
    base = date(2024, 2, 1)
    return [
        ForecastPoint(
            ds=(base + timedelta(days=i)).isoformat(),
            yhat=round(1000.0 + i * 10, 2),
            yhat_lower=round(900.0 + i * 10, 2),
            yhat_upper=round(1100.0 + i * 10, 2),
        )
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


async def test_sku_forecast_shape():
    """Forecast returns 30 points with ds, yhat, yhat_lower, yhat_upper."""
    daily_docs = [
        {"_id": f"2024-01-{i + 1:02d}", "revenue": 1000.0 + i * 5}
        for i in range(20)
    ]
    col = MagicMock()
    col.aggregate = MagicMock(return_value=_cursor(daily_docs))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    fake_pts = _fake_points(30)
    with (
        patch("app.domains.forecasting.forecast_service.get_mongo_db", return_value=mock_db),
        patch("app.domains.forecasting.forecast_service._fit_and_predict", return_value=fake_pts),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/forecasting/sku?sku=BLZ-BLK-M")

    assert r.status_code == 200
    data = r.json()
    assert data["sku"] == "BLZ-BLK-M"
    assert len(data["points"]) == 30
    pt = data["points"][0]
    assert "ds" in pt
    assert "yhat" in pt
    assert "yhat_lower" in pt
    assert "yhat_upper" in pt


async def test_sku_forecast_confidence_intervals():
    """yhat_lower <= yhat <= yhat_upper for every forecast point."""
    daily_docs = [
        {"_id": f"2024-01-{i + 1:02d}", "revenue": 500.0}
        for i in range(10)
    ]
    col = MagicMock()
    col.aggregate = MagicMock(return_value=_cursor(daily_docs))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    fake_pts = _fake_points(30)
    with (
        patch("app.domains.forecasting.forecast_service.get_mongo_db", return_value=mock_db),
        patch("app.domains.forecasting.forecast_service._fit_and_predict", return_value=fake_pts),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/forecasting/sku?sku=SHT-WHT-L")

    assert r.status_code == 200
    data = r.json()
    for pt in data["points"]:
        assert pt["yhat_lower"] <= pt["yhat"], "lower bound must not exceed yhat"
        assert pt["yhat"] <= pt["yhat_upper"], "yhat must not exceed upper bound"


async def test_sku_forecast_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/forecasting/sku?sku=BLZ-BLK-M")

    app.dependency_overrides.clear()
    assert r.status_code == 403


async def test_top_skus_forecast_shape():
    """top-skus returns a list of SkuForecast objects with 30 points each."""
    fake_forecast = ForecastOut(forecasts=[
        SkuForecast(sku="BLZ-BLK-M", points=_fake_points(30)),
        SkuForecast(sku="SHT-WHT-L", points=_fake_points(30)),
    ])

    with patch(
        "app.api.v1.endpoints.forecasting.get_top_skus_forecast",
        new=AsyncMock(return_value=fake_forecast),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/forecasting/top-skus")

    assert r.status_code == 200
    data = r.json()
    assert "forecasts" in data
    assert len(data["forecasts"]) == 2
    assert data["forecasts"][0]["sku"] == "BLZ-BLK-M"
    assert len(data["forecasts"][0]["points"]) == 30


async def test_top_skus_forecast_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/forecasting/top-skus")

    app.dependency_overrides.clear()
    assert r.status_code == 403
