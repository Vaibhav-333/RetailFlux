"""Backend tests for sprint planning and approval workflow endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.main import app
from app.models.task import Sprint, TaskApproval
from app.models.user import User

# ── Fixed IDs ─────────────────────────────────────────────────────────────────

TASK_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
APPROVER_ID = uuid.uuid4()
APPROVAL_ID = uuid.uuid4()
SPRINT_ID = uuid.uuid4()
COMPANY_ID = uuid.uuid4()
NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)
LATER = datetime(2025, 6, 15, tzinfo=timezone.utc)


# ── Fake helpers ──────────────────────────────────────────────────────────────


def _fake_user(role: str = "ceo") -> MagicMock:
    u = MagicMock(spec=User)
    u.id = USER_ID
    u.email = "ceo@test.com"
    u.name = "CEO"
    u.role = role
    u.company_id = COMPANY_ID
    u.is_active = True
    return u


def _fake_approval(*, decision: str | None = None) -> MagicMock:
    a = MagicMock(spec=TaskApproval)
    a.id = APPROVAL_ID
    a.task_id = TASK_ID
    a.approver_id = APPROVER_ID
    a.requested_by = USER_ID
    a.decision = decision
    a.note = None
    a.decided_at = NOW if decision else None
    a.created_at = NOW
    return a


def _fake_sprint() -> MagicMock:
    s = MagicMock(spec=Sprint)
    s.id = SPRINT_ID
    s.company_id = COMPANY_ID
    s.name = "Sprint 1"
    s.goal = None
    s.starts_at = NOW
    s.ends_at = LATER
    s.status = "planning"
    s.capacity_hours = None
    # task_ids must be a plain list so Pydantic's field_validator returns []
    s.task_ids = []
    s.sprint_tasks = []
    s.created_by = USER_ID
    s.created_at = NOW
    s.updated_at = NOW
    return s


# ── DB + auth fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _override_db():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def _fake_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _fake_get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def _as_ceo():
    user = _fake_user("ceo")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def _as_sales():
    user = _fake_user("sales")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ═══════════════════════════════════════════════════════════════════════════════
# Approval: request
# ═══════════════════════════════════════════════════════════════════════════════


async def test_request_approval_success(_override_db, _as_ceo):
    approval = _fake_approval()
    with patch(
        "app.domains.tasks.approvals.request_approval", new_callable=AsyncMock
    ) as mock:
        mock.return_value = approval
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{TASK_ID}/approvals",
                json={"approver_id": str(APPROVER_ID)},
            )

    assert r.status_code == 201
    data = r.json()
    assert data["task_id"] == str(TASK_ID)
    assert data["approver_id"] == str(APPROVER_ID)
    assert data["decision"] is None


async def test_request_approval_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/tasks/{TASK_ID}/approvals",
            json={"approver_id": str(APPROVER_ID)},
        )
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Approval: list pending
# ═══════════════════════════════════════════════════════════════════════════════


async def test_list_pending_approvals_empty(_override_db, _as_ceo):
    with patch(
        "app.domains.tasks.approvals.list_pending_approvals", new_callable=AsyncMock
    ) as mock:
        mock.return_value = ([], 0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks/approvals/pending")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_pending_approvals_has_items(_override_db, _as_ceo):
    approval = _fake_approval()
    with patch(
        "app.domains.tasks.approvals.list_pending_approvals", new_callable=AsyncMock
    ) as mock:
        mock.return_value = ([approval], 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks/approvals/pending")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["approver_id"] == str(APPROVER_ID)


# ═══════════════════════════════════════════════════════════════════════════════
# Approval: decide
# ═══════════════════════════════════════════════════════════════════════════════


async def test_decide_approval_approve(_override_db, _as_ceo):
    approval = _fake_approval(decision="approved")
    with patch(
        "app.domains.tasks.approvals.decide_approval", new_callable=AsyncMock
    ) as mock:
        mock.return_value = approval
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/approvals/{APPROVAL_ID}/decide",
                json={"decision": "approved"},
            )

    assert r.status_code == 200
    assert r.json()["decision"] == "approved"


async def test_decide_approval_reject(_override_db, _as_ceo):
    approval = _fake_approval(decision="rejected")
    with patch(
        "app.domains.tasks.approvals.decide_approval", new_callable=AsyncMock
    ) as mock:
        mock.return_value = approval
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/approvals/{APPROVAL_ID}/decide",
                json={"decision": "rejected"},
            )

    assert r.status_code == 200
    assert r.json()["decision"] == "rejected"


async def test_decide_approval_unauthorized(_override_db, _as_sales):
    with patch(
        "app.domains.tasks.approvals.decide_approval", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = HTTPException(status_code=403, detail="Only the designated approver can decide")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/approvals/{APPROVAL_ID}/decide",
                json={"decision": "approved"},
            )

    assert r.status_code == 403


async def test_decide_approval_already_decided(_override_db, _as_ceo):
    with patch(
        "app.domains.tasks.approvals.decide_approval", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = HTTPException(status_code=409, detail="Approval already decided")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/approvals/{APPROVAL_ID}/decide",
                json={"decision": "approved"},
            )

    assert r.status_code == 409


async def test_decide_approval_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/tasks/approvals/{APPROVAL_ID}/decide",
            json={"decision": "approved"},
        )
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Sprints: CRUD
# ═══════════════════════════════════════════════════════════════════════════════


async def test_list_sprints_empty(_override_db, _as_ceo):
    with patch(
        "app.domains.tasks.sprints.list_sprints", new_callable=AsyncMock
    ) as mock:
        mock.return_value = ([], 0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks/sprints")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_create_sprint_success(_override_db, _as_ceo):
    sprint = _fake_sprint()
    with patch(
        "app.domains.tasks.sprints.create_sprint", new_callable=AsyncMock
    ) as mock:
        mock.return_value = sprint
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/tasks/sprints",
                json={
                    "name": "Sprint 1",
                    "starts_at": NOW.isoformat(),
                    "ends_at": LATER.isoformat(),
                },
            )

    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Sprint 1"
    assert data["status"] == "planning"
    assert data["task_ids"] == []


async def test_create_sprint_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/tasks/sprints",
            json={
                "name": "Sprint 1",
                "starts_at": NOW.isoformat(),
                "ends_at": LATER.isoformat(),
            },
        )
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Department board
# ═══════════════════════════════════════════════════════════════════════════════


async def test_department_board_returns_tasks(_override_db, _as_ceo):
    from app.models.task import Task

    fake_task = MagicMock(spec=Task)
    fake_task.id = TASK_ID
    fake_task.company_id = COMPANY_ID
    fake_task.title = "Dept Task"
    fake_task.description = None
    fake_task.status = "open"
    fake_task.priority = "medium"
    fake_task.task_type = "general"
    fake_task.source = "manual"
    fake_task.departments = []
    fake_task.assignees = []
    fake_task.activity = []
    fake_task.comments = []
    fake_task.due_at = None
    fake_task.sla_hours = None
    fake_task.breached = False
    fake_task.task_metadata = {}
    fake_task.created_by = USER_ID
    fake_task.created_at = NOW
    fake_task.updated_at = NOW
    fake_task.deleted_at = None

    with patch(
        "app.domains.tasks.sprints.get_department_board", new_callable=AsyncMock
    ) as mock:
        mock.return_value = ([fake_task], 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks/board/sales")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Dept Task"


async def test_department_board_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/tasks/board/sales")
    assert r.status_code == 403
