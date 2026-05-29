import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw } from "lucide-react";
import { getOperationsKpisApi } from "@/features/operations/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { EmptyState } from "@/components/EmptyState";
import { OperationsSkeleton } from "@/pages/skeletons";
import { KpiCard } from "@/components/ui/KpiCard";
import { SmartChart } from "@/components/charts/SmartChart";
import { SankeyChart, warehouseStockToSankey } from "@/components/charts/Sankey";
import { useFilters } from "@/state/FilterContext";
import { DepartmentTasksTab } from "@/components/tasks/DepartmentTasksTab";
import type { LowStockSku } from "@/types";

function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

function LowStockTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: LowStockSku }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded border bg-white p-2 text-xs shadow">
      <p className="font-medium">{d.sku}</p>
      <p>Stock: {d.stock_level}</p>
      <p>Reorder at: {d.reorder_point}</p>
    </div>
  );
}

const SYNC_ID = "operations-charts";

export function OperationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") ?? "analytics";
  const { dateFrom, dateTo, compareTo, dims } = useFilters();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["operations-kpis", dateFrom, dateTo, compareTo, dims],
    queryFn: () => getOperationsKpisApi(dateFrom, dateTo, compareTo || undefined, dims || undefined),
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  async function handleRefresh() {
    setIsRefreshing(true);
    try { await invalidateAnalyticsCacheApi("operations"); await refetch(); }
    finally { setIsRefreshing(false); }
  }

  if (isLoading) return <OperationsSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        Failed to load operations data.
      </div>
    );
  }

  if (data.daily_stock_level.length === 0) {
    return <EmptyState dept="Operations" />;
  }

  const d = data.deltas;

  if (view === "tasks") {
    return (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Operations</h1>
          <button onClick={() => setSearchParams({})} className="rounded px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors">Analytics</button>
          <button className="rounded px-3 py-1 text-sm font-medium bg-primary text-primary-foreground">Tasks</button>
        </div>
        <DepartmentTasksTab department="operations" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-bold mr-4">Operations Analytics</h1>
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
          label="Total SKUs Tracked"
          value={fmtNum(data.total_skus)}
          delta={d?.total_skus}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="Total Stock Units"
          value={fmtNum(data.total_stock_units)}
          delta={d?.total_stock_units}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard
          label="SKUs Below Reorder"
          value={fmtNum(data.skus_below_reorder)}
          alert={data.skus_below_reorder > 0}
          valueVariant={data.skus_below_reorder > 0 ? "bad" : "default"}
          delta={d?.skus_below_reorder}
          deltaLabel={compareTo ? "vs prev" : undefined}
        />
        <KpiCard label="Active Warehouses" value={fmtNum(data.active_warehouses)} />
      </div>

      {/* Daily avg stock level area chart */}
      <SmartChart
        title="Avg Daily Stock Level"
        syncId={SYNC_ID}
        legendKeys={[{ key: "avg_stock_level", color: "#22c55e", label: "Avg Stock" }]}
      >
        {({ syncId, brush }) =>
          data.daily_stock_level.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No data for selected range.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={brush ? 290 : 260}>
              <AreaChart data={data.daily_stock_level} syncId={syncId}>
                <defs>
                  <linearGradient id="stockGrad" x1="0" y1="0" x2="0" y2="1">
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
                  tickFormatter={(v: number) => fmtNum(v)}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v: number) => [`${fmtNum(v)} units`, "Avg stock"]}
                  labelFormatter={(l) => `Date: ${l}`}
                />
                <Area
                  type="monotone"
                  dataKey="avg_stock_level"
                  stroke="#22c55e"
                  fill="url(#stockGrad)"
                  strokeWidth={2}
                  dot={false}
                />
                {brush && (
                  <Brush dataKey="date" height={20} stroke="#22c55e" fill="transparent" />
                )}
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </SmartChart>

      {/* Warehouse bar + Low-stock bar side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Stock by warehouse */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Stock by Warehouse</h2>
          {data.stock_by_warehouse.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No warehouse data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.stock_by_warehouse} margin={{ bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis
                  dataKey="warehouse"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  angle={-20}
                  textAnchor="end"
                />
                <YAxis
                  tickFormatter={(v: number) => fmtNum(v)}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip formatter={(v: number) => [`${fmtNum(v)} units`, "Stock"]} />
                <Bar dataKey="stock_level" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top 10 low-stock SKUs */}
        <div className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold">Top 10 Low-Stock SKUs</h2>
          {data.low_stock_skus.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No low-stock SKUs.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.low_stock_skus} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  tickFormatter={(v: number) => fmtNum(v)}
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
                <Tooltip content={<LowStockTooltip />} />
                <Bar dataKey="stock_level" radius={[0, 4, 4, 0]}>
                  {data.low_stock_skus.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.stock_level < entry.reorder_point ? "#ef4444" : "#f97316"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Sankey: stock distribution across warehouses */}
      {data.stock_by_warehouse.length > 0 && (() => {
        const { nodes, links } = warehouseStockToSankey(data.stock_by_warehouse);
        return (
          <SankeyChart
            title="Stock Flow by Warehouse"
            nodes={nodes}
            links={links}
            height={Math.min(400, Math.max(200, data.stock_by_warehouse.length * 50))}
            formatValue={(v) => `${new Intl.NumberFormat("en-US").format(v)} units`}
          />
        );
      })()}
    </div>
  );
}
