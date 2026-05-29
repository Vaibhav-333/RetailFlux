/**
 * Command registry — maps verb IDs to their handlers.
 * The CommandPalette's "Do" section reads from this registry.
 * Each feature registers its own commands; the palette renders them all.
 */
export interface Command {
  id: string;
  label: string;
  description: string;
  /** Optional keyboard hint string, e.g. "⌘⇧R" */
  shortcut?: string;
  /** Category shown in the Do section */
  category?: string;
  handler: () => void | Promise<void>;
}

const _registry = new Map<string, Command>();

export const commandRegistry = {
  register(cmd: Command): void {
    _registry.set(cmd.id, cmd);
  },

  unregister(id: string): void {
    _registry.delete(id);
  },

  get(id: string): Command | undefined {
    return _registry.get(id);
  },

  getAll(): Command[] {
    return Array.from(_registry.values());
  },
};

// ── Built-in global commands ───────────────────────────────────────────────────
// Feature-specific commands are registered by their respective pages/hooks.

commandRegistry.register({
  id: "refresh-insights",
  label: "Refresh AI Insights",
  description: "Regenerate AI insights from latest data",
  category: "AI",
  handler: () => {
    // Invalidate the insights cache; the actual TanStack Query invalidation
    // happens in the CommandPalette handler which has access to queryClient.
    window.dispatchEvent(new CustomEvent("rf:command", { detail: { id: "refresh-insights" } }));
  },
});

commandRegistry.register({
  id: "toggle-density",
  label: "Toggle Compact Mode",
  description: "Switch between comfortable and compact UI density",
  category: "Display",
  handler: () => {
    document.body.classList.toggle("density-compact");
    const compact = document.body.classList.contains("density-compact");
    localStorage.setItem("rf-density", compact ? "compact" : "comfortable");
  },
});

commandRegistry.register({
  id: "open-settings",
  label: "Open Settings",
  description: "Manage profile, team, and alert preferences",
  category: "Navigation",
  handler: () => {
    window.dispatchEvent(new CustomEvent("rf:navigate", { detail: { path: "/dashboard/settings" } }));
  },
});

commandRegistry.register({
  id: "export-report",
  label: "Export Report",
  description: "Download a CSV or JSON report for any department",
  category: "Data",
  handler: () => {
    window.dispatchEvent(new CustomEvent("rf:navigate", { detail: { path: "/dashboard/reports" } }));
  },
});
