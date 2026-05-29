"""Scenario Planner endpoints — digital twin simulation."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.scenarios import engine as sim_engine
from app.domains.scenarios import service
from app.models.scenario import Scenario, ScenarioRun
from app.models.user import User

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sc_dict(sc: Scenario) -> dict:
    return {
        "id": str(sc.id),
        "company_id": str(sc.company_id),
        "name": sc.name,
        "description": sc.description,
        "created_by": str(sc.created_by),
        "assumptions": sc.assumptions,
        "baseline_snapshot": sc.baseline_snapshot,
        "is_shared": sc.is_shared,
        "share_token": sc.share_token,
        "created_at": sc.created_at.isoformat(),
        "updated_at": sc.updated_at.isoformat(),
    }


def _run_dict(run: ScenarioRun) -> dict:
    return {
        "id": str(run.id),
        "scenario_id": str(run.scenario_id),
        "run_by": str(run.run_by),
        "assumptions_snapshot": run.assumptions_snapshot,
        "results": run.results,
        "run_at": run.run_at.isoformat(),
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_scenario(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new scenario with initial assumptions."""
    try:
        sc = await service.create_scenario(
            db,
            company_id=current_user.company_id,
            actor=current_user,
            name=payload.get("name", "New Scenario"),
            description=payload.get("description"),
            assumptions=payload.get("assumptions", {}),
            baseline_snapshot=payload.get("baseline_snapshot"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _sc_dict(sc)


@router.get("")
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List scenarios for the current company."""
    result = await service.list_scenarios(db, current_user.company_id, page, page_size)
    return {
        "items": [_sc_dict(sc) for sc in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a scenario with its run history."""
    try:
        sc = await service.get_scenario(db, current_user.company_id, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {**_sc_dict(sc), "runs": [_run_dict(r) for r in sc.runs]}


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: uuid.UUID = Path(...),
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update a scenario's name, description, or assumptions."""
    try:
        sc = await service.update_scenario(
            db,
            current_user.company_id,
            scenario_id,
            current_user,
            name=payload.get("name"),
            description=payload.get("description"),
            assumptions=payload.get("assumptions"),
            baseline_snapshot=payload.get("baseline_snapshot"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _sc_dict(sc)


@router.delete("/{scenario_id}", status_code=204, response_model=None)
async def delete_scenario(
    scenario_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a scenario and all its runs."""
    try:
        await service.delete_scenario(db, current_user.company_id, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Simulation ────────────────────────────────────────────────────────────────

@router.post("/{scenario_id}/run")
async def run_scenario(
    scenario_id: uuid.UUID = Path(...),
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run a simulation and persist the results as a ScenarioRun."""
    try:
        sc = await service.get_scenario(db, current_user.company_id, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    assumptions = payload.get("assumptions") or sc.assumptions
    baseline = sc.baseline_snapshot or {}
    results = sim_engine.run_simulation(baseline, assumptions)

    run = await service.save_run(
        db,
        scenario_id=scenario_id,
        actor=current_user,
        assumptions_snapshot=results["assumptions"],
        results=results,
        company_id=current_user.company_id,
    )
    return _run_dict(run)


@router.post("/simulate")
async def quick_simulate(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run a one-off simulation without persisting (for live assumption tuning)."""
    baseline = payload.get("baseline", {})
    assumptions = payload.get("assumptions", {})
    return sim_engine.run_simulation(baseline, assumptions)


# ── Sharing ───────────────────────────────────────────────────────────────────

@router.post("/{scenario_id}/share")
async def share_scenario(
    scenario_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate or retrieve the shareable token for a scenario."""
    try:
        token = await service.generate_share_token(db, current_user.company_id, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"share_token": token, "share_url": f"/dashboard/scenarios/shared/{token}"}
