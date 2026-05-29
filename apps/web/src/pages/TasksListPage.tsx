import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Grid3x3,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { listTasksApi, deleteTaskApi } from "@/features/tasks/api";
import { TaskCreatorModal } from "@/components/tasks/TaskCreatorModal";
import { cn } from "@/lib/utils";
import type { TaskOut, TaskPriority, TaskStatus } from "@/types";

const STATUS_OPTIONS: TaskStatus[] = [
  "open", "in_progress", "blocked", "in_review", "done", "cancelled",
];

const STATUS_BADGE: Record<TaskStatus, string> = {
  open: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  in_progress: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  blocked: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  in_review: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  done: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  cancelled: "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500",
};

const PRIORITY_BADGE: Record<TaskPriority, string> = {
  low: "text-gray-500",
  medium: "text-blue-600 dark:text-blue-400",
  high: "text-amber-600 dark:text-amber-400",
  urgent: "text-orange-600 dark:text-orange-400",
  critical: "text-red-600 dark:text-red-400 font-bold",
};

export function TasksListPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const SIZE = 25;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tasks", statusFilter, page],
    queryFn: () =>
      listTasksApi({ status: statusFilter || undefined, page, size: SIZE }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteTaskApi(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Task deleted");
    },
    onError: () => toast.error("Failed to delete task"),
  });

  const totalPages = data ? Math.ceil(data.total / SIZE) : 1;

  return (
    <div className="space-y-5 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <div className="flex items-center gap-2">
          <Link
            to="/dashboard/tasks/board"
            className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors"
          >
            <Grid3x3 className="w-3.5 h-3.5" />
            Board
          </Link>
          <button
            onClick={() => void refetch()}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-3 py-1 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Task
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => { setStatusFilter(""); setPage(1); }}
          className={cn(
            "rounded-full px-3 py-0.5 text-xs font-medium border transition-colors",
            statusFilter === ""
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-background border-border hover:border-primary text-muted-foreground"
          )}
        >
          All
        </button>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={cn(
              "rounded-full px-3 py-0.5 text-xs font-medium border transition-colors capitalize",
              statusFilter === s
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background border-border hover:border-primary text-muted-foreground"
            )}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : isError ? (
          <div className="flex h-40 items-center justify-center text-destructive text-sm">
            Failed to load tasks.
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col h-40 items-center justify-center gap-2 text-muted-foreground">
            <p className="text-sm">No tasks yet.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="text-xs text-primary hover:underline"
            >
              Create your first task
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                <th className="px-4 py-2 font-medium">Title</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Priority</th>
                <th className="px-4 py-2 font-medium">Departments</th>
                <th className="px-4 py-2 font-medium">Due</th>
                <th className="px-4 py-2 font-medium">SLA</th>
                <th className="px-4 py-2 font-medium w-10" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((task: TaskOut) => (
                <tr
                  key={task.id}
                  className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-2.5 max-w-xs">
                    <div className="flex items-start gap-1.5">
                      {task.breached && (
                        <AlertTriangle className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
                      )}
                      <span className="line-clamp-1 font-medium">{task.title}</span>
                    </div>
                    {task.description && (
                      <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                        {task.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={cn(
                        "rounded px-2 py-0.5 text-xs font-medium capitalize",
                        STATUS_BADGE[task.status]
                      )}
                    >
                      {task.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={cn("text-xs capitalize", PRIORITY_BADGE[task.priority])}>
                      {task.priority}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">
                    {task.departments.join(", ") || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">
                    {task.due_at ? new Date(task.due_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">
                    {task.sla_hours ? `${task.sla_hours}h` : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      onClick={() => {
                        if (confirm("Delete this task?")) deleteMut.mutate(task.id);
                      }}
                      className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > SIZE && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted-foreground">
            {(page - 1) * SIZE + 1}–{Math.min(page * SIZE, data.total)} of{" "}
            {data.total} tasks
          </p>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded border px-2.5 py-1 text-xs hover:bg-accent disabled:opacity-50 transition-colors"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded border px-2.5 py-1 text-xs hover:bg-accent disabled:opacity-50 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {showCreate && <TaskCreatorModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
