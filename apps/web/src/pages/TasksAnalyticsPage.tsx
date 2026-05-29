import { useQuery } from "@tanstack/react-query";
import { getAnalyticsDashboardApi } from "@/features/tasks/api";
import { WorkloadHeatmap } from "@/components/tasks/WorkloadHeatmap";
import { AIRecommendationsInbox } from "@/components/tasks/AIRecommendationsInbox";

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 flex flex-col gap-1 shadow-sm">
      <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
      <span className="text-2xl font-bold text-foreground">{value}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

const PRIORITY_COLOR: Record<string, string> = {
  low: "bg-slate-400",
  medium: "bg-blue-500",
  high: "bg-amber-500",
  urgent: "bg-orange-600",
  critical: "bg-red-600",
};

export function TasksAnalyticsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["tasks-analytics-dashboard"],
    queryFn: getAnalyticsDashboardApi,
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Failed to load analytics. Please try again.
      </div>
    );
  }

  const { team_score: ts, department_productivity: depts, bottlenecks } = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-foreground">Task Analytics</h1>

      {/* Team Score row */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Team Score
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Total" value={ts.total_tasks} />
          <StatCard label="Done" value={ts.done_tasks} />
          <StatCard label="Open" value={ts.open_tasks} />
          <StatCard label="Overdue" value={ts.overdue_tasks} />
          <StatCard
            label="Completion"
            value={`${(ts.completion_rate * 100).toFixed(1)}%`}
          />
          <StatCard
            label="On-time"
            value={`${(ts.on_time_rate * 100).toFixed(1)}%`}
          />
          <StatCard
            label="Avg Cycle"
            value={`${ts.avg_cycle_days}d`}
          />
        </div>
      </section>

      {/* Department Productivity */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Department Productivity
        </h2>
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Department</th>
                <th className="text-right px-4 py-2 font-medium">Total</th>
                <th className="text-right px-4 py-2 font-medium">Done</th>
                <th className="text-right px-4 py-2 font-medium">In Progress</th>
                <th className="text-right px-4 py-2 font-medium">Blocked</th>
                <th className="text-right px-4 py-2 font-medium">Completion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {depts.map((d) => (
                <tr key={d.department} className="hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-2 font-medium capitalize">{d.department}</td>
                  <td className="px-4 py-2 text-right">{d.total}</td>
                  <td className="px-4 py-2 text-right text-emerald-600 font-medium">{d.done}</td>
                  <td className="px-4 py-2 text-right text-blue-600">{d.in_progress}</td>
                  <td className="px-4 py-2 text-right text-red-500">{d.blocked}</td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-24 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${(d.completion_rate * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">
                        {(d.completion_rate * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
              {depts.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No department data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Bottlenecks */}
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Bottlenecks (stuck &gt; 24h)
        </h2>
        <div className="space-y-2">
          {bottlenecks.map((b) => (
            <div
              key={b.task_id}
              className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3 shadow-sm"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span
                  className={`inline-block h-2 w-2 rounded-full shrink-0 ${PRIORITY_COLOR[b.priority] ?? "bg-slate-400"}`}
                />
                <div className="min-w-0">
                  <p className="font-medium text-sm text-foreground truncate">{b.title}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {b.departments.join(", ")} · {b.status}
                    {b.breached && (
                      <span className="ml-2 text-red-500 font-semibold">SLA breached</span>
                    )}
                  </p>
                </div>
              </div>
              <span className="shrink-0 ml-4 text-sm font-semibold text-amber-600">
                {b.days_stuck}d stuck
              </span>
            </div>
          ))}
          {bottlenecks.length === 0 && (
            <p className="text-center text-muted-foreground py-6">No bottlenecks — great work!</p>
          )}
        </div>
      </section>

      {/* Workload Heatmap */}
      <WorkloadHeatmap workload={data.workload} />

      {/* AI Recommendations */}
      <AIRecommendationsInbox />
    </div>
  );
}
