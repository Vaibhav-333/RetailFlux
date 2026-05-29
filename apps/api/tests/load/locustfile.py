"""Locust load test for RetailFlux API.

Simulates a realistic mix of CEO-level traffic across analytics, inventory,
tasks, and scenarios endpoints.

Target SLAs (see docs/adr/0006-free-tier-production-stack.md):
  - Analytics endpoints:   p95 < 600 ms
  - Copilot first-token:   < 1.5 s  (tested separately via /copilot/usage)
  - WebSocket reconnect:   < 2 %
  - 100 concurrent users, 10-minute ramp

Run:
  locust -f tests/load/locustfile.py \\
         --headless -u 100 -r 10 --run-time 10m \\
         --host http://localhost:8000

Or with HTML report:
  locust -f tests/load/locustfile.py \\
         --headless -u 100 -r 10 --run-time 10m \\
         --host http://localhost:8000 \\
         --html tests/load/results/report.html \\
         --csv  tests/load/results/stats
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from locust import HttpUser, between, events, task
from locust.exception import RescheduleTask

# ---------------------------------------------------------------------------
# Demo credentials (must match scripts/seed_demo.py)
# ---------------------------------------------------------------------------

_DEMO_EMAIL = "ceo@retailflux.demo"
_DEMO_PASSWORD = "demo1234"

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _date_range(days_back: int = 90) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "date_from": (now - timedelta(days=days_back)).strftime("%Y-%m-%d"),
        "date_to": now.strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------


class RetailFluxUser(HttpUser):
    """Simulates a logged-in CEO browsing dashboards and using the copilot."""

    wait_time = between(1, 3)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_start(self) -> None:
        """Log in and store the bearer token."""
        with self.client.post(
            "/api/v1/auth/login",
            json={"email": _DEMO_EMAIL, "password": _DEMO_PASSWORD},
            catch_response=True,
            name="POST /auth/login",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Login failed: {resp.status_code} {resp.text[:200]}")
                raise RescheduleTask()
            data = resp.json()
            token = data.get("access_token")
            if not token:
                resp.failure("No access_token in login response")
                raise RescheduleTask()
            self.token = token
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.company_id = data.get("user", {}).get("company_id", "")

    # ------------------------------------------------------------------
    # Analytics — high frequency (weight 3-4 each)
    # ------------------------------------------------------------------

    @task(4)
    def dashboard_summary(self) -> None:
        self.client.get(
            "/api/v1/analytics/summary",
            headers=self.headers,
            name="GET /analytics/summary",
        )

    @task(3)
    def sales_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/sales",
            headers=self.headers,
            params=_date_range(90),
            name="GET /analytics/sales",
        )

    @task(2)
    def marketing_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/marketing",
            headers=self.headers,
            params=_date_range(90),
            name="GET /analytics/marketing",
        )

    @task(2)
    def operations_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/operations",
            headers=self.headers,
            params=_date_range(90),
            name="GET /analytics/operations",
        )

    @task(2)
    def finance_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/finance",
            headers=self.headers,
            params=_date_range(90),
            name="GET /analytics/finance",
        )

    @task(1)
    def procurement_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/procurement",
            headers=self.headers,
            params=_date_range(90),
            name="GET /analytics/procurement",
        )

    # ------------------------------------------------------------------
    # Inventory — medium frequency (weight 2-3)
    # ------------------------------------------------------------------

    @task(3)
    def inventory_overview(self) -> None:
        self.client.get(
            "/api/v1/inventory/overview",
            headers=self.headers,
            name="GET /inventory/overview",
        )

    @task(2)
    def reorder_queue(self) -> None:
        self.client.get(
            "/api/v1/inventory/reorder-queue",
            headers=self.headers,
            name="GET /inventory/reorder-queue",
        )

    @task(1)
    def inventory_abc(self) -> None:
        self.client.get(
            "/api/v1/inventory/abc-xyz",
            headers=self.headers,
            name="GET /inventory/abc-xyz",
        )

    @task(1)
    def inventory_aging(self) -> None:
        self.client.get(
            "/api/v1/inventory/aging",
            headers=self.headers,
            name="GET /inventory/aging",
        )

    # ------------------------------------------------------------------
    # Tasks — medium frequency (weight 2)
    # ------------------------------------------------------------------

    @task(2)
    def list_tasks(self) -> None:
        self.client.get(
            "/api/v1/tasks",
            headers=self.headers,
            params={"page": 1, "page_size": 20, "status": "open"},
            name="GET /tasks (list)",
        )

    @task(1)
    def task_analytics_dept(self) -> None:
        self.client.get(
            "/api/v1/tasks/analytics/department",
            headers=self.headers,
            name="GET /tasks/analytics/department",
        )

    # ------------------------------------------------------------------
    # Scenarios — lower frequency (weight 1)
    # ------------------------------------------------------------------

    @task(1)
    def quick_simulate(self) -> None:
        """Run a lightweight scenario simulation."""
        payload = {
            "name": f"locust-test-{uuid.uuid4().hex[:8]}",
            "assumptions": {
                "demand_shock_pct": round(random.uniform(-0.3, 0.3), 2),
                "price_change_pct": round(random.uniform(-0.1, 0.1), 2),
                "ad_spend_multiplier": round(random.uniform(0.5, 2.0), 2),
                "lead_time_change_days": random.randint(-5, 10),
            },
        }
        self.client.post(
            "/api/v1/scenarios/simulate",
            headers=self.headers,
            json=payload,
            name="POST /scenarios/simulate",
        )

    @task(1)
    def list_scenarios(self) -> None:
        self.client.get(
            "/api/v1/scenarios",
            headers=self.headers,
            name="GET /scenarios (list)",
        )

    # ------------------------------------------------------------------
    # Copilot usage check — lowest frequency (weight 1)
    # ------------------------------------------------------------------

    @task(1)
    def copilot_usage(self) -> None:
        """Check token usage — lightweight proxy for copilot health."""
        self.client.get(
            "/api/v1/copilot/usage",
            headers=self.headers,
            name="GET /copilot/usage",
        )

    # ------------------------------------------------------------------
    # Notifications — low frequency (weight 1)
    # ------------------------------------------------------------------

    @task(1)
    def list_notifications(self) -> None:
        self.client.get(
            "/api/v1/notifications",
            headers=self.headers,
            params={"page": 1, "size": 20},
            name="GET /notifications",
        )

    # ------------------------------------------------------------------
    # Observability — very low frequency (weight 1, CEO only)
    # ------------------------------------------------------------------

    @task(1)
    def observability_dashboard(self) -> None:
        self.client.get(
            "/api/v1/observability/dashboard",
            headers=self.headers,
            name="GET /observability/dashboard",
        )


class RetailFluxReadOnlyUser(HttpUser):
    """Simulates a department member (Sales/Marketing) with read-heavy access.

    Uses the same demo CEO credentials for simplicity in the load test.
    In a real multi-tenant test, each user class would have its own credentials.
    """

    wait_time = between(2, 5)

    def on_start(self) -> None:
        with self.client.post(
            "/api/v1/auth/login",
            json={"email": _DEMO_EMAIL, "password": _DEMO_PASSWORD},
            catch_response=True,
            name="POST /auth/login",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Login failed: {resp.status_code}")
                raise RescheduleTask()
            self.token = resp.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def sales_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/sales",
            headers=self.headers,
            params=_date_range(30),
            name="GET /analytics/sales (read-only user)",
        )

    @task(3)
    def marketing_kpis(self) -> None:
        self.client.get(
            "/api/v1/analytics/marketing",
            headers=self.headers,
            params=_date_range(30),
            name="GET /analytics/marketing (read-only user)",
        )

    @task(2)
    def list_tasks(self) -> None:
        self.client.get(
            "/api/v1/tasks",
            headers=self.headers,
            params={"page": 1, "page_size": 20},
            name="GET /tasks (read-only user)",
        )

    @task(1)
    def uploads_list(self) -> None:
        self.client.get(
            "/api/v1/uploads",
            headers=self.headers,
            name="GET /uploads (read-only user)",
        )


# ---------------------------------------------------------------------------
# Custom event hooks — log SLA breaches to the console
# ---------------------------------------------------------------------------

_SLA_THRESHOLDS_MS = {
    "GET /analytics/summary": 600,
    "GET /analytics/sales": 600,
    "GET /analytics/marketing": 600,
    "GET /analytics/operations": 600,
    "GET /analytics/finance": 600,
    "GET /analytics/procurement": 600,
    "GET /inventory/overview": 600,
    "GET /inventory/reorder-queue": 600,
    "POST /scenarios/simulate": 1000,
    "GET /copilot/usage": 500,
}


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response,
    context,
    exception,
    **kwargs,
) -> None:
    """Log SLA breaches for monitored endpoints."""
    threshold = _SLA_THRESHOLDS_MS.get(name)
    if threshold and response_time > threshold:
        print(
            f"[SLA BREACH] {request_type} {name} "
            f"took {response_time:.0f}ms (threshold {threshold}ms)"
        )
