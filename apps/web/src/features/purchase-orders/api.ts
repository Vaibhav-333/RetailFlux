import { api } from "@/lib/api";

export interface PoLine {
  id: string;
  sku: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
  notes?: string;
}

export interface PurchaseOrder {
  id: string;
  company_id: string;
  status: "draft" | "pending_approval" | "approved" | "rejected" | "cancelled" | "sent";
  supplier_name: string | null;
  total_cost: number;
  notes: string | null;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  lines: PoLine[];
}

export interface PurchaseOrderListOut {
  items: PurchaseOrder[];
  total: number;
  page: number;
  page_size: number;
}

export async function listPurchaseOrdersApi(
  status?: string,
  page = 1,
  pageSize = 20,
): Promise<PurchaseOrderListOut> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  const { data } = await api.get<PurchaseOrderListOut>("/purchase-orders", { params });
  return data;
}

export async function getPurchaseOrderApi(id: string): Promise<PurchaseOrder> {
  const { data } = await api.get<PurchaseOrder>(`/purchase-orders/${id}`);
  return data;
}

export async function approvePurchaseOrderApi(id: string): Promise<PurchaseOrder> {
  const { data } = await api.post<PurchaseOrder>(`/purchase-orders/${id}/approve`);
  return data;
}

export async function rejectPurchaseOrderApi(id: string, reason?: string): Promise<PurchaseOrder> {
  const { data } = await api.post<PurchaseOrder>(`/purchase-orders/${id}/reject`, { reason });
  return data;
}

export async function submitPurchaseOrderApi(id: string): Promise<PurchaseOrder> {
  const { data } = await api.post<PurchaseOrder>(`/purchase-orders/${id}/submit`);
  return data;
}

export async function cancelPurchaseOrderApi(id: string): Promise<PurchaseOrder> {
  const { data } = await api.post<PurchaseOrder>(`/purchase-orders/${id}/cancel`);
  return data;
}

export async function bulkApprovePurchaseOrdersApi(
  poIds: string[],
): Promise<{ approved: string[]; failed: { id: string; reason: string }[]; total_approved: number }> {
  const { data } = await api.post("/purchase-orders/bulk-approve", { po_ids: poIds });
  return data;
}

export function exportPurchaseOrderUrl(id: string, format: "json" | "csv" | "email"): string {
  return `/api/v1/purchase-orders/${id}/export?format=${format}`;
}
