import { Bell, Moon, Sun, Search, LogOut, User, Menu, Check, Sparkles, ClipboardCheck } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { CommandPalette } from "@/components/CommandPalette";
import { CopilotDock } from "@/components/ai/CopilotDock";
import {
  listNotificationsApi,
  markAllNotificationsReadApi,
  markNotificationReadApi,
} from "@/features/notifications/api";
import { listPendingApprovalsApi, decideApprovalApi } from "@/features/tasks/api";
import { toast } from "sonner";
import type { Notification } from "@/types";

type PaletteSection = "go" | "do" | "ask" | "recent";

interface TopBarProps {
  userName: string;
  userRole: string;
  onLogout: () => void;
  darkMode: boolean;
  onToggleDark: () => void;
  onMenuOpen: () => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const TYPE_COLOR: Record<string, string> = {
  info: "bg-blue-500",
  warning: "bg-amber-500",
  critical: "bg-red-500",
};

export function TopBar({
  userName,
  userRole,
  onLogout,
  darkMode,
  onToggleDark,
  onMenuOpen,
}: TopBarProps) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteSection, setPaletteSection] = useState<PaletteSection>("go");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const approvalRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ── Notifications ──────────────────────────────────────────────────────────
  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotificationsApi,
    refetchInterval: 30_000,
    retry: 1,
  });

  const markRead = useMutation({
    mutationFn: markNotificationReadApi,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAll = useMutation({
    mutationFn: markAllNotificationsReadApi,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const unreadCount = notifData?.unread_count ?? 0;

  // ── Approvals ──────────────────────────────────────────────────────────────
  const { data: approvalData } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => listPendingApprovalsApi({ size: 10 }),
    refetchInterval: 60_000,
    retry: 1,
  });

  const decideApproval = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approved" | "rejected" }) =>
      decideApprovalApi(id, decision),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["approvals", "pending"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success(vars.decision === "approved" ? "Approved" : "Rejected");
    },
    onError: () => toast.error("Failed to process decision"),
  });

  const pendingCount = approvalData?.total ?? 0;

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;

      if (mod && e.key === "k") {
        e.preventDefault();
        setPaletteSection("go");
        setPaletteOpen((o) => !o);
      } else if (mod && e.key === "p") {
        e.preventDefault();
        setPaletteSection("go");
        setPaletteOpen(true);
      } else if (mod && e.key === ".") {
        e.preventDefault();
        setPaletteSection("do");
        setPaletteOpen(true);
      } else if (mod && e.key === "/") {
        e.preventDefault();
        setPaletteSection("ask");
        setPaletteOpen(true);
      } else if (mod && e.key === "j") {
        e.preventDefault();
        setCopilotOpen((o) => !o);
      } else if (e.key === "]" && !e.metaKey && !e.ctrlKey) {
        // ] closes/opens context rail — dispatched by AppShell
        window.dispatchEvent(new CustomEvent("rf:toggle-rail"));
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ── Click-outside for dropdowns ────────────────────────────────────────────
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        defaultSection={paletteSection}
      />

      <CopilotDock open={copilotOpen} onClose={() => setCopilotOpen(false)} />

      <header
        className="h-14 shrink-0 flex items-center justify-between px-4 border-b border-border bg-card"
        style={{ height: "var(--topbar-height)" }}
      >
        {/* Left: hamburger (mobile) + search */}
        <div className="flex items-center gap-2">
          <button
            onClick={onMenuOpen}
            className="md:hidden w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Open navigation"
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Search / command palette trigger */}
          <button
            onClick={() => { setPaletteSection("go"); setPaletteOpen(true); }}
            className="flex items-center gap-2 bg-muted rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent transition-colors w-44 sm:w-72"
            aria-label="Open command palette"
          >
            <Search className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline flex-1 text-left">Search analytics…</span>
            <kbd className="hidden sm:inline text-xs border border-border rounded px-1">⌘K</kbd>
          </button>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-1">
          {/* AI Copilot button */}
          <button
            onClick={() => setCopilotOpen((o) => !o)}
            className={cn(
              "w-8 h-8 flex items-center justify-center rounded-md transition-colors",
              copilotOpen
                ? "bg-violet-500/20 text-violet-400"
                : "hover:bg-accent text-muted-foreground hover:text-violet-400",
            )}
            aria-label="Toggle AI Copilot (⌘J)"
            title="AI Copilot (⌘J)"
          >
            <Sparkles className="w-4 h-4" />
          </button>

          {/* Approval inbox */}
          <div ref={approvalRef} className="relative">
            <button
              onClick={() => setApprovalOpen((o) => !o)}
              className="relative w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              aria-label={`Approvals${pendingCount > 0 ? ` (${pendingCount} pending)` : ""}`}
              title="Pending Approvals"
            >
              <ClipboardCheck className="w-4 h-4" />
              {pendingCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-amber-500 text-white text-[9px] font-bold flex items-center justify-center leading-none">
                  {pendingCount > 9 ? "9+" : pendingCount}
                </span>
              )}
            </button>

            {approvalOpen && (
              <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border bg-card shadow-xl">
                <div className="flex items-center justify-between px-4 py-2 border-b">
                  <span className="text-sm font-semibold">Pending Approvals</span>
                  <button
                    onClick={() => setApprovalOpen(false)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    ✕
                  </button>
                </div>
                <div className="max-h-80 overflow-y-auto divide-y">
                  {(approvalData?.items ?? []).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-6">
                      No pending approvals
                    </p>
                  )}
                  {(approvalData?.items ?? []).map((a) => (
                    <div key={a.id} className="px-4 py-3 space-y-2">
                      <p className="text-xs text-muted-foreground">Task #{a.task_id.slice(0, 8)}</p>
                      <p className="text-xs text-muted-foreground">
                        Requested {new Date(a.created_at).toLocaleDateString()}
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => decideApproval.mutate({ id: a.id, decision: "approved" })}
                          disabled={decideApproval.isPending}
                          className="flex-1 rounded bg-green-600 text-white text-xs py-1 hover:bg-green-700 disabled:opacity-50 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => decideApproval.mutate({ id: a.id, decision: "rejected" })}
                          disabled={decideApproval.isPending}
                          className="flex-1 rounded bg-destructive text-destructive-foreground text-xs py-1 hover:bg-destructive/90 disabled:opacity-50 transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="px-4 py-2 border-t text-center">
                  <button
                    onClick={() => { navigate("/dashboard/tasks"); setApprovalOpen(false); }}
                    className="text-xs text-primary hover:underline"
                  >
                    View all tasks →
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Dark mode toggle */}
          <button
            onClick={onToggleDark}
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Toggle dark mode"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Notifications */}
          <div ref={notifRef} className="relative">
            <button
              onClick={() => setNotifOpen((o) => !o)}
              className="relative w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
              aria-expanded={notifOpen}
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-danger text-white text-[9px] font-bold flex items-center justify-center leading-none">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-full mt-1 w-80 bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden animate-fade-in">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                  <p className="text-sm font-semibold text-foreground">Notifications</p>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => markAll.mutate()}
                      disabled={markAll.isPending}
                      className="text-xs text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors disabled:opacity-50"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-72 overflow-y-auto">
                  {!notifData || notifData.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                      <Bell className="w-6 h-6 text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">No notifications yet</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Run an alert check from Settings to get started
                      </p>
                    </div>
                  ) : (
                    notifData.items.map((n: Notification) => (
                      <div
                        key={n.id}
                        className={cn(
                          "flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 transition-colors",
                          n.read_at ? "opacity-60" : "bg-muted/30",
                        )}
                      >
                        <div
                          className={cn(
                            "mt-1 w-2 h-2 rounded-full shrink-0",
                            TYPE_COLOR[n.type] ?? "bg-muted-foreground",
                          )}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-foreground truncate">
                            {(n.payload.title as string) ?? "Alert"}
                          </p>
                          {n.payload.message && (
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                              {n.payload.message as string}
                            </p>
                          )}
                          <p className="text-[10px] text-muted-foreground mt-1">
                            {timeAgo(n.created_at)}
                          </p>
                        </div>
                        {!n.read_at && (
                          <button
                            onClick={() => markRead.mutate(n.id)}
                            className="shrink-0 w-6 h-6 flex items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                            aria-label="Mark as read"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Profile */}
          <div ref={profileRef} className="relative">
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-accent transition-colors"
              aria-label="User menu"
              aria-expanded={profileOpen}
              aria-haspopup="menu"
            >
              <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center">
                <span className="text-white text-xs font-semibold">
                  {userName.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-xs font-medium text-foreground leading-tight">{userName}</p>
                <p className="text-xs text-muted-foreground capitalize leading-tight">{userRole}</p>
              </div>
            </button>

            {profileOpen && (
              <div className="absolute right-0 top-full mt-1 w-44 bg-card border border-border rounded-lg shadow-lg z-50 py-1 animate-fade-in">
                <button
                  onClick={() => { navigate("/dashboard/settings"); setProfileOpen(false); }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  <User className="w-4 h-4" />
                  Settings
                </button>
                <div className="my-1 border-t border-border" />
                <button
                  onClick={onLogout}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-danger hover:bg-danger/10 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
