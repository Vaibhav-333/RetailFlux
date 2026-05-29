import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  FlaskConical,
  Plus,
  RefreshCw,
  Share2,
  Trash2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  createScenarioApi,
  deleteScenarioApi,
  quickSimulateApi,
  runScenarioApi,
  shareScenarioApi,
  type Scenario,
  type ScenarioAssumptions,
  type ScenarioBaseline,
  type SimulationResults,
} from "@/features/scenarios/api";
import { useQuery as useListQuery } from "@tanstack/react-query";
import { listScenariosApi } from "@/features/scenarios/api";
import { ScenariosSkeleton } from "@/pages/skeletons";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function pct(n: number, showSign = true) {
  const sign = showSign && n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

const DEFAULT_ASSUMPTIONS: ScenarioAssumptions = {
  demand_shock_pct: 0,
  price_change_pct: 0,
  cogs_change_pct: 0,
  marketing_spend_change_pct: 0,
  lead_time_change_days: 0,
  horizon_days: 90,
};

const DEFAULT_BASELINE: ScenarioBaseline = {
  daily_revenue: 10000,
  daily_cogs: 6000,
  daily_units: 200,
  avg_price: 50,
  avg_unit_cost: 30,
  inventory_value: 500000,
};

// ── Assumption slider row ─────────────────────────────────────────────────────

function SliderRow({
  label,
  field,
  min,
  max,
  step,
  format,
  assumptions,
  onChange,
}: {
  label: string;
  field: keyof ScenarioAssumptions;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  assumptions: ScenarioAssumptions;
  onChange: (field: keyof ScenarioAssumptions, value: number) => void;
}) {
  const value = (assumptions[field] as number) ?? 0;
  const isPositive = value > 0;
  const isNegative = value < 0;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span
          className={`text-sm font-mono font-semibold ${
            isPositive ? "text-green-400" : isNegative ? "text-red-400" : "text-foreground"
          }`}
        >
          {format(value)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(field, parseFloat(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none bg-border cursor-pointer accent-brand-500"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

// ── Delta chip ────────────────────────────────────────────────────────────────

function DeltaChip({ value, suffix = "%" }: { value: number; suffix?: string }) {
  const isUp = value > 0;
  const isDown = value < 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded ${
        isUp
          ? "bg-green-900/40 text-green-400"
          : isDown
          ? "bg-red-900/40 text-red-400"
          : "bg-muted text-muted-foreground"
      }`}
    >
      {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : null}
      {value > 0 ? "+" : ""}{value.toFixed(1)}{suffix}
    </span>
  );
}

// ── Scenario list item ────────────────────────────────────────────────────────

function ScenarioListItem({
  scenario,
  isActive,
  onSelect,
  onDelete,
}: {
  scenario: Scenario;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`flex items-center justify-between px-3 py-2.5 rounded-md cursor-pointer transition-colors ${
        isActive
          ? "bg-brand-900/30 border border-brand-700/40 text-brand-300"
          : "hover:bg-accent text-muted-foreground hover:text-foreground"
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <FlaskConical className="w-3.5 h-3.5 shrink-0 text-violet-400" />
        <span className="text-sm font-medium truncate">{scenario.name}</span>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="ml-2 p-0.5 rounded hover:bg-red-900/30 hover:text-red-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
        title="Delete scenario"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ScenariosPage() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [assumptions, setAssumptions] = useState<ScenarioAssumptions>(DEFAULT_ASSUMPTIONS);
  const [results, setResults] = useState<SimulationResults | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState("");

  const { data: list, isLoading } = useListQuery({
    queryKey: ["scenarios"],
    queryFn: () => listScenariosApi(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createScenarioApi({
        name: newName || "New Scenario",
        assumptions,
        baseline_snapshot: DEFAULT_BASELINE,
      }),
    onSuccess: (sc) => {
      qc.invalidateQueries({ queryKey: ["scenarios"] });
      setActiveId(sc.id);
      setShowNewForm(false);
      setNewName("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteScenarioApi(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenarios"] });
      if (activeId === deleteMutation.variables) setActiveId(null);
    },
  });

  const shareMutation = useMutation({
    mutationFn: (id: string) => shareScenarioApi(id),
    onSuccess: (data) => alert(`Share link copied! Token: ${data.share_token}`),
  });

  function handleAssumptionChange(field: keyof ScenarioAssumptions, value: number) {
    setAssumptions((prev) => ({ ...prev, [field]: value }));
  }

  async function handleRunSimulation() {
    setIsRunning(true);
    try {
      const r = await quickSimulateApi(DEFAULT_BASELINE, assumptions);
      setResults(r);
    } finally {
      setIsRunning(false);
    }
  }

  async function handleSaveAndRun() {
    if (!activeId) return;
    setIsRunning(true);
    try {
      const run = await runScenarioApi(activeId, assumptions);
      setResults(run.results);
    } finally {
      setIsRunning(false);
    }
  }

  if (isLoading) return <ScenariosSkeleton />;

  const activeScenario = list?.items.find((s) => s.id === activeId);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Left sidebar — scenario list */}
      <aside className="w-56 shrink-0 border-r border-border flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold">Scenarios</h2>
          <button
            onClick={() => setShowNewForm(true)}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="New scenario"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {showNewForm && (
          <div className="px-3 py-2 border-b border-border">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") createMutation.mutate();
                if (e.key === "Escape") setShowNewForm(false);
              }}
              placeholder="Scenario name…"
              className="w-full text-sm bg-muted/50 rounded px-2 py-1 outline-none border border-border focus:border-brand-500"
            />
            <div className="flex gap-1 mt-1.5">
              <button
                onClick={() => createMutation.mutate()}
                className="flex-1 text-xs rounded bg-brand-600 hover:bg-brand-500 text-white py-1 transition-colors"
              >
                Create
              </button>
              <button
                onClick={() => setShowNewForm(false)}
                className="flex-1 text-xs rounded bg-muted hover:bg-accent py-1 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          {(list?.items ?? []).map((sc) => (
            <div key={sc.id} className="group">
              <ScenarioListItem
                scenario={sc}
                isActive={sc.id === activeId}
                onSelect={() => {
                  setActiveId(sc.id);
                  setAssumptions(sc.assumptions || DEFAULT_ASSUMPTIONS);
                  setResults(null);
                }}
                onDelete={() => deleteMutation.mutate(sc.id)}
              />
            </div>
          ))}
          {!list?.items.length && (
            <p className="text-xs text-muted-foreground px-2 py-4 text-center">
              No scenarios yet.
              <br />
              Click + to create one.
            </p>
          )}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6 max-w-6xl">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold">
                {activeScenario ? activeScenario.name : "Scenario Planner"}
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                Adjust assumptions and simulate the impact on revenue, margin, and inventory.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {activeId && (
                <button
                  onClick={() => shareMutation.mutate(activeId)}
                  className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors"
                >
                  <Share2 className="w-3.5 h-3.5" />
                  Share
                </button>
              )}
              <button
                onClick={activeId ? handleSaveAndRun : handleRunSimulation}
                disabled={isRunning}
                className="inline-flex items-center gap-1.5 rounded bg-brand-600 hover:bg-brand-500 text-white px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? "animate-spin" : ""}`} />
                {isRunning ? "Simulating…" : activeId ? "Save & Run" : "Run Simulation"}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Assumption panel */}
            <div className="rounded-lg border bg-card p-5 shadow-sm space-y-5">
              <h2 className="text-sm font-semibold text-foreground">Assumptions</h2>

              <SliderRow
                label="Demand shock"
                field="demand_shock_pct"
                min={-0.5}
                max={0.5}
                step={0.01}
                format={(v) => pct(v * 100)}
                assumptions={assumptions}
                onChange={handleAssumptionChange}
              />
              <SliderRow
                label="Price change"
                field="price_change_pct"
                min={-0.3}
                max={0.3}
                step={0.01}
                format={(v) => pct(v * 100)}
                assumptions={assumptions}
                onChange={handleAssumptionChange}
              />
              <SliderRow
                label="COGS change"
                field="cogs_change_pct"
                min={-0.3}
                max={0.3}
                step={0.01}
                format={(v) => pct(v * 100)}
                assumptions={assumptions}
                onChange={handleAssumptionChange}
              />
              <SliderRow
                label="Marketing spend"
                field="marketing_spend_change_pct"
                min={-0.5}
                max={1.0}
                step={0.05}
                format={(v) => pct(v * 100)}
                assumptions={assumptions}
                onChange={handleAssumptionChange}
              />

              {/* Horizon selector */}
              <div className="flex flex-col gap-1.5">
                <span className="text-sm text-muted-foreground">Horizon</span>
                <div className="flex gap-1.5">
                  {[30, 60, 90].map((d) => (
                    <button
                      key={d}
                      onClick={() => setAssumptions((prev) => ({ ...prev, horizon_days: d }))}
                      className={`flex-1 rounded text-xs py-1 font-medium transition-colors ${
                        assumptions.horizon_days === d
                          ? "bg-brand-600 text-white"
                          : "bg-muted hover:bg-accent text-muted-foreground"
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={activeId ? handleSaveAndRun : handleRunSimulation}
                disabled={isRunning}
                className="w-full rounded bg-brand-600 hover:bg-brand-500 text-white py-2 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isRunning ? "Running…" : "Run Simulation"}
              </button>
            </div>

            {/* Results panel */}
            <div className="lg:col-span-2 space-y-4">
              {!results ? (
                <div className="flex h-64 items-center justify-center rounded-lg border bg-card text-muted-foreground">
                  <div className="text-center space-y-2">
                    <FlaskConical className="w-10 h-10 mx-auto text-muted-foreground/40" />
                    <p className="text-sm">Adjust assumptions and click <strong>Run Simulation</strong></p>
                  </div>
                </div>
              ) : (
                <>
                  {/* KPI comparison strip */}
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {(
                      [
                        { label: "Revenue", base: results.baseline_totals.revenue, scen: results.scenario_totals.revenue, delta: results.deltas.revenue_pct, format: fmt },
                        { label: "Gross Profit", base: results.baseline_totals.gross_profit, scen: results.scenario_totals.gross_profit, delta: results.deltas.gross_profit_pct, format: fmt },
                        { label: "Gross Margin", base: results.baseline_totals.gross_margin_pct, scen: results.scenario_totals.gross_margin_pct, delta: results.deltas.gross_margin_pp, format: (v: number) => `${v.toFixed(1)}%`, deltaSuffix: "pp" },
                        { label: "Units Sold", base: results.baseline_totals.units_sold, scen: results.scenario_totals.units_sold, delta: results.deltas.units_sold_pct, format: (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 }) },
                      ]
                    ).map(({ label, base, scen, delta, format, deltaSuffix }) => (
                      <div key={label} className="rounded-lg border bg-card p-3 shadow-sm">
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className="text-lg font-bold mt-0.5">{(format as (v: number) => string)(scen as number)}</p>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="text-xs text-muted-foreground line-through">
                            {(format as (v: number) => string)(base as number)}
                          </span>
                          <DeltaChip value={delta as number} suffix={deltaSuffix ?? "%"} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Revenue overlay chart */}
                  <div className="rounded-lg border bg-card p-5 shadow-sm">
                    <h3 className="text-sm font-semibold mb-4">Revenue: Baseline vs Scenario</h3>
                    <ResponsiveContainer width="100%" height={220}>
                      <ComposedChart data={results.daily_series}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10 }}
                          tickLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                          tick={{ fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip
                          formatter={(v: number, name: string) => [fmt(v), name]}
                          labelFormatter={(l) => `Date: ${l}`}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="baseline_revenue"
                          fill="#6366f1"
                          stroke="#6366f1"
                          fillOpacity={0.08}
                          strokeWidth={1.5}
                          strokeDasharray="4 2"
                          name="Baseline Revenue"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="scenario_revenue"
                          stroke="#a78bfa"
                          strokeWidth={2}
                          name="Scenario Revenue"
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>

                  {/* GP overlay chart */}
                  <div className="rounded-lg border bg-card p-5 shadow-sm">
                    <h3 className="text-sm font-semibold mb-4">Gross Profit: Baseline vs Scenario</h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <ComposedChart data={results.daily_series}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10 }}
                          tickLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                          tick={{ fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip
                          formatter={(v: number, name: string) => [fmt(v), name]}
                          labelFormatter={(l) => `Date: ${l}`}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="baseline_gp"
                          fill="#22c55e"
                          stroke="#22c55e"
                          fillOpacity={0.08}
                          strokeWidth={1.5}
                          strokeDasharray="4 2"
                          name="Baseline GP"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="scenario_gp"
                          stroke="#86efac"
                          strokeWidth={2}
                          name="Scenario GP"
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Key drivers */}
                  <div className="rounded-lg border bg-card p-5 shadow-sm">
                    <h3 className="text-sm font-semibold mb-4">Key Drivers (impact on GP)</h3>
                    <div className="space-y-2">
                      {results.key_drivers.map((d) => {
                        const isPos = d.impact >= 0;
                        return (
                          <div key={d.name} className="flex items-center gap-3">
                            <span className="w-36 text-xs text-muted-foreground shrink-0">{d.name}</span>
                            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className={`h-2 rounded-full ${isPos ? "bg-green-500" : "bg-red-500"}`}
                                style={{ width: `${Math.min(100, Math.abs(d.impact_pct) * 2)}%` }}
                              />
                            </div>
                            <span
                              className={`text-xs font-mono w-16 text-right ${isPos ? "text-green-400" : "text-red-400"}`}
                            >
                              {isPos ? "+" : ""}{fmt(d.impact)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Inventory roll-forward */}
                  <div className="rounded-lg border bg-card p-4 shadow-sm">
                    <h3 className="text-sm font-semibold mb-3">Inventory Roll-Forward</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Baseline End Value</p>
                        <p className="text-lg font-bold">{fmt(results.inventory_roll_forward.baseline_end_value)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Scenario End Value</p>
                        <p className="text-lg font-bold">{fmt(results.inventory_roll_forward.scenario_end_value)}</p>
                        <DeltaChip
                          value={
                            results.inventory_roll_forward.baseline_end_value > 0
                              ? ((results.inventory_roll_forward.scenario_end_value /
                                  results.inventory_roll_forward.baseline_end_value) -
                                  1) *
                                100
                              : 0
                          }
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
