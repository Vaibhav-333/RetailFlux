# ADR-0006: Free-Tier Production Stack — Infrastructure Decisions

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

RetailFlux v3 is a portfolio/demo product with the hard constraint: **total monthly infrastructure cost = $0**. This constraint ruled out the obvious "right" choices at every layer (RDS, ElastiCache, Atlas M10, OpenAI, Pinecone, Datadog) and required deliberate decisions at each tier.

The stack must support:
- A Python 3.11 FastAPI backend + Celery worker + Celery Beat scheduler
- A React 18 + Vite + TypeScript frontend (SPA)
- PostgreSQL with pgvector extension (for the Copilot RAG layer)
- Redis for caching, rate limiting, pub/sub (WebSocket fan-out), and Celery broker/backend
- MongoDB for analytics staging data (~7K sales rows/day, 5 collections)
- Object storage for uploaded CSV/Excel files and task attachments
- LLM inference (Gemini primary, Groq fallback)
- CI/CD (lint + test + deploy on every push to main)
- Error tracking
- Email delivery

---

## Decision

The selected stack, organized by role:

| Layer | Service | Free Tier Limits | Chosen For |
|-------|---------|-----------------|------------|
| **Postgres** | [Neon](https://neon.tech) | 0.5GB storage, serverless compute, 10 branches | pgvector support, serverless scale-to-zero, branching for migrations |
| **Redis** | [Upstash](https://upstash.com) | 10,000 commands/day, 256MB | Serverless Redis with HTTP fallback; zero idle cost |
| **MongoDB** | [Atlas M0](https://mongodb.com/atlas) | 512MB storage, shared cluster | 512MB fits all 5 staging collections at demo scale |
| **Object Storage** | [Cloudflare R2](https://cloudflare.com/r2) | 10GB storage, 1M Class A ops/mo | Zero egress cost (unlike S3); S3-compatible API |
| **Backend Hosting** | [Render](https://render.com) | 512MB RAM, shared CPU, spins down after 15min inactivity | Free web service + 2 workers (Celery + Beat); Dockerfile supported |
| **Frontend Hosting** | [Vercel](https://vercel.com) | 100GB bandwidth/mo, unlimited builds | Zero-config Vite SPA deploy; edge CDN; preview URLs per PR |
| **LLM (primary)** | [Google AI Studio — Gemini 2.5 Flash Lite](https://aistudio.google.com) | 1,500 req/min, 1M tokens/day | Fastest available Gemini model; generous free quota |
| **LLM (fallback)** | [Groq — Llama 3.1 8B](https://groq.com) | 14,400 req/day, 6K tokens/req | ~10× faster than Gemini at inference; free API |
| **Embeddings** | Gemini `text-embedding-004` | 1,500 req/min | Co-billed with Gemini quota; 1,536-dim vectors |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) | 2,000 min/mo (public repo: unlimited) | Already in use; matrix lint+typecheck+test |
| **Error tracking** | [Sentry](https://sentry.io) | 5,000 events/mo | SDK already in `requirements.txt`; zero config |
| **Email** | [Resend](https://resend.com) | 100 emails/day, 3,000/mo | REST API; React Email templates; generous free tier |

---

## Rationale by Layer

### Postgres → Neon (vs. Supabase, PlanetScale, ElephantSQL)

**Neon** was selected over competitors for one decisive reason: **pgvector is available on the free tier**. The Copilot RAG architecture (ADR-0004) requires the `vector` extension. Supabase's free tier also supports pgvector but has a 500MB limit and enforces a 7-day paused project policy. Neon does not pause projects. PlanetScale is MySQL-only. ElephantSQL (now sunset) was ruled out.

### Redis → Upstash (vs. Redis Cloud, Fly.io Redis)

**Upstash** is the only truly serverless Redis with a perpetual free tier. Redis Cloud's free tier (30MB) is insufficient for analytics caching. The key Upstash advantage: **HTTP REST API as a fallback** — if the Redis TCP connection is blocked (some corporate networks), the app falls back to the Upstash REST API automatically.

### MongoDB → Atlas M0 (vs. self-hosted, Cosmos DB)

Atlas M0 is the only free MongoDB offering that is fully managed, persistent, and backed by MongoDB Inc. Self-hosting on Render's free tier is possible but consumes the 512MB RAM allowance. Atlas M0's 512MB limit fits the staging collections at demo scale (~90 days × 5 collections × ~200KB/day = ~90MB compressed).

### Object Storage → Cloudflare R2 (vs. AWS S3 free tier, Backblaze B2)

**R2's zero egress cost** was decisive. AWS S3 free tier (5GB, 12 months, then ~$0.09/GB egress) would incur charges after 12 months or at high download volume. Backblaze B2 has $0.01/GB egress (vs. R2's $0). R2 is S3-compatible, so `boto3` works unchanged with `endpoint_url` set.

### Backend Hosting → Render (vs. Fly.io, Railway, Heroku)

**Render** offers the most generous free tier for multi-service deployments:
- 1 free web service (FastAPI)
- 2 free worker services (Celery worker + Celery Beat)
- `render.yaml` blueprint for infrastructure-as-code

Trade-off: Render free services spin down after 15 minutes of inactivity, adding a 30–60 second cold start on the first request after idle. Mitigated by the Celery Beat service (which stays active) pinging the web service every 5 minutes via a health-check task.

Fly.io's free tier (3 shared-CPU VMs) is comparable but requires more manual configuration and has tighter memory limits on shared-CPU machines.

### LLM → Gemini + Groq (vs. OpenAI, Anthropic Claude)

**OpenAI** and **Anthropic** both require credit card registration and have no perpetual free tier. **Gemini** (Google AI Studio) offers a free tier with 1,500 requests/min and 1M tokens/day — sufficient for a portfolio demo. **Groq** adds a fast, free fallback for when Gemini is rate-limited or unavailable.

The fallback chain in `app/core/gemini.py`:
1. Gemini 2.5 Flash Lite (primary, streaming-capable)
2. Groq Llama 3.1 8B (non-streaming fallback)
3. Static error message ("I'm unable to generate a response right now")

---

## Alternatives Considered

### Full AWS free tier (12 months)
AWS offers 750 hours/mo EC2 t2.micro, 5GB S3, 25GB DynamoDB, 30GB EBS — enough to run the stack. **Rejected** because: the 12-month limit creates a "free tier cliff"; requires credit card; no managed pgvector option without RDS Postgres ($23/mo minimum).

### Supabase (Postgres + Auth + Storage + Edge Functions)
Supabase combines Postgres + object storage + auth in one platform. **Rejected** because: pgvector is available but the free tier pauses projects inactive for 7 days; auth system would conflict with the custom JWT implementation; edge functions (Deno) differ from the FastAPI architecture.

### Vercel + PlanetScale + Upstash (all-in-one JS stack)
Fully serverless TypeScript stack. **Rejected** because: the ML/analytics backend (Prophet, statsmodels, PyOD) requires Python; rewriting the backend in TypeScript/WASM was out of scope.

---

## Consequences

**Positive:**
- **$0/month** at demo/portfolio scale indefinitely (all services have perpetual free tiers, not 12-month trials).
- The stack is a direct subset of production-grade architecture (Neon → RDS, Upstash → ElastiCache, R2 → S3, Render → ECS/Cloud Run) — upgrading is a config change, not a rewrite.
- Every service has a public status page; outages are visible without custom monitoring.

**Negative / Trade-offs:**
- **Render cold start** — first request after 15 minutes idle takes 30–60 seconds. Unacceptable for real production but acceptable for a demo/portfolio product. Fix: upgrade to Render Starter ($7/mo) to disable sleep.
- **Upstash 10K commands/day** — analytics caching + rate limiting + pub/sub + Celery broker share this quota. At 10 active users hitting dashboards, 10K/day is marginal. Fix: Upstash Pay-As-You-Go ($0.2 per 100K additional commands).
- **Atlas M0 512MB** — shared cluster with no dedicated IOPS. Heavy aggregation queries may be slow under load. Fix: upgrade to M2 ($9/mo) for dedicated resources.
- **Gemini 1M tokens/day** — a company with 50 active Copilot users could hit this limit. Mitigated by the per-company daily token cap in `copilot_usage_daily`. Fix: Gemini API pay-as-you-go.
- **No persistent disk on Render** — Celery Beat's schedule state is in memory; a restart resets the "last run" time. For hourly tasks this adds at most 1 hour of delay; for daily tasks at most 24 hours. Fix: use a Postgres-backed Celery Beat scheduler (`django-celery-beat` equivalent for FastAPI).

**Follow-ons:**
- v3.x: add a `/health/infra` endpoint that checks each service's free tier quota usage and alerts when > 80% consumed.
- v3.x: document the "paid upgrade path" per service with exact SKU and cost.
- v3.x: evaluate Fly.io Machines (pay-per-second, no sleep penalty) as an alternative to Render for the API service.
