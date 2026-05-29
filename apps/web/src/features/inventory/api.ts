import { api } from "@/lib/api";
import type {
  AbcMatrixOut,
  AbcXyzMatrixOut,
  AgingOut,
  AnomalyOut,
  CopilotAskIn,
  CopilotAskOut,
  DeadStockOut,
  ExplanationOut,
  HealthScoreOut,
  HeatmapOut,
  InventoryOverviewOut,
  OverstockOut,
  ReorderAcceptOut,
  ReorderQueueOut,
  ReplenishmentOut,
  SeasonalityOut,
  SkuListOut,
  UnderstockOut,
  ValuationOut,
  VelocityOut,
  XyzMatrixOut,
} from "@/types";

export async function getInventoryOverviewApi(): Promise<InventoryOverviewOut> {
  const r = await api.get<InventoryOverviewOut>("/inventory/overview");
  return r.data;
}

export async function getSkuListApi(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<SkuListOut> {
  const r = await api.get<SkuListOut>("/inventory/skus", { params });
  return r.data;
}

export async function getAbcMatrixApi(): Promise<AbcMatrixOut> {
  const r = await api.get<AbcMatrixOut>("/inventory/abc");
  return r.data;
}

export async function getXyzMatrixApi(): Promise<XyzMatrixOut> {
  const r = await api.get<XyzMatrixOut>("/inventory/xyz");
  return r.data;
}

export async function getAbcXyzMatrixApi(): Promise<AbcXyzMatrixOut> {
  const r = await api.get<AbcXyzMatrixOut>("/inventory/abc-xyz");
  return r.data;
}

export async function getAgingApi(): Promise<AgingOut> {
  const r = await api.get<AgingOut>("/inventory/aging");
  return r.data;
}

export async function getValuationApi(): Promise<ValuationOut> {
  const r = await api.get<ValuationOut>("/inventory/valuation");
  return r.data;
}

export async function getVelocityApi(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<VelocityOut> {
  const r = await api.get<VelocityOut>("/inventory/velocity", { params });
  return r.data;
}

// ── Session 33 — Inventory Intelligence ──────────────────────────────────────

export async function getReorderQueueApi(): Promise<ReorderQueueOut> {
  const r = await api.get<ReorderQueueOut>("/inventory/reorder-queue");
  return r.data;
}

export async function acceptReorderApi(
  itemId: string,
  quantity?: number,
): Promise<ReorderAcceptOut> {
  const r = await api.post<ReorderAcceptOut>(
    `/inventory/reorder-queue/${itemId}/accept`,
    quantity !== undefined ? { quantity } : {},
  );
  return r.data;
}

export async function getDeadStockApi(days = 90): Promise<DeadStockOut> {
  const r = await api.get<DeadStockOut>("/inventory/dead-stock", { params: { days } });
  return r.data;
}

export async function getOverstockApi(targetDoh = 90): Promise<OverstockOut> {
  const r = await api.get<OverstockOut>("/inventory/overstock", { params: { target_doh: targetDoh } });
  return r.data;
}

export async function getUnderstockApi(): Promise<UnderstockOut> {
  const r = await api.get<UnderstockOut>("/inventory/understock");
  return r.data;
}

export async function getHealthScoresApi(): Promise<HealthScoreOut> {
  const r = await api.get<HealthScoreOut>("/inventory/health-score");
  return r.data;
}

export async function getAnomaliesApi(): Promise<AnomalyOut> {
  const r = await api.get<AnomalyOut>("/inventory/anomalies");
  return r.data;
}

export async function getSeasonalityApi(sku: string): Promise<SeasonalityOut> {
  const r = await api.get<SeasonalityOut>(`/inventory/seasonality/${encodeURIComponent(sku)}`);
  return r.data;
}

export async function getReplenishmentApi(): Promise<ReplenishmentOut> {
  const r = await api.get<ReplenishmentOut>("/inventory/replenishment");
  return r.data;
}

export async function getHeatmapApi(): Promise<HeatmapOut> {
  const r = await api.get<HeatmapOut>("/inventory/heatmap");
  return r.data;
}

export async function inventoryCopilotAskApi(body: CopilotAskIn): Promise<CopilotAskOut> {
  const r = await api.post<CopilotAskOut>("/inventory/copilot", body);
  return r.data;
}

export async function getExplanationApi(recommendationId: string): Promise<ExplanationOut> {
  const r = await api.get<ExplanationOut>(`/inventory/explain/${encodeURIComponent(recommendationId)}`);
  return r.data;
}
