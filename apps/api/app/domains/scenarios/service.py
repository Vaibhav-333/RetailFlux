"""Scenario CRUD and persistence service."""
from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.event_log import record_event
from app.models.scenario import Scenario, ScenarioRun
from app.models.user import User


async def create_scenario(
    db: AsyncSession,
    company_id: uuid.UUID,
    actor: User,
    name: str,
    description: Optional[str] = None,
    assumptions: Optional[dict] = None,
    baseline_snapshot: Optional[dict] = None,
) -> Scenario:
    sc = Scenario(
        company_id=company_id,
        created_by=actor.id,
        name=name,
        description=description,
        assumptions=assumptions or {},
        baseline_snapshot=baseline_snapshot,
    )
    db.add(sc)
    await db.commit()
    await db.refresh(sc)
    asyncio.ensure_future(record_event(
        db,
        company_id=company_id,
        kind="scenario.created",
        payload={"name": sc.name},
        actor_id=actor.id,
        resource_type="scenario",
        resource_id=sc.id,
    ))
    return sc


async def list_scenarios(
    db: AsyncSession,
    company_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    base_q = select(Scenario).where(Scenario.company_id == company_id)
    count_result = await db.execute(base_q)
    total = len(count_result.scalars().all())

    q = (
        base_q
        .order_by(Scenario.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_scenario(
    db: AsyncSession,
    company_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Scenario:
    result = await db.execute(
        select(Scenario)
        .where(Scenario.id == scenario_id, Scenario.company_id == company_id)
        .options(selectinload(Scenario.runs))
    )
    sc = result.scalar_one_or_none()
    if sc is None:
        raise ValueError(f"Scenario {scenario_id} not found")
    return sc


async def update_scenario(
    db: AsyncSession,
    company_id: uuid.UUID,
    scenario_id: uuid.UUID,
    actor: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    assumptions: Optional[dict] = None,
    baseline_snapshot: Optional[dict] = None,
) -> Scenario:
    sc = await get_scenario(db, company_id, scenario_id)
    if name is not None:
        sc.name = name
    if description is not None:
        sc.description = description
    if assumptions is not None:
        sc.assumptions = assumptions
    if baseline_snapshot is not None:
        sc.baseline_snapshot = baseline_snapshot
    sc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sc)
    return sc


async def delete_scenario(
    db: AsyncSession,
    company_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> None:
    sc = await get_scenario(db, company_id, scenario_id)
    await db.delete(sc)
    await db.commit()


async def save_run(
    db: AsyncSession,
    scenario_id: uuid.UUID,
    actor: User,
    assumptions_snapshot: dict,
    results: dict,
    company_id: uuid.UUID | None = None,
) -> ScenarioRun:
    run = ScenarioRun(
        scenario_id=scenario_id,
        run_by=actor.id,
        assumptions_snapshot=assumptions_snapshot,
        results=results,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    if company_id is not None:
        asyncio.ensure_future(record_event(
            db,
            company_id=company_id,
            kind="scenario.run",
            payload={"scenario_id": str(scenario_id), "run_id": str(run.id)},
            actor_id=actor.id,
            resource_type="scenario",
            resource_id=scenario_id,
        ))
    return run


async def generate_share_token(
    db: AsyncSession,
    company_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> str:
    sc = await get_scenario(db, company_id, scenario_id)
    if not sc.share_token:
        sc.share_token = secrets.token_urlsafe(24)
        sc.is_shared = True
        sc.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(sc)
    return sc.share_token
