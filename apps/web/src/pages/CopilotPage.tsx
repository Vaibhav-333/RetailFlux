import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  MessageSquare,
  Trash2,
  Plus,
  ChevronRight,
  Loader2,
  Bot,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import {
  listConversationsApi,
  getConversationApi,
  deleteConversationApi,
  getCopilotUsageApi,
  type Conversation,
  type ConversationMessage,
} from "@/features/copilot/api";
import { CopilotDock } from "@/components/ai/CopilotDock";
import { AIBadge } from "@/components/ui/AIBadge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: ConversationMessage }) {
  if (msg.role === "system") {
    return (
      <div className="flex justify-center">
        <div className="text-[10px] text-muted-foreground px-3 py-1 rounded-full bg-muted/50 border border-border max-w-xl text-center">
          {msg.content.replace("[Conversation summary]", "📝 Summary: ")}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}>
      {msg.role === "assistant" && (
        <div className="w-7 h-7 rounded-full bg-violet-500/20 flex items-center justify-center shrink-0 mt-1">
          <Sparkles className="w-3.5 h-3.5 text-violet-400" aria-hidden />
        </div>
      )}
      <div className="flex flex-col gap-1.5 max-w-2xl">
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            msg.role === "user"
              ? "bg-brand-600 text-white rounded-br-sm"
              : "bg-muted/60 text-foreground border border-border rounded-bl-sm",
          )}
        >
          <p className="whitespace-pre-wrap">{msg.content}</p>
          {msg.role === "assistant" && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              {msg.provider && <AIBadge provider={msg.provider} size="xs" />}
              {msg.tool_used && (
                <span className="text-[10px] text-muted-foreground">via {msg.tool_used}</span>
              )}
            </div>
          )}
        </div>

        {/* Proposed actions */}
        {msg.role === "assistant" && msg.proposed_actions?.length > 0 && (
          <div className="flex flex-col gap-1">
            {msg.proposed_actions.map((action, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-[11px] px-3 py-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-300"
              >
                <ChevronRight className="w-3 h-3 shrink-0" />
                <span className="font-medium">{action.verb}</span>
                <span className="text-violet-400/70">— {action.description}</span>
                {action.url_path && (
                  <a
                    href={action.url_path}
                    className="ml-auto underline hover:text-violet-200"
                  >
                    Go
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        <span className="text-[10px] text-muted-foreground px-1">
          {relativeTime(msg.created_at)}
        </span>
      </div>
    </div>
  );
}

// ── Conversation list sidebar ─────────────────────────────────────────────────

interface ConvListProps {
  selected: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function ConversationList({ selected, onSelect, onNew }: ConvListProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["copilot-conversations"],
    queryFn: listConversationsApi,
    staleTime: 10_000,
  });

  const deleteMut = useMutation({
    mutationFn: deleteConversationApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilot-conversations"] });
      toast.success("Conversation deleted");
    },
  });

  return (
    <aside className="w-64 shrink-0 border-r border-border flex flex-col h-full bg-card/50">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <span className="text-sm font-semibold text-foreground">Conversations</span>
        <button
          onClick={onNew}
          className="w-7 h-7 rounded-lg bg-brand-600 hover:bg-brand-700 flex items-center justify-center text-white transition-colors"
          aria-label="New conversation"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && (!data?.conversations || data.conversations.length === 0) && (
          <div className="text-center py-8 text-xs text-muted-foreground px-4">
            No conversations yet. Start chatting with the AI Copilot.
          </div>
        )}

        {data?.conversations?.map((conv: Conversation) => (
          <button
            key={conv.id}
            onClick={() => onSelect(conv.id)}
            className={cn(
              "w-full text-left px-4 py-3 border-b border-border/50 hover:bg-accent/50 transition-colors group",
              selected === conv.id && "bg-accent",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">
                  {conv.title || "Untitled"}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {conv.message_count} msg · {relativeTime(conv.last_message_at)}
                </p>
                {conv.summary && (
                  <p className="text-[10px] text-muted-foreground/70 mt-0.5 line-clamp-2">
                    {conv.summary}
                  </p>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteMut.mutate(conv.id);
                }}
                className="shrink-0 opacity-0 group-hover:opacity-100 w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-red-400 transition-all"
                aria-label="Delete conversation"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </button>
        ))}
      </div>

      {/* Usage widget */}
      <UsageWidget />
    </aside>
  );
}

// ── Usage widget ──────────────────────────────────────────────────────────────

function UsageWidget() {
  const { data } = useQuery({
    queryKey: ["copilot-usage"],
    queryFn: getCopilotUsageApi,
    staleTime: 30_000,
  });

  if (!data) return null;

  return (
    <div className="p-4 border-t border-border">
      <p className="text-[10px] text-muted-foreground mb-1">
        Daily usage: {data.tokens_used.toLocaleString()} / {data.cap.toLocaleString()} tokens
      </p>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            data.pct_used > 80 ? "bg-red-500" : data.pct_used > 50 ? "bg-amber-500" : "bg-brand-500",
          )}
          style={{ width: `${Math.min(100, data.pct_used)}%` }}
        />
      </div>
      <p className="text-[10px] text-muted-foreground mt-1">{data.pct_used}% used today</p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function CopilotPage() {
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [dockOpen, setDockOpen] = useState(false);
  const [dockConvId, setDockConvId] = useState<string | null>(null);
  const [dockMessages, setDockMessages] = useState<ConversationMessage[]>([]);

  const { data: convData, isLoading: convLoading } = useQuery({
    queryKey: ["copilot-conversation", selectedConvId],
    queryFn: () => (selectedConvId ? getConversationApi(selectedConvId) : null),
    enabled: !!selectedConvId,
    staleTime: 5000,
  });

  function handleSelectConversation(id: string) {
    setSelectedConvId(id);
  }

  function handleNewConversation() {
    setSelectedConvId(null);
    setDockConvId(null);
    setDockMessages([]);
    setDockOpen(true);
  }

  function handleContinueConversation() {
    if (convData) {
      setDockConvId(selectedConvId);
      setDockMessages(convData.messages);
      setDockOpen(true);
    }
  }

  const messages = convData?.messages ?? [];

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Sidebar */}
      <ConversationList
        selected={selectedConvId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
      />

      {/* Main area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-foreground">Executive AI Copilot</h1>
              <p className="text-xs text-muted-foreground">
                Ask anything about your business data
              </p>
            </div>
          </div>
          <button
            onClick={handleNewConversation}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Chat
          </button>
        </div>

        {/* Content */}
        {!selectedConvId ? (
          <EmptyState onStart={handleNewConversation} />
        ) : convLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Conversation messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
              {messages.length === 0 ? (
                <p className="text-center text-xs text-muted-foreground py-8">
                  No messages in this conversation.
                </p>
              ) : (
                messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)
              )}
            </div>

            {/* Continue bar */}
            <div className="shrink-0 border-t border-border px-6 py-3 flex items-center gap-3">
              <MessageSquare className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground flex-1">
                {messages.length} message{messages.length !== 1 ? "s" : ""}
              </span>
              <button
                onClick={handleContinueConversation}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 text-xs font-medium transition-colors border border-violet-500/30"
              >
                <Sparkles className="w-3 h-3" />
                Continue
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Floating dock for new / continued chat */}
      <CopilotDock
        open={dockOpen}
        onClose={() => setDockOpen(false)}
        conversationId={dockConvId}
        initialMessages={dockMessages}
      />
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────

function EmptyState({ onStart }: { onStart: () => void }) {
  const examples = [
    "Why did gross margin drop last week?",
    "Which SKUs need reordering urgently?",
    "Summarize this week's sales performance.",
    "What tasks are overdue in Operations?",
    "Compare Q1 vs Q2 procurement spend.",
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="w-16 h-16 rounded-2xl bg-violet-500/15 flex items-center justify-center mb-4">
        <Sparkles className="w-8 h-8 text-violet-400" />
      </div>
      <h2 className="text-lg font-semibold text-foreground mb-2">
        AI Copilot for RetailFlux
      </h2>
      <p className="text-sm text-muted-foreground mb-8 max-w-md">
        Ask questions about your sales, inventory, tasks, and more. Copilot uses your
        company's real data to provide grounded, actionable answers.
      </p>

      <div className="grid grid-cols-1 gap-2 w-full max-w-md mb-8">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={onStart}
            className="text-left text-xs px-4 py-2.5 rounded-xl border border-border bg-muted/30 hover:bg-accent text-foreground transition-colors"
          >
            "{ex}"
          </button>
        ))}
      </div>

      <button
        onClick={onStart}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors"
      >
        <Sparkles className="w-4 h-4" />
        Start a conversation
      </button>
    </div>
  );
}
