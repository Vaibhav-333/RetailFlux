import { useQuery } from "@tanstack/react-query";
import { listTasksApi } from "@/features/tasks/api";
import type { TaskOut } from "@/types";

const PRIORITY_FILL: Record<string, string> = {
  low: "#94a3b8",
  medium: "#3b82f6",
  high: "#f59e0b",
  urgent: "#ea580c",
  critical: "#dc2626",
};

const STATUS_OPACITY: Record<string, number> = {
  todo: 0.45,
  open: 0.45,
  in_progress: 0.8,
  blocked: 0.6,
  review: 0.7,
  done: 1,
  cancelled: 0.25,
};

const ROW_H = 36;
const ROW_GAP = 4;
const LEFT_W = 180;
const BAR_H = 20;
const DAY_W = 28;

function buildTimeline(tasks: TaskOut[]) {
  const tasksWithDates = tasks.filter((t) => t.created_at && t.due_at);
  if (!tasksWithDates.length) return null;

  const allDates = tasksWithDates.flatMap((t) => [
    new Date(t.created_at),
    new Date(t.due_at!),
  ]);
  const minDate = new Date(Math.min(...allDates.map((d) => d.getTime())));
  const maxDate = new Date(Math.max(...allDates.map((d) => d.getTime())));

  minDate.setHours(0, 0, 0, 0);
  maxDate.setHours(23, 59, 59, 999);

  const totalDays =
    Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;

  return { tasksWithDates, minDate, totalDays };
}

function dayOffset(date: Date, minDate: Date): number {
  return (date.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
}

/** Compute bar geometry for a task row. */
function barGeom(task: TaskOut, minDate: Date, rowIndex: number) {
  const start = new Date(task.created_at);
  const end = new Date(task.due_at!);
  const x = dayOffset(start, minDate) * DAY_W + LEFT_W;
  const width = Math.max(DAY_W, dayOffset(end, minDate) * DAY_W - (x - LEFT_W) + DAY_W);
  const cy = rowIndex * (ROW_H + ROW_GAP) + ROW_H / 2;
  const y = cy - BAR_H / 2;
  return { x, width, y, cy };
}

function GanttBar({
  task,
  minDate,
  rowIndex,
}: {
  task: TaskOut;
  minDate: Date;
  rowIndex: number;
}) {
  const { x, width, y } = barGeom(task, minDate, rowIndex);
  const fill = PRIORITY_FILL[task.priority] ?? "#94a3b8";
  const opacity = STATUS_OPACITY[task.status] ?? 0.7;
  const isBreached = task.breached;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={BAR_H}
        rx={4}
        fill={fill}
        opacity={opacity}
        stroke={isBreached ? "#dc2626" : "transparent"}
        strokeWidth={isBreached ? 2 : 0}
      />
      <text
        x={x + 6}
        y={y + BAR_H / 2 + 4}
        fontSize={10}
        fill="white"
        fontWeight="600"
        clipPath={`url(#clip-${rowIndex})`}
      >
        {task.title}
      </text>
      <clipPath id={`clip-${rowIndex}`}>
        <rect x={x} y={y} width={width - 4} height={BAR_H} />
      </clipPath>
    </g>
  );
}

/**
 * Dependency arrow: cubic bezier from right-center of the "from" bar
 * to left-center of the "to" bar, with an arrowhead.
 */
function DependencyArrow({
  fromTask,
  toTask,
  fromRow,
  toRow,
  minDate,
}: {
  fromTask: TaskOut;
  toTask: TaskOut;
  fromRow: number;
  toRow: number;
  minDate: Date;
}) {
  const from = barGeom(fromTask, minDate, fromRow);
  const to = barGeom(toTask, minDate, toRow);

  const x1 = from.x + from.width; // right edge of from-bar
  const y1 = from.cy;
  const x2 = to.x;                // left edge of to-bar
  const y2 = to.cy;

  // Control points for a smooth cubic bezier
  const dx = Math.abs(x2 - x1) * 0.5;
  const path = `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;

  // Arrowhead triangle pointing right at (x2, y2)
  const aw = 6;
  const ah = 4;
  const arrowPoints = `${x2},${y2} ${x2 - aw},${y2 - ah} ${x2 - aw},${y2 + ah}`;

  return (
    <g opacity={0.55}>
      <path
        d={path}
        fill="none"
        stroke="#6366f1"
        strokeWidth={1.5}
        strokeDasharray="4 2"
      />
      <polygon points={arrowPoints} fill="#6366f1" />
    </g>
  );
}

export function TasksTimelinePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["tasks-timeline"],
    queryFn: () => listTasksApi({ size: 200 }),
  });

  const tasks = data?.items ?? [];
  const timeline = buildTimeline(tasks);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!timeline) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-foreground">Task Timeline</h1>
        <p className="text-center text-muted-foreground py-12">
          No tasks with both start and due dates to display.
        </p>
      </div>
    );
  }

  const { tasksWithDates, minDate, totalDays } = timeline;
  const svgW = LEFT_W + totalDays * DAY_W;
  const svgH = tasksWithDates.length * (ROW_H + ROW_GAP) + 30;
  const today = new Date();
  const todayX = dayOffset(today, minDate) * DAY_W + LEFT_W;

  // Build index: task.id → row index
  const rowByTaskId = new Map<string, number>(
    tasksWithDates.map((t, i) => [t.id, i])
  );

  // Build dependency edges from task_metadata.depends_on
  const depEdges: Array<{ fromTask: TaskOut; toTask: TaskOut; fromRow: number; toRow: number }> = [];
  for (const task of tasksWithDates) {
    const deps = task.task_metadata?.depends_on;
    if (!Array.isArray(deps)) continue;
    const toRow = rowByTaskId.get(task.id);
    if (toRow === undefined) continue;
    for (const depId of deps as string[]) {
      const fromTask = tasksWithDates.find((t) => t.id === depId);
      const fromRow = rowByTaskId.get(depId);
      if (fromTask !== undefined && fromRow !== undefined) {
        depEdges.push({ fromTask, toTask: task, fromRow, toRow });
      }
    }
  }

  // Column day labels (at most ~20 ticks)
  const dayLabels: { label: string; x: number }[] = [];
  for (let i = 0; i < totalDays; i += Math.max(1, Math.floor(totalDays / 20))) {
    const d = new Date(minDate);
    d.setDate(d.getDate() + i);
    dayLabels.push({
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      x: LEFT_W + i * DAY_W,
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Task Timeline</h1>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-6 bg-red-500" />
            Today
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded border-2 border-red-500" />
            SLA breached
          </span>
          <span className="flex items-center gap-1">
            <svg width="20" height="10" viewBox="0 0 20 10">
              <path d="M0,5 C5,5 10,5 14,5" stroke="#6366f1" strokeWidth="1.5" strokeDasharray="4 2" fill="none" />
              <polygon points="20,5 14,2 14,8" fill="#6366f1" />
            </svg>
            Dependency
          </span>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-sm overflow-auto">
        <svg
          width={svgW}
          height={svgH}
          className="font-sans"
          style={{ minWidth: "100%" }}
        >
          {/* Background stripes */}
          {tasksWithDates.map((_, i) => (
            <rect
              key={i}
              x={0}
              y={i * (ROW_H + ROW_GAP)}
              width={svgW}
              height={ROW_H}
              fill={i % 2 === 0 ? "transparent" : "rgba(0,0,0,0.02)"}
            />
          ))}

          {/* Vertical grid lines */}
          {dayLabels.map((dl) => (
            <g key={dl.x}>
              <line
                x1={dl.x}
                y1={0}
                x2={dl.x}
                y2={svgH - 20}
                stroke="currentColor"
                strokeOpacity={0.08}
                strokeWidth={1}
              />
              <text x={dl.x + 2} y={svgH - 5} fontSize={9} fill="currentColor" opacity={0.4}>
                {dl.label}
              </text>
            </g>
          ))}

          {/* Today line */}
          {todayX >= LEFT_W && todayX <= svgW && (
            <line
              x1={todayX}
              y1={0}
              x2={todayX}
              y2={svgH - 20}
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="4 2"
            />
          )}

          {/* Dependency arrows (drawn BEFORE bars so bars render on top) */}
          {depEdges.map(({ fromTask, toTask, fromRow, toRow }, idx) => (
            <DependencyArrow
              key={`dep-${idx}`}
              fromTask={fromTask}
              toTask={toTask}
              fromRow={fromRow}
              toRow={toRow}
              minDate={minDate}
            />
          ))}

          {/* Row labels and bars */}
          {tasksWithDates.map((task, i) => {
            const y = i * (ROW_H + ROW_GAP) + ROW_H / 2 + 4;
            return (
              <g key={task.id}>
                <text x={8} y={y} fontSize={11} fill="currentColor" opacity={0.8}>
                  {task.title.length > 20 ? task.title.slice(0, 19) + "…" : task.title}
                </text>
                <GanttBar task={task} minDate={minDate} rowIndex={i} />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Priority legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        {Object.entries(PRIORITY_FILL).map(([p, color]) => (
          <span key={p} className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-5 rounded" style={{ backgroundColor: color }} />
            <span className="capitalize">{p}</span>
          </span>
        ))}
        <span className="flex items-center gap-1.5 ml-4 text-muted-foreground">
          Opacity: dark = done/active · light = todo/cancelled
        </span>
      </div>

      {depEdges.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {depEdges.length} dependency link{depEdges.length !== 1 ? "s" : ""} shown.
          Set <code className="bg-muted rounded px-1">task_metadata.depends_on</code> to add more.
        </p>
      )}
    </div>
  );
}
