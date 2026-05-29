import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listRecommendationsApi, refreshRecommendationsApi } from "@/features/tasks/api";
import type { TaskRecommendationOut } from "@/types";

const PRIORITY_BADGE: Record<string, string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-amber-100 text-amber-800",
  urgent: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-700",
};

function RecommendationCard({ rec }: { rec: TaskRecommendationOut }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm space-y-2">
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium text-sm text-foreground flex-1">{rec.title}</p>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${
            PRIORITY_BADGE[rec.priority] ?? "bg-slate-100 text-slate-600"
          }`}
        >
          {rec.priority}
        </span>
      </div>
      {rec.description && (
        <p className="text-xs text-muted-foreground leading-relaxed">{rec.description}</p>
      )}
      {rec.departments.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {rec.departments.map((d) => (
            <span
              key={d}
              className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground"
            >
              {d}
            </span>
          ))}
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Generated {new Date(rec.created_at).toLocaleDateString()}
      </p>
    </div>
  );
}

export function AIRecommendationsInbox() {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["task-recommendations", page],
    queryFn: () => listRecommendationsApi({ page, size: 10 }),
  });

  const refresh = useMutation({
    mutationFn: refreshRecommendationsApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-recommendations"] });
    },
  });

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          AI Recommendations
        </h2>
        <button
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {refresh.isPending ? (
            <span className="animate-spin h-3 w-3 rounded-full border-2 border-primary-foreground border-t-transparent" />
          ) : (
            <span>✨</span>
          )}
          {refresh.isPending ? "Generating…" : "Refresh AI"}
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin h-6 w-6 rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {data?.items.map((rec) => (
              <RecommendationCard key={rec.id} rec={rec} />
            ))}
            {data?.items.length === 0 && !refresh.isPending && (
              <div className="rounded-xl border border-dashed border-border p-8 text-center text-muted-foreground text-sm">
                <p className="mb-2">No AI recommendations yet.</p>
                <p className="text-xs">Click "Refresh AI" to generate action tasks from recent anomalies.</p>
              </div>
            )}
          </div>

          {/* Pagination */}
          {data && data.total > 10 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-muted-foreground">
                {data.total} recommendations · page {page}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded px-2 py-1 text-xs border border-border disabled:opacity-40 hover:bg-muted transition-colors"
                >
                  ← Prev
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 10 >= data.total}
                  className="rounded px-2 py-1 text-xs border border-border disabled:opacity-40 hover:bg-muted transition-colors"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
