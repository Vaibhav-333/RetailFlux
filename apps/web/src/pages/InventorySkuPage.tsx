import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowLeft,
  Brain,
  ChevronDown,
  ChevronRight,
  Package,
  Sparkles,
} from "lucide-react";
import {
  getExplanationApi,
  getReorderQueueApi,
  getSeasonalityApi,
  getSkuListApi,
} from "@/features/inventory/api";
import type { ExplanationOut, ReorderItem, SkuSummaryOut } from "@/types";

function fmtMoney(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}
function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-2 border-b last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

// ── Health score gauge ────────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const color = score >= 70 ? "#22c55e" : score >= 40 ? "#eab308" : "#ef4444";
  return (
    <div className="flex items-center gap-4">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <svg viewBox="0 0 36 36" className="h-20 w-20 -rotate-90">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="3"
          />
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={`${score}, 100`}
          />
        </svg>
        <span className="absolute text-base font-bold" style={{ color }}>
          {score}
        </span>
      </div>
      <div>
        <p className="text-sm font-medium">Health Score</p>
        <p className="text-xs text-muted-foreground">
          {score >= 70 ? "Good" : score >= 40 ? "Needs attention" : "Critical"}
        </p>
      </div>
    </div>
  );
}

// ── AI Explanation panel ──────────────────────────────────────────────────────

function AiExplanationPanel({ sku, itemId }: { sku: string; itemId?: string }) {
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<ExplanationOut | null>(null);

  const explainMutation = useMutation({
    mutationFn: () => getExplanationApi(itemId ?? sku),
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-500" />
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            AI Explanation
          </h2>
          {result?.cached && (
            <span className="text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">cached</span>
          )}
        </div>
        <button
          className="flex items-center gap-1 text-xs bg-violet-500/10 text-violet-500 rounded px-2 py-1 hover:bg-violet-500/20 transition-colors disabled:opacity-50"
          disabled={explainMutation.isPending}
          onClick={() => {
            setOpen(true);
            explainMutation.mutate();
          }}
        >
          <Brain className="h-3 w-3" />
          {explainMutation.isPending ? "Thinking…" : "Explain"}
        </button>
      </div>

      {open && result && (
        <div className="mt-4 space-y-3">
          <p className="text-sm leading-relaxed">{result.rationale}</p>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Confidence:</span>
            <span className={`text-xs font-medium ${
              result.confidence === "high" ? "text-green-500"
              : result.confidence === "medium" ? "text-amber-500"
              : "text-muted-foreground"
            }`}>
              {result.confidence}
            </span>
          </div>

          {result.key_factors.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Key factors</p>
              <ul className="space-y-1">
                {result.key_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs">
                    <ChevronRight className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.alternatives.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Alternatives</p>
              <ul className="space-y-1">
                {result.alternatives.map((a, i) => (
                  <li key={i} className="text-xs text-muted-foreground">· {a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {open && !result && !explainMutation.isPending && (
        <p className="text-xs text-muted-foreground mt-3">Failed to generate explanation — try again.</p>
      )}
    </div>
  );
}

// ── Seasonality chart ─────────────────────────────────────────────────────────

function SeasonalityPanel({ sku }: { sku: string }) {
  const [expanded, setExpanded] = useState(false);

  const { data: seasonality, isLoading } = useQuery({
    queryKey: ["inventory-seasonality", sku],
    queryFn: () => getSeasonalityApi(sku),
    enabled: expanded,
  });

  const trendData = seasonality?.trend.map((p, i) => ({
    date: p.date,
    trend: p.value,
    seasonal: seasonality.seasonal[i]?.value ?? 0,
  })) ?? [];

  return (
    <div className="rounded-xl border bg-card p-5">
      <button
        className="w-full flex items-center justify-between"
        onClick={() => setExpanded((v) => !v)}
      >
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
          Demand Seasonality
        </h2>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div className="mt-4">
          {isLoading && <div className="h-40 bg-muted rounded animate-pulse" />}

          {!isLoading && (seasonality?.trend.length ?? 0) === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">
              Not enough history for decomposition (need 21+ days).
            </p>
          )}

          {!isLoading && trendData.length > 0 && (
            <>
              <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-0.5 bg-indigo-500" /> Trend
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-0.5 bg-amber-400" /> Seasonal
                </span>
                {seasonality?.has_yearly_pattern && (
                  <span className="text-green-500 font-medium">Yearly pattern detected</span>
                )}
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={trendData} margin={{ left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(d: string) => d.slice(5)}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [v.toFixed(1), name]}
                    contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="trend"
                    stroke="#6366f1"
                    fill="#6366f120"
                    strokeWidth={2}
                    dot={false}
                    name="Trend"
                  />
                  <Area
                    type="monotone"
                    dataKey="seasonal"
                    stroke="#f59e0b"
                    fill="#f59e0b10"
                    strokeWidth={1.5}
                    dot={false}
                    name="Seasonal"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function InventorySkuPage() {
  const { sku } = useParams<{ sku: string }>();
  const navigate = useNavigate();
  const decodedSku = sku ? decodeURIComponent(sku) : "";

  const { data: list, isLoading } = useQuery({
    queryKey: ["inventory-skus-search", decodedSku],
    queryFn: () => getSkuListApi({ page: 1, page_size: 100, search: decodedSku }),
    enabled: !!decodedSku,
  });

  const { data: reorderQueue } = useQuery({
    queryKey: ["inventory-reorder-queue"],
    queryFn: getReorderQueueApi,
    enabled: !!decodedSku,
  });

  const skuData: SkuSummaryOut | undefined = list?.items.find((s) => s.sku === decodedSku);
  const reorderItem: ReorderItem | undefined = reorderQueue?.items.find(
    (i) => i.sku === decodedSku,
  );

  // Synthetic health score from SKU data (0-100, rough approximation for display)
  const healthScore = skuData
    ? Math.min(100, Math.max(0, Math.round(
        (skuData.current_stock >= skuData.reorder_point ? 50 : 20) +
        (skuData.days_on_hand !== null && skuData.days_on_hand >= 14 && skuData.days_on_hand <= 90 ? 30 : 10) +
        (skuData.abc_class === "A" ? 20 : skuData.abc_class === "B" ? 12 : 5),
      )))
    : 0;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <button
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        onClick={() => navigate("/dashboard/inventory")}
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Inventory
      </button>

      {isLoading && (
        <div className="space-y-4 animate-pulse">
          <div className="h-12 rounded-xl bg-muted" />
          <div className="h-48 rounded-xl bg-muted" />
          <div className="h-48 rounded-xl bg-muted" />
        </div>
      )}

      {!isLoading && skuData && (
        <>
          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Package className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold font-mono">{skuData.sku}</h1>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                {skuData.abc_class && (
                  <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                    skuData.abc_class === "A" ? "bg-green-500/10 text-green-500"
                    : skuData.abc_class === "B" ? "bg-blue-500/10 text-blue-500"
                    : "bg-muted text-muted-foreground"
                  }`}>
                    ABC: {skuData.abc_class}
                  </span>
                )}
                {skuData.xyz_class && (
                  <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                    skuData.xyz_class === "X" ? "bg-green-500/10 text-green-500"
                    : skuData.xyz_class === "Y" ? "bg-amber-500/10 text-amber-500"
                    : "bg-red-500/10 text-red-500"
                  }`}>
                    XYZ: {skuData.xyz_class}
                  </span>
                )}
                {skuData.current_stock < skuData.reorder_point && (
                  <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-destructive/10 text-destructive">
                    Below Reorder Point
                  </span>
                )}
                {reorderItem && (
                  <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${
                    reorderItem.priority === "critical" ? "bg-red-500/10 text-red-500 border-red-500/20"
                    : reorderItem.priority === "high" ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                    : "bg-blue-500/10 text-blue-500 border-blue-500/20"
                  }`}>
                    {reorderItem.priority} priority
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Health Score */}
          <div className="rounded-xl border bg-card p-5 mb-4">
            <HealthGauge score={healthScore} />
          </div>

          {/* Stock metrics */}
          <div className="rounded-xl border bg-card p-5 mb-4">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Stock Metrics
            </h2>
            <InfoRow label="Current Stock" value={fmtNum(skuData.current_stock)} />
            <InfoRow label="Reorder Point" value={fmtNum(skuData.reorder_point)} />
            <InfoRow
              label="Days on Hand"
              value={skuData.days_on_hand !== null ? `${skuData.days_on_hand} days` : "N/A"}
            />
            <InfoRow label="Avg Daily Demand" value={`${skuData.avg_daily_demand} units/day`} />
          </div>

          {/* Reorder Math (only if in queue) */}
          {reorderItem && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5 mb-4">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
                Reorder Intelligence
              </h2>
              <InfoRow label="EOQ (Economic Order Qty)" value={fmtNum(reorderItem.eoq)} />
              <InfoRow label="Safety Stock" value={fmtNum(reorderItem.safety_stock)} />
              <InfoRow label="Recommended Order Qty" value={
                <span className="text-amber-500 font-semibold">{fmtNum(reorderItem.recommended_order_qty)}</span>
              } />
              <InfoRow label="Estimated Cost" value={fmtMoney(reorderItem.estimated_cost)} />
              <InfoRow label="Lead Time" value={`${reorderItem.lead_time_days} days`} />
              {reorderItem.days_until_stockout !== null && (
                <InfoRow
                  label="Days Until Stockout"
                  value={
                    <span className={reorderItem.days_until_stockout < 7 ? "text-destructive font-bold" : ""}>
                      {reorderItem.days_until_stockout}d
                    </span>
                  }
                />
              )}
            </div>
          )}

          {/* Valuation */}
          <div className="rounded-xl border bg-card p-5 mb-4">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Valuation
            </h2>
            <InfoRow label="Avg Unit Cost" value={fmtMoney(skuData.avg_unit_cost)} />
            <InfoRow label="Total Inventory Value" value={fmtMoney(skuData.total_value)} />
          </div>

          {/* Seasonality */}
          <div className="mb-4">
            <SeasonalityPanel sku={decodedSku} />
          </div>

          {/* AI Explanation */}
          <AiExplanationPanel sku={decodedSku} itemId={reorderItem?.id} />
        </>
      )}

      {!isLoading && !skuData && decodedSku && (
        <div className="rounded-xl border bg-card p-12 text-center">
          <Package className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h3 className="font-medium">SKU not found</h3>
          <p className="text-sm text-muted-foreground mt-1">
            "{decodedSku}" was not found in the current inventory data.
          </p>
        </div>
      )}
    </div>
  );
}
