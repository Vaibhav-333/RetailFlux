import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle,
  Clock,
  ClipboardList,
  Database,
  DollarSign,
  ListChecks,
  RefreshCw,
  Timer,
  Trash2,
  Zap,
} from "lucide-react";
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
  getAiUsageApi,
  getAuditLogsApi,
  getCeleryStatsApi,
  getObservabilityDashboardApi,
} from "@/features/observability/api";
import { getCacheStatsApi, invalidateAnalyticsCacheApi, warmCacheApi } from "@/features/cache/api";
import type { AuditLogEntry, CeleryTaskStat, EndpointStat } from "@/types";
import { cn } from "@/lib/utils";

// ─── Shared KPI card ──────────────────────────────────────────────────────────
function KpiCard({
  label,
  value,
  icon: Icon,
  accent = "blue",
  sub,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  accent?: "blue" | "red" | "amber" | "emerald";
  sub?: string;
}) {
  const colours: Record<string, string> = {
    blue:    "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
    red:     "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400",
    amber:   "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400",
    emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400",
  };
  return (
    <div className="rounded-xl border border-border bg-card p-5 flex gap-4 items-start">
      <div className={`rounded-lg p-2.5 shrink-0 ${colours[accent]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-foreground mt-0.5 truncate">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Method badge ─────────────────────────────────────────────────────────────
function MethodBadge({ method }: { method: string }) {
  const colours: Record<string, string> = {
    GET:    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    POST:   "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    PATCH:  "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    DELETE: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    PUT:    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  };
  return (
    <span className={`inline-block text-[10px] font-bold px-1.5 py-0.5 rounded ${colours[method] ?? "bg-muted text-muted-foreground"}`}>
      {method}
    </span>
  );
}

// ─── Traffic tab ─────────────────────────────────────────────────────────────
function TrafficTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["observability", "traffic"],
    queryFn: getObservabilityDashboardApi,
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spinner />;
  if (isError || !data) return <ErrorMsg />;

  const chartData = data.hourly_volume.map((b) => ({
    hour: b.hour.slice(11, 16),
    Requests: b.requests,
    Errors: b.errors,
  }));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Requests" value={data.total_requests_24h.toLocaleString()} icon={Zap} accent="blue" sub="last 24 h" />
        <KpiCard
          label="Errors"
          value={data.error_count_24h.toLocaleString()}
          icon={AlertTriangle}
          accent={data.error_count_24h > 0 ? "red" : "emerald"}
          sub={`${(data.error_rate_24h * 100).toFixed(2)}% error rate`}
        />
        <KpiCard
          label="Avg Latency"
          value={`${data.avg_duration_ms_24h.toFixed(0)} ms`}
          icon={Clock}
          accent={data.avg_duration_ms_24h > 500 ? "amber" : "blue"}
          sub="mean response time"
        />
        <KpiCard
          label="P95 Latency"
          value={`${data.p95_duration_ms_24h.toFixed(0)} ms`}
          icon={Timer}
          accent={data.p95_duration_ms_24h > 1000 ? "red" : data.p95_duration_ms_24h > 500 ? "amber" : "emerald"}
          sub="95th percentile"
        />
      </div>

      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Hourly Traffic (last 24 h)</h2>
        {chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-10">No traffic recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gReq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gErr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="Requests" stroke="#6366f1" fill="url(#gReq)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="Errors" stroke="#ef4444" fill="url(#gErr)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <EndpointsTable rows={data.top_endpoints} />
    </div>
  );
}

function EndpointsTable({ rows }: { rows: EndpointStat[] }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-semibold text-foreground mb-4">Top Endpoints (last 24 h)</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">No requests recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase tracking-wide">
                <th className="pb-2 pr-4 font-medium">Endpoint</th>
                <th className="pb-2 pr-4 font-medium">Method</th>
                <th className="pb-2 pr-4 font-medium text-right">Requests</th>
                <th className="pb-2 pr-4 font-medium text-right">Avg ms</th>
                <th className="pb-2 font-medium text-right">Error rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rows.map((r) => (
                <tr key={`${r.method}-${r.endpoint}`} className="hover:bg-muted/30 transition-colors">
                  <td className="py-2.5 pr-4 font-mono text-xs max-w-[240px] truncate">{r.endpoint}</td>
                  <td className="py-2.5 pr-4"><MethodBadge method={r.method} /></td>
                  <td className="py-2.5 pr-4 text-right tabular-nums">{r.request_count.toLocaleString()}</td>
                  <td className="py-2.5 pr-4 text-right tabular-nums">
                    <span className={r.avg_duration_ms > 500 ? "text-amber-600 font-medium" : ""}>{r.avg_duration_ms.toFixed(0)}</span>
                  </td>
                  <td className="py-2.5 text-right tabular-nums">
                    <span className={r.error_rate > 0.05 ? "text-red-600 font-semibold" : "text-muted-foreground"}>
                      {(r.error_rate * 100).toFixed(1)}%
                    </span>
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

// ─── Tasks tab ────────────────────────────────────────────────────────────────
function TasksTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["observability", "celery"],
    queryFn: getCeleryStatsApi,
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spinner />;
  if (isError || !data) return <ErrorMsg />;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Tasks Run" value={data.total_tasks_24h.toLocaleString()} icon={ListChecks} accent="blue" sub="last 24 h" />
        <KpiCard
          label="Succeeded"
          value={data.success_count_24h.toLocaleString()}
          icon={CheckCircle}
          accent="emerald"
          sub={`${(data.success_rate_24h * 100).toFixed(1)}% success rate`}
        />
        <KpiCard
          label="Failed"
          value={data.failure_count_24h.toLocaleString()}
          icon={AlertTriangle}
          accent={data.failure_count_24h > 0 ? "red" : "emerald"}
          sub="last 24 h"
        />
        <KpiCard
          label="Avg Duration"
          value={data.avg_duration_ms_24h >= 1000
            ? `${(data.avg_duration_ms_24h / 1000).toFixed(1)} s`
            : `${data.avg_duration_ms_24h.toFixed(0)} ms`}
          icon={Timer}
          accent={data.avg_duration_ms_24h > 30000 ? "amber" : "blue"}
          sub="per task"
        />
      </div>

      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">By Task (last 24 h)</h2>
        {data.by_task.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No tasks recorded. Celery worker may not be running.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase tracking-wide">
                  <th className="pb-2 pr-4 font-medium">Task</th>
                  <th className="pb-2 pr-4 font-medium text-right">Total</th>
                  <th className="pb-2 pr-4 font-medium text-right">Success</th>
                  <th className="pb-2 pr-4 font-medium text-right">Failures</th>
                  <th className="pb-2 pr-4 font-medium text-right">Success rate</th>
                  <th className="pb-2 font-medium text-right">Avg duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.by_task.map((t: CeleryTaskStat) => (
                  <tr key={t.task_name} className="hover:bg-muted/30 transition-colors">
                    <td className="py-2.5 pr-4 font-mono text-xs">{t.task_name}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums">{t.total}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-emerald-600">{t.success}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums">
                      <span className={t.failure > 0 ? "text-red-600 font-semibold" : "text-muted-foreground"}>{t.failure}</span>
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums">
                      <span className={t.success_rate < 0.9 ? "text-red-600 font-semibold" : ""}>
                        {(t.success_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                      {t.avg_duration_ms >= 1000 ? `${(t.avg_duration_ms / 1000).toFixed(1)}s` : `${t.avg_duration_ms.toFixed(0)}ms`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data.recent_failures.length > 0 && (
        <div className="rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/50 dark:bg-red-900/10 p-5">
          <h2 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Recent Failures
          </h2>
          <ul className="space-y-2">
            {data.recent_failures.map((f, i) => (
              <li key={i} className="text-sm flex flex-col gap-0.5">
                <span className="font-mono text-xs font-semibold text-foreground">{f.task_name}</span>
                <span className="text-muted-foreground text-xs">{f.error ?? "No error message"}</span>
                <span className="text-muted-foreground text-[11px]">{new Date(f.timestamp).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Audit tab ────────────────────────────────────────────────────────────────
function AuditTab() {
  const [page, setPage] = useState(1);
  const [resourceFilter, setResourceFilter] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit", "logs", page, resourceFilter],
    queryFn: () => getAuditLogsApi({ page, size: 20, resource: resourceFilter || undefined }),
    refetchInterval: 30_000,
  });

  if (isLoading) return <Spinner />;
  if (isError || !data) return <ErrorMsg />;

  const totalPages = Math.ceil(data.total / data.pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Filter by resource (e.g. users, uploads)…"
          value={resourceFilter}
          onChange={(e) => { setResourceFilter(e.target.value); setPage(1); }}
          className="flex-1 max-w-xs px-3 py-1.5 text-sm rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <span className="text-xs text-muted-foreground">{data.total.toLocaleString()} entries</span>
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {data.items.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-10">
            No audit entries yet. They appear once mutating API calls (POST/PATCH/PUT/DELETE) are made.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40">
                <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase tracking-wide">
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">Method</th>
                  <th className="px-4 py-2.5 font-medium">Resource</th>
                  <th className="px-4 py-2.5 font-medium">Resource ID</th>
                  <th className="px-4 py-2.5 font-medium">User</th>
                  <th className="px-4 py-2.5 font-medium">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.items.map((entry: AuditLogEntry) => (
                  <tr key={entry.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5"><MethodBadge method={entry.action} /></td>
                    <td className="px-4 py-2.5 font-mono text-xs">{entry.resource}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground max-w-[120px] truncate">
                      {entry.resource_id ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground max-w-[140px] truncate">
                      {entry.user_id ? entry.user_id.slice(0, 8) + "…" : "anonymous"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{entry.ip ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-md border border-border text-sm disabled:opacity-40 hover:bg-accent transition-colors"
          >
            Previous
          </button>
          <span className="text-muted-foreground">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 rounded-md border border-border text-sm disabled:opacity-40 hover:bg-accent transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Cache tab ────────────────────────────────────────────────────────────────
const DEPTS = ["sales", "marketing", "operations", "finance", "procurement"] as const;

function CacheTab() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["observability", "cache"],
    queryFn: getCacheStatsApi,
    refetchInterval: 30_000,
  });

  const invalidate = useMutation({
    mutationFn: (dept?: string) => invalidateAnalyticsCacheApi(dept),
    onSuccess: () => { void refetch(); },
  });

  const warm = useMutation({
    mutationFn: () => warmCacheApi(),
    onSuccess: () => { void refetch(); },
  });

  if (isLoading) return <Spinner />;
  if (isError || !data) return <ErrorMsg />;

  const categoryRows = Object.entries(data.by_category).sort((a, b) => b[1] - a[1]);
  const m = data.metrics;
  const h = data.health;

  return (
    <div className="space-y-5">
      {/* Health + Metrics KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Redis Status"
          value={h.status === "healthy" ? "Healthy" : "Unhealthy"}
          icon={Database}
          accent={h.status === "healthy" ? "emerald" : "red"}
          sub={h.latency_ms >= 0 ? `${h.latency_ms}ms latency` : h.error ?? "unreachable"}
        />
        <KpiCard
          label="Hit Rate"
          value={m.total_lookups > 0 ? `${(m.hit_rate * 100).toFixed(1)}%` : "—"}
          icon={Zap}
          accent={m.hit_rate >= 0.7 ? "emerald" : m.hit_rate >= 0.4 ? "amber" : "red"}
          sub={`${m.hits.toLocaleString()} hits / ${m.total_lookups.toLocaleString()} lookups`}
        />
        <KpiCard
          label="Total Keys"
          value={data.total_keys.toLocaleString()}
          icon={Database}
          accent="blue"
          sub={`${categoryRows.length} namespaces`}
        />
        <KpiCard
          label="Stale Serves"
          value={m.stale_hits.toLocaleString()}
          icon={Timer}
          accent={m.stale_hits > 0 ? "amber" : "emerald"}
          sub="stale-while-revalidate"
        />
      </div>

      {/* Breakdown table */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-foreground">Cache Keys by Namespace</h2>
          <button
            onClick={() => void refetch()}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
        {categoryRows.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Cache is empty. Data will be cached after the first analytics request.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase tracking-wide">
                  <th className="pb-2 pr-4 font-medium">Namespace</th>
                  <th className="pb-2 text-right font-medium">Keys</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {categoryRows.map(([cat, count]) => (
                  <tr key={cat} className="hover:bg-muted/30 transition-colors">
                    <td className="py-2.5 pr-4 font-mono text-xs">{cat}</td>
                    <td className="py-2.5 text-right tabular-nums font-medium">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Warm + Invalidation controls */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-1">Cache Management</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Invalidate stale entries or pre-warm the cache for instant dashboard loads.
        </p>
        <div className="flex flex-wrap gap-2">
          {DEPTS.map((dept) => (
            <button
              key={dept}
              disabled={invalidate.isPending}
              onClick={() => void invalidate.mutate(dept)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border hover:bg-accent transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3 h-3" />
              {dept.charAt(0).toUpperCase() + dept.slice(1)}
            </button>
          ))}
          <button
            disabled={invalidate.isPending}
            onClick={() => {
              void invalidate.mutate(undefined);
              void qc.invalidateQueries({ queryKey: ["sales-kpis"] });
              void qc.invalidateQueries({ queryKey: ["marketing-kpis"] });
              void qc.invalidateQueries({ queryKey: ["operations-kpis"] });
              void qc.invalidateQueries({ queryKey: ["finance-kpis"] });
              void qc.invalidateQueries({ queryKey: ["procurement-kpis"] });
              void qc.invalidateQueries({ queryKey: ["dashboard"] });
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-3 h-3" />
            Invalidate All
          </button>
          <button
            disabled={warm.isPending}
            onClick={() => void warm.mutate()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
          >
            <Zap className="w-3 h-3" />
            {warm.isPending ? "Warming…" : "Warm Cache"}
          </button>
        </div>
        {invalidate.isSuccess && (
          <p className="mt-3 text-xs text-emerald-600 dark:text-emerald-400">
            Invalidated {invalidate.data?.deleted ?? 0} key{(invalidate.data?.deleted ?? 0) !== 1 ? "s" : ""}.
            {invalidate.data?.warmed && ` Warmed: ${Object.entries(invalidate.data.warmed).filter(([,v]) => v).length}/5 depts.`}
          </p>
        )}
        {warm.isSuccess && (
          <p className="mt-3 text-xs text-emerald-600 dark:text-emerald-400">
            Cache warmed: {Object.entries(warm.data?.warmed ?? {}).filter(([,v]) => v).length}/5 departments pre-loaded.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── AI Usage tab ─────────────────────────────────────────────────────────────
function AiUsageTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["observability", "ai-usage"],
    queryFn: getAiUsageApi,
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spinner />;
  if (isError || !data) return <ErrorMsg />;

  const fmt = (n: number) => n.toLocaleString();
  const providers = Object.entries(data.calls_by_provider).sort(([, a], [, b]) => b - a);

  return (
    <div className="space-y-5">
      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total LLM Calls"
          value={fmt(data.total_calls_24h)}
          icon={BrainCircuit}
          accent="blue"
          sub="last 24 h"
        />
        <KpiCard
          label="Total Tokens"
          value={fmt(data.total_tokens_24h)}
          icon={Zap}
          accent="amber"
          sub={`${fmt(data.total_tokens_in_24h)} in · ${fmt(data.total_tokens_out_24h)} out`}
        />
        <KpiCard
          label="Est. Cost"
          value={`$${data.total_cost_usd_24h.toFixed(4)}`}
          icon={DollarSign}
          accent={data.total_cost_usd_24h > 0.01 ? "amber" : "emerald"}
          sub="USD (informational)"
        />
        <KpiCard
          label="Avg Latency"
          value={`${data.avg_latency_ms_24h.toFixed(0)} ms`}
          icon={Timer}
          accent={data.avg_latency_ms_24h > 2000 ? "red" : data.avg_latency_ms_24h > 1000 ? "amber" : "emerald"}
          sub={`${(data.cache_hit_rate_24h * 100).toFixed(1)}% cache hit rate`}
        />
      </div>

      {/* Provider breakdown */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Calls by Provider (last 24 h)</h2>
        {providers.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No AI calls recorded yet. Use the Copilot or trigger an insight refresh to see data here.
          </p>
        ) : (
          <div className="space-y-3">
            {providers.map(([provider, count]) => {
              const pct = data.total_calls_24h > 0
                ? Math.round((count / data.total_calls_24h) * 100)
                : 0;
              const colourMap: Record<string, string> = {
                gemini:   "bg-indigo-500",
                groq:     "bg-emerald-500",
                cached:   "bg-sky-500",
                fallback: "bg-amber-500",
              };
              const bar = colourMap[provider] ?? "bg-muted-foreground";
              return (
                <div key={provider}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-foreground capitalize">{provider}</span>
                    <span className="text-xs text-muted-foreground">{fmt(count)} calls ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Token breakdown */}
      {data.total_calls_24h > 0 && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">Token Usage Detail</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Input</p>
              <p className="text-xl font-bold text-foreground">{fmt(data.total_tokens_in_24h)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Output</p>
              <p className="text-xl font-bold text-foreground">{fmt(data.total_tokens_out_24h)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Total</p>
              <p className="text-xl font-bold text-indigo-500">{fmt(data.total_tokens_24h)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Shared helpers ───────────────────────────────────────────────────────────
function Spinner() {
  return <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">Loading…</div>;
}
function ErrorMsg() {
  return <div className="flex items-center justify-center h-40 text-red-500 text-sm">Failed to load data. You may not have permission.</div>;
}

// ─── Tab definitions ──────────────────────────────────────────────────────────
type Tab = "traffic" | "tasks" | "audit" | "cache" | "ai";
const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "traffic", label: "Traffic",      icon: Activity },
  { id: "tasks",   label: "Celery Tasks", icon: ListChecks },
  { id: "audit",   label: "Audit Log",    icon: ClipboardList },
  { id: "cache",   label: "Cache",        icon: Database },
  { id: "ai",      label: "AI Usage",     icon: BrainCircuit },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<Tab>("traffic");

  return (
    <div className="space-y-5 p-1">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Activity className="w-6 h-6 text-brand-600" />
        <div>
          <h1 className="text-xl font-bold text-foreground">System Observability</h1>
          <p className="text-sm text-muted-foreground">Request metrics · Task health · Audit trail</p>
        </div>
        <span className="ml-auto inline-flex items-center gap-1.5 text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-2.5 py-1 rounded-full font-medium">
          <CheckCircle className="w-3.5 h-3.5" />
          Live
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              activeTab === id
                ? "border-brand-600 text-brand-700 dark:text-brand-400"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "traffic" && <TrafficTab />}
      {activeTab === "tasks"   && <TasksTab />}
      {activeTab === "audit"   && <AuditTab />}
      {activeTab === "cache"   && <CacheTab />}
      {activeTab === "ai"      && <AiUsageTab />}
    </div>
  );
}
