"""Upload endpoint tests (service layer mocked; no real DB/MinIO/Celery required)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.domains.auth.dependencies import get_current_user
from app.main import app
from app.models.upload import Upload, UploadStatus
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()
FAKE_UPL_ID = uuid.uuid4()
NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


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
    u.created_at = NOW
    return u


def _fake_upload(**kwargs) -> MagicMock:
    u = MagicMock(spec=Upload)
    u.id = FAKE_UPL_ID
    u.company_id = FAKE_CID
    u.user_id = FAKE_UID
    u.dept = "sales"
    u.original_name = "sales_jan.csv"
    u.storage_key = f"{FAKE_CID}/sales/{FAKE_UPL_ID}/sales_jan.csv"
    u.status = UploadStatus.QUEUED.value
    u.rows_total = None
    u.rows_clean = None
    u.rows_rejected = None
    u.schema_version = 1
    u.ge_report_id = None
    u.created_at = NOW
    u.updated_at = NOW
    for k, v in kwargs.items():
        setattr(u, k, v)
    return u


@pytest.fixture(autouse=True)
def _override_deps():
    user = _fake_user()
    access_tok = create_access_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})
    mock_db = AsyncMock()

    async def _fake_db():
        yield mock_db

    async def _fake_user_dep():
        return user

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user] = _fake_user_dep
    yield {"user": user, "token": access_tok, "db": mock_db}
    app.dependency_overrides.clear()


async def test_create_upload_returns_201():
    upload = _fake_upload()
    with patch("app.domains.uploads.service.create_upload", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = upload
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/uploads",
                files={"file": ("sales.csv", b"date,product_id,sku,quantity,revenue\n2024-01-01,P1,SKU1,10,100.0", "text/csv")},
                data={"dept": "sales"},
            )

    assert r.status_code == 201
    data = r.json()
    assert data["dept"] == "sales"
    assert data["status"] == "queued"
    mock_svc.assert_awaited_once()


async def test_create_upload_requires_auth():
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/uploads",
            files={"file": ("sales.csv", b"col\nval", "text/csv")},
            data={"dept": "sales"},
        )
    assert r.status_code == 403


async def test_list_uploads_returns_items():
    uploads = [_fake_upload(), _fake_upload(dept="marketing")]
    with patch("app.domains.uploads.service.list_uploads", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = (uploads, 2)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/uploads")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_upload_returns_single():
    upload = _fake_upload(status=UploadStatus.COMPLETE.value, rows_total=100, rows_clean=95, rows_rejected=5)
    with patch("app.domains.uploads.service.get_upload", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = upload
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/uploads/{FAKE_UPL_ID}")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "complete"
    assert data["rows_total"] == 100
    assert data["rows_clean"] == 95


async def test_get_upload_not_found():
    from fastapi import HTTPException
    with patch("app.domains.uploads.service.get_upload", new_callable=AsyncMock) as mock_svc:
        mock_svc.side_effect = HTTPException(status_code=404, detail="Upload not found")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/uploads/{uuid.uuid4()}")

    assert r.status_code == 404
