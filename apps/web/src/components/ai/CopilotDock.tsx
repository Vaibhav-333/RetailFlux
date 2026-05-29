import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, X, Send, CheckCircle, ExternalLink, Trash2, Clock } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { AIBadge } from "@/components/ui/AIBadge";
import {
  copilotStreamApi,
  type SSEEvent,
  type ConversationMessage,
} from "@/features/copilot/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  provider?: string;
  toolUsed?: string | null;
  proposedActions?: Array<{ verb: string; description: string; url_path: string }>;
  streaming?: boolean;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PAGE_LABELS: Record<string, string> = {
  "/dashboard": "Master Dashboard",
  "/dashboard/sales": "Sales Analytics",
  "/dashboard/marketing": "Marketing Analytics",
  "/dashboard/operations": "Operations Analytics",
  "/dashboard/finance": "Finance Analytics",
  "/dashboard/procurement": "Procurement Analytics",
  "/dashboard/inventory": "Inventory Intelligence",
  "/dashboard/tasks": "Task Center",
  "/dashboard/tasks/board": "Task Board",
  "/dashboard/tasks/analytics": "Task Analytics",
  "/dashboard/ai-chat": "AI Chat",
  "/dashboard/reports": "Reports",
  "/dashboard/settings": "Settings",
  "/dashboard/observability": "Observability",
};

const SUGGESTED_PROMPTS: Record<string, string[]> = {
  "/dashboard": ["Summarize today's KPIs", "Any anomalies this week?", "What should I focus on?"],
  "/dashboard/sales": ["Why is revenue down?", "Top performing SKUs?", "Sales by region breakdown"],
  "/dashboard/marketing": ["ROAS vs target?", "Best campaign this month?", "CAC trend"],
  "/dashboard/operations": ["SKUs below reorder?", "Warehouse stock summary", "Low-stock alerts"],
  "/dashboard/finance": ["Gross margin trend", "Revenue vs COGS", "Monthly P&L summary"],
  "/dashboard/procurement": ["Top suppliers by spend", "Average lead time", "Procurement cost trend"],
  "/dashboard/inventory": ["Which SKUs need reordering?", "Dead stock value?", "ABC/XYZ distribution"],
  "/dashboard/tasks": ["What's overdue?", "Team workload summary", "Bottlenecks this week"],
};

const DEFAULT_PROMPTS = ["What's the key insight today?", "Show me anomalies", "Compare departments"];

// ── Props ─────────────────────────────────────────────────────────────────────

interface CopilotDockProps {
  open: boolean;
  onClose: () => void;
  /** Pre-populate with messages from a loaded conversation */
  initialMessages?: ConversationMessage[];
  conversationId?: string | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CopilotDock({
  open,
  onClose,
  initialMessages,
  conversationId: initialConvId,
}: CopilotDockProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(initialConvId ?? null);
  const [pendingActionConfirm, setPendingActionConfirm] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  const pageName = PAGE_LABELS[location.pathname] ?? "RetailFlux";
  const suggestions = SUGGESTED_PROMPTS[location.pathname] ?? DEFAULT_PROMPTS;

  // Load initial messages from a loaded conversation
  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(
        initialMessages.map((m) => ({
          role: m.role as Message["role"],
          content: m.content,
          provider: m.provider ?? undefined,
          toolUsed: m.tool_used,
          proposedActions: m.proposed_actions,
        })),
      );
    }
  }, [initialMessages]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const msg = input.trim();
    if (!msg || isStreaming) return;
    setInput("");
    setIsStreaming(true);

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: "user", content: msg }]);

    // Add placeholder for streaming assistant message
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", streaming: true },
    ]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let toolUsed: string | null = null;
    let proposedActions: Message["proposedActions"] = [];
    let finalMsgId: string | null = null;
    let finalProvider = "gemini";

    try {
      await copilotStreamApi(
        {
          message: msg,
          page_context: { page: pageName, path: location.pathname },
          conversation_id: conversationId,
        },
        (event: SSEEvent) => {
          if (event.type === "token" && event.content) {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                last.content += event.content;
              }
              return updated;
            });
          } else if (event.type === "tool_used" && event.tool) {
            toolUsed = event.tool;
          } else if (event.type === "proposed_actions" && event.actions) {
            proposedActions = event.actions;
          } else if (event.type === "done") {
            finalMsgId = event.message_id ?? null;
            finalProvider = event.provider ?? "gemini";
            if (!conversationId && finalMsgId) {
              // extract conversation id from message context if needed
            }
          } else if (event.type === "error" && event.message) {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                last.content = event.message!;
                last.streaming = false;
              }
              return updated;
            });
          }
        },
        ctrl.signal,
      );
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            last.content = "Sorry, I couldn't reach the AI service. Please try again.";
            last.streaming = false;
          }
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
      // Finalise the streaming message
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === "assistant") {
          last.streaming = false;
          last.toolUsed = toolUsed;
          last.proposedActions = proposedActions;
          last.provider = finalProvider;
        }
        return updated;
      });
    }
  }, [input, isStreaming, pageName, location.pathname, conversationId]);

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleStop() {
    abortRef.current?.abort();
    setIsStreaming(false);
  }

  function handleClear() {
    setMessages([]);
    setConversationId(null);
  }

  function handleNavigate(urlPath: string) {
    if (urlPath) navigate(urlPath);
    onClose();
  }

  if (!open) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 w-[420px] max-h-[640px] flex flex-col rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
      style={{ boxShadow: "0 0 40px hsl(239 84% 67% / 0.15), 0 8px 32px rgba(0,0,0,0.4)" }}
      role="dialog"
      aria-label="AI Copilot"
    >
      {/* Header */}
      <div
        className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-border"
        style={{
          background: "linear-gradient(135deg, hsl(var(--ai-from)/0.12), hsl(var(--ai-to)/0.08))",
        }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-400" aria-hidden />
          <span className="text-sm font-semibold text-foreground">AI Copilot</span>
          <AIBadge size="xs" />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-muted-foreground hidden sm:inline">{pageName}</span>
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              title="New conversation"
              className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Clear conversation"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={() => navigate("/dashboard/copilot")}
            title="Open full conversation history"
            className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Full copilot view"
          >
            <Clock className="w-3 h-3" />
          </button>
          <button
            onClick={onClose}
            className="ml-1 w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close copilot"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="py-4">
            <p className="text-xs text-muted-foreground mb-3">Ask about your data:</p>
            <div className="flex flex-col gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-border bg-muted/30 text-foreground hover:bg-accent transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={cn("flex gap-2", m.role === "user" ? "justify-end" : "justify-start")}
          >
            {m.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center shrink-0 mt-0.5">
                <Sparkles className="w-3 h-3 text-violet-400" aria-hidden />
              </div>
            )}
            <div className="flex flex-col gap-1.5 max-w-[85%]">
              <div
                className={cn(
                  "rounded-2xl px-3 py-2 text-xs leading-relaxed",
                  m.role === "user"
                    ? "bg-brand-600 text-white rounded-br-sm"
                    : "bg-muted/50 text-foreground border border-border rounded-bl-sm",
                )}
              >
                {m.content || (m.streaming && <span className="opacity-50">Thinking…</span>)}
                {m.streaming && (
                  <span className="inline-block w-1.5 h-3 bg-violet-400 ml-0.5 animate-pulse rounded-sm" />
                )}
                {m.role === "assistant" && m.provider && !m.streaming && (
                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                    <AIBadge provider={m.provider} size="xs" />
                    {m.toolUsed && (
                      <span className="text-[9px] text-muted-foreground">via {m.toolUsed}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Proposed actions */}
              {m.role === "assistant" &&
                m.proposedActions &&
                m.proposedActions.length > 0 && (
                  <div className="flex flex-col gap-1">
                    {m.proposedActions.map((action, ai) => (
                      <button
                        key={ai}
                        onClick={() => {
                          if (action.verb.toLowerCase().includes("delete") ||
                              action.verb.toLowerCase().includes("remove")) {
                            setPendingActionConfirm(`${action.verb}: ${action.description}`);
                          } else {
                            handleNavigate(action.url_path);
                          }
                        }}
                        className="flex items-center gap-1.5 text-left text-[10px] px-2 py-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 transition-colors"
                      >
                        <CheckCircle className="w-3 h-3 shrink-0" />
                        <span className="font-medium">{action.verb}</span>
                        <span className="text-violet-400/70 truncate">— {action.description}</span>
                        {action.url_path && <ExternalLink className="w-2.5 h-2.5 shrink-0 ml-auto" />}
                      </button>
                    ))}
                  </div>
                )}
            </div>
          </div>
        ))}

        {/* Action confirmation dialog */}
        {pendingActionConfirm && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs">
            <p className="text-red-300 mb-2">⚠ Confirm action: {pendingActionConfirm}</p>
            <div className="flex gap-2">
              <button
                onClick={() => setPendingActionConfirm(null)}
                className="flex-1 px-2 py-1 rounded-md bg-muted text-muted-foreground hover:bg-accent text-[10px]"
              >
                Cancel
              </button>
              <button
                onClick={() => setPendingActionConfirm(null)}
                className="flex-1 px-2 py-1 rounded-md bg-red-600 text-white hover:bg-red-700 text-[10px]"
              >
                Confirm
              </button>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-border p-3">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-muted/30 px-3 py-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about your data…"
            rows={1}
            className="flex-1 resize-none bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none leading-relaxed max-h-24"
            aria-label="Ask AI a question"
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
              onClick={handleStop}
              className="shrink-0 w-7 h-7 rounded-lg bg-red-600 hover:bg-red-700 flex items-center justify-center text-white transition-colors"
              aria-label="Stop generation"
            >
              <span className="w-2 h-2 bg-white rounded-sm" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="shrink-0 w-7 h-7 rounded-lg bg-brand-600 hover:bg-brand-700 flex items-center justify-center text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <p className="mt-1.5 text-[10px] text-muted-foreground text-center">
          <kbd className="border border-border rounded px-1">↵</kbd> send ·{" "}
          <kbd className="border border-border rounded px-1">⇧↵</kbd> newline ·{" "}
          <kbd className="border border-border rounded px-1">⌘J</kbd> toggle
        </p>
      </div>
    </div>
  );
}
