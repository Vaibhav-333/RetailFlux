# RetailFlux Load Tests

Performance load tests using [Locust](https://locust.io). Tests the full API surface
against the SLA targets defined in ADR-0006.

---

## SLA Targets

| Endpoint category        | p95 target |
|--------------------------|-----------|
| Analytics endpoints      | < 600 ms  |
| Inventory overview       | < 600 ms  |
| Scenario simulation      | < 1,000 ms |
| Copilot first-token      | < 1,500 ms (tested manually) |
| WebSocket reconnect rate | < 2 %      |

---

## Prerequisites

```bash
# From the apps/api directory, activate the venv first
.venv/Scripts/activate        # Windows
source .venv/bin/activate     # Linux / macOS

pip install locust             # or: it's in requirements.txt
```

The API server must be running before starting the load test:

```bash
# Terminal 1 — start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — (optional) start Celery worker for background tasks
celery -A app.workers.celery_app worker --loglevel=info
```

Demo data must be seeded:

```bash
python scripts/seed_demo.py
```

---

## Running the Load Test

### Interactive (Locust Web UI)

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

Open http://localhost:8089, set:
- Number of users: **100**
- Spawn rate: **10** users/second
- Run time: **10 minutes**

### Headless (CI / scripted)

```bash
locust -f tests/load/locustfile.py \
       --headless \
       -u 100 \
       -r 10 \
       --run-time 10m \
       --host http://localhost:8000
```

### With HTML report + CSV stats

```bash
mkdir -p tests/load/results

locust -f tests/load/locustfile.py \
       --headless \
       -u 100 \
       -r 10 \
       --run-time 10m \
       --host http://localhost:8000 \
       --html tests/load/results/report.html \
       --csv  tests/load/results/stats
```

Reports are written to `tests/load/results/`:
- `report.html` — full interactive HTML report
- `stats.csv` — per-endpoint request count, p50/p95/p99, failure rate
- `stats_history.csv` — time-series of RPS and latency
- `failures.csv` — details on every failed request

---

## User Types

| Class | Weight | Represents |
|-------|--------|------------|
| `RetailFluxUser` | 70% | CEO: dashboards + inventory + scenarios + copilot |
| `RetailFluxReadOnlyUser` | 30% | Department member: analytics + tasks read-only |

Both classes authenticate with the demo credentials (`ceo@retailflux.demo` / `demo1234`). In a multi-tenant load test, create separate user credentials per simulated company.

---

## Interpreting Results

### Key metrics to watch

**Failure rate** — should be 0% for all authenticated endpoints. Any failures indicate:
- 401/403: token expiry during the 10-minute run (the locust user doesn't implement token refresh)
- 422: validation error in request payload (check `failures.csv`)
- 500: server error (check API logs)
- Connection error: server overwhelmed or rate limited

**p95 latency** — compare against SLA targets table above. Breaches are logged to console in real time by the `on_request` hook in `locustfile.py`.

**RPS (requests per second)** — at 100 concurrent users with `wait_time between(1, 3)`, expect ~33–50 RPS. If RPS is significantly lower, the server is the bottleneck.

### Expected behaviour with Redis cache

The first request to each analytics endpoint (cache miss) will be slower than subsequent requests (cache hit). The Locust ramp-up period (100 users over 10 minutes) naturally warms the cache before peak load.

To test **cold cache performance**, flush Redis between runs:

```bash
redis-cli FLUSHDB
# or for Upstash: use the Upstash console "Flush" button
```

### Redis cache hit rate

After the run, query Redis key stats:

```bash
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses
```

Target: > 75% hit rate during steady state (per plan §8).

---

## Copilot Load Test (separate)

The SSE streaming endpoint (`POST /copilot/stream`) is not included in the main locust file because it holds connections open for the duration of the stream (typically 3–8 seconds). Testing 100 concurrent SSE connections requires a different approach.

Manual copilot load test (run from a separate terminal):

```bash
# Install httpie for clean SSE output
pip install httpie

# Get a token first
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ceo@retailflux.demo","password":"demo1234"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Send a copilot message and measure time to first token
time curl -s -N \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/v1/copilot/stream \
  -d '{"message":"What was our best-selling SKU last month?"}' \
  | head -c 200
```

Target: first `data: {"type":"token"` event within 1,500ms.

---

## WebSocket Reconnect Test

The `useRealtimeAlerts` hook in the frontend implements exponential backoff reconnection. To verify the < 2% reconnect rate target:

1. Start the load test
2. Mid-run, restart the API server (`Ctrl+C` + `uvicorn ...`)
3. Observe the browser WebSocket reconnect in the Network tab
4. A reconnect within 5 seconds with no visible data loss counts as a success

---

## Adding Tests

To add a new endpoint to the load test:

```python
@task(2)  # weight relative to other tasks
def my_new_endpoint(self) -> None:
    self.client.get(
        "/api/v1/my-endpoint",
        headers=self.headers,
        name="GET /my-endpoint",  # shown in Locust UI
    )
```

Add the endpoint to `_SLA_THRESHOLDS_MS` in `locustfile.py` to get SLA breach logging.
