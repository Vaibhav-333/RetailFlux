"""Task workflow state machine.

Valid statuses and allowed transitions:
  open       → in_progress, cancelled
  in_progress → blocked, in_review, done, cancelled
  blocked    → in_progress, cancelled
  in_review  → in_progress, done, cancelled
  done       → (terminal)
  cancelled  → (terminal)
"""
from __future__ import annotations

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "cancelled"},
    "in_progress": {"blocked", "in_review", "done", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "in_review": {"in_progress", "done", "cancelled"},
    "done": set(),
    "cancelled": set(),
}

TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "cancelled"})


def can_transition(from_status: str, to_status: str) -> bool:
    """Return True if transitioning from_status → to_status is allowed."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def valid_statuses() -> list[str]:
    """Return all valid task status values."""
    return list(ALLOWED_TRANSITIONS)
