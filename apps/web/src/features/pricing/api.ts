import { api } from "@/lib/api";

export interface PricingSuggestion {
  sku: string;
  current_price: number;
  suggested_price: number;
  unit_cost: number;
  current_margin_pct: number;
  suggested_margin_pct: number;
  expected_lift_pct: number;
  direction: "increase" | "decrease";
  reason: string;
  confidence: "high" | "medium" | "low";
  elasticity: number;
  r_squared: number;
  avg_daily_qty: number;
  generated_at?: string;
}

export interface PricingSuggestionsOut {
  items: PricingSuggestion[];
  total: number;
  page: number;
  page_size: number;
}

export interface PricingSummaryOut {
  total_skus: number;
  increase_count: number;
  decrease_count: number;
  avg_expected_lift_pct: number;
  high_confidence_count: number;
}

export async function getPricingSuggestionsApi(
  page = 1,
  pageSize = 20,
  direction?: "increase" | "decrease",
  minLift?: number,
): Promise<PricingSuggestionsOut> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (direction) params.direction = direction;
  if (minLift !== undefined) params.min_lift = minLift;
  const { data } = await api.get<PricingSuggestionsOut>("/pricing/suggestions", { params });
  return data;
}

export async function getPricingSummaryApi(): Promise<PricingSummaryOut> {
  const { data } = await api.get<PricingSummaryOut>("/pricing/summary");
  return data;
}

export async function refreshPricingSuggestionsApi(): Promise<{ refreshed: number; status: string }> {
  const { data } = await api.post<{ refreshed: number; status: string }>("/pricing/refresh");
  return data;
}
