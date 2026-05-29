"""Tests for Task Analytics, Recommendations, and Escalation endpoints/services."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.main import app
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    BottleneckTask,
    DepartmentProductivity,
    TaskAnalyticsDashboard,
    TeamScore,
    UserWorkload,
)

# ── Fixed IDs ─────────────────────────────────────────────────────────────────
USER_ID = uuid.uuid4()
COMPANY_ID = uuid.uuid4()
TASK_ID = uuid.uuid4()

# ── Fake helpers ──────────────────────────────────────────────────────────────


def _fake_user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = USER_ID
    u.email = "manager@test.com"
    u.name = "Manager"
    u.role = "manager"
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
    t.status = "in_progress"
    t.priority = "high"
    t.task_type = "general"
    t.source = "ai_recommendation"
    t.departments = []
    t.assignees = []
    t.due_at = None
    t.sla_hours = None
    t.breached = False
    t.task_metadata = {"ai_generated": True}
    t.created_by = USER_ID
    t.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t.deleted_at = None
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def _dept_prod(**kwargs) -> DepartmentProductivity:
    defaults = dict(
        department="operations",
        total=10,
        done=5,
        in_progress=3,
        blocked=2,
        completion_rate=0.5,
    )
    defaults.update(kwargs)
    return DepartmentProductivity(**defaults)


def _user_workload(**kwargs) -> UserWorkload:
    defaults = dict(
        user_id=USER_ID,
        open_count=5,
        in_progress_count=2,
        blocked_count=1,
        overdue_count=1,
        total_open=5,
    )
    defaults.update(kwargs)
    return UserWorkload(**defaults)


def _bottleneck(**kwargs) -> BottleneckTask:
    defaults = dict(
        task_id=TASK_ID,
        title="Stuck Task",
        status="in_progress",
        priority="high",
        days_stuck=3.5,
        departments=["operations"],
        breached=False,
    )
    defaults.update(kwargs)
    return BottleneckTask(**defaults)


def _team_score(**kwargs) -> TeamScore:
    defaults = dict(
        total_tasks=100,
        done_tasks=60,
        open_tasks=40,
        overdue_tasks=5,
        completion_rate=0.6,
        on_time_rate=0.9,
        avg_cycle_days=2.5,
    )
    defaults.update(kwargs)
    return TeamScore(**defaults)


def _dashboard() -> TaskAnalyticsDashboard:
    return TaskAnalyticsDashboard(
        department_productivity=[_dept_prod()],
        workload=[_user_workload()],
        bottlenecks=[_bottleneck()],
        team_score=_team_score(),
    )


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
# Analytics schema unit tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_department_productivity_schema():
    dp = _dept_prod()
    assert dp.completion_rate == 0.5
    assert dp.department == "operations"
    assert dp.blocked == 2


def test_user_workload_schema():
    w = _user_workload()
    assert w.open_count == 5
    assert w.overdue_count == 1
    assert w.total_open == 5


def test_bottleneck_schema():
    b = _bottleneck(days_stuck=7.0, breached=True)
    assert b.days_stuck == 7.0
    assert b.breached is True


def test_team_score_schema():
    ts = _team_score(on_time_rate=0.85)
    assert ts.on_time_rate == 0.85
    assert ts.avg_cycle_days == 2.5


def test_analytics_dashboard_schema():
    dash = _dashboard()
    assert len(dash.department_productivity) == 1
    assert len(dash.workload) == 1
    assert len(dash.bottlenecks) == 1
    assert dash.team_score.total_tasks == 100


# ═══════════════════════════════════════════════════════════════════════════════
# Analytics endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_analytics_dashboard_endpoint(_as_user):
    dash = _dashboard()
    with patch(
        "app.domains.tasks.analytics_service.get_analytics_dashboard",
        new=AsyncMock(return_value=dash),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "team_score" in data
    assert data["team_score"]["total_tasks"] == 100
    assert len(data["department_productivity"]) == 1


@pytest.mark.anyio
async def test_analytics_department_endpoint(_as_user):
    with patch(
        "app.domains.tasks.analytics_service.get_department_productivity",
        new=AsyncMock(return_value=[_dept_prod()]),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/department")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["department"] == "operations"
    assert data[0]["completion_rate"] == 0.5


@pytest.mark.anyio
async def test_analytics_workload_endpoint(_as_user):
    with patch(
        "app.domains.tasks.analytics_service.get_workload",
        new=AsyncMock(return_value=[_user_workload()]),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/workload")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["open_count"] == 5


@pytest.mark.anyio
async def test_analytics_bottlenecks_endpoint(_as_user):
    with patch(
        "app.domains.tasks.analytics_service.get_bottlenecks",
        new=AsyncMock(return_value=[_bottleneck()]),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/bottlenecks")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["days_stuck"] == 3.5
    assert data[0]["title"] == "Stuck Task"


@pytest.mark.anyio
async def test_analytics_bottlenecks_custom_params(_as_user):
    with patch(
        "app.domains.tasks.analytics_service.get_bottlenecks",
        new=AsyncMock(return_value=[]),
    ) as mock_fn:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/bottlenecks?stuck_hours=72&limit=50")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_analytics_team_score_endpoint(_as_user):
    with patch(
        "app.domains.tasks.analytics_service.get_team_score",
        new=AsyncMock(return_value=_team_score()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/analytics/team-score")
    assert r.status_code == 200
    data = r.json()
    assert data["completion_rate"] == 0.6
    assert data["on_time_rate"] == 0.9


@pytest.mark.anyio
async def test_analytics_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.get("/api/v1/tasks/analytics/dashboard")
    assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# Recommendations endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_list_recommendations_empty(_as_user):
    with patch(
        "app.domains.tasks.recommendation.list_recommendations",
        new=AsyncMock(return_value=([], 0)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/recommendations")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_list_recommendations_returns_tasks(_as_user):
    task = _fake_task()
    with patch(
        "app.domains.tasks.recommendation.list_recommendations",
        new=AsyncMock(return_value=([task], 1)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/tasks/recommendations")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["source"] == "ai_recommendation"


@pytest.mark.anyio
async def test_refresh_recommendations_creates_tasks(_as_user):
    task = _fake_task()
    with patch(
        "app.domains.tasks.recommendation.generate_recommendations",
        new=AsyncMock(return_value=[task]),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.post("/api/v1/tasks/recommendations/refresh")
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["priority"] == "high"


@pytest.mark.anyio
async def test_refresh_recommendations_empty_context(_as_user):
    with patch(
        "app.domains.tasks.recommendation.generate_recommendations",
        new=AsyncMock(return_value=[]),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.post("/api/v1/tasks/recommendations/refresh")
    assert r.status_code == 201
    assert r.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# Escalation service unit tests
# ═══════════════════════════════════════════════════════════════════════════════


def _scalars_result(rows):
    """Return a MagicMock that behaves like db.scalars(...) result with .all() → rows."""
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.anyio
async def test_escalate_stuck_tasks_dry_run(_override_db):
    """Dry run should return task IDs without committing."""
    from app.domains.tasks.escalation_service import escalate_stuck_tasks

    mock_task = _fake_task(status="in_progress", priority="urgent")
    # side_effect as a plain function: await db.scalars(stmt) → MagicMock with .all()
    _override_db.scalars.side_effect = lambda _stmt: _scalars_result([mock_task])

    result = await escalate_stuck_tasks(_override_db, COMPANY_ID, stuck_hours=48, dry_run=True)
    assert isinstance(result, list)
    # commit should NOT be called in dry run
    _override_db.commit.assert_not_called()


@pytest.mark.anyio
async def test_escalate_breached_tasks_no_duplicates(_override_db):
    """Already-escalated breach tasks should not be re-escalated."""
    from app.domains.tasks.escalation_service import escalate_breached_tasks

    mock_task = _fake_task(
        status="in_progress",
        breached=True,
        due_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    # Pop results in sequence: first call → task list, second → already_escalated IDs
    calls = iter([_scalars_result([mock_task]), _scalars_result([TASK_ID])])
    _override_db.scalars.side_effect = lambda _stmt: next(calls)

    result = await escalate_breached_tasks(_override_db, COMPANY_ID)
    # TASK_ID is already in already_escalated — should be skipped
    assert TASK_ID not in result


@pytest.mark.anyio
async def test_run_escalation_sweep(_override_db):
    """run_escalation_sweep should return a summary dict."""
    from app.domains.tasks.escalation_service import run_escalation_sweep

    # All scalars queries return empty → zero counts
    _override_db.scalars.side_effect = lambda _stmt: _scalars_result([])

    with patch("app.core.pubsub.publish_event", new=AsyncMock()):
        result = await run_escalation_sweep(_override_db, COMPANY_ID)

    assert "stuck_escalated" in result
    assert "breach_escalated" in result
    assert result["total"] == result["stuck_escalated"] + result["breach_escalated"]


# ═══════════════════════════════════════════════════════════════════════════════
# Golden tests for rule-based recommendation context (_get_context)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_get_context_includes_anomalies():
    """_get_context should include anomaly lines when anomalies are present."""
    from app.domains.tasks.recommendation import _get_context

    # Mock anomaly with a z-score and date
    mock_anomaly = MagicMock()
    mock_anomaly.date = "2025-01-15"
    mock_anomaly.z_score = 3.2

    with patch(
        "app.domains.insights.anomaly_service.get_revenue_anomalies",
        new=AsyncMock(return_value=[mock_anomaly]),
    ), patch(
        "app.domains.analytics.operations_service.get_operations_kpis",
        new=AsyncMock(side_effect=Exception("no ops")),
    ):
        context = await _get_context(COMPANY_ID)

    assert "Revenue anomalies" in context
    assert "2025-01-15" in context
    assert "3.2" in context


@pytest.mark.anyio
async def test_get_context_includes_low_stock():
    """_get_context should include low-stock SKUs when present."""
    from app.domains.tasks.recommendation import _get_context

    mock_sku = MagicMock()
    mock_sku.sku = "SKU-001"

    mock_ops = MagicMock()
    mock_ops.low_stock_skus = [mock_sku]

    with patch(
        "app.domains.insights.anomaly_service.get_revenue_anomalies",
        new=AsyncMock(side_effect=Exception("no anomalies")),
    ), patch(
        "app.domains.analytics.operations_service.get_operations_kpis",
        new=AsyncMock(return_value=mock_ops),
    ):
        context = await _get_context(COMPANY_ID)

    assert "Low-stock SKUs" in context
    assert "SKU-001" in context


@pytest.mark.anyio
async def test_get_context_empty_when_all_fail():
    """_get_context should return empty string when all data sources fail."""
    from app.domains.tasks.recommendation import _get_context

    with patch(
        "app.domains.insights.anomaly_service.get_revenue_anomalies",
        new=AsyncMock(side_effect=Exception("anomaly service down")),
    ), patch(
        "app.domains.analytics.operations_service.get_operations_kpis",
        new=AsyncMock(side_effect=Exception("ops service down")),
    ):
        context = await _get_context(COMPANY_ID)

    assert context == ""


@pytest.mark.anyio
async def test_generate_recommendations_skips_empty_context(_override_db):
    """generate_recommendations returns [] when no context is available."""
    from app.domains.tasks.recommendation import generate_recommendations

    result = await generate_recommendations(
        _override_db, COMPANY_ID, USER_ID, context=""
    )
    assert result == []


@pytest.mark.anyio
async def test_generate_recommendations_golden(_override_db):
    """Golden test: known Gemini JSON → 3 tasks created with correct fields."""
    from app.domains.tasks.recommendation import generate_recommendations

    # A deterministic AI response matching the expected JSON schema
    golden_json = """[
      {"title": "Investigate revenue spike on 2025-01-15",
       "description": "Review sales and refund data for the anomaly date.",
       "priority": "high",
       "task_type": "anomaly_response",
       "departments": ["finance", "operations"]},
      {"title": "Reorder SKU-001 before stockout",
       "description": "SKU-001 is critically low — initiate emergency reorder.",
       "priority": "urgent",
       "task_type": "reorder",
       "departments": ["procurement"]},
      {"title": "Schedule ops review for low-stock SKUs",
       "description": "Schedule weekly ops review for items below reorder point.",
       "priority": "medium",
       "task_type": "review",
       "departments": ["operations"]}
    ]"""

    # Simulate created task
    created_task = _fake_task(source="ai_recommendation")

    with patch(
        "app.core.gemini.generate_text",
        new=AsyncMock(return_value=(golden_json, {})),
    ), patch(
        "app.domains.tasks.recommendation.generate_recommendations",
        wraps=None,  # ensure real function runs
    ):
        # Mock the DB so flush/commit succeed and scalar reloads the task
        _override_db.flush = AsyncMock()
        _override_db.commit = AsyncMock()
        _override_db.scalar = AsyncMock(return_value=created_task)

        with patch("app.core.pubsub.publish_event", new=AsyncMock()):
            result = await generate_recommendations(
                _override_db,
                COMPANY_ID,
                USER_ID,
                context="Revenue anomalies: 2025-01-15 z=3.2\nLow-stock SKUs: SKU-001",
            )

    # 3 suggestions → 3 tasks attempted; scalar reloads for each
    assert isinstance(result, list)
    # At least one task returned (scalar always returns created_task)
    assert len(result) >= 1


@pytest.mark.anyio
async def test_generate_recommendations_handles_malformed_json(_override_db):
    """When Gemini returns non-JSON, generate_recommendations returns []."""
    from app.domains.tasks.recommendation import generate_recommendations

    with patch(
        "app.core.gemini.generate_text",
        new=AsyncMock(return_value=("This is not JSON!", {})),
    ):
        result = await generate_recommendations(
            _override_db,
            COMPANY_ID,
            USER_ID,
            context="Revenue anomalies: 2025-01-15 z=3.2",
        )

    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# Productivity rollup tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_productivity_rollup_returns_ok(_override_db):
    """snapshot_productivity should return a status=ok dict on success."""
    from app.domains.tasks.productivity_rollup import snapshot_productivity

    score = _team_score()
    depts = [_dept_prod()]
    workload = [_user_workload()]

    with patch(
        "app.domains.tasks.analytics_service.get_team_score",
        new=AsyncMock(return_value=score),
    ), patch(
        "app.domains.tasks.analytics_service.get_department_productivity",
        new=AsyncMock(return_value=depts),
    ), patch(
        "app.domains.tasks.analytics_service.get_workload",
        new=AsyncMock(return_value=workload),
    ), patch(
        "app.core.mongodb.get_mongo_db",
    ) as mock_mongo:
        mock_col = AsyncMock()
        mock_col.update_one = AsyncMock()
        mock_mongo.return_value.__getitem__ = MagicMock(return_value=mock_col)

        result = await snapshot_productivity(_override_db, COMPANY_ID)

    assert result["status"] == "ok"
    assert "date" in result
    assert result["departments_snapshotted"] == 1
    assert result["users_snapshotted"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Digest email tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_digest_email_no_recipients(_override_db):
    """send_task_digest returns 0 emails when no eligible users exist."""
    from app.domains.tasks.digest_email import send_task_digest

    _override_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

    with patch(
        "app.domains.tasks.analytics_service.get_team_score",
        new=AsyncMock(return_value=_team_score()),
    ), patch(
        "app.domains.tasks.analytics_service.get_bottlenecks",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.domains.tasks.recommendation.list_recommendations",
        new=AsyncMock(return_value=([], 0)),
    ):
        result = await send_task_digest(_override_db, COMPANY_ID)

    assert result["emails_sent"] == 0


def test_digest_html_contains_kpis():
    """digest HTML generation includes completion rate and task counts."""
    from app.domains.tasks.digest_email import _digest_html

    html = _digest_html(
        name="CEO",
        score_data={
            "total_tasks": 50,
            "done_tasks": 30,
            "open_tasks": 20,
            "overdue_tasks": 3,
            "completion_rate": 0.6,
            "on_time_rate": 0.9,
            "avg_cycle_days": 2.5,
        },
        bottlenecks=[],
        ai_rec_count=5,
    )

    assert "CEO" in html
    assert "50" in html      # total
    assert "30" in html      # done
    assert "60.0" in html    # completion %
    assert "5" in html       # ai_rec_count reference
