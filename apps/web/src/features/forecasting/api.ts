import { api } from "@/lib/api";
import type { ForecastOut, SkuForecast } from "@/types";

export async function getTopSkusForecastApi(): Promise<ForecastOut> {
  const { data } = await api.get<ForecastOut>("/forecasting/top-skus");
  return data;
}

export async function getSkuForecastApi(sku: string): Promise<SkuForecast> {
  const { data } = await api.get<SkuForecast>(
    `/forecasting/sku?sku=${encodeURIComponent(sku)}`,
  );
  return data;
}
