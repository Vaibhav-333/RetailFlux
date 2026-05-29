"""Celery beat task: send each user a daily digest of their due/overdue tasks.

Runs at 07:00 UTC.  Respects users.prefs['email_task_digest'] — defaults to True
when the key is absent so opt-out is explicit.  Uses the existing Resend email
infrastructure (app/core/email.py); silently skips when RESEND_API_KEY is unset.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone

from celery import shared_task
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings

log = logging.getLogger(__name__)

_SYNC_DB_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)

# Terminal statuses — skip tasks in these states
_DONE_STATUSES = {"done", "cancelled"}


def _digest_html(name: str, due_today: list[dict], overdue: list[dict]) -> str:
    today_str = date.today().strftime("%B %d, %Y")

    def _task_rows(tasks: list[dict], row_bg: str) -> str:
        return "".join(
            f"<tr style='background:{row_bg}'>"
            f"<td style='padding:6px 10px;font-size:13px'>{t['title'][:80]}</td>"
            f"<td style='padding:6px 10px;font-size:12px;color:#64748b'>"
            f"{t['priority'].upper()}</td>"
            f"<td style='padding:6px 10px;font-size:12px;color:#64748b'>"
            f"{t['due_label']}</td>"
            f"</tr>"
            for t in tasks
        )

    due_section = (
        f"""
        <h3 style="color:#1e293b;font-size:14px;margin:20px 0 8px">
            Due today ({len(due_today)})
        </h3>
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="background:#f1f5f9">
            <th style="padding:6px 10px;text-align:left;font-size:12px">Task</th>
            <th style="padding:6px 10px;text-align:left;font-size:12px">Priority</th>
            <th style="padding:6px 10px;text-align:left;font-size:12px">Due</th>
          </tr></thead>
          <tbody>{_task_rows(due_today, '#fff')}</tbody>
        </table>"""
        if due_today else ""
    )

    overdue_section = (
        f"""
        <h3 style="color:#dc2626;font-size:14px;margin:20px 0 8px">
            Overdue ({len(overdue)})
        </h3>
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="background:#fef2f2">
            <th style="padding:6px 10px;text-align:left;font-size:12px">Task</th>
            <th style="padding:6px 10px;text-align:left;font-size:12px">Priority</th>
            <th style="padding:6px 10px;text-align:left;font-size:12px">Due</th>
          </tr></thead>
          <tbody>{_task_rows(overdue, '#fff7f7')}</tbody>
        </table>"""
        if overdue else ""
    )

    total = len(due_today) + len(overdue)
    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#fff">
  <div style="background:#6366f1;padding:24px 32px;border-radius:8px 8px 0 0">
    <h1 style="color:#fff;margin:0;font-size:20px">RetailFlux — Daily Task Digest</h1>
    <p style="color:#c7d2fe;margin:4px 0 0;font-size:13px">{today_str}</p>
  </div>

  <div style="padding:24px 32px">
    <p style="margin:0 0 4px">Hi {name},</p>
    <p style="color:#475569;margin:0 0 16px">
      You have <strong>{total}</strong> task{"s" if total != 1 else ""} that need{"" if total == 1 else "s"} attention today.
    </p>

    {due_section}
    {overdue_section}

    <div style="margin-top:24px">
      <a href="https://app.retailflux.io/tasks"
         style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;
                text-decoration:none;font-size:14px;font-weight:600">
        Open Task Centre →
      </a>
    </div>
  </div>

  <div style="padding:16px 32px;border-top:1px solid #e2e8f0">
    <p style="color:#94a3b8;font-size:11px;margin:0">
      Daily digest from RetailFlux.
      <a href="https://app.retailflux.io/dashboard/settings" style="color:#6366f1">
        Manage preferences
      </a>
    </p>
  </div>
</div>"""


async def _send_digest_for_company(company_id: str) -> dict:
    """Build and send daily digests for all opted-in users in one company."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.core.email import send_email  # noqa: PLC0415
    from app.models.task import Task, TaskAssignee  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415

    cid = uuid.UUID(company_id)
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

    sent = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        # Fetch all active users for this company
        users_result = await db.execute(
            select(User).where(
                User.company_id == cid,
                User.is_active.is_(True),
            )
        )
        users = users_result.scalars().all()

        for user in users:
            # Respect users.prefs['email_task_digest'] — default True
            prefs = user.prefs or {}
            if prefs.get("email_task_digest") is False:
                skipped += 1
                continue

            # Tasks assigned to this user, not yet terminal
            assigned_q = (
                select(Task)
                .join(TaskAssignee, TaskAssignee.task_id == Task.id)
                .where(
                    Task.company_id == cid,
                    TaskAssignee.user_id == user.id,
                    Task.status.notin_(list(_DONE_STATUSES)),
                )
            )
            task_result = await db.execute(assigned_q)
            all_tasks = task_result.scalars().all()

            due_today: list[dict] = []
            overdue: list[dict] = []

            for t in all_tasks:
                if t.due_at is None:
                    continue
                due_dt = t.due_at if t.due_at.tzinfo else t.due_at.replace(tzinfo=timezone.utc)
                if due_dt < today_start:
                    overdue.append({
                        "title": t.title,
                        "priority": t.priority,
                        "due_label": due_dt.strftime("%b %d"),
                    })
                elif today_start <= due_dt <= today_end:
                    due_today.append({
                        "title": t.title,
                        "priority": t.priority,
                        "due_label": "Today",
                    })

            if not due_today and not overdue:
                skipped += 1
                continue

            html = _digest_html(user.name or user.email, due_today, overdue)
            ok = await send_email(
                to=user.email,
                subject=f"RetailFlux — {len(due_today) + len(overdue)} tasks need your attention today",
                html=html,
            )
            if ok:
                sent += 1

    return {"company_id": company_id, "sent": sent, "skipped": skipped}


@shared_task(bind=True, name="app.workers.tasks.task_digest.daily_task_digest")
def daily_task_digest(self):  # type: ignore[no-untyped-def]
    """Send per-user daily task digests for all active companies."""
    with Session(_engine) as session:
        rows = session.execute(text("SELECT id FROM app.companies")).fetchall()

    company_ids = [str(r[0]) for r in rows]
    log.info("Daily task digest: processing %d companies", len(company_ids))

    total_sent = 0
    for cid in company_ids:
        result = asyncio.run(_send_digest_for_company(cid))
        total_sent += result.get("sent", 0)

    log.info("Daily task digest complete: %d total emails sent", total_sent)
    return {"companies": len(company_ids), "emails_sent": total_sent}
