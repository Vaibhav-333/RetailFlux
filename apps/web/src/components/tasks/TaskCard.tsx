import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { AlertTriangle, Calendar, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TaskOut, TaskPriority, TaskStatus } from "@/types";

// ── Colour maps ───────────────────────────────────────────────────────────────

const PRIORITY_BADGE: Record<TaskPriority, string> = {
  low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  high: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  urgent: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
};

const STATUS_DOT: Record<TaskStatus, string> = {
  open: "bg-gray-400",
  in_progress: "bg-blue-500",
  blocked: "bg-red-500",
  in_review: "bg-amber-500",
  done: "bg-green-500",
  cancelled: "bg-gray-300",
};

// ── Component ─────────────────────────────────────────────────────────────────

interface TaskCardProps {
  task: TaskOut;
  onClick?: () => void;
  /** When true the card is being used in a sortable context and DnD handles are enabled. */
  sortable?: boolean;
  /** Compact mode hides department chips and metadata for tighter boards. */
  compact?: boolean;
}

export function TaskCard({ task, onClick, sortable = false, compact = false }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id, disabled: !sortable });

  const style = sortable
    ? { transform: CSS.Transform.toString(transform), transition }
    : undefined;

  const isOverdue =
    task.due_at && !["done", "cancelled"].includes(task.status)
      ? new Date(task.due_at) < new Date()
      : false;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...(sortable ? { ...attributes, ...listeners } : {})}
      onClick={onClick}
      className={cn(
        "rounded-lg border bg-card p-3 shadow-sm cursor-pointer select-none",
        "hover:shadow-md hover:border-primary/30 transition-all",
        isDragging && "opacity-50 shadow-lg scale-95",
        task.breached && "border-red-300 dark:border-red-800"
      )}
    >
      {/* Status dot + title */}
      <div className="flex items-start gap-2">
        <span
          className={cn(
            "mt-1 flex-shrink-0 w-2 h-2 rounded-full",
            STATUS_DOT[task.status]
          )}
        />
        <p className="text-sm font-medium leading-snug line-clamp-2 flex-1">
          {task.title}
        </p>
      </div>

      {/* Meta row */}
      {!compact && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              PRIORITY_BADGE[task.priority]
            )}
          >
            {task.priority}
          </span>

          {task.departments.map((d) => (
            <span
              key={d}
              className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] bg-muted text-muted-foreground"
            >
              {d}
            </span>
          ))}

          {task.breached && (
            <span className="inline-flex items-center gap-0.5 text-[10px] text-red-600 dark:text-red-400 font-medium">
              <AlertTriangle className="w-3 h-3" /> SLA
            </span>
          )}
        </div>
      )}

      {/* Due date */}
      {task.due_at && (
        <div
          className={cn(
            "mt-1.5 flex items-center gap-1 text-[10px]",
            isOverdue ? "text-red-500" : "text-muted-foreground"
          )}
        >
          <Calendar className="w-3 h-3" />
          {new Date(task.due_at).toLocaleDateString()}
          {task.sla_hours && (
            <>
              <Clock className="w-3 h-3 ml-1" />
              {task.sla_hours}h SLA
            </>
          )}
        </div>
      )}

      {/* Assignee count */}
      {task.assignees.length > 0 && (
        <div className="mt-1.5 text-[10px] text-muted-foreground">
          {task.assignees.length} assignee{task.assignees.length > 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
