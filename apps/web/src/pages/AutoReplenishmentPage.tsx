import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, Download, Loader2, RefreshCw, XCircle } from "lucide-react";
import { toast } from "sonner";
import {
  listPurchaseOrdersApi,
  approvePurchaseOrderApi,
  rejectPurchaseOrderApi,
  bulkApprovePurchaseOrdersApi,
  type PurchaseOrder,
} from "@/features/purchase-orders/api";
import { KpiCard } from "@/components/ui/KpiCard";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-slate-500/20 text-slate-300",
  pending_approval: "bg-amber-500/20 text-amber-300",
  approved: "bg-green-500/20 text-green-400",
  rejected: "bg-red-500/20 text-red-400",
  cancelled: "bg-slate-500/20 text-slate-400 line-through",
  sent: "bg-blue-500/20 text-blue-400",
};

type StatusFilter = "all" | "pending_approval" | "approved" | "draft";

export function AutoReplenishmentPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending_approval");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const qc = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["purchase-orders", statusFilter],
    queryFn: () =>
      listPurchaseOrdersApi(statusFilter === "all" ? undefined : statusFilter),
  });

  const approveMut = useMutation({
    mutationFn: approvePurchaseOrderApi,
    onSuccess: () => {
      toast.success("PO approved");
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectPurchaseOrderApi(id),
    onSuccess: () => {
      toast.success("PO rejected");
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const bulkApproveMut = useMutation({
    mutationFn: () => bulkApprovePurchaseOrdersApi(Array.from(selectedIds)),
    onSuccess: (result) => {
      toast.success(`${result.total_approved} POs approved`);
      if (result.failed.length > 0) toast.warning(`${result.failed.length} failed`);
      setSelectedIds(new Set());
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const orders = data?.items ?? [];
  const pendingCount = orders.filter((o) => o.status === "pending_approval").length;
  const approvedCount = orders.filter((o) => o.status === "approved").length;
  const totalValue = orders.reduce((s, o) => s + o.total_cost, 0);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    const pendingIds = orders
      .filter((o) => o.status === "pending_approval")
      .map((o) => o.id);
    if (selectedIds.size === pendingIds.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingIds));
    }
  }

  const pendingOrders = orders.filter((o) => o.status === "pending_approval");

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Auto-Replenishment</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Review and approve AI-generated purchase orders
          </p>
        </div>
        <button
          onClick={() => void refetch()}
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-medium hover:bg-accent transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Pending Approval" value={String(pendingCount)} valueVariant={pendingCount > 0 ? "warn" : "default"} />
        <KpiCard label="Approved" value={String(approvedCount)} valueVariant="ok" />
        <KpiCard label="Total Value" value={fmt(totalValue)} subline="all shown POs" />
        <KpiCard label="Total POs" value={String(data?.total ?? 0)} />
      </div>

      {/* Filters + bulk actions */}
      <div className="flex flex-wrap items-center gap-2">
        {(["pending_approval", "approved", "draft", "all"] as StatusFilter[]).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded px-3 py-1 text-sm font-medium transition-colors capitalize ${
              statusFilter === s
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            {s === "pending_approval" ? "Pending" : s}
          </button>
        ))}

        {selectedIds.size > 0 && (
          <button
            onClick={() => bulkApproveMut.mutate()}
            disabled={bulkApproveMut.isPending}
            className="ml-auto inline-flex items-center gap-1.5 rounded bg-green-600 hover:bg-green-700 text-white px-3 py-1 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {bulkApproveMut.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CheckCheck className="w-3.5 h-3.5" />
            )}
            Bulk Approve ({selectedIds.size})
          </button>
        )}
      </div>

      {/* PO table */}
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading purchase orders…
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2 text-muted-foreground">
            <CheckCheck className="w-8 h-8 text-green-400" />
            <p className="text-sm">No purchase orders in this status.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30">
                  {statusFilter === "pending_approval" && (
                    <th className="w-8 px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === pendingOrders.length && pendingOrders.length > 0}
                        onChange={toggleSelectAll}
                        className="rounded"
                      />
                    </th>
                  )}
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">PO ID</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Supplier</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Lines</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Total</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Created</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((po) => (
                  <PoRow
                    key={po.id}
                    po={po}
                    selected={selectedIds.has(po.id)}
                    onToggle={() => toggleSelect(po.id)}
                    showCheckbox={statusFilter === "pending_approval"}
                    onApprove={() => approveMut.mutate(po.id)}
                    onReject={() => rejectMut.mutate(po.id)}
                    approving={approveMut.isPending && approveMut.variables === po.id}
                    rejecting={rejectMut.isPending && rejectMut.variables === po.id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

interface PoRowProps {
  po: PurchaseOrder;
  selected: boolean;
  onToggle: () => void;
  showCheckbox: boolean;
  onApprove: () => void;
  onReject: () => void;
  approving: boolean;
  rejecting: boolean;
}

function PoRow({ po, selected, onToggle, showCheckbox, onApprove, onReject, approving, rejecting }: PoRowProps) {
  const [expanded, setExpanded] = useState(false);
  const canApprove = po.status === "pending_approval" || po.status === "draft";

  return (
    <>
      <tr
        className={`border-b transition-colors cursor-pointer hover:bg-accent/30 ${selected ? "bg-primary/5" : ""}`}
        onClick={() => setExpanded((v) => !v)}
      >
        {showCheckbox && (
          <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
            {canApprove && (
              <input
                type="checkbox"
                checked={selected}
                onChange={onToggle}
                className="rounded"
              />
            )}
          </td>
        )}
        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
          PO-{po.id.slice(0, 8).toUpperCase()}
        </td>
        <td className="px-4 py-3 font-medium">{po.supplier_name ?? "—"}</td>
        <td className="px-4 py-3 text-muted-foreground">{po.lines.length} SKUs</td>
        <td className="px-4 py-3 text-right font-semibold">{fmt(po.total_cost)}</td>
        <td className="px-4 py-3">
          <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_BADGE[po.status] ?? ""}`}>
            {po.status.replace("_", " ")}
          </span>
        </td>
        <td className="px-4 py-3 text-muted-foreground text-xs">
          {po.created_at ? new Date(po.created_at).toLocaleDateString() : "—"}
        </td>
        <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-end gap-1">
            {canApprove && (
              <button
                onClick={onApprove}
                disabled={approving}
                className="inline-flex items-center gap-1 rounded bg-green-600/80 hover:bg-green-600 text-white px-2 py-0.5 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {approving ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCheck className="w-3 h-3" />}
                Approve
              </button>
            )}
            {canApprove && (
              <button
                onClick={onReject}
                disabled={rejecting}
                className="inline-flex items-center gap-1 rounded border border-destructive/50 text-destructive hover:bg-destructive/10 px-2 py-0.5 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {rejecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                Reject
              </button>
            )}
            <a
              href={`/api/v1/purchase-orders/${po.id}/export?format=csv`}
              download
              className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-medium hover:bg-accent transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <Download className="w-3 h-3" />
              CSV
            </a>
          </div>
        </td>
      </tr>
      {expanded && po.lines.length > 0 && (
        <tr className="bg-muted/20">
          <td colSpan={showCheckbox ? 8 : 7} className="px-8 py-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left pb-1">SKU</th>
                  <th className="text-right pb-1">Quantity</th>
                  <th className="text-right pb-1">Unit Cost</th>
                  <th className="text-right pb-1">Line Total</th>
                </tr>
              </thead>
              <tbody>
                {po.lines.map((ln) => (
                  <tr key={ln.id} className="border-t border-border/30">
                    <td className="py-1 font-mono">{ln.sku}</td>
                    <td className="py-1 text-right">{ln.quantity.toLocaleString()}</td>
                    <td className="py-1 text-right">${ln.unit_cost.toFixed(2)}</td>
                    <td className="py-1 text-right font-semibold">{fmt(ln.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  );
}
