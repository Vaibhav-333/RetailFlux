import { api } from "@/lib/api";
import type { AnomalyPoint, InsightsOut } from "@/types";

export async function getInsightsApi(): Promise<InsightsOut> {
  const { data } = await api.get<InsightsOut>("/insights/summary");
  return data;
}

export async function getAnomaliesApi(): Promise<AnomalyPoint[]> {
  const { data } = await api.get<AnomalyPoint[]>("/insights/anomalies");
  return data;
}
