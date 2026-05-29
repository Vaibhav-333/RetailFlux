import { api } from "@/lib/api";

export type ReportDept = "sales" | "marketing" | "operations" | "finance" | "procurement";
export type ReportFormat = "csv" | "json";

export interface DownloadReportParams {
  dept: ReportDept;
  date_from?: string;
  date_to?: string;
  fmt: ReportFormat;
}

export async function downloadReportApi(params: DownloadReportParams): Promise<void> {
  const search = new URLSearchParams({ dept: params.dept, fmt: params.fmt });
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);

  const { data, headers } = await api.get(`/reports/export?${search}`, {
    responseType: "blob",
  });

  const contentDisposition = (headers["content-disposition"] as string) ?? "";
  const match = /filename="([^"]+)"/.exec(contentDisposition);
  const filename = match?.[1] ?? `retailflux_${params.dept}.${params.fmt}`;

  const url = URL.createObjectURL(new Blob([data as BlobPart]));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
