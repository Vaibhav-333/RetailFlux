import { api } from "@/lib/api";

export interface FeatureFlag {
  id: string;
  company_id: string | null;
  key: string;
  enabled: boolean;
  payload: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeatureFlagsResponse {
  flags: FeatureFlag[];
  total: number;
}

export async function listFeatureFlagsApi(): Promise<FeatureFlagsResponse> {
  const { data } = await api.get<FeatureFlagsResponse>("/feature-flags");
  return data;
}

export async function checkFeatureFlagApi(key: string): Promise<boolean> {
  const { data } = await api.get<{ key: string; enabled: boolean }>(
    `/feature-flags/${key}/check`
  );
  return data.enabled;
}

export async function updateFeatureFlagApi(
  key: string,
  enabled: boolean,
  payload?: Record<string, unknown>
): Promise<{ key: string; enabled: boolean }> {
  const { data } = await api.patch<{ key: string; enabled: boolean }>(
    `/feature-flags/${key}`,
    { enabled, payload }
  );
  return data;
}
