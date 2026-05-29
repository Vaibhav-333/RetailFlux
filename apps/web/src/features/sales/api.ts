import { api } from "@/lib/api";
import type { SalesKpisOut } from "@/types";

export async function getSalesKpisApi(
  dateFrom?: string,
  dateTo?: string,
  compareTo?: string,
  dims?: string,
): Promise<SalesKpisOut> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (compareTo) params.set("compare_to", compareTo);
  if (dims) params.set("dims", dims);
  const { data } = await api.get<SalesKpisOut>(`/analytics/sales?${params}`);
  return data;
}
