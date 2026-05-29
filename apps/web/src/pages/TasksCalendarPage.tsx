import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listTasksApi } from "@/features/tasks/api";
import type { TaskOut } from "@/types";

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const PRIORITY_COLOR: Record<string, string> = {
  low: "bg-slate-200 text-slate-700",
  medium: "bg-blue-200 text-blue-800",
  high: "bg-amber-200 text-amber-900",
  urgent: "bg-orange-300 text-orange-900",
  critical: "bg-red-300 text-red-900",
};

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function getDaysInMonth(year: number, month: number): Date[] {
  const days: Date[] = [];
  const date = new Date(year, month, 1);
  while (date.getMonth() === month) {
    days.push(new Date(date));
    date.setDate(date.getDate() + 1);
  }
  return days;
}

function buildCalendarGrid(year: number, month: number): (Date | null)[] {
  const days = getDaysInMonth(year, month);
  const firstDow = days[0].getDay(); // 0=Sun
  const grid: (Date | null)[] = Array(firstDow).fill(null);
  grid.push(...days);
  // pad to full weeks
  while (grid.length % 7 !== 0) grid.push(null);
  return grid;
}

function DayCell({
  date,
  tasks,
  isToday,
}: {
  date: Date | null;
  tasks: TaskOut[];
  isToday: boolean;
}) {
  if (!date) {
    return <div className="h-28 border border-border bg-muted/20 rounded" />;
  }

  return (
    <div
      className={`h-28 border rounded p-1 overflow-hidden flex flex-col gap-0.5 transition-colors ${
        isToday
          ? "border-primary bg-primary/5"
          : "border-border bg-card hover:bg-muted/20"
      }`}
    >
      <span
        className={`text-xs font-semibold self-end px-1 rounded ${
          isToday ? "bg-primary text-primary-foreground" : "text-muted-foreground"
        }`}
      >
        {date.getDate()}
      </span>
      <div className="flex-1 overflow-hidden space-y-0.5">
        {tasks.slice(0, 3).map((t) => (
          <div
            key={t.id}
            className={`truncate rounded px-1 text-[10px] font-medium ${
              PRIORITY_COLOR[t.priority] ?? "bg-slate-200 text-slate-700"
            }`}
            title={t.title}
          >
            {t.title}
          </div>
        ))}
        {tasks.length > 3 && (
          <div className="text-[10px] text-muted-foreground px-1">
            +{tasks.length - 3} more
          </div>
        )}
      </div>
    </div>
  );
}

export function TasksCalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const { data, isLoading } = useQuery({
    queryKey: ["tasks-calendar", year, month],
    queryFn: () => listTasksApi({ size: 200 }),
  });

  const tasks = data?.items ?? [];

  // Group tasks by their due_at date
  const tasksByDate = new Map<string, TaskOut[]>();
  for (const t of tasks) {
    if (!t.due_at) continue;
    const d = new Date(t.due_at);
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    if (!tasksByDate.has(key)) tasksByDate.set(key, []);
    tasksByDate.get(key)!.push(t);
  }

  const grid = buildCalendarGrid(year, month);

  function prevMonth() {
    if (month === 0) { setMonth(11); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
  }

  function nextMonth() {
    if (month === 11) { setMonth(0); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
  }

  const monthName = new Date(year, month).toLocaleString("default", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Task Calendar</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={prevMonth}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            ←
          </button>
          <span className="text-sm font-semibold text-foreground min-w-[10rem] text-center">
            {monthName}
          </span>
          <button
            onClick={nextMonth}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            →
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1">
            {DAYS_OF_WEEK.map((d) => (
              <div
                key={d}
                className="text-center text-xs font-semibold text-muted-foreground py-1"
              >
                {d}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {grid.map((date, i) => {
              const key = date
                ? `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
                : `null-${i}`;
              const dayTasks = date ? (tasksByDate.get(key) ?? []) : [];
              const isToday = date ? isSameDay(date, today) : false;
              return (
                <DayCell key={key} date={date} tasks={dayTasks} isToday={isToday} />
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            {Object.entries(PRIORITY_COLOR).map(([p, cls]) => (
              <span key={p} className="flex items-center gap-1">
                <span className={`inline-block h-2 w-4 rounded ${cls}`} />
                <span className="capitalize">{p}</span>
              </span>
            ))}
          </div>

          {/* Tasks without due dates */}
          {tasks.filter((t) => !t.due_at).length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                Tasks without due dates ({tasks.filter((t) => !t.due_at).length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {tasks
                  .filter((t) => !t.due_at)
                  .slice(0, 20)
                  .map((t) => (
                    <span
                      key={t.id}
                      className={`rounded px-2 py-0.5 text-xs ${PRIORITY_COLOR[t.priority] ?? "bg-slate-200"}`}
                    >
                      {t.title}
                    </span>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
