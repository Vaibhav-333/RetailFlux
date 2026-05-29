import { X, Sparkles, Bell, Info } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { WhyDrawer } from "@/components/ai/WhyDrawer";
import { useQuery } from "@tanstack/react-query";
import { listNotificationsApi } from "@/features/notifications/api";

export interface ContextRailFocus {
  resource: string;
  resourceId: string;
  title: string;
  context?: Record<string, unknown>;
}

interface ContextRailProps {
  open: boolean;
  onClose: () => void;
  focus?: ContextRailFocus | null;
}

type RailTab = "ai" | "notifications" | "info";

/**
 * Right-edge context rail (360px).
 * Shows AI explanations for the focused widget, related notifications, and audit lineage.
 * Hidden by default; toggled via `]` key or the rail button.
 */
export function ContextRail({ open, onClose, focus }: ContextRailProps) {
  const [tab, setTab] = useState<RailTab>("ai");
  const [whyOpen, setWhyOpen] = useState(false);

  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotificationsApi,
    refetchInterval: 30_000,
    retry: 1,
    enabled: open && tab === "notifications",
  });

  if (!open) return null;

  const notifications = notifData?.items ?? [];
  const unread = notifData?.unread_count ?? 0;

  const tabs: { id: RailTab; label: string; icon: React.ElementType; badge?: number }[] = [
    { id: "ai", label: "AI", icon: Sparkles },
    { id: "notifications", label: "Alerts", icon: Bell, badge: unread },
    { id: "info", label: "Info", icon: Info },
  ];

  return (
    <div
      className={cn(
        "fixed inset-y-0 right-0 z-40 w-[360px] flex flex-col bg-card border-l border-border shadow-2xl",
        "animate-in slide-in-from-right duration-200",
      )}
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  "relative flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md transition-colors",
                  tab === t.id
                    ? "bg-brand-600/20 text-brand-400"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent",
                )}
              >
                <Icon className="w-3.5 h-3.5" aria-hidden />
                {t.label}
                {t.badge && t.badge > 0 ? (
                  <span className="absolute -top-1 -right-1 min-w-[14px] h-3.5 rounded-full bg-danger text-white text-[9px] font-bold flex items-center justify-center px-1">
                    {t.badge > 9 ? "9+" : t.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        <button
          onClick={onClose}
          className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Close context rail"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {tab === "ai" && (
          <div className="h-full">
            {focus && !whyOpen ? (
              <div className="p-4 space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-0.5">Focused widget</p>
                  <p className="text-sm font-semibold text-foreground">{focus.title}</p>
                </div>
                <button
                  onClick={() => setWhyOpen(true)}
                  className="flex items-center gap-2 w-full px-3 py-2.5 rounded-lg border border-border bg-muted/30 text-xs text-foreground hover:bg-accent transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5 text-violet-400" aria-hidden />
                  Explain this metric with AI
                </button>
                <p className="text-[10px] text-muted-foreground">
                  Click a KPI card or chart to focus it here for a deeper explanation.
                </p>
              </div>
            ) : whyOpen && focus ? (
              <WhyDrawer
                open
                onClose={() => setWhyOpen(false)}
                resource={focus.resource}
                resourceId={focus.resourceId}
                title={focus.title}
                context={focus.context}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-3 p-8 text-center">
                <Sparkles className="w-8 h-8 text-muted-foreground/50" aria-hidden />
                <div>
                  <p className="text-sm font-medium text-foreground mb-1">No widget focused</p>
                  <p className="text-xs text-muted-foreground">
                    Click any KPI card or chart to see AI explanations here.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "notifications" && (
          <div className="h-full overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 gap-3 text-center p-6">
                <Bell className="w-8 h-8 text-muted-foreground/50" aria-hidden />
                <p className="text-xs text-muted-foreground">No recent notifications.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      "px-4 py-3",
                      !n.read_at ? "bg-muted/20" : "opacity-60",
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <div
                        className={cn(
                          "mt-1 w-1.5 h-1.5 rounded-full shrink-0",
                          n.type === "critical"
                            ? "bg-red-500"
                            : n.type === "warning"
                              ? "bg-amber-500"
                              : "bg-blue-500",
                        )}
                      />
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-foreground truncate">
                          {(n.payload?.title as string) ?? "Alert"}
                        </p>
                        {n.payload?.message && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-3">
                            {n.payload.message as string}
                          </p>
                        )}
                        <p className="text-[10px] text-muted-foreground mt-1">
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "info" && (
          <div className="p-4 space-y-4">
            <div>
              <p className="text-xs font-semibold text-foreground mb-2">Keyboard Shortcuts</p>
              <div className="space-y-1.5">
                {[
                  ["⌘K", "Open command bar"],
                  ["⌘J", "Toggle AI Copilot"],
                  ["⌘P", "Quick navigate"],
                  ["⌘.", "Actions menu"],
                  ["⌘/", "Ask AI"],
                  ["]", "Toggle context rail"],
                  ["?", "Show all shortcuts"],
                ].map(([key, desc]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{desc}</span>
                    <kbd className="text-[10px] border border-border rounded px-1.5 py-0.5 text-muted-foreground font-mono">
                      {key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
            <div className="pt-2 border-t border-border">
              <p className="text-[10px] text-muted-foreground">
                Press <kbd className="border border-border rounded px-1 text-[9px]">]</kbd> to
                close this panel
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
