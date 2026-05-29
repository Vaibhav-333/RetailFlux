import { useState, useRef, useCallback, cloneElement } from "react";
import { cn } from "@/lib/utils";

type TooltipSide = "top" | "bottom" | "left" | "right";

interface SmartTooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: TooltipSide;
  delay?: number;
  className?: string;
}

const POSITION: Record<TooltipSide, string> = {
  top:    "bottom-full left-1/2 -translate-x-1/2 mb-1.5",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-1.5",
  left:   "right-full top-1/2 -translate-y-1/2 mr-1.5",
  right:  "left-full top-1/2 -translate-y-1/2 ml-1.5",
};

export function SmartTooltip({
  content,
  children,
  side = "top",
  delay = 350,
  className,
}: SmartTooltipProps) {
  const [visible, setVisible] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    timer.current = setTimeout(() => setVisible(true), delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setVisible(false);
  }, []);

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {cloneElement(children)}
      {visible && (
        <span
          role="tooltip"
          className={cn(
            "absolute z-50 whitespace-nowrap rounded-md border border-border",
            "bg-popover px-2.5 py-1 text-xs text-popover-foreground shadow-md",
            "animate-scale-in pointer-events-none",
            POSITION[side],
            className
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
