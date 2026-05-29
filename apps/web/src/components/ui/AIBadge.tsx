import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIBadgeProps {
  provider?: string;
  size?: "xs" | "sm";
  className?: string;
}

export function AIBadge({ provider, size = "xs", className }: AIBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        size === "xs" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        className
      )}
      style={{
        background: "linear-gradient(135deg, hsl(var(--ai-from)/0.15), hsl(var(--ai-to)/0.12))",
        color: "hsl(var(--ai-from))",
        borderColor: "hsl(var(--ai-from)/0.3)",
      }}
    >
      <Sparkles
        className={size === "xs" ? "w-2.5 h-2.5" : "w-3 h-3"}
        aria-hidden
      />
      {provider ? `AI · ${provider}` : "AI"}
    </span>
  );
}
