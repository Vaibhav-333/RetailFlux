/**
 * CalendarHeatmap — GitHub-style contribution calendar
 *
 * Renders a full year (52 weeks × 7 days) of coloured cells.
 *
 * Usage:
 *   <CalendarHeatmap
 *     data={[{ date: "2024-01-15", value: 1234 }, ...]}
 *     formatValue={(v) => `$${v.toLocaleString()}`}
 *   />
 */
import { useMemo, useState } from "react";

export interface CalendarCell {
  date: string; // "YYYY-MM-DD"
  value: number;
}

interface CalendarHeatmapProps {
  data: CalendarCell[];
  colorFrom?: string;
  colorTo?: string;
  emptyColor?: string;
  formatValue?: (v: number) => string;
  /** Number of weeks to show (default: 52) */
  weeks?: number;
}

const CELL = 12;
const GAP = 2;
const STEP = CELL + GAP;
const DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""];
const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpColor(from: string, to: string, t: number): string {
  const p = (hex: string): [number, number, number] => {
    const c = hex.replace("#", "");
    return [parseInt(c.slice(0,2),16), parseInt(c.slice(2,4),16), parseInt(c.slice(4,6),16)];
  };
  const [r1,g1,b1] = p(from);
  const [r2,g2,b2] = p(to);
  return `rgb(${Math.round(lerp(r1,r2,t))},${Math.round(lerp(g1,g2,t))},${Math.round(lerp(b1,b2,t))})`;
}

function addDays(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function CalendarHeatmap({
  data,
  colorFrom = "#dbeafe",
  colorTo = "#1d4ed8",
  emptyColor = "#f1f5f9",
  formatValue = (v) => String(v),
  weeks = 52,
}: CalendarHeatmapProps) {
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; date: string; value: number | null;
  } | null>(null);

  const { cells, monthLabels } = useMemo(() => {
    const lookup = new Map(data.map((d) => [d.date, d.value]));
    const values = data.map((d) => d.value);
    const maxV = values.length ? Math.max(...values) : 1;
    const minV = values.length ? Math.min(...values) : 0;
    const range = maxV - minV || 1;

    // Start from (weeks) weeks ago, aligned to Sunday
    const today = new Date();
    const endDate = new Date(today);
    const startDate = addDays(endDate, -(weeks * 7 - 1));
    // Snap start to Sunday
    const dayOfWeek = startDate.getDay(); // 0=Sun
    const snapStart = addDays(startDate, -dayOfWeek);

    const cells: Array<{
      date: string;
      value: number | null;
      fill: string;
      week: number;
      day: number;
    }> = [];

    const monthLabels: Array<{ x: number; label: string }> = [];
    let lastMonth = -1;

    for (let w = 0; w < weeks; w++) {
      for (let d = 0; d < 7; d++) {
        const date = addDays(snapStart, w * 7 + d);
        const dateStr = iso(date);
        const value = lookup.get(dateStr) ?? null;

        const fill =
          value === null
            ? emptyColor
            : lerpColor(colorFrom, colorTo, (value - minV) / range);

        cells.push({ date: dateStr, value, fill, week: w, day: d });

        // Month label at first day of each month
        if (d === 0 && date.getMonth() !== lastMonth) {
          lastMonth = date.getMonth();
          monthLabels.push({ x: w * STEP, label: MONTH_ABBR[date.getMonth()] });
        }
      }
    }

    return { cells, monthLabels };
  }, [data, weeks, colorFrom, colorTo, emptyColor]);

  const svgW = weeks * STEP + 20;
  const svgH = 7 * STEP + 30; // 7 days + month labels + day labels

  return (
    <div className="relative overflow-x-auto">
      <svg
        width={svgW}
        height={svgH}
        style={{ minWidth: svgW }}
        aria-label="Calendar heatmap"
      >
        {/* Month labels */}
        <g transform="translate(20,0)">
          {monthLabels.map((m, i) => (
            <text
              key={i}
              x={m.x}
              y={9}
              fontSize={9}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {m.label}
            </text>
          ))}
        </g>

        {/* Day-of-week labels */}
        <g transform={`translate(0,14)`}>
          {DAY_LABELS.map((lbl, i) => (
            <text
              key={i}
              x={8}
              y={i * STEP + CELL / 2 + 3}
              fontSize={8}
              fill="currentColor"
              textAnchor="middle"
              className="text-muted-foreground"
            >
              {lbl}
            </text>
          ))}
        </g>

        {/* Cells */}
        <g transform="translate(20,14)">
          {cells.map((c) => (
            <rect
              key={c.date}
              x={c.week * STEP}
              y={c.day * STEP}
              width={CELL}
              height={CELL}
              fill={c.fill}
              rx={2}
              ry={2}
              onMouseEnter={(e) =>
                setTooltip({ x: e.clientX, y: e.clientY, date: c.date, value: c.value })
              }
              onMouseLeave={() => setTooltip(null)}
              style={{ cursor: "default" }}
            />
          ))}
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none rounded bg-popover border border-border shadow-lg px-2 py-1 text-xs"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          <span className="font-medium">{tooltip.date}</span>
          {tooltip.value !== null ? (
            <span className="ml-1.5 text-muted-foreground">
              {formatValue(tooltip.value)}
            </span>
          ) : (
            <span className="ml-1.5 text-muted-foreground">No data</span>
          )}
        </div>
      )}
    </div>
  );
}
