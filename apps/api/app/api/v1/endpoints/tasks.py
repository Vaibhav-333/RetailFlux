"""Task management REST endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.tasks import service
from app.models.user import User
from app.schemas.task import (
    ActivityListResponse,
    ApprovalDecision,
    ApprovalListResponse,
    ApprovalOut,
    ApprovalRequest,
    BottleneckTask,
    DepartmentProductivity,
    MilestoneCreate,
    MilestoneListResponse,
    MilestoneOut,
    MilestoneUpdate,
    SprintAddTask,
    SprintCreate,
    SprintListResponse,
    SprintOut,
    SprintUpdate,
    TaskAnalyticsDashboard,
    TaskAssignRequest,
    TaskCommentCreate,
    TaskCommentOut,
    TaskCreate,
    TaskDetailOut,
    TaskListResponse,
    TaskOut,
    TaskRecommendationListResponse,
    TaskRecommendationOut,
    TaskTransition,
    TaskUpdate,
    TeamScore,
    UserWorkload,
)

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Analytics endpoints (must be before /{task_id} to avoid UUID conflict) ──────


@router.get("/analytics/dashboard", response_model=TaskAnalyticsDashboard)
async def analytics_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskAnalyticsDashboard:
    from app.domains.tasks.analytics_service import get_analytics_dashboard  # noqa: PLC0415
    return await get_analytics_dashboard(db, current_user.company_id)


@router.get("/analytics/department", response_model=list[DepartmentProductivity])
async def analytics_department(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[DepartmentProductivity]:
    from app.domains.tasks.analytics_service import get_department_productivity  # noqa: PLC0415
    return await get_department_productivity(db, current_user.company_id)


@router.get("/analytics/workload", response_model=list[UserWorkload])
async def analytics_workload(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[UserWorkload]:
    from app.domains.tasks.analytics_service import get_workload  # noqa: PLC0415
    return await get_workload(db, current_user.company_id)


@router.get("/analytics/bottlenecks", response_model=list[BottleneckTask])
async def analytics_bottlenecks(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    stuck_hours: int = Query(24, ge=1, le=720),
    limit: int = Query(20, ge=1, le=100),
) -> list[BottleneckTask]:
    from app.domains.tasks.analytics_service import get_bottlenecks  # noqa: PLC0415
    return await get_bottlenecks(db, current_user.company_id, stuck_hours=stuck_hours, limit=limit)


@router.get("/analytics/team-score", response_model=TeamScore)
async def analytics_team_score(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TeamScore:
    from app.domains.tasks.analytics_service import get_team_score  # noqa: PLC0415
    return await get_team_score(db, current_user.company_id)


# ── Recommendations endpoints (before /{task_id}) ───────────────────────────────


@router.get("/recommendations", response_model=TaskRecommendationListResponse)
async def list_recommendations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> TaskRecommendationListResponse:
    from app.domains.tasks.recommendation import list_recommendations as _list  # noqa: PLC0415
    items, total = await _list(db, current_user.company_id, page=page, size=size)
    return TaskRecommendationListResponse(
        items=[TaskRecommendationOut.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/recommendations/refresh", response_model=list[TaskRecommendationOut], status_code=201)
async def refresh_recommendations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[TaskRecommendationOut]:
    from app.domains.tasks.recommendation import generate_recommendations  # noqa: PLC0415
    tasks = await generate_recommendations(db, current_user.company_id, current_user.id)
    return [TaskRecommendationOut.model_validate(t) for t in tasks]


# ── Standard CRUD endpoints ──────────────────────────────────────────────────────


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status"),
    assignee_id: Optional[uuid.UUID] = Query(None, description="Filter by assignee user ID"),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> TaskListResponse:
    items, total = await service.list_tasks(
        db,
        current_user.company_id,
        status=status,
        assignee_id=assignee_id,
        page=page,
        size=size,
    )
    return TaskListResponse(
        items=[TaskOut.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await service.create_task(db, current_user.company_id, current_user.id, body)
    return TaskOut.model_validate(task)


# ── Milestone list/create (must come before /{task_id} to avoid route shadow) ──


@router.get("/milestones", response_model=MilestoneListResponse)
async def list_milestones(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    milestone_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> MilestoneListResponse:
    from app.domains.tasks.sprints import list_milestones as _list  # noqa: PLC0415
    items, total = await _list(
        db, current_user.company_id, milestone_status=milestone_status, page=page, size=size
    )
    return MilestoneListResponse(
        items=[MilestoneOut.model_validate(m) for m in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/milestones", response_model=MilestoneOut, status_code=201)
async def create_milestone(
    body: MilestoneCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    from app.domains.tasks.sprints import create_milestone as _create  # noqa: PLC0415
    m = await _create(
        db, current_user.company_id, current_user.id,
        body.name, body.description, body.due_at,
    )
    return MilestoneOut.model_validate(m)


# ── Sprint list/create (must come before /{task_id} to avoid route shadow) ──────


@router.get("/sprints", response_model=SprintListResponse)
async def list_sprints(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    sprint_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> SprintListResponse:
    from app.domains.tasks.sprints import list_sprints as _list  # noqa: PLC0415
    items, total = await _list(
        db, current_user.company_id, sprint_status=sprint_status, page=page, size=size
    )
    return SprintListResponse(
        items=[SprintOut.model_validate(s) for s in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/sprints", response_model=SprintOut, status_code=201)
async def create_sprint(
    body: SprintCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SprintOut:
    from app.domains.tasks.sprints import create_sprint as _create  # noqa: PLC0415
    s = await _create(
        db, current_user.company_id, current_user.id,
        body.name, body.starts_at, body.ends_at,
        goal=body.goal,
        capacity_hours=body.capacity_hours,
    )
    return SprintOut.model_validate(s)


@router.get("/{task_id}", response_model=TaskDetailOut)
async def get_task(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailOut:
    task = await service.get_task(db, current_user.company_id, task_id)
    return TaskDetailOut.model_validate(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await service.update_task(db, current_user.company_id, task_id, body, current_user.id)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=204, response_model=None)
async def delete_task(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_task(db, current_user.company_id, task_id, current_user.id)


@router.post("/{task_id}/transition", response_model=TaskOut)
async def transition_task(
    task_id: uuid.UUID,
    body: TaskTransition,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await service.transition_task(
        db, current_user.company_id, task_id, body, current_user.id
    )
    return TaskOut.model_validate(task)


@router.post("/{task_id}/assignees", response_model=TaskOut)
async def assign_task(
    task_id: uuid.UUID,
    body: TaskAssignRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await service.assign_task(
        db, current_user.company_id, task_id, body, current_user.id
    )
    return TaskOut.model_validate(task)


@router.delete("/{task_id}/assignees/{user_id}", response_model=TaskOut)
async def remove_assignee(
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await service.remove_assignee(
        db, current_user.company_id, task_id, user_id, current_user.id
    )
    return TaskOut.model_validate(task)


@router.post("/{task_id}/comments", response_model=TaskCommentOut, status_code=201)
async def add_comment(
    task_id: uuid.UUID,
    body: TaskCommentCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskCommentOut:
    comment = await service.add_comment(
        db, current_user.company_id, task_id, current_user.id, body
    )
    return TaskCommentOut.model_validate(comment)


@router.get("/{task_id}/activity", response_model=ActivityListResponse)
async def get_activity(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> ActivityListResponse:
    items, total = await service.get_activity(db, task_id, page=page, size=size)
    return ActivityListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=page,
        size=size,
    )


# ── Approval endpoints ────────────────────────────────────────────────────────


@router.get("/approvals/pending", response_model=ApprovalListResponse)
async def list_pending_approvals(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> ApprovalListResponse:
    from app.domains.tasks.approvals import list_pending_approvals as _list  # noqa: PLC0415
    items, total = await _list(db, current_user.company_id, current_user.id, page=page, size=size)
    return ApprovalListResponse(
        items=[ApprovalOut.model_validate(a) for a in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/{task_id}/approvals", response_model=ApprovalOut, status_code=201)
async def request_approval(
    task_id: uuid.UUID,
    body: ApprovalRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ApprovalOut:
    from app.domains.tasks.approvals import request_approval as _req  # noqa: PLC0415
    approval = await _req(
        db, current_user.company_id, task_id, body.approver_id, current_user.id
    )
    return ApprovalOut.model_validate(approval)


@router.get("/{task_id}/approvals", response_model=list[ApprovalOut])
async def list_task_approvals(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalOut]:
    from app.domains.tasks.approvals import list_task_approvals as _list  # noqa: PLC0415
    items = await _list(db, current_user.company_id, task_id)
    return [ApprovalOut.model_validate(a) for a in items]


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalOut)
async def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ApprovalOut:
    from app.domains.tasks.approvals import decide_approval as _decide  # noqa: PLC0415
    role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    approval = await _decide(
        db,
        current_user.company_id,
        approval_id,
        current_user.id,
        role,
        body.decision,
        body.note,
    )
    return ApprovalOut.model_validate(approval)


# ── Department board endpoint ──────────────────────────────────────────────────


@router.get("/board/{department}", response_model=TaskListResponse)
async def department_board(
    department: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    sprint_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
) -> TaskListResponse:
    from app.domains.tasks.sprints import get_department_board  # noqa: PLC0415
    items, total = await get_department_board(
        db,
        current_user.company_id,
        department,
        sprint_id=sprint_id,
        page=page,
        size=size,
    )
    return TaskListResponse(
        items=[TaskOut.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


# ── Milestone detail endpoints ─────────────────────────────────────────────────


@router.get("/milestones/{milestone_id}", response_model=MilestoneOut)
async def get_milestone(
    milestone_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    from app.domains.tasks.sprints import get_milestone as _get  # noqa: PLC0415
    m = await _get(db, current_user.company_id, milestone_id)
    return MilestoneOut.model_validate(m)


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
async def update_milestone(
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    from app.domains.tasks.sprints import update_milestone as _update  # noqa: PLC0415
    m = await _update(
        db, current_user.company_id, milestone_id,
        name=body.name,
        description=body.description,
        due_at=body.due_at,
        milestone_status=body.status,
    )
    return MilestoneOut.model_validate(m)


@router.delete("/milestones/{milestone_id}", status_code=204, response_model=None)
async def delete_milestone(
    milestone_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    from app.domains.tasks.sprints import delete_milestone as _delete  # noqa: PLC0415
    await _delete(db, current_user.company_id, milestone_id)


# ── Sprint detail endpoints ────────────────────────────────────────────────────


@router.get("/sprints/{sprint_id}", response_model=SprintOut)
async def get_sprint(
    sprint_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SprintOut:
    from app.domains.tasks.sprints import get_sprint as _get  # noqa: PLC0415
    s = await _get(db, current_user.company_id, sprint_id)
    return SprintOut.model_validate(s)


@router.patch("/sprints/{sprint_id}", response_model=SprintOut)
async def update_sprint(
    sprint_id: uuid.UUID,
    body: SprintUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SprintOut:
    from app.domains.tasks.sprints import update_sprint as _update  # noqa: PLC0415
    s = await _update(
        db, current_user.company_id, sprint_id,
        name=body.name,
        goal=body.goal,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        sprint_status=body.status,
        capacity_hours=body.capacity_hours,
    )
    return SprintOut.model_validate(s)


@router.delete("/sprints/{sprint_id}", status_code=204, response_model=None)
async def delete_sprint(
    sprint_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    from app.domains.tasks.sprints import delete_sprint as _delete  # noqa: PLC0415
    await _delete(db, current_user.company_id, sprint_id)


@router.post("/sprints/{sprint_id}/tasks", response_model=SprintOut)
async def add_task_to_sprint(
    sprint_id: uuid.UUID,
    body: SprintAddTask,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SprintOut:
    from app.domains.tasks.sprints import add_task_to_sprint as _add  # noqa: PLC0415
    s = await _add(db, current_user.company_id, sprint_id, body.task_id)
    return SprintOut.model_validate(s)


@router.delete("/sprints/{sprint_id}/tasks/{task_id}", response_model=SprintOut)
async def remove_task_from_sprint(
    sprint_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SprintOut:
    from app.domains.tasks.sprints import remove_task_from_sprint as _remove  # noqa: PLC0415
    s = await _remove(db, current_user.company_id, sprint_id, task_id)
    return SprintOut.model_validate(s)


@router.get("/sprints/{sprint_id}/tasks", response_model=TaskListResponse)
async def get_sprint_tasks(
    sprint_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    from app.domains.tasks.sprints import get_sprint_tasks as _tasks  # noqa: PLC0415
    items = await _tasks(db, current_user.company_id, sprint_id)
    return TaskListResponse(
        items=[TaskOut.model_validate(t) for t in items],
        total=len(items),
        page=1,
        size=len(items) or 1,
    )
