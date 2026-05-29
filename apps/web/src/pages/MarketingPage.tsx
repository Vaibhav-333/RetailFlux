import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DepartmentTasksTab } from "@/components/tasks/DepartmentTasksTab";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw } from "lucide-react";
import { getMarketingKpisApi } from "@/features/marketing/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { EmptyState } from "@/components/EmptyState";
import { MarketingSkeleton } from "@/pages/skeletons";
import { KpiCard } from "@/components/ui/KpiCard";
import { SmartChart } from "@/components/charts/SmartChart";
import { useFilters } from "@/state/FilterContext";

const PIE_COLORS = [
  "#8b5cf6", "#6366f1", "#ec4899", "#f43f5e",
  "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#3b82f6", "#a855f7",
];

const SYNC_ID = "marketing-charts";

function fmtCurrency(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

export function MarketingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") ?? "analytics";
  const { dateFrom, dateTo, compareTo, dims } = useFilters();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["marketing-kpis", dateFrom, dateTo, compareTo, dims],
    queryFn: () => getMarketingKpisApi(dateFrom, dateTo, compareTo || undefined, dims || undefined),
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  async function handleRefresh() {
    setIsRefreshing(true);
    try { await invalidateAnalyticsCacheApi("marketing"); await refetch(); }
    finally { setIsRefreshing(false); }
  }

  if (isLoading) return <MarketingSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        Failed to load marketing data.
      </div>
    );
  }

  if (data.daily_spend.length === 0) {
    return <EmptyState dept="Marketing" />;
  }

  const d = data.deltas;

  if (view === "tasks") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Marketing</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Tasks</button>
        </div>
        <DepartmentTasksTab department="marketing" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Marketing Analytics</h1>
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
          label="Total Spend"
          value={fmtCurrency(data.total_spend)}
          subline={`${fmtNum(data.total_conversions)} conversions`}
          delta={d?.total_spend}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="ROAS"
          value={`${data.roas.toFixed(2)}×`}
          subline="revenue ÷ spend"
          delta={d?.roas}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="CAC"
          value={fmtCurrency(data.cac)}
          subline="cost per conversion"
          delta={d?.cac}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="CTR"
          value={`${data.ctr.toFixed(2)}%`}
          subline={`${fmtNum(data.total_impressions)} impressions`}
          delta={d?.ctr}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
      </div>

      {/* Daily spend area chart */}
      <SmartChart
        title="Daily Spend Trend"
        syncId={SYNC_ID}
        legendKeys={[{ key: "spend", color: "#8b5cf6", label: "Spend" }]}
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
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
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
                  formatter={(v: number) => fmtCurrency(v)}
                  labelFormatter={(l) => `Date: ${l}`}
                />
                <Area
                  type="monotone"
                  dataKey="spend"
                  stroke="#8b5cf6"
                  fill="url(#spendGrad)"
                  strokeWidth={2}
                  dot={false}
                />
                {brush && (
                  <Brush dataKey="date" height={20} stroke="#8b5cf6" fill="transparent" />
                )}
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </SmartChart>

      {/* Bar + Pie side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Top 10 campaigns by conversions */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Top 10 Campaigns by Conversions</h2>
          {data.top_campaigns.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No campaign data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.top_campaigns} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="campaign_id"
                  width={72}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <Tooltip formatter={(v: number) => `${fmtNum(v)} conversions`} />
                <Bar dataKey="conversions" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Spend by campaign pie chart */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Spend by Campaign</h2>
          {data.spend_by_campaign.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No spend data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={data.spend_by_campaign}
                  dataKey="spend"
                  nameKey="campaign_id"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({
                    campaign_id,
                    percent,
                  }: {
                    campaign_id: string;
                    percent: number;
                  }) => `${campaign_id} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {data.spend_by_campaign.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
