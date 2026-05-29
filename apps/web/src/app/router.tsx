import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { UploadsPage } from "@/pages/UploadsPage";
import { SalesPage } from "@/pages/SalesPage";
import { MarketingPage } from "@/pages/MarketingPage";
import { OperationsPage } from "@/pages/OperationsPage";
import { FinancePage } from "@/pages/FinancePage";
import { ProcurementPage } from "@/pages/ProcurementPage";
import { ChatPage } from "@/pages/ChatPage";
import { ObservabilityPage } from "@/pages/ObservabilityPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { TasksListPage } from "@/pages/TasksListPage";
import { TasksBoardPage } from "@/pages/TasksBoardPage";
import { TasksAnalyticsPage } from "@/pages/TasksAnalyticsPage";
import { TasksCalendarPage } from "@/pages/TasksCalendarPage";
import { TasksTimelinePage } from "@/pages/TasksTimelinePage";
import { SprintsPage } from "@/pages/SprintsPage";
import { InventoryPage } from "@/pages/InventoryPage";
import { InventorySkuPage } from "@/pages/InventorySkuPage";
import { CopilotPage } from "@/pages/CopilotPage";
import { ProfitIntelligencePage } from "@/pages/ProfitIntelligencePage";
import { AutoReplenishmentPage } from "@/pages/AutoReplenishmentPage";
import { ScenariosPage } from "@/pages/ScenariosPage";
import { useAuthStore } from "@/features/auth/authStore";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "sales", element: <SalesPage /> },
      { path: "marketing", element: <MarketingPage /> },
      { path: "operations", element: <OperationsPage /> },
      { path: "finance", element: <FinancePage /> },
      { path: "procurement", element: <ProcurementPage /> },
      { path: "uploads", element: <UploadsPage /> },
      { path: "ai-chat", element: <ChatPage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "observability", element: <ObservabilityPage /> },
      { path: "tasks", element: <TasksListPage /> },
      { path: "tasks/board", element: <TasksBoardPage /> },
      { path: "tasks/analytics", element: <TasksAnalyticsPage /> },
      { path: "tasks/calendar", element: <TasksCalendarPage /> },
      { path: "tasks/timeline", element: <TasksTimelinePage /> },
      { path: "tasks/sprints", element: <SprintsPage /> },
      { path: "inventory", element: <InventoryPage /> },
      { path: "inventory/:sku", element: <InventorySkuPage /> },
      { path: "copilot", element: <CopilotPage /> },
      { path: "finance/profit-intelligence", element: <ProfitIntelligencePage /> },
      { path: "procurement/auto-replenishment", element: <AutoReplenishmentPage /> },
      { path: "scenarios", element: <ScenariosPage /> },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/login" replace />,
  },
]);
