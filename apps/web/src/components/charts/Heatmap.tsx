/**
 * Heatmap — pure SVG grid heatmap
 *
 * Usage:
 *   <Heatmap
 *     data={[{ x: "Mon", y: "Jan", value: 42 }, ...]}
 *     width={500}
 *     height={200}
 *   />
 */
import { useMemo, useState } from "react";

export interface HeatmapCell {
  x: string;
  y: string;
  value: number;
}

interface HeatmapProps {
  data: HeatmapCell[];
  width?: number;
  height?: number;
  colorFrom?: string;
  colorTo?: string;
  /** Labels below x-axis */
  xLabel?: string;
  /** Labels left of y-axis */
  yLabel?: string;
  formatValue?: (v: number) => string;
}

const MARGIN = { top: 8, right: 8, bottom: 32, left: 48 };
const CELL_GAP = 2;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Linearly interpolate between two hex colours */
function lerpColor(from: string, to: string, t: number): string {
  const parse = (hex: string): [number, number, number] => {
    const c = hex.replace("#", "");
    return [
      parseInt(c.slice(0, 2), 16),
      parseInt(c.slice(2, 4), 16),
      parseInt(c.slice(4, 6), 16),
    ];
  };
  const [r1, g1, b1] = parse(from);
  const [r2, g2, b2] = parse(to);
  const r = Math.round(lerp(r1, r2, t));
  const g = Math.round(lerp(g1, g2, t));
  const b = Math.round(lerp(b1, b2, t));
  return `rgb(${r},${g},${b})`;
}

export function Heatmap({
  data,
  width = 480,
  height = 200,
  colorFrom = "#e0f2fe",
  colorTo = "#0369a1",
  formatValue = (v) => String(v),
}: HeatmapProps) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; cell: HeatmapCell } | null>(
    null
  );

  const { xs, ys, cellW, cellH, minV, range } = useMemo(() => {
    const xs = Array.from(new Set(data.map((d) => d.x)));
    const ys = Array.from(new Set(data.map((d) => d.y)));
    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = height - MARGIN.top - MARGIN.bottom;
    const cellW = Math.max(1, (innerW - (xs.length - 1) * CELL_GAP) / xs.length);
    const cellH = Math.max(1, (innerH - (ys.length - 1) * CELL_GAP) / ys.length);
    const values = data.map((d) => d.value);
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;
    return { xs, ys, cellW, cellH, minV, range };
  }, [data, width, height]);

  const lookup = useMemo(() => {
    const m = new Map<string, number>();
    data.forEach((d) => m.set(`${d.x}|${d.y}`, d.value));
    return m;
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ width, height }}>
        No data
      </div>
    );
  }

  return (
    <div className="relative inline-block">
      <svg width={width} height={height} aria-label="Heatmap">
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {ys.map((y, yi) =>
            xs.map((x, xi) => {
              const v = lookup.get(`${x}|${y}`);
              if (v === undefined) return null;
              const t = (v - minV) / range;
              const fill = lerpColor(colorFrom, colorTo, t);
              const cx = xi * (cellW + CELL_GAP);
              const cy = yi * (cellH + CELL_GAP);
              return (
                <rect
                  key={`${x}-${y}`}
                  x={cx}
                  y={cy}
                  width={cellW}
                  height={cellH}
                  fill={fill}
                  rx={2}
                  ry={2}
                  onMouseEnter={(e) =>
                    setTooltip({
                      x: e.clientX,
                      y: e.clientY,
                      cell: { x, y, value: v },
                    })
                  }
                  onMouseLeave={() => setTooltip(null)}
                  style={{ cursor: "default" }}
                />
              );
            })
          )}

          {/* X-axis labels */}
          {xs.map((x, xi) => (
            <text
              key={`xl-${x}`}
              x={xi * (cellW + CELL_GAP) + cellW / 2}
              y={ys.length * (cellH + CELL_GAP) + 14}
              textAnchor="middle"
              fontSize={9}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {x}
            </text>
          ))}

          {/* Y-axis labels */}
          {ys.map((y, yi) => (
            <text
              key={`yl-${y}`}
              x={-6}
              y={yi * (cellH + CELL_GAP) + cellH / 2 + 4}
              textAnchor="end"
              fontSize={9}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {y}
            </text>
          ))}
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none rounded bg-popover border border-border shadow-lg px-2 py-1 text-xs"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          <span className="font-semibold">{tooltip.cell.x}</span>
          {" · "}
          <span>{tooltip.cell.y}</span>
          {": "}
          <span className="font-semibold">{formatValue(tooltip.cell.value)}</span>
        </div>
      )}
    </div>
  );
}
