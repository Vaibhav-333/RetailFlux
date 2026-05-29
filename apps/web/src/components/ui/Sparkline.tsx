import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface SparklineProps {
  data: number[];
  height?: number;
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  className?: string;
}

export function Sparkline({
  data,
  height = 32,
  color = "hsl(var(--primary))",
  fillColor,
  strokeWidth = 1.5,
  className,
}: SparklineProps) {
  const { linePath, fillPath } = useMemo(() => {
    if (data.length < 2) return { linePath: "", fillPath: "" };

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const W = 100 - pad * 2;
    const H = height - pad * 2;

    const pts = data.map((v, i) => {
      const x = pad + (i / (data.length - 1)) * W;
      const y = pad + H - ((v - min) / range) * H;
      return { x, y };
    });

    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
    const fill = fillColor
      ? `${line} L ${(pad + W).toFixed(2)},${(pad + H).toFixed(2)} L ${pad.toFixed(2)},${(pad + H).toFixed(2)} Z`
      : "";

    return { linePath: line, fillPath: fill };
  }, [data, height, fillColor]);

  if (data.length < 2) return null;

  return (
    <svg
      viewBox={`0 0 100 ${height}`}
      height={height}
      preserveAspectRatio="none"
      className={cn("w-full", className)}
      aria-hidden="true"
    >
      {fillColor && fillPath && (
        <path d={fillPath} fill={fillColor} opacity={0.12} />
      )}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
