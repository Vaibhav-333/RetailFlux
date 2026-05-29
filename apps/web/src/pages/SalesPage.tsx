import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { DepartmentTasksTab } from "@/components/tasks/DepartmentTasksTab";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw } from "lucide-react";
import { getSalesKpisApi } from "@/features/sales/api";
import { getTopSkusForecastApi } from "@/features/forecasting/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { EmptyState } from "@/components/EmptyState";
import { SalesSkeleton } from "@/pages/skeletons";
import { KpiCard } from "@/components/ui/KpiCard";
import { SmartChart } from "@/components/charts/SmartChart";
import { TreemapChart } from "@/components/charts/Treemap";
import { useFilters } from "@/state/FilterContext";

const REGION_COLORS = [
  "#6366f1", "#8b5cf6", "#a855f7", "#ec4899",
  "#f43f5e", "#f97316", "#eab308", "#22c55e",
  "#14b8a6", "#3b82f6",
];

const SYNC_ID = "sales-charts";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export function SalesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") ?? "analytics";
  const { dateFrom, dateTo, compareTo, dims } = useFilters();
  const [selectedSkuIdx, setSelectedSkuIdx] = useState(0);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["sales-kpis", dateFrom, dateTo, compareTo, dims],
    queryFn: () => getSalesKpisApi(dateFrom, dateTo, compareTo || undefined, dims || undefined),
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  async function handleRefresh() {
    setIsRefreshing(true);
    try { await invalidateAnalyticsCacheApi("sales"); await refetch(); }
    finally { setIsRefreshing(false); }
  }

  const { data: forecastData, isLoading: forecastLoading } = useQuery({
    queryKey: ["top-skus-forecast"],
    queryFn: getTopSkusForecastApi,
  });

  const selectedForecast = forecastData?.forecasts[selectedSkuIdx] ?? null;

  const combinedChartData = useMemo(() => {
    const hist = (data?.daily_revenue ?? []).map((p) => ({
      date: p.date,
      revenue: p.revenue,
      yhat: undefined as number | undefined,
      lower: undefined as number | undefined,
      band: undefined as number | undefined,
    }));

    const fcPoints = selectedForecast?.points ?? [];
    const fc = fcPoints.map((p) => ({
      date: p.ds,
      revenue: undefined as number | undefined,
      yhat: p.yhat < 0 ? 0 : p.yhat,
      lower: p.yhat_lower < 0 ? 0 : p.yhat_lower,
      band: Math.max(0, p.yhat_upper - p.yhat_lower),
    }));

    return [...hist, ...fc];
  }, [data, selectedForecast]);

  if (isLoading) return <SalesSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        Failed to load sales data.
      </div>
    );
  }

  if (data.daily_revenue.length === 0) {
    return <EmptyState dept="Sales" />;
  }

  const d = data.deltas;

  if (view === "tasks") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Sales</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Tasks</button>
        </div>
        <DepartmentTasksTab department="sales" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Sales Analytics</h1>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Analytics</button>
          <button onClick={() => setSearchParams({ view: "tasks" })} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Tasks</button>
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
          label="Total Units Sold"
          value={data.total_units.toLocaleString()}
          delta={d?.total_units}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Avg Order Value"
          value={fmt(data.aov)}
          delta={d?.aov}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard label="Top SKU" value={data.top_sku ?? "—"} />
      </div>

      {/* Daily revenue area chart */}
      <SmartChart
        title="Daily Revenue Trend"
        syncId={SYNC_ID}
        legendKeys={[{ key: "revenue", color: "#6366f1", label: "Revenue" }]}
      >
        {({ syncId, brush }) =>
          data.daily_revenue.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No data for selected range.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={brush ? 290 : 260}>
              <AreaChart data={data.daily_revenue} syncId={syncId}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
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
                <Tooltip formatter={(v: number) => fmt(v)} labelFormatter={(l) => `Date: ${l}`} />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#6366f1"
                  fill="url(#revGrad)"
                  strokeWidth={2}
                  dot={false}
                />
                {brush && (
                  <Brush dataKey="date" height={20} stroke="#6366f1" fill="transparent" />
                )}
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </SmartChart>

      {/* Bar + Pie side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Top 10 SKUs bar chart */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Top 10 SKUs by Revenue</h2>
          {data.top_skus.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No SKU data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.top_skus} layout="vertical" margin={{ left: 16 }}>
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
                  dataKey="sku"
                  width={88}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="revenue" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Revenue by region pie chart */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Revenue by Region</h2>
          {data.revenue_by_region.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No regional data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={data.revenue_by_region}
                  dataKey="revenue"
                  nameKey="region"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ region, percent }: { region: string; percent: number }) =>
                    `${region} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {data.revenue_by_region.map((_, i) => (
                    <Cell key={i} fill={REGION_COLORS[i % REGION_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Revenue breakdown treemap */}
      {data.top_skus.length > 0 && (
        <TreemapChart
          title="Revenue Breakdown by SKU"
          data={data.top_skus.map((s) => ({ name: s.sku, value: s.revenue }))}
          height={260}
          formatValue={(v) =>
            new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
              maximumFractionDigits: 0,
            }).format(v)
          }
        />
      )}

      {/* ── 30-Day Demand Forecast ─────────────────────────────────────────── */}
      <div className="rounded-lg border bg-card p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold">30-Day Demand Forecast</h2>
          {forecastData && forecastData.forecasts.length > 0 && (
            <select
              value={selectedSkuIdx}
              onChange={(e) => setSelectedSkuIdx(Number(e.target.value))}
              className="rounded border px-2 py-1 text-sm"
            >
              {forecastData.forecasts.map((f, i) => (
                <option key={f.sku} value={i}>
                  {f.sku}
                </option>
              ))}
            </select>
          )}
        </div>

        {forecastLoading ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Fitting forecast model…
          </p>
        ) : !selectedForecast || selectedForecast.points.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Insufficient historical data for forecast.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={combinedChartData}>
              <defs>
                <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
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
                formatter={(v: unknown, name: string) => {
                  if (typeof v !== "number") return [null, name];
                  const labels: Record<string, string> = {
                    revenue: "Historical",
                    yhat: "Forecast",
                    lower: "CI lower",
                    band: "CI width",
                  };
                  return [fmt(v), labels[name] ?? name];
                }}
                labelFormatter={(l) => `Date: ${l}`}
              />
              <Legend
                formatter={(value) => {
                  const map: Record<string, string> = {
                    revenue: "Historical",
                    yhat: "Forecast (yhat)",
                    lower: "CI lower",
                    band: "CI band",
                  };
                  return map[value as string] ?? value;
                }}
              />

              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#6366f1"
                fill="url(#histGrad)"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="lower"
                stackId="ci"
                stroke="none"
                fill="transparent"
                dot={false}
                connectNulls={false}
                legendType="none"
              />
              <Area
                type="monotone"
                dataKey="band"
                stackId="ci"
                stroke="none"
                fill="#f97316"
                fillOpacity={0.18}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="yhat"
                stroke="#f97316"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={false}
                connectNulls={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
