/**
 * SankeyChart — wrapper around recharts Sankey for flow visualization.
 *
 * Typical use: supplier → warehouse stock flow, category → channel revenue.
 *
 * Usage:
 *   <SankeyChart
 *     title="Stock Flow by Warehouse"
 *     nodes={[{ name: 'Total Stock' }, { name: 'WH-East' }, ...]}
 *     links={[{ source: 0, target: 1, value: 4200 }, ...]}
 *   />
 */
import { Sankey, Tooltip, Rectangle } from "recharts";
import { cn } from "@/lib/utils";

export interface SankeyNode {
  name: string;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
}

export interface SankeyChartProps {
  title: string;
  nodes: SankeyNode[];
  links: SankeyLink[];
  height?: number;
  className?: string;
  formatValue?: (v: number) => string;
}

const NODE_COLORS = [
  "#6366f1", "#8b5cf6", "#a855f7", "#ec4899",
  "#f43f5e", "#22c55e", "#14b8a6", "#3b82f6",
  "#f97316", "#eab308",
];

function SankeyNode({
  x, y, width, height, index, payload,
}: {
  x: number; y: number; width: number; height: number;
  index: number; payload: { name: string };
}) {
  const color = NODE_COLORS[index % NODE_COLORS.length];
  return (
    <g>
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        fillOpacity={0.9}
        radius={2}
      />
      <text
        x={x + width + 6}
        y={y + height / 2}
        dy="0.35em"
        fontSize={11}
        fill="currentColor"
        className="fill-foreground"
      >
        {payload.name}
      </text>
    </g>
  );
}

function SankeyLink({
  sourceX, sourceY, sourceControlX,
  targetX, targetY, targetControlX,
  linkWidth, index,
}: {
  sourceX: number; sourceY: number; sourceControlX: number;
  targetX: number; targetY: number; targetControlX: number;
  linkWidth: number; index: number;
}) {
  const color = NODE_COLORS[index % NODE_COLORS.length];
  return (
    <path
      d={`
        M${sourceX},${sourceY}
        C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}
      `}
      stroke={color}
      strokeWidth={Math.max(1, linkWidth)}
      fill="none"
      strokeOpacity={0.4}
    />
  );
}

export function SankeyChart({
  title,
  nodes,
  links,
  height = 300,
  className,
  formatValue = (v) => v.toLocaleString(),
}: SankeyChartProps) {
  const data = { nodes, links };

  return (
    <div className={cn("rounded-lg border border-border bg-card p-5 shadow-sm", className)}>
      <h2 className="mb-4 text-base font-semibold text-foreground">{title}</h2>

      {nodes.length < 2 || links.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No flow data available.
        </p>
      ) : (
        <Sankey
          width={540}
          height={height}
          data={data}
          nodePadding={24}
          nodeWidth={12}
          margin={{ top: 8, right: 120, bottom: 8, left: 8 }}
          node={<SankeyNode x={0} y={0} width={0} height={0} index={0} payload={{ name: "" }} />}
          link={
            <SankeyLink
              sourceX={0} sourceY={0} sourceControlX={0}
              targetX={0} targetY={0} targetControlX={0}
              linkWidth={0} index={0}
            />
          }
        >
          <Tooltip
            formatter={(value: number) => [formatValue(value), "Flow"]}
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
        </Sankey>
      )}
    </div>
  );
}

/**
 * Transform a flat warehouse stock list into Sankey nodes + links
 * with a single "Total Stock" source node.
 */
export function warehouseStockToSankey(
  warehouses: { warehouse: string; stock_level: number }[]
): { nodes: SankeyNode[]; links: SankeyLink[] } {
  const nodes: SankeyNode[] = [
    { name: "Total Stock" },
    ...warehouses.map((w) => ({ name: w.warehouse })),
  ];
  const links: SankeyLink[] = warehouses.map((w, i) => ({
    source: 0,
    target: i + 1,
    value: Math.max(1, w.stock_level),
  }));
  return { nodes, links };
}
