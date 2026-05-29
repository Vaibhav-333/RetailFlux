/**
 * SmartChart — opinionated chart card wrapper for Recharts
 *
 * Features:
 *  • Consistent card chrome (title, controls)
 *  • Synced cursor: pass the same syncId to multiple SmartCharts
 *  • Brush/zoom toggle per chart
 *  • Legend-key toggle (hide/show individual series)
 *  • Cross-filter hook (passes onDataClick to children via render prop)
 */
import { useCallback, useState, type ReactNode } from "react";
import { ZoomIn, ZoomOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChartCursor } from "@/state/ChartCursorContext";

export interface LegendKey {
  key: string;
  color: string;
  label?: string;
}

export interface SmartChartRenderProps {
  /** Recharts syncId for cursor sync across sibling charts */
  syncId: string | undefined;
  /** Whether the Brush component should be rendered inside the chart */
  brush: boolean;
  /** Set of series keys whose data should be hidden */
  hiddenKeys: Set<string>;
  /** Call this from chart onClick to register a cross-filter */
  onDataClick?: (dimKey: string, value: string) => void;
  /** Current global cursor X from ChartCursorContext — use as Recharts activeLabel */
  activeX: string | number | null;
  /** Broadcast the hovered X position to all sibling charts via ChartCursorContext */
  onCursorMove: (x: string | number | null) => void;
}

export interface SmartChartProps {
  title: string;
  /** Recharts syncId — charts sharing the same value will sync their cursor */
  syncId?: string;
  /** Show Brush zoom control initially (default false) */
  defaultBrush?: boolean;
  /** Series keys to render as toggleable legend items */
  legendKeys?: LegendKey[];
  /** Called when user clicks a data point and cross-filter is desired */
  onDataClick?: (dimKey: string, value: string) => void;
  children: (props: SmartChartRenderProps) => ReactNode;
  className?: string;
  /** Extra controls to render in the title bar */
  extraControls?: ReactNode;
  /** Skip the card chrome — render children inline (for embedding) */
  bare?: boolean;
}

export function SmartChart({
  title,
  syncId,
  defaultBrush = false,
  legendKeys = [],
  onDataClick,
  children,
  className,
  extraControls,
  bare = false,
}: SmartChartProps) {
  const [brush, setBrush] = useState(defaultBrush);
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
  const { activeX, setActiveX } = useChartCursor();

  function toggleKey(k: string) {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  }

  const onCursorMove = useCallback(
    (x: string | number | null) => setActiveX(x),
    [setActiveX]
  );

  const renderProps: SmartChartRenderProps = {
    syncId,
    brush,
    hiddenKeys,
    onDataClick,
    activeX,
    onCursorMove,
  };

  if (bare) {
    return <>{children(renderProps)}</>;
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-5 shadow-sm",
        className
      )}
    >
      {/* Title bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>

        <div className="flex flex-wrap items-center gap-2">
          {/* Legend toggles */}
          {legendKeys.map((lk) => {
            const hidden = hiddenKeys.has(lk.key);
            return (
              <button
                key={lk.key}
                onClick={() => toggleKey(lk.key)}
                className={cn(
                  "flex items-center gap-1.5 text-xs rounded px-1.5 py-0.5 transition-colors",
                  hidden
                    ? "opacity-40 hover:opacity-70"
                    : "opacity-100 hover:opacity-80"
                )}
                aria-pressed={!hidden}
                title={`Toggle ${lk.label ?? lk.key}`}
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0 transition-colors"
                  style={{ background: hidden ? "#9ca3af" : lk.color }}
                />
                <span className="text-muted-foreground">
                  {lk.label ?? lk.key}
                </span>
              </button>
            );
          })}

          {/* Extra controls slot */}
          {extraControls}

          {/* Brush toggle */}
          <button
            onClick={() => setBrush((b) => !b)}
            className={cn(
              "flex items-center gap-1 text-xs px-1.5 py-0.5 rounded transition-colors",
              brush
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
            title="Toggle zoom / brush"
            aria-pressed={brush}
          >
            {brush ? (
              <ZoomOut className="w-3 h-3" />
            ) : (
              <ZoomIn className="w-3 h-3" />
            )}
            <span className="hidden sm:inline">Zoom</span>
          </button>
        </div>
      </div>

      {/* Chart content */}
      {children(renderProps)}
    </div>
  );
}
