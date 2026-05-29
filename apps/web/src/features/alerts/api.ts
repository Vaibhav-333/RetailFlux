import { api } from "@/lib/api";
import type { AlertPrefs, AlertCheckResult } from "@/types";

export async function getAlertPrefsApi(): Promise<AlertPrefs> {
  const { data } = await api.get<AlertPrefs>("/alerts/preferences");
  return data;
}

export async function updateAlertPrefsApi(
  prefs: Partial<AlertPrefs>,
): Promise<AlertPrefs> {
  const { data } = await api.patch<AlertPrefs>("/alerts/preferences", prefs);
  return data;
}

export async function checkAlertsApi(): Promise<AlertCheckResult> {
  const { data } = await api.post<AlertCheckResult>("/alerts/check");
  return data;
}
