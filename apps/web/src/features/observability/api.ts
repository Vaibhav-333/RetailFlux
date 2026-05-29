import { api } from "@/lib/api";
import type { AiUsageSummaryOut, AuditLogsResponse, CeleryStatsOut, ObservabilityDashboardOut } from "@/types";

export async function getObservabilityDashboardApi(): Promise<ObservabilityDashboardOut> {
  const { data } = await api.get<ObservabilityDashboardOut>("/observability/dashboard");
  return data;
}

export async function getCeleryStatsApi(): Promise<CeleryStatsOut> {
  const { data } = await api.get<CeleryStatsOut>("/observability/celery-stats");
  return data;
}

export async function getAuditLogsApi(params?: {
  page?: number;
  size?: number;
  resource?: string;
  action?: string;
}): Promise<AuditLogsResponse> {
  const { data } = await api.get<AuditLogsResponse>("/audit/logs", { params });
  return data;
}

export async function getAiUsageApi(): Promise<AiUsageSummaryOut> {
  const { data } = await api.get<AiUsageSummaryOut>("/observability/ai-usage");
  return data;
}
