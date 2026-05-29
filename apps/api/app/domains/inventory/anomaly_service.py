"""Inventory anomaly detection using IsolationForest (PyOD / sklearn)."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

import numpy as np

from app.core.cache import ANALYTICS_TTL, get_json, inventory_key, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import AnomalyOut, InventoryAnomalyItem


# ── Pure anomaly functions (testable without DB) ──────────────────────────────


def detect_anomalies_iforest(
    features: np.ndarray,
    sku_ids: list[str],
    contamination: float = 0.05,
) -> list[int]:
    """Run IsolationForest on feature matrix, return indices of anomalies.

    features: shape (n_skus, n_features) — each row is one SKU's stats.
    Returns list of row indices predicted as anomalous (-1 label).
    """
    n = len(sku_ids)
    if n < 10:
        return []

    try:
        from pyod.models.iforest import IForest  # noqa: PLC0415

        clf = IForest(contamination=contamination, random_state=42, n_estimators=100)
        clf.fit(features)
        labels = clf.labels_  # 0=normal, 1=outlier
        return [i for i, lbl in enumerate(labels) if lbl == 1]
    except Exception:
        pass

    # Fallback: sklearn IsolationForest
    try:
        from sklearn.ensemble import IsolationForest  # noqa: PLC0415

        clf_sk = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        preds = clf_sk.fit_predict(features)  # 1=normal, -1=outlier
        return [i for i, p in enumerate(preds) if p == -1]
    except Exception:
        pass

    # Final fallback: z-score on first feature column
    col = features[:, 0]
    mean, std = float(np.mean(col)), float(np.std(col))
    if std == 0:
        return []
    z_scores = np.abs((col - mean) / std)
    return [i for i, z in enumerate(z_scores) if z > 2.5]


def classify_anomaly_severity(z_score: float) -> str:
    """Classify anomaly severity from standardized score."""
    if z_score > 3.0:
        return "high"
    elif z_score > 2.0:
        return "medium"
    return "low"


# ── Async service ─────────────────────────────────────────────────────────────


async def get_inventory_anomalies(company_id: str) -> AnomalyOut:
    """Detect anomalous demand/stock patterns using IsolationForest."""
    cache_key = inventory_key("anomalies", company_id)
    hit = await get_json(cache_key)
    if hit:
        return AnomalyOut(**hit)

    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_ops = db["staging_operations"]

    date_90d = (date.today() - timedelta(days=90)).isoformat()
    date_28d = (date.today() - timedelta(days=28)).isoformat()
    date_7d = (date.today() - timedelta(days=7)).isoformat()

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return AnomalyOut(anomalies=[], total=0)

    latest_date = latest_docs[0]["max_date"]

    # Parallel: demand stats across windows + stock
    demand_90, demand_28, demand_7, stock_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_90d}}},
            {"$group": {
                "_id": "$sku",
                "total_qty": {"$sum": "$quantity"},
                "days_count": {"$addToSet": "$date"},
            }},
        ]).to_list(length=5000),
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_28d}}},
            {"$group": {"_id": "$sku", "total_qty": {"$sum": "$quantity"}}},
        ]).to_list(length=5000),
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_7d}}},
            {"$group": {"_id": "$sku", "total_qty": {"$sum": "$quantity"}}},
        ]).to_list(length=5000),
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {"_id": "$sku", "total_stock": {"$sum": "$stock_level"}}},
        ]).to_list(length=5000),
    )

    # Build per-SKU feature matrix
    d90_map = {d["_id"]: (float(d.get("total_qty", 0)), len(d.get("days_count", []))) for d in demand_90 if d.get("_id")}
    d28_map = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_28 if d.get("_id")}
    d7_map = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_7 if d.get("_id")}
    stock_map = {d["_id"]: float(d.get("total_stock", 0)) for d in stock_docs if d.get("_id")}

    all_skus = list(d90_map.keys())
    if len(all_skus) < 5:
        return AnomalyOut(anomalies=[], total=0)

    feature_rows = []
    for sku in all_skus:
        qty_90, n_days = d90_map[sku]
        qty_28 = d28_map.get(sku, 0.0)
        qty_7 = d7_map.get(sku, 0.0)
        stock = stock_map.get(sku, 0.0)
        n_days = max(n_days, 1)

        avg_daily_90 = qty_90 / 90
        avg_daily_28 = qty_28 / 28
        avg_daily_7 = qty_7 / 7

        # Compute acceleration: how much is recent demand different from baseline?
        accel_28 = (avg_daily_28 - avg_daily_90) / (avg_daily_90 + 1e-9)
        accel_7 = (avg_daily_7 - avg_daily_90) / (avg_daily_90 + 1e-9)

        feature_rows.append([
            avg_daily_90,
            accel_28,
            accel_7,
            stock / (avg_daily_90 * 30 + 1),  # Stock cover ratio
        ])

    features = np.array(feature_rows, dtype=float)
    anomaly_indices = detect_anomalies_iforest(features, all_skus)

    anomalies: list[InventoryAnomalyItem] = []
    for idx in anomaly_indices:
        sku = all_skus[idx]
        qty_90, _ = d90_map[sku]
        qty_7 = d7_map.get(sku, 0.0)
        avg_daily_90 = qty_90 / 90
        avg_daily_7 = qty_7 / 7

        if avg_daily_90 > 0:
            z = abs(avg_daily_7 - avg_daily_90) / (avg_daily_90 * 0.3 + 1e-9)
        else:
            z = 3.0

        if avg_daily_7 > avg_daily_90 * 1.5:
            anomaly_type = "demand_spike"
        elif avg_daily_7 < avg_daily_90 * 0.5 and avg_daily_90 > 0:
            anomaly_type = "demand_drop"
        else:
            anomaly_type = "unusual_pattern"

        anomalies.append(InventoryAnomalyItem(
            sku=sku,
            anomaly_type=anomaly_type,
            severity=classify_anomaly_severity(z),
            metric_value=round(avg_daily_7, 3),
            baseline_value=round(avg_daily_90, 3),
            detected_at=date.today().isoformat(),
        ))

    anomalies.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x.severity])
    result = AnomalyOut(anomalies=anomalies, total=len(anomalies))
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 2)
    return result
