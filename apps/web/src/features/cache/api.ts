import { api } from "@/lib/api";
import type { CacheHealth, CacheInvalidateResult, CacheStatsOut, CacheWarmResult } from "@/types";

export async function getCacheStatsApi(): Promise<CacheStatsOut> {
  const res = await api.get<CacheStatsOut>("/observability/cache-stats");
  return res.data;
}

export async function invalidateAnalyticsCacheApi(
  dept?: string,
  warm = false
): Promise<CacheInvalidateResult> {
  const params: Record<string, string | boolean> = {};
  if (dept) params.dept = dept;
  if (warm) params.warm = true;
  const res = await api.delete<CacheInvalidateResult>("/cache/analytics", { params });
  return res.data;
}

export async function warmCacheApi(): Promise<CacheWarmResult> {
  const res = await api.post<CacheWarmResult>("/cache/warm");
  return res.data;
}

export async function getCacheHealthApi(): Promise<CacheHealth> {
  const res = await api.get<CacheHealth>("/cache/health");
  return res.data;
}
