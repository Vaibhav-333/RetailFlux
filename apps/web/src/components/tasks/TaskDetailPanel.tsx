import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  MessageSquare,
  Send,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { addCommentApi, getTaskApi, transitionTaskApi } from "@/features/tasks/api";
import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/types";

const STATUS_LABEL: Record<TaskStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  blocked: "Blocked",
  in_review: "In Review",
  done: "Done",
  cancelled: "Cancelled",
};

const STATUS_COLOR: Record<TaskStatus, string> = {
  open: "text-gray-500",
  in_progress: "text-blue-500",
  blocked: "text-red-500",
  in_review: "text-amber-500",
  done: "text-green-500",
  cancelled: "text-gray-400",
};

interface TaskDetailPanelProps {
  taskId: string;
}

export function TaskDetailPanel({ taskId }: TaskDetailPanelProps) {
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [toStatus, setToStatus] = useState("");

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => getTaskApi(taskId),
    enabled: !!taskId,
  });

  const transitionMut = useMutation({
    mutationFn: (s: string) => transitionTaskApi(taskId, s),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task", taskId] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      setToStatus("");
      toast.success("Status updated");
    },
    onError: () => toast.error("Cannot transition to that status"),
  });

  const commentMut = useMutation({
    mutationFn: () => addCommentApi(taskId, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task", taskId] });
      setComment("");
      toast.success("Comment added");
    },
    onError: () => toast.error("Failed to add comment"),
  });

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!task) return <p className="text-sm text-muted-foreground p-3">Task not found.</p>;

  return (
    <div className="space-y-4 text-sm">
      {/* Title + status */}
      <div>
        <h3 className="font-semibold text-base leading-snug">{task.title}</h3>
        <p className={cn("text-xs mt-0.5 font-medium", STATUS_COLOR[task.status])}>
          {STATUS_LABEL[task.status]}
        </p>
        {task.breached && (
          <p className="mt-1 flex items-center gap-1 text-xs text-red-500">
            <AlertTriangle className="w-3 h-3" /> SLA breached
          </p>
        )}
      </div>

      {/* Description */}
      {task.description && (
        <p className="text-xs text-muted-foreground leading-relaxed">
          {task.description}
        </p>
      )}

      {/* Meta grid */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Priority</span>
        <span className="capitalize">{task.priority}</span>
        <span className="font-medium text-foreground">Type</span>
        <span className="capitalize">{task.task_type.replace(/_/g, " ")}</span>
        <span className="font-medium text-foreground">Source</span>
        <span className="capitalize">{task.source.replace(/_/g, " ")}</span>
        {task.departments.length > 0 && (
          <>
            <span className="font-medium text-foreground">Departments</span>
            <span>{task.departments.join(", ")}</span>
          </>
        )}
        {task.due_at && (
          <>
            <span className="font-medium text-foreground flex items-center gap-1">
              <Calendar className="w-3 h-3" /> Due
            </span>
            <span>{new Date(task.due_at).toLocaleString()}</span>
          </>
        )}
        {task.sla_hours && (
          <>
            <span className="font-medium text-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" /> SLA
            </span>
            <span>{task.sla_hours}h</span>
          </>
        )}
      </div>

      {/* Transition */}
      <div>
        <p className="text-xs font-medium mb-1">Move to status</p>
        <div className="flex gap-2">
          <select
            value={toStatus}
            onChange={(e) => setToStatus(e.target.value)}
            className="flex-1 rounded border bg-background px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">Select…</option>
            {(["open", "in_progress", "blocked", "in_review", "done", "cancelled"] as TaskStatus[]).map(
              (s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              )
            )}
          </select>
          <button
            onClick={() => toStatus && transitionMut.mutate(toStatus)}
            disabled={!toStatus || transitionMut.isPending}
            className="inline-flex items-center gap-1 rounded bg-primary text-primary-foreground px-2.5 py-1 text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            <CheckCircle className="w-3 h-3" />
            Move
          </button>
        </div>
      </div>

      {/* Comments */}
      <div>
        <p className="text-xs font-medium mb-1 flex items-center gap-1">
          <MessageSquare className="w-3 h-3" />
          Comments ({task.comments.length})
        </p>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {task.comments.length === 0 ? (
            <p className="text-xs text-muted-foreground">No comments yet.</p>
          ) : (
            task.comments.map((c) => (
              <div key={c.id} className="rounded bg-muted p-2">
                <p className="text-xs leading-relaxed">{c.body}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {new Date(c.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Add comment */}
        <div className="mt-2 flex gap-1.5">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && comment.trim()) {
                e.preventDefault();
                commentMut.mutate();
              }
            }}
            placeholder="Add a comment…"
            className="flex-1 rounded border bg-background px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={() => commentMut.mutate()}
            disabled={!comment.trim() || commentMut.isPending}
            className="inline-flex items-center rounded bg-primary text-primary-foreground p-1.5 hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
