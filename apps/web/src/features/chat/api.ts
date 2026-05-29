import { api } from "@/lib/api";
import type { ChatResponse } from "@/types";

export async function sendChatMessageApi(message: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat/message", { message });
  return data;
}
