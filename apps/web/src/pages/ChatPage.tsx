import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { sendChatMessageApi } from "@/features/chat/api";
import type { ChatResponse } from "@/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolUsed?: string | null;
  data?: Record<string, unknown> | null;
  provider?: string;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi! I can help you explore your business data. Try asking about sales trends, marketing ROI, inventory levels, or financial performance.",
      toolUsed: null,
      data: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: ChatResponse = await sendChatMessageApi(text);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        toolUsed: res.tool_used,
        data: res.data,
        provider: res.provider,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-foreground">AI Chat</h1>
        <p className="text-sm text-muted-foreground">Ask questions about your business data in natural language</p>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pb-4 pr-2">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
                <Bot className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-lg px-4 py-3 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-foreground"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {msg.toolUsed && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
                    {msg.toolUsed.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-muted-foreground">via {msg.provider}</span>
                </div>
              )}
              {msg.data && <DataPreview data={msg.data} />}
            </div>
            {msg.role === "user" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="w-4 h-4 text-primary" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
              <Bot className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div className="bg-muted rounded-lg px-4 py-3">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t pt-4">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your business data..."
            className="flex-1 rounded-lg border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-primary px-4 py-2.5 text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

function DataPreview({ data }: { data: Record<string, unknown> }) {
  const numericEntries = Object.entries(data).filter(
    ([, v]) => typeof v === "number"
  );
  if (numericEntries.length === 0) return null;

  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      {numericEntries.slice(0, 6).map(([key, value]) => (
        <div key={key} className="bg-background/50 rounded px-2 py-1.5">
          <div className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</div>
          <div className="text-sm font-medium">
            {typeof value === "number"
              ? value >= 1000
                ? `${(value / 1000).toFixed(1)}k`
                : (value as number).toFixed(2)
              : String(value)}
          </div>
        </div>
      ))}
    </div>
  );
}
