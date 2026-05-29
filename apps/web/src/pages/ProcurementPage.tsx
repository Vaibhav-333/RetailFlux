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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw, RefreshCcw } from "lucide-react";
import { getProcurementKpisApi } from "@/features/procurement/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { EmptyState } from "@/components/EmptyState";
import { ProcurementSkeleton } from "@/pages/skeletons";
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

const SYNC_ID = "procurement-charts";

export function ProcurementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") ?? "analytics";
  const { dateFrom, dateTo, compareTo, dims } = useFilters();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["procurement-kpis", dateFrom, dateTo, compareTo, dims],
    queryFn: () => getProcurementKpisApi(dateFrom, dateTo, compareTo || undefined, dims || undefined),
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  async function handleRefresh() {
    setIsRefreshing(true);
    try { await invalidateAnalyticsCacheApi("procurement"); await refetch(); }
    finally { setIsRefreshing(false); }
  }

  if (isLoading) return <ProcurementSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        Failed to load procurement data.
      </div>
    );
  }

  if (data.daily_spend.length === 0) {
    return <EmptyState dept="Procurement" />;
  }

  const d = data.deltas;

  if (view === "tasks") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Procurement</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Tasks</button>
        </div>
        <DepartmentTasksTab department="procurement" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Procurement Analytics</h1>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Analytics</button>
          <button onClick={() => setSearchParams({ view: "tasks" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Tasks</button>
          <button onClick={() => navigate("/dashboard/procurement/auto-replenishment")} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors flex items-center gap-1"><RefreshCcw className="w-3 h-3" /> Auto-Replenishment</button>
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
          label="Total Spend"
          value={fmt(data.total_spend)}
          delta={d?.total_spend}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Units Ordered"
          value={data.total_units.toLocaleString()}
          subline="total quantity"
          delta={d?.total_units}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Unique Suppliers"
          value={data.unique_suppliers.toLocaleString()}
        />
        <KpiCard
          label="Avg Lead Days"
          value={`${data.avg_lead_days.toFixed(1)} days`}
          subline="order to delivery"
          delta={d?.avg_lead_days}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
      </div>

      {/* Daily spend area chart */}
      <SmartChart
        title="Daily Procurement Spend"
        syncId={SYNC_ID}
        legendKeys={[{ key: "spend", color: "#f59e0b", label: "Spend" }]}
      >
        {({ syncId, brush }) =>
          data.daily_spend.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No data for selected range.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={brush ? 290 : 260}>
              <AreaChart data={data.daily_spend} syncId={syncId}>
                <defs>
                  <linearGradient id="procGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
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
                  dataKey="spend"
                  stroke="#f59e0b"
                  fill="url(#procGrad)"
                  strokeWidth={2}
                  dot={false}
                  name="Spend"
                />
                {brush && (
                  <Brush dataKey="date" height={20} stroke="#f59e0b" fill="transparent" />
                )}
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </SmartChart>

      {/* Top suppliers + Top SKU costs */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Top 10 suppliers by spend — horizontal bar */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Top Suppliers by Spend</h2>
          {data.top_suppliers.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No supplier data.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={data.top_suppliers}
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
                  dataKey="supplier_id"
                  width={72}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="spend" fill="#f59e0b" radius={[0, 4, 4, 0]} name="Spend" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top 10 SKUs by avg unit cost — horizontal bar */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Top SKUs by Avg Unit Cost</h2>
          {data.top_sku_costs.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No SKU cost data.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={data.top_sku_costs}
                layout="vertical"
                margin={{ left: 16 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="sku"
                  width={88}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <Tooltip formatter={(v: number) => `$${(v as number).toFixed(2)}`} />
                <Bar dataKey="avg_unit_cost" fill="#6366f1" radius={[0, 4, 4, 0]} name="Avg Unit Cost" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
