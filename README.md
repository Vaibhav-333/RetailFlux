# RetailFlux

AI-powered business analytics & procurement intelligence platform for fashion/clothing companies.

## What It Does

RetailFlux replaces manual Excel-based analytics with a live, multi-department control centre. Upload your department CSV/Excel files and instantly get:

- **5 department dashboards** — Sales, Marketing, Operations, Finance, Procurement
- **CEO summary dashboard** — all key KPIs at a glance with revenue sparkline
- **AI insights** — Gemini 1.5 Flash generates plain-English summaries per department
- **Anomaly detection** — z-score flagging of revenue spikes/drops on the sparkline
- **30-day demand forecasting** — Prophet time-series forecasts with confidence intervals per SKU
- **Reports & Exports** — download any department's data as CSV or JSON

## Tech Stack

| Layer | Local dev | Production (free tier) |
|-------|-----------|------------------------|
| Frontend | Vite + React 18 + TypeScript | Vercel (free) |
| Backend | FastAPI 0.115 (Python 3.11) | Render (free 512 MB) |
| PostgreSQL | Docker | Neon (free 0.5 GB) |
| Redis | Docker | Upstash (free 10K cmd/day) |
| MongoDB | Docker | MongoDB Atlas M0 (free 512 MB) |
| Object storage | MinIO | Cloudflare R2 (free 10 GB/mo) |
| LLM primary | — | Gemini 1.5 Flash (1 500 req/day free) |
| LLM fallback | — | Groq Llama-3.1-70B (free) |
| ML | Prophet · scikit-learn · XGBoost | Same Python on Render |
| Email | — | Resend (100/day free) |
| Error tracking | — | Sentry (5 K events/mo free) |
| CI/CD | — | GitHub Actions |

**Total production cost: $0** — 100% free-tier.

## Quick Start (local)

```bash
# 1. Clone and enter
git clone <repo-url>
cd retailflux

# 2. Copy env and fill in your API keys
cp .env.example .env

# 3. Start all services
make up

# 4. Run migrations and seed demo data
make migrate
docker-compose exec api python scripts/seed_demo.py

# 5. Open the app
#   UI:      http://localhost:3000
#   API:     http://localhost:8000
#   Docs:    http://localhost:8000/docs
#   MinIO:   http://localhost:9001
```

## Demo Credentials

After running `seed_demo.py`:

| Role | Email | Password |
|------|-------|----------|
| CEO | `ceo@retailflux.demo` | `demo1234` |
| Sales | `sales@retailflux.demo` | `demo1234` |
| Marketing | `marketing@retailflux.demo` | `demo1234` |
| Finance | `finance@retailflux.demo` | `demo1234` |
| Ops | `ops@retailflux.demo` | `demo1234` |
| Procurement | `procurement@retailflux.demo` | `demo1234` |

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

```env
# Required for AI features
GEMINI_API_KEY=     # Google AI Studio — free tier
GROQ_API_KEY=       # Groq console — free tier

# Required for production
DATABASE_URL=       # Neon connection string
REDIS_URL=          # Upstash Redis URL
MONGODB_URL=        # Atlas connection string
MINIO_ENDPOINT=     # Cloudflare R2 endpoint
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

# Optional monitoring
SENTRY_DSN=         # Sentry project DSN
RESEND_API_KEY=     # Email alerts
```

## Running Tests

```bash
make test
# or directly:
docker-compose exec api pytest tests/ -v
```

## Deploying to Production

### GitHub Secrets Required

| Secret | Where to get it |
|--------|-----------------|
| `RENDER_DEPLOY_HOOK_URL` | Render dashboard → service → Deploy hook |
| `VERCEL_TOKEN` | Vercel dashboard → Settings → Tokens |

### Steps

1. Push to `main` — GitHub Actions triggers `deploy.yml` automatically
2. Backend deploys to Render via deploy hook
3. Frontend builds and deploys to Vercel via CLI

See `render.yaml` and `apps/web/vercel.json` for full configuration.

## API Reference

Interactive docs are available at `/docs` in development mode:

```
GET  /api/v1/health
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/analytics/sales
GET  /api/v1/analytics/marketing
GET  /api/v1/analytics/operations
GET  /api/v1/analytics/finance
GET  /api/v1/analytics/procurement
GET  /api/v1/analytics/summary
GET  /api/v1/insights/summary
GET  /api/v1/insights/anomalies
GET  /api/v1/forecasting/top-skus
GET  /api/v1/forecasting/sku?sku=BLZ-BLK-M
GET  /api/v1/reports/export?dept=sales&fmt=csv
POST /api/v1/uploads
```

## Project Structure

```
retailflux/
├── apps/
│   ├── api/                 FastAPI backend (Python 3.11)
│   │   ├── app/
│   │   │   ├── api/v1/      REST endpoints
│   │   │   ├── core/        Config, DB clients, security, LLM
│   │   │   ├── domains/     Business logic per domain
│   │   │   ├── schemas/     Pydantic request/response models
│   │   │   └── workers/     Celery tasks
│   │   └── tests/           pytest (all mocked, no live services needed)
│   └── web/                 React 18 + Vite + TypeScript
│       └── src/
│           ├── features/    Per-domain API callers + stores
│           ├── pages/       One page component per route
│           └── types/       Shared TypeScript interfaces
├── scripts/
│   └── seed_demo.py         Populates Postgres + MongoDB with 90 days of demo data
├── render.yaml              Render service definitions (API + Celery worker)
├── .github/workflows/
│   ├── ci.yml               Lint + typecheck + test on every push/PR
│   └── deploy.yml           Deploy to Render + Vercel on push to main
└── docker-compose.yml       Full local stack
```

## Architecture

```
React (Vercel)
    │ HTTPS + JWT (Bearer)
FastAPI (Render free)
    ├── Auth     — JWT + bcrypt, refresh token in httpOnly cookie, Redis denylist
    ├── Uploads  — MinIO/R2 storage, Celery processing, Pandera validation
    ├── Analytics — 5 dept MongoDB aggregation pipelines
    ├── Insights — Gemini → Groq → static fallback chain
    ├── Forecast — Prophet per SKU via asyncio.to_thread
    └── Reports  — CSV / JSON export from analytics pipelines
         │
    Celery + Redis (Upstash)
         │
    ┌────┼────────────────┐
    │    │                │
  Neon  MongoDB Atlas  Cloudflare R2
  (PG)  (staging data)  (file blobs)
```

## Session History

| Session | Feature |
|---------|---------|
| 1 | Project scaffold + docker-compose + CI stub |
| 2 | JWT auth system (register, login, refresh, logout, RBAC) |
| 3 | File upload pipeline (MinIO → Celery → Pandera → MongoDB) |
| 4 | Sales Analytics dashboard |
| 5 | Marketing Analytics dashboard |
| 6 | Operations Analytics dashboard |
| 7 | Finance Analytics dashboard |
| 8 | Procurement Analytics dashboard |
| 9 | CEO Summary dashboard |
| 10 | AI Insights (Gemini) + anomaly detection |
| 11 | Demand Forecasting (Prophet, 30-day SKU forecasts) |
| 12 | Polish + Deploy (CI/CD, Render + Vercel, Reports builder, demo seeder) |
