import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowRight, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  getProfitForecastApi,
  getProfitAttributionApi,
  getProfitLeversApi,
} from "@/features/profit/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { Waterfall } from "@/components/charts/Waterfall";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

const EFFORT_COLOR: Record<string, string> = {
  low: "text-green-400",
  medium: "text-amber-400",
  high: "text-red-400",
};

const CONFIDENCE_COLOR: Record<string, string> = {
  high: "bg-green-500/20 text-green-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-slate-500/20 text-slate-400",
};

type Period = "7d" | "28d" | "90d";

export function ProfitIntelligencePage() {
  const [period, setPeriod] = useState<Period>("28d");
  const navigate = useNavigate();

  const forecastQ = useQuery({
    queryKey: ["profit-forecast"],
    queryFn: getProfitForecastApi,
    staleTime: 1000 * 60 * 30,
  });

  const attributionQ = useQuery({
    queryKey: ["profit-attribution", period],
    queryFn: () => getProfitAttributionApi(period),
  });

  const leversQ = useQuery({
    queryKey: ["profit-levers"],
    queryFn: getProfitLeversApi,
    staleTime: 1000 * 60 * 5,
  });

  const isLoading = forecastQ.isLoading || attributionQ.isLoading || leversQ.isLoading;

  const forecast = forecastQ.data;
  const attribution = attributionQ.data;
  const levers = leversQ.data;

  // Combine historical + forecast for the chart (last 30 hist + 90 forecast)
  const chartData = [
    ...(forecast?.historical.slice(-30) ?? []).map((p) => ({
      date: p.date,
      gross_profit: p.gross_profit,
      type: "historical",
    })),
    ...(forecast?.forecast ?? []).map((p) => ({
      date: p.date,
      forecast_gp: p.gross_profit,
      gp_lower: p.gp_lower,
      gp_upper: p.gp_upper,
      type: "forecast",
    })),
  ];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-violet-400" />
            Profit Intelligence
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            AI-powered profit forecast, attribution, and ranked action levers
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(["7d", "28d", "90d"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
                period === p
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-card border" />
          ))}
        </div>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="90d Forecast Revenue"
              value={fmt(forecast?.summary.forecast_90d_revenue ?? 0)}
              isAIForecasted
              subline="next 90 days"
            />
            <KpiCard
              label="90d Forecast Gross Profit"
              value={fmt(forecast?.summary.forecast_90d_gross_profit ?? 0)}
              isAIForecasted
              valueVariant={(forecast?.summary.forecast_90d_gross_profit ?? 0) >= 0 ? "ok" : "bad"}
            />
            <KpiCard
              label="Forecast Gross Margin"
              value={`${forecast?.summary.forecast_gross_margin_pct.toFixed(1) ?? "–"}%`}
              subline={`Confidence: ${forecast?.summary.confidence ?? "–"}`}
              isAIForecasted
            />
            <KpiCard
              label="Potential GP Lift"
              value={fmt(levers?.total_potential_lift ?? 0)}
              subline={`${levers?.levers.length ?? 0} action levers`}
              valueVariant="ok"
            />
          </div>

          {/* Forecast chart */}
          <div className="rounded-lg border bg-card p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold">90-Day Gross Profit Forecast</h2>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  CONFIDENCE_COLOR[forecast?.summary.confidence ?? "low"]
                }`}
              >
                {forecast?.summary.confidence ?? "–"} confidence ·{" "}
                ±{forecast?.summary.ci_width_pct.toFixed(0) ?? "–"}% CI
              </span>
            </div>
            {chartData.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Not enough data for forecast.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="fcstGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
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
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    formatter={(v: number) => fmt(v)}
                    labelFormatter={(l) => `Date: ${l}`}
                  />
                  <Legend verticalAlign="top" height={28} />
                  <Area
                    type="monotone"
                    dataKey="gross_profit"
                    stroke="#22c55e"
                    fill="url(#histGrad)"
                    strokeWidth={2}
                    dot={false}
                    name="Historical GP"
                    connectNulls
                  />
                  <Area
                    type="monotone"
                    dataKey="gp_lower"
                    stroke="transparent"
                    fill="url(#fcstGrad)"
                    strokeWidth={0}
                    dot={false}
                    name="CI Lower"
                    connectNulls
                    legendType="none"
                  />
                  <Area
                    type="monotone"
                    dataKey="gp_upper"
                    stroke="#a78bfa"
                    fill="url(#fcstGrad)"
                    strokeWidth={0}
                    dot={false}
                    name="CI Upper"
                    legendType="none"
                    connectNulls
                  />
                  <Area
                    type="monotone"
                    dataKey="forecast_gp"
                    stroke="#a78bfa"
                    fill="transparent"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    dot={false}
                    name="Forecast GP"
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Attribution waterfall + levers */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Waterfall */}
            <div className="rounded-lg border bg-card p-5 shadow-sm">
              <h2 className="mb-1 text-base font-semibold">GP Attribution Waterfall</h2>
              <p className="text-xs text-muted-foreground mb-4">
                {attribution
                  ? `${fmt(attribution.previous.total_gp)} → ${fmt(attribution.current.total_gp)} (${
                      attribution.total_delta >= 0 ? "+" : ""
                    }${fmt(attribution.total_delta)})`
                  : "Loading…"}
              </p>
              {attribution ? (
                <Waterfall
                  data={attribution.waterfall}
                  height={260}
                  formatValue={(v) => `$${Math.abs(v) >= 1000 ? (v / 1000).toFixed(0) + "k" : v.toFixed(0)}`}
                />
              ) : (
                <div className="h-52 flex items-center justify-center text-muted-foreground text-sm">
                  Loading attribution…
                </div>
              )}
            </div>

            {/* Levers */}
            <div className="rounded-lg border bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold">Top Profit Levers</h2>
                <span className="text-xs text-muted-foreground">
                  {levers ? `${levers.levers.length} levers · ${fmt(levers.total_potential_lift)} potential` : ""}
                </span>
              </div>
              {levers?.levers.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No levers computed yet — upload more data.
                </p>
              ) : (
                <div className="space-y-3">
                  {(levers?.levers ?? []).slice(0, 6).map((lever) => (
                    <div
                      key={lever.id}
                      className="flex items-start gap-3 rounded-lg border border-border/50 p-3 hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium truncate">{lever.title}</span>
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded-full ${CONFIDENCE_COLOR[lever.confidence]}`}
                          >
                            {lever.confidence}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                          {lever.description}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs text-muted-foreground">
                            Effort:{" "}
                            <span className={EFFORT_COLOR[lever.effort]}>{lever.effort}</span>
                          </span>
                          <span className="text-xs text-muted-foreground">
                            Category: {lever.category}
                          </span>
                        </div>
                      </div>
                      <div className="flex-shrink-0 text-right">
                        <div className="text-sm font-semibold text-green-400">
                          +{fmt(lever.estimated_gp_lift)}
                        </div>
                        <button
                          onClick={() => {
                            if (lever.action === "view_reorder_queue") navigate("/dashboard/inventory");
                            else if (lever.action === "view_pricing_suggestions") navigate("/dashboard/finance?view=pricing");
                            else if (lever.action === "view_dead_stock") navigate("/dashboard/inventory");
                            else toast.info("Opening scenario planner…");
                          }}
                          className="text-xs text-primary hover:underline flex items-center gap-0.5 mt-1"
                        >
                          Simulate <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
