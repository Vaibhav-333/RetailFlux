import { api } from "@/lib/api";
import type { Upload, Department } from "@/types";

export interface UploadListResponse {
  items: Upload[];
  total: number;
}

export async function uploadFileApi(file: File, dept: Department): Promise<Upload> {
  const form = new FormData();
  form.append("file", file);
  form.append("dept", dept);
  const { data } = await api.post<Upload>("/uploads", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listUploadsApi(
  dept?: Department,
  page = 1,
  size = 20,
): Promise<UploadListResponse> {
  const params: Record<string, string | number> = { page, size };
  if (dept) params.dept = dept;
  const { data } = await api.get<UploadListResponse>("/uploads", { params });
  return data;
}

export async function getUploadApi(id: string): Promise<Upload> {
  const { data } = await api.get<Upload>(`/uploads/${id}`);
  return data;
}
