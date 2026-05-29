import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { createTaskApi } from "@/features/tasks/api";
import { copilotAskApi } from "@/features/copilot/api";

const DEPARTMENTS = ["sales", "marketing", "operations", "finance", "procurement"];
const PRIORITIES = ["low", "medium", "high", "urgent", "critical"];
const TASK_TYPES = ["general", "anomaly_response", "reorder", "approval", "review", "incident"];

interface TaskCreatorModalProps {
  onClose: () => void;
  defaultDepartments?: string[];
}

export function TaskCreatorModal({ onClose, defaultDepartments }: TaskCreatorModalProps) {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [taskType, setTaskType] = useState("general");
  const [depts, setDepts] = useState<string[]>(defaultDepartments ?? []);
  const [dueAt, setDueAt] = useState("");
  const [slaHours, setSlaHours] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  const createMut = useMutation({
    mutationFn: () =>
      createTaskApi({
        title,
        description: description || undefined,
        priority,
        task_type: taskType,
        departments: depts,
        due_at: dueAt || undefined,
        sla_hours: slaHours ? parseInt(slaHours, 10) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Task created");
      onClose();
    },
    onError: () => toast.error("Failed to create task"),
  });

  async function handleAiSuggest() {
    if (!title.trim()) {
      toast.info("Enter a title first so AI can suggest details.");
      return;
    }
    setAiLoading(true);
    try {
      const resp = await copilotAskApi({
        message: `For a retail analytics task titled "${title}", suggest a concise description (1-2 sentences), the best priority level (low/medium/high/urgent/critical), and the most relevant departments (choose from: sales, marketing, operations, finance, procurement). Reply with JSON only: {"description":"...","priority":"...","departments":["..."]}`,
      });
      const json = JSON.parse(resp.answer.replace(/```json\n?|```/g, "").trim()) as {
        description?: string;
        priority?: string;
        departments?: string[];
      };
      if (json.description) setDescription(json.description);
      if (json.priority && PRIORITIES.includes(json.priority)) setPriority(json.priority);
      if (json.departments)
        setDepts(json.departments.filter((d) => DEPARTMENTS.includes(d)));
      toast.success("AI suggestions applied");
    } catch {
      toast.error("AI suggestion failed — fill in manually");
    } finally {
      setAiLoading(false);
    }
  }

  function toggleDept(d: string) {
    setDepts((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold">New Task</h2>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-accent transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Title + AI assist */}
          <div>
            <label className="block text-xs font-medium mb-1">
              Title <span className="text-destructive">*</span>
            </label>
            <div className="flex gap-2">
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Describe the task…"
                className="flex-1 rounded border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                type="button"
                onClick={() => void handleAiSuggest()}
                disabled={aiLoading}
                title="AI suggest description, priority & departments"
                className="inline-flex items-center gap-1 rounded border px-2.5 py-1.5 text-xs font-medium hover:bg-accent transition-colors disabled:opacity-50"
              >
                <Sparkles className={`w-3 h-3 ${aiLoading ? "animate-pulse" : ""}`} />
                {aiLoading ? "…" : "AI"}
              </button>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Optional details…"
              className="w-full rounded border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>

          {/* Priority + Type row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Type</label>
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="w-full rounded border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
              >
                {TASK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Departments */}
          <div>
            <label className="block text-xs font-medium mb-1">Departments</label>
            <div className="flex flex-wrap gap-1.5">
              {DEPARTMENTS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => toggleDept(d)}
                  className={`rounded px-2 py-0.5 text-xs font-medium border transition-colors ${
                    depts.includes(d)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background text-muted-foreground border-border hover:border-primary"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Due date + SLA */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Due Date</label>
              <input
                type="datetime-local"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
                className="w-full rounded border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">SLA (hours)</label>
              <input
                type="number"
                value={slaHours}
                onChange={(e) => setSlaHours(e.target.value)}
                placeholder="e.g. 24"
                min={1}
                className="w-full rounded border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t px-5 py-3">
          <button
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm border hover:bg-accent transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => createMut.mutate()}
            disabled={!title.trim() || createMut.isPending}
            className="rounded bg-primary text-primary-foreground px-4 py-1.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {createMut.isPending ? "Creating…" : "Create Task"}
          </button>
        </div>
      </div>
    </div>
  );
}
