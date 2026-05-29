import { api } from "@/lib/api";
import type { DashboardSummaryOut } from "@/types";

export async function getDashboardSummaryApi(): Promise<DashboardSummaryOut> {
  const { data } = await api.get<DashboardSummaryOut>("/analytics/summary");
  return data;
}
