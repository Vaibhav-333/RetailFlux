import type { UserWorkload } from "@/types";

interface Props {
  workload: UserWorkload[];
}

const CELL_COLORS = [
  "bg-emerald-100 text-emerald-800",
  "bg-yellow-100 text-yellow-800",
  "bg-amber-200 text-amber-900",
  "bg-orange-300 text-orange-900",
  "bg-red-400 text-white",
];

function heatLevel(count: number, max: number): number {
  if (max === 0) return 0;
  const ratio = count / max;
  if (ratio < 0.2) return 0;
  if (ratio < 0.4) return 1;
  if (ratio < 0.6) return 2;
  if (ratio < 0.8) return 3;
  return 4;
}

function shortId(userId: string) {
  return userId.slice(0, 8);
}

export function WorkloadHeatmap({ workload }: Props) {
  if (!workload.length) {
    return (
      <section>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Workload Heatmap
        </h2>
        <p className="text-center text-muted-foreground py-6">No active assignees.</p>
      </section>
    );
  }

  const maxOpen = Math.max(...workload.map((w) => w.open_count), 1);
  const maxOverdue = Math.max(...workload.map((w) => w.overdue_count), 1);

  const COLS: Array<{ key: keyof UserWorkload; label: string; max: number }> = [
    { key: "open_count", label: "Open", max: maxOpen },
    { key: "in_progress_count", label: "In Progress", max: maxOpen },
    { key: "blocked_count", label: "Blocked", max: maxOpen },
    { key: "overdue_count", label: "Overdue", max: maxOverdue },
  ];

  return (
    <section>
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Workload Heatmap
      </h2>
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-muted-foreground">
            <tr>
              <th className="text-left px-4 py-2 font-medium">User</th>
              {COLS.map((c) => (
                <th key={c.key} className="text-center px-3 py-2 font-medium">
                  {c.label}
                </th>
              ))}
              <th className="text-right px-4 py-2 font-medium">Total Open</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {workload.map((w) => (
              <tr key={w.user_id} className="hover:bg-muted/20 transition-colors">
                <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                  {shortId(w.user_id)}…
                </td>
                {COLS.map((c) => {
                  const val = w[c.key] as number;
                  const level = heatLevel(val, c.max);
                  return (
                    <td key={c.key} className="px-3 py-2 text-center">
                      <span
                        className={`inline-flex items-center justify-center rounded-md px-2 py-0.5 font-semibold text-xs ${CELL_COLORS[level]}`}
                      >
                        {val}
                      </span>
                    </td>
                  );
                })}
                <td className="px-4 py-2 text-right font-bold text-foreground">
                  {w.total_open}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Legend */}
        <div className="flex items-center gap-2 px-4 py-2 border-t border-border bg-muted/20">
          <span className="text-xs text-muted-foreground mr-1">Heat:</span>
          {CELL_COLORS.map((cls, i) => (
            <span
              key={i}
              className={`inline-block h-3 w-6 rounded text-xs ${cls}`}
            />
          ))}
          <span className="text-xs text-muted-foreground ml-1">low → high</span>
        </div>
      </div>
    </section>
  );
}
