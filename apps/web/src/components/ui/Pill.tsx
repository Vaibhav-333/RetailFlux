import { cn } from "@/lib/utils";

export type PillVariant = "default" | "ok" | "warn" | "bad" | "info" | "ai" | "muted";
type PillSize = "xs" | "sm";

interface PillProps {
  children: React.ReactNode;
  variant?: PillVariant;
  size?: PillSize;
  dot?: boolean;
  className?: string;
}

const VARIANT_CLASSES: Record<PillVariant, string> = {
  default: "bg-primary/10 text-primary border-primary/20",
  ok:      "border bg-[hsl(var(--ok)/0.1)] text-[hsl(var(--ok))] border-[hsl(var(--ok)/0.25)]",
  warn:    "border bg-[hsl(var(--warn)/0.1)] text-[hsl(var(--warn))] border-[hsl(var(--warn)/0.25)]",
  bad:     "border bg-[hsl(var(--bad)/0.1)] text-[hsl(var(--bad))] border-[hsl(var(--bad)/0.25)]",
  info:    "border bg-[hsl(var(--info)/0.1)] text-[hsl(var(--info))] border-[hsl(var(--info)/0.25)]",
  ai:      "border bg-[hsl(var(--ai)/0.1)] text-[hsl(var(--ai))] border-[hsl(var(--ai)/0.25)]",
  muted:   "bg-muted text-muted-foreground border border-border",
};

export function Pill({ children, variant = "default", size = "xs", dot, className }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium",
        size === "xs" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        VARIANT_CLASSES[variant],
        className
      )}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0 bg-current"
          aria-hidden
        />
      )}
      {children}
    </span>
  );
}
