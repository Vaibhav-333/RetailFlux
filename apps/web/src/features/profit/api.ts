import { api } from "@/lib/api";

export interface ProfitForecastPoint {
  date: string;
  revenue: number;
  cogs: number;
  gross_profit: number;
  gp_lower?: number;
  gp_upper?: number;
}

export interface ProfitForecastOut {
  generated_at: string;
  historical: ProfitForecastPoint[];
  forecast: ProfitForecastPoint[];
  summary: {
    forecast_90d_revenue: number;
    forecast_90d_cogs: number;
    forecast_90d_gross_profit: number;
    forecast_gross_margin_pct: number;
    confidence: "high" | "medium" | "low";
    ci_width_pct: number;
  };
}

export interface WaterfallEntry {
  label: string;
  value: number;
  type: "base" | "delta" | "total";
}

export interface ProfitAttributionOut {
  period: string;
  compare_period: string;
  current: { total_gp: number; total_revenue: number; total_cogs: number };
  previous: { total_gp: number; total_revenue: number; total_cogs: number };
  total_delta: number;
  waterfall: WaterfallEntry[];
}

export interface ProfitLever {
  id: string;
  title: string;
  description: string;
  category: string;
  estimated_gp_lift: number;
  effort: "low" | "medium" | "high";
  confidence: "high" | "medium" | "low";
  action: string;
  skus: string[];
}

export interface ProfitLeversOut {
  generated_at: string;
  baseline_gp_28d: number;
  total_potential_lift: number;
  levers: ProfitLever[];
}

export async function getProfitForecastApi(): Promise<ProfitForecastOut> {
  const { data } = await api.get<ProfitForecastOut>("/profit/forecast");
  return data;
}

export async function getProfitAttributionApi(
  period = "28d",
  comparePeriod = "prev_28d",
): Promise<ProfitAttributionOut> {
  const { data } = await api.get<ProfitAttributionOut>("/profit/attribution", {
    params: { period, compare_period: comparePeriod },
  });
  return data;
}

export async function getProfitLeversApi(): Promise<ProfitLeversOut> {
  const { data } = await api.get<ProfitLeversOut>("/profit/levers");
  return data;
}
