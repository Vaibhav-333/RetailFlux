import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Area,
  ComposedChart,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import {
  ShoppingCart,
  Megaphone,
  Warehouse,
  DollarSign,
  Truck,
  AlertTriangle,
  Activity,
  TrendingUp,
  Sparkles,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { getDashboardSummaryApi } from "@/features/dashboard/api";
import { invalidateAnalyticsCacheApi } from "@/features/cache/api";
import { getInsightsApi, getAnomaliesApi } from "@/features/insights/api";
import { getTopSkusForecastApi } from "@/features/forecasting/api";
import { getOperationsKpisApi } from "@/features/operations/api";
import { getProcurementKpisApi } from "@/features/procurement/api";
import { getTeamScoreApi, listRecommendationsApi } from "@/features/tasks/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import type { LowStockSku, SupplierSpend } from "@/types";

type AlertSev = "critical" | "warning";
type DynAlert = { id: string | number; msg: string; sev: AlertSev };

const DEPT_ICONS: Record<string, React.ElementType> = {
  sales: ShoppingCart,
  marketing: Megaphone,
  operations: Warehouse,
  finance: DollarSign,
  procurement: Truck,
};

export function DashboardPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      await invalidateAnalyticsCacheApi();
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["insights-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["top-skus-forecast-dash"] });
    } finally { setIsRefreshing(false); }
  }

  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummaryApi,
    staleTime: 5 * 60 * 1000,
  });

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ["insights-summary"],
    queryFn: getInsightsApi,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const { data: anomalies = [] } = useQuery({
    queryKey: ["revenue-anomalies"],
    queryFn: getAnomaliesApi,
    staleTime: 10 * 60 * 1000,
    enabled: !!summary,
    retry: 1,
  });

  const { data: forecastData } = useQuery({
    queryKey: ["top-skus-forecast-dash"],
    queryFn: getTopSkusForecastApi,
    staleTime: 30 * 60 * 1000,
    retry: 1,
  });

  const { data: operationsData } = useQuery({
    queryKey: ["operations-kpis-dash"],
    queryFn: () => getOperationsKpisApi(),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const { data: procurementData } = useQuery({
    queryKey: ["procurement-kpis-dash"],
    queryFn: () => getProcurementKpisApi(),
  });

  const { data: teamScore } = useQuery({
    queryKey: ["task-team-score-dash"],
    queryFn: getTeamScoreApi,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const { data: aiRecs } = useQuery({
    queryKey: ["task-recommendations-dash"],
    queryFn: () => listRecommendationsApi({ page: 1, size: 3 }),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const forecastChartData = useMemo(() => {
    const hist = (summary?.daily_revenue ?? []).slice(-30).map((p) => ({
      date: p.date,
      revenue: p.revenue,
      yhat: undefined as number | undefined,
      lower: undefined as number | undefined,
      band: undefined as number | undefined,
    }));
    const topFc = forecastData?.forecasts[0];
    const fc = (topFc?.points ?? []).map((p) => ({
      date: p.ds,
      revenue: undefined as number | undefined,
      yhat: Math.max(0, p.yhat),
      lower: Math.max(0, p.yhat_lower),
      band: Math.max(0, p.yhat_upper - p.yhat_lower),
    }));
    return [...hist, ...fc];
  }, [summary, forecastData]);

  const dynamicAlerts = useMemo((): DynAlert[] => {
    const alerts: DynAlert[] = [];
    anomalies.forEach((a, i) => {
      alerts.push({
        id: `anomaly-${i}`,
        msg: `Revenue anomaly on ${a.date} — z-score ${a.z_score > 0 ? "+" : ""}${a.z_score.toFixed(2)}`,
        sev: "critical",
      });
    });
    const below = operationsData?.skus_below_reorder ?? 0;
    if (below > 0) {
      alerts.push({
        id: "low-stock",
        msg: `${below} SKU${below > 1 ? "s" : ""} below reorder point — restocking needed`,
        sev: below > 5 ? "critical" : "warning",
      });
    }
    const outOfStock = (operationsData?.low_stock_skus ?? []).filter((s) => s.stock_level === 0);
    if (outOfStock.length > 0) {
      alerts.push({
        id: "out-of-stock",
        msg: `${outOfStock.length} SKU${outOfStock.length > 1 ? "s" : ""} completely out of stock`,
        sev: "critical",
      });
    }
    return alerts;
  }, [anomalies, operationsData]);

  const anomalyDates = new Set(anomalies.map((a) => a.date));
  const topForecastSku = forecastData?.forecasts[0]?.sku ?? "";
  const revenueSparkline = useMemo(
    () => (summary?.daily_revenue ?? []).slice(-30).map((d) => d.revenue),
    [summary]
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Master Dashboard</h1>
          <p className="text-sm text-muted-foreground">Company-wide overview · Last 90 days</p>
        </div>
        <button
          onClick={() => { void handleRefresh(); }}
          disabled={isRefreshing}
          title="Bust all caches and refetch from MongoDB"
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* 5 dept KPI cards */}
      {summaryLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <KpiCard key={i} label="" value="" loading size="md" />
          ))}
        </div>
      )}
      {summaryError && (
        <p className="text-sm text-destructive">Failed to load summary data.</p>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <KpiCard
              label="Total Revenue"
              value={formatCurrency(summary.total_revenue)}
              icon={ShoppingCart}
              subline={summary.top_sku ? `Top: ${summary.top_sku}` : undefined}
              sparkline={revenueSparkline}
              onClick={() => navigate("/dashboard/sales")}
              size="md"
            />
            <KpiCard
              label="ROAS"
              value={`${summary.roas.toFixed(2)}×`}
              icon={Megaphone}
              subline={`Spend: ${formatCurrency(summary.marketing_spend)}`}
              onClick={() => navigate("/dashboard/marketing")}
              size="md"
            />
            <KpiCard
              label="SKUs Below Reorder"
              value={summary.skus_below_reorder.toLocaleString()}
              icon={Warehouse}
              subline={`${summary.active_warehouses} active warehouses`}
              alert={summary.skus_below_reorder > 0}
              onClick={() => navigate("/dashboard/operations")}
              size="md"
            />
            <KpiCard
              label="Gross Margin"
              value={formatPercent(summary.gross_margin)}
              icon={DollarSign}
              subline={`Profit: ${formatCurrency(summary.total_gross_profit)}`}
              valueVariant={summary.gross_margin >= 30 ? "ok" : summary.gross_margin < 0 ? "bad" : "default"}
              onClick={() => navigate("/dashboard/finance")}
              size="md"
            />
            <KpiCard
              label="Procurement Spend"
              value={formatCurrency(summary.procurement_spend)}
              icon={Truck}
              subline={`${summary.unique_suppliers} suppliers · ${summary.avg_lead_days}d lead`}
              onClick={() => navigate("/dashboard/procurement")}
              size="md"
            />
          </div>

          {/* Revenue sparkline with anomaly dots */}
          {summary.daily_revenue.length > 0 && (
            <div className="rounded-lg border bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-foreground flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-brand-500" />
                  Revenue Trend (last 90 days)
                  {anomalies.length > 0 && (
                    <span className="text-xs bg-[hsl(var(--warn)/0.1)] text-[hsl(var(--warn))] px-2 py-0.5 rounded-full font-medium">
                      {anomalies.length} anomal{anomalies.length === 1 ? "y" : "ies"}
                    </span>
                  )}
                </h2>
                <Link to="/dashboard/sales" className="text-xs text-brand-500 hover:underline">View details →</Link>
              </div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={summary.daily_revenue}>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={(l) => `Date: ${l}`} contentStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2} dot={false} name="Revenue" />
                  {summary.daily_revenue.filter((d) => anomalyDates.has(d.date)).map((d) => (
                    <ReferenceDot key={d.date} x={d.date} y={d.revenue} r={5} fill="#f59e0b" stroke="#ffffff" strokeWidth={1.5} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              {anomalies.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 mr-1" />
                  {anomalies.map((a) => `${a.date} (z=${a.z_score > 0 ? "+" : ""}${a.z_score})`).join(", ")}
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* Alerts + AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AlertsPanel alerts={dynamicAlerts} isLoading={summaryLoading} />
        <AiInsightsPanel insights={insights} isLoading={insightsLoading} />
      </div>

      {/* Real data panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <DemandForecastPanel chartData={forecastChartData} topSku={topForecastSku} />
        <SkuRecommendationsPanel skus={operationsData?.low_stock_skus ?? []} isLoading={!operationsData} />
        <SupplyChainRiskPanel suppliers={procurementData?.top_suppliers ?? []} avgLeadDays={procurementData?.avg_lead_days ?? 0} isLoading={!procurementData} />
      </div>

      {/* Task analytics block */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TaskScorePanel score={teamScore} />
        <AiRecsPanel recs={aiRecs?.items ?? []} />
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AlertsPanel({ alerts, isLoading }: { alerts: DynAlert[]; isLoading?: boolean }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-[hsl(var(--warn))]" />
        <h3 className="text-sm font-medium text-foreground">Active Alerts</h3>
        {alerts.length > 0 && (
          <span className="ml-auto text-xs bg-[hsl(var(--bad)/0.1)] text-[hsl(var(--bad))] px-2 py-0.5 rounded-full font-medium">
            {alerts.length}
          </span>
        )}
      </div>
      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />Loading alerts…
        </div>
      ) : alerts.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">No active alerts — all systems nominal.</p>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={cn(
                "flex items-start gap-2 p-2 rounded-md text-xs",
                a.sev === "critical"
                  ? "bg-[hsl(var(--bad)/0.06)] text-[hsl(var(--bad))]"
                  : "bg-[hsl(var(--warn)/0.06)] text-[hsl(var(--warn))]"
              )}
            >
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              {a.msg}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AiInsightsPanel({ insights, isLoading }: { insights: import("@/types").InsightsOut | undefined; isLoading: boolean }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-brand-500" />
        <h3 className="text-sm font-medium text-foreground">AI Executive Summary</h3>
        {insights && <span className="ml-auto text-xs text-muted-foreground capitalize">via {insights.generated_by}</span>}
      </div>
      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />Generating insights…
        </div>
      )}
      {insights && !isLoading && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground leading-relaxed">{insights.summary}</p>
          {insights.insights.length > 0 && (
            <div className="space-y-1.5 mt-3">
              {insights.insights.map((item, i) => {
                const Icon = DEPT_ICONS[item.dept] ?? Activity;
                return (
                  <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <Icon className="w-3.5 h-3.5 mt-0.5 shrink-0 text-brand-400" />
                    <span><strong className="text-foreground capitalize">{item.dept}:</strong> {item.text}</span>
                  </div>
                );
              })}
            </div>
          )}
          {insights.generated_by === "fallback" && (
            <p className="text-xs text-muted-foreground/50 mt-2 italic">Add GEMINI_API_KEY or GROQ_API_KEY to .env for live insights.</p>
          )}
        </div>
      )}
      {!isLoading && !insights && (
        <p className="text-xs text-muted-foreground py-4">Could not load AI insights.</p>
      )}
    </div>
  );
}

function DemandForecastPanel({ chartData, topSku }: {
  chartData: { date: string; revenue?: number; yhat?: number; lower?: number; band?: number }[];
  topSku: string;
}) {
  const hasData = chartData.length > 0;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp className="w-4 h-4 text-brand-500" />
        <h3 className="text-sm font-medium text-foreground">Demand Forecast (30d)</h3>
        {topSku && <span className="ml-auto text-[10px] text-muted-foreground truncate max-w-[80px]">{topSku}</span>}
      </div>
      {!hasData ? (
        <p className="text-xs text-muted-foreground py-8 text-center">Insufficient data for forecast.</p>
      ) : (
        <ResponsiveContainer width="100%" height={130}>
          <ComposedChart data={chartData}>
            <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={(l) => `Date: ${l}`} contentStyle={{ fontSize: 11 }} />
            <Area type="monotone" dataKey="lower" stackId="ci" stroke="none" fill="transparent" dot={false} legendType="none" />
            <Area type="monotone" dataKey="band" stackId="ci" fill="#f97316" fillOpacity={0.18} stroke="none" dot={false} legendType="none" />
            <Line type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={1.5} dot={false} connectNulls={false} />
            <Line type="monotone" dataKey="yhat" stroke="#f97316" strokeDasharray="4 2" strokeWidth={1.5} dot={false} connectNulls={false} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
      <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-indigo-500" />Historical</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 border-t border-dashed border-orange-400" />Forecast</span>
      </div>
    </div>
  );
}

function SkuRecommendationsPanel({ skus, isLoading }: { skus: LowStockSku[]; isLoading: boolean }) {
  const top5 = skus.slice(0, 5);
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Warehouse className="w-4 h-4 text-[hsl(var(--warn))]" />
        <h3 className="text-sm font-medium text-foreground">SKU Recommendations</h3>
      </div>
      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />Loading…
        </div>
      ) : top5.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">All SKUs adequately stocked.</p>
      ) : (
        <div className="space-y-2.5">
          {top5.map((s) => {
            const ratio = s.reorder_point > 0 ? s.stock_level / s.reorder_point : 1;
            const critical = s.stock_level < s.reorder_point;
            return (
              <div key={s.sku} className="text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className={cn("font-medium truncate max-w-[110px]", critical ? "text-[hsl(var(--bad))]" : "text-[hsl(var(--warn))]")}>{s.sku}</span>
                  <span className="text-muted-foreground tabular-nums">{s.stock_level}/{s.reorder_point}</span>
                </div>
                <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, ratio * 100).toFixed(0)}%`,
                      background: critical ? "hsl(var(--bad))" : "hsl(var(--warn))",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SupplyChainRiskPanel({ suppliers, avgLeadDays, isLoading }: { suppliers: SupplierSpend[]; avgLeadDays: number; isLoading: boolean }) {
  const top5 = suppliers.slice(0, 5);
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Truck className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-medium text-foreground">Supply Chain Risk</h3>
        {avgLeadDays > 0 && <span className="ml-auto text-[10px] text-muted-foreground">{avgLeadDays.toFixed(1)}d avg lead</span>}
      </div>
      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />Loading…
        </div>
      ) : top5.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">No supplier data available.</p>
      ) : (
        <div className="space-y-2">
          {top5.map((s) => (
            <div key={s.supplier_id} className="flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full bg-brand-400 shrink-0" />
              <span className="flex-1 truncate text-muted-foreground">{s.supplier_id}</span>
              <span className="tabular-nums text-foreground font-medium">{formatCurrency(s.spend)}</span>
            </div>
          ))}
          <p className="text-[10px] text-muted-foreground mt-1 pt-1 border-t border-border">
            Spend concentration in top {top5.length} suppliers
          </p>
        </div>
      )}
    </div>
  );
}

function TaskScorePanel({ score }: { score: import("@/types").TeamScore | undefined }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-medium text-foreground">Task Team Score</h3>
        <Link to="/dashboard/tasks/analytics" className="ml-auto text-xs text-primary hover:underline">
          View analytics →
        </Link>
      </div>
      {!score ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />Loading…
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-xl font-bold text-foreground">{score.done_tasks}</p>
            <p className="text-[10px] text-muted-foreground">Done</p>
          </div>
          <div>
            <p className="text-xl font-bold text-amber-600">{score.overdue_tasks}</p>
            <p className="text-[10px] text-muted-foreground">Overdue</p>
          </div>
          <div>
            <p className="text-xl font-bold text-emerald-600">
              {(score.completion_rate * 100).toFixed(0)}%
            </p>
            <p className="text-[10px] text-muted-foreground">Completion</p>
          </div>
          <div className="col-span-3 mt-1">
            <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(score.completion_rate * 100).toFixed(0)}%` }}
              />
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              {score.open_tasks} open · {score.avg_cycle_days}d avg cycle ·{" "}
              {(score.on_time_rate * 100).toFixed(0)}% on-time
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

const PRIORITY_BADGE_DASH: Record<string, string> = {
  low: "text-slate-500",
  medium: "text-blue-600",
  high: "text-amber-600",
  urgent: "text-orange-700",
  critical: "text-red-600",
};

function AiRecsPanel({ recs }: { recs: import("@/types").TaskRecommendationOut[] }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-brand-500" />
        <h3 className="text-sm font-medium text-foreground">AI Task Recommendations</h3>
        <Link to="/dashboard/tasks/analytics" className="ml-auto text-xs text-primary hover:underline">
          View all →
        </Link>
      </div>
      {recs.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">
          No pending AI recommendations. Visit Task Analytics to generate.
        </p>
      ) : (
        <div className="space-y-2">
          {recs.map((r) => (
            <div key={r.id} className="flex items-start gap-2 text-xs">
              <span className={`mt-0.5 font-semibold capitalize shrink-0 ${PRIORITY_BADGE_DASH[r.priority] ?? ""}`}>
                [{r.priority}]
              </span>
              <span className="text-foreground flex-1 truncate">{r.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
