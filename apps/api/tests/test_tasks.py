"""Task system tests — workflow unit tests + endpoint integration tests (DB mocked)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user  # used via dependency_overrides
from app.domains.tasks.workflow import can_transition, valid_statuses
from app.main import app
from app.models.task import Task, TaskActivity, TaskComment
from app.models.user import User

# ── Fixed IDs ─────────────────────────────────────────────────────────────────
TASK_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
COMPANY_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()

# ── Fake helpers ──────────────────────────────────────────────────────────────


def _fake_user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = USER_ID
    u.email = "ceo@test.com"
    u.name = "CEO"
    u.role = "ceo"
    u.company_id = COMPANY_ID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.onboarding_step = 0
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


def _fake_task(**kwargs) -> MagicMock:
    t = MagicMock(spec=Task)
    t.id = TASK_ID
    t.company_id = COMPANY_ID
    t.title = "Test Task"
    t.description = None
    t.status = "open"
    t.priority = "medium"
    t.task_type = "general"
    t.source = "manual"
    t.departments = []
    t.assignees = []
    t.activity = []
    t.comments = []
    t.due_at = None
    t.sla_hours = None
    t.breached = False
    t.task_metadata = {}
    t.created_by = USER_ID
    t.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t.deleted_at = None
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def _fake_comment() -> MagicMock:
    c = MagicMock(spec=TaskComment)
    c.id = uuid.uuid4()
    c.task_id = TASK_ID
    c.user_id = USER_ID
    c.body = "A comment"
    c.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    c.edited_at = None
    return c


def _fake_activity() -> MagicMock:
    a = MagicMock(spec=TaskActivity)
    a.id = uuid.uuid4()
    a.task_id = TASK_ID
    a.user_id = USER_ID
    a.kind = "created"
    a.old_value = None
    a.new_value = "Test Task"
    a.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return a


# ── DB fixture ────────────────────────────────────────────────────────────────


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
def _as_user():
    user = _fake_user()
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow unit tests (pure Python — no HTTP)
# ═══════════════════════════════════════════════════════════════════════════════


def test_workflow_open_to_in_progress():
    assert can_transition("open", "in_progress") is True


def test_workflow_open_to_cancelled():
    assert can_transition("open", "cancelled") is True


def test_workflow_open_cannot_jump_to_done():
    assert can_transition("open", "done") is False


def test_workflow_in_progress_to_blocked():
    assert can_transition("in_progress", "blocked") is True


def test_workflow_done_is_terminal():
    assert can_transition("done", "open") is False
    assert can_transition("done", "in_progress") is False
    assert can_transition("done", "cancelled") is False


def test_workflow_cancelled_is_terminal():
    for target in ("open", "in_progress", "blocked", "in_review", "done"):
        assert can_transition("cancelled", target) is False


def test_valid_statuses_complete():
    statuses = valid_statuses()
    expected = {"open", "in_progress", "blocked", "in_review", "done", "cancelled"}
    assert set(statuses) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# List tasks
# ═══════════════════════════════════════════════════════════════════════════════


async def test_list_tasks_empty(_override_db, _as_user):
    with patch("app.domains.tasks.service.list_tasks", new_callable=AsyncMock) as mock:
        mock.return_value = ([], 0)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_tasks_returns_items(_override_db, _as_user):
    task = _fake_task()
    with patch("app.domains.tasks.service.list_tasks", new_callable=AsyncMock) as mock:
        mock.return_value = ([task], 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tasks")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Task"
    assert data["items"][0]["status"] == "open"


async def test_list_tasks_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/tasks")
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Create task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_create_task_success(_override_db, _as_user):
    task = _fake_task()
    with patch("app.domains.tasks.service.create_task", new_callable=AsyncMock) as mock:
        mock.return_value = task
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/tasks", json={"title": "Test Task"})

    assert r.status_code == 201
    assert r.json()["title"] == "Test Task"


async def test_create_task_missing_title(_override_db, _as_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/tasks", json={"priority": "high"})
    assert r.status_code == 422


async def test_create_task_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/tasks", json={"title": "Test"})
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Get task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_get_task_success(_override_db, _as_user):
    task = _fake_task()
    with patch("app.domains.tasks.service.get_task", new_callable=AsyncMock) as mock:
        mock.return_value = task
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/tasks/{TASK_ID}")

    assert r.status_code == 200
    assert r.json()["id"] == str(TASK_ID)


async def test_get_task_not_found(_override_db, _as_user):
    from fastapi import HTTPException

    with patch("app.domains.tasks.service.get_task", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(status_code=404, detail="Task not found")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/tasks/{uuid.uuid4()}")

    assert r.status_code == 404


async def test_get_task_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/tasks/{TASK_ID}")
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Update task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_update_task_success(_override_db, _as_user):
    task = _fake_task(title="Updated Title")
    with patch("app.domains.tasks.service.update_task", new_callable=AsyncMock) as mock:
        mock.return_value = task
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(f"/api/v1/tasks/{TASK_ID}", json={"title": "Updated Title"})

    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"


async def test_update_task_not_found(_override_db, _as_user):
    from fastapi import HTTPException

    with patch("app.domains.tasks.service.update_task", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(status_code=404, detail="Task not found")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(f"/api/v1/tasks/{uuid.uuid4()}", json={"title": "X"})

    assert r.status_code == 404


async def test_update_task_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"/api/v1/tasks/{TASK_ID}", json={"title": "X"})
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Delete task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_delete_task_success(_override_db, _as_user):
    with patch("app.domains.tasks.service.delete_task", new_callable=AsyncMock) as mock:
        mock.return_value = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v1/tasks/{TASK_ID}")

    assert r.status_code == 204
    mock.assert_awaited_once()


async def test_delete_task_not_found(_override_db, _as_user):
    from fastapi import HTTPException

    with patch("app.domains.tasks.service.delete_task", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(status_code=404, detail="Task not found")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v1/tasks/{uuid.uuid4()}")

    assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Transition task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_transition_task_success(_override_db, _as_user):
    task = _fake_task(status="in_progress")
    with patch("app.domains.tasks.service.transition_task", new_callable=AsyncMock) as mock:
        mock.return_value = task
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{TASK_ID}/transition",
                json={"to_status": "in_progress"},
            )

    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


async def test_transition_task_invalid(_override_db, _as_user):
    from fastapi import HTTPException

    with patch("app.domains.tasks.service.transition_task", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(
            status_code=422,
            detail="Cannot transition from 'done' to 'open'",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{TASK_ID}/transition",
                json={"to_status": "open"},
            )

    assert r.status_code == 422


async def test_transition_task_not_found(_override_db, _as_user):
    from fastapi import HTTPException

    with patch("app.domains.tasks.service.transition_task", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(status_code=404, detail="Task not found")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{uuid.uuid4()}/transition",
                json={"to_status": "in_progress"},
            )

    assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Assign task
# ═══════════════════════════════════════════════════════════════════════════════


async def test_assign_task_success(_override_db, _as_user):
    task = _fake_task()
    with patch("app.domains.tasks.service.assign_task", new_callable=AsyncMock) as mock:
        mock.return_value = task
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{TASK_ID}/assignees",
                json={"user_id": str(OTHER_USER_ID), "role_in_task": "collaborator"},
            )

    assert r.status_code == 200
    mock.assert_awaited_once()


async def test_assign_task_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/tasks/{TASK_ID}/assignees",
            json={"user_id": str(OTHER_USER_ID)},
        )
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Add comment
# ═══════════════════════════════════════════════════════════════════════════════


async def test_add_comment_success(_override_db, _as_user):
    comment = _fake_comment()
    with patch("app.domains.tasks.service.add_comment", new_callable=AsyncMock) as mock:
        mock.return_value = comment
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/api/v1/tasks/{TASK_ID}/comments",
                json={"body": "A comment"},
            )

    assert r.status_code == 201
    assert r.json()["body"] == "A comment"


async def test_add_comment_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/v1/tasks/{TASK_ID}/comments", json={"body": "test"})
    assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Get activity
# ═══════════════════════════════════════════════════════════════════════════════


async def test_get_activity_success(_override_db, _as_user):
    activity = _fake_activity()
    with patch("app.domains.tasks.service.get_activity", new_callable=AsyncMock) as mock:
        mock.return_value = ([activity], 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/tasks/{TASK_ID}/activity")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["kind"] == "created"


async def test_get_activity_auth_required(_override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/tasks/{TASK_ID}/activity")
    assert r.status_code == 403
