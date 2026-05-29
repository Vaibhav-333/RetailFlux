import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw } from "lucide-react";
import { getDepartmentBoardApi } from "@/features/tasks/api";
import { TaskCard } from "./TaskCard";
import { TaskCreatorModal } from "./TaskCreatorModal";
import { cn } from "@/lib/utils";
import type { TaskOut, TaskStatus } from "@/types";

const COLUMNS: { id: TaskStatus; label: string; accent: string }[] = [
  { id: "open", label: "Open", accent: "border-b-gray-400" },
  { id: "in_progress", label: "In Progress", accent: "border-b-blue-500" },
  { id: "blocked", label: "Blocked", accent: "border-b-red-500" },
  { id: "in_review", label: "In Review", accent: "border-b-amber-500" },
  { id: "done", label: "Done", accent: "border-b-green-500" },
];

interface Props {
  department: string;
}

export function DepartmentTasksTab({ department }: Props) {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dept-board", department],
    queryFn: () => getDepartmentBoardApi(department, { size: 200 }),
  });

  const tasks = data?.items ?? [];

  const byStatus = COLUMNS.reduce<Record<string, TaskOut[]>>((acc, col) => {
    acc[col.id] = tasks.filter((t) => t.status === col.id);
    return acc;
  }, {});

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-destructive">
        Failed to load department tasks.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {tasks.length} task{tasks.length !== 1 ? "s" : ""} in {department}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs hover:bg-accent transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-2.5 py-1 text-xs font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Task
          </button>
        </div>
      </div>

      {/* Mini kanban */}
      <div className="overflow-x-auto">
        <div className="inline-flex gap-3 pb-3 min-w-full">
          {COLUMNS.map((col) => (
            <div key={col.id} className="flex flex-col min-w-[200px] max-w-[220px] shrink-0">
              <div
                className={cn(
                  "flex items-center justify-between px-3 py-1.5 mb-2 border-b-2 rounded-t",
                  col.accent
                )}
              >
                <span className="text-xs font-semibold">{col.label}</span>
                <span className="text-xs text-muted-foreground bg-muted rounded-full px-1.5 py-0.5">
                  {byStatus[col.id]?.length ?? 0}
                </span>
              </div>
              <div className="space-y-1.5 min-h-[80px] rounded-b border-x border-b border-dashed border-border p-1.5 bg-muted/20">
                {(byStatus[col.id] ?? []).map((task) => (
                  <TaskCard key={task.id} task={task} compact />
                ))}
                {(byStatus[col.id] ?? []).length === 0 && (
                  <p className="text-center text-xs text-muted-foreground py-4">—</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {showCreate && (
        <TaskCreatorModal
          defaultDepartments={[department]}
          onClose={() => {
            setShowCreate(false);
            qc.invalidateQueries({ queryKey: ["dept-board", department] });
          }}
        />
      )}
    </div>
  );
}
