import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/api";

const BASE_WS_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /^http/,
  "ws"
);
const MAX_RECONNECT_DELAY_MS = 30_000;

export function useRealtimeAlerts() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(1_000);
  const unmounted = useRef(false);

  useEffect(() => {
    unmounted.current = false;

    function connect() {
      const token = getAccessToken();
      if (!token) return;

      const ws = new WebSocket(`${BASE_WS_URL}/api/v1/ws?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectDelay.current = 1_000; // reset backoff on success
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data as string) as { type: string };
          if (msg.type === "alert") {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
            queryClient.invalidateQueries({ queryKey: ["dashboard"] });
          }
          // "ping" — no action, just a keep-alive
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (unmounted.current) return;
        if (event.code === 4001) return; // Auth failure — don't retry
        const delay = reconnectDelay.current;
        reconnectDelay.current = Math.min(delay * 2, MAX_RECONNECT_DELAY_MS);
        setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      unmounted.current = true;
      wsRef.current?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
