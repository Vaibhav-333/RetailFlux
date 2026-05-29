/** Per-page loading skeletons — anatomy matches the real page layout. */

function KpiSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className={`grid grid-cols-2 sm:grid-cols-${Math.min(count, 4)} gap-4 animate-pulse`}>
      {[...Array(count)].map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-5 flex gap-3 items-start">
          <div className="w-9 h-9 rounded-lg bg-muted shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-16 rounded bg-muted" />
            <div className="h-6 w-24 rounded bg-muted" />
            <div className="h-2 w-12 rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ChartSkeleton({ height = 210, label = true }: { height?: number; label?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 animate-pulse">
      {label && <div className="h-4 w-36 rounded bg-muted mb-4" />}
      <div className="rounded-lg bg-muted" style={{ height }} />
    </div>
  );
}

function HeaderSkeleton() {
  return (
    <div className="flex items-center justify-between animate-pulse">
      <div className="space-y-1.5">
        <div className="h-6 w-44 rounded bg-muted" />
        <div className="h-3 w-28 rounded bg-muted" />
      </div>
      <div className="h-8 w-24 rounded-md bg-muted" />
    </div>
  );
}

// ─── Per-page skeletons ───────────────────────────────────────────────────────

export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={5} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton height={160} />
    </div>
  );
}

export function SalesSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}

export function MarketingSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2"><ChartSkeleton /></div>
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}

export function OperationsSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}

export function FinanceSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}

export function ProcurementSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}

export function ObservabilitySkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <ChartSkeleton />
      <div className="rounded-xl border border-border bg-card p-5 animate-pulse">
        <div className="h-4 w-36 rounded bg-muted mb-4" />
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-8 rounded bg-muted" style={{ width: `${70 + (i % 3) * 10}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function UploadsSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <div className="rounded-xl border-2 border-dashed border-border p-10 flex items-center justify-center animate-pulse">
        <div className="space-y-2 text-center">
          <div className="w-12 h-12 rounded-full bg-muted mx-auto" />
          <div className="h-4 w-32 rounded bg-muted mx-auto" />
        </div>
      </div>
      <div className="rounded-xl border border-border bg-card p-5 animate-pulse space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 rounded bg-muted" />
        ))}
      </div>
    </div>
  );
}

export function SettingsSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-5 animate-pulse space-y-3">
          <div className="h-4 w-28 rounded bg-muted" />
          <div className="h-10 rounded bg-muted" />
          <div className="h-10 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}

export function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full gap-4 p-1">
      <HeaderSkeleton />
      <div className="flex-1 space-y-3 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}>
            <div className="h-12 rounded-2xl bg-muted" style={{ width: `${40 + (i % 3) * 15}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ReportsSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <div className="flex gap-2 animate-pulse">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 w-24 rounded-full bg-muted" />
        ))}
      </div>
      <KpiSkeleton count={4} />
    </div>
  );
}

/** Scenarios page skeleton. */
export function ScenariosSkeleton() {
  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <div className="w-56 shrink-0 border-r border-border animate-pulse">
        <div className="h-12 border-b border-border" />
        <div className="p-2 space-y-1">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-8 rounded bg-muted" />
          ))}
        </div>
      </div>
      <div className="flex-1 p-6 space-y-5 animate-pulse">
        <div className="flex justify-between">
          <div className="space-y-2">
            <div className="h-6 w-48 rounded bg-muted" />
            <div className="h-3 w-64 rounded bg-muted" />
          </div>
          <div className="h-9 w-28 rounded bg-muted" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="rounded-lg border bg-card p-5 space-y-4">
            <div className="h-4 w-24 rounded bg-muted" />
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-1.5">
                <div className="h-3 w-32 rounded bg-muted" />
                <div className="h-1.5 w-full rounded bg-muted" />
              </div>
            ))}
          </div>
          <div className="lg:col-span-2 space-y-4">
            <div className="grid grid-cols-4 gap-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="rounded-lg border bg-card p-3 space-y-2">
                  <div className="h-3 w-16 rounded bg-muted" />
                  <div className="h-6 w-20 rounded bg-muted" />
                </div>
              ))}
            </div>
            <div className="rounded-lg border bg-card p-5">
              <div className="h-4 w-36 rounded bg-muted mb-4" />
              <div className="h-52 rounded bg-muted" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Generic fallback skeleton — mirrors the old PageSkeleton layout. */
export function GenericSkeleton() {
  return (
    <div className="space-y-6 p-1">
      <HeaderSkeleton />
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <ChartSkeleton />
    </div>
  );
}
