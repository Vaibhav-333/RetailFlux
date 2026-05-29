import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  Archive,
  CheckCircle,
  DollarSign,
  Layers,
  PackageX,
  ShoppingCart,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  acceptReorderApi,
  getAbcXyzMatrixApi,
  getAgingApi,
  getDeadStockApi,
  getInventoryOverviewApi,
  getOverstockApi,
  getReorderQueueApi,
  getSkuListApi,
  getUnderstockApi,
  getValuationApi,
} from "@/features/inventory/api";
import { KpiCard } from "@/components/ui/KpiCard";
import type { AbcXyzCell, ReorderItem } from "@/types";

function fmtMoney(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}
function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

// ── ABC×XYZ Matrix ────────────────────────────────────────────────────────────

const ABC_LABELS = ["A", "B", "C"];
const XYZ_LABELS = ["X", "Y", "Z"];

const CELL_COLORS: Record<string, string> = {
  AX: "#22c55e",  // green — fast, reliable, high-value
  AY: "#84cc16",
  AZ: "#eab308",  // amber — high-value but erratic
  BX: "#60a5fa",
  BY: "#818cf8",
  BZ: "#a78bfa",
  CX: "#94a3b8",
  CY: "#94a3b8",
  CZ: "#f87171",  // red — low-value, erratic → dead stock risk
};

function AbcXyzGrid({ cells }: { cells: AbcXyzCell[] }) {
  const cellMap: Record<string, AbcXyzCell> = {};
  cells.forEach((c) => { cellMap[`${c.abc}${c.xyz}`] = c; });

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="p-2 text-muted-foreground" />
            {XYZ_LABELS.map((y) => (
              <th key={y} className="p-2 text-center font-medium text-muted-foreground">
                {y} <span className="opacity-60 text-[10px] block">
                  {y === "X" ? "CV<0.25" : y === "Y" ? "CV<0.50" : "CV≥0.50"}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ABC_LABELS.map((a) => (
            <tr key={a}>
              <td className="p-2 font-medium text-muted-foreground">
                {a} <span className="opacity-60 text-[10px] block">
                  {a === "A" ? "top 80% rev" : a === "B" ? "next 15%" : "rest 5%"}
                </span>
              </td>
              {XYZ_LABELS.map((y) => {
                const key = `${a}${y}`;
                const cell = cellMap[key];
                const count = cell?.sku_count ?? 0;
                return (
                  <td
                    key={key}
                    className="p-3 text-center border border-border/30 rounded"
                    style={{ backgroundColor: `${CELL_COLORS[key]}22` }}
                  >
                    <div
                      className="inline-block w-2 h-2 rounded-full mb-1"
                      style={{ backgroundColor: CELL_COLORS[key] }}
                    />
                    <div className="font-semibold text-foreground">{count}</div>
                    <div className="text-muted-foreground text-[10px]">SKUs</div>
                    {count > 0 && (
                      <div className="text-muted-foreground text-[10px]">
                        {fmtMoney(cell.total_revenue)}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Reorder Queue ─────────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
  high: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  medium: "bg-blue-500/10 text-blue-500 border-blue-500/20",
};

function ReorderQueuePanel() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: queue, isLoading } = useQuery({
    queryKey: ["inventory-reorder-queue"],
    queryFn: getReorderQueueApi,
  });

  const acceptMutation = useMutation({
    mutationFn: ({ itemId, qty }: { itemId: string; qty?: number }) =>
      acceptReorderApi(itemId, qty),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory-reorder-queue"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-overview"] });
    },
  });

  const items = (queue?.items ?? []).slice(0, 10);

  if (isLoading) {
    return <div className="h-48 rounded-xl bg-muted animate-pulse" />;
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center">
        <CheckCircle className="mx-auto mb-3 h-8 w-8 text-green-500" />
        <p className="font-medium text-sm">No reorder items</p>
        <p className="text-xs text-muted-foreground mt-1">All SKUs are above their reorder points.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between p-5 border-b">
        <div>
          <h2 className="text-base font-medium">Reorder Queue</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {queue?.total ?? 0} SKUs below reorder point · top 10 shown
          </p>
        </div>
        <ShoppingCart className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b">
            <tr>
              {["SKU", "Stock", "Reorder Pt", "EOQ", "Est. Cost", "Days Out", "Priority", ""].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item: ReorderItem) => (
              <tr
                key={item.id}
                className="border-b last:border-0 hover:bg-muted/30 transition-colors"
              >
                <td
                  className="px-4 py-3 font-mono text-xs font-medium cursor-pointer hover:underline"
                  onClick={() => navigate(`/dashboard/inventory/${encodeURIComponent(item.sku)}`)}
                >
                  {item.sku}
                </td>
                <td className="px-4 py-3 text-destructive font-medium">{fmtNum(item.current_stock)}</td>
                <td className="px-4 py-3">{fmtNum(item.reorder_point)}</td>
                <td className="px-4 py-3">{fmtNum(item.eoq)}</td>
                <td className="px-4 py-3">{fmtMoney(item.estimated_cost)}</td>
                <td className="px-4 py-3">
                  {item.days_until_stockout !== null ? (
                    <span className={item.days_until_stockout < 7 ? "text-destructive font-medium" : ""}>
                      {item.days_until_stockout}d
                    </span>
                  ) : "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium ${PRIORITY_STYLES[item.priority]}`}>
                    {item.priority}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    className="inline-flex items-center gap-1 rounded bg-primary/10 text-primary px-2 py-1 text-xs font-medium hover:bg-primary/20 transition-colors disabled:opacity-50"
                    disabled={acceptMutation.isPending}
                    onClick={() => acceptMutation.mutate({ itemId: item.id })}
                  >
                    <Zap className="h-3 w-3" />
                    Accept
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Stock Status Tabs ─────────────────────────────────────────────────────────

const STOCK_TABS = ["Understock", "Overstock", "Dead Stock"] as const;
type StockTab = typeof STOCK_TABS[number];

function StockStatusPanel() {
  const [activeTab, setActiveTab] = useState<StockTab>("Understock");

  const { data: understock } = useQuery({
    queryKey: ["inventory-understock"],
    queryFn: getUnderstockApi,
    enabled: activeTab === "Understock",
  });

  const { data: overstock } = useQuery({
    queryKey: ["inventory-overstock"],
    queryFn: () => getOverstockApi(90),
    enabled: activeTab === "Overstock",
  });

  const { data: deadStock } = useQuery({
    queryKey: ["inventory-dead-stock"],
    queryFn: () => getDeadStockApi(90),
    enabled: activeTab === "Dead Stock",
  });

  return (
    <div className="rounded-xl border bg-card">
      {/* Tab bar */}
      <div className="flex border-b px-4 pt-4 gap-1">
        {STOCK_TABS.map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab
                ? "bg-background border border-b-background -mb-px text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
            {tab === "Understock" && (understock?.total ?? 0) > 0 && (
              <span className="ml-2 rounded-full bg-destructive/10 text-destructive px-1.5 py-0.5 text-xs">
                {understock!.total}
              </span>
            )}
            {tab === "Overstock" && (overstock?.total ?? 0) > 0 && (
              <span className="ml-2 rounded-full bg-amber-500/10 text-amber-500 px-1.5 py-0.5 text-xs">
                {overstock!.total}
              </span>
            )}
            {tab === "Dead Stock" && (deadStock?.total ?? 0) > 0 && (
              <span className="ml-2 rounded-full bg-muted text-muted-foreground px-1.5 py-0.5 text-xs">
                {deadStock!.total}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-5">
        {activeTab === "Understock" && (
          <>
            <div className="flex items-center gap-2 mb-4">
              <TrendingDown className="h-4 w-4 text-destructive" />
              <p className="text-xs text-muted-foreground">
                {understock?.total ?? 0} SKUs below safety stock
              </p>
            </div>
            {(understock?.items?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No understock issues detected.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b">
                    <tr>
                      {["SKU", "Stock", "Reorder Pt", "Shortage", "Days Out", "Priority"].map((h) => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {understock!.items.slice(0, 20).map((item) => (
                      <tr key={item.sku} className="border-b last:border-0">
                        <td className="px-3 py-2 font-mono text-xs">{item.sku}</td>
                        <td className="px-3 py-2 text-destructive">{fmtNum(item.current_stock)}</td>
                        <td className="px-3 py-2">{fmtNum(item.reorder_point)}</td>
                        <td className="px-3 py-2 text-destructive">{fmtNum(item.shortage_units)}</td>
                        <td className="px-3 py-2">
                          {item.days_until_stockout !== null ? `${item.days_until_stockout}d` : "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium ${PRIORITY_STYLES[item.priority] ?? ""}`}>
                            {item.priority}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {activeTab === "Overstock" && (
          <>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-4 w-4 text-amber-500" />
              <p className="text-xs text-muted-foreground">
                {overstock?.total ?? 0} SKUs above 90-day DOH target ·{" "}
                {fmtMoney(overstock?.total_excess_value ?? 0)} excess value
              </p>
            </div>
            {(overstock?.items?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No overstock detected at 90-day DOH target.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b">
                    <tr>
                      {["SKU", "Stock", "DOH", "Excess Units", "Excess $"].map((h) => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {overstock!.items.slice(0, 20).map((item) => (
                      <tr key={item.sku} className="border-b last:border-0">
                        <td className="px-3 py-2 font-mono text-xs">{item.sku}</td>
                        <td className="px-3 py-2">{fmtNum(item.current_stock)}</td>
                        <td className="px-3 py-2 text-amber-500 font-medium">{item.doh}d</td>
                        <td className="px-3 py-2">{fmtNum(item.excess_units)}</td>
                        <td className="px-3 py-2 text-amber-500">{fmtMoney(item.excess_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {activeTab === "Dead Stock" && (
          <>
            <div className="flex items-center gap-2 mb-4">
              <Archive className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">
                {deadStock?.total ?? 0} SKUs with no sales in 90+ days ·{" "}
                {fmtMoney(deadStock?.total_tied_up_value ?? 0)} tied up
              </p>
            </div>
            {(deadStock?.items?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No dead stock detected (90-day threshold).</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b">
                    <tr>
                      {["SKU", "Stock", "Last Sold", "Tied-Up $"].map((h) => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {deadStock!.items.slice(0, 20).map((item) => (
                      <tr key={item.sku} className="border-b last:border-0">
                        <td className="px-3 py-2 font-mono text-xs">{item.sku}</td>
                        <td className="px-3 py-2">{fmtNum(item.current_stock)}</td>
                        <td className="px-3 py-2 text-muted-foreground">{item.last_sold_days_ago}+ days ago</td>
                        <td className="px-3 py-2 font-medium">{fmtMoney(item.tied_up_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const AGING_COLORS: Record<string, string> = {
  "<30d": "#22c55e",
  "30-60d": "#84cc16",
  "60-90d": "#eab308",
  "90-180d": "#f97316",
  "180+d": "#ef4444",
};

export function InventoryPage() {
  const navigate = useNavigate();

  const { data: overview, isLoading: ovLoading } = useQuery({
    queryKey: ["inventory-overview"],
    queryFn: getInventoryOverviewApi,
  });

  const { data: abcXyz, isLoading: matrixLoading } = useQuery({
    queryKey: ["inventory-abc-xyz"],
    queryFn: getAbcXyzMatrixApi,
  });

  const { data: aging, isLoading: agingLoading } = useQuery({
    queryKey: ["inventory-aging"],
    queryFn: getAgingApi,
  });

  const { data: valuation } = useQuery({
    queryKey: ["inventory-valuation"],
    queryFn: getValuationApi,
  });

  const { data: skuList } = useQuery({
    queryKey: ["inventory-skus", 1, 20],
    queryFn: () => getSkuListApi({ page: 1, page_size: 20 }),
  });

  const isLoading = ovLoading || matrixLoading || agingLoading;

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="grid grid-cols-3 gap-4 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-muted" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-72 rounded-xl bg-muted" />
          <div className="h-72 rounded-xl bg-muted" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Inventory Intelligence</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Stock health, ABC/XYZ classification, and valuation analysis
        </p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Total Inventory Value"
          value={fmtMoney(overview?.total_inventory_value ?? 0)}
          icon={DollarSign}
        />
        <KpiCard
          label="Total SKUs"
          value={fmtNum(overview?.total_skus ?? 0)}
          icon={Layers}
        />
        <KpiCard
          label="SKUs at Risk"
          value={fmtNum(overview?.skus_at_risk ?? 0)}
          icon={AlertTriangle}
          valueVariant={(overview?.skus_at_risk ?? 0) > 0 ? "warn" : "ok"}
          alert={(overview?.skus_at_risk ?? 0) > 0}
        />
        <KpiCard
          label="Stockout Risk"
          value={fmtNum(overview?.stockout_risk_skus ?? 0)}
          icon={PackageX}
          valueVariant={(overview?.stockout_risk_skus ?? 0) > 0 ? "bad" : "ok"}
          alert={(overview?.stockout_risk_skus ?? 0) > 0}
        />
        <KpiCard
          label="Dead Stock Value"
          value={fmtMoney(overview?.dead_stock_value ?? 0)}
          icon={Archive}
          valueVariant={(overview?.dead_stock_value ?? 0) > 0 ? "warn" : "default"}
        />
        <KpiCard
          label="Reorder Queue"
          value={fmtNum(overview?.reorder_queue_count ?? 0)}
          icon={ShoppingCart}
          valueVariant={(overview?.reorder_queue_count ?? 0) > 0 ? "warn" : "default"}
        />
      </div>

      {/* ABC×XYZ + Aging */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* ABC×XYZ Matrix */}
        <div className="rounded-xl border bg-card p-5">
          <h2 className="text-base font-medium mb-1">ABC × XYZ Matrix</h2>
          <p className="text-xs text-muted-foreground mb-4">
            {abcXyz?.total_skus ?? 0} SKUs ·{" "}
            {fmtMoney(abcXyz?.total_revenue ?? 0)} total revenue
          </p>
          {abcXyz && abcXyz.cells.length > 0 ? (
            <AbcXyzGrid cells={abcXyz.cells} />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-12">
              No data — upload sales data to see ABC×XYZ classification.
            </p>
          )}
        </div>

        {/* Aging Buckets */}
        <div className="rounded-xl border bg-card p-5">
          <h2 className="text-base font-medium mb-1">Inventory Aging</h2>
          <p className="text-xs text-muted-foreground mb-4">
            {aging?.total_skus ?? 0} SKUs ·{" "}
            {fmtMoney(aging?.total_value ?? 0)} total value
          </p>
          {aging && aging.buckets.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={aging.buckets} layout="vertical" margin={{ left: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  dataKey="bucket"
                  type="category"
                  tick={{ fontSize: 11 }}
                  width={55}
                />
                <Tooltip
                  formatter={(v: number) => [fmtMoney(v), "Value"]}
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="total_value" radius={[0, 4, 4, 0]}>
                  {aging.buckets.map((b) => (
                    <Cell key={b.bucket} fill={AGING_COLORS[b.bucket] ?? "#6366f1"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-12">
              No aging data — upload operations data to classify inventory age.
            </p>
          )}
        </div>
      </div>

      {/* Valuation by Category */}
      {valuation && valuation.by_category.length > 0 && (
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-medium">Inventory Valuation</h2>
              <p className="text-xs text-muted-foreground">
                Cost {fmtMoney(valuation.total_cost_value)} ·
                Retail {fmtMoney(valuation.total_retail_value)} ·
                Potential margin {valuation.potential_margin}%
              </p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={valuation.by_category.slice(0, 12)} margin={{ left: 60 }} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={55} />
              <Tooltip
                formatter={(v: number, name: string) => [fmtMoney(v), name === "cost_value" ? "Cost" : "Retail"]}
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="cost_value" fill="#6366f1" name="cost_value" radius={[0, 4, 4, 0]} />
              <Bar dataKey="retail_value" fill="#22c55e" name="retail_value" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Reorder Queue */}
      <ReorderQueuePanel />

      {/* Stock Status Tabs */}
      <StockStatusPanel />

      {/* SKU Table */}
      {skuList && skuList.items.length > 0 && (
        <div className="rounded-xl border bg-card">
          <div className="flex items-center justify-between p-5 border-b">
            <h2 className="text-base font-medium">SKU Overview</h2>
            <span className="text-xs text-muted-foreground">{skuList.total} total SKUs</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr>
                  {["SKU", "Stock", "Reorder Pt", "Unit Cost", "Value", "DOH", "ABC", "XYZ"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {skuList.items.map((sku) => (
                  <tr
                    key={sku.sku}
                    className="border-b last:border-0 hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() => navigate(`/dashboard/inventory/${encodeURIComponent(sku.sku)}`)}
                  >
                    <td className="px-4 py-3 font-mono font-medium text-xs">{sku.sku}</td>
                    <td className="px-4 py-3">{fmtNum(sku.current_stock)}</td>
                    <td className={`px-4 py-3 ${sku.current_stock < sku.reorder_point ? "text-destructive font-medium" : ""}`}>
                      {fmtNum(sku.reorder_point)}
                    </td>
                    <td className="px-4 py-3">{fmtMoney(sku.avg_unit_cost)}</td>
                    <td className="px-4 py-3">{fmtMoney(sku.total_value)}</td>
                    <td className="px-4 py-3">
                      {sku.days_on_hand !== null ? `${sku.days_on_hand}d` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {sku.abc_class ? (
                        <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                          sku.abc_class === "A" ? "bg-green-500/10 text-green-500"
                          : sku.abc_class === "B" ? "bg-blue-500/10 text-blue-500"
                          : "bg-muted text-muted-foreground"
                        }`}>{sku.abc_class}</span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {sku.xyz_class ? (
                        <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                          sku.xyz_class === "X" ? "bg-green-500/10 text-green-500"
                          : sku.xyz_class === "Y" ? "bg-amber-500/10 text-amber-500"
                          : "bg-red-500/10 text-red-500"
                        }`}>{sku.xyz_class}</span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && (overview?.total_skus ?? 0) === 0 && (
        <div className="rounded-xl border bg-card p-12 text-center">
          <Layers className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h3 className="font-medium">No inventory data yet</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Upload operations and sales data to unlock inventory intelligence.
          </p>
        </div>
      )}
    </div>
  );
}
