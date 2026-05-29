import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CopilotAskRequest {
  message: string;
  page_context?: Record<string, string | number | boolean | null>;
}

export interface CopilotAskResponse {
  answer: string;
  tool_used: string | null;
  provider: string;
}

export interface CopilotStreamRequest {
  message: string;
  page_context?: Record<string, string | number | boolean | null>;
  conversation_id?: string | null;
}

export type SSEEventType =
  | "token"
  | "tool_used"
  | "context_sources"
  | "proposed_actions"
  | "done"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  content?: string;
  tool?: string;
  sources?: Array<{ entity_type: string; entity_id: string; content: string; distance: number }>;
  actions?: Array<{ verb: string; description: string; url_path: string }>;
  message_id?: string | null;
  provider?: string;
  message?: string;
}

export interface ExplanationResponse {
  body: string;
  resource: string;
  resource_id: string;
  cached: boolean;
  version: number;
}

export interface Conversation {
  id: string;
  title: string | null;
  summary: string | null;
  message_count: number;
  total_tokens: number;
  last_message_at: string | null;
  created_at: string | null;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_used: string | null;
  rag_sources: Array<{ entity_type: string; entity_id: string; content: string }>;
  proposed_actions: Array<{ verb: string; description: string; url_path: string }>;
  token_estimate: number;
  provider: string | null;
  created_at: string | null;
}

export interface CopilotUsage {
  tokens_used: number;
  request_count: number;
  cap: number;
  pct_used: number;
}

// ── Non-streaming ask ─────────────────────────────────────────────────────────

export async function copilotAskApi(req: CopilotAskRequest): Promise<CopilotAskResponse> {
  const { data } = await api.post<CopilotAskResponse>("/copilot/ask", req);
  return data;
}

// ── SSE streaming ─────────────────────────────────────────────────────────────

/**
 * Open a fetch-based SSE stream to /copilot/stream.
 * Calls onEvent for each parsed event; resolves when the stream ends.
 * Uses fetch (not EventSource) because the endpoint is POST with a body.
 */
export async function copilotStreamApi(
  req: CopilotStreamRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getAccessToken();
  const baseUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

  const response = await fetch(`${baseUrl}/api/v1/copilot/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(req),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Copilot stream error: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE format: "data: {...}\n\n"
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice(5).trim();
      if (jsonStr === "[DONE]") return;

      try {
        const event = JSON.parse(jsonStr) as SSEEvent;
        onEvent(event);
      } catch {
        // malformed chunk — ignore
      }
    }
  }
}

// ── Explanation ───────────────────────────────────────────────────────────────

export async function getExplanationApi(
  resource: string,
  resourceId: string,
  context?: Record<string, unknown>,
): Promise<ExplanationResponse> {
  const { data } = await api.post<ExplanationResponse>(
    `/copilot/explain/${resource}/${encodeURIComponent(resourceId)}`,
    { context: context ?? null },
  );
  return data;
}

// ── Conversations ─────────────────────────────────────────────────────────────

export async function listConversationsApi(): Promise<{ conversations: Conversation[]; total: number }> {
  const { data } = await api.get("/copilot/conversations");
  return data;
}

export async function getConversationApi(
  id: string,
): Promise<{ conversation_id: string; messages: ConversationMessage[] }> {
  const { data } = await api.get(`/copilot/conversations/${id}`);
  return data;
}

export async function deleteConversationApi(id: string): Promise<void> {
  await api.delete(`/copilot/conversations/${id}`);
}

// ── Usage ─────────────────────────────────────────────────────────────────────

export async function getCopilotUsageApi(): Promise<CopilotUsage> {
  const { data } = await api.get<CopilotUsage>("/copilot/usage");
  return data;
}
