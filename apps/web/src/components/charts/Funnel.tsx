/**
 * Funnel — simple trapezoidal SVG funnel chart
 *
 * Usage:
 *   <Funnel
 *     stages={[
 *       { label: "Impressions", value: 10000 },
 *       { label: "Clicks",      value: 1200 },
 *       { label: "Add to Cart", value: 320 },
 *       { label: "Purchase",    value: 80 },
 *     ]}
 *     width={400}
 *     height={300}
 *   />
 */
import { useState } from "react";

export interface FunnelStage {
  label: string;
  value: number;
  color?: string;
}

interface FunnelProps {
  stages: FunnelStage[];
  width?: number;
  height?: number;
  colors?: string[];
  formatValue?: (v: number) => string;
}

const DEFAULT_COLORS = [
  "#6366f1",
  "#8b5cf6",
  "#a855f7",
  "#c084fc",
  "#e879f9",
];

export function Funnel({
  stages,
  width = 380,
  height = 280,
  colors = DEFAULT_COLORS,
  formatValue = (v) => v.toLocaleString(),
}: FunnelProps) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (stages.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-muted-foreground"
        style={{ width, height }}
      >
        No data
      </div>
    );
  }

  const maxValue = stages[0].value || 1;
  const stageHeight = (height - 20) / stages.length;
  // Widths as fraction of chart width (min 20% for visual clarity)
  const maxW = width * 0.9;
  const minW = width * 0.2;

  return (
    <svg width={width} height={height} aria-label="Funnel chart">
      {stages.map((stage, i) => {
        const topW = i === 0
          ? maxW
          : Math.max(minW, maxW * (stages[i - 1].value / maxValue) * 0.95);
        const botW = Math.max(minW, maxW * (stage.value / maxValue) * 0.95);
        const topY = i * stageHeight + 4;
        const botY = topY + stageHeight - 2;
        const topLeft = (width - topW) / 2;
        const botLeft = (width - botW) / 2;

        const points = [
          `${topLeft},${topY}`,
          `${topLeft + topW},${topY}`,
          `${botLeft + botW},${botY}`,
          `${botLeft},${botY}`,
        ].join(" ");

        const color = stage.color ?? colors[i % colors.length];
        const convRate =
          i > 0 && stages[i - 1].value > 0
            ? ((stage.value / stages[i - 1].value) * 100).toFixed(1)
            : null;

        return (
          <g
            key={i}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            <polygon
              points={points}
              fill={color}
              opacity={hovered === i ? 1 : 0.82}
              style={{ transition: "opacity 0.15s" }}
            />

            {/* Stage label */}
            <text
              x={width / 2}
              y={topY + stageHeight / 2 - 4}
              textAnchor="middle"
              fontSize={11}
              fontWeight="600"
              fill="white"
              style={{ pointerEvents: "none" }}
            >
              {stage.label}
            </text>

            {/* Value */}
            <text
              x={width / 2}
              y={topY + stageHeight / 2 + 10}
              textAnchor="middle"
              fontSize={10}
              fill="white"
              opacity={0.9}
              style={{ pointerEvents: "none" }}
            >
              {formatValue(stage.value)}
              {convRate !== null && ` (${convRate}%)`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
