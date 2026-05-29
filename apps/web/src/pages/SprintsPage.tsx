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
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Gauge,
  GripVertical,
  List,
  Plus,
  Trash2,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import {
  addTaskToSprintApi,
  createSprintApi,
  deleteSprintApi,
  listSprintsApi,
  listTasksApi,
  removeTaskFromSprintApi,
  updateSprintApi,
} from "@/features/tasks/api";
import { TaskCard } from "@/components/tasks/TaskCard";
import { cn } from "@/lib/utils";
import type { SprintOut, TaskOut } from "@/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, string> = {
  planning: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  active: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  cancelled: "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500",
};

function fmtDate(d: string) {
  try {
    return format(new Date(d), "MMM d, yyyy");
  } catch {
    return d;
  }
}

// ── Backlog task row (draggable) ────────────────────────────────────────────────

function BacklogTaskRow({ task }: { task: TaskOut }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `backlog:${task.id}` });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-center gap-2 rounded border bg-card px-3 py-2 text-sm cursor-grab select-none",
        isDragging && "opacity-40 shadow-lg ring-2 ring-primary"
      )}
      {...attributes}
      {...listeners}
    >
      <GripVertical className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      <span className="flex-1 truncate">{task.title}</span>
      <span
        className={cn(
          "text-xs rounded-full px-1.5 py-0.5",
          task.priority === "critical" || task.priority === "urgent"
            ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
            : "bg-muted text-muted-foreground"
        )}
      >
        {task.priority}
      </span>
    </div>
  );
}

// ── Sprint column ──────────────────────────────────────────────────────────────

function SprintColumn({
  sprint,
  sprintTasks,
  onRemoveTask,
  onDelete,
  onActivate,
}: {
  sprint: SprintOut;
  sprintTasks: TaskOut[];
  onRemoveTask: (sprintId: string, taskId: string) => void;
  onDelete: (sprintId: string) => void;
  onActivate: (sprintId: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const usedHours = sprintTasks.length; // placeholder — could use estimated_hours
  const capacity = sprint.capacity_hours ?? null;
  const fillPct = capacity ? Math.min(100, (usedHours / capacity) * 100) : null;

  return (
    <div className="flex flex-col min-w-[280px] max-w-[300px] shrink-0 rounded-lg border bg-card">
      {/* Sprint header */}
      <div className="px-4 py-3 border-b space-y-1">
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-1.5 text-sm font-semibold hover:text-primary transition-colors min-w-0"
          >
            {open ? (
              <ChevronDown className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 shrink-0" />
            )}
            <span className="truncate">{sprint.name}</span>
          </button>
          <span
            className={cn(
              "text-xs rounded-full px-2 py-0.5 font-medium shrink-0",
              STATUS_BADGE[sprint.status] ?? STATUS_BADGE.planning
            )}
          >
            {sprint.status}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CalendarDays className="w-3 h-3" />
          {fmtDate(sprint.starts_at)} → {fmtDate(sprint.ends_at)}
        </div>
        {/* Capacity bar */}
        {capacity !== null && (
          <div className="space-y-0.5">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{sprintTasks.length} tasks</span>
              <span>{fillPct?.toFixed(0)}% capacity</span>
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  fillPct! > 90 ? "bg-red-500" : fillPct! > 70 ? "bg-amber-500" : "bg-primary"
                )}
                style={{ width: `${fillPct}%` }}
              />
            </div>
          </div>
        )}
        {/* Actions */}
        <div className="flex items-center gap-1 pt-0.5">
          {sprint.status === "planning" && (
            <button
              onClick={() => onActivate(sprint.id)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
            >
              <Zap className="w-3 h-3" />
              Activate
            </button>
          )}
          <button
            onClick={() => onDelete(sprint.id)}
            className="ml-auto text-xs text-destructive hover:underline flex items-center gap-0.5"
          >
            <Trash2 className="w-3 h-3" />
            Delete
          </button>
        </div>
      </div>

      {/* Drop zone */}
      {open && (
        <SortableContext
          items={sprintTasks.map((t) => `sprint:${sprint.id}:${t.id}`)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex-1 min-h-[80px] p-2 space-y-1.5">
            {sprintTasks.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                Drop tasks here
              </p>
            )}
            {sprintTasks.map((task) => (
              <div key={task.id} className="relative group">
                <TaskCard task={task} />
                <button
                  onClick={() => onRemoveTask(sprint.id, task.id)}
                  className="absolute top-1 right-1 hidden group-hover:flex items-center justify-center w-4 h-4 rounded bg-destructive text-white text-xs"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </SortableContext>
      )}
    </div>
  );
}

// ── Create Sprint modal ────────────────────────────────────────────────────────

function CreateSprintModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [capacity, setCapacity] = useState("");

  const mut = useMutation({
    mutationFn: createSprintApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sprints"] });
      toast.success("Sprint created");
      onClose();
    },
    onError: () => toast.error("Failed to create sprint"),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !startsAt || !endsAt) return;
    mut.mutate({
      name,
      goal: goal || undefined,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      capacity_hours: capacity ? parseFloat(capacity) : undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={handleSubmit}
        className="bg-card rounded-lg border shadow-xl p-6 w-full max-w-md space-y-4"
      >
        <h2 className="text-lg font-semibold">New Sprint</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Name *</label>
            <input
              className="w-full rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Sprint 1"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Goal</label>
            <input
              className="w-full rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Sprint objective…"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Start *</label>
              <input
                type="date"
                className="w-full rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">End *</label>
              <input
                type="date"
                className="w-full rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
                required
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Capacity (hours)</label>
            <input
              type="number"
              min="0"
              step="0.5"
              className="w-full rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              placeholder="e.g. 80"
            />
          </div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-3 py-1 text-sm hover:bg-accent transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mut.isPending}
            className="rounded bg-primary text-primary-foreground px-3 py-1 text-sm font-medium disabled:opacity-50"
          >
            {mut.isPending ? "Creating…" : "Create Sprint"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function SprintsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const { data: sprintData } = useQuery({
    queryKey: ["sprints"],
    queryFn: () => listSprintsApi({ size: 50 }),
  });

  const { data: backlogData } = useQuery({
    queryKey: ["tasks", "backlog"],
    queryFn: () => listTasksApi({ page: 1, size: 200 }),
  });

  const sprints = sprintData?.items ?? [];
  const allTasks = backlogData?.items ?? [];

  // Determine which task IDs are in any sprint
  const sprintTaskIdSet = new Set(sprints.flatMap((s) => s.task_ids));
  const backlogTasks = allTasks.filter(
    (t) => !sprintTaskIdSet.has(t.id) && t.status !== "done" && t.status !== "cancelled"
  );

  // Per-sprint task lists (using task IDs stored on each sprint)
  const sprintTasksMap: Record<string, TaskOut[]> = {};
  for (const sprint of sprints) {
    sprintTasksMap[sprint.id] = sprint.task_ids
      .map((id) => allTasks.find((t) => t.id === id))
      .filter(Boolean) as TaskOut[];
  }

  const addMut = useMutation({
    mutationFn: ({ sprintId, taskId }: { sprintId: string; taskId: string }) =>
      addTaskToSprintApi(sprintId, taskId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sprints"] }),
    onError: () => toast.error("Failed to add task to sprint"),
  });

  const removeMut = useMutation({
    mutationFn: ({ sprintId, taskId }: { sprintId: string; taskId: string }) =>
      removeTaskFromSprintApi(sprintId, taskId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sprints"] }),
    onError: () => toast.error("Failed to remove task"),
  });

  const deleteMut = useMutation({
    mutationFn: deleteSprintApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sprints"] });
      toast.success("Sprint deleted");
    },
    onError: () => toast.error("Failed to delete sprint"),
  });

  const activateMut = useMutation({
    mutationFn: (sprintId: string) => updateSprintApi(sprintId, { status: "active" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sprints"] });
      toast.success("Sprint activated");
    },
    onError: () => toast.error("Failed to activate sprint"),
  });

  function handleDragStart(event: DragStartEvent) {
    setActiveTaskId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTaskId(null);
    const { active, over } = event;
    if (!over) return;

    const activeIdStr = String(active.id);
    const overIdStr = String(over.id);

    // Parse source: "backlog:taskId" or "sprint:sprintId:taskId"
    const isFromBacklog = activeIdStr.startsWith("backlog:");
    const sourceTaskId = isFromBacklog
      ? activeIdStr.replace("backlog:", "")
      : activeIdStr.split(":")[2];

    // Parse target sprint from drop zone id "sprint-drop:sprintId"
    let targetSprintId: string | null = null;
    if (overIdStr.startsWith("sprint-drop:")) {
      targetSprintId = overIdStr.replace("sprint-drop:", "");
    } else if (overIdStr.startsWith("sprint:")) {
      const parts = overIdStr.split(":");
      targetSprintId = parts[1];
    }

    if (!targetSprintId || !sourceTaskId) return;
    if (sprintTasksMap[targetSprintId]?.some((t) => t.id === sourceTaskId)) return;

    addMut.mutate({ sprintId: targetSprintId, taskId: sourceTaskId });
  }

  const activeTask = activeTaskId
    ? allTasks.find(
        (t) =>
          t.id === activeTaskId.replace("backlog:", "").split(":").pop()
      ) ?? null
    : null;

  return (
    <div className="flex flex-col h-full p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Sprint Planning</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Drag tasks from the backlog into a sprint to plan your work.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {backlogTasks.length} unassigned tasks
          </span>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-3 py-1 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Sprint
          </button>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto">
        <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div className="inline-flex gap-4 pb-4 min-w-full">
            {/* Backlog column */}
            <div className="flex flex-col min-w-[260px] max-w-[280px] shrink-0 rounded-lg border bg-muted/30">
              <div className="px-4 py-3 border-b">
                <div className="flex items-center gap-2">
                  <List className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-semibold">Backlog</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {backlogTasks.length}
                  </span>
                </div>
              </div>
              <SortableContext
                items={backlogTasks.map((t) => `backlog:${t.id}`)}
                strategy={verticalListSortingStrategy}
              >
                <div className="flex-1 p-2 space-y-1.5 overflow-y-auto max-h-[70vh]">
                  {backlogTasks.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-6">
                      All tasks assigned to sprints
                    </p>
                  )}
                  {backlogTasks.map((task) => (
                    <BacklogTaskRow key={task.id} task={task} />
                  ))}
                </div>
              </SortableContext>
            </div>

            {/* Sprint columns */}
            {sprints.map((sprint) => (
              <SprintColumn
                key={sprint.id}
                sprint={sprint}
                sprintTasks={sprintTasksMap[sprint.id] ?? []}
                onRemoveTask={(sprintId, taskId) => removeMut.mutate({ sprintId, taskId })}
                onDelete={(id) => deleteMut.mutate(id)}
                onActivate={(id) => activateMut.mutate(id)}
              />
            ))}

            {sprints.length === 0 && (
              <div className="flex flex-col items-center justify-center min-w-[200px] text-center text-sm text-muted-foreground gap-2">
                <Gauge className="w-8 h-8 opacity-30" />
                <p>No sprints yet.</p>
                <button
                  onClick={() => setShowCreate(true)}
                  className="text-primary hover:underline text-xs"
                >
                  Create your first sprint
                </button>
              </div>
            )}
          </div>

          <DragOverlay>
            {activeTask ? (
              <div className="rotate-1 shadow-xl opacity-90 max-w-[260px]">
                <TaskCard task={activeTask} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {showCreate && <CreateSprintModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
