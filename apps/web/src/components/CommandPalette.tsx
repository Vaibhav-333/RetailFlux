import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ShoppingCart,
  Megaphone,
  Warehouse,
  DollarSign,
  Truck,
  Upload,
  MessageSquare,
  BarChart3,
  Settings,
  Search,
  Zap,
  Clock,
  Sparkles,
  ArrowRight,
  Loader2,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { commandRegistry, type Command } from "@/lib/commandRegistry";
import { copilotAskApi } from "@/features/copilot/api";

// ── Go section: navigable routes ────────────────────────────────────────────

interface NavItem {
  label: string;
  description: string;
  icon: React.ElementType;
  path: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Master Dashboard", description: "CEO overview", icon: LayoutDashboard, path: "/dashboard" },
  { label: "Sales", description: "Revenue & SKU analytics", icon: ShoppingCart, path: "/dashboard/sales" },
  { label: "Marketing", description: "Spend, ROAS & campaigns", icon: Megaphone, path: "/dashboard/marketing" },
  { label: "Operations", description: "Stock levels & warehouses", icon: Warehouse, path: "/dashboard/operations" },
  { label: "Finance", description: "P&L and gross margin", icon: DollarSign, path: "/dashboard/finance" },
  { label: "Procurement", description: "Suppliers & lead times", icon: Truck, path: "/dashboard/procurement" },
  { label: "Uploads", description: "Upload department data", icon: Upload, path: "/dashboard/uploads" },
  { label: "AI Chat", description: "Ask questions about your data", icon: MessageSquare, path: "/dashboard/ai-chat" },
  { label: "Reports", description: "Export CSV or JSON reports", icon: BarChart3, path: "/dashboard/reports" },
  { label: "Observability", description: "API metrics & audit log", icon: Activity, path: "/dashboard/observability" },
  { label: "Settings", description: "Profile and preferences", icon: Settings, path: "/dashboard/settings" },
];

// ── Recent items (persisted in sessionStorage) ───────────────────────────────

const RECENTS_KEY = "rf:cmd:recent";
const MAX_RECENTS = 5;

function loadRecents(): NavItem[] {
  try {
    const raw = sessionStorage.getItem(RECENTS_KEY);
    if (!raw) return [];
    const paths: string[] = JSON.parse(raw);
    return paths
      .map((p) => NAV_ITEMS.find((n) => n.path === p))
      .filter(Boolean) as NavItem[];
  } catch {
    return [];
  }
}

function saveRecent(path: string): void {
  try {
    const paths: string[] = JSON.parse(sessionStorage.getItem(RECENTS_KEY) ?? "[]");
    const updated = [path, ...paths.filter((p) => p !== path)].slice(0, MAX_RECENTS);
    sessionStorage.setItem(RECENTS_KEY, JSON.stringify(updated));
  } catch {
    // noop
  }
}

// ── Section types ─────────────────────────────────────────────────────────────

type Section = "go" | "do" | "ask" | "recent";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  /** Pre-select a section, e.g. "ask" when opened via ⌘/ */
  defaultSection?: Section;
}

export function CommandPalette({ open, onClose, defaultSection }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const [section, setSection] = useState<Section>(defaultSection ?? "go");
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const commands: Command[] = commandRegistry.getAll();
  const recents = loadRecents();

  // ── Reset on open ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
      setAiAnswer(null);
      setAiLoading(false);
      setSection(defaultSection ?? "go");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open, defaultSection]);

  useEffect(() => {
    setActiveIdx(0);
    setAiAnswer(null);
  }, [query, section]);

  // ── Navigation ─────────────────────────────────────────────────────────────
  function selectNav(item: NavItem) {
    saveRecent(item.path);
    navigate(item.path);
    onClose();
  }

  // ── Command execution ──────────────────────────────────────────────────────
  function runCommand(cmd: Command) {
    cmd.handler();
    onClose();
  }

  // ── AI ask ─────────────────────────────────────────────────────────────────
  async function submitAsk() {
    const q = query.trim();
    if (!q || aiLoading) return;
    setAiLoading(true);
    setAiAnswer(null);
    try {
      const res = await copilotAskApi({ message: q });
      setAiAnswer(res.answer);
    } catch {
      setAiAnswer("Sorry, the AI service is unavailable right now.");
    } finally {
      setAiLoading(false);
    }
  }

  // ── Open full chat with pre-loaded question ────────────────────────────────
  function openInChat() {
    navigate("/dashboard/ai-chat");
    onClose();
  }

  // ── Filter items by query ──────────────────────────────────────────────────
  const filteredNav = query.trim()
    ? NAV_ITEMS.filter(
        (n) =>
          n.label.toLowerCase().includes(query.toLowerCase()) ||
          n.description.toLowerCase().includes(query.toLowerCase()),
      )
    : NAV_ITEMS;

  const filteredCmds = query.trim()
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.description.toLowerCase().includes(query.toLowerCase()),
      )
    : commands;

  // ── Active items for keyboard nav ──────────────────────────────────────────
  const activeItems: Array<{ type: "nav"; item: NavItem } | { type: "cmd"; item: Command }> =
    section === "go"
      ? filteredNav.map((n) => ({ type: "nav", item: n }))
      : section === "do"
        ? filteredCmds.map((c) => ({ type: "cmd", item: c }))
        : section === "recent"
          ? recents.map((n) => ({ type: "nav", item: n }))
          : [];

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, activeItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      if (section === "ask") {
        if (aiAnswer) openInChat();
        else submitAsk();
        return;
      }
      const active = activeItems[activeIdx];
      if (active?.type === "nav") selectNav(active.item);
      if (active?.type === "cmd") runCommand(active.item);
    } else if (e.key === "Escape") {
      onClose();
    } else if (e.key === "Tab") {
      e.preventDefault();
      const order: Section[] = ["go", "do", "ask", "recent"];
      const idx = order.indexOf(section);
      setSection(order[(idx + 1) % order.length]);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-hidden />

      <div
        className="relative w-full max-w-xl rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
        style={{ boxShadow: "0 0 60px hsl(239 84% 67% / 0.12), 0 16px 48px rgba(0,0,0,0.5)" }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKey}
      >
        {/* Section tabs */}
        <div className="flex items-center gap-1 px-3 pt-3 pb-0">
          {(
            [
              { id: "go" as Section, label: "Go", icon: Search, hint: "⌘P" },
              { id: "do" as Section, label: "Do", icon: Zap, hint: "⌘." },
              { id: "ask" as Section, label: "Ask AI", icon: Sparkles, hint: "⌘/" },
              { id: "recent" as Section, label: "Recent", icon: Clock },
            ] as const
          ).map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setSection(t.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-medium transition-colors",
                  section === t.id
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                <Icon className="w-3 h-3" aria-hidden />
                {t.label}
                {"hint" in t && t.hint && (
                  <kbd className="text-[9px] border border-border rounded px-1 opacity-60">
                    {t.hint}
                  </kbd>
                )}
              </button>
            );
          })}
        </div>

        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-muted/30">
          {section === "ask" ? (
            <Sparkles className="w-4 h-4 text-violet-400 shrink-0" aria-hidden />
          ) : (
            <Search className="w-4 h-4 text-muted-foreground shrink-0" aria-hidden />
          )}
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              section === "go"
                ? "Go to page or saved view…"
                : section === "do"
                  ? "Find an action…"
                  : section === "ask"
                    ? "Ask AI about your data…"
                    : "Recent items"
            }
            className="flex-1 bg-transparent text-sm outline-none text-foreground placeholder:text-muted-foreground"
            aria-label={section === "ask" ? "Ask AI" : "Search"}
          />
          {section === "ask" && query.trim() && !aiLoading && (
            <button
              onClick={submitAsk}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs transition-colors"
            >
              Ask
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
          {aiLoading && (
            <Loader2 className="shrink-0 w-4 h-4 animate-spin text-violet-400" aria-hidden />
          )}
          <kbd className="shrink-0 text-xs border border-border rounded px-1.5 py-0.5 text-muted-foreground">
            Esc
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-1">
          {/* ── Go section ── */}
          {section === "go" && (
            <>
              {filteredNav.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                  No pages match "{query}"
                </p>
              ) : (
                filteredNav.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.path}
                      onClick={() => selectNav(item)}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                        idx === activeIdx
                          ? "bg-brand-500/10 text-brand-400"
                          : "text-foreground hover:bg-accent",
                      )}
                    >
                      <Icon className="w-4 h-4 shrink-0 text-muted-foreground" aria-hidden />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        <p className="text-xs text-muted-foreground truncate">{item.description}</p>
                      </div>
                    </button>
                  );
                })
              )}
            </>
          )}

          {/* ── Do section ── */}
          {section === "do" && (
            <>
              {filteredCmds.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                  No actions match "{query}"
                </p>
              ) : (
                filteredCmds.map((cmd, idx) => (
                  <button
                    key={cmd.id}
                    onClick={() => runCommand(cmd)}
                    className={cn(
                      "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                      idx === activeIdx
                        ? "bg-brand-500/10 text-brand-400"
                        : "text-foreground hover:bg-accent",
                    )}
                  >
                    <Zap className="w-4 h-4 shrink-0 text-amber-400" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{cmd.label}</p>
                      <p className="text-xs text-muted-foreground truncate">{cmd.description}</p>
                    </div>
                    {cmd.shortcut && (
                      <kbd className="shrink-0 text-[10px] border border-border rounded px-1.5 py-0.5 text-muted-foreground">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </button>
                ))
              )}
            </>
          )}

          {/* ── Ask section ── */}
          {section === "ask" && (
            <div className="px-4 py-3">
              {!aiAnswer && !aiLoading && !query.trim() && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground mb-2">Suggested questions:</p>
                  {[
                    "What is the gross margin trend?",
                    "Which SKUs are below reorder point?",
                    "Compare revenue this week vs last",
                    "Top performing campaigns?",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => setQuery(q)}
                      className="flex w-full items-center gap-2 px-3 py-2 rounded-lg border border-border bg-muted/30 text-xs text-foreground hover:bg-accent transition-colors"
                    >
                      <Sparkles className="w-3 h-3 text-violet-400 shrink-0" aria-hidden />
                      {q}
                    </button>
                  ))}
                </div>
              )}

              {aiLoading && (
                <div className="flex items-center gap-2 py-4">
                  <Loader2 className="w-4 h-4 animate-spin text-violet-400" aria-hidden />
                  <span className="text-sm text-muted-foreground">Thinking…</span>
                </div>
              )}

              {aiAnswer && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-3">
                    <p className="text-sm text-foreground leading-relaxed">{aiAnswer}</p>
                  </div>
                  <button
                    onClick={openInChat}
                    className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                  >
                    Open full AI Chat
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Recent section ── */}
          {section === "recent" && (
            <>
              {recents.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                  No recent items yet
                </p>
              ) : (
                recents.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.path}
                      onClick={() => selectNav(item)}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                        idx === activeIdx
                          ? "bg-brand-500/10 text-brand-400"
                          : "text-foreground hover:bg-accent",
                      )}
                    >
                      <Clock className="w-4 h-4 shrink-0 text-muted-foreground" aria-hidden />
                      <Icon className="w-4 h-4 shrink-0 text-muted-foreground" aria-hidden />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        <p className="text-xs text-muted-foreground truncate">{item.description}</p>
                      </div>
                    </button>
                  );
                })
              )}
            </>
          )}
        </div>

        {/* Footer hint */}
        <div className="shrink-0 flex items-center justify-between px-4 py-2 border-t border-border bg-muted/20">
          <span className="text-[10px] text-muted-foreground">
            <kbd className="border border-border rounded px-1">↑↓</kbd> navigate ·{" "}
            <kbd className="border border-border rounded px-1">↵</kbd> select ·{" "}
            <kbd className="border border-border rounded px-1">Tab</kbd> switch section
          </span>
          <span className="text-[10px] text-muted-foreground">⌘K</span>
        </div>
      </div>
    </div>
  );
}
