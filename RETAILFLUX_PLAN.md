# RetailFlux — AI-Powered Business Analytics & Procurement Intelligence
## Complete Project Blueprint (100% Free / Free-Tier Stack)

---

## Product Vision

**RetailFlux** is an enterprise-grade, AI-powered analytics and procurement intelligence
platform purpose-built for fashion/clothing companies. It replaces manual Excel-based
analytics with a live, multi-department control centre that ingests CSV/Excel uploads,
auto-cleans data, computes KPIs, and uses LLMs + classical ML to generate plain-English
insights, demand forecasts, anomaly alerts, and supplier risk scores.

**Target users**: SMB-to-mid-market fashion brands (5–500 employees).  
**Primary value**: Replaces ~10 hrs/wk of manual analyst work; surfaces procurement risks
and inventory issues before they cost money.

---

## Free-Tier Technology Stack

| Layer | Dev (local) | Prod (free tier) | Notes |
|---|---|---|---|
| Frontend host | Vite dev server | **Vercel** (free) | Unlimited personal projects |
| Backend host | Docker | **Render** (free 512 MB) | Spins down on idle; use `/health` ping |
| PostgreSQL | Docker postgres:16 | **Neon** (free 0.5 GB, serverless, branching) | Best free Postgres; pgvector supported |
| Redis | Docker redis:7 | **Upstash** (free 10K cmd/day, 256 MB) | Serverless Redis; great free tier |
| MongoDB | Docker mongo:7 | **MongoDB Atlas M0** (free 512 MB) | Raw uploads, AI logs, GE reports |
| Object storage | MinIO (Docker) | **Cloudflare R2** (free 10 GB/mo, no egress) | S3-compatible; zero egress cost |
| LLM (primary) | Ollama (local, optional) | **Google Gemini 1.5 Flash** (free: 15 RPM, 1M TPM, 1500 req/day) | Best free hosted LLM |
| LLM (fallback) | — | **Groq** (free: 30 RPM, Llama-3.1-70B) | Fastest free inference |
| Auth | JWT self-hosted | JWT self-hosted (no 3rd party needed) | Free forever |
| Email | — | **Resend** (free: 100 emails/day, 3K/mo) | Alerts + reports |
| CI/CD | GitHub Actions local | **GitHub Actions** (free: 2000 min/mo) | Lint + test + build + deploy |
| Monitoring | Console logs | **Sentry** (free: 5K events/mo) | Errors only in free tier |
| ML | Local Python | Same Python on Render worker | Prophet, scikit-learn, XGBoost, PyOD — all free |
| DNS/WAF | localhost | **Cloudflare** (free) | Proxy + DDoS protection |

**Total monthly cost at prod scale: $0** (within free-tier limits for a portfolio project).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  React 18 + Vite + TypeScript + Tailwind + shadcn/ui        │
│  TanStack Query · Zustand · Recharts · visx · deck.gl        │
│  Hosted: Vercel (free)                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / JWT
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI 0.115 (Python 3.11)   — Hosted: Render free        │
│  /auth  /upload  /metrics  /forecast  /ai/*  /ws             │
└─────┬──────────┬────────────┬───────────┬────────────────────┘
      │          │            │           │
  Auth svc  Ingestion    Metrics     AI Service
             worker      engine    (LLM + ML)
      │          │            │           │
      └──────────┴────────────┴───────────┘
                       │
      Celery + Upstash Redis (task queue)
                       │
  ┌────────────────────┼────────────────────┐
  │                    │                    │
Neon Postgres    MongoDB Atlas         Cloudflare R2
(star schema     (raw uploads,         (file blobs)
 + app tables)    AI logs, GE)
```

---

## Database Schema (PostgreSQL — Neon)

### `app` schema — OLTP
```
users(id, email, password_hash, name, role, company_id, created_at, last_login_at)
companies(id, name, plan, created_at)
uploads(id, company_id, user_id, dept, original_name, storage_key, status,
        rows_total, rows_clean, rows_rejected, schema_version, ge_report_id, created_at)
upload_errors(id, upload_id, row_num, column, error_type, message)
audit_log(id, user_id, action, resource, resource_id, ip, ua, created_at)
notifications(id, user_id, type, payload jsonb, read_at, created_at)
```

### `analytics` schema — Star schema
**Dimensions**: dim_date, dim_product, dim_customer, dim_supplier, dim_warehouse,
dim_campaign, dim_channel  
**Facts**: fact_sales, fact_returns, fact_inventory_snapshot, fact_inventory_movement,
fact_marketing_spend, fact_procurement, fact_finance_ledger, fact_ai_insight

---

## Department Dashboards

### Master (CEO) Dashboard
Company Health Score (0–100) · Revenue KPIs (D/W/M/Y) · Dept Performance Scorecard ·
AI Executive Summary · Inventory Risk Heatmap · Top-5 Anomalies · Supplier Risk Top-5 ·
Demand Forecast (30d) · Marketing ROI by Channel · Cash Flow Snapshot · Geo Revenue Map ·
Alert Inbox

### Sales Dashboard
Net revenue / AOV / units / return rate / gross margin · Revenue trend · Top/Bottom SKUs ·
Category×Season heatmap · Regional choropleth · Channel mix · RFM segments · Return pivot ·
Inventory-sales scatter · Prophet forecast · AI panel

### Marketing Dashboard
CAC / LTV / LTV:CAC / ROAS · Campaign table (AI-tagged) · Funnel · Cohort retention ·
Channel ROAS bars · Geo effectiveness · Customer segments · Email/social metrics · AI panel

### Operations Dashboard
Fulfillment % / dead-stock value / days-on-hand · Warehouse occupancy · Stock aging ·
Fulfillment funnel · Inventory Sankey · Bottleneck detection · Delay heatmap · AI panel

### Finance Dashboard
Revenue / gross margin / EBITDA proxy / cash position · P&L waterfall · Margin by category ·
Dept spend bars · Cash flow · Budget vs actual · Revenue forecast · Risk indicators · AI panel

### Procurement Dashboard
Active suppliers / avg lead time / on-time % / defect rate · Supplier scorecard ·
Lead-time box plot · PO Kanban · Defect trend · Vendor radar · Spend Pareto ·
Delay analysis · Optimization recommendations · AI panel

---

## AI / ML Features

| Capability | Implementation |
|---|---|
| Demand forecasting | Prophet per SKU + SARIMA fallback |
| Anomaly detection | PyOD IsolationForest + STL z-score |
| Customer segmentation | KMeans on RFM, silhouette k-selection |
| Churn propensity | XGBoost classifier |
| Supplier risk score | Gradient boosted regressor (0–100) |
| NL → data query | Gemini Flash / Groq via constrained tool-spec (no raw SQL) |
| Executive summary | LLM over computed KPI deltas (numbers from code, prose from LLM) |
| Embeddings / RAG | pgvector (past insights search) |

---

## Build Phases (one session = one phase)

| Session | Phase | Deliverable |
|---|---|---|
| **1 (done)** | **Foundations** | Repo scaffold, docker-compose, FastAPI health, React shell, CLAUDE.md |
| 2 | Auth System | JWT login/register/refresh, RBAC middleware, user management UI |
| 3 | Upload Pipeline | File upload → MinIO → Celery → Pandera/GE → star-schema load |
| 4 | Sales Dashboard | Sales KPIs, trend, SKUs, returns, segments, regional map |
| 5 | Marketing Dashboard | Campaign table, funnel, ROAS, cohort, segments |
| 6 | Operations Dashboard | Stock aging, Sankey, fulfillment funnel, bottleneck |
| 7 | Finance Dashboard | P&L waterfall, cash flow, budget vs actual, forecast |
| 8 | Procurement Dashboard | Supplier scorecard, PO Kanban, vendor radar, risk |
| 9 | Master Dashboard | Health Score, all dept scores, geo map, AI summary widget |
| 10 | AI/ML — Forecasting + Anomaly | Prophet per SKU, PyOD, insight engine, fact_ai_insight |
| 11 | NL Query + AI Chat | Gemini tool-spec, constrained executor, chat UI |
| 12 | Polish + Deploy | CI/CD, Vercel + Render deploy, Sentry, report builder, README + demo |

---

## Recommended Free Datasets

| Dataset | Source | Used For |
|---|---|---|
| H&M Personalized Fashion Recommendations | Kaggle | Sales, products, customers |
| Brazilian E-Commerce (Olist) | Kaggle | Suppliers, regions, returns |
| Online Retail II (UCI) | Kaggle | Forecasting baseline |
| DataCo Smart Supply Chain | Kaggle | Procurement, lead times |
| Marketing Campaign Performance | Kaggle | Marketing dashboard |
| Synthetic top-up | Faker + Mimesis | Finance, supplier defects |

---

## Project Structure

```
retailflux/
├── CLAUDE.md                        ← Always-updated session guide
├── RETAILFLUX_PLAN.md               ← This file
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── apps/
│   ├── api/                         ← FastAPI backend (Python 3.11)
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/                ← config, db, redis, mongo, security, logging
│   │   │   ├── api/v1/endpoints/    ← routers per domain
│   │   │   ├── domains/             ← auth, uploads, sales, marketing, ops, finance, procurement, insights
│   │   │   ├── ml/                  ← forecasting, anomaly, segmentation, supplier_risk, nl_query
│   │   │   ├── data/                ← pandera schemas, GE suites, cleaners, loaders
│   │   │   ├── models/              ← SQLAlchemy ORM models
│   │   │   ├── schemas/             ← Pydantic request/response models
│   │   │   └── workers/             ← Celery tasks
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── web/                         ← React 18 + Vite + TypeScript
│       ├── src/
│       │   ├── app/                 ← router, providers
│       │   ├── components/          ← ui, charts, layout
│       │   ├── features/            ← master, sales, marketing, ops, finance, procurement, upload, ai-chat, auth
│       │   ├── hooks/
│       │   ├── lib/                 ← api, utils, queryClient
│       │   ├── pages/
│       │   └── types/
│       ├── package.json
│       └── Dockerfile
├── scripts/
│   └── seed_demo.py
├── docs/adr/
└── examples/sample_uploads/
```

---

## RBAC Matrix

| Dashboard | CEO | Sales | Marketing | Finance | Ops | Procurement |
|---|---|---|---|---|---|---|
| Master | Full | Read (limited) | Read (limited) | Read (limited) | Read (limited) | Read (limited) |
| Sales | Full | Full | Read | Read | Read | — |
| Marketing | Full | Read | Full | Read | — | — |
| Operations | Full | Read | — | Read | Full | Read |
| Finance | Full | — | — | Full | — | — |
| Procurement | Full | — | — | Read | Read | Full |
| Uploads | All | Own dept | Own dept | Own dept | Own dept | Own dept |
| AI Chat | All | Dept-scoped | Dept-scoped | Dept-scoped | Dept-scoped | Dept-scoped |
| User Mgmt | Full | — | — | — | — | — |

---

## Security Rules

- JWT access tokens: 15 min; refresh: 7 days rotating; denylist in Upstash Redis
- Passwords: bcrypt cost 12
- Row-level isolation: every query scoped by `company_id`
- Column masking: Finance fields hidden when role ≠ Finance/CEO (Pydantic response models)
- Rate limiting: SlowAPI — `/auth` 10/min, `/upload` 30/hr, `/ai/*` 60/hr
- File safety: SHA-256 dedup, UUID storage keys, `secure_filename` sanitize
- LLM safety: tool-call only, no raw SQL passthrough, numbers from code not LLM
- PII: `customer_id` HMAC-pseudonymized at ingest
- Secrets: `.env` only, never committed; Doppler/Infisical for prod
