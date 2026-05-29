from typing import Optional

from pydantic import BaseModel


class SkuRevenue(BaseModel):
    sku: str
    revenue: float


class RegionRevenue(BaseModel):
    region: str
    revenue: float


class DailyRevenue(BaseModel):
    date: str
    revenue: float


class SalesKpisOut(BaseModel):
    total_revenue: float
    total_units: int
    aov: float
    top_sku: str | None
    top_skus: list[SkuRevenue]
    revenue_by_region: list[RegionRevenue]
    daily_revenue: list[DailyRevenue]
    # compare_to deltas — percent change vs comparison period (None when not requested)
    deltas: Optional[dict[str, float]] = None


# ─── Marketing ────────────────────────────────────────────────────────────────

class CampaignKpis(BaseModel):
    campaign_id: str
    conversions: int


class CampaignSpend(BaseModel):
    campaign_id: str
    spend: float


class DailySpend(BaseModel):
    date: str
    spend: float


class MarketingKpisOut(BaseModel):
    total_spend: float
    total_conversions: int
    total_impressions: int
    ctr: float
    roas: float
    cac: float
    top_campaigns: list[CampaignKpis]
    spend_by_campaign: list[CampaignSpend]
    daily_spend: list[DailySpend]
    deltas: Optional[dict[str, float]] = None


# ─── Operations ───────────────────────────────────────────────────────────────

class WarehouseStock(BaseModel):
    warehouse: str
    stock_level: int


class LowStockSku(BaseModel):
    sku: str
    stock_level: float
    reorder_point: int


class DailyStockLevel(BaseModel):
    date: str
    avg_stock_level: float


class OperationsKpisOut(BaseModel):
    total_skus: int
    total_stock_units: int
    skus_below_reorder: int
    active_warehouses: int
    stock_by_warehouse: list[WarehouseStock]
    low_stock_skus: list[LowStockSku]
    daily_stock_level: list[DailyStockLevel]
    deltas: Optional[dict[str, float]] = None


# ─── Dashboard Summary ────────────────────────────────────────────────────────

class DashboardSummaryOut(BaseModel):
    # Sales
    total_revenue: float
    top_sku: str | None
    # Marketing
    roas: float
    marketing_spend: float
    # Operations
    skus_below_reorder: int
    active_warehouses: int
    # Finance
    gross_margin: float
    total_gross_profit: float
    # Procurement
    procurement_spend: float
    unique_suppliers: int
    avg_lead_days: float
    # Revenue sparkline (last 90 days)
    daily_revenue: list[DailyRevenue]


# ─── Procurement ──────────────────────────────────────────────────────────────

class SupplierSpend(BaseModel):
    supplier_id: str
    spend: float


class SkuCost(BaseModel):
    sku: str
    avg_unit_cost: float


class ProcurementKpisOut(BaseModel):
    total_spend: float
    total_units: int
    unique_suppliers: int
    avg_lead_days: float
    top_suppliers: list[SupplierSpend]
    daily_spend: list[DailySpend]
    top_sku_costs: list[SkuCost]
    deltas: Optional[dict[str, float]] = None


# ─── Finance ──────────────────────────────────────────────────────────────────

class CategoryRevenue(BaseModel):
    category: str
    revenue: float


class DailyGrossProfit(BaseModel):
    date: str
    gross_profit: float


class MonthlyPnL(BaseModel):
    month: str   # "YYYY-MM"
    revenue: float
    cogs: float


class FinanceKpisOut(BaseModel):
    total_revenue: float
    total_cogs: float
    total_gross_profit: float
    gross_margin: float
    revenue_by_category: list[CategoryRevenue]
    daily_gross_profit: list[DailyGrossProfit]
    monthly_pnl: list[MonthlyPnL]
    deltas: Optional[dict[str, float]] = None
