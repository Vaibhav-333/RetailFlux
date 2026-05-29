import { Calendar, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useFilters,
  type CompareTo,
  type Preset,
} from "@/state/FilterContext";

const PRESETS: { label: string; value: Preset }[] = [
  { label: "7d", value: "7d" },
  { label: "28d", value: "28d" },
  { label: "QTD", value: "qtd" },
  { label: "YTD", value: "ytd" },
  { label: "Custom", value: "custom" },
];

const COMPARE_OPTIONS: { label: string; value: CompareTo }[] = [
  { label: "No compare", value: "" },
  { label: "Prev period", value: "previous_period" },
  { label: "Prev year", value: "previous_year" },
];

export function DateControl() {
  const {
    preset,
    dateFrom,
    dateTo,
    compareTo,
    setPreset,
    setDateFrom,
    setDateTo,
    setCompareTo,
  } = useFilters();

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-sm">
      {/* Preset segmented buttons */}
      <div className="flex items-center rounded-md border border-border bg-background overflow-hidden">
        {PRESETS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPreset(p.value)}
            className={cn(
              "px-2.5 py-1 text-xs font-medium transition-colors",
              "border-r border-border last:border-r-0",
              preset === p.value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
            aria-pressed={preset === p.value}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Custom date pickers — shown only when preset is "custom" */}
      {preset === "custom" && (
        <div className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded border border-border bg-background px-2 py-0.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            aria-label="From date"
          />
          <span className="text-muted-foreground text-xs">–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded border border-border bg-background px-2 py-0.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            aria-label="To date"
          />
        </div>
      )}

      {/* Compare-to selector */}
      <div className="relative">
        <select
          value={compareTo}
          onChange={(e) => setCompareTo(e.target.value as CompareTo)}
          className={cn(
            "appearance-none rounded border border-border bg-background",
            "pl-2.5 pr-6 py-1 text-xs font-medium transition-colors",
            "focus:outline-none focus:ring-1 focus:ring-primary",
            compareTo
              ? "text-brand-600 dark:text-brand-400 border-brand-400"
              : "text-muted-foreground hover:text-foreground"
          )}
          aria-label="Compare to period"
        >
          {COMPARE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
      </div>
    </div>
  );
}
