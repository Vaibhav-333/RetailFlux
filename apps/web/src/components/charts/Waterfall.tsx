/**
 * Custom SVG Waterfall chart for profit attribution (Session 35).
 *
 * Renders a waterfall/bridge chart where each bar either:
 *   - Starts from zero (type="base" or type="total")
 *   - Floats from the cumulative running total (type="delta")
 */
import { useMemo } from "react";

export interface WaterfallItem {
  label: string;
  value: number;
  type: "base" | "delta" | "total";
}

interface WaterfallProps {
  data: WaterfallItem[];
  height?: number;
  formatValue?: (v: number) => string;
}

const COLOR_BASE = "#6366f1";   // indigo — base / total bars
const COLOR_UP = "#22c55e";     // green — positive delta
const COLOR_DOWN = "#f43f5e";   // red — negative delta

function fmt(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
  return v.toFixed(0);
}

export function Waterfall({ data, height = 280, formatValue = fmt }: WaterfallProps) {
  const PADDING_LEFT = 40;
  const PADDING_RIGHT = 16;
  const PADDING_TOP = 24;
  const PADDING_BOTTOM = 48;
  const LABEL_HEIGHT = 32;

  const bars = useMemo(() => {
    let runningTotal = 0;
    return data.map((item) => {
      if (item.type === "base") {
        runningTotal = item.value;
        return { ...item, start: 0, end: item.value, runningBefore: 0 };
      }
      if (item.type === "total") {
        return { ...item, start: 0, end: item.value, runningBefore: runningTotal };
      }
      // delta
      const start = runningTotal;
      runningTotal += item.value;
      return { ...item, start, end: runningTotal, runningBefore: start };
    });
  }, [data]);

  const allValues = bars.flatMap((b) => [b.start, b.end]);
  const minVal = Math.min(0, ...allValues);
  const maxVal = Math.max(0, ...allValues);
  const range = maxVal - minVal || 1;

  const chartWidth = 600;
  const chartHeight = height - PADDING_TOP - PADDING_BOTTOM;
  const barWidth = Math.max(
    24,
    Math.floor((chartWidth - PADDING_LEFT - PADDING_RIGHT) / bars.length) - 8,
  );

  function toY(v: number): number {
    return PADDING_TOP + chartHeight - ((v - minVal) / range) * chartHeight;
  }

  const zeroY = toY(0);
  const totalWidth = chartWidth;

  return (
    <svg
      viewBox={`0 0 ${totalWidth} ${height}`}
      className="w-full overflow-visible"
      role="img"
      aria-label="Profit attribution waterfall chart"
    >
      {/* Zero baseline */}
      <line
        x1={PADDING_LEFT}
        x2={totalWidth - PADDING_RIGHT}
        y1={zeroY}
        y2={zeroY}
        stroke="currentColor"
        strokeOpacity={0.15}
        strokeWidth={1}
        strokeDasharray="4 4"
      />

      {bars.map((bar, i) => {
        const colWidth =
          (totalWidth - PADDING_LEFT - PADDING_RIGHT) / bars.length;
        const cx = PADDING_LEFT + i * colWidth + colWidth / 2;
        const bx = cx - barWidth / 2;

        const yTop = toY(Math.max(bar.start, bar.end));
        const yBot = toY(Math.min(bar.start, bar.end));
        const bh = Math.max(2, yBot - yTop);

        let fill: string;
        if (bar.type === "base" || bar.type === "total") {
          fill = COLOR_BASE;
        } else {
          fill = bar.value >= 0 ? COLOR_UP : COLOR_DOWN;
        }

        // Connector line to previous bar
        let connectorX: number | null = null;
        if (i > 0 && bar.type === "delta") {
          const prevColWidth =
            (totalWidth - PADDING_LEFT - PADDING_RIGHT) / bars.length;
          const prevCx = PADDING_LEFT + (i - 1) * prevColWidth + prevColWidth / 2;
          connectorX = prevCx + barWidth / 2;
        }

        const labelY = yTop - 6;
        const valueSign = bar.type === "delta" && bar.value > 0 ? "+" : "";
        const valueLabel = `${valueSign}${formatValue(bar.value)}`;

        return (
          <g key={bar.label}>
            {/* Floating connector */}
            {connectorX !== null && (
              <line
                x1={connectorX}
                x2={bx}
                y1={bar.value >= 0 ? yTop : yBot}
                y2={bar.value >= 0 ? yTop : yBot}
                stroke="currentColor"
                strokeOpacity={0.2}
                strokeWidth={1}
                strokeDasharray="3 3"
              />
            )}

            {/* Bar */}
            <rect
              x={bx}
              y={yTop}
              width={barWidth}
              height={bh}
              fill={fill}
              fillOpacity={bar.type === "total" ? 1 : 0.85}
              rx={3}
              ry={3}
            >
              <title>{`${bar.label}: ${valueSign}${formatValue(bar.value)}`}</title>
            </rect>

            {/* Value label */}
            <text
              x={cx}
              y={labelY}
              textAnchor="middle"
              fontSize={10}
              fill={fill}
              fontWeight={600}
              className="font-mono"
            >
              {valueLabel}
            </text>

            {/* X-axis label */}
            <text
              x={cx}
              y={height - LABEL_HEIGHT + 16}
              textAnchor="middle"
              fontSize={10}
              fill="currentColor"
              fillOpacity={0.6}
              className="select-none"
            >
              {bar.label.length > 10 ? bar.label.slice(0, 9) + "…" : bar.label}
            </text>
          </g>
        );
      })}

      {/* Y-axis ticks */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
        const v = minVal + pct * range;
        const y = toY(v);
        return (
          <g key={pct}>
            <line
              x1={PADDING_LEFT - 4}
              x2={PADDING_LEFT}
              y1={y}
              y2={y}
              stroke="currentColor"
              strokeOpacity={0.3}
            />
            <text
              x={PADDING_LEFT - 6}
              y={y + 4}
              textAnchor="end"
              fontSize={9}
              fill="currentColor"
              fillOpacity={0.5}
            >
              {formatValue(v)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
