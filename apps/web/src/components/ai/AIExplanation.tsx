import { useState } from "react";
import { Sparkles, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { AIBadge } from "@/components/ui/AIBadge";
import { getExplanationApi } from "@/features/copilot/api";

interface AIExplanationProps {
  resource: string;
  resourceId: string;
  context?: Record<string, unknown>;
  className?: string;
}

/**
 * Inline "why?" affordance — shows a sparkle icon that expands to a 2–4 sentence
 * AI explanation for the attached metric, chart, or resource.
 */
export function AIExplanation({
  resource,
  resourceId,
  context,
  className,
}: AIExplanationProps) {
  const [open, setOpen] = useState(false);

  const { data, isFetching, isError } = useQuery({
    queryKey: ["explanation", resource, resourceId, context],
    queryFn: () => getExplanationApi(resource, resourceId, context),
    enabled: open,
    staleTime: 30 * 60 * 1000, // 30 min — explanations rarely change
    retry: 1,
  });

  return (
    <div className={cn("relative inline-block", className)}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium transition-colors",
          open
            ? "text-violet-400 bg-violet-500/10"
            : "text-muted-foreground hover:text-violet-400 hover:bg-violet-500/10",
        )}
        aria-label="Show AI explanation"
        aria-expanded={open}
      >
        <Sparkles className="w-3 h-3" aria-hidden />
        Why?
      </button>

      {open && (
        <div
          className={cn(
            "absolute z-30 left-0 mt-1 w-72 rounded-xl border border-border bg-card p-3 shadow-xl",
            "animate-in fade-in slide-in-from-top-2 duration-150",
          )}
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <AIBadge provider={data?.cached ? "cached" : "gemini"} />
            <button
              onClick={() => setOpen(false)}
              className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close explanation"
            >
              <X className="w-3 h-3" />
            </button>
          </div>

          {isFetching && (
            <div className="flex items-center gap-2 py-2">
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
              <span className="text-xs text-muted-foreground">Generating explanation…</span>
            </div>
          )}

          {isError && !isFetching && (
            <p className="text-xs text-danger">
              Unable to load explanation. Please try again.
            </p>
          )}

          {data && !isFetching && (
            <p className="text-xs text-foreground leading-relaxed">{data.body}</p>
          )}
        </div>
      )}
    </div>
  );
}
