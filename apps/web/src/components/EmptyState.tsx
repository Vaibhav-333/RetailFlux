import { Filter, Lock, PlugZap, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

type EmptyVariant = "no-data" | "filter-empty" | "permission" | "not-connected" | "default";

interface EmptyStateProps {
  variant?: EmptyVariant;
  dept?: string;
  title?: string;
  message?: string;
  action?: { label: string; to?: string; onClick?: () => void };
  className?: string;
}

const VARIANTS: Record<
  EmptyVariant,
  {
    Icon: React.ElementType;
    iconClass: string;
    defaultTitle: (dept?: string) => string;
    defaultMessage: (dept?: string) => string;
    defaultAction?: { label: string; to: string };
  }
> = {
  "no-data": {
    Icon: UploadCloud,
    iconClass: "text-brand-400",
    defaultTitle: (dept) => `No ${dept ?? ""} data yet`.trim(),
    defaultMessage: (dept) =>
      `Upload your ${dept ? dept.toLowerCase() + " " : ""}data to start seeing analytics here.`,
    defaultAction: { label: "Upload Data", to: "/dashboard/uploads" },
  },
  "filter-empty": {
    Icon: Filter,
    iconClass: "text-muted-foreground",
    defaultTitle: () => "No results found",
    defaultMessage: () =>
      "Your current filters returned no results. Try adjusting the date range or clearing filters.",
  },
  "permission": {
    Icon: Lock,
    iconClass: "text-amber-400",
    defaultTitle: () => "Access restricted",
    defaultMessage: () =>
      "You don't have permission to view this data. Contact your administrator to request access.",
  },
  "not-connected": {
    Icon: PlugZap,
    iconClass: "text-muted-foreground",
    defaultTitle: () => "Integration not connected",
    defaultMessage: () =>
      "This data source is not connected. Upload a CSV or connect your integration to see analytics.",
    defaultAction: { label: "Upload Data", to: "/dashboard/uploads" },
  },
  "default": {
    Icon: UploadCloud,
    iconClass: "text-muted-foreground",
    defaultTitle: () => "Nothing here yet",
    defaultMessage: () => "There is no data to display right now.",
  },
};

export function EmptyState({
  variant = "no-data",
  dept,
  title,
  message,
  action,
  className,
}: EmptyStateProps) {
  const cfg = VARIANTS[variant];
  const { Icon, iconClass } = cfg;
  const resolvedTitle = title ?? cfg.defaultTitle(dept);
  const resolvedMessage = message ?? cfg.defaultMessage(dept);
  const resolvedAction = action ?? cfg.defaultAction;

  return (
    <div className={cn("flex flex-col items-center justify-center gap-4 py-14 text-center px-6", className)}>
      <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center">
        <Icon className={cn("w-7 h-7", iconClass)} aria-hidden="true" />
      </div>
      <div className="max-w-xs">
        <p className="text-base font-semibold text-foreground">{resolvedTitle}</p>
        <p className="mt-1.5 text-sm text-muted-foreground">{resolvedMessage}</p>
      </div>
      {resolvedAction && (
        resolvedAction.to ? (
          <Link
            to={resolvedAction.to}
            className="mt-1 inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none"
          >
            {resolvedAction.label}
          </Link>
        ) : (
          <button
            onClick={(resolvedAction as { onClick?: () => void }).onClick}
            className="mt-1 inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none"
          >
            {resolvedAction.label}
          </button>
        )
      )}
    </div>
  );
}
