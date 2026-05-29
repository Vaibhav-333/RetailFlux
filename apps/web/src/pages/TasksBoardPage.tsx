import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Link, } from "react-router-dom";
import { List, Plus } from "lucide-react";
import { toast } from "sonner";
import { listTasksApi, transitionTaskApi } from "@/features/tasks/api";
import { TaskCard } from "@/components/tasks/TaskCard";
import { TaskCreatorModal } from "@/components/tasks/TaskCreatorModal";
import { cn } from "@/lib/utils";
import type { TaskOut, TaskStatus } from "@/types";

// ── Board column configuration ─────────────────────────────────────────────────

interface Column {
  id: TaskStatus;
  label: string;
  headerClass: string;
}

const COLUMNS: Column[] = [
  { id: "open", label: "Open", headerClass: "border-b-gray-400" },
  { id: "in_progress", label: "In Progress", headerClass: "border-b-blue-500" },
  { id: "blocked", label: "Blocked", headerClass: "border-b-red-500" },
  { id: "in_review", label: "In Review", headerClass: "border-b-amber-500" },
  { id: "done", label: "Done", headerClass: "border-b-green-500" },
  { id: "cancelled", label: "Cancelled", headerClass: "border-b-gray-300" },
];

// ── Board column component ─────────────────────────────────────────────────────

function BoardColumn({
  col,
  tasks,
}: {
  col: Column;
  tasks: TaskOut[];
}) {
  return (
    <div className="flex flex-col min-w-[220px] max-w-[260px] flex-shrink-0">
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2 mb-2 border-b-2 rounded-t",
          col.headerClass
        )}
      >
        <span className="text-sm font-semibold">{col.label}</span>
        <span className="text-xs text-muted-foreground bg-muted rounded-full px-1.5 py-0.5">
          {tasks.length}
        </span>
      </div>
      <SortableContext
        items={tasks.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex-1 space-y-2 min-h-[120px] rounded-b border-x border-b border-dashed border-border p-2 bg-muted/20">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} sortable />
          ))}
          {tasks.length === 0 && (
            <p className="text-center text-xs text-muted-foreground py-6">
              No tasks
            </p>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function TasksBoardPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [activeTask, setActiveTask] = useState<TaskOut | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // Fetch all tasks (up to 200 for the board view)
  const { data, isLoading, isError } = useQuery({
    queryKey: ["tasks", "board"],
    queryFn: () => listTasksApi({ page: 1, size: 200 }),
  });

  const transitionMut = useMutation({
    mutationFn: ({ taskId, toStatus }: { taskId: string; toStatus: string }) =>
      transitionTaskApi(taskId, toStatus),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Cannot move card to that status"),
  });

  const tasks = data?.items ?? [];

  // Group tasks by status
  const byStatus = COLUMNS.reduce<Record<string, TaskOut[]>>((acc, col) => {
    acc[col.id] = tasks.filter((t) => t.status === col.id);
    return acc;
  }, {});

  function handleDragStart(event: DragStartEvent) {
    const task = tasks.find((t) => t.id === event.active.id);
    setActiveTask(task ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTask(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    // `over.id` could be a task ID or a column ID
    // Determine target status from the over element
    const overIsColumn = COLUMNS.some((c) => c.id === over.id);
    let targetStatus: string | undefined;

    if (overIsColumn) {
      targetStatus = over.id as string;
    } else {
      // Over a task card → find its column
      const overTask = tasks.find((t) => t.id === over.id);
      targetStatus = overTask?.status;
    }

    if (!targetStatus) return;

    const sourceTask = tasks.find((t) => t.id === active.id);
    if (!sourceTask || sourceTask.status === targetStatus) return;

    transitionMut.mutate({ taskId: String(active.id), toStatus: targetStatus });
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive text-sm">
        Failed to load tasks.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Task Board</h1>
        <div className="flex items-center gap-2">
          <Link
            to="/dashboard/tasks"
            className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors"
          >
            <List className="w-3.5 h-3.5" />
            List
          </Link>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-3 py-1 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Task
          </button>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto">
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="inline-flex gap-4 pb-4 min-w-full">
            {COLUMNS.map((col) => (
              <BoardColumn
                key={col.id}
                col={col}
                tasks={byStatus[col.id] ?? []}
              />
            ))}
          </div>

          {/* Drag overlay — renders the card being dragged */}
          <DragOverlay>
            {activeTask ? (
              <div className="rotate-2 shadow-xl opacity-90">
                <TaskCard task={activeTask} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {showCreate && <TaskCreatorModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
