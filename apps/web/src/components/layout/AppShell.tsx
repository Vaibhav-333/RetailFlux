import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ContextRail, type ContextRailFocus } from "./ContextRail";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useAuthStore } from "@/features/auth/authStore";
import { getAccessToken, refreshAccessToken } from "@/lib/api";
import { useRealtimeAlerts } from "@/hooks/useRealtimeAlerts";
import { FilterProvider } from "@/state/FilterContext";
import { DateControl } from "@/components/DateControl";
import { ScopeChips } from "@/components/ScopeChips";
import { realtimeBus } from "@/state/realtimeBus";
import { useQueryClient } from "@tanstack/react-query";
import { OnboardingWizard } from "@/components/onboarding/Wizard";
import { KeyboardShortcuts, useKeyboardShortcuts } from "@/components/KeyboardShortcuts";
import { ChartCursorProvider } from "@/state/ChartCursorContext";

function WsProvider() {
  useRealtimeAlerts();
  return null;
}

const DARK_MODE_KEY = "retailflux-dark-mode";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Master Dashboard — RetailFlux",
  "/dashboard/sales": "Sales Analytics — RetailFlux",
  "/dashboard/marketing": "Marketing Analytics — RetailFlux",
  "/dashboard/operations": "Operations Analytics — RetailFlux",
  "/dashboard/finance": "Finance Analytics — RetailFlux",
  "/dashboard/procurement": "Procurement Analytics — RetailFlux",
  "/dashboard/uploads": "Data Uploads — RetailFlux",
  "/dashboard/ai-chat": "AI Chat — RetailFlux",
  "/dashboard/reports": "Reports — RetailFlux",
  "/dashboard/settings": "Settings — RetailFlux",
  "/dashboard/tasks": "Tasks — RetailFlux",
  "/dashboard/tasks/board": "Task Board — RetailFlux",
  "/dashboard/tasks/analytics": "Task Analytics — RetailFlux",
  "/dashboard/tasks/calendar": "Task Calendar — RetailFlux",
  "/dashboard/tasks/timeline": "Task Timeline — RetailFlux",
  "/dashboard/tasks/sprints": "Sprint Planning — RetailFlux",
};

const FILTER_ROUTES = new Set([
  "/dashboard/sales",
  "/dashboard/marketing",
  "/dashboard/operations",
  "/dashboard/finance",
  "/dashboard/procurement",
]);

function FilterBar({ pathname }: { pathname: string }) {
  if (!FILTER_ROUTES.has(pathname)) return null;
  return (
    <div className="shrink-0 flex flex-wrap items-center gap-3 px-5 py-2 border-b border-border bg-card">
      <DateControl />
      <ScopeChips />
    </div>
  );
}

/** Wire realtimeBus to sonner toasts, deduped by the bus itself. */
function RealtimeBusProvider() {
  const queryClient = useQueryClient();

  useEffect(() => {
    function onAlert(evt: { type: string; key: string; message?: string }) {
      toast.info(evt.message ?? "New alert received", {
        description: "Check the notifications panel for details.",
        action: { label: "View", onClick: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }) },
      });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }

    realtimeBus.on("alert", onAlert);
    return () => realtimeBus.off("alert", onAlert);
  }, [queryClient]);

  return null;
}

export function AppShell() {
  const { user, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [railOpen, setRailOpen] = useState(false);
  const [railFocus, setRailFocus] = useState<ContextRailFocus | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const { open: kbOpen, setOpen: setKbOpen } = useKeyboardShortcuts();
  const location = useLocation();

  // On hard reload the in-memory token is gone but the refresh cookie survives.
  useEffect(() => {
    if (getAccessToken()) {
      setAuthReady(true);
      return;
    }
    refreshAccessToken()
      .then(() => setAuthReady(true))
      .catch(() => logout());
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Show the onboarding wizard for new users (step 0 = never completed).
  useEffect(() => {
    if (user && (user.onboarding_step ?? 0) === 0) {
      setShowWizard(true);
    }
  }, [user]);

  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(DARK_MODE_KEY);
      if (stored !== null) return stored === "true";
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem(DARK_MODE_KEY, String(darkMode));
  }, [darkMode]);

  useEffect(() => {
    document.title = PAGE_TITLES[location.pathname] ?? "RetailFlux";
  }, [location.pathname]);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // ] key toggles the rail (dispatched by TopBar keyboard handler)
  useEffect(() => {
    function onToggleRail() {
      setRailOpen((o) => !o);
    }
    window.addEventListener("rf:toggle-rail", onToggleRail);
    return () => window.removeEventListener("rf:toggle-rail", onToggleRail);
  }, []);

  // Global event for widgets to "focus" themselves in the ContextRail
  useEffect(() => {
    function onFocus(e: Event) {
      const detail = (e as CustomEvent<ContextRailFocus>).detail;
      setRailFocus(detail);
      setRailOpen(true);
    }
    window.addEventListener("rf:focus-widget", onFocus);
    return () => window.removeEventListener("rf:focus-widget", onFocus);
  }, []);

  if (!user || !authReady) return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="animate-spin h-8 w-8 rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );

  return (
    <ChartCursorProvider>
    <FilterProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        {authReady && <WsProvider />}
        <RealtimeBusProvider />

        {/* Desktop sidebar */}
        <div className="hidden md:flex">
          <Sidebar role={user.role} />
        </div>

        {/* Mobile sidebar overlay */}
        {mobileOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-hidden="true"
            />
            <div className="fixed inset-y-0 left-0 z-50 md:hidden">
              <Sidebar role={user.role} onClose={() => setMobileOpen(false)} mobile />
            </div>
          </>
        )}

        {/* Main content column */}
        <div className="flex flex-col flex-1 overflow-hidden min-w-0">
          <TopBar
            userName={user.name}
            userRole={user.role}
            onLogout={logout}
            darkMode={darkMode}
            onToggleDark={() => setDarkMode((d) => !d)}
            onMenuOpen={() => setMobileOpen(true)}
          />

          <FilterBar pathname={location.pathname} />

          <main
            className="flex-1 overflow-y-auto p-5 bg-background"
            style={{ marginRight: railOpen ? "360px" : undefined }}
          >
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </main>
        </div>

        {/* Right-edge context rail */}
        <ContextRail
          open={railOpen}
          onClose={() => setRailOpen(false)}
          focus={railFocus}
        />
      </div>

      {/* Onboarding wizard — shown once for new users (onboarding_step === 0) */}
      {showWizard && (
        <OnboardingWizard onComplete={() => setShowWizard(false)} />
      )}

      {/* Global keyboard shortcuts modal — toggle with ? */}
      <KeyboardShortcuts open={kbOpen} onClose={() => setKbOpen(false)} />
    </FilterProvider>
    </ChartCursorProvider>
  );
}
