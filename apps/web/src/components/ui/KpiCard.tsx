import { useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sparkline } from "./Sparkline";
import { TrendDelta } from "./TrendDelta";

export type KpiSize = "xs" | "sm" | "md" | "lg";
export type KpiValueVariant = "default" | "ok" | "bad" | "warn";

interface MenuItem {
  label: string;
  onClick: () => void;
}

export interface KpiCardProps {
  label: string;
  value: string;
  icon?: React.ElementType;
  /** Percentage delta, e.g. 12.4 or -3.2 */
  delta?: number;
  /** Text shown after the delta, e.g. "vs last period" */
  deltaLabel?: string;
  /** Array of numeric values for the sparkline */
  sparkline?: number[];
  /** Small subtext line below the sparkline */
  subline?: string;
  /** Colors the value text */
  valueVariant?: KpiValueVariant;
  /** Shows AI forecasted indicator (violet bottom border on hover) */
  isAIForecasted?: boolean;
  loading?: boolean;
  size?: KpiSize;
  menuItems?: MenuItem[];
  onClick?: () => void;
  /** Warning state — amber tinted border + bg */
  alert?: boolean;
  className?: string;
}

const PAD: Record<KpiSize, string> = {
  xs: "p-3",
  sm: "p-3.5",
  md: "p-4",
  lg: "p-5",
};

const VAL_SIZE: Record<KpiSize, string> = {
  xs: "text-lg",
  sm: "text-xl",
  md: "text-2xl",
  lg: "text-3xl",
};

const LBL_SIZE: Record<KpiSize, string> = {
  xs: "text-[10px]",
  sm: "text-xs",
  md: "text-xs",
  lg: "text-sm",
};

const SPARK_H: Record<KpiSize, number> = {
  xs: 0,
  sm: 26,
  md: 34,
  lg: 46,
};

const VAL_COLOR: Record<KpiValueVariant, string> = {
  default: "text-foreground",
  ok:      "text-[hsl(var(--ok))]",
  bad:     "text-[hsl(var(--bad))]",
  warn:    "text-[hsl(var(--warn))]",
};

export function KpiCard({
  label,
  value,
  icon: Icon,
  delta,
  deltaLabel,
  sparkline,
  subline,
  valueVariant = "default",
  isAIForecasted = false,
  loading = false,
  size = "md",
  menuItems,
  onClick,
  alert = false,
  className,
}: KpiCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const sparkH = SPARK_H[size];
  const showSpark = sparkH > 0 && sparkline && sparkline.length >= 2;
  const sparkColor = isAIForecasted ? "hsl(var(--ai-from))" : "hsl(var(--primary))";

  return (
    <div
      className={cn(
        "kpi-card group relative overflow-hidden select-none",
        PAD[size],
        onClick && "cursor-pointer",
        alert && "border-[hsl(var(--warn)/0.5)] bg-[hsl(var(--warn)/0.04)]",
        className
      )}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(); }
          : undefined
      }
    >
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 rounded-lg bg-muted animate-pulse" aria-hidden />
      )}

      {/* Title row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          {Icon && (
            <Icon
              className={cn(
                "shrink-0 text-muted-foreground",
                size === "lg" ? "w-4 h-4" : "w-3.5 h-3.5"
              )}
              aria-hidden
            />
          )}
          <p className={cn("text-muted-foreground truncate font-medium", LBL_SIZE[size])}>
            {label}
          </p>
        </div>

        {menuItems && menuItems.length > 0 && (
          <div ref={menuRef} className="relative shrink-0 ml-1">
            <button
              className="opacity-0 group-hover:opacity-100 transition-opacity rounded p-0.5 text-muted-foreground hover:text-foreground hover:bg-accent focus-visible:opacity-100"
              onClick={(e) => { e.stopPropagation(); setMenuOpen((v) => !v); }}
              aria-label="Card options"
              aria-haspopup="true"
              aria-expanded={menuOpen}
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-6 z-20 min-w-[140px] rounded-lg border border-border bg-popover shadow-lg py-1 animate-scale-in"
                role="menu"
              >
                {menuItems.map((item, i) => (
                  <button
                    key={i}
                    role="menuitem"
                    className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-accent transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      item.onClick();
                      setMenuOpen(false);
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Value + delta row */}
      <div className="flex items-baseline gap-2 mt-1.5">
        <p
          className={cn(
            "font-semibold tabular-nums tracking-tight truncate",
            VAL_SIZE[size],
            VAL_COLOR[valueVariant]
          )}
          style={{ fontFeatureSettings: '"ss01","cv11","tnum"' }}
        >
          {value}
        </p>
        {delta !== undefined && (
          <TrendDelta delta={delta} size="xs" className="shrink-0" />
        )}
      </div>

      {/* Sparkline */}
      {showSpark && (
        <>
          <div className="my-2 h-px bg-border/40" aria-hidden />
          <Sparkline
            data={sparkline!}
            height={sparkH}
            color={sparkColor}
            fillColor={sparkColor}
          />
        </>
      )}

      {/* Subline / delta label */}
      {(deltaLabel || subline) && (
        <p className="text-[10px] text-muted-foreground mt-1.5 truncate">
          {deltaLabel}
          {deltaLabel && subline && <span className="mx-1 opacity-50">·</span>}
          {subline}
        </p>
      )}

      {/* AI forecasted accent — violet gradient bottom border, reveals on hover */}
      {isAIForecasted && (
        <div
          className="absolute inset-x-0 bottom-0 h-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-[var(--dur-2)]"
          style={{
            background: "linear-gradient(90deg, hsl(var(--ai-from)), hsl(var(--ai-to)))",
          }}
          aria-hidden
        />
      )}
    </div>
  );
}
