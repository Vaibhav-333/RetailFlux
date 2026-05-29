import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowUpRight, Loader2, RefreshCw, Sparkles, TrendingUp } from "lucide-react";
import { getFinanceKpisApi } from "@/features/finance/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { getPricingSuggestionsApi } from "@/features/pricing/api";
import { EmptyState } from "@/components/EmptyState";
import { FinanceSkeleton } from "@/pages/skeletons";
import { KpiCard } from "@/components/ui/KpiCard";
import { SmartChart } from "@/components/charts/SmartChart";
import { useFilters } from "@/state/FilterContext";
import { DepartmentTasksTab } from "@/components/tasks/DepartmentTasksTab";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

const SYNC_ID = "finance-charts";

const CONFIDENCE_COLOR: Record<string, string> = {
  high: "text-green-400",
  medium: "text-amber-400",
  low: "text-muted-foreground",
};

function PricingTab() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["pricing-suggestions", 1, 50],
    queryFn: () => getPricingSuggestionsApi(1, 50),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading pricing suggestions…
      </div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-violet-400" /> Pricing Suggestions
        </h2>
        <button
          onClick={() => navigate("/dashboard/finance/profit-intelligence")}
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          Profit Intelligence <ArrowUpRight className="w-3 h-3" />
        </button>
      </div>
      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No pricing suggestions — upload more sales data.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">SKU</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Current Price</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Suggested Price</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Margin Δ</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Expected Lift</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Direction</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.sku} className="border-b hover:bg-accent/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{s.sku}</td>
                  <td className="px-4 py-3 text-right">${s.current_price.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-semibold">
                    ${s.suggested_price.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right ${s.suggested_margin_pct > s.current_margin_pct ? "text-green-400" : "text-red-400"}`}>
                    {s.suggested_margin_pct > s.current_margin_pct ? "+" : ""}
                    {(s.suggested_margin_pct - s.current_margin_pct).toFixed(1)}pp
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${s.expected_lift_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {s.expected_lift_pct > 0 ? "+" : ""}{s.expected_lift_pct.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${s.direction === "increase" ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"}`}>
                      {s.direction === "increase" ? "↑ Increase" : "↓ Decrease"}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-xs ${CONFIDENCE_COLOR[s.confidence]}`}>
                    {s.confidence}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function FinancePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") ?? "analytics";
  const { dateFrom, dateTo, compareTo, dims } = useFilters();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["finance-kpis", dateFrom, dateTo, compareTo, dims],
    queryFn: () => getFinanceKpisApi(dateFrom, dateTo, compareTo || undefined, dims || undefined),
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  async function handleRefresh() {
    setIsRefreshing(true);
    try { await invalidateAnalyticsCacheApi("finance"); await refetch(); }
    finally { setIsRefreshing(false); }
  }

  if (isLoading) return <FinanceSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        Failed to load finance data.
      </div>
    );
  }

  if (data.daily_gross_profit.length === 0) {
    return <EmptyState dept="Finance" />;
  }

  const d = data.deltas;

  if (view === "tasks") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Finance</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Tasks</button>
          <button onClick={() => setSearchParams({ view: "pricing" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Pricing</button>
        </div>
        <DepartmentTasksTab department="finance" />
      </div>
    );
  }

  if (view === "pricing") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Finance</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button onClick={() => setSearchParams({ view: "tasks" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Tasks</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Pricing</button>
        </div>
        <PricingTab />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Finance Analytics</h1>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Analytics</button>
          <button onClick={() => setSearchParams({ view: "tasks" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Tasks</button>
          <button onClick={() => setSearchParams({ view: "pricing" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors flex items-center gap-1"><Sparkles className="w-3 h-3" /> Pricing</button>
        </div>
        <button
          onClick={() => { void handleRefresh(); }}
          disabled={isRefreshing}
          title="Bust Redis cache and refetch from MongoDB"
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          label="Total Revenue"
          value={fmt(data.total_revenue)}
          delta={d?.total_revenue}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Total COGS"
          value={fmt(data.total_cogs)}
          valueVariant="bad"
        />
        <KpiCard
          label="Gross Profit"
          value={fmt(data.total_gross_profit)}
          valueVariant={data.total_gross_profit >= 0 ? "ok" : "bad"}
          delta={d?.total_gross_profit}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Gross Margin"
          value={`${data.gross_margin.toFixed(1)}%`}
          subline="gross profit ÷ revenue"
          valueVariant={data.gross_margin >= 0 ? "ok" : "bad"}
          delta={d?.gross_margin}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
      </div>

      {/* Daily gross profit area chart */}
      <SmartChart
        title="Daily Gross Profit"
        syncId={SYNC_ID}
        legendKeys={[{ key: "gross_profit", color: "#22c55e", label: "Gross Profit" }]}
      >
        {({ syncId, brush }) =>
          data.daily_gross_profit.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No data for selected range.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={brush ? 290 : 260}>
              <AreaChart data={data.daily_gross_profit} syncId={syncId}>
                <defs>
                  <linearGradient id="gpGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v: number) => fmt(v)}
                  labelFormatter={(l) => `Date: ${l}`}
                />
                <Area
                  type="monotone"
                  dataKey="gross_profit"
                  stroke="#22c55e"
                  fill="url(#gpGrad)"
                  strokeWidth={2}
                  dot={false}
                  name="Gross Profit"
                />
                {brush && (
                  <Brush dataKey="date" height={20} stroke="#22c55e" fill="transparent" />
                )}
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </SmartChart>

      {/* Category bar + Monthly grouped bar */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Revenue by category — horizontal bar */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Revenue by Category</h2>
          {data.revenue_by_category.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No category data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={data.revenue_by_category}
                layout="vertical"
                margin={{ left: 16 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="category"
                  width={80}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="revenue" fill="#6366f1" radius={[0, 4, 4, 0]} name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Monthly Revenue vs COGS — grouped bar */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Monthly Revenue vs COGS</h2>
          {data.monthly_pnl.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No monthly data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.monthly_pnl} margin={{ bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  angle={-30}
                  textAnchor="end"
                />
                <YAxis
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Legend verticalAlign="top" height={28} />
                <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} name="Revenue" />
                <Bar dataKey="cogs" fill="#f43f5e" radius={[4, 4, 0, 0]} name="COGS" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
