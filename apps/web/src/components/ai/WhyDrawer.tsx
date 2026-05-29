import { X, Sparkles, ExternalLink } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AIBadge } from "@/components/ui/AIBadge";
import { getExplanationApi } from "@/features/copilot/api";

export interface WhyDrawerProps {
  open: boolean;
  onClose: () => void;
  resource: string;
  resourceId: string;
  title: string;
  context?: Record<string, unknown>;
}

/**
 * Full-panel "Why?" drawer that shows a detailed AI explanation for
 * a metric or resource. Slides in from the right side of the ContextRail.
 */
export function WhyDrawer({
  open,
  onClose,
  resource,
  resourceId,
  title,
  context,
}: WhyDrawerProps) {
  const { data, isFetching, isError } = useQuery({
    queryKey: ["explanation-drawer", resource, resourceId, context],
    queryFn: () => getExplanationApi(resource, resourceId, context),
    enabled: open,
    staleTime: 30 * 60 * 1000,
    retry: 1,
  });

  if (!open) return null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-4 border-b border-border shrink-0">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-4 h-4 text-violet-400 shrink-0" aria-hidden />
            <p className="text-sm font-semibold text-foreground truncate">AI Explanation</p>
          </div>
          <p className="text-xs text-muted-foreground truncate">{title}</p>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Close explanation panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isFetching && (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="w-6 h-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
            <p className="text-xs text-muted-foreground">Generating explanation…</p>
          </div>
        )}

        {isError && !isFetching && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 p-3">
            <p className="text-xs text-danger">Failed to load explanation. Try again later.</p>
          </div>
        )}

        {data && !isFetching && (
          <>
            <div className="flex items-center gap-2">
              <AIBadge provider={data.cached ? "cached" : "gemini"} />
              {data.cached && (
                <span className="text-[10px] text-muted-foreground">Cached result</span>
              )}
            </div>

            <div className="rounded-xl border border-border bg-muted/30 p-4">
              <p className="text-sm text-foreground leading-relaxed">{data.body}</p>
            </div>

            <div className="text-[10px] text-muted-foreground pt-1">
              Resource: {data.resource} / {data.resource_id} · Schema v{data.version}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="shrink-0 p-3 border-t border-border">
        <button
          onClick={onClose}
          className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-border py-2 text-xs text-muted-foreground hover:bg-accent transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Open full AI Chat
        </button>
      </div>
    </div>
  );
}
