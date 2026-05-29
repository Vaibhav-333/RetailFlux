import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  BarChart3,
  CalendarRange,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Boxes,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  Megaphone,
  RefreshCcw,
  Settings,
  ShoppingCart,
  Sparkles,
  Truck,
  Upload,
  Warehouse,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/types";

interface NavItem {
  label: string;
  icon: React.ElementType;
  path: string;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Master",
    icon: LayoutDashboard,
    path: "/dashboard",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  { label: "Sales", icon: ShoppingCart, path: "/dashboard/sales", roles: ["ceo", "admin", "sales", "marketing", "finance", "operations"] },
  { label: "Marketing", icon: Megaphone, path: "/dashboard/marketing", roles: ["ceo", "admin", "sales", "marketing", "finance"] },
  { label: "Operations", icon: Warehouse, path: "/dashboard/operations", roles: ["ceo", "admin", "sales", "finance", "operations", "procurement"] },
  { label: "Finance", icon: DollarSign, path: "/dashboard/finance", roles: ["ceo", "admin", "finance"] },
  { label: "Profit Intelligence", icon: LineChart, path: "/dashboard/finance/profit-intelligence", roles: ["ceo", "admin", "finance"] },
  { label: "Procurement", icon: Truck, path: "/dashboard/procurement", roles: ["ceo", "admin", "finance", "operations", "procurement"] },
  { label: "Auto-Replenishment", icon: RefreshCcw, path: "/dashboard/procurement/auto-replenishment", roles: ["ceo", "admin", "finance", "operations", "procurement"] },
  { label: "Scenarios", icon: FlaskConical, path: "/dashboard/scenarios", roles: ["ceo", "admin", "finance"] },
];

const BOTTOM_ITEMS: NavItem[] = [
  {
    label: "Tasks",
    icon: CheckSquare,
    path: "/dashboard/tasks",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  {
    label: "Sprints",
    icon: CalendarRange,
    path: "/dashboard/tasks/sprints",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  {
    label: "Inventory",
    icon: Boxes,
    path: "/dashboard/inventory",
    roles: ["ceo", "admin", "finance", "operations", "procurement"],
  },
  {
    label: "Uploads",
    icon: Upload,
    path: "/dashboard/uploads",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  {
    label: "Copilot",
    icon: Sparkles,
    path: "/dashboard/copilot",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  {
    label: "Reports",
    icon: BarChart3,
    path: "/dashboard/reports",
    roles: ["ceo", "admin", "sales", "marketing", "finance", "operations", "procurement"],
  },
  {
    label: "Settings",
    icon: Settings,
    path: "/dashboard/settings",
    roles: ["ceo", "admin"],
  },
  {
    label: "Observability",
    icon: Activity,
    path: "/dashboard/observability",
    roles: ["ceo", "admin"],
  },
];

interface SidebarProps {
  role: UserRole;
  /** On mobile, called when a nav item is clicked or X is pressed. */
  onClose?: () => void;
  /** True when rendered inside the mobile overlay drawer. */
  mobile?: boolean;
}

export function Sidebar({ role, onClose, mobile = false }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(role));
  const visibleBottom = BOTTOM_ITEMS.filter((item) => item.roles.includes(role));

  // Mobile drawer is always expanded
  const isCollapsed = mobile ? false : collapsed;

  return (
    <aside
      className={cn(
        "flex flex-col h-screen bg-card border-r border-border transition-all duration-200 shrink-0",
        isCollapsed ? "w-16" : "w-60"
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo + close button (mobile) */}
      <div className="flex items-center gap-3 h-14 px-4 border-b border-border shrink-0">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
          <span className="text-white text-xs font-bold">RF</span>
        </div>
        {!isCollapsed && (
          <span className="font-semibold text-sm tracking-tight text-foreground flex-1">
            RetailFlux
          </span>
        )}
        {mobile && onClose && (
          <button
            onClick={onClose}
            className="ml-auto w-6 h-6 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Primary nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {visibleItems.map((item) => (
          <NavItem
            key={item.path}
            item={item}
            collapsed={isCollapsed}
            active={location.pathname === item.path}
            onNavigate={onClose}
          />
        ))}
      </nav>

      {/* Bottom nav */}
      <div className="py-3 px-2 border-t border-border space-y-0.5">
        {visibleBottom.map((item) => (
          <NavItem
            key={item.path}
            item={item}
            collapsed={isCollapsed}
            active={location.pathname === item.path}
            onNavigate={onClose}
          />
        ))}
      </div>

      {/* Collapse toggle — desktop only */}
      {!mobile && (
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center h-10 border-t border-border hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      )}
    </aside>
  );
}

function NavItem({
  item,
  collapsed,
  active,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.path}
      end={item.path === "/dashboard"}
      title={collapsed ? item.label : undefined}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-3 px-2 py-2 rounded-md text-sm font-medium transition-colors",
        active
          ? "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
    >
      <Icon className="w-4 h-4 shrink-0" />
      {!collapsed && <span>{item.label}</span>}
    </NavLink>
  );
}
