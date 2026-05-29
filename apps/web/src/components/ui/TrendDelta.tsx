import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

type DeltaSize = "xs" | "sm" | "md";

interface TrendDeltaProps {
  delta: number;
  label?: string;
  size?: DeltaSize;
  className?: string;
}

const SIZE_TEXT: Record<DeltaSize, string> = {
  xs: "text-[10px] gap-0.5",
  sm: "text-xs gap-1",
  md: "text-sm gap-1",
};

const SIZE_ICON: Record<DeltaSize, string> = {
  xs: "w-2.5 h-2.5",
  sm: "w-3 h-3",
  md: "w-3.5 h-3.5",
};

export function TrendDelta({ delta, label, size = "sm", className }: TrendDeltaProps) {
  const isNeutral = delta === 0;
  const isPositive = delta > 0;
  const Icon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span
      className={cn(
        "inline-flex items-center font-medium tabular-nums shrink-0",
        SIZE_TEXT[size],
        isNeutral
          ? "text-muted-foreground"
          : isPositive
          ? "text-[hsl(var(--ok))]"
          : "text-[hsl(var(--bad))]",
        className
      )}
    >
      <Icon className={SIZE_ICON[size]} aria-hidden />
      {isNeutral ? "0%" : `${isPositive ? "+" : ""}${delta.toFixed(1)}%`}
      {label && (
        <span className="ml-1 font-normal text-muted-foreground">{label}</span>
      )}
    </span>
  );
}
