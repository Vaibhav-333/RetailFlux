import { api } from "@/lib/api";
import type { ProcurementKpisOut } from "@/types";

export async function getProcurementKpisApi(
  dateFrom?: string,
  dateTo?: string,
  compareTo?: string,
  dims?: string,
): Promise<ProcurementKpisOut> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (compareTo) params.set("compare_to", compareTo);
  if (dims) params.set("dims", dims);
  const { data } = await api.get<ProcurementKpisOut>(`/analytics/procurement?${params}`);
  return data;
}
