"""Purchase order approval workflow tests (Session 35)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.pricing.po_approval_service import (
    bulk_approve,
)
from app.main import app
from app.models.purchase_order import PoLine, PurchaseOrder
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()
FAKE_PO_ID = uuid.uuid4()


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


def _fake_po(status: str = "pending_approval") -> MagicMock:
    po = MagicMock(spec=PurchaseOrder)
    po.id = FAKE_PO_ID
    po.company_id = FAKE_CID
    po.status = status
    po.supplier_name = "Test Supplier"
    po.total_cost = Decimal("1500.00")
    po.notes = None
    po.created_by = FAKE_UID
    po.approved_by = None
    po.approved_at = None
    po.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    po.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    po.lines = []
    return po


# ── Auth guard tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_purchase_orders_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/purchase-orders")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_purchase_order_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/purchase-orders", json={
            "supplier_name": "Test", "lines": []
        })
    assert r.status_code in (401, 403)


# ── RBAC tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_approve_rejects_sales_role():
    """SALES role cannot bulk-approve purchase orders."""
    db = AsyncMock()
    company_id = uuid.uuid4()
    actor = _fake_user(UserRole.SALES)
    actor.role = UserRole.SALES

    with pytest.raises(PermissionError, match="Only CEO"):
        await bulk_approve(db, company_id, [uuid.uuid4()], actor)


@pytest.mark.asyncio
async def test_approve_endpoint_forbidden_for_sales():
    """SALES user should get 403 when approving a PO."""
    from app.domains.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: _fake_user(UserRole.SALES)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/purchase-orders/{FAKE_PO_ID}/approve",
                headers={"Authorization": "Bearer test-token"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


# ── Workflow state machine tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_po_success():
    """CEO approving a pending_approval PO should succeed."""
    from app.domains.pricing.po_approval_service import approve_purchase_order

    po = _fake_po(status="pending_approval")
    actor = _fake_user(UserRole.CEO)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=po)))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Patch get_purchase_order to return our fake PO
    with patch(
        "app.domains.pricing.po_approval_service.get_purchase_order",
        new_callable=AsyncMock,
        return_value=po,
    ):
        result = await approve_purchase_order(db, FAKE_CID, FAKE_PO_ID, actor)

    assert result.status == "approved"
    assert result.approved_by == actor.id
    assert result.approved_at is not None


@pytest.mark.asyncio
async def test_cannot_approve_already_approved_po():
    """Attempting to approve an already-approved PO should raise ValueError."""
    from app.domains.pricing.po_approval_service import approve_purchase_order

    po = _fake_po(status="approved")
    actor = _fake_user(UserRole.CEO)

    db = AsyncMock()

    with (
        patch(
            "app.domains.pricing.po_approval_service.get_purchase_order",
            new_callable=AsyncMock,
            return_value=po,
        ),
        pytest.raises(ValueError, match="Cannot approve PO in status 'approved'"),
    ):
        await approve_purchase_order(db, FAKE_CID, FAKE_PO_ID, actor)


@pytest.mark.asyncio
async def test_reject_po_success():
    """CEO rejecting a pending PO should mark it rejected."""
    from app.domains.pricing.po_approval_service import reject_purchase_order

    po = _fake_po(status="pending_approval")
    actor = _fake_user(UserRole.CEO)

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch(
        "app.domains.pricing.po_approval_service.get_purchase_order",
        new_callable=AsyncMock,
        return_value=po,
    ):
        result = await reject_purchase_order(db, FAKE_CID, FAKE_PO_ID, actor, reason="Too expensive")

    assert result.status == "rejected"
    assert "Too expensive" in (result.notes or "")


@pytest.mark.asyncio
async def test_bulk_approve_returns_results():
    """Bulk approve should return approved list and failed list."""
    approved_po = _fake_po(status="pending_approval")
    already_po = _fake_po(status="approved")
    already_po.id = uuid.uuid4()

    actor = _fake_user(UserRole.CEO)
    db = AsyncMock()
    db.commit = AsyncMock()

    call_count = [0]

    async def _mock_get_po(db, company_id, po_id):
        call_count[0] += 1
        if call_count[0] == 1:
            return approved_po
        return already_po

    with patch(
        "app.domains.pricing.po_approval_service.get_purchase_order",
        side_effect=_mock_get_po,
    ):
        result = await bulk_approve(
            db, FAKE_CID, [approved_po.id, already_po.id], actor
        )

    assert result["total_approved"] == 1
    assert len(result["approved"]) == 1
    assert len(result["failed"]) == 1


# ── Export tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_po_csv_content():
    """CSV export should contain SKU, quantity, cost header row."""
    from app.domains.pricing.po_approval_service import export_purchase_order, _po_to_dict

    po = _fake_po(status="approved")
    line = MagicMock(spec=PoLine)
    line.id = uuid.uuid4()
    line.sku = "BLZ-BLK-M"
    line.quantity = Decimal("50")
    line.unit_cost = Decimal("25.00")
    line.notes = None
    po.lines = [line]

    db = AsyncMock()

    with patch(
        "app.domains.pricing.po_approval_service.get_purchase_order",
        new_callable=AsyncMock,
        return_value=po,
    ):
        content, media_type, filename = await export_purchase_order(
            db, FAKE_CID, FAKE_PO_ID, format="csv"
        )

    assert media_type == "text/csv"
    assert "BLZ-BLK-M" in content
    assert "SKU" in content  # header row


@pytest.mark.asyncio
async def test_export_po_json_content():
    """JSON export should contain the PO structure."""
    import json
    from app.domains.pricing.po_approval_service import export_purchase_order

    po = _fake_po(status="approved")
    po.lines = []

    db = AsyncMock()

    with patch(
        "app.domains.pricing.po_approval_service.get_purchase_order",
        new_callable=AsyncMock,
        return_value=po,
    ):
        content, media_type, filename = await export_purchase_order(
            db, FAKE_CID, FAKE_PO_ID, format="json"
        )

    assert media_type == "application/json"
    parsed = json.loads(content)
    assert "supplier_name" in parsed
    assert "lines" in parsed
    assert "status" in parsed


# ── List endpoint test ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_purchase_orders_returns_pagination():
    """List endpoint returns paginated structure."""
    from app.domains.auth.dependencies import get_current_user
    from app.core.database import get_db

    empty_scalars = MagicMock()
    empty_scalars.all = MagicMock(return_value=[])
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=empty_scalars)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(
                "/api/v1/purchase-orders",
                headers={"Authorization": "Bearer test-token"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
