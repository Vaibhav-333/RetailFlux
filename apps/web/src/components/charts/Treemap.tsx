/**
 * TreemapChart — wrapper around recharts Treemap for proportional breakdown.
 *
 * Typical use: revenue by SKU, spend by category, inventory by warehouse.
 *
 * Usage:
 *   <TreemapChart
 *     title="Revenue by SKU"
 *     data={top_skus.map(s => ({ name: s.sku, value: s.revenue }))}
 *     formatValue={v => `$${(v/1000).toFixed(0)}k`}
 *   />
 */
import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import { cn } from "@/lib/utils";

export interface TreemapItem {
  name: string;
  value: number;
  /** Optional children for nested treemaps */
  children?: TreemapItem[];
}

export interface TreemapChartProps {
  title: string;
  data: TreemapItem[];
  height?: number;
  className?: string;
  formatValue?: (v: number) => string;
}

const COLORS = [
  "#6366f1", "#8b5cf6", "#a855f7", "#ec4899",
  "#f43f5e", "#22c55e", "#14b8a6", "#3b82f6",
  "#f97316", "#eab308", "#06b6d4", "#84cc16",
];

interface CustomContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  value?: number;
  depth?: number;
  index?: number;
  formatValue?: (v: number) => string;
}

function CustomContent({
  x = 0, y = 0, width = 0, height = 0,
  name = "", value = 0, depth = 0, index = 0,
  formatValue,
}: CustomContentProps) {
  const color = COLORS[index % COLORS.length];
  const isSmall = width < 60 || height < 36;
  const fmt = formatValue ?? ((v: number) => v.toLocaleString());

  if (depth === 0) return null;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={Math.max(0, width - 2)}
        height={Math.max(0, height - 2)}
        fill={color}
        fillOpacity={0.85}
        rx={3}
      />
      {!isSmall && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            fontSize={Math.min(12, width / 6)}
            fill="#fff"
            fontWeight={600}
          >
            {name.length > 12 ? `${name.slice(0, 11)}…` : name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fontSize={Math.min(11, width / 7)}
            fill="rgba(255,255,255,0.8)"
          >
            {fmt(value)}
          </text>
        </>
      )}
    </g>
  );
}

export function TreemapChart({
  title,
  data,
  height = 300,
  className,
  formatValue = (v) => v.toLocaleString(),
}: TreemapChartProps) {
  // recharts Treemap needs a "size" dataKey; map value → size
  const rechartData = data.map((d) => ({ ...d, size: d.value }));

  return (
    <div className={cn("rounded-lg border border-border bg-card p-5 shadow-sm", className)}>
      <h2 className="mb-4 text-base font-semibold text-foreground">{title}</h2>

      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No data available.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <Treemap
            data={rechartData}
            dataKey="size"
            aspectRatio={4 / 3}
            stroke="transparent"
            content={
              <CustomContent formatValue={formatValue} />
            }
          >
            <Tooltip
              formatter={(v: number) => [formatValue(v), "Value"]}
              contentStyle={{
                background: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
          </Treemap>
        </ResponsiveContainer>
      )}
    </div>
  );
}
