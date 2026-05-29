import { useEffect, useRef, useState } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Hotspot {
  selector: string;
  title: string;
  body: string;
  position?: "top" | "bottom" | "left" | "right";
}

interface TourHotspotsProps {
  hotspots: Hotspot[];
  active: boolean;
  onComplete: () => void;
}

interface TooltipPos {
  top: number;
  left: number;
}

function getTooltipPos(el: Element, position: Hotspot["position"]): TooltipPos {
  const rect = el.getBoundingClientRect();
  const GAP = 12;
  switch (position) {
    case "top":
      return { top: rect.top - GAP, left: rect.left + rect.width / 2 };
    case "left":
      return { top: rect.top + rect.height / 2, left: rect.left - GAP };
    case "right":
      return { top: rect.top + rect.height / 2, left: rect.right + GAP };
    case "bottom":
    default:
      return { top: rect.bottom + GAP, left: rect.left + rect.width / 2 };
  }
}

export function TourHotspots({ hotspots, active, onComplete }: TourHotspotsProps) {
  const [index, setIndex] = useState(0);
  const [pos, setPos] = useState<TooltipPos | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) return;
    setIndex(0);
  }, [active]);

  useEffect(() => {
    if (!active || hotspots.length === 0) return;
    const hotspot = hotspots[index];
    const el = document.querySelector(hotspot.selector);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    setPos(getTooltipPos(el, hotspot.position ?? "bottom"));
    el.classList.add("ring-2", "ring-brand-500", "ring-offset-2", "rounded-lg", "z-[45]", "relative");
    return () => {
      el.classList.remove("ring-2", "ring-brand-500", "ring-offset-2", "rounded-lg", "z-[45]", "relative");
    };
  }, [active, index, hotspots]);

  if (!active || hotspots.length === 0 || !pos) return null;

  const hotspot = hotspots[index];

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" aria-hidden="true" />
      <div
        ref={tooltipRef}
        role="tooltip"
        style={{ position: "fixed", top: pos.top, left: pos.left, transform: "translateX(-50%)" }}
        className={cn(
          "z-50 w-72 bg-card border border-border rounded-xl shadow-xl p-4",
          "animate-in fade-in-0 slide-in-from-bottom-2",
        )}
      >
        <div className="flex items-start justify-between mb-2">
          <p className="text-sm font-semibold text-foreground">{hotspot.title}</p>
          <button
            onClick={onComplete}
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close tour"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">{hotspot.body}</p>
        <div className="flex items-center justify-between mt-4">
          <span className="text-[10px] text-muted-foreground">
            {index + 1} / {hotspots.length}
          </span>
          <div className="flex items-center gap-2">
            {index > 0 && (
              <button
                onClick={() => setIndex((i) => i - 1)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs border border-border rounded-md hover:bg-accent transition-colors"
              >
                <ChevronLeft className="w-3 h-3" /> Back
              </button>
            )}
            <button
              onClick={() => {
                if (index < hotspots.length - 1) setIndex((i) => i + 1);
                else onComplete();
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-brand-600 text-white rounded-md hover:bg-brand-700 transition-colors"
            >
              {index < hotspots.length - 1 ? "Next" : "Done"}
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
