# ADR-0005: Scenario Planner Engine — Pure Python stdlib over numpy/pandas Vectorization

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

The Scenario Planner (Session 36) requires a simulation engine that takes a baseline forecast (revenue, COGS, margin, inventory) and a set of user-defined assumption deltas (demand shock %, price change %, ad spend multiplier, lead time change), then propagates them through the business model to produce a projected outcome.

The engine must:
1. Run interactively — the UI shows scenario vs. baseline deltas in real time as the user drags sliders.
2. Handle a 365-day horizon across ~5K active SKUs per company.
3. Produce deterministic, reproducible results (same inputs → same output every time).
4. Be auditable — the CEO must be able to understand *why* the scenario projected a specific margin.

The question was: **what runtime environment should power the simulation loop?**

---

## Decision

Implement the simulation engine in **pure Python stdlib math** (`math`, `statistics`, `itertools`) with `decimal.Decimal` for financial precision where required. No numpy, no pandas, no scipy in the simulation hot path.

### How the engine works

```python
# app/domains/scenarios/engine.py — simplified

def simulate(baseline: BaselineSnapshot, assumptions: Assumptions) -> ScenarioResult:
    demand_factor = 1.0 + assumptions.demand_shock_pct
    price_factor = 1.0 + assumptions.price_change_pct
    ad_multiplier = assumptions.ad_spend_multiplier

    projected_units = baseline.avg_daily_units * demand_factor * 365
    projected_revenue = projected_units * baseline.avg_unit_price * price_factor
    projected_cogs = projected_units * baseline.avg_unit_cost
    projected_gross_profit = projected_revenue - projected_cogs
    projected_gross_margin = projected_gross_profit / projected_revenue if projected_revenue else 0

    # Marketing impact: ad spend → revenue via ROAS
    incremental_ad_spend = (ad_multiplier - 1.0) * baseline.annual_ad_spend
    incremental_revenue_from_ads = incremental_ad_spend * baseline.roas

    # Inventory roll-forward
    projected_avg_inventory_value = (
        baseline.avg_inventory_units * baseline.avg_unit_cost
        * (1.0 / demand_factor)  # higher demand → lower average inventory
    )

    return ScenarioResult(
        projected_revenue=projected_revenue + incremental_revenue_from_ads,
        projected_gross_profit=projected_gross_profit,
        projected_gross_margin_pct=projected_gross_margin * 100,
        projected_avg_inventory_value=projected_avg_inventory_value,
        assumptions_applied=assumptions,
    )
```

The `BaselineSnapshot` is pulled from Redis (cached daily from the analytics services) — the simulation itself does no DB I/O. This makes the endpoint latency purely CPU-bound, and the CPU cost is trivial (< 1ms for a single scenario).

For multi-scenario sweeps (parameter sensitivity analysis, e.g., "show me outcomes for demand_shock in [-30%, -20%, ..., +30%]"), the Celery task `scenario_sweep` fans out via `asyncio.gather`.

---

## Alternatives Considered

### numpy vectorized simulation
Vectorize the 365-day roll-forward as numpy array operations: `revenue_per_day = units_per_day * price_per_day` where each is a length-365 float64 array. Day-level granularity enables weekday seasonality and promo event modeling.

**Rejected for v3** because:
- numpy is already in `requirements.txt` (via statsmodels/Prophet transitive dep), so it's not a new dependency — but vectorizing the simulation requires thinking in array semantics which adds cognitive overhead for maintainers.
- Day-level granularity is not needed for the v3 use case (executives want quarterly/annual projections, not daily).
- The marginal accuracy improvement of daily simulation does not justify the complexity uplift for initial launch.
- **Upgrade path is explicit**: the `engine.py` interface is stable; swapping the implementation to numpy is a one-file change when daily granularity becomes a requirement.

### pandas DataFrame simulation
Model the business as a pandas DataFrame (rows = SKUs, columns = metrics) and apply vectorized operations to project outcomes.

**Rejected** because:
- pandas DataFrames are high-memory (8 bytes per float64 cell × 5K SKUs × ~30 columns = 1.2MB per scenario). For 100 concurrent scenario simulations, this would exhaust Render's 512MB limit.
- pandas adds ~200ms startup time when first imported in a cold worker process — unacceptable for interactive slider-driven simulation.
- The simulation logic fits in < 80 lines of pure Python; wrapping it in DataFrame operations would be architecture astronautics.

### Celery-only heavy simulation (async, no interactive)
Run every scenario simulation as a Celery task (async, background). User submits assumptions, gets a job ID, polls for results.

**Rejected for the interactive use case** because:
- A Celery task round-trip (Redis enqueue → worker pick-up → execute → result TTL) adds 200–800ms latency on free-tier infrastructure. This makes slider-driven simulation unusable (each slider move triggers a new task, resulting in a queue backlog).
- For the multi-scenario sweep (`/scenarios/sweep`) this pattern IS used — it's the right tool for non-interactive, computationally intensive work.

### scipy.optimize for scenario optimization
Instead of simulating a user-specified scenario, use `scipy.optimize` to *find* the optimal assumption combination (maximize GP subject to budget constraints).

**Deferred** (not rejected): this is the right approach for "lever optimization" (ADR-0002 Predictive Profit Intelligence). The current engine is a forward simulator (given assumptions → outcome); the optimization layer sits on top and calls the simulator as its objective function.

---

## Consequences

**Positive:**
- **Interactive latency < 5ms** — pure Python arithmetic on cached baseline snapshots is computationally trivial. The SSE endpoint returns the first projected KPIs in < 50ms including network overhead.
- **Zero new dependencies** — `math`, `statistics`, `decimal` are Python stdlib. No additional package to install, pin, or audit for security vulnerabilities.
- **Fully testable** — pure functions with typed inputs/outputs. Golden-dataset tests confirm numerical correctness without mocking.
- **Deterministic** — no floating-point non-determinism from BLAS/LAPACK libraries (which can produce subtly different results across platforms).
- **Debuggable** — a CEO's controller can step through the simulation in a Python debugger and see exactly which formula produced each output.

**Negative / Trade-offs:**
- **Annual granularity only** — the current engine averages over 365 days and doesn't model day-level seasonality. A demand shock on December 15 looks the same as one on July 15.
- **Linear model** — the engine assumes linear relationships (demand × price → revenue). Real businesses have non-linear effects (price elasticity, saturation curves, cannibalization). These are captured in the Pricing module's elasticity model but not yet wired into the scenario engine.
- **No uncertainty quantification** — the engine returns a point estimate, not a distribution. A Monte Carlo layer (1K samples from the demand forecast's confidence interval) would give a P10/P50/P90 scenario — this is a v3.x upgrade.

**Follow-ons:**
- v3.x: add day-level granularity using the existing Prophet daily forecasts as the baseline demand array.
- v3.x: Monte Carlo uncertainty quantification (sample from forecast CI × price elasticity CI).
- v3.x: scipy.optimize lever optimization endpoint ("what assumption combination maximizes GP?").
- v3.x: numpy vectorized implementation behind the same `engine.py` interface, switched on by a feature flag, for benchmarking.
