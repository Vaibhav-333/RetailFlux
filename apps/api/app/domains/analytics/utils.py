"""Shared helpers for all analytics services — compare-period math and dim filtering."""
from datetime import date, timedelta
from typing import Optional


def compute_compare_period(
    date_from: str,
    date_to: str,
    compare_to: str,
) -> tuple[str, str] | None:
    """Return (prev_from, prev_to) ISO strings for the requested comparison window.

    compare_to values:
    - ``previous_period`` — a window of the same length immediately before date_from
    - ``previous_year``   — the same calendar window shifted back 365 days
    Returns ``None`` for unrecognised values.
    """
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    period_days = (d_to - d_from).days + 1

    if compare_to == "previous_period":
        prev_to = d_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_days - 1)
    elif compare_to == "previous_year":
        prev_from = d_from - timedelta(days=365)
        prev_to = d_to - timedelta(days=365)
    else:
        return None

    return prev_from.isoformat(), prev_to.isoformat()


def pct_delta(current: float, prev: float) -> float | None:
    """Percentage change (current - prev) / |prev| × 100, rounded to 1 dp.
    Returns ``None`` when prev == 0 (undefined growth)."""
    if prev == 0:
        return None
    return round((current - prev) / abs(prev) * 100, 1)


def parse_dims(dims: Optional[str]) -> dict:
    """Parse ``region=North,channel=online`` → ``{"region": "North", "channel": "online"}``.
    Returns an empty dict when dims is None or empty."""
    if not dims:
        return {}
    result: dict = {}
    for pair in dims.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                result[k] = v
    return result
