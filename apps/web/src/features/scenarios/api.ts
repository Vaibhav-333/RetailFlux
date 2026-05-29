import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ScenarioAssumptions {
  demand_shock_pct?: number;       // -0.99 to +2.0
  price_change_pct?: number;       // -0.5  to +1.0
  cogs_change_pct?: number;        // -0.5  to +1.0
  marketing_spend_change_pct?: number; // -1.0  to +3.0
  lead_time_change_days?: number;  // integer days
  horizon_days?: number;           // 7–365
}

export interface ScenarioBaseline {
  daily_revenue?: number;
  daily_cogs?: number;
  daily_units?: number;
  avg_price?: number;
  avg_unit_cost?: number;
  marketing_spend_daily?: number;
  inventory_value?: number;
}

export interface Scenario {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  created_by: string;
  assumptions: ScenarioAssumptions;
  baseline_snapshot: ScenarioBaseline | null;
  is_shared: boolean;
  share_token: string | null;
  created_at: string;
  updated_at: string;
  runs?: ScenarioRun[];
}

export interface DailyDataPoint {
  date: string;
  baseline_revenue: number;
  baseline_gp: number;
  scenario_revenue: number;
  scenario_gp: number;
}

export interface KeyDriver {
  name: string;
  impact: number;
  impact_pct: number;
}

export interface SimulationTotals {
  revenue: number;
  cogs: number;
  gross_profit: number;
  gross_margin_pct: number;
  units_sold: number;
}

export interface SimulationDeltas {
  revenue_pct: number;
  gross_profit_pct: number;
  gross_margin_pp: number;
  units_sold_pct: number;
}

export interface SimulationResults {
  assumptions: ScenarioAssumptions;
  baseline_totals: SimulationTotals;
  scenario_totals: SimulationTotals;
  deltas: SimulationDeltas;
  daily_series: DailyDataPoint[];
  key_drivers: KeyDriver[];
  inventory_roll_forward: {
    baseline_end_value: number;
    scenario_end_value: number;
  };
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  run_by: string;
  assumptions_snapshot: ScenarioAssumptions;
  results: SimulationResults;
  run_at: string;
}

export interface ScenarioListOut {
  items: Scenario[];
  total: number;
  page: number;
  page_size: number;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listScenariosApi(page = 1, pageSize = 20): Promise<ScenarioListOut> {
  const r = await api.get<ScenarioListOut>("/scenarios", { params: { page, page_size: pageSize } });
  return r.data;
}

export async function createScenarioApi(payload: {
  name: string;
  description?: string;
  assumptions?: ScenarioAssumptions;
  baseline_snapshot?: ScenarioBaseline;
}): Promise<Scenario> {
  const r = await api.post<Scenario>("/scenarios", payload);
  return r.data;
}

export async function getScenarioApi(scenarioId: string): Promise<Scenario> {
  const r = await api.get<Scenario>(`/scenarios/${scenarioId}`);
  return r.data;
}

export async function updateScenarioApi(
  scenarioId: string,
  payload: Partial<{
    name: string;
    description: string;
    assumptions: ScenarioAssumptions;
    baseline_snapshot: ScenarioBaseline;
  }>
): Promise<Scenario> {
  const r = await api.put<Scenario>(`/scenarios/${scenarioId}`, payload);
  return r.data;
}

export async function deleteScenarioApi(scenarioId: string): Promise<void> {
  await api.delete(`/scenarios/${scenarioId}`);
}

export async function runScenarioApi(
  scenarioId: string,
  assumptions?: ScenarioAssumptions
): Promise<ScenarioRun> {
  const r = await api.post<ScenarioRun>(`/scenarios/${scenarioId}/run`, { assumptions });
  return r.data;
}

export async function quickSimulateApi(
  baseline: ScenarioBaseline,
  assumptions: ScenarioAssumptions
): Promise<SimulationResults> {
  const r = await api.post<SimulationResults>("/scenarios/simulate", { baseline, assumptions });
  return r.data;
}

export async function shareScenarioApi(scenarioId: string): Promise<{ share_token: string; share_url: string }> {
  const r = await api.post(`/scenarios/${scenarioId}/share`);
  return r.data;
}
