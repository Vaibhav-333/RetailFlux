"""Per-SKU price elasticity estimation via log-log OLS regression.

Model: ln(units) = a + b × ln(price) + season_coeff × sin(2π day/7)
         where b = elasticity (typically negative, e.g. -1.2 means 1% price ↑ → 1.2% qty ↓)

Uses only numpy / statsmodels — no scipy required here.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np


def estimate_elasticity(
    prices: list[float],
    quantities: list[float],
    min_observations: int = 14,
) -> dict:
    """Estimate price elasticity from (price, qty) pairs.

    Returns:
        {elasticity, r_squared, intercept, observations, reliable}
    """
    n = len(prices)
    if n < min_observations:
        return {
            "elasticity": -1.0,  # Default unit elasticity
            "r_squared": 0.0,
            "intercept": 0.0,
            "observations": n,
            "reliable": False,
        }

    # Filter out zeros
    pairs = [(p, q) for p, q in zip(prices, quantities) if p > 0 and q > 0]
    if len(pairs) < min_observations:
        return {
            "elasticity": -1.0,
            "r_squared": 0.0,
            "intercept": 0.0,
            "observations": len(pairs),
            "reliable": False,
        }

    log_prices = np.array([math.log(p) for p, _ in pairs])
    log_qtys = np.array([math.log(q) for _, q in pairs])

    # OLS: add intercept column
    X = np.column_stack([np.ones(len(log_prices)), log_prices])
    try:
        coeffs, residuals, rank, _ = np.linalg.lstsq(X, log_qtys, rcond=None)
    except np.linalg.LinAlgError:
        return {
            "elasticity": -1.0,
            "r_squared": 0.0,
            "intercept": 0.0,
            "observations": len(pairs),
            "reliable": False,
        }

    intercept = float(coeffs[0])
    elasticity = float(coeffs[1])

    # R²
    y_pred = X @ coeffs
    ss_res = float(np.sum((log_qtys - y_pred) ** 2))
    ss_tot = float(np.sum((log_qtys - np.mean(log_qtys)) ** 2))
    r_squared = max(0.0, 1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Reliability: need reasonable R² and elasticity in plausible range
    reliable = r_squared > 0.05 and -5.0 < elasticity < 0.0

    return {
        "elasticity": round(elasticity, 4),
        "r_squared": round(r_squared, 4),
        "intercept": round(intercept, 4),
        "observations": len(pairs),
        "reliable": reliable,
    }


def predict_demand(
    elasticity: float,
    intercept: float,
    current_price: float,
    new_price: float,
    current_demand: float,
) -> float:
    """Predict new demand given a price change using the log-log model."""
    if current_price <= 0 or new_price <= 0 or current_demand <= 0:
        return current_demand
    price_ratio = new_price / current_price
    demand_multiplier = price_ratio ** elasticity
    return max(0.0, current_demand * demand_multiplier)


def optimal_price_range(
    current_price: float,
    unit_cost: float,
    elasticity: float,
    min_margin_pct: float = 0.15,
    search_pct_range: float = 0.30,
    steps: int = 61,
) -> dict:
    """Scan ±30% price range, return price maximizing expected GP per unit.

    GP per unit = (price - cost) × expected_relative_demand
    """
    if current_price <= 0 or unit_cost <= 0:
        return {"optimal_price": current_price, "expected_lift_pct": 0.0}

    min_price = max(unit_cost * (1 + min_margin_pct), current_price * (1 - search_pct_range))
    max_price = current_price * (1 + search_pct_range)

    best_price = current_price
    best_gp = (current_price - unit_cost)  # baseline at demand index 1.0

    for i in range(steps):
        p = min_price + (max_price - min_price) * i / (steps - 1)
        relative_demand = (p / current_price) ** elasticity
        gp = (p - unit_cost) * relative_demand
        if gp > best_gp:
            best_gp = gp
            best_price = p

    baseline_gp = current_price - unit_cost
    lift_pct = (best_gp - baseline_gp) / max(1.0, abs(baseline_gp)) * 100 if baseline_gp > 0 else 0.0

    return {
        "optimal_price": round(best_price, 2),
        "expected_lift_pct": round(lift_pct, 2),
        "expected_gp_per_unit": round(best_gp, 4),
    }
