/**
 * realtimeBus — thin event bus for in-app realtime notifications.
 *
 * Purpose: deduplicate toasts when multiple WebSocket events fire quickly
 * for the same logical event (e.g. two alert checks running in quick
 * succession both publishing the same "anomaly_detected" payload).
 *
 * Usage:
 *   realtimeBus.emit({ type: "alert", key: "anomaly:2024-01-15", message: "..." })
 *   realtimeBus.on("alert", (evt) => toast(...))
 *   realtimeBus.off("alert", handler)
 */

export interface BusEvent {
  /** Logical event type (alert, task_update, system, ...) */
  type: string;
  /** Deduplication key — same key within dedup_ms window is dropped */
  key: string;
  /** Human-readable message to display */
  message?: string;
  /** Arbitrary payload from the server */
  payload?: unknown;
}

type Handler = (event: BusEvent) => void;

const DEDUP_WINDOW_MS = 5_000;

class RealtimeBus {
  private _handlers = new Map<string, Set<Handler>>();
  private _seen = new Map<string, number>();

  on(type: string, handler: Handler): void {
    if (!this._handlers.has(type)) this._handlers.set(type, new Set());
    this._handlers.get(type)!.add(handler);
  }

  off(type: string, handler: Handler): void {
    this._handlers.get(type)?.delete(handler);
  }

  emit(event: BusEvent): void {
    const dedupKey = `${event.type}:${event.key}`;
    const now = Date.now();
    const last = this._seen.get(dedupKey) ?? 0;

    if (now - last < DEDUP_WINDOW_MS) return; // duplicate — drop

    this._seen.set(dedupKey, now);

    // Purge old entries to prevent unbounded growth
    if (this._seen.size > 500) {
      const cutoff = now - DEDUP_WINDOW_MS * 2;
      for (const [k, t] of this._seen) {
        if (t < cutoff) this._seen.delete(k);
      }
    }

    const handlers = this._handlers.get(event.type);
    if (handlers) {
      for (const h of handlers) {
        try {
          h(event);
        } catch {
          // Individual handler errors must not break other handlers
        }
      }
    }

    // Also fire on the wildcard "*" channel
    const wildcardHandlers = this._handlers.get("*");
    if (wildcardHandlers) {
      for (const h of wildcardHandlers) {
        try {
          h(event);
        } catch {
          // noop
        }
      }
    }
  }
}

export const realtimeBus = new RealtimeBus();
