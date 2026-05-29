import { api } from "@/lib/api";
import type { Notification } from "@/types";

export interface NotificationListResponse {
  items: Notification[];
  unread_count: number;
}

export async function listNotificationsApi(): Promise<NotificationListResponse> {
  const { data } = await api.get<NotificationListResponse>("/notifications");
  return data;
}

export async function markNotificationReadApi(id: string): Promise<void> {
  await api.patch(`/notifications/${id}/read`);
}

export async function markAllNotificationsReadApi(): Promise<void> {
  await api.post("/notifications/read-all");
}
