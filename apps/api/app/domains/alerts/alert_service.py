"""Alert domain — preference storage (MongoDB) and alert dispatch."""
import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.core.mongodb import get_mongo_db
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.summary_service import get_dashboard_summary
from app.domains.insights.anomaly_service import detect_anomalies
from app.models.notification import Notification
from app.models.user import User
from app.schemas.alerts import AlertCheckResult, AlertPrefsOut, AlertPrefsUpdate

_DEFAULTS: dict[str, Any] = {
    "email_alerts_enabled": True,
    "alert_on_anomalies": True,
    "alert_on_low_stock": True,
}

# Stricter z-score threshold for email alerts vs. the dashboard's 2.0
ANOMALY_ALERT_THRESHOLD = 2.5


async def get_alert_prefs(user_id: uuid.UUID) -> AlertPrefsOut:
    col = get_mongo_db()["alert_prefs"]
    doc = await col.find_one({"user_id": str(user_id)})
    merged = {**_DEFAULTS, **(doc or {})}
    return AlertPrefsOut(**{k: merged[k] for k in AlertPrefsOut.model_fields})


async def update_alert_prefs(
    user_id: uuid.UUID,
    prefs: AlertPrefsUpdate,
) -> AlertPrefsOut:
    col = get_mongo_db()["alert_prefs"]
    updates = {k: v for k, v in prefs.model_dump().items() if v is not None}
    if updates:
        await col.update_one(
            {"user_id": str(user_id)},
            {"$set": updates},
            upsert=True,
        )
    return await get_alert_prefs(user_id)


async def check_and_send_alerts(
    company_id: uuid.UUID,
    db: AsyncSession,
) -> AlertCheckResult:
    company_id_str = str(company_id)

    summary_result, ops_result = await asyncio.gather(
        get_dashboard_summary(company_id_str),
        get_operations_kpis(company_id_str),
        return_exceptions=True,
    )

    anomalies = (
        detect_anomalies(summary_result.daily_revenue, threshold=ANOMALY_ALERT_THRESHOLD)
        if not isinstance(summary_result, Exception)
        else []
    )

    low_stock_skus = (
        [s for s in ops_result.low_stock_skus if s.stock_level < s.reorder_point]
        if not isinstance(ops_result, Exception)
        else []
    )

    result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.is_active == True,  # noqa: E712
        )
    )
    company_users = result.scalars().all()

    prefs_col = get_mongo_db()["alert_prefs"]
    user_ids = [str(u.id) for u in company_users]
    prefs_docs = await prefs_col.find({"user_id": {"$in": user_ids}}).to_list(length=200)
    prefs_map = {d["user_id"]: d for d in prefs_docs}

    emails_sent = 0
    notifications_created = 0

    for user in company_users:
        prefs = {**_DEFAULTS, **(prefs_map.get(str(user.id), {}))}
        if not prefs["email_alerts_enabled"]:
            continue

        if anomalies and prefs["alert_on_anomalies"]:
            sent = await send_email(
                to=user.email,
                subject="RetailFlux Alert: Revenue Anomalies Detected",
                html=_anomaly_email_html(user.name, anomalies),
            )
            if sent:
                emails_sent += 1
            dates_str = ", ".join(a.date for a in anomalies[:3])
            db.add(
                Notification(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    type="warning",
                    payload={
                        "title": "Revenue anomaly detected",
                        "message": f"{len(anomalies)} spike{'s' if len(anomalies) > 1 else ''} detected (z > 2.5σ): {dates_str}",
                        "anomaly_count": len(anomalies),
                        "dates": [a.date for a in anomalies[:3]],
                    },
                )
            )
            notifications_created += 1

        if low_stock_skus and prefs["alert_on_low_stock"]:
            sent = await send_email(
                to=user.email,
                subject="RetailFlux Alert: Low Stock Warning",
                html=_low_stock_email_html(user.name, low_stock_skus),
            )
            if sent:
                emails_sent += 1
            skus_str = ", ".join(s.sku for s in low_stock_skus[:5])
            db.add(
                Notification(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    type="warning",
                    payload={
                        "title": "Low stock warning",
                        "message": f"{len(low_stock_skus)} SKU{'s' if len(low_stock_skus) > 1 else ''} below reorder point: {skus_str}",
                        "sku_count": len(low_stock_skus),
                        "skus": [s.sku for s in low_stock_skus[:5]],
                    },
                )
            )
            notifications_created += 1

    if notifications_created:
        await db.commit()

    return AlertCheckResult(
        anomalies_found=len(anomalies),
        low_stock_skus_found=len(low_stock_skus),
        emails_sent=emails_sent,
        notifications_created=notifications_created,
    )


def _anomaly_email_html(name: str, anomalies: list) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 8px'>{a.date}</td>"
        f"<td style='padding:4px 8px'>${a.revenue:,.0f}</td>"
        f"<td style='padding:4px 8px'>{a.z_score:+.2f}σ</td></tr>"
        for a in anomalies
    )
    return f"""
<div style="font-family:sans-serif;max-width:560px;margin:0 auto">
  <h2 style="color:#7c3aed">RetailFlux — Revenue Anomaly Alert</h2>
  <p>Hi {name},</p>
  <p>{len(anomalies)} revenue anomal{'ies' if len(anomalies) > 1 else 'y'} detected
     (z-score &gt; 2.5σ):</p>
  <table style="border-collapse:collapse;width:100%">
    <thead><tr style="background:#f3f4f6">
      <th style="padding:4px 8px;text-align:left">Date</th>
      <th style="padding:4px 8px;text-align:left">Revenue</th>
      <th style="padding:4px 8px;text-align:left">Z-Score</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#6b7280;font-size:12px;margin-top:24px">
    You are receiving this because anomaly alerts are enabled in your RetailFlux settings.
  </p>
</div>"""


def _low_stock_email_html(name: str, skus: list) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 8px'>{s.sku}</td>"
        f"<td style='padding:4px 8px'>{s.stock_level:.0f}</td>"
        f"<td style='padding:4px 8px'>{s.reorder_point}</td></tr>"
        for s in skus[:10]
    )
    return f"""
<div style="font-family:sans-serif;max-width:560px;margin:0 auto">
  <h2 style="color:#d97706">RetailFlux — Low Stock Alert</h2>
  <p>Hi {name},</p>
  <p>{len(skus)} SKU{'s' if len(skus) > 1 else ''} below reorder point:</p>
  <table style="border-collapse:collapse;width:100%">
    <thead><tr style="background:#f3f4f6">
      <th style="padding:4px 8px;text-align:left">SKU</th>
      <th style="padding:4px 8px;text-align:left">Stock Level</th>
      <th style="padding:4px 8px;text-align:left">Reorder Point</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#6b7280;font-size:12px;margin-top:24px">
    You are receiving this because low stock alerts are enabled in your RetailFlux settings.
  </p>
</div>"""
