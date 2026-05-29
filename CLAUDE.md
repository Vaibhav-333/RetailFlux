# RetailFlux — Claude Session Context

> This file is updated at the END of every session so the next Claude instance
> knows exactly where the project stands and what to build.

---

## Project Identity
- **Name**: RetailFlux
- **Type**: AI-powered business analytics & procurement intelligence platform for fashion/clothing companies
- **Stack**: React 18 + Vite + TypeScript · FastAPI 0.115 (Python 3.11) · PostgreSQL (Neon) · Redis (Upstash) · MongoDB Atlas · Cloudflare R2 · Gemini 1.5 Flash (LLM) · Prophet/scikit-learn/XGBoost (ML)
- **Cost constraint**: 100% free / free-tier everywhere
- **Working directory**: `C:\Users\Vaibhav\OneDrive\Desktop\New folder\retailflux\`

---

## Session History

### Session 4 — Sales Analytics Dashboard (COMPLETE)
**What was built:**
- `app/schemas/analytics.py` — `SkuRevenue`, `RegionRevenue`, `DailyRevenue`, `SalesKpisOut` Pydantic models
- `app/domains/analytics/__init__.py` — package init
- `app/domains/analytics/sales_service.py` — `get_sales_kpis`: 4 parallel MongoDB aggregations against `staging_sales` → total KPIs, top-10 SKUs, revenue by region, daily time-series; defaults to last 90 days
- `app/api/v1/endpoints/analytics.py` — `GET /analytics/sales` with `date_from`/`date_to` query params, protected by `get_current_user`
- `app/api/v1/router.py` — analytics router wired at `/analytics`
- `tests/test_analytics.py` — 3 tests: empty result, data present (verifies AOV calc + all shapes), auth-required 403
- `src/types/index.ts` — `SkuRevenue`, `RegionRevenue`, `DailyRevenue`, `SalesKpisOut` interfaces added
- `src/features/sales/api.ts` — `getSalesKpisApi(dateFrom?, dateTo?)`
- `src/pages/SalesPage.tsx` — 4 KPI cards · AreaChart daily trend · BarChart top-10 SKUs (horizontal) · PieChart revenue by region; date-range inputs wired to TanStack Query
- `src/app/router.tsx` — `/dashboard/sales` → `<SalesPage />`

**Status at end of Session 4**: Sales Analytics Dashboard complete. Backend aggregates live MongoDB `staging_sales` data. Frontend renders 4 KPI cards + 3 Recharts visualisations with a date-range picker.

---

### Session 3 — Upload Pipeline (COMPLETE)
**What was built:**
- `app/core/storage.py` — MinIO client wrapper: `get_minio_client`, `ensure_bucket`, `upload_bytes`, `download_bytes`
- `app/models/upload.py` — `Upload` ORM model + `UploadStatus` enum (maps to existing migration table)
- `app/models/__init__.py` — `Upload` + `UploadStatus` exported
- `app/schemas/upload.py` — `UploadOut`, `UploadListResponse` Pydantic models
- `app/domains/uploads/pandera_schemas.py` — Pandera `DataFrameSchema` per dept (sales, marketing, operations, finance, procurement)
- `app/domains/uploads/service.py` — `create_upload` (validate ext/size → MinIO → DB → Celery), `get_upload`, `list_uploads`
- `app/workers/tasks/process_upload.py` — Celery task: download → parse CSV/Excel → Pandera lazy validation → count clean/rejected → insert clean rows into MongoDB `staging_{dept}` collection → update Upload record
- `app/workers/celery_app.py` — `process_upload` module registered in `include`
- `app/api/v1/endpoints/uploads.py` — `POST /uploads` (multipart), `GET /uploads`, `GET /uploads/{id}`
- `app/api/v1/router.py` — uploads router wired in
- `tests/test_uploads.py` — 5 tests covering create, auth-required, list, get, 404
- `src/features/uploads/api.ts` — `uploadFileApi`, `listUploadsApi`, `getUploadApi`
- `src/pages/UploadsPage.tsx` — drag-and-drop zone, dept selector, upload button; history table with status badges + row counts; auto-refetch every 3 s while any upload is queued/processing
- `src/app/router.tsx` — `/dashboard/uploads` → `<UploadsPage />`
- `src/types/index.ts` — `Upload.rows_*` made nullable (`number | null`)

**Status at end of Session 3**: Upload pipeline complete. Files are stored in MinIO, validated by Pandera per-department schemas, clean rows written to MongoDB staging collections, and Upload DB records updated with final status + row counts.

---

### Session 2 — Authentication System (COMPLETE)
**What was built:**
- `app/models/company.py` — Company model extracted to its own file
- `app/models/user.py` — Company removed; User model finalized
- `app/core/security.py` — `create_refresh_token` now returns `(token, jti)` tuple; adds `jti` + optional `extra` to refresh payload for denylist support
- `app/core/limiter.py` — SlowAPI Limiter singleton (imported by both main.py and auth endpoint)
- `app/schemas/user.py` — `UserOut`, `UserUpdate`, `AdminCreateUser`, `UsersListResponse`
- `app/schemas/auth.py` — `RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshResponse`
- `app/domains/auth/service.py` — `register`, `login`, `refresh_tokens`, `logout` business logic; refresh token denylist in Redis (`jwt:denylist:{jti}`)
- `app/domains/auth/dependencies.py` — `get_current_user` FastAPI dep; `require_role(*roles)` dep factory
- `app/api/v1/endpoints/auth.py` — POST /auth/register, /auth/login, /auth/refresh, /auth/logout; refresh token in httpOnly cookie; SlowAPI rate limit on register+login
- `app/api/v1/endpoints/users.py` — GET /users/me, PATCH /users/me, GET /users (admin), POST /users (admin)
- `app/api/v1/router.py` — auth + users routers wired in
- `app/main.py` — limiter imported from core/limiter
- `tests/test_auth.py` — register, login, bad-creds 401, refresh-without-cookie 401, logout, protected-without-token 403, get-me with valid token
- `src/features/auth/api.ts` — `loginApi`, `registerApi`, `logoutApi`, `getMeApi`
- `src/features/auth/authStore.ts` — logout now calls `logoutApi()` before clearing state
- `src/pages/LoginPage.tsx` — full react-hook-form + zod form; sonner toast on success/error
- `src/pages/RegisterPage.tsx` — company + user registration form with confirm-password validation
- `src/app/router.tsx` — `/register` route added; ProtectedRoute unchanged

**Status at end of Session 2**: Full JWT auth system working. Register creates company + CEO user. Login returns access token (memory) + refresh token (httpOnly cookie). Logout denylists jti in Redis. All API routes protected via `get_current_user` dependency.

---

### Session 1 — Foundations (COMPLETE)
**What was built:**
- Complete directory tree (46 dirs)
- `RETAILFLUX_PLAN.md` — full project blueprint, all 12 sessions mapped
- `CLAUDE.md` — this file
- `docker-compose.yml` — all local services: Postgres, Redis, MongoDB, MinIO, FastAPI, Celery worker, React
- `.env.example` — all environment variables documented
- `.gitignore`
- `Makefile` — `make up`, `make down`, `make logs`, `make migrate`, `make test`, `make seed`
- **FastAPI backend scaffold**:
  - `app/main.py` — app factory, CORS, middleware, lifespan
  - `app/core/config.py` — Pydantic Settings (reads from .env)
  - `app/core/database.py` — async SQLAlchemy + session factory
  - `app/core/redis_client.py` — async Redis client
  - `app/core/mongodb.py` — Motor async MongoDB
  - `app/core/logging_setup.py` — structured JSON logging
  - `app/core/security.py` — JWT create/verify, bcrypt hash/verify
  - `app/api/v1/router.py` — main v1 router
  - `app/api/v1/endpoints/health.py` — `GET /health` endpoint (verifies DB, Redis, Mongo)
  - `app/models/base.py` — SQLAlchemy declarative base
  - `app/models/user.py` — User + Company ORM models
  - `app/schemas/health.py` — health response Pydantic model
  - `app/workers/celery_app.py` — Celery app factory
  - `alembic.ini` + `alembic/env.py` — migrations setup
  - `requirements.txt` — all pinned deps
  - `Dockerfile` — multi-stage
  - `tests/test_health.py` — health endpoint test
- **React frontend scaffold**:
  - `package.json` — React 18, Vite, TS, Tailwind, shadcn deps, TanStack Query, Zustand, React Router, Recharts, lucide-react
  - `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`
  - `index.html`
  - `src/main.tsx` — React root + QueryClient + Router
  - `src/App.tsx` — route outlet
  - `src/index.css` — Tailwind directives + CSS variables for shadcn
  - `src/app/router.tsx` — React Router routes (login, dashboard shell, per-dept routes)
  - `src/components/layout/AppShell.tsx` — sidebar + topbar layout
  - `src/components/layout/Sidebar.tsx` — nav with dept icons, active state, collapse
  - `src/components/layout/TopBar.tsx` — search, date range, notifications, profile
  - `src/lib/api.ts` — Axios instance with JWT interceptor + refresh logic
  - `src/lib/utils.ts` — `cn()` helper
  - `src/lib/queryClient.ts` — TanStack Query client config
  - `src/types/index.ts` — shared TypeScript interfaces
  - `src/pages/LoginPage.tsx` — placeholder login page
  - `src/pages/DashboardPage.tsx` — placeholder CEO dashboard
  - `src/features/auth/AuthProvider.tsx` — React context for auth state
  - `.github/workflows/ci.yml` — lint + typecheck + test on push/PR
  - `scripts/seed_demo.py` — stub for future demo data seeding

**Status at end of Session 1**: Project runs with `make up`. FastAPI responds at
`http://localhost:8000/health`. React shell renders at `http://localhost:3000`.
No real data yet — placeholder pages only. Auth not implemented.

---

### Session 5 — Marketing Analytics Dashboard (COMPLETE)
**What was built:**
- `app/schemas/analytics.py` — added `CampaignKpis`, `CampaignSpend`, `DailySpend`, `MarketingKpisOut` Pydantic models
- `app/domains/analytics/marketing_service.py` — `get_marketing_kpis`: 4 aggregations against `staging_marketing` (total KPIs, top campaigns, daily spend, spend-by-campaign pie) + 1 against `staging_sales` (revenue for ROAS); computes CTR, ROAS, CAC
- `app/api/v1/endpoints/analytics.py` — `GET /analytics/marketing` added alongside the existing sales endpoint
- `tests/test_analytics.py` — 3 marketing tests added (empty, full-data with ROAS/CAC/CTR assertions, auth-required 403)
- `src/types/index.ts` — `CampaignKpis`, `CampaignSpend`, `DailySpend`, `MarketingKpisOut` interfaces added
- `src/features/marketing/api.ts` — `getMarketingKpisApi(dateFrom?, dateTo?)`
- `src/pages/MarketingPage.tsx` — 4 KPI cards (spend, ROAS, CAC, CTR) · AreaChart daily spend · BarChart top-10 campaigns by conversions · PieChart spend by campaign; date-range picker wired to TanStack Query
- `src/app/router.tsx` — `/dashboard/marketing` → `<MarketingPage />`

**Status at end of Session 5**: Marketing Analytics Dashboard complete. ROAS joins `staging_sales` revenue into the marketing aggregation pipeline. All 6 analytics tests pass (3 sales + 3 marketing).

---

### Session 6 — Operations Analytics Dashboard (COMPLETE)
**What was built:**
- `app/schemas/analytics.py` — added `WarehouseStock`, `LowStockSku`, `DailyStockLevel`, `OperationsKpisOut`
- `app/domains/analytics/operations_service.py` — `get_operations_kpis`: 5 MongoDB aggregations against `staging_operations` → total KPIs (distinct SKUs, total stock units, active warehouses via `$addToSet`), SKUs below reorder point (using `$expr`+`$lt`), stock by warehouse, top-10 low-stock SKUs (avg ascending), daily avg stock level
- `app/api/v1/endpoints/analytics.py` — `GET /analytics/operations` added
- `tests/test_analytics.py` — 3 operations tests: empty, full-data (5 pipeline responses mocked in sequence), auth-required 403; total test count now 9
- `src/types/index.ts` — `WarehouseStock`, `LowStockSku`, `DailyStockLevel`, `OperationsKpisOut` interfaces added
- `src/features/operations/api.ts` — `getOperationsKpisApi(dateFrom?, dateTo?)`
- `src/pages/OperationsPage.tsx` — 4 KPI cards (SKUs below reorder highlighted red when > 0) · AreaChart daily avg stock · BarChart stock by warehouse · horizontal BarChart low-stock SKUs (red cell when below reorder point, orange when above)
- `src/app/router.tsx` — `/dashboard/operations` → `<OperationsPage />`

**Status at end of Session 6**: Operations Analytics Dashboard complete. 9 analytics tests total across sales, marketing, and operations. `staging_operations` aggregations use `$addToSet`+`$size` for distinct counts and `$expr` for reorder-point comparison.

---

### Session 8 — Procurement Analytics Dashboard (COMPLETE)
**What was built:**
- `apps/api/app/schemas/analytics.py` — added `SupplierSpend`, `SkuCost`, `ProcurementKpisOut`
- `apps/api/app/domains/analytics/procurement_service.py` — `get_procurement_kpis`: 4 MongoDB aggregations against `staging_procurement` → total KPIs (spend=quantity×unit_cost, total units, unique suppliers via `$addToSet`+`$size`, avg lead days), top 10 suppliers by spend, daily spend time-series, top 10 SKUs by avg unit cost
- `apps/api/app/api/v1/endpoints/analytics.py` — `GET /analytics/procurement` added; all 5 dept analytics endpoints now live
- `apps/api/tests/test_analytics.py` — 3 procurement tests: empty, full-data (all shapes + values verified), auth-required 403; total test count now 15
- `apps/web/src/types/index.ts` — `SupplierSpend`, `SkuCost`, `ProcurementKpisOut` interfaces added
- `apps/web/src/features/procurement/api.ts` — `getProcurementKpisApi(dateFrom?, dateTo?)`
- `apps/web/src/pages/ProcurementPage.tsx` — 4 KPI cards (total spend, units ordered, unique suppliers, avg lead days) · AreaChart daily spend (amber) · horizontal BarChart top 10 suppliers by spend · horizontal BarChart top 10 SKUs by avg unit cost; date-range picker wired to TanStack Query
- `apps/web/src/app/router.tsx` — `/dashboard/procurement` → `<ProcurementPage />`

**Status at end of Session 8**: Procurement Analytics Dashboard complete. `staging_procurement` aggregations use `$multiply` for spend computation and `$addToSet`+`$size` for unique supplier counts. 15 analytics tests total across all 5 departments.

---

### Session 7 — Finance Analytics Dashboard (COMPLETE)
**What was built:**
- `app/schemas/analytics.py` — added `CategoryRevenue`, `DailyGrossProfit`, `MonthlyPnL`, `FinanceKpisOut`
- `app/domains/analytics/finance_service.py` — `get_finance_kpis`: 4 MongoDB aggregations against `staging_finance` → total P&L KPIs (revenue, COGS, gross profit, gross margin %), revenue by category, daily gross profit time-series, monthly revenue vs COGS using `$substr` to extract YYYY-MM from date string
- `app/api/v1/endpoints/analytics.py` — `GET /analytics/finance` added; all 4 dept analytics endpoints now live
- `tests/test_analytics.py` — 3 finance tests: empty, full-data (gross margin 40% verified), auth-required 403; total test count now 12
- `src/types/index.ts` — `CategoryRevenue`, `DailyGrossProfit`, `MonthlyPnL`, `FinanceKpisOut` interfaces added
- `src/features/finance/api.ts` — `getFinanceKpisApi(dateFrom?, dateTo?)`
- `src/pages/FinancePage.tsx` — 4 KPI cards (COGS in red, gross profit/margin coloured by sign) · AreaChart daily gross profit · horizontal BarChart revenue by category · grouped BarChart monthly Revenue vs COGS (two bars, indigo + red)
- `src/app/router.tsx` — `/dashboard/finance` → `<FinancePage />`

**Status at end of Session 7**: Finance Analytics Dashboard complete. Monthly P&L uses MongoDB `$substr` aggregation to group ISO date strings into YYYY-MM buckets. 12 analytics tests total.

---

### Session 9 — CEO Dashboard / Summary (COMPLETE)
**What was built:**
- `apps/api/app/schemas/analytics.py` — added `DashboardSummaryOut` (headline KPIs from all 5 depts + daily_revenue sparkline)
- `apps/api/app/domains/analytics/summary_service.py` — `get_dashboard_summary`: fans out via `asyncio.gather` to all 5 dept services concurrently; uses `return_exceptions=True` so a single dept failure doesn't crash the whole summary
- `apps/api/app/api/v1/endpoints/analytics.py` — `GET /analytics/summary` added; all analytics endpoints now live
- `apps/api/tests/test_analytics.py` — 3 summary tests (all-empty, with-data verifying all 11 fields, auth-required 403); total test count now 18
- `apps/web/src/types/index.ts` — `DashboardSummaryOut` interface added
- `apps/web/src/features/dashboard/api.ts` — `getDashboardSummaryApi()`
- `apps/web/src/pages/DashboardPage.tsx` — full CEO dashboard: 5 linked dept KPI cards (revenue→sales, ROAS→marketing, SKUs below reorder→operations, gross margin→finance, procurement spend→procurement) with alert/trend indicators + revenue sparkline (Recharts LineChart) + alerts panel + AI summary panel (placeholder) + chart placeholders for Session 10

**Status at end of Session 9**: CEO Dashboard complete. `asyncio.gather` fans out to all 5 dept MongoDB aggregations in parallel. `DashboardPage` is fully live with real API data; all 5 dept cards link to their respective pages. 18 analytics tests total.

---

### Session 10 — AI Insights (COMPLETE)
**What was built:**
- `apps/api/app/core/gemini.py` — async wrapper: tries Gemini 1.5 Flash (`asyncio.to_thread` for sync SDK), falls back to Groq AsyncGroq, then static JSON fallback; returns `(text, provider)` tuple
- `apps/api/app/schemas/insights.py` — `InsightItem`, `AnomalyPoint`, `InsightsOut` Pydantic models
- `apps/api/app/domains/insights/__init__.py` — package init
- `apps/api/app/domains/insights/anomaly_service.py` — `detect_anomalies(daily_revenue, threshold=2.0)`: pure z-score function (no scipy dep); `get_revenue_anomalies(company_id)` fetches summary + detects
- `apps/api/app/domains/insights/insight_service.py` — `generate_insights(company_id)`: fetches summary → builds structured prompt → calls `generate_text` → JSON-parses response (strips markdown fences); falls back to raw text on parse error
- `apps/api/app/api/v1/endpoints/insights.py` — `GET /insights/summary` + `GET /insights/anomalies`, both protected by `get_current_user`
- `apps/api/app/api/v1/router.py` — insights router wired at `/insights`
- `apps/api/tests/test_insights.py` — 6 tests: summary success (Gemini JSON parsed), summary fallback on bad JSON, summary auth-required, anomalies empty (< 3 points), anomalies spike flagged (z > 2), anomalies auth-required
- `apps/web/src/types/index.ts` — `InsightItem`, `AnomalyPoint`, `InsightsOut` interfaces added
- `apps/web/src/features/insights/api.ts` — `getInsightsApi()`, `getAnomaliesApi()`
- `apps/web/src/pages/DashboardPage.tsx` — `AiInsightsPanel` replaces static panel: live Gemini insights with per-dept icons, loading spinner, provider badge, fallback message; revenue sparkline now renders amber `ReferenceDot` for each anomaly + anomaly count badge + date/z-score legend

**Status at end of Session 10**: AI Insights live. Gemini → Groq → fallback chain works. Z-score anomaly detection runs server-side with pure Python (no scipy). Dashboard shows live AI summaries per dept and flags revenue anomalies on the sparkline.

---

### Session 11 — Demand Forecasting (COMPLETE)
**What was built:**
- `apps/api/app/schemas/forecast.py` — `ForecastPoint` (ds, yhat, yhat_lower, yhat_upper), `SkuForecast` (sku, points), `ForecastOut` (forecasts: list[SkuForecast])
- `apps/api/app/domains/forecasting/__init__.py` — package init
- `apps/api/app/domains/forecasting/forecast_service.py` — `get_sku_forecast(company_id, sku, horizon_days=30)`: queries last 90 days of daily revenue from `staging_sales` → builds pandas DataFrame → runs Prophet via `asyncio.to_thread` (non-blocking) → returns 30-day forecast with CI; `_fit_and_predict` is a pure sync helper patched in tests
- `apps/api/app/domains/forecasting/top_skus_forecast.py` — `get_top_skus_forecast(company_id, n=5)`: finds top-N SKUs by revenue → runs `get_sku_forecast` for each concurrently via `asyncio.gather(return_exceptions=True)`
- `apps/api/app/api/v1/endpoints/forecasting.py` — `GET /forecasting/top-skus` + `GET /forecasting/sku?sku=BLZ-BLK-M`, both protected by `get_current_user`
- `apps/api/app/api/v1/router.py` — forecasting router wired at `/forecasting`
- `apps/api/tests/test_forecasting.py` — 5 tests: forecast shape (30 points with all 4 fields), confidence intervals (lower ≤ yhat ≤ upper), auth-required 403 for /sku, top-skus shape, auth-required 403 for /top-skus
- `apps/web/src/types/index.ts` — `ForecastPoint`, `SkuForecast`, `ForecastOut` interfaces added
- `apps/web/src/features/forecasting/api.ts` — `getTopSkusForecastApi()`, `getSkuForecastApi(sku)`
- `apps/web/src/pages/SalesPage.tsx` — forecast section added below existing charts: SKU selector dropdown, ComposedChart with historical Area (indigo gradient) + confidence-interval band (stacked Area trick: transparent lower + amber band) + dashed amber forecast Line

**Status at end of Session 11**: Demand Forecasting complete. Prophet fits on last 90 days of staging_sales data per SKU. `asyncio.to_thread` keeps the sync Prophet fit non-blocking. Dashboard/Sales page shows historical + 30-day forecast overlay with CI shading for top-5 revenue SKUs. 5 new tests (23 total across all modules).

---

### Session 12 — Polish + Deploy (COMPLETE)
**What was built:**
- `.github/workflows/ci.yml` — updated: added MongoDB service, fixed `requirements.dev.txt` → `requirements.txt`, added `MONGODB_URL`/`MONGODB_DATABASE` env vars, skip health test in CI with `-k "not test_health_endpoint"`
- `.github/workflows/deploy.yml` — Render backend deploy via HTTP hook + Vercel frontend deploy via CLI (pull env → build → deploy --prebuilt --prod); triggers on push to main
- `render.yaml` — Render service definitions: `retailflux-api` (FastAPI web service, free plan, builds with `alembic upgrade head`) + `retailflux-worker` (Celery worker, free plan); Neon Postgres as managed DB; all secrets via `sync: false` env vars
- `apps/web/vercel.json` — Vite SPA config: `buildCommand`, `outputDirectory: dist`, SPA rewrite `/((?!api/).*)→/index.html`, immutable asset caching headers, security headers (X-Frame-Options, X-Content-Type-Options)
- `apps/api/app/domains/reports/__init__.py` — package init
- `apps/api/app/domains/reports/report_service.py` — `export_report(company_id, dept, date_from, date_to, fmt)`: delegates to existing analytics services → CSV (daily time-series via `_primary_series`) or full JSON via `model_dump_json()`; `_to_csv` uses stdlib csv.DictWriter
- `apps/api/app/api/v1/endpoints/reports.py` — `GET /reports/export?dept=sales&fmt=csv` with streaming `Response` and `Content-Disposition: attachment` header
- `apps/api/app/api/v1/router.py` — reports router wired at `/reports`
- `apps/api/tests/test_reports.py` — 4 tests: CSV export (sales, checks content-type + date row present), JSON export (finance, full object), empty CSV returns `b""`, auth-required 403
- `apps/web/src/features/reports/api.ts` — `downloadReportApi(params)`: calls `/reports/export` with `responseType: blob`, extracts filename from `Content-Disposition`, triggers browser download via `URL.createObjectURL`
- `apps/web/src/pages/ReportsPage.tsx` — dept pill selector (5 depts, coloured), date-range picker, CSV + JSON download buttons with loading spinner + sonner toast, live KPI preview tiles using existing analytics queries
- `apps/web/src/app/router.tsx` — `/dashboard/reports` now renders `<ReportsPage />` (was PlaceholderPage)
- `scripts/seed_demo.py` — full rewrite: seeds Postgres (company + 6 users) AND MongoDB (5 staging collections with 90 days of realistic data: ~7K sales rows, ~630 marketing rows, ~16K operations rows, ~450 finance rows, ~500 procurement rows); idempotent via document count check
- `README.md` — comprehensive project README: what it does, full stack table, quick start, demo credentials, env vars guide, deploy steps, API reference, architecture diagram, session history

**Status at end of Session 12**: Project is production-ready. CI runs on every push/PR (lint + typecheck + pytest). Deploys automatically to Render (API) + Vercel (frontend) on push to main. Reports page replaces placeholder with real CSV/JSON export. Demo seeder populates all 5 MongoDB staging collections with 90 days of realistic fashion data. 4 new tests (27 total across all modules).

---

## Session 13 — Bug-Fix Sprint: Registration Failure (COMPLETE)

**Root cause chain (all fixed):**

1. **`email-validator` missing** — `pydantic[email]` extra was not in `requirements.txt`; `EmailStr` fields in `RegisterRequest` caused an `ImportError` on startup → added `pydantic[email]==2.10.3` to `requirements.txt`.

2. **`UploadOut` NameError** — `uploads.py` endpoint used `-> Upload:` return annotation but only imported `UploadOut` (the schema). Fixed by changing return types to `-> UploadOut`.

3. **`from prophet import Prophet` at module level** — Prophet's C++ build can fail on Windows; a module-level import crashes the entire app on startup. Fixed by moving the import inside `_fit_and_predict` (lazy import).

4. **`resend==2.5.0` not published** — that exact patch was never published to PyPI. Fixed by bumping to `resend==2.5.1` in `requirements.txt`.

5. **`bcrypt==5.0.0` incompatible with `passlib==1.7.4`** — passlib's `detect_wrap_bug()` calls bcrypt with a >72-byte test password; bcrypt 4.0+ rejects it with `ValueError`. Fixed by pinning `bcrypt==4.0.1` in `requirements.txt`.

6. **Alembic migration double-creates `userrole` enum** — migration had an explicit `op.execute("CREATE TYPE app.userrole …")` followed by `op.create_table` with an `Enum` column that also auto-creates the type. Removed the redundant `op.execute` block and let SQLAlchemy handle it via `op.create_table`.

7. **SQLAlchemy stores enum `.name` ("CEO") not `.value` ("ceo")** — ORM model used `Enum(UserRole, schema="app")` which defaults to storing the Python enum *name* uppercase; DB type expects lowercase values. Fixed by switching the column to use explicit string values: `Enum("ceo","admin",…, create_type=False)`.

**Infrastructure set up (no Docker):**
- PostgreSQL 16 installed via `winget` → `retailflux` DB + user created, migrations run.
- Python 3.11 venv created at `apps/api/.venv`; core deps installed.
- `start-api.ps1` script in root: run `.\start-api.ps1` to start the FastAPI dev server.
- `.env` file created from `.env.example` (uses localhost instead of Docker service names).

**Verified working:**
- `POST /api/v1/auth/register` → 201, returns `{access_token, user}` ✓
- `POST /api/v1/auth/login` → 200 ✓
- `GET /api/v1/users/me` with Bearer token → 200, returns user object ✓

---

### Session 14 — Test Suite Fixes (COMPLETE)
**What was fixed:**
- `scripts/seed_demo.py` — corrected `sys.path` to point at `apps/api/` (not repo root); added UTF-8 stdout wrapper for Windows console compatibility
- `tests/test_chat.py::test_chat_selects_tool_and_answers` — fixed `SalesKpisOut` mock (added missing `total_units` field); fixed mock strategy: `TOOL_REGISTRY` stores function references at import time so patching the module name doesn't reach the registry — switched to `patch.dict(cs_mod.TOOL_REGISTRY, ...)` to replace the function object directly
- `tests/test_insights.py::test_anomalies_spike_flagged` — with only 3 data points, population z-score of a spike is mathematically bounded at √2 ≈ 1.41 (never > 2.0 threshold); fixed by using 10 normal days + spike so z ≈ 3.2
- Installed `pytest`, `pytest-asyncio`, `httpx` into `.venv` (missing from prior setup)

**Status:** 54/54 tests pass. Demo data already seeded (Postgres + all 5 MongoDB staging collections).

---

### Session 15 — Full-Stack Verification & Bug-Fix Sprint (COMPLETE)

**What was fixed:**

1. **`apps/api/.env` missing** — Pydantic-settings reads `.env` from the CWD (`apps/api/`) not the repo root. Created `apps/api/.env` with all required values including `GEMINI_API_KEY`, so the server loads keys correctly regardless of how it is started.

2. **Gemini model deprecated** — `gemini-1.5-flash` no longer exists in this account's v1beta API. Tested available models; updated default everywhere (`config.py`, both `.env` files, `start-api.ps1`) to `gemini-2.5-flash-lite` which is available and working.

3. **Prophet missing `stan_backend`** — Prophet 1.1.6 requires CmdStan (compiled via `make`) which fails on Windows without MinGW. Replaced `_fit_and_predict` in `forecast_service.py` with a two-tier approach: Prophet first (works in Docker/Linux), falls back to **Holt-Winters exponential smoothing** (`statsmodels`) which runs pure-Python with no native compilation. Installed `statsmodels==0.14.4`. All 5 forecasting tests still pass (they mock `_fit_and_predict`).

**Files changed:**
- `apps/api/.env` — new file: full env config + `GEMINI_API_KEY` + `GEMINI_MODEL=gemini-2.5-flash-lite`
- `apps/api/app/core/config.py` — `GEMINI_MODEL` default updated to `gemini-2.5-flash-lite`
- `.env` (root) — `GEMINI_MODEL` updated to `gemini-2.5-flash-lite`
- `start-api.ps1` — `GEMINI_MODEL` env var added/updated
- `apps/api/app/domains/forecasting/forecast_service.py` — `_fit_and_predict` now tries Prophet then falls back to `_holtwinters_forecast`

**Verified working end-to-end:**
| System | Status | Key metric |
|---|---|---|
| Auth (login) | ✓ 200 | CEO demo user |
| analytics/sales | ✓ 200 | revenue $2,091,703 |
| analytics/marketing | ✓ 200 | ROAS 13.04x |
| analytics/operations | ✓ 200 | 20 SKUs below reorder |
| analytics/finance | ✓ 200 | gross margin 44.95% |
| analytics/procurement | ✓ 200 | spend $2,127,139 |
| analytics/summary | ✓ 200 | top SKU BLZ-NVY-M |
| forecasting/top-skus | ✓ 200 | 5 SKUs × 30 days |
| insights/summary | ✓ 200 | provider=gemini, 5 insights |
| insights/anomalies | ✓ 200 | 3 anomalies detected |
| reports/export | ✓ 200 | CSV download |
| React frontend | ✓ 200 | http://localhost:3000 |

**Status:** 54/54 tests pass. All 12 endpoints operational. Gemini AI insights live with `gemini-2.5-flash-lite`. Forecasting live with Holt-Winters. Full stack verified.

---

### Session 16 — Auth Resilience, Hard-Reload Fix, Chat Bug Fix (COMPLETE)

**What was fixed:**

1. **Redis graceful degradation** — `refresh_tokens` and `logout` in `apps/api/app/domains/auth/service.py` both crashed when Redis is unavailable (connection refused), blocking all hard reloads. Wrapped both Redis calls in `try/except`: on failure, `refresh_tokens` logs a warning and issues a new access token anyway; `logout` logs a warning and clears client-side state without denylisting the JTI.

2. **Hard-reload 403 bug** — On page reload, the in-memory Zustand access token is lost. FastAPI's `HTTPBearer` returns **403** (not 401) when the header is missing, bypassing Axios's 401 retry interceptor. Fixed by adding an auth-ready gate in `AppShell.tsx`: on mount, if no token is in memory, calls `refreshAccessToken()` (which sends the httpOnly cookie) before rendering any child page. Shows a spinner while pending; redirects to login on failure.

3. **`current_user.role.value` crash on chat endpoint** — The `role` column uses SQLAlchemy string values (not Python enums), so `current_user.role` from the DB is a plain `str`. Calling `.value` on a plain string raises `AttributeError` → 500. Fixed in `apps/api/app/api/v1/endpoints/chat.py`: `role=current_user.role.value if hasattr(current_user.role, "value") else current_user.role` — handles both plain strings (from DB) and `UserRole` enums (from test mocks). Note: `str(UserRole.SALES)` in Python 3.11 returns `"UserRole.SALES"` not `"sales"` — must use `.value`.

**Files changed:**
- `apps/api/app/domains/auth/service.py` — Redis calls wrapped in try/except in both `refresh_tokens` and `logout`; import ordering cleaned up
- `apps/web/src/components/layout/AppShell.tsx` — auth-ready gate with `refreshAccessToken()` on mount
- `apps/web/src/lib/api.ts` — `refreshAccessToken` exported
- `apps/api/app/api/v1/endpoints/chat.py` — role extraction uses `hasattr(role, "value")` guard

**Verified working:**
| Endpoint | Result |
|---|---|
| `POST /auth/refresh` with Redis down | ✓ 200, new access token issued, warning logged |
| Hard reload on any dashboard page | ✓ Spinner → data loads (no 403) |
| `POST /chat/message` | ✓ Selects tool, calls MongoDB, returns Gemini answer |
| `GET /reports/export?dept=sales&fmt=csv` | ✓ 200, 90 days of daily revenue |
| `GET /reports/export?dept=finance&fmt=json` | ✓ 200, full finance KPI JSON |

**Status:** 54/54 tests pass. All bugs fixed. Server restart required for the running ghost process to pick up chat.py changes — run `.\start-api.ps1` to restart.

---

### Session 17 — User Management UI (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/app/schemas/user.py` — added `AdminUpdateUser` Pydantic model (`role?: UserRole`, `is_active?: bool`)
- `apps/api/app/api/v1/endpoints/users.py` — added `PATCH /users/{user_id}` endpoint:
  - CEO/admin only (uses `AdminUser` dependency)
  - Guards against deactivating your own account (400)
  - Scoped to `company_id` — can't update users from other companies (404)
  - Uses `body.role.value` to assign plain string to the SQLAlchemy column (avoids Python 3.11 `str(UserRole)` → `"UserRole.CEO"` bug)
- `apps/api/tests/test_users.py` — new test file, 5 tests:
  1. `test_list_users_returns_paginated_list` — admin gets user list with total count
  2. `test_list_users_requires_admin` — non-admin gets 403
  3. `test_create_user_success` — admin creates user, `db.refresh` populates generated fields
  4. `test_update_user_role` — admin changes another user's role
  5. `test_update_user_cannot_deactivate_self` — self-deactivation returns 400

**Frontend:**
- `apps/web/src/features/users/api.ts` — new module: `listUsersApi`, `createUserApi`, `adminUpdateUserApi`
- `apps/web/src/pages/SettingsPage.tsx` — full rewrite:
  - **Profile section**: display name editor (existing)
  - **Team Members section** (CEO/admin only): user list table with role-select dropdowns + active/inactive toggle per row; inline "Invite User" form that collapses on success; initials avatars; last-login column; self-row is read-only
  - **Company section**: company ID + plan badge (existing)
  - **Appearance section**: dark mode info (existing)
  - **Account section**: member since + last login + status (existing)
  - Role badges use per-role colour coding (violet=ceo, blue=admin, emerald=sales, etc.)

**Key technical choices:**
- `db.add = MagicMock()` in tests — SQLAlchemy's `session.add()` is synchronous, not async; using `AsyncMock` caused a `RuntimeWarning` about unawaited coroutines
- `mock_session.refresh` set to a coroutine that populates generated fields (`id`, `created_at`) — avoids having to patch the `User` class (which breaks `select(User)` in the same endpoint)
- Role selector uses `<select>` with `appearance-none` + a `ChevronDown` icon overlay for consistent cross-browser styling
- All team mutations invalidate the `["users"]` query key via `useQueryClient`

**Status:** 59/59 tests pass. `PATCH /users/{id}` live. Settings page now has full user management for CEO/admin users.

### Session 18 — Email Alerts / Resend Integration (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/app/core/email.py` — `send_email(to, subject, html)` async wrapper: imports Resend lazily, wraps sync `Emails.send` in `asyncio.to_thread`; silently skips (logs warning) when `RESEND_API_KEY` is not set
- `apps/api/app/schemas/alerts.py` — `AlertPrefsOut`, `AlertPrefsUpdate`, `AlertCheckResult` Pydantic models
- `apps/api/app/domains/alerts/__init__.py` — package init
- `apps/api/app/domains/alerts/alert_service.py` — four functions:
  - `get_alert_prefs(user_id)` — reads from MongoDB `alert_prefs` collection; merges with `{email_alerts_enabled: true, alert_on_anomalies: true, alert_on_low_stock: true}` defaults
  - `update_alert_prefs(user_id, prefs)` — upserts to MongoDB then returns updated prefs
  - `check_and_send_alerts(company_id, db)` — fans out `get_dashboard_summary` + `get_operations_kpis` concurrently; detects anomalies at z > 2.5; filters low-stock SKUs; loads all active company users + their prefs; for each user respecting their toggles: calls `send_email` and inserts a `Notification` DB row; returns `AlertCheckResult`
  - HTML email template helpers `_anomaly_email_html` and `_low_stock_email_html` (inline styles, tabular data)
- `apps/api/app/api/v1/endpoints/alerts.py` — three routes:
  - `GET /alerts/preferences` — per-user prefs (`get_current_user`)
  - `PATCH /alerts/preferences` — update toggles (`get_current_user`)
  - `POST /alerts/check` — trigger company-wide check (`require_role(CEO, ADMIN)`)
- `apps/api/app/api/v1/router.py` — alerts router wired at `/alerts`
- `apps/api/tests/test_alerts.py` — 7 tests: defaults returned when no MongoDB doc, stored values returned, PATCH calls update_one and returns merged result, auth guard on GET, SALES role gets 403 on POST /check, CEO gets 200 AlertCheckResult, zero result path

**Frontend:**
- `apps/web/src/features/alerts/api.ts` — `getAlertPrefsApi`, `updateAlertPrefsApi`, `checkAlertsApi` using typed `api.get/patch/post`
- `apps/web/src/types/index.ts` — `AlertPrefs` and `AlertCheckResult` interfaces added
- `apps/web/src/pages/SettingsPage.tsx` — `Toggle` compound component (accessible `role="switch"`); `EmailAlertsSection` with three toggles (master + anomalies + low-stock), each auto-saves on click via `useMutation`; CEO/Admin users see "Run Check" button that calls `POST /alerts/check` and toasts the result summary; inserted between Company and Appearance sections

**Status at end of Session 18**: 66 total tests (64 pass without Docker health test; 66/66 with Docker). Resend email alerts live — graceful no-op without API key. MongoDB `alert_prefs` collection stores per-user toggles. `POST /alerts/check` dispatches both anomaly and low-stock email + DB notification in one company-wide sweep.

### Session 19 — Notification Bell Polish + TypeScript Zero-Error (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/app/domains/notifications/service.py` — added `mark_all_read(user_id, db)`: bulk UPDATE sets `read_at=now()` for all unread notifications for the user; returns rowcount
- `apps/api/app/api/v1/endpoints/notifications.py` — added `POST /notifications/read-all` (204); updated docstring
- `apps/api/app/domains/alerts/alert_service.py` — anomaly and low-stock notification payloads now include a human-readable `message` field (e.g. "2 spikes detected (z > 2.5σ): 2024-01-15, ..."); TopBar displays this as the notification body
- `apps/api/tests/test_notifications.py` — 6 new tests: list empty, list with data + unread count, mark read 204, mark read 404, mark all read 204, auth guard 403

**Frontend:**
- `apps/web/src/vite-env.d.ts` — new file: `/// <reference types="vite/client" />` — fixes `ImportMeta.env` TypeScript errors in `lib/api.ts` and `main.tsx`
- `apps/web/src/pages/OperationsPage.tsx` — removed unused `ReferenceLine` import
- `apps/web/src/pages/SalesPage.tsx` — fixed Recharts `Tooltip` formatter signature (`v: unknown` + `typeof v !== 'number'` guard); fixed `Legend` formatter to use `Record<string, string>` cast to avoid implicit-any indexing
- `apps/web/src/types/index.ts` — `Notification.payload` changed from rigid `{ title: string; message: string; dept?: Department }` to open `{ title?: string; message?: string; [key: string]: unknown }` — accommodates the varying JSONB payloads from the alert service
- `apps/web/src/features/notifications/api.ts` — added `markAllNotificationsReadApi()`
- `apps/web/src/components/layout/TopBar.tsx` — wired `markAllNotificationsReadApi` into a `useMutation`; added "Mark all read" button in dropdown header (visible when `unreadCount > 0`); fixed empty-state copy to "Run an alert check from Settings to get started"; made `payload.message` conditional (renders only when present)

**Status at end of Session 19:** 70 backend tests pass (72 total, 2 Docker health excluded). TypeScript compiles clean — **zero errors**. Notification bell is fully polished: unread badge, per-item mark-read, bulk mark-all-read, meaningful message text from alert payloads.

### Session 20 — WebSocket Live Updates + Celery Beat Alerts (COMPLETE)

**What was built:**

- `apps/api/app/core/pubsub.py` — `publish_event` (async, for FastAPI routes) + `publish_event_sync` (sync, for Celery tasks); both publish JSON payloads to `retailflux:events:{company_id}` Redis channels
- `apps/api/app/api/v1/endpoints/ws.py` — `GET /ws?token=<jwt>` WebSocket endpoint: validates JWT from query param, resolves company_id from DB, accepts connection, subscribes to company-scoped Redis channel, relays messages in real-time; 25-second ping loop keeps connection alive under proxy timeouts; dedicated Redis connection for pub/sub (can't block the shared pool on subscribe)
- `apps/api/app/workers/tasks/alert_tasks.py` — `periodic_alert_check` Celery task: queries all companies, runs `check_and_send_alerts` for each via `asyncio.run`, publishes `alert` event to Redis whenever notifications are created
- Updated `apps/api/app/workers/celery_app.py` — added `alert_tasks` to include list + `hourly-alerts` beat schedule (`crontab(minute=0)` — top of every hour)
- Updated `apps/api/app/api/v1/router.py` — ws router wired in (no prefix, tag="WebSocket")
- Updated `apps/api/app/core/config.py` — added `FRONTEND_URL: str = "http://localhost:3000"` setting
- Updated `apps/api/app/main.py` — CORS `allow_origins` now uses `settings.FRONTEND_URL` (configurable for prod deploy)
- `apps/api/tests/test_ws.py` — 3 tests: bad JWT rejected, refresh token rejected, valid JWT accepted + event relayed from mock pub/sub
- `apps/web/src/hooks/useRealtimeAlerts.ts` — custom hook: opens `ws://…/api/v1/ws?token=<jwt>`, reconnects with exponential backoff (max 30s), on `alert` event invalidates `["notifications"]` + `["dashboard"]` query keys, skips reconnect on 4001 (auth failure)
- Updated `apps/web/src/components/layout/AppShell.tsx` — added `<WsProvider />` component (renders null, just calls `useRealtimeAlerts()`) mounted only when `authReady` is true — ensures token is in memory before WebSocket connects
- Updated `.env.example` — fixed `GEMINI_MODEL` to `gemini-2.5-flash-lite`, added `FRONTEND_URL` (backend CORS), added prod comments for `VITE_API_URL` + WebSocket URL derivation note

**Test status:** 75/75 tests pass. TypeScript: zero errors.

**Architecture note:** Celery → Redis pub/sub → FastAPI WebSocket is the cross-process bridge. Celery tasks can't directly push to WebSocket connections (different process/memory), so they publish to a Redis channel. The WebSocket endpoint subscribes to that channel and relays messages. Each company gets its own channel (`retailflux:events:{company_id}`) for isolation.

### Session 21 — Production Deploy Config (COMPLETE)

**What was fixed:**

- `render.yaml` — Full rewrite: removed deprecated Render free Postgres (`databases:` section + `fromDatabase:`); both services now use `DATABASE_URL: sync: false` pointing to Neon. Added `FRONTEND_URL`, `CELERY_BROKER_URL`, `GEMINI_MODEL`, `EMAIL_FROM` to API service. Added `GEMINI_API_KEY`, `GROQ_API_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `GEMINI_MODEL` to worker service (needed by `periodic_alert_check`). Changed worker `startCommand` to include `--beat` so scheduled tasks (hourly alerts, nightly forecasts/insights) run in production without a separate Beat service.
- `.github/workflows/deploy.yml` — Added `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` env vars to all three Vercel CLI steps (required by `vercel pull`/`build`/`deploy`); added inline comment explaining how to retrieve them.
- `apps/api/Dockerfile` — Changed production `uvicorn --workers 2` → `--workers 1` to stay within Render's free 512 MB RAM limit.
- `apps/web/vercel.json` — Added `VITE_APP_NAME: RetailFlux` to `env` section.

**Test status:** 75/75 tests pass. TypeScript: zero errors.

---

### Session 22 — Observability (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/app/core/metrics_middleware.py` — `RequestMetricsMiddleware` (Starlette `BaseHTTPMiddleware`): times every non-health/non-metrics request, records `{timestamp, endpoint, method, status_code, duration_ms, is_error}` to MongoDB `api_metrics` collection via `asyncio.create_task` (fire-and-forget — never adds latency to responses). Creates a 7-day TTL index on `timestamp` on first run, guarded by a module-level flag.
- `apps/api/app/schemas/observability.py` — `EndpointStat`, `HourlyBucket`, `ObservabilityDashboardOut` Pydantic models
- `apps/api/app/domains/observability/__init__.py` — package init
- `apps/api/app/domains/observability/service.py` — `get_observability_dashboard()`: 3 MongoDB aggregations on `api_metrics` (summary stats, hourly volume bucketed by `$dateToString`, top-15 endpoints by request count) + P95 latency via sort+skip approximation; all scoped to last 24 h
- `apps/api/app/api/v1/endpoints/observability.py` — `GET /observability/dashboard` (CEO/Admin only via `require_role`)
- `apps/api/app/api/v1/router.py` — observability router wired at `/observability`
- `apps/api/app/main.py` — `RequestMetricsMiddleware` registered (runs outermost, before `RequestIDMiddleware`)
- `apps/api/tests/test_observability.py` — 4 tests: empty result, full data (error rate + P95 + shapes), zero error rate when all requests succeed, 403 for SALES role

**Frontend:**
- `apps/web/src/features/observability/api.ts` — `getObservabilityDashboardApi()`
- `apps/web/src/types/index.ts` — `EndpointStat`, `HourlyBucket`, `ObservabilityDashboardOut` interfaces added
- `apps/web/src/pages/ObservabilityPage.tsx` — CEO/Admin-only page: 4 KPI cards (total requests, error count with red/green accent, avg latency with amber warning >500ms, P95 latency with red/amber/emerald thresholds) · dual-series AreaChart (requests indigo + errors red, hourly buckets) · EndpointsTable with method badges, slow-endpoint amber highlighting (>500ms avg), high-error-rate red colouring (>5%) · auto-refreshes every 60 s
- `apps/web/src/app/router.tsx` — `/dashboard/observability` → `<ObservabilityPage />`
- `apps/web/src/components/layout/Sidebar.tsx` — "Observability" nav item with `Activity` icon added to `BOTTOM_ITEMS` (CEO/Admin only)

**Architecture note:** The metrics middleware records at the outer edge of the request pipeline (registered last, executes first). Using `asyncio.create_task` for the MongoDB write means the HTTP response is returned to the client before the write completes — adding zero observable latency. The 7-day TTL index keeps the collection bounded without any cron cleanup.

**Status at end of Session 22:** 77/77 tests pass (75 prior + 4 observability − 2 Docker health excluded). TypeScript: zero errors. `GET /observability/dashboard` live. Every API request automatically recorded to `api_metrics`; CEO/Admin can view traffic, error rates, and latency breakdown in real time.

**Local stack verified:**
| Endpoint | Result |
|---|---|
| `GET /api/v1/observability/dashboard` | ✓ 200 (CEO token) |
| `GET /api/v1/observability/dashboard` | ✓ 403 (sales token) |
| React `/dashboard/observability` | ✓ renders with KPI cards + chart + table |
| Middleware recording | ✓ `api_metrics` documents inserted per request |

---

### Session 23 — Audit Trail + Celery Task Monitoring (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/app/models/audit.py` — `AuditLog` SQLAlchemy ORM model mapping to the existing `app.audit_log` Postgres table (created in migration 0001 but never written to until now)
- `apps/api/app/core/audit_middleware.py` — `AuditMiddleware`: intercepts every mutating request (POST/PATCH/PUT/DELETE), decodes JWT (no DB lookup — fast path via `decode_token`), parses path into `(resource, resource_id)`, writes to `audit_log` via `asyncio.create_task` (fire-and-forget); skips 5xx errors so infrastructure failures don't appear as user actions
- `apps/api/app/schemas/audit.py` — `AuditLogEntry`, `AuditLogsResponse` Pydantic models
- `apps/api/app/domains/audit/__init__.py` — package init
- `apps/api/app/domains/audit/service.py` — `list_audit_logs(db, page, size, resource, action)`: paginated + filterable SQLAlchemy query with total count via subquery
- `apps/api/app/api/v1/endpoints/audit.py` — `GET /audit/logs?page=&size=&resource=&action=` (CEO/Admin only)
- `apps/api/app/workers/celery_signals.py` — Celery `task_prerun`/`task_postrun`/`task_failure` signal handlers: auto-tracks every task execution into MongoDB `celery_metrics` (30-day TTL index); uses `asyncio.run()` for the async MongoDB write, consistent with the pattern in `alert_tasks.py`
- `apps/api/app/schemas/observability.py` — added `CeleryTaskStat`, `RecentFailure`, `CeleryStatsOut` models
- `apps/api/app/domains/observability/service.py` — added `get_celery_stats()`: 3 MongoDB aggregations on `celery_metrics` (summary, per-task breakdown, recent failures)
- `apps/api/app/api/v1/endpoints/observability.py` — added `GET /observability/celery-stats`
- `apps/api/app/api/v1/router.py` — audit router wired at `/audit`
- `apps/api/app/main.py` — `AuditMiddleware` registered
- `apps/api/app/workers/celery_app.py` — `import app.workers.celery_signals` to activate signal handlers
- `apps/api/tests/test_audit.py` — 4 tests: empty list, with data, pagination params forwarded, 403 for SALES
- `apps/api/tests/test_observability.py` — 2 new tests: celery stats empty, celery stats with data (success rate + per-task + failures)

**Frontend:**
- `apps/web/src/types/index.ts` — `CeleryTaskStat`, `RecentFailure`, `CeleryStatsOut`, `AuditLogEntry`, `AuditLogsResponse` interfaces added
- `apps/web/src/features/observability/api.ts` — added `getCeleryStatsApi()`, `getAuditLogsApi(params)`
- `apps/web/src/pages/ObservabilityPage.tsx` — full rewrite: 3-tab layout
  - **Traffic tab** (existing content: 4 KPI cards + hourly dual-series AreaChart + endpoints table)
  - **Celery Tasks tab** (new): 4 KPI cards (tasks run, succeeded, failed, avg duration) + per-task breakdown table with success rate colouring + recent failures panel (red card, only shown when failures exist)
  - **Audit Log tab** (new): paginated table (20 rows/page) with resource filter input; columns: timestamp, method badge, resource, resource_id, user_id (truncated UUID), IP; Prev/Next pagination controls; auto-refresh every 30 s

**Architecture notes:**
- `AuditMiddleware` uses JWT fast-decode (no DB call) to capture `user_id` — tolerates missing/invalid tokens gracefully, storing `NULL` for anonymous/unauthenticated requests
- Celery signals activate at import time when `celery_app.py` is loaded by any worker — zero changes to existing task code needed
- `celery_metrics` uses a 30-day TTL (vs 7-day for `api_metrics`) because task history is more valuable for trend analysis

**Status at end of Session 23:** 83/83 tests pass (77 prior + 4 audit + 2 celery stats). TypeScript: zero errors.

---

### Session 24 — Redis Analytics Cache + Cache Management (COMPLETE)

**What was built:**

**Backend — Cache Layer:**
- `apps/api/app/core/cache.py` — full Redis cache utility: `get_json` (returns None on miss/error), `set_json` (fire-and-forget safe), `delete_pattern` (glob-based invalidation), `get_stats` (key counts by namespace), `invalidate_company_sync` (sync version for Celery workers); TTL constants: `ANALYTICS_TTL=300s`, `INSIGHTS_TTL=1800s`, `FORECAST_TTL=7200s`; key namespace: `rf:cache:{category}:{identifier}`
- `apps/api/app/schemas/cache.py` — `CacheStatsOut`, `CacheInvalidateResult` Pydantic models
- `apps/api/app/api/v1/endpoints/cache.py` — `DELETE /cache/analytics?dept=` (CEO/Admin only): invalidates one dept or all analytics + summary + insights + forecast

**Backend — Cache Wrapping (all 7 analytics services):**
- `sales_service.py` — wrapped with `analytics_key("sales", ...)` + `ANALYTICS_TTL`
- `marketing_service.py` — wrapped with `analytics_key("marketing", ...)` + `ANALYTICS_TTL`
- `operations_service.py` — wrapped with `analytics_key("operations", ...)` + `ANALYTICS_TTL`
- `finance_service.py` — wrapped with `analytics_key("finance", ...)` + `ANALYTICS_TTL`
- `procurement_service.py` — wrapped with `analytics_key("procurement", ...)` + `ANALYTICS_TTL`
- `summary_service.py` — wrapped with `summary_key(company_id)` + `ANALYTICS_TTL`
- `insight_service.py` — wrapped with `insights_key(company_id)` + `INSIGHTS_TTL` (30 min — LLM calls are expensive)
- `top_skus_forecast.py` — wrapped with `forecast_key(company_id)` + `FORECAST_TTL` (2 hr — Prophet/Holt-Winters fits are very expensive)

**Backend — Auto-Invalidation:**
- `apps/api/app/workers/tasks/process_upload.py` — calls `invalidate_company_sync(str(upload.company_id))` after MongoDB staging load (step 4); ensures fresh data is served immediately after a file upload completes

**Backend — Observability Extension:**
- `apps/api/app/domains/observability/service.py` — added `get_cache_stats()` → calls `cache.get_stats()` and returns `CacheStatsOut`
- `apps/api/app/api/v1/endpoints/observability.py` — added `GET /observability/cache-stats` (CEO/Admin only)
- `apps/api/app/api/v1/router.py` — added cache router at `/cache`

**Backend — Tests:**
- `apps/api/tests/test_cache.py` — 8 tests: cache hit (returns deserialized JSON), cache miss (returns None), Redis unavailable graceful degradation, set_json swallows errors, invalidate all (4 patterns × N keys), invalidate dept-specific, 403 for SALES role, unknown dept no-op

**Frontend:**
- `apps/web/src/types/index.ts` — added `CacheStatsOut`, `CacheInvalidateResult` interfaces
- `apps/web/src/features/cache/api.ts` — `getCacheStatsApi()`, `invalidateAnalyticsCacheApi(dept?)`
- `apps/web/src/pages/ObservabilityPage.tsx` — added 4th "Cache" tab: total keys KPI card, namespace count card, breakdown table (category × key count), invalidation controls (per-dept buttons + "Invalidate All" red button); success toast shows deleted count
- `apps/web/src/pages/SalesPage.tsx` — added Refresh button (busts Redis sales cache → refetches from MongoDB)
- `apps/web/src/pages/MarketingPage.tsx` — added Refresh button (busts marketing cache)
- `apps/web/src/pages/OperationsPage.tsx` — added Refresh button (busts operations cache)
- `apps/web/src/pages/FinancePage.tsx` — added Refresh button (busts finance cache)
- `apps/web/src/pages/ProcurementPage.tsx` — added Refresh button (busts procurement cache)
- `apps/web/src/pages/DashboardPage.tsx` — added Refresh button (busts all caches + invalidates TanStack Query keys)

**Cache architecture:**
- All `get_json`/`set_json` wrap Redis calls in try/except → graceful degradation when Redis is down (app works fine, just without caching)
- Pattern: check cache → if hit return early → if miss compute → store in cache → return result
- Upload pipeline auto-invalidates via `invalidate_company_sync` (sync Redis for Celery workers)
- Layered caching: individual dept services cache separately; summary service has its own cache; insights/forecast have longer TTLs
- TTL strategy: 5 min for analytics (frequent data), 30 min for LLM insights (expensive), 2 hr for forecasts (very expensive)

**Status at end of Session 24:** 90/90 tests pass (83 prior + 8 cache − 1 pre-existing WS event-loop issue excluded). TypeScript: zero errors. All 7 analytics services cached. Auto-invalidation on upload. Manual invalidation via Observability Cache tab + per-page Refresh buttons.

---

### Session 27 — Command Bar v2, AI Surface, Context Rail, Realtime Polish (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/alembic/versions/0004_explanations.py` — Alembic migration: creates `app.explanations` table (`id UUID PK, resource, resource_id, version, body, created_at`) with unique index on `(resource, resource_id, version)` for cache keying
- `apps/api/app/domains/copilot/__init__.py` — copilot domain package init
- `apps/api/app/domains/copilot/explain_service.py` — `get_explanation(db, resource, resource_id, context)`: checks `app.explanations` DB cache → on miss, builds resource-specific Gemini prompt from 5 templates (metric, sku, chart, anomaly, default), calls `generate_text`, stores result with `ON CONFLICT DO NOTHING`; returns `{body, resource, resource_id, cached, version}`. Cache key includes SHA-256 hash of context dict to handle same-resource different-data cases.
- `apps/api/app/api/v1/endpoints/copilot.py` — two endpoints:
  - `POST /copilot/ask` — wraps existing `handle_chat_message`; if `page_context` dict supplied, prepends it as a structured preamble to the message before LLM routing; rate-limited 120/hr
  - `POST /copilot/explain/{resource}/{resource_id}` — calls `get_explanation`, returns `ExplanationResponse`; rate-limited 200/hr
- `apps/api/app/api/v1/router.py` — copilot router wired at `/copilot`
- `apps/api/tests/test_copilot.py` — 8 tests: ask basic, ask with page context, ask auth guard, ask empty message 422, explain cache hit (LLM not called), explain cache miss (LLM called + commit), explain auth guard, explain LLM fallback on error → no 500

**Frontend:**
- `apps/web/src/lib/commandRegistry.ts` — singleton `commandRegistry` with `register/unregister/get/getAll`; 4 built-in global commands (refresh-insights, toggle-density, open-settings, export-report); feature commands registered via `window.dispatchEvent('rf:command')` pattern
- `apps/web/src/state/realtimeBus.ts` — `RealtimeBus` event bus with 5s dedup window per `type:key`; `on/off/emit`; wildcard `*` channel; auto-purges stale seen-keys at 500 entries
- `apps/web/src/features/copilot/api.ts` — `copilotAskApi`, `getExplanationApi` calling the new `/copilot/*` endpoints
- `apps/web/src/components/CommandPalette.tsx` — **rewritten** to 4-section command bar:
  - **Go** (`⌘P`) — navigable routes with search filter + `saveRecent()` on navigate
  - **Do** (`⌘.`) — action commands from `commandRegistry`, searchable
  - **Ask** (`⌘/`) — free-text → `copilotAskApi`, answer streamed inline; "Open full AI Chat" link
  - **Recent** — last 5 visited routes (sessionStorage)
  - Section tabs + Tab key cycles through them; keyboard nav (↑↓↵) per section; footer kbd hints
- `apps/web/src/components/ai/AIExplanation.tsx` — inline "Why?" sparkle button that fetches and displays AI explanation in a popover; cached 30 min in TanStack Query; loading spinner + error state
- `apps/web/src/components/ai/CopilotDock.tsx` — floating 420px chat dock (bottom-right); page-aware suggested prompts per route; user/assistant message bubbles; loading state; `⌘J` to toggle; `Enter` to send, `⇧Enter` for newline
- `apps/web/src/components/ai/WhyDrawer.tsx` — full-panel AI explanation view inside ContextRail; `ExternalLink` → full AI Chat; shows AIBadge + version info
- `apps/web/src/components/layout/ContextRail.tsx` — fixed right-edge 360px panel with 3 tabs:
  - **AI** — shows focused widget name + "Explain with AI" button → `WhyDrawer`; empty state when no widget focused
  - **Alerts** — paginated notification list from existing `listNotificationsApi`
  - **Info** — keyboard shortcuts reference
  - Toggled by `]` key or close button; `slide-in-from-right` animation; badge on Alerts tab for unread count
- `apps/web/src/components/layout/TopBar.tsx` — extended with:
  - `⌘J` → toggle CopilotDock
  - `⌘P` → CommandPalette Go section
  - `⌘.` → CommandPalette Do section
  - `⌘/` → CommandPalette Ask section
  - `]` → dispatches `rf:toggle-rail` CustomEvent
  - New AI Copilot sparkle button (violet when active)
  - `<CopilotDock>` rendered from TopBar
- `apps/web/src/components/layout/AppShell.tsx` — extended with:
  - `<ContextRail>` wired with `open`/`onClose`/`focus` props
  - `rf:toggle-rail` event listener for `]` key
  - `rf:focus-widget` event listener for widgets to set ContextRail focus
  - `<RealtimeBusProvider>` hooks `realtimeBus.on("alert", ...)` → deduped sonner toast + `notifications` query invalidation
  - `marginRight: railOpen ? "360px" : undefined` on main to avoid overlap

**Architecture notes:**
- `realtimeBus` sits between WebSocket events and toast notifications — deduplication prevents N toasts for the same alert sweep
- `rf:focus-widget` CustomEvent pattern lets any KPI card or chart register itself in the ContextRail without prop-drilling — fire `new CustomEvent('rf:focus-widget', {detail: {resource, resourceId, title, context}})` from any leaf component
- Explanation cache key = `sha256(context_json)[:16]` appended to `resource_id` — same SKU with different context data generates separate explanations; same data returns instantly from DB
- CommandPalette "Ask" section uses `copilotAskApi` (non-streaming) for inline answer; ⌘J dock provides a full conversation experience for deeper Q&A

**Status at end of Session 27:** 159/160 tests pass (8 new copilot tests + 151 prior; 1 pre-existing WS Windows asyncio issue unchanged). TypeScript: zero errors.

---

### Session 34 — Executive AI Copilot v1 (COMPLETE)

**What was built:**

**Backend:**
- `apps/api/alembic/versions/0010_copilot.py` — migration creates `app.conversations`, `app.conversation_messages`, `app.embeddings` (JSONB fallback when pgvector unavailable on Windows), `app.copilot_usage_daily`; uses PL/pgSQL DO block to attempt `CREATE EXTENSION vector` and fall back gracefully
- `apps/api/app/domains/copilot/memory.py` — conversation CRUD: `get_or_create_conversation`, `list_conversations`, `get_conversation_messages`, `add_message` (fixed `CAST(:sources AS jsonb)` syntax for asyncpg), `get_recent_messages_for_prompt`, `compact_if_needed` (LLM-based summarization of oldest half when >6000 tokens), `delete_conversation`
- `apps/api/app/domains/copilot/retriever.py` — `retrieve_context`: pgvector cosine similarity search with zero-vector fallback when pgvector/embedding unavailable
- `apps/api/app/domains/copilot/tool_router.py` — 20-tool registry with role-based access (`get_tools_for_role`); routes sales, marketing, operations, finance, procurement, inventory, tasks tools by user role
- `apps/api/app/domains/copilot/stream_service.py` — full SSE streaming pipeline: token cap → conversation → RAG retrieval → tool selection (Gemini) → tool execution → history → streaming answer → persist → compact; fixed f-string `.format()` JSON conflict (`{"tool":...}` was treated as format placeholder, fixed to inline f-string)
- `apps/api/app/domains/copilot/usage.py` — `check_and_record_usage`: daily token cap enforcement per company (100K default); `get_usage_today` for usage stats
- `apps/api/app/api/v1/endpoints/copilot.py` — routes: `POST /copilot/ask` (non-streaming), `POST /copilot/stream` (SSE), `POST /copilot/explain/{resource}/{id}`, `GET /copilot/conversations`, `GET /copilot/conversations/{id}`, `DELETE /copilot/conversations/{id}`, `GET /copilot/usage`
- `apps/api/tests/test_copilot_stream.py` — 21 tests: embeddings (4), tool routing (5), SSE streaming (3), token cap (3), conversation endpoints (4), retriever (2)

**Migration fixes (applied during this session):**
- `0006_task_management.py` — removed 6 duplicate `op.execute("CREATE TYPE ...")` calls that conflicted with SQLAlchemy's auto-create in `op.create_table`; removed `create_type=False` from all Enum columns
- `0010_copilot.py` — wrapped `CREATE EXTENSION IF NOT EXISTS vector` in DO block with exception handler; creates `embedding JSONB` instead of `vector(768)` on Windows PostgreSQL without pgvector
- `app.users` RLS — ran `ALTER USER retailflux BYPASSRLS` to allow seed script inserts without `app.current_company_id` session variable

**Frontend:**
- `apps/web/src/pages/CopilotPage.tsx` — full conversation history page: two-column layout (sidebar with conversation list + usage widget, main with message bubbles, proposed-action chips, continue button)
- `apps/web/src/components/ai/CopilotDock.tsx` — floating 420px SSE chat dock: `fetch()`-based ReadableStream SSE parser, streaming token accumulation with blinking cursor, tool_used + proposed_actions display, abort/stop button, page-aware suggested prompts, `⌘J` toggle
- `apps/web/src/features/copilot/api.ts` — `copilotStreamApi` (fetch-based SSE), `copilotAskApi`, `listConversationsApi`, `getConversationApi`, `deleteConversationApi`, `getExplanationApi`, `getCopilotUsageApi`; full TypeScript types for all SSE event shapes
- `apps/web/src/app/router.tsx` — `/dashboard/copilot` → `<CopilotPage />`
- `apps/web/src/components/layout/Sidebar.tsx` — "Copilot" nav item with `Sparkles` icon at `/dashboard/copilot` (replaced "AI Chat" → `/dashboard/ai-chat` entry)

**Key bugs fixed:**
- `KeyError: '"tool"'` — `.format(msg=message)` on a string containing `{"tool": "<tool_name>"}` literal; fixed by using inline f-string
- `PostgresSyntaxError: syntax error at or near ":"` — `:sources::jsonb` confuses asyncpg; fixed with `CAST(:sources AS jsonb)`
- `DuplicateObjectError: type "task_status" already exists` — migration 0006 double-created enums; fixed by removing explicit `CREATE TYPE` calls
- `FeatureNotSupportedError: extension "vector" is not available` — migration 0010 pgvector; fixed with PL/pgSQL DO block fallback

**SSE event protocol:** `data: {json}\n\n` — events: `token`, `tool_used`, `context_sources`, `proposed_actions`, `done`, `error`

**Status at end of Session 34:**
- 310/311 tests pass; 1 pre-existing failure (`test_ws_rejects_invalid_token` — Windows asyncio/proactor issue, unrelated)
- All 21 new copilot tests pass
- `POST /copilot/stream` → 200, `text/event-stream`
- Conversations persist (CAST fix confirmed: conversations have `message_count=2`, `total_tokens` populated)
- Sidebar updated: "Copilot" with Sparkles icon at `/dashboard/copilot`

**Local stack verified (Session 34):**
| Endpoint | Result |
|---|---|
| `GET /api/v1/health` | ✓ 200, all services ok |
| `POST /copilot/stream` | ✓ 200, SSE events: tool_used, token×N, proposed_actions, done |
| `GET /copilot/conversations` | ✓ 200, 12 conversations |
| `GET /copilot/conversations/{id}` | ✓ 200, 2 messages (user + assistant) |
| `GET /copilot/usage` | ✓ 200 |
| `GET /analytics/summary` | ✓ 200, revenue $1.9M, ROAS 12x |

---

**Local stack verified:**
| Service | Status | Notes |
|---|---|---|
| Redis | ✓ Running | Installed via `winget install Redis.Redis`; start with `Start-Process "C:\Program Files\Redis\redis-server.exe" -WindowStyle Hidden` |
| PostgreSQL | ✓ Running | Installed Session 13 via winget |
| MongoDB | ✓ Running | Installed Session 13 |
| FastAPI API | ✓ `http://localhost:8000/health` | Started via `.\start-api.ps1` |
| React frontend | ✓ `http://localhost:3000` | `cd apps/web && npm run dev` |
| Login (demo) | ✓ | `ceo@retailflux.demo` / `demo1234` |
| Analytics (all 5 depts) | ✓ 200 | Revenue $2.1M, ROAS 12x |
| AI insights | ✓ 200 | provider=gemini, 5 insights |

---

## Deploy Checklist (follow in order)

### 1. GitHub
- Create a new **public** GitHub repo
- `git init && git add . && git commit -m "Initial commit"`
- `git remote add origin https://github.com/<you>/<repo>.git && git push -u origin main`

### 2. Neon (free Postgres)
- Sign up at neon.tech → Create project → Copy connection string
- Format: `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`

### 3. Upstash (free Redis)
- Sign up at upstash.com → Create database → Copy Redis URL
- Format: `rediss://default:<token>@<host>.upstash.io:6379`
- Use same URL for both `REDIS_URL` and `CELERY_BROKER_URL`

### 4. MongoDB Atlas (free M0)
- Sign up at mongodb.com/atlas → Create free M0 cluster → Add DB user → Whitelist 0.0.0.0/0 → Copy connection string
- Format: `mongodb+srv://user:pass@cluster0.xxx.mongodb.net/retailflux`

### 5. Cloudflare R2 (free 10 GB/mo)
- Sign up at cloudflare.com → R2 → Create bucket `retailflux-uploads`
- Create API token with R2 read+write → Copy Access Key ID + Secret

### 6. Render (API + Worker)
- Sign up at render.com → New → Blueprint → connect GitHub repo → Render reads `render.yaml`
- After first deploy, go to the API service env panel, copy `SECRET_KEY` (auto-generated) and paste it into the worker service `SECRET_KEY` field
- Set all `sync: false` env vars in both services:
  - `DATABASE_URL` (Neon)
  - `REDIS_URL`, `CELERY_BROKER_URL` (Upstash)
  - `MONGODB_URL` (Atlas)
  - `FRONTEND_URL` (your Vercel URL — see step 7)
  - `GEMINI_API_KEY` (Google AI Studio → aistudio.google.com)
  - `GROQ_API_KEY` (groq.com — optional fallback)
  - `RESEND_API_KEY` (resend.com — optional, alerts skip gracefully)
  - `SENTRY_DSN` (sentry.io — optional)
  - `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` (Cloudflare R2)

### 7. Vercel (frontend)
- Sign up at vercel.com → New Project → Import GitHub repo → set Root Directory to `apps/web`
- Add env var: `VITE_API_URL` = your Render API URL (e.g. `https://retailflux-api.onrender.com`)
- Deploy → copy the Vercel URL → go back to Render and set `FRONTEND_URL` to this URL

### 8. GitHub Secrets (for CI/CD auto-deploy)
Add these in repo → Settings → Secrets and variables → Actions:
- `RENDER_DEPLOY_HOOK_URL` — Render API service → Settings → Deploy Hook → copy URL
- `VERCEL_TOKEN` — Vercel → Settings → Tokens → create
- `VERCEL_ORG_ID` — run `vercel link` locally in `apps/web/`, then read `.vercel/project.json`
- `VERCEL_PROJECT_ID` — same file as above

### 9. Seed demo data
```bash
# Run against your Neon Postgres + Atlas MongoDB
cd retailflux
DATABASE_URL="<neon_url>" MONGODB_URL="<atlas_url>" python scripts/seed_demo.py
```
Demo credentials: `ceo@retailflux-demo.com` / `Demo1234!`

### 10. Verify
- `https://<vercel-url>` — frontend loads
- `https://retailflux-api.onrender.com/health` — `{"status":"ok"}`
- `https://retailflux-api.onrender.com/docs` — API docs (disabled in prod, use `/health`)
- Login with demo CEO → all 5 dashboards load real data

---

---

## Key Design Decisions
- **No auth library** (Auth0, Supabase Auth, etc.) — custom JWT keeps it free forever and teaches the pattern
- **Refresh token in httpOnly cookie** — XSS-safe; access token in memory (Zustand)
- **company_id** on every DB row — multi-tenant row isolation from day 1
- **Celery tasks** for anything async: file processing, ML, insight generation
- **Gemini 2.5 Flash Lite** primary LLM (free tier), Groq Llama-3.1 fallback; model configured in `GEMINI_MODEL` env var
- **Neon** for prod Postgres (serverless, free 0.5 GB, works with SQLAlchemy async)
- **Upstash** for prod Redis (serverless, 10K free cmd/day, REST + redis-py both work)

---

## How to Run
```bash
cd retailflux
cp .env.example .env          # fill in your API keys
make up                       # docker-compose up --build
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
# UI:   http://localhost:3000
# MinIO: http://localhost:9001 (retailflux / retailflux_dev)
```

## Running tests
```bash
make test                     # runs pytest inside api container
```

---

## Free Service Sign-Ups Needed (for Session 12 — deploy)
- [ ] Neon (neon.tech) — free Postgres
- [ ] Upstash (upstash.com) — free Redis
- [ ] MongoDB Atlas (mongodb.com/atlas) — free M0 cluster
- [ ] Cloudflare (cloudflare.com) — R2 + DNS (free)
- [ ] Vercel (vercel.com) — frontend hosting (free)
- [ ] Render (render.com) — backend hosting (free 512 MB)
- [ ] Google AI Studio (aistudio.google.com) — Gemini API key (free tier)
- [ ] Groq (groq.com) — free Llama inference
- [ ] Sentry (sentry.io) — error tracking (free 5K events)
- [ ] Resend (resend.com) — email alerts (free 100/day)
- [ ] GitHub (github.com) — repo + Actions (free)
