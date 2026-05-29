"""Purchase-order approval workflow, bulk approve, and integration-ready export.

PO status transitions:
  draft → pending_approval → approved → sent / rejected / cancelled

Only CEO/Admin/Finance can approve.  Buyer (procurement role) creates and submits.
"""
from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase_order import PoLine, PurchaseOrder
from app.models.user import User, UserRole

_ALLOWED_APPROVER_ROLES = {UserRole.CEO, UserRole.ADMIN, UserRole.FINANCE}
_SUBMITTER_ROLES = {UserRole.CEO, UserRole.ADMIN, UserRole.FINANCE, UserRole.PROCUREMENT, UserRole.OPERATIONS}


def _assert_company(po: PurchaseOrder, company_id: uuid.UUID) -> None:
    if po.company_id != company_id:
        raise PermissionError("PO not found")


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    created_by: uuid.UUID,
    supplier_name: str,
    lines: list[dict],
    notes: Optional[str] = None,
) -> PurchaseOrder:
    """Create a draft PO with line items."""
    total_cost = sum(
        float(ln.get("quantity", 0)) * float(ln.get("unit_cost", 0))
        for ln in lines
    )
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=company_id,
        status="draft",
        supplier_name=supplier_name,
        total_cost=total_cost,
        notes=notes,
        created_by=created_by,
    )
    db.add(po)
    await db.flush()

    for ln in lines:
        db.add(PoLine(
            id=uuid.uuid4(),
            po_id=po.id,
            sku=str(ln["sku"]),
            quantity=float(ln.get("quantity", 0)),
            unit_cost=float(ln.get("unit_cost", 0)),
            notes=ln.get("notes"),
        ))

    await db.commit()
    await db.refresh(po)
    return po


# ── Read ──────────────────────────────────────────────────────────────────────

async def list_purchase_orders(
    db: AsyncSession,
    company_id: uuid.UUID,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    q = select(PurchaseOrder).where(PurchaseOrder.company_id == company_id)
    if status:
        q = q.where(PurchaseOrder.status == status)
    q = q.order_by(PurchaseOrder.created_at.desc())

    count_q = select(PurchaseOrder).where(PurchaseOrder.company_id == company_id)
    if status:
        count_q = count_q.where(PurchaseOrder.status == status)
    count_result = await db.execute(count_q)
    total = len(count_result.scalars().all())

    q = q.offset((page - 1) * page_size).limit(page_size)
    q = q.options(selectinload(PurchaseOrder.lines))
    result = await db.execute(q)
    items = result.scalars().all()

    return {"items": [_po_to_dict(po) for po in items], "total": total, "page": page, "page_size": page_size}


async def get_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    q = select(PurchaseOrder).where(
        PurchaseOrder.id == po_id,
        PurchaseOrder.company_id == company_id,
    ).options(selectinload(PurchaseOrder.lines))
    result = await db.execute(q)
    po = result.scalar_one_or_none()
    if not po:
        raise ValueError("PO not found")
    return po


# ── Transitions ───────────────────────────────────────────────────────────────

async def submit_for_approval(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    actor: User,
) -> PurchaseOrder:
    if actor.role not in _SUBMITTER_ROLES:
        raise PermissionError("Only procurement/finance/admin can submit POs")
    po = await get_purchase_order(db, company_id, po_id)
    if po.status != "draft":
        raise ValueError(f"Cannot submit PO in status '{po.status}'")
    po.status = "pending_approval"
    po.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return po


async def approve_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    actor: User,
) -> PurchaseOrder:
    if actor.role not in _ALLOWED_APPROVER_ROLES:
        raise PermissionError("Only CEO, Admin, or Finance can approve POs")
    po = await get_purchase_order(db, company_id, po_id)
    if po.status not in ("pending_approval", "draft"):
        raise ValueError(f"Cannot approve PO in status '{po.status}'")
    po.status = "approved"
    po.approved_by = actor.id
    po.approved_at = datetime.now(timezone.utc)
    po.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return po


async def reject_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    actor: User,
    reason: Optional[str] = None,
) -> PurchaseOrder:
    if actor.role not in _ALLOWED_APPROVER_ROLES:
        raise PermissionError("Only CEO, Admin, or Finance can reject POs")
    po = await get_purchase_order(db, company_id, po_id)
    if po.status not in ("pending_approval", "draft"):
        raise ValueError(f"Cannot reject PO in status '{po.status}'")
    po.status = "rejected"
    po.notes = f"Rejected: {reason}" if reason else po.notes
    po.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return po


async def cancel_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    actor: User,
) -> PurchaseOrder:
    po = await get_purchase_order(db, company_id, po_id)
    if actor.role not in _ALLOWED_APPROVER_ROLES and po.created_by != actor.id:
        raise PermissionError("Only creator or admin can cancel POs")
    if po.status in ("approved", "sent"):
        raise ValueError(f"Cannot cancel PO in status '{po.status}'")
    po.status = "cancelled"
    po.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return po


async def bulk_approve(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_ids: list[uuid.UUID],
    actor: User,
) -> dict:
    if actor.role not in _ALLOWED_APPROVER_ROLES:
        raise PermissionError("Only CEO, Admin, or Finance can bulk-approve POs")

    approved = []
    failed = []
    now = datetime.now(timezone.utc)

    for po_id in po_ids:
        try:
            po = await get_purchase_order(db, company_id, po_id)
            if po.status in ("pending_approval", "draft"):
                po.status = "approved"
                po.approved_by = actor.id
                po.approved_at = now
                po.updated_at = now
                approved.append(str(po_id))
            else:
                failed.append({"id": str(po_id), "reason": f"Status was '{po.status}'"})
        except Exception as exc:
            failed.append({"id": str(po_id), "reason": str(exc)})

    await db.commit()
    return {"approved": approved, "failed": failed, "total_approved": len(approved)}


# ── Export ────────────────────────────────────────────────────────────────────

async def export_purchase_order(
    db: AsyncSession,
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    format: str = "json",
) -> tuple[str, str, str]:
    """Return (content, media_type, filename) for the given export format."""
    po = await get_purchase_order(db, company_id, po_id)
    po_dict = _po_to_dict(po)

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["SKU", "Quantity", "Unit Cost", "Line Total"])
        for line in po_dict.get("lines", []):
            qty = float(line.get("quantity", 0))
            uc = float(line.get("unit_cost", 0))
            writer.writerow([
                line.get("sku", ""),
                qty,
                uc,
                round(qty * uc, 2),
            ])
        content = buf.getvalue()
        filename = f"PO-{po_id}-{po_dict.get('supplier_name', 'unknown')}.csv"
        return content, "text/csv", filename

    elif format == "email":
        lines_text = "\n".join(
            f"  - {ln.get('sku')}  qty={ln.get('quantity')}  cost=${ln.get('unit_cost')}"
            for ln in po_dict.get("lines", [])
        )
        content = (
            f"Subject: Purchase Order #{str(po_id)[:8].upper()} — {po_dict.get('supplier_name', '')}\n\n"
            f"Dear {po_dict.get('supplier_name', 'Supplier')},\n\n"
            f"Please find below our purchase order:\n\n"
            f"{lines_text}\n\n"
            f"Total: ${po_dict.get('total_cost', 0):,.2f}\n"
            f"Notes: {po_dict.get('notes', 'N/A')}\n\n"
            f"Please confirm receipt and expected delivery date.\n\n"
            f"Thank you."
        )
        return content, "text/plain", f"po_{str(po_id)[:8]}_email.txt"

    else:  # json (default)
        content = json.dumps(po_dict, indent=2, default=str)
        return content, "application/json", f"po_{str(po_id)[:8]}.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _po_to_dict(po: PurchaseOrder) -> dict:
    return {
        "id": str(po.id),
        "company_id": str(po.company_id),
        "status": po.status,
        "supplier_name": po.supplier_name,
        "total_cost": float(po.total_cost),
        "notes": po.notes,
        "created_by": str(po.created_by) if po.created_by else None,
        "approved_by": str(po.approved_by) if po.approved_by else None,
        "approved_at": po.approved_at.isoformat() if po.approved_at else None,
        "created_at": po.created_at.isoformat() if po.created_at else None,
        "updated_at": po.updated_at.isoformat() if po.updated_at else None,
        "lines": [
            {
                "id": str(ln.id),
                "sku": ln.sku,
                "quantity": float(ln.quantity),
                "unit_cost": float(ln.unit_cost),
                "line_total": round(float(ln.quantity) * float(ln.unit_cost), 2),
                "notes": ln.notes,
            }
            for ln in (po.lines or [])
        ],
    }
