"""Purchase Orders API — auto-replenishment approval workflow (Session 35)."""
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.pricing.po_approval_service import (
    approve_purchase_order,
    bulk_approve,
    cancel_purchase_order,
    create_purchase_order,
    export_purchase_order,
    get_purchase_order,
    list_purchase_orders,
    reject_purchase_order,
    submit_for_approval,
)
from app.models.user import User

router = APIRouter()


class PoLineIn(BaseModel):
    sku: str
    quantity: float
    unit_cost: float
    notes: Optional[str] = None


class CreatePoIn(BaseModel):
    supplier_name: str
    lines: list[PoLineIn]
    notes: Optional[str] = None


class RejectIn(BaseModel):
    reason: Optional[str] = None


class BulkApproveIn(BaseModel):
    po_ids: list[uuid.UUID]


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_po(
    body: CreatePoIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a draft purchase order."""
    po = await create_purchase_order(
        db=db,
        company_id=current_user.company_id,
        created_by=current_user.id,
        supplier_name=body.supplier_name,
        lines=[ln.model_dump() for ln in body.lines],
        notes=body.notes,
    )
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


@router.get("")
async def list_pos(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List purchase orders (paginated, filterable by status)."""
    return await list_purchase_orders(
        db=db,
        company_id=current_user.company_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{po_id}")
async def get_po(
    po_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a single PO with line items."""
    try:
        po = await get_purchase_order(db, current_user.company_id, po_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


# ── Workflow transitions ──────────────────────────────────────────────────────

@router.post("/{po_id}/submit")
async def submit_po(
    po_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Submit draft PO for approval."""
    try:
        po = await submit_for_approval(db, current_user.company_id, po_id, current_user)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


@router.post("/{po_id}/approve")
async def approve_po(
    po_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Approve a pending PO (CEO/Admin/Finance only)."""
    try:
        po = await approve_purchase_order(db, current_user.company_id, po_id, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


@router.post("/{po_id}/reject")
async def reject_po(
    po_id: uuid.UUID = Path(...),
    body: RejectIn = Body(default=RejectIn()),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Reject a pending PO."""
    try:
        po = await reject_purchase_order(db, current_user.company_id, po_id, current_user, body.reason)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


@router.post("/{po_id}/cancel")
async def cancel_po(
    po_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a PO that has not been approved/sent yet."""
    try:
        po = await cancel_purchase_order(db, current_user.company_id, po_id, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    from app.domains.pricing.po_approval_service import _po_to_dict
    return _po_to_dict(po)


@router.post("/bulk-approve")
async def bulk_approve_pos(
    body: BulkApproveIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk-approve multiple POs in one request."""
    try:
        result = await bulk_approve(db, current_user.company_id, body.po_ids, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return result


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/{po_id}/export")
async def export_po(
    po_id: uuid.UUID = Path(...),
    format: str = Query("json", description="Export format: json, csv, email"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export a PO as JSON, CSV, or email draft."""
    try:
        content, media_type, filename = await export_purchase_order(
            db, current_user.company_id, po_id, format=format
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
