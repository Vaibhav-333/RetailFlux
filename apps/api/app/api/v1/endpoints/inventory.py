"""Inventory intelligence endpoints — Session 32 + Session 33."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.inventory.abc_xyz_service import (
    get_abc_matrix,
    get_abc_xyz_matrix,
    get_xyz_matrix,
)
from app.domains.inventory.aging_service import get_aging_buckets
from app.domains.inventory.anomaly_service import get_inventory_anomalies
from app.domains.inventory.copilot_service import inventory_copilot_ask
from app.domains.inventory.inventory_explain_service import explain_reorder_recommendation
from app.domains.inventory.reorder_service import (
    get_dead_stock,
    get_overstock,
    get_reorder_queue,
    get_understock,
    reorder_item_id,
)
from app.domains.inventory.replenishment_service import (
    get_heatmap,
    get_replenishment_suggestions,
    get_transfer_suggestions,
)
from app.domains.inventory.scoring_service import get_health_scores
from app.domains.inventory.seasonality_service import get_seasonality
from app.domains.inventory.service import get_inventory_overview, get_sku_list
from app.domains.inventory.valuation_service import get_valuation
from app.domains.inventory.velocity_service import get_velocity
from app.models.purchase_order import PoLine, PurchaseOrder
from app.models.user import User
from app.schemas.inventory import (
    AbcMatrixOut,
    AbcXyzMatrixOut,
    AgingOut,
    AnomalyOut,
    CopilotAskIn,
    CopilotAskOut,
    ExplanationOut,
    HealthScoreOut,
    InventoryOverviewOut,
    ReorderAcceptOut,
    ReorderQueueOut,
    ReplenishmentOut,
    SeasonalityOut,
    SkuListOut,
    ValuationOut,
    VelocityOut,
    XyzMatrixOut,
)

router = APIRouter()


# ── Session 32 endpoints (inventory foundation) ───────────────────────────────


@router.get("/overview", response_model=InventoryOverviewOut)
async def inventory_overview(
    current_user: User = Depends(get_current_user),
) -> InventoryOverviewOut:
    return await get_inventory_overview(company_id=str(current_user.company_id))


@router.get("/skus", response_model=SkuListOut)
async def sku_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Filter by SKU substring"),
    current_user: User = Depends(get_current_user),
) -> SkuListOut:
    return await get_sku_list(
        company_id=str(current_user.company_id),
        page=page,
        page_size=page_size,
        search=search,
    )


@router.get("/abc", response_model=AbcMatrixOut)
async def abc_matrix(
    current_user: User = Depends(get_current_user),
) -> AbcMatrixOut:
    return await get_abc_matrix(company_id=str(current_user.company_id))


@router.get("/xyz", response_model=XyzMatrixOut)
async def xyz_matrix(
    current_user: User = Depends(get_current_user),
) -> XyzMatrixOut:
    return await get_xyz_matrix(company_id=str(current_user.company_id))


@router.get("/abc-xyz", response_model=AbcXyzMatrixOut)
async def abc_xyz_matrix(
    current_user: User = Depends(get_current_user),
) -> AbcXyzMatrixOut:
    return await get_abc_xyz_matrix(company_id=str(current_user.company_id))


@router.get("/aging", response_model=AgingOut)
async def aging_buckets(
    current_user: User = Depends(get_current_user),
) -> AgingOut:
    return await get_aging_buckets(company_id=str(current_user.company_id))


@router.get("/valuation", response_model=ValuationOut)
async def valuation(
    current_user: User = Depends(get_current_user),
) -> ValuationOut:
    return await get_valuation(company_id=str(current_user.company_id))


@router.get("/velocity", response_model=VelocityOut)
async def velocity(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
) -> VelocityOut:
    return await get_velocity(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
    )


# ── Session 33 endpoints (intelligence layer) ─────────────────────────────────


@router.get("/reorder-queue", response_model=ReorderQueueOut)
async def reorder_queue(
    current_user: User = Depends(get_current_user),
) -> ReorderQueueOut:
    """Ranked reorder recommendations with EOQ + safety stock math."""
    return await get_reorder_queue(company_id=str(current_user.company_id))


@router.post("/reorder-queue/{item_id}/accept", response_model=ReorderAcceptOut)
async def accept_reorder(
    item_id: str = Path(..., description="Reorder item hash ID"),
    quantity: Optional[float] = Body(None, embed=True, description="Override order quantity"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReorderAcceptOut:
    """Accept a reorder recommendation → creates a draft PurchaseOrder."""
    company_id = str(current_user.company_id)

    # Find the item in the queue
    queue = await get_reorder_queue(company_id)
    item = next((i for i in queue.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Reorder item not found")

    order_qty = quantity if quantity and quantity > 0 else item.recommended_order_qty
    unit_cost = item.estimated_cost / item.recommended_order_qty if item.recommended_order_qty > 0 else 0.0

    # Create PurchaseOrder in Postgres
    po = PurchaseOrder(
        company_id=current_user.company_id,
        status="draft",
        supplier_name=None,  # Populated later by replenishment_service
        total_cost=round(order_qty * unit_cost, 2),
        created_by=current_user.id,
        metadata_={"source": "reorder_queue", "item_id": item_id, "sku": item.sku},
    )
    db.add(po)
    await db.flush()  # Get po.id before adding lines

    line = PoLine(
        po_id=po.id,
        sku=item.sku,
        quantity=order_qty,
        unit_cost=unit_cost,
    )
    db.add(line)
    await db.commit()
    await db.refresh(po)

    return ReorderAcceptOut(
        message=f"Draft purchase order created for {item.sku} ({order_qty:.0f} units)",
        po_id=str(po.id),
        sku=item.sku,
        quantity=order_qty,
    )


@router.get("/dead-stock", response_model=dict)
async def dead_stock(
    days: int = Query(90, ge=30, le=365, description="Days without sales to classify as dead"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """SKUs not sold in N days, ranked by tied-up capital."""
    return await get_dead_stock(
        company_id=str(current_user.company_id),
        days_threshold=days,
    )


@router.get("/overstock", response_model=dict)
async def overstock(
    target_doh: float = Query(90.0, ge=7.0, description="Target days-on-hand threshold"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """SKUs with DOH above target, with $ exposure."""
    return await get_overstock(
        company_id=str(current_user.company_id),
        target_doh=target_doh,
    )


@router.get("/understock", response_model=dict)
async def understock(
    current_user: User = Depends(get_current_user),
) -> dict:
    """SKUs below safety stock + projected stock-out days."""
    return await get_understock(company_id=str(current_user.company_id))


@router.get("/health-score", response_model=HealthScoreOut)
async def health_score(
    current_user: User = Depends(get_current_user),
) -> HealthScoreOut:
    """Distribution of composite 0-100 inventory health scores + top/bottom 20 SKUs."""
    return await get_health_scores(company_id=str(current_user.company_id))


@router.get("/anomalies", response_model=AnomalyOut)
async def inventory_anomalies(
    current_user: User = Depends(get_current_user),
) -> AnomalyOut:
    """Detect demand/stock anomalies using IsolationForest."""
    return await get_inventory_anomalies(company_id=str(current_user.company_id))


@router.get("/seasonality/{sku}", response_model=SeasonalityOut)
async def sku_seasonality(
    sku: str = Path(..., description="SKU code"),
    current_user: User = Depends(get_current_user),
) -> SeasonalityOut:
    """STL decomposition: trend + seasonal + residual for a single SKU."""
    return await get_seasonality(
        company_id=str(current_user.company_id),
        sku=sku,
    )


@router.get("/replenishment", response_model=ReplenishmentOut)
async def replenishment(
    current_user: User = Depends(get_current_user),
) -> ReplenishmentOut:
    """Supplier-aware PO draft suggestions grouped by supplier."""
    return await get_replenishment_suggestions(company_id=str(current_user.company_id))


@router.get("/transfer-suggestions", response_model=dict)
async def transfer_suggestions(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Inter-warehouse transfer recommendations to balance demand vs stock."""
    return await get_transfer_suggestions(company_id=str(current_user.company_id))


@router.get("/heatmap", response_model=dict)
async def stock_heatmap(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Warehouse × Category stock health heatmap."""
    return await get_heatmap(company_id=str(current_user.company_id))


@router.post("/copilot", response_model=CopilotAskOut)
async def inventory_copilot(
    body: CopilotAskIn,
    current_user: User = Depends(get_current_user),
) -> CopilotAskOut:
    """Answer inventory-related natural language questions."""
    return await inventory_copilot_ask(
        question=body.question,
        company_id=str(current_user.company_id),
        context=body.context,
    )


@router.get("/explain/{recommendation_id}", response_model=ExplanationOut)
async def explain_recommendation(
    recommendation_id: str = Path(..., description="SKU or reorder item ID"),
    current_user: User = Depends(get_current_user),
) -> ExplanationOut:
    """AI-generated rationale for an inventory recommendation."""
    company_id = str(current_user.company_id)

    # Try to find context from reorder queue
    context: dict = {}
    try:
        queue = await get_reorder_queue(company_id)
        item = next(
            (i for i in queue.items if i.id == recommendation_id or i.sku == recommendation_id),
            None,
        )
        if item:
            context = {
                "sku": item.sku,
                "current_stock": item.current_stock,
                "reorder_point": item.reorder_point,
                "eoq": item.eoq,
                "safety_stock": item.safety_stock,
                "avg_daily_demand": item.avg_daily_demand,
                "lead_time_days": item.lead_time_days,
                "days_until_stockout": item.days_until_stockout,
                "priority": item.priority,
            }
    except Exception:
        pass

    sku = context.get("sku", recommendation_id)
    return await explain_reorder_recommendation(
        sku=sku,
        context=context,
        recommendation_id=recommendation_id,
    )
