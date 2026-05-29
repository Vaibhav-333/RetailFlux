import { X } from "lucide-react";
import { useFilters } from "@/state/FilterContext";
import { cn } from "@/lib/utils";

const CHIP_COLORS: Record<string, string> = {
  region: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-700",
  channel: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300 border-violet-200 dark:border-violet-700",
  category: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700",
  warehouse: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-700",
};

const DEFAULT_CHIP =
  "bg-muted text-muted-foreground border-border";

export function ScopeChips({ className }: { className?: string }) {
  const { parsedDims, removeDim } = useFilters();

  if (parsedDims.length === 0) return null;

  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      <span className="text-xs text-muted-foreground font-medium">Filters:</span>
      {parsedDims.map((dim) => (
        <span
          key={dim.key}
          className={cn(
            "inline-flex items-center gap-1 text-xs font-medium rounded-full",
            "border px-2 py-0.5",
            CHIP_COLORS[dim.key] ?? DEFAULT_CHIP
          )}
        >
          <span className="opacity-70">{dim.key}</span>
          <span>=</span>
          <span>{dim.value}</span>
          <button
            onClick={() => removeDim(dim.key)}
            className="ml-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 p-0.5 transition-colors"
            aria-label={`Remove ${dim.key} filter`}
          >
            <X className="w-2.5 h-2.5" />
          </button>
        </span>
      ))}
    </div>
  );
}
