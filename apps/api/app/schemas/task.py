"""Pydantic schemas for the Task System."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskAssigneeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role_in_task: str
    assigned_at: datetime


class TaskActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    kind: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime


class TaskCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    created_at: datetime
    edited_at: Optional[datetime] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    task_type: str
    source: str
    departments: list[str] = []
    assignees: list[TaskAssigneeOut] = []
    due_at: Optional[datetime] = None
    sla_hours: Optional[int] = None
    breached: bool = False
    task_metadata: dict = {}
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("departments", mode="before")
    @classmethod
    def _coerce_departments(cls, v: Any) -> list[str]:
        """Convert TaskDepartment ORM objects to plain strings."""
        if not v:
            return []
        if isinstance(v, list) and v and isinstance(v[0], str):
            return v
        return [d.department if hasattr(d, "department") else str(d) for d in v]


class TaskDetailOut(TaskOut):
    """Extends TaskOut with full activity and comments."""
    activity: list[TaskActivityOut] = []
    comments: list[TaskCommentOut] = []


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = "medium"
    task_type: str = "general"
    source: str = "manual"
    departments: list[str] = []
    due_at: Optional[datetime] = None
    sla_hours: Optional[int] = Field(None, ge=1)
    task_metadata: dict = {}
    assignee_ids: list[uuid.UUID] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    departments: Optional[list[str]] = None
    due_at: Optional[datetime] = None
    sla_hours: Optional[int] = Field(None, ge=1)
    task_metadata: Optional[dict] = None


class TaskTransition(BaseModel):
    to_status: str = Field(..., description="Target workflow status")


class TaskAssignRequest(BaseModel):
    user_id: uuid.UUID
    role_in_task: str = "collaborator"


class TaskCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    size: int


class ActivityListResponse(BaseModel):
    items: list[TaskActivityOut]
    total: int
    page: int
    size: int


# ── Task Analytics schemas ─────────────────────────────────────────────────────


class DepartmentProductivity(BaseModel):
    department: str
    total: int
    done: int
    in_progress: int
    blocked: int
    completion_rate: float  # 0.0–1.0


class UserWorkload(BaseModel):
    user_id: uuid.UUID
    open_count: int
    in_progress_count: int
    blocked_count: int
    overdue_count: int
    total_open: int


class BottleneckTask(BaseModel):
    task_id: uuid.UUID
    title: str
    status: str
    priority: str
    days_stuck: float
    departments: list[str]
    breached: bool


class TeamScore(BaseModel):
    total_tasks: int
    done_tasks: int
    open_tasks: int
    overdue_tasks: int
    completion_rate: float
    on_time_rate: float
    avg_cycle_days: float


class TaskAnalyticsDashboard(BaseModel):
    department_productivity: list[DepartmentProductivity]
    workload: list[UserWorkload]
    bottlenecks: list[BottleneckTask]
    team_score: TeamScore


class TaskRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: str
    departments: list[str] = []
    source: str
    task_metadata: dict = {}
    created_at: datetime

    @field_validator("departments", mode="before")
    @classmethod
    def _coerce_depts(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, list) and v and isinstance(v[0], str):
            return v
        return [d.department if hasattr(d, "department") else str(d) for d in v]


class TaskRecommendationListResponse(BaseModel):
    items: list[TaskRecommendationOut]
    total: int
    page: int
    size: int


# ── Milestone schemas ──────────────────────────────────────────────────────────


class MilestoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    due_at: Optional[datetime] = None


class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MilestoneListResponse(BaseModel):
    items: list[MilestoneOut]
    total: int
    page: int
    size: int


# ── Sprint schemas ─────────────────────────────────────────────────────────────


class SprintTaskRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sprint_id: uuid.UUID
    task_id: uuid.UUID
    added_at: datetime


class SprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    goal: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    capacity_hours: Optional[float] = Field(None, ge=0)


class SprintUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    goal: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    status: Optional[str] = None
    capacity_hours: Optional[float] = Field(None, ge=0)


class SprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    goal: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    status: str
    capacity_hours: Optional[float] = None
    task_ids: list[uuid.UUID] = []
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("task_ids", mode="before")
    @classmethod
    def _extract_task_ids(cls, v: Any) -> list[uuid.UUID]:
        if not v:
            return []
        if isinstance(v, list) and v and isinstance(v[0], uuid.UUID):
            return v
        return [st.task_id for st in v]


class SprintListResponse(BaseModel):
    items: list[SprintOut]
    total: int
    page: int
    size: int


class SprintAddTask(BaseModel):
    task_id: uuid.UUID


# ── Approval schemas ───────────────────────────────────────────────────────────


class ApprovalRequest(BaseModel):
    approver_id: uuid.UUID


class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    note: Optional[str] = None


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    approver_id: uuid.UUID
    requested_by: uuid.UUID
    decision: Optional[str] = None
    note: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime


class ApprovalListResponse(BaseModel):
    items: list[ApprovalOut]
    total: int
    page: int
    size: int
