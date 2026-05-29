"""Weekly task analytics digest email for company managers/admins."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.models.user import User

log = logging.getLogger(__name__)

# Roles that receive the task digest
_DIGEST_ROLES = {"ceo", "admin", "manager"}


def _digest_html(
    name: str,
    score_data: dict,
    bottlenecks: list,
    ai_rec_count: int,
) -> str:
    total = score_data.get("total_tasks", 0)
    done = score_data.get("done_tasks", 0)
    open_tasks = score_data.get("open_tasks", 0)
    overdue = score_data.get("overdue_tasks", 0)
    completion_pct = f"{score_data.get('completion_rate', 0) * 100:.1f}"
    on_time_pct = f"{score_data.get('on_time_rate', 0) * 100:.1f}"
    avg_cycle = score_data.get("avg_cycle_days", 0)

    bottleneck_rows = "".join(
        f"<tr>"
        f"<td style='padding:4px 8px'>{b.get('title', '')[:60]}</td>"
        f"<td style='padding:4px 8px;color:#d97706'>{b.get('days_stuck', 0):.1f}d</td>"
        f"<td style='padding:4px 8px'>{b.get('priority', '')}</td>"
        f"</tr>"
        for b in bottlenecks[:5]
    )

    ai_section = (
        f"<p><strong>{ai_rec_count}</strong> AI-generated tasks are awaiting review in your "
        f"<a href='https://app.retailflux.io/dashboard/tasks/analytics' style='color:#6366f1'>Task Analytics</a> inbox.</p>"
        if ai_rec_count > 0
        else "<p>No pending AI recommendations.</p>"
    )

    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#6366f1;padding:24px 32px;border-radius:8px 8px 0 0">
    <h1 style="color:#fff;margin:0;font-size:20px">RetailFlux — Weekly Task Digest</h1>
    <p style="color:#c7d2fe;margin:4px 0 0;font-size:13px">
      {datetime.now(timezone.utc).strftime('%B %d, %Y')}
    </p>
  </div>

  <div style="padding:24px 32px">
    <p>Hi {name},</p>
    <p>Here's your weekly task performance summary:</p>

    <!-- KPI row -->
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr>
        <td style="text-align:center;padding:12px;background:#f8fafc;border-radius:6px">
          <div style="font-size:28px;font-weight:bold;color:#1e293b">{total}</div>
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">Total</div>
        </td>
        <td style="width:8px"></td>
        <td style="text-align:center;padding:12px;background:#f0fdf4;border-radius:6px">
          <div style="font-size:28px;font-weight:bold;color:#16a34a">{done}</div>
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">Done</div>
        </td>
        <td style="width:8px"></td>
        <td style="text-align:center;padding:12px;background:#fef3c7;border-radius:6px">
          <div style="font-size:28px;font-weight:bold;color:#b45309">{overdue}</div>
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">Overdue</div>
        </td>
        <td style="width:8px"></td>
        <td style="text-align:center;padding:12px;background:#eff6ff;border-radius:6px">
          <div style="font-size:28px;font-weight:bold;color:#1d4ed8">{open_tasks}</div>
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">Open</div>
        </td>
      </tr>
    </table>

    <p style="color:#475569;font-size:13px">
      Completion rate: <strong>{completion_pct}%</strong> ·
      On-time rate: <strong>{on_time_pct}%</strong> ·
      Avg cycle: <strong>{avg_cycle:.1f}d</strong>
    </p>

    <!-- Bottlenecks -->
    {"" if not bottlenecks else f'''
    <h3 style="color:#dc2626;font-size:14px;margin-top:24px">⚠ Bottlenecks ({len(bottlenecks)} tasks stuck)</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#fef2f2">
        <th style="padding:4px 8px;text-align:left">Task</th>
        <th style="padding:4px 8px;text-align:left">Stuck</th>
        <th style="padding:4px 8px;text-align:left">Priority</th>
      </tr></thead>
      <tbody>{bottleneck_rows}</tbody>
    </table>
    '''}

    <!-- AI Recommendations -->
    <h3 style="color:#6366f1;font-size:14px;margin-top:24px">✨ AI Recommendations</h3>
    {ai_section}

    <div style="margin-top:24px">
      <a href="https://app.retailflux.io/dashboard/tasks/analytics"
         style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;
                text-decoration:none;font-size:14px;font-weight:600">
        View Full Analytics →
      </a>
    </div>
  </div>

  <div style="padding:16px 32px;border-top:1px solid #e2e8f0">
    <p style="color:#94a3b8;font-size:11px;margin:0">
      You're receiving this weekly digest because you manage tasks in RetailFlux.
      <a href="https://app.retailflux.io/dashboard/settings" style="color:#6366f1">Manage preferences</a>
    </p>
  </div>
</div>"""


async def send_task_digest(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> dict:
    """
    Fetch analytics + pending AI recs, then email all managers/CEOs/admins.

    Returns a summary of emails attempted.
    """
    from app.domains.tasks.analytics_service import (  # noqa: PLC0415
        get_bottlenecks,
        get_team_score,
    )
    from app.domains.tasks.recommendation import list_recommendations  # noqa: PLC0415

    # Gather data
    try:
        score = await get_team_score(db, company_id)
        bottlenecks = await get_bottlenecks(db, company_id, stuck_hours=48, limit=5)
        _, ai_rec_count = await list_recommendations(db, company_id, page=1, size=1)
    except Exception as exc:  # noqa: BLE001
        log.warning("Digest data gather failed for company %s: %s", company_id, exc)
        return {"status": "error", "error": str(exc)}

    score_data = score.model_dump()
    bottleneck_dicts = [b.model_dump() for b in bottlenecks]

    # Find eligible recipients
    result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.is_active.is_(True),
        )
    )
    users = result.scalars().all()
    recipients = [u for u in users if u.role in _DIGEST_ROLES]

    if not recipients:
        log.info("No digest recipients for company %s", company_id)
        return {"status": "ok", "emails_sent": 0}

    sent = 0
    for user in recipients:
        html = _digest_html(user.name, score_data, bottleneck_dicts, ai_rec_count)
        ok = await send_email(
            to=user.email,
            subject="RetailFlux — Weekly Task Performance Digest",
            html=html,
        )
        if ok:
            sent += 1

    log.info("Task digest sent to %d recipients for company %s", sent, company_id)
    return {"status": "ok", "emails_sent": sent, "recipients": len(recipients)}
