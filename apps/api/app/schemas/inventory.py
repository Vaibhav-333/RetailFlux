"""Inventory intelligence Pydantic schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class InventoryOverviewOut(BaseModel):
    total_inventory_value: float
    total_skus: int
    total_stock_units: int
    skus_at_risk: int
    stockout_risk_skus: int
    dead_stock_value: float
    reorder_queue_count: int
    avg_health_score: float


class SkuSummaryOut(BaseModel):
    sku: str
    current_stock: float
    reorder_point: float
    avg_unit_cost: float
    total_value: float
    days_on_hand: Optional[float]
    abc_class: Optional[str]
    xyz_class: Optional[str]
    avg_daily_demand: float


class SkuListOut(BaseModel):
    items: list[SkuSummaryOut]
    total: int
    page: int
    page_size: int


class AbcMatrixOut(BaseModel):
    segments: dict[str, list[str]]
    sku_counts: dict[str, int]
    revenue_pcts: dict[str, float]
    total_revenue: float


class XyzMatrixOut(BaseModel):
    segments: dict[str, list[str]]
    sku_counts: dict[str, int]
    cv_ranges: dict[str, str]


class AbcXyzCell(BaseModel):
    abc: str
    xyz: str
    sku_count: int
    total_revenue: float
    skus: list[str]


class AbcXyzMatrixOut(BaseModel):
    cells: list[AbcXyzCell]
    total_skus: int
    total_revenue: float


class AgingBucket(BaseModel):
    bucket: str
    sku_count: int
    total_value: float
    skus: list[str]


class AgingOut(BaseModel):
    buckets: list[AgingBucket]
    total_skus: int
    total_value: float


class CategoryValuation(BaseModel):
    category: str
    cost_value: float
    retail_value: float
    sku_count: int


class ValuationOut(BaseModel):
    total_cost_value: float
    total_retail_value: float
    potential_margin: float
    by_category: list[CategoryValuation]


class SkuVelocity(BaseModel):
    sku: str
    units_sold: float
    current_stock: float
    sell_through: float
    avg_unit_cost: float
    revenue: float


class VelocityOut(BaseModel):
    fast_movers: list[SkuVelocity]
    slow_movers: list[SkuVelocity]
    avg_sell_through: float
    total_skus_analyzed: int


# ── Session 33 schemas ────────────────────────────────────────────────────────


class ReorderItem(BaseModel):
    id: str
    sku: str
    current_stock: float
    reorder_point: float
    safety_stock: float
    eoq: float
    avg_daily_demand: float
    lead_time_days: float
    days_until_stockout: Optional[float]
    priority: str  # critical | high | medium
    recommended_order_qty: float
    estimated_cost: float


class ReorderQueueOut(BaseModel):
    items: list[ReorderItem]
    total: int


class SkuHealthScore(BaseModel):
    sku: str
    score: float
    components: dict[str, float]
    category: Optional[str]
    abc_class: Optional[str]
    xyz_class: Optional[str]


class HealthScoreOut(BaseModel):
    avg_score: float
    top_skus: list[SkuHealthScore]
    bottom_skus: list[SkuHealthScore]
    distribution: dict[str, int]
    total_skus: int


class InventoryAnomalyItem(BaseModel):
    sku: str
    anomaly_type: str  # demand_spike | demand_drop | unusual_pattern
    severity: str  # high | medium | low
    metric_value: float
    baseline_value: float
    detected_at: str


class AnomalyOut(BaseModel):
    anomalies: list[InventoryAnomalyItem]
    total: int


class SeasonalityPoint(BaseModel):
    date: str
    value: float


class SeasonalityOut(BaseModel):
    sku: str
    trend: list[SeasonalityPoint]
    seasonal: list[SeasonalityPoint]
    residual: list[SeasonalityPoint]
    period_days: int
    has_yearly_pattern: bool


class ExplanationOut(BaseModel):
    recommendation_id: str
    rationale: str
    confidence: str  # high | medium | low
    key_factors: list[str]
    alternatives: list[str]
    cached: bool = False


class CopilotAskIn(BaseModel):
    question: str
    context: Optional[dict] = None


class CopilotAskOut(BaseModel):
    answer: str
    context_used: list[str]
    provider: str


class ReorderAcceptOut(BaseModel):
    message: str
    po_id: Optional[str]
    sku: str
    quantity: float


class PoLineItem(BaseModel):
    sku: str
    quantity: float
    unit_cost: float
    line_total: float


class SupplierPoDraft(BaseModel):
    supplier_name: str
    lines: list[PoLineItem]
    total_cost: float
    lead_time_days: int
    expected_delivery: str
    sku_count: int
    priority: str


class ReplenishmentOut(BaseModel):
    po_drafts: list[SupplierPoDraft]
    total_suggested_cost: float
