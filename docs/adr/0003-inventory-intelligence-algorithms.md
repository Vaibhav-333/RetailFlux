# ADR-0003: Inventory Intelligence — Classical Algorithms over ML-Based Replenishment

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

RetailFlux v3's Inventory Intelligence module (Session 32–33) needed to answer the question: **what should a buyer reorder, when, and how much?**

The answer requires:
1. Estimating future demand per SKU.
2. Computing a reorder point that accounts for demand variability and supplier lead time.
3. Sizing the order quantity to balance ordering cost against carrying cost.
4. Surfacing an explainable rationale that a buyer can understand and challenge.

The decision was: **which algorithms to use for replenishment math?**

Fashion retail is a notoriously difficult forecasting domain:
- High SKU count (thousands of active SKUs per company)
- Short product lifecycles (seasonal items sell for 8–12 weeks)
- Sparse demand history for new launches (< 4 weeks of data)
- Exogenous demand drivers (promotions, weather, trend cycles) that are hard to capture in time-series models alone

---

## Decision

Use **classical inventory management formulas** (EOQ, safety stock, reorder point) as the v3 replenishment engine, with Prophet/Holt-Winters demand forecasts as inputs.

### Formula set

**Economic Order Quantity (EOQ):**
```
Q* = sqrt(2 × D × S / H)
```
Where D = annual demand units, S = ordering cost per PO (configurable per supplier), H = holding cost per unit per year (defaults to 25% of unit cost).

**Safety Stock:**
```
SS = Z × σ_demand × sqrt(lead_time_days)
```
Where Z = service-level z-score (default 1.65 for 95% fill rate), σ_demand = standard deviation of daily demand over last 28 days.

**Reorder Point:**
```
ROP = avg_daily_demand × lead_time_days + SS
```

**Days-on-Hand:**
```
DOH = current_stock / avg_daily_demand_last_28d
```

These run in `app/domains/inventory/reorder_service.py` and complete in < 1ms per SKU, making real-time reorder queue updates feasible even for 10K-SKU catalogs.

### Demand inputs
The daily demand estimate (`avg_daily_demand`) comes from existing Prophet/Holt-Winters forecasts (Session 11). Classical formulas consume the forecast output; they don't replace the forecasting layer.

---

## Alternatives Considered

### Prophet-native replenishment (forecast-first)
Use Prophet's 30-day forecast directly as the reorder signal: if `yhat` falls below safety stock within the next `lead_time_days`, trigger a reorder.

**Rejected** because:
- Prophet requires ≥ 2 seasons of data (ideally 2 years) for reliable confidence intervals. New SKUs with < 8 weeks of history produce wide, unreliable CIs.
- Prophet's runtime (1–3 seconds per SKU on CPU) makes batch recomputation for 10K SKUs prohibitive without a distributed compute layer.
- The forecast is already used as a *demand signal input*; combining forecast + replenishment logic in a single model creates a single point of failure.

### XGBoost regressor for reorder quantity
Train a gradient-boosted model on historical reorder data: features = (DOH, forecast, ABC class, season, lead time variance), target = "quantity that minimized stockouts + overstock in the following cycle."

**Rejected** because:
- Requires labeled training data ("what was the optimal order quantity?") that new customers don't have.
- Model interpretability is poor — buyers cannot understand why the model recommended 240 units instead of 180. In a procurement approval workflow, explainability is essential.
- No training data on day 1 means the model would default to a random or average recommendation, worse than classical math for cold-start scenarios.

### ML-based demand sensing (Facebook Kats, Amazon Chronos)
Use a modern transformer-based time-series foundation model (zero-shot, no training required) for demand forecasting, feeding its output into classical replenishment math.

**Deferred** (not rejected):
- Chronos and similar models are promising for cold-start demand sensing.
- Deferred to v3.x because they require additional dependencies (PyTorch, ~500MB) incompatible with the free-tier memory constraint (512MB on Render).
- The hybrid path is clean: replace `_holtwinters_forecast` in `forecast_service.py` with a foundation model call when infra allows.

---

## Consequences

**Positive:**
- **Explainable recommendations:** every reorder card in the UI shows the EOQ formula inputs. A buyer can disagree with the assumed ordering cost and the UI recalculates live.
- **Cold-start safe:** EOQ works with as little as 2 weeks of demand history. No warm-up period for new customers.
- **Zero training infrastructure:** no model training pipeline, no feature store, no drift monitoring.
- **Deterministic:** given the same inputs, the same output is always produced. Buyers can audit decisions after the fact.
- **Fast:** entire 10K-SKU reorder queue refreshes in < 2 seconds on a single CPU core.

**Negative / Trade-offs:**
- EOQ assumes constant demand and fixed ordering/holding costs. Fashion demand is neither constant nor predictable — the model is a simplification.
- Safety stock formula assumes normally distributed demand error. Actual fashion demand is often fat-tailed (viral SKUs spike suddenly). A non-parametric safety stock (historical quantile approach) would be more accurate.
- Optimal service level (Z) is hardcoded to 95%. Different SKU classes (A/B/C) warrant different service levels; this requires a configurability upgrade.

**Follow-ons:**
- v3.x: per-ABC-class service level (A=98%, B=95%, C=90%) with user configuration in Settings.
- v3.x: non-parametric safety stock using historical demand quantiles.
- v3.x: Chronos/foundation model integration for demand forecasting when memory constraints are relaxed.
- v3.x: supplier-specific ordering cost parameters exposed in the Supplier profile page.
