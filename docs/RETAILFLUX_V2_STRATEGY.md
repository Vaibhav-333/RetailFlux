# RetailFlux V2 — Strategic Engineering Roadmap

> **Audience:** Engineering, product, and exec leadership.
> **Owner:** Founding engineer / principal architect.
> **Purpose:** Reference document for all V2 development. Every future session begins by reading this file.
> **Last updated:** 2026-05-16
> **Status:** Approved roadmap; supersedes the original `RETAILFLUX_PLAN.md` 12-session plan (which is now complete through Session 21).

---

## Table of Contents

1. [Current Platform Audit](#1-current-platform-audit)
2. [Enterprise Gap Analysis](#2-enterprise-gap-analysis)
3. [Product Evolution Vision](#3-product-evolution-vision)
4. [Missing Critical Features](#4-missing-critical-features)
5. [Advanced AI Opportunities](#5-advanced-ai-opportunities)
6. [Enterprise UX/UI Improvements](#6-enterprise-uxui-improvements)
7. [Backend Architecture Evolution](#7-backend-architecture-evolution)
8. [Frontend Architecture Evolution](#8-frontend-architecture-evolution)
9. [Database & Analytics Evolution](#9-database--analytics-evolution)
10. [Scalability & Infrastructure Evolution](#10-scalability--infrastructure-evolution)
11. [Security & Governance Evolution](#11-security--governance-evolution)
12. [Observability & Reliability Evolution](#12-observability--reliability-evolution)
13. [AI/ML Roadmap](#13-aiml-roadmap)
14. [Session-Wise Master Development Roadmap](#14-session-wise-master-development-roadmap)
15. [Top Priority Immediate Next Sessions](#15-top-priority-immediate-next-sessions)
16. [Long-Term World-Class Vision](#16-long-term-world-class-vision)

---

## 1. Current Platform Audit

### Backend (FastAPI 0.115, Python 3.11)

| Layer | State | Verdict |
|---|---|---|
| Auth (JWT + refresh denylist) | Production-grade | Solid |
| RBAC | Tool-level only | Endpoint-level missing |
| Multi-tenancy (`company_id` filtering) | App-layer everywhere | No Postgres RLS |
| File upload pipeline (MinIO → Pandera → Mongo) | Production-grade | Solid |
| 5-dept analytics services | MongoDB aggregations, real KPIs | Works, but 1-dimensional |
| Forecasting (Prophet + HW fallback) | Production-grade | Solid |
| Anomaly detection (z-score) | Production-grade | Works for daily revenue only |
| AI insights (Gemini → Groq → static) | Production-grade | Solid |
| AI chat (LLM tool selection) | MVP | No streaming, no memory, no plan-and-execute |
| Celery + Beat (hourly alerts) | Production-grade | Solid |
| WebSocket (Redis pub/sub → client) | Production-grade | Solid |
| Audit log table | Exists, never written to | Compliance gap |
| Observability (Sentry/OTEL/Prometheus) | Not wired | Blind in prod |
| Caching (Redis) | Connected, unused for queries | Every request hits Mongo |
| Star schema / warehouse | None | Will collapse past 1M rows |
| `ml/` folder (segmentation, risk, NL) | Empty stub directories | Promised, undelivered |
| Tests | 75 unit, 0 integration/security/load | Happy paths only |

### Frontend (React 18, Vite, TS, Tailwind, shadcn/ui, Recharts)

| Layer | State | Verdict |
|---|---|---|
| Routing + protected routes + role-aware sidebar | Solid | OK |
| Cmd+K palette, dark mode, mobile drawer | Solid | OK |
| 5 dept dashboards + CEO summary | Each: 4 KPIs + 3 charts + date range | Single-dimension, no drilldown |
| Chart interactivity | Vanilla Recharts | No zoom/brush/click handlers |
| Cross-filtering | None | Missing |
| Period-over-period (YoY/MoM/WoW) | None | Missing |
| Per-chart export, annotations, saved views | None | Missing |
| Tables | Raw HTML `<table>` | No AG-Grid/TanStack Table |
| AI chat UI | Non-streaming, no suggestions, no history | MVP |
| Settings (users, alerts) | Solid | OK |
| WebSocket integration | Invalidates queries on alert | OK |
| Accessibility | Partial | Gaps |
| Brand theming (white-label) | None | Missing |

### Infrastructure / Deploy

| Layer | State |
|---|---|
| CI (GitHub Actions: lint + typecheck + pytest) | OK |
| CD (Render + Vercel auto-deploy on push to main) | OK |
| Free-tier prod config (Neon + Upstash + Atlas + R2) | OK |
| Local dev (Postgres + Redis + Mongo + start-api.ps1) | OK |
| Sentry, Datadog, Prometheus, Grafana | None |
| dbt, Airflow, Dagster | None |
| Feature flags (Unleash/LaunchDarkly) | None |

### Honest Verdict

RetailFlux is a **well-architected MVP** that demonstrates the right pieces. It is **not yet** a Fortune-500 product. The single biggest gaps, in order:

1. **Data architecture** — no star schema, no caching, no incremental ETL. Everything is a full Mongo scan.
2. **Analytics depth** — 1 dimension per chart, no cohorts, no comparisons, no drilldown.
3. **Observability** — zero traces/metrics/error tracking; cannot debug production incidents.
4. **Advanced AI** — chat is static tool-routing; no autonomous agents, no scenario sim, no root-cause analysis.
5. **Enterprise UX** — no drilldown, cross-filter, comparison, annotation, saved views.

---

## 2. Enterprise Gap Analysis

### 2.1 Missing Enterprise Features

| Category | Missing |
|---|---|
| Multi-tenancy | Workspace switcher, sub-organizations, shared dashboards across orgs |
| Identity | SSO (SAML/OIDC), SCIM provisioning, MFA, IP allowlist, audit-grade session log |
| Governance | Data lineage, column-level masking, row-level security, retention policies |
| Compliance | SOC 2 audit trail, GDPR data export/delete, region pinning |
| Integrations | Shopify, WooCommerce, Magento, NetSuite, Stripe, Klaviyo, Meta Ads, Google Ads, TikTok Ads, Mailchimp, Slack, Teams, Salesforce, HubSpot, SAP, ERP via webhook |
| Collaboration | Comments on charts, mentions, shared annotations, follow dashboards, scheduled email digests |
| Workflows | Approval flows (POs, discounts, refunds), task assignment, SLA timers |
| Reporting | PDF report builder, scheduled distribution, brand-templated reports |
| Embed/share | Public read-only links, iframe embed, white-label client portals |
| Mobile app | Native iOS/Android for executives |

### 2.2 Weak / Missing Dashboards

| Dashboard | Today | Missing |
|---|---|---|
| Sales | Revenue, AOV, top SKUs, regions | Cohorts, RFM, return rates, channel mix, basket analysis, AOV by segment, repeat-customer rate |
| Marketing | Spend, ROAS, CAC, CTR | Multi-touch attribution, funnel conversion stages, cohort retention, LTV:CAC, incrementality, brand vs performance split, creative-level performance |
| Operations | Stock, reorder, warehouses | Stockout incidents, turnover, ABC analysis, dead-stock dollars, days-on-hand, fulfillment SLA, shrinkage, location heatmap |
| Finance | Revenue, COGS, GP | EBITDA, contribution margin, P&L by entity, cash flow, AR/AP aging, budget vs actual, working capital, scenario modeling |
| Procurement | Spend, suppliers, lead days | Supplier scorecard, on-time %, defect %, lead-time variance, cost variance vs PO, dependency risk, spend concentration |
| CEO | 5 KPI cards + sparkline + AI insights | Health score, board pack, alert inbox, what-changed-yesterday view |
| Customer | None | RFM, churn risk, CLV, cohort retention, segment performance |
| Pricing | None | Margin per SKU, elasticity, markdown effectiveness, competitive price index |
| Supply chain | None | Inbound/outbound flow, network map, lead-time distributions, freight cost |
| Workforce | None | Productivity, attendance, attrition, sales-per-employee |

### 2.3 Missing AI Capabilities

- Multi-step **planning agent** (decomposes "Why did revenue drop last week?" into sub-queries)
- **Root-cause analysis** (RCA) that decomposes a metric movement into driver contributions
- **Scenario simulator** ("If we cut marketing 20% in Q3, what happens to revenue?")
- **Forecast explanation** (why is Prophet predicting X — what feature/event drove it?)
- **Automated narrative reports** (weekly/monthly auto-generated executive review)
- **Conversation memory** (chat remembers prior turns within a session)
- **Tool-streaming** (live tool-call progress in chat UI)
- **Natural-language to chart** ("show me revenue by region as a heatmap" → generate viz spec)
- **Document Q&A / RAG** (upload a vendor contract, ask questions)
- **Voice input** (push-to-talk for mobile execs)
- **Pricing AI** (dynamic price recommendations)
- **Demand-shaping** (suggest promotions to balance inventory)
- **Vendor-risk scoring** (combine delay, defect, financial-news signals)
- **Churn-prediction** (XGBoost on customer features)
- **Customer segmentation** (KMeans on RFM)
- **Image AI** (detect product defects from supplier-shipment photos)
- **OCR for invoices** (auto-process supplier invoices)

### 2.4 Missing Infrastructure

- Star schema in Postgres (`analytics.fact_*`, `analytics.dim_*`)
- **dbt** for declarative transforms with tests + docs
- **TimescaleDB** or partitioned tables for time-series KPIs
- **Redis cache** for hot aggregations with smart invalidation
- **Pre-aggregated cubes** (daily roll-ups computed once, served from cache)
- **MinIO/R2 data lake** with bronze/silver/gold layers
- **OpenTelemetry** end-to-end traces
- **Prometheus + Grafana** for metrics
- **Sentry** for error tracking (config exists, not integrated)
- **Feature store** for ML features
- **MLflow** for experiment tracking
- **Vector DB** (`pgvector`) for RAG and pattern memory
- **Workflow engine** (Temporal or Prefect) for long-running business workflows
- **API gateway** with rate-limit per company plan
- **CDN** for static assets (Cloudflare already DNS)
- **Background job retries** with DLQ

### 2.5 Missing Governance / Security

- PostgreSQL Row-Level Security policies
- Column-level masking in Pydantic response models per role
- Audit log writes on every mutation
- Data-retention policy enforcement
- PII pseudonymization at ingest (mentioned in plan; not implemented)
- Per-company data-residency (US/EU/APAC)
- Encryption at rest for MongoDB (Atlas does this by default)
- Field-level encryption for sensitive Finance/HR data
- SSO + SCIM
- MFA / TOTP
- API keys per integration with scopes
- Webhook secret rotation

---

## 3. Product Evolution Vision

**Positioning shift:** From *"AI-powered dashboard for fashion SMBs"* to ***"the AI Chief Operating Officer for retail brands."***

RetailFlux V2 should answer four questions for every executive in real time:

1. **What just happened?** (instrumentation + alerts + dashboards)
2. **Why did it happen?** (root-cause AI; causal decomposition)
3. **What should we do?** (autonomous recommendations + scenario sim + decision support)
4. **Who is doing it?** (workflow engine + task assignment + SLA tracking)

**Three product pillars:**

| Pillar | Core Modules |
|---|---|
| **Intelligence** | Unified data platform · pre-aggregated cubes · star schema · cross-source joins · live KPIs · drilldowns · annotations · saved views · comparisons · cohort engine |
| **Autonomy** | Plan-and-execute AI copilots per role · root-cause agent · scenario simulator · auto-generated weekly executive review · dynamic price / reorder / promotion recommendations · vendor-risk auto-scoring |
| **Operations** | Workflow engine (POs, refunds, discounts) · SLA tracking · approvals · supplier portal · scheduled reports · integrations marketplace · embedded analytics for clients |

**North-star metric:** *"Minutes from question to decision."* Today: ~30 (human analyst). V2 target: <30 seconds.

---

## 4. Missing Critical Features

### 4.1 Analytics

- **Period-over-period comparison toggle** (Today / WoW / MoM / QoQ / YoY) on every chart
- **Drilldown from any chart** (click region → store → SKU → transaction)
- **Cross-filtering** (select a category bar → all other charts filter to that category)
- **Saved views** (per-user dashboard state)
- **Annotations** (mark "Black Friday" or "stockout" on a chart)
- **Custom KPI builder** (drag-drop formula)
- **Pivot table** (rows × cols × measures)
- **Heatmaps** (category × season, region × channel)
- **Sankey** (inventory flow, fulfillment funnel)
- **Cohort matrix** (acquisition month × retention month)
- **Geo choropleth** (revenue by ZIP/state)
- **Treemap** (spend hierarchy)
- **Waterfall** (P&L decomposition)
- **Funnel** (marketing → conversion → revenue)
- **Confidence intervals on every forecast**
- **Variance vs forecast / vs budget**

### 4.2 Operational

- **Alerts builder** ("when ROAS drops below 3x, email + Slack")
- **Workflow automation** ("when stock < reorder, draft PO and route for approval")
- **Approval queues** (POs, discounts, refunds)
- **Task management** (assigned to user, due date, SLA)
- **Comments + @mentions** on charts/insights
- **Scheduled reports** (PDF emailed every Monday 8am)
- **Public share links** (read-only, expiry)
- **Embeddable dashboards** (iframe + JWT)

### 4.3 Integrations

- **Shopify connector** (orders, products, customers)
- **Meta/Google/TikTok Ads** (campaigns, spend, conversions)
- **Stripe** (payments, refunds)
- **Klaviyo / Mailchimp** (email + SMS)
- **Slack / Teams** (alert delivery, slash commands)
- **NetSuite / SAP / QuickBooks** (finance sync)
- **Zapier / Make webhooks** (long tail)
- **REST + GraphQL public API** (customer-built integrations)
- **CSV/Excel ingest** (existing — extend with column-mapping wizard)

### 4.4 Identity & Governance

- **SSO (SAML/OIDC)** with Okta/Azure AD/Google Workspace
- **SCIM** auto-provisioning
- **MFA / TOTP**
- **API keys with scoped permissions**
- **Audit log UI** (filter by user/action/resource)
- **Data export / delete** (GDPR)
- **Region pinning** per company

---

## 5. Advanced AI Opportunities

| AI Capability | Implementation | Business Value |
|---|---|---|
| **Plan-and-execute agent** | LangGraph-style state machine; LLM decomposes question → tool calls → synthesizes | Replaces analyst |
| **Root-cause decomposition** | Drift detection on KPIs → automated decomposition by dimension contributions | Answers "why" without humans |
| **Scenario simulator** | What-if engine on top of forecast + price-elasticity models | Strategic planning |
| **Auto exec review** | Nightly Celery task generates a markdown/PDF "yesterday in 5 minutes" report per role | Saves exec time |
| **Customer segmentation AI** | KMeans on RFM features; persistent segments in `analytics.dim_customer_segment` | Marketing targeting |
| **Churn prediction** | XGBoost on customer features; score 0-100; segment "high risk" | Retention campaigns |
| **Dynamic pricing AI** | Bayesian price-elasticity per SKU + competitor index → recommended price band | Margin optimization |
| **Demand-shaping promotions** | Combine forecast + inventory → suggest promo to clear dead-stock | Inventory turn |
| **Supplier risk scoring** | GBM on lead-time variance + defect rate + delivery-on-time + spend share | Procurement intel |
| **Anomaly detection v2** | PyOD IsolationForest + STL z-score across all KPIs (not just daily revenue) | Catch issues earlier |
| **Smart reorder agent** | Forecast × current stock × lead time + safety stock → reorder qty + draft PO | Inventory autopilot |
| **Natural-language to chart** | LLM produces Vega-Lite spec from question; render with vega-embed | Self-service BI |
| **Vector RAG memory** | pgvector stores past insights + chats; retrieved for context | Continuity of conversation |
| **Doc Q&A** | Upload contract/policy → embed → ask questions | Eliminate manual lookup |
| **Voice input** | Whisper API for mobile push-to-talk | Executive on-the-go |
| **Image AI (defect detection)** | Vision API on supplier shipment photos | QA automation |
| **OCR invoice processing** | Tesseract/Vision → extract → match PO → flag variance | AP automation |
| **Forecast explainability** | SHAP-style component breakdown; show seasonality + trend + holiday contribution | Trust in forecasts |

**Architecture principle:** Numbers come from code (deterministic Postgres/Mongo queries). Prose comes from LLM. The LLM never invents a number; it only narrates around computed values. This is non-negotiable for enterprise trust.

---

## 6. Enterprise UX/UI Improvements

### 6.1 Layout & Navigation

- **Workspace switcher** (top-left, like Slack/Linear)
- **Breadcrumbs** on every page
- **Pinned/recent pages** in sidebar
- **Global search** (entities + KPIs + dashboards + chats — Cmd+K already exists, extend it)
- **Notification inbox** as a side panel (not just dropdown)
- **In-app help / docs** drawer
- **Onboarding tour** (Shepherd.js)

### 6.2 Dashboards

- **Drilldown** on every chart (click → next dimension)
- **Cross-filter** state machine (select bar → other charts narrow)
- **Date-comparison toggle** (vs prior period / vs YoY / vs custom)
- **Annotations** (right-click chart → add note)
- **Per-chart export** (PNG, SVG, CSV, send to email)
- **Saved views** (state in URL + Postgres `analytics.saved_view`)
- **Compare mode** (split-screen two date ranges)
- **Density toggle** (compact / comfortable)
- **Dashboard builder** (drag-drop widgets, save to library)

### 6.3 Tables

- **TanStack Table** with sortable headers, column visibility, filtering, pagination, row selection, sticky headers, virtualization
- **Inline editing** for users/suppliers/POs
- **Bulk operations** (assign, archive, export)
- **Conditional formatting** (heatmap cells, traffic-light columns)

### 6.4 Charts

- Migrate from raw Recharts to **ECharts** (zoom + brush + pan + click handlers + 30+ chart types out-of-box)
- **Sparklines** in KPI cards
- **Tooltips** with mini-charts
- **Legend interactivity** (click series to toggle)
- **Confidence bands** standardized (forecasts, anomaly thresholds)

### 6.5 AI Chat

- **Streaming responses** (SSE or WebSocket)
- **Tool-call progress** ("Calling get_sales_kpis…", "Querying anomalies…")
- **Suggested prompts** per role
- **Conversation history** (left sidebar, like ChatGPT)
- **Save chat as report**
- **Voice input** (Whisper)
- **Reactions / feedback** thumbs-up/down → fine-tune dataset

### 6.6 Polish

- **Empty states** with helpful CTAs (already exists; extend)
- **Loading skeletons** that match the real layout
- **Success animations** (Lottie or framer-motion)
- **Toast queue** management
- **Keyboard shortcuts** documented (Cmd+K, Cmd+/, ?)
- **Focus management** (trap focus in modals)
- **Print stylesheets** (for PDF report generation client-side)

### 6.7 Brand / White-Label

- **CSS variable theme tokens** (replace hard-coded indigo/pink/amber)
- **Per-company theme** (logo + accent color + favicon)
- **Light/dark/system preference sync**
- **Density modes** (compact/comfortable/spacious)

### 6.8 Accessibility

- WCAG 2.1 AA: `aria-current` on nav, skip-to-content, focus rings, semantic headings, form-label association
- Screen-reader test with NVDA/JAWS
- High-contrast theme
- Reduced motion respect (`prefers-reduced-motion`)
- Keyboard reachable everywhere

### 6.9 Mobile

- Native-feeling responsive
- Tablet-specific layouts (md breakpoint)
- Drawer-based navigation
- Touch targets ≥44px
- Eventually: React Native executive app

---

## 7. Backend Architecture Evolution

### 7.1 Bounded Contexts (DDD)

Reorganize `apps/api/app/domains/` into clear bounded contexts:

```
domains/
├── identity/        # users, companies, sessions, sso, mfa, scim
├── ingestion/       # uploads, connectors, etl, data-quality
├── catalog/         # products, skus, categories, attributes
├── customers/       # customers, segments, churn, ltv
├── orders/          # transactions, returns, refunds
├── inventory/       # stock, movements, reorders, warehouses
├── marketing/       # campaigns, attribution, funnels, cohorts
├── finance/         # ledger, p&l, cash, ar/ap, budgets
├── procurement/     # suppliers, pos, contracts, risk
├── analytics/       # cubes, drilldowns, saved-views
├── insights/        # llm-narratives, rca, scenario-sim
├── forecasting/     # demand, finance, supply
├── workflows/       # approvals, tasks, slas
├── notifications/   # alerts, email, slack, ws
├── governance/      # audit, lineage, retention, pii
└── platform/        # billing, plans, feature-flags, integrations
```

### 7.2 Layered Architecture

```
api/v1/endpoints/   ← HTTP (FastAPI routers)
        ↓
schemas/            ← Pydantic DTOs (request/response)
        ↓
domains/<ctx>/      ← Application services (orchestration)
        ↓
domains/<ctx>/      ← Domain models (entities, value objects)
        ↓
infrastructure/     ← Repos (SQLAlchemy + Motor), gateways (Gemini, Resend, Slack, R2)
```

### 7.3 Async Everywhere

- Already async (SQLAlchemy 2.0, Motor, httpx, FastAPI)
- Add **structured concurrency** with `asyncio.TaskGroup` (Python 3.11+) for fan-out queries
- **Connection pooling** review (Mongo Motor 100, Postgres asyncpg 20)

### 7.4 Celery → Workflow Engine

Keep Celery for **short tasks** (alerts, single forecasts). Add **Temporal** (or Prefect) for **long-running workflows**:

- Multi-day reorder workflow (forecast → reserve stock → draft PO → route approval → email supplier → confirm receipt)
- Monthly close workflow (revenue recognition → variance → exec review)
- Onboarding workflow (verify → seed → tour → first-week digest)

### 7.5 API Versioning

- Keep `/api/v1` stable
- Add `/api/v2` for breaking changes
- Deprecation header: `Sunset: <RFC-3339>`

### 7.6 Public API

- REST: OpenAPI auto-generated (FastAPI does this)
- GraphQL: **Strawberry** for flexible client queries
- Webhooks: subscribe to events (order.created, alert.fired, forecast.complete)
- API keys: per-company, scoped, rate-limited

---

## 8. Frontend Architecture Evolution

### 8.1 State Management

| State | Tool |
|---|---|
| Server state | TanStack Query (already) |
| Auth | Zustand (already) |
| UI state (drawers, modals, toasts) | Zustand global store |
| Dashboard filters (date range, cross-filter, drilldown stack) | URL search params + Jotai (atomic) |
| Forms | react-hook-form + zod (already) |
| Real-time | WebSocket + TanStack Query invalidation (already) |

### 8.2 Component System

Split `components/` into:

```
components/
├── ui/              # Shadcn primitives (buttons, dialogs, inputs)
├── data-display/    # KpiCard, StatBadge, Sparkline, TrendIndicator
├── charts/          # Wrapped ECharts with consistent theming
├── tables/          # DataTable (TanStack), GridTable (AG-Grid for power-users)
├── filters/         # DateRange, DimensionPicker, Comparison
├── layout/          # AppShell, Sidebar, TopBar, PageHeader
├── feedback/        # EmptyState, ErrorState, Skeleton, Toast
├── forms/           # FormField, FormSelect, FormDate
├── ai/              # ChatMessage, ToolCallTrace, SuggestionChip
└── editors/         # Annotation, Comment, MarkdownEditor
```

### 8.3 Chart Library Migration

Replace Recharts with **Apache ECharts** (or **visx** for custom + **deck.gl** for geo). ECharts wins because:

- 30+ chart types out-of-box
- Built-in zoom/brush/pan/click
- Better performance with large series (50K+ points)
- Theming via JSON config
- Server-side rendering possible (Node)
- Wrap in `<RfChart type="bar" data={…} theme={…} />` for consistent API

### 8.4 Routing

Add to React Router (or migrate to **TanStack Router** for type-safe routes):

- `/workspace/:workspaceId/...`
- `/dashboard/sales/region/:regionId/sku/:skuId` (drilldown stack)
- `/saved-views/:viewId`
- `/admin/users` `/admin/integrations` `/admin/audit-log`

### 8.5 Performance

- **Code-splitting** per route (`React.lazy`)
- **Component-level Suspense**
- **Web Workers** for heavy client computations (cohort matrix calc)
- **Service Worker** for offline KPI viewing (TanStack Query persisted)
- **Bundle analyzer** in CI (size budget)

---

## 9. Database & Analytics Evolution

### 9.1 Star Schema (Postgres `analytics` schema)

**Dimensions:**

```sql
analytics.dim_date            (date_key, date, day_of_week, week, month, quarter, year, holiday_flag)
analytics.dim_company         (company_id, name, plan, region)
analytics.dim_sku             (sku_id, sku_code, name, category, subcategory, brand, season)
analytics.dim_customer        (customer_id, pseudo_id, country, city, segment_id, first_order_date)
analytics.dim_customer_segment (segment_id, name, rfm_score, churn_score, ltv)
analytics.dim_supplier        (supplier_id, name, country, tier, risk_score)
analytics.dim_warehouse       (warehouse_id, name, location, capacity)
analytics.dim_campaign        (campaign_id, name, channel, type)
analytics.dim_channel         (channel_id, name)
```

**Facts (partitioned by month):**

```sql
analytics.fact_sales              (sale_id, date_key, company_id, sku_id, customer_id, channel_id, qty, gross, discount, net, cost)
analytics.fact_returns            (return_id, ...)
analytics.fact_inventory_snapshot (snap_id, date_key, sku_id, warehouse_id, on_hand, reserved, available)
analytics.fact_inventory_movement (movement_id, date_key, sku_id, warehouse_id, type, qty)
analytics.fact_marketing_spend    (spend_id, date_key, campaign_id, channel_id, spend, impressions, clicks, conversions)
analytics.fact_procurement        (po_id, date_key, supplier_id, sku_id, qty, unit_cost, lead_days_planned, lead_days_actual, defect_qty)
analytics.fact_finance_ledger     (entry_id, date_key, account, debit, credit)
analytics.fact_ai_insight         (insight_id, date_key, dept, text, severity, dimensions jsonb, embedding vector)
```

### 9.2 Bronze / Silver / Gold Layers

- **Bronze:** raw uploads in MinIO/R2 + raw rows in MongoDB `staging_*`
- **Silver:** cleaned/validated rows (current MongoDB after Pandera)
- **Gold:** facts + dimensions in Postgres `analytics` schema, populated by **dbt** runs scheduled by Celery Beat

### 9.3 dbt Project

```
dbt/
├── models/
│   ├── staging/        # 1:1 with Mongo (via dbt's mongo source or sync to Postgres staging)
│   ├── intermediate/   # joins, lookups
│   └── marts/
│       ├── core/       # facts + dims
│       ├── marketing/  # attribution models
│       ├── sales/      # cohort, RFM
│       └── finance/    # P&L, AR/AP
├── tests/              # not_null, unique, accepted_values, freshness
├── snapshots/          # SCD2 for dims
├── docs/               # auto-generated lineage graph
└── exposures/          # dashboard → model lineage
```

### 9.4 Pre-Aggregated Cubes

Materialized views refreshed nightly + on-demand:

```sql
analytics.cube_sales_daily         (date_key, company_id, channel_id, region, revenue, units, returns, net)
analytics.cube_sales_monthly       (month, company_id, ...)
analytics.cube_marketing_daily     (date_key, company_id, campaign_id, channel_id, spend, conv, revenue, roas)
analytics.cube_inventory_daily     (date_key, company_id, sku_id, warehouse_id, on_hand, days_on_hand)
analytics.cube_finance_monthly     (month, company_id, revenue, cogs, gp, opex, ebitda)
analytics.cube_procurement_monthly (month, company_id, supplier_id, spend, on_time_pct, defect_pct)
```

API endpoints query cubes first; fall back to Mongo only for ad-hoc drilldowns.

### 9.5 Caching Strategy

- **Redis L1:** per-(company, endpoint, params, hour) cached JSON, TTL 5-60 min, invalidate on relevant `fact_*` update
- **HTTP cache:** `Cache-Control: private, max-age=60`
- **TanStack Query L2:** `staleTime` 2 min for KPIs, 30 sec for live data
- **CDN:** static assets only

### 9.6 Vector DB (pgvector)

- Insights table: store embeddings of every generated insight
- Chat history: store embeddings of past Q&A
- RAG retrieval: "have we seen this anomaly pattern before?"

---

## 10. Scalability & Infrastructure Evolution

### 10.1 Phased Scaling

| Phase | Users | Stack |
|---|---|---|
| **Free tier (today)** | 1-10 cos | Render free + Neon + Upstash + Atlas + Vercel |
| **Hobby paid ($25/mo)** | 10-100 cos | Render Starter (2GB) + Neon Pro + Upstash Pro |
| **SMB ($200/mo)** | 100-1K cos | Render Standard + Neon Scale + dedicated Atlas + Cloudflare R2 |
| **Mid-market ($1K-5K/mo)** | 1K-10K cos | Self-hosted K8s (EKS/GKE) + RDS + ElastiCache + DocumentDB + S3 + CloudFront |
| **Enterprise ($25K+/mo)** | 10K+ cos | Multi-region K8s + Aurora Global + DocumentDB Sharding + Snowflake/BigQuery for warehouse + Datadog + per-region data residency |

### 10.2 Service Decomposition (later)

Monolith first (today). When clear pain emerges, extract:

1. **AI service** (Gemini calls, embeddings, RAG) → own container, own scaling
2. **Ingestion service** (uploads, ETL, dbt) → own worker pool
3. **Reporting service** (PDF, scheduled, exports) → own container
4. **Analytics gateway** (BFF for dashboard queries) → caches + assembles

Keep **shared:** auth, billing, audit, governance.

### 10.3 Data Residency

- Region tag on `dim_company`
- Per-region Mongo Atlas cluster
- Per-region Postgres replica
- API gateway routes by `company.region`

### 10.4 Cost Controls

- **LLM cost tracking** per company (token usage in `analytics.fact_ai_usage`)
- **Plan-based rate limits** (free 100 chats/mo, pro unlimited)
- **Storage quotas** per plan
- **Auto-archive** old uploads (R2 lifecycle)

---

## 11. Security & Governance Evolution

### 11.1 Identity

- SSO (SAML 2.0 + OIDC) via Authentik or WorkOS
- SCIM 2.0 provisioning
- MFA (TOTP, WebAuthn)
- Session management (revoke, list devices)
- IP allowlist per company

### 11.2 Authorization

- **Casbin** or **OPA** for policy-as-code
- Endpoint-level `@require_role(...)` on every analytics route
- Column-level masking in Pydantic response models (already partial in plan)
- **Postgres RLS** policies for defense-in-depth:

```sql
CREATE POLICY company_isolation ON analytics.fact_sales
  USING (company_id = current_setting('app.current_company_id')::uuid);
```

### 11.3 Audit

- Wire `audit_log` writes on every mutation (create, update, delete, login, role change, integration connect)
- Audit log UI: filter, export, retain 7 years
- Tamper-evident hashing (append-only, hash-chained)

### 11.4 PII

- HMAC-pseudonymize `customer_id` at ingest (mentioned in plan)
- Field-level encryption for SSN/payment
- GDPR data-export / right-to-be-forgotten endpoint
- Retention policy enforcement (delete `fact_sales` rows older than X years per policy)

### 11.5 Application Security

- CSRF tokens on cookie-auth mutations
- CSP headers
- Strict CORS (already)
- HSTS preload
- Rate-limit by user + by IP + by company plan
- SAST (Snyk / Semgrep) in CI
- DAST (OWASP ZAP) weekly
- Dependabot alerts auto-PR'd
- Secrets scanning (Gitleaks)

### 11.6 Compliance Roadmap

- **SOC 2 Type II** (12-month observation)
- **GDPR**
- **CCPA**
- **PCI scope-reduction** (Stripe handles PAN)
- **ISO 27001** (later)

---

## 12. Observability & Reliability Evolution

### 12.1 Three Pillars

- **Logs:** Already structlog. Ship to Loki (Grafana) or Datadog Logs.
- **Metrics:** Add `prometheus-fastapi-instrumentator` → /metrics endpoint → Grafana dashboards. Track p50/p95/p99 latency, error rate, RPS, Mongo query duration, LLM token usage.
- **Traces:** OpenTelemetry SDK → OTLP exporter → Jaeger or Datadog APM. Trace propagation FastAPI → Mongo → Celery → Gemini.

### 12.2 Error Tracking

- Sentry SDK in FastAPI + React
- Source maps uploaded in CI
- Release tags
- Performance monitoring (Sentry Tracing)

### 12.3 SLOs

| Service | SLO |
|---|---|
| API availability | 99.9% |
| API p95 latency | < 500ms |
| Forecast freshness | < 24h |
| Alert delivery | < 60s |
| WebSocket reconnect success | > 99% |

### 12.4 Alerting

- PagerDuty / Opsgenie
- Alert on SLO burn-rate (Google SRE multi-window)
- Synthetic monitoring (Checkly) for critical user journeys

### 12.5 Reliability Patterns

- **Circuit breakers** for Gemini/Groq (Tenacity already; add CircuitBreaker)
- **Bulkheads** (separate thread pools for Mongo vs LLM)
- **Timeouts** on every external call
- **Idempotency keys** on mutating endpoints
- **Graceful degradation** (LLM fallback chain already done; extend to analytics fallbacks)

### 12.6 Disaster Recovery

- Neon point-in-time recovery (built-in)
- Atlas continuous backups
- R2 cross-region replication
- DR runbook: RTO 4h, RPO 1h
- Quarterly chaos drill

---

## 13. AI/ML Roadmap

### 13.1 Foundation (Sessions 22-26)

- pgvector setup; embedding pipeline; insight & chat memory
- Chat streaming (SSE); conversation persistence; suggested prompts
- Tool registry expansion (segmentation, churn, supplier risk)
- Multi-step planning agent (LangGraph or hand-rolled state machine)
- Forecast explainability (component decomposition)

### 13.2 Predictive Models (Sessions 27-32)

- **Demand forecasting v2:** hierarchical reconciliation (top-down + bottom-up); covariate features (price, promo, holiday)
- **Customer segmentation:** RFM + KMeans; persistent segment IDs
- **Churn prediction:** XGBoost; calibrated probability; retention-recommendation engine
- **Supplier risk:** GBM on lead-time + defect + on-time + financial signals
- **Anomaly detection v2:** IsolationForest across all KPIs (not just revenue)
- **Stockout prediction:** survival model on inventory time-to-stockout
- **Price elasticity:** Bayesian regression per SKU
- **Returns prediction:** classifier per order

### 13.3 Autonomous Agents (Sessions 33-38)

- **RCA agent:** "Revenue dropped 12% Friday. Why?" → decompose by channel, region, SKU, return rate → narrate top contributors
- **Scenario simulator:** "If we cut marketing 20% Q3, revenue impact?" → use elasticity + attribution models
- **Reorder agent:** forecast × stock × lead → suggest reorder qty + draft PO → human approval
- **Pricing agent:** elasticity × competitor index × inventory → suggest price band
- **Campaign optimizer:** reallocate spend across channels weekly
- **Executive briefing agent:** nightly markdown/PDF "yesterday in 5 minutes"
- **Smart-alert refinement:** learn which alerts users actually act on

### 13.4 Multimodal (Sessions 39-44)

- Vision (defect detection on supplier photos)
- OCR (invoice processing)
- Voice (Whisper for mobile)
- NL to chart (Vega-Lite generation)
- Document Q&A (vendor contracts, policies)

### 13.5 MLOps (Session 45)

- MLflow experiment tracking
- Model registry
- Feature store (Feast)
- Drift monitoring (Evidently)
- A/B testing framework
- Continuous retraining on Celery Beat

---

## 14. Session-Wise Master Development Roadmap

Each session is **self-contained**, **production-grade**, and **independently shippable** in 1-2 days of focused work. Sessions are ordered to minimize refactor cost — foundations first, then features that build on them.

> **Format per session:** Objective · Business Value · User Impact · Backend Δ · Frontend Δ · Postgres/Mongo Δ · APIs · AI/ML · Celery · Realtime · RBAC · Charts · UX · Scalability · Testing · Deploy · Observability · Performance · Complexity · Order · Dependencies · Risks · Folders · Reusable Components

### PHASE A — Production Hardening (Sessions 22-26)

These are non-negotiable foundations. Without them, every later feature is fragile.

#### Session 22 — Observability Foundation
- **Objective:** Wire Sentry + structlog correlation IDs + Prometheus metrics + OpenTelemetry traces
- **Business value:** Mean-time-to-detect drops from "user complains" to <60s
- **User impact:** Invisible to end-users; massive impact for operators
- **Backend:** `core/observability.py`; OTEL FastAPI/SQLAlchemy/Motor/Celery instrumentors; Sentry SDK
- **Frontend:** Sentry React SDK; web-vitals reporting; user feedback widget
- **DB:** none
- **APIs:** add `/metrics` (Prometheus)
- **Celery:** OTEL instrumentor for tasks
- **Real-time:** WebSocket span propagation
- **RBAC:** none (operator-only `/metrics`)
- **Charts:** none
- **UX:** error fallback boundary, "Send feedback" button on errors
- **Scalability:** essential
- **Testing:** smoke test `/metrics` returns Prometheus format
- **Deploy:** SENTRY_DSN env in Render; OTEL collector optional
- **Observability:** this IS the session
- **Perf:** OTEL overhead <2%
- **Complexity:** Medium
- **Order:** 1
- **Dependencies:** none
- **Risks:** SDK conflicts; mitigate by version pinning
- **Folders:** `apps/api/app/core/observability/`
- **Reusable:** request-id middleware, error boundary component

#### Session 23 — Audit Log Wiring + Compliance Foundation
- **Objective:** Make `audit_log` actually capture every mutation (login, role change, upload, mutation)
- **Business value:** SOC 2 / GDPR readiness
- **Backend:** `core/audit.py` decorator; apply to all POST/PATCH/DELETE; capture user_id, action, resource, resource_id, ip, ua, before/after diff (jsonb)
- **DB:** Alembic migration extends `audit_log` with `diff jsonb`, `request_id`
- **APIs:** `GET /admin/audit-log` (CEO/admin), filters by user/resource/date
- **Frontend:** Admin > Audit Log page with TanStack Table
- **RBAC:** CEO/admin only
- **Testing:** decorator unit tests
- **Order:** 2
- **Folders:** `apps/api/app/core/audit/`, `apps/api/app/api/v1/endpoints/audit.py`

#### Session 24 — Endpoint-Level RBAC + Postgres RLS
- **Objective:** Tighten authz. Every analytics endpoint requires the right role. Postgres has RLS as defense-in-depth.
- **Backend:** `dependencies/rbac.py` (Casbin); `@require_role(SALES, ADMIN, CEO)` on `/analytics/sales`; equivalent on all dept endpoints
- **DB:** RLS policies on `app.users`, `app.uploads`, future `analytics.fact_*` tables; SET LOCAL app.current_company_id on every session
- **Tests:** matrix tests (every role × every endpoint)
- **Order:** 3
- **Folders:** `apps/api/app/core/rbac/`

#### Session 25 — Redis Caching Layer + Cache Invalidation
- **Objective:** Cache analytics aggregations by (company, endpoint, params, hour). Invalidate on relevant ingestion event.
- **Backend:** `core/cache.py` with `@cached(key, ttl)` decorator; wrap every analytics service method
- **Invalidation:** on `process_upload` completion → publish `cache.invalidate.{company_id}.{dept}` to Redis pub/sub → consumer deletes matching keys
- **Observability:** cache hit/miss metrics
- **Tests:** cache hit asserts no Mongo call
- **Order:** 4
- **Performance impact:** 10-100x for repeat queries
- **Folders:** `apps/api/app/core/cache/`

#### Session 26 — Postgres Star Schema + dbt Foundation
- **Objective:** Build `analytics` schema with dims + facts. Wire dbt project. Schedule nightly run.
- **DB:** Alembic migration creates `analytics.dim_date`, `dim_sku`, `dim_customer`, `dim_supplier`, `dim_warehouse`, `dim_campaign`, `dim_channel`; `fact_sales`, `fact_marketing_spend`, `fact_inventory_snapshot`, `fact_procurement`, `fact_finance_ledger`. Partitioning by month.
- **Pipeline:** Celery task syncs staging Mongo → Postgres facts (incremental by date); dbt runs after sync; cube materialized views refresh
- **dbt:** new `dbt/` project at repo root; models: staging → intermediate → marts; tests on every column
- **Order:** 5
- **Folders:** `dbt/`, `apps/api/app/workers/tasks/etl.py`, `apps/api/alembic/versions/0002_analytics_schema.py`
- **Risk:** longest session; can split into 26a (schema) and 26b (dbt sync)

### PHASE B — Analytics Depth (Sessions 27-32)

Now build the comparison, drilldown, cohort, and segmentation features that competitors have.

#### Session 27 — Period-Over-Period Comparison Engine
- **Objective:** Every KPI returns current + prior + delta + delta%
- **Backend:** analytics services accept `compare_to: previous_period | yoy | mom | wow | custom`
- **Frontend:** PoP toggle on every dashboard; KPI cards show ▲/▼ with %; trend lines show two series
- **Cubes:** dbt models pre-compute "yesterday" and "last week" for fast comparison
- **Order:** 6

#### Session 28 — Drilldown State Machine + Saved Views
- **Backend:** `analytics.saved_view` table (user_id, dashboard, filters jsonb)
- **Frontend:** click chart element → push to drilldown stack (URL: `/dashboard/sales?path=region:US,sku:BLZ-NVY-M`); breadcrumb above chart; "Save view" button
- **Order:** 7
- **Reusable:** `useDrilldown` hook, `DrilldownBreadcrumb` component

#### Session 29 — Cross-Filtering on Dashboards
- **Frontend:** Jotai filter atom per dashboard; clicking a bar/pie segment filters all sibling charts; "Clear filters" pill
- **Backend:** all services already accept filter dict
- **Order:** 8

#### Session 30 — Customer Analytics + RFM + Cohorts
- **Backend:** `domains/customers/`: RFM scoring service; KMeans segmentation; cohort retention service
- **DB:** `analytics.dim_customer_segment`, `analytics.cube_cohort_retention`
- **Frontend:** new `/dashboard/customers` page: RFM scatter, cohort matrix, segment table, churn score distribution
- **AI:** ML pipeline computes RFM features nightly
- **Order:** 9

#### Session 31 — Multi-Touch Attribution + Marketing Funnel v2
- **Backend:** attribution service (last-touch, first-touch, linear, time-decay, Markov)
- **DB:** `fact_marketing_touch` with order_id link
- **Frontend:** funnel chart, attribution-model selector, channel contribution waterfall
- **Order:** 10

#### Session 32 — Inventory Intelligence (ABC, Days-on-Hand, Stockout Risk)
- **Backend:** ABC analysis (Pareto), days-on-hand calc, stockout-risk model (forecast × stock × lead time)
- **Frontend:** `/dashboard/operations` adds ABC quadrant, DoH bar, stockout-risk SKU table
- **Order:** 11

### PHASE C — Autonomous AI (Sessions 33-38)

#### Session 33 — Chat Streaming + Conversation Memory
- **Backend:** SSE endpoint `/chat/stream`; pgvector `chat_messages` with embeddings; retrieve last N relevant turns
- **Frontend:** stream tokens to bubble; tool-call progress trace; left sidebar with conversation history
- **AI:** Gemini streaming API; pgvector retrieval
- **Order:** 12

#### Session 34 — Plan-and-Execute Agent
- **Backend:** state-machine agent: plan → execute tools → synthesize; logs each step to `chat_messages` with step_type
- **Frontend:** show plan steps in UI; collapsible tool-call traces
- **Order:** 13

#### Session 35 — Root-Cause Analysis Agent
- **Backend:** RCA service: drift detection on a KPI → decompose by dimension contributions → LLM narrative
- **Frontend:** "Why did X drop?" button on any KPI; modal shows decomposition + AI narrative
- **Order:** 14

#### Session 36 — Scenario Simulator
- **Backend:** simulator service uses elasticity + attribution models to project outcomes
- **Frontend:** sliders for marketing spend / price / promo depth; live forecast preview
- **Order:** 15

#### Session 37 — Auto Executive Briefing
- **Backend:** Celery Beat nightly task generates per-role markdown report; rendered to PDF (WeasyPrint); emailed via Resend
- **Frontend:** `/briefings` list page; viewer with annotations
- **Order:** 16

#### Session 38 — Smart Reorder Agent + Approval Workflow
- **Backend:** reorder service computes qty; creates draft PO; routes to approver; Slack DM notification
- **DB:** `workflows.purchase_order` + `workflows.approval_step`
- **Frontend:** approval inbox; PO detail; one-click approve/reject
- **Order:** 17

### PHASE D — Enterprise UX (Sessions 39-44)

#### Session 39 — ECharts Migration + Interactive Charts
- Replace Recharts with ECharts; consistent `<RfChart>` wrapper; zoom, brush, pan, click

#### Session 40 — TanStack Table Everywhere + AG-Grid for Power Users
- Migrate Uploads, Users, Notifications, Audit Log to TanStack Table
- AG-Grid Community for big tables (POs, customers, transactions)

#### Session 41 — Dashboard Builder + Custom Widgets
- Drag-drop widget grid (react-grid-layout); widget palette; save per user/role

#### Session 42 — Annotations, Comments, Mentions
- Postgres `analytics.annotation` + `chat.comment`; UI: right-click chart → add note; @mention triggers notification

#### Session 43 — Scheduled Reports + PDF Builder
- Schedule any dashboard/view; PDF render server-side (Playwright or WeasyPrint); email or Slack delivery

#### Session 44 — White-Label Theming + Brand Tokens
- CSS variables for all colors; per-company logo + accent color + favicon; light/dark/system

### PHASE E — Integrations (Sessions 45-50)

#### Session 45 — Shopify Connector
- OAuth → webhook subscription → ingestion service → Mongo staging → dbt → cubes

#### Session 46 — Ads Connectors (Meta, Google, TikTok)
- Daily polling jobs; unified `fact_marketing_spend`

#### Session 47 — Stripe + Klaviyo + Slack
- Stripe: payments, refunds; Klaviyo: campaigns; Slack: alert delivery + slash commands

#### Session 48 — Public REST API + Webhooks
- API keys; scoped permissions; rate limits; webhook delivery with retries + signing

#### Session 49 — GraphQL API (Strawberry)
- Wrap key analytics + entities; persisted queries for security

#### Session 50 — Integrations Marketplace UI
- Browse + connect + status + logs; OAuth flows; per-connector config UI

### PHASE F — Identity & Compliance (Sessions 51-54)

#### Session 51 — SSO (SAML + OIDC) via WorkOS
- Replace local-only login for enterprise plans; backward-compatible with email/password

#### Session 52 — SCIM Provisioning + MFA
- SCIM 2.0 endpoint; TOTP enrollment; WebAuthn passkeys

#### Session 53 — GDPR Data Export / Delete
- User-self-service export ZIP; right-to-be-forgotten erases or pseudonymizes

#### Session 54 — Data Residency + Region Pinning
- Per-company region; routing layer; per-region databases

### PHASE G — Scale-Out (Sessions 55-58)

#### Session 55 — Service Decomposition (AI service)
- Extract AI service to its own container; gRPC contract with API

#### Session 56 — Reporting Service Extraction
- PDF rendering moves to own service; separate scaling

#### Session 57 — Multi-Region Database Replication
- Read replicas in EU + APAC; routing layer reads from nearest

#### Session 58 — Workflow Engine (Temporal)
- Replace long Celery tasks with Temporal workflows; durable state; visibility UI

### PHASE H — Mobile + Voice (Sessions 59-60)

#### Session 59 — React Native Executive App (iOS + Android)
- Dashboards, alerts, AI chat (voice), approvals

#### Session 60 — Voice Input Everywhere (Whisper)
- Push-to-talk; transcribe to chat; voice-driven dashboard navigation

---

## 15. Top Priority Immediate Next Sessions

If we can only do 5 more sessions before "real" customer onboarding, do these in order:

1. **Session 22 — Observability Foundation** (Sentry + Prometheus + OTEL + structured logs with correlation IDs). Cannot debug prod without it.
2. **Session 23 — Audit Log Wiring**. Compliance unlock.
3. **Session 24 — Endpoint RBAC + Postgres RLS**. Closes the most dangerous security gap.
4. **Session 25 — Redis Cache Layer**. 10-100x perf on repeat queries; reduces Mongo load on free tier.
5. **Session 26 — Star Schema + dbt**. Unlocks period-over-period, drilldowns, cohorts. Every later session depends on it.

After these five, RetailFlux is **enterprise-ready foundationally**. Then Phase B (analytics depth) and Phase C (autonomous AI) are where the product becomes a category leader.

---

## 16. Long-Term World-Class Vision

In 18 months, **RetailFlux is the AI Chief Operating Officer of every fashion brand**, with these properties:

- **A single sentence answers any question.** "Why did revenue drop?" → 15-second response with decomposed drivers, narrative, and recommended actions.
- **Workflows execute themselves.** Stockouts trigger reorders. Anomalies trigger investigations. POs get drafted, routed, approved, and confirmed without humans typing.
- **Every executive gets a personalized briefing every morning.** 5 minutes to read. 100% relevant.
- **The product learns.** RAG-based pattern memory: "this looks like the December 2024 stockout — here's what worked."
- **Customers extend it.** Public API + webhooks + GraphQL + SDK + marketplace.
- **It runs on a per-user budget of <$5/month.** Aggressive caching, model-tier routing (Haiku for simple, Sonnet/Opus for complex), pre-aggregated cubes.
- **It is invisible.** Mobile-first. Voice-driven. Push notifications. The dashboard is a fallback, not the product.

**Competitive moat:**

- **Vertical depth** in fashion/retail (SKU lifecycle, season, returns, fit, supplier ecosystem)
- **Vertical-native AI agents** trained on fashion operations
- **Embedded automation** (workflow engine inside the analytics platform)
- **Composable integrations** (every channel, every ERP, every ad platform)
- **Honest AI** (numbers from code, prose from LLM; explainable forecasts)

**Three-year stretch goals:**

- Multi-vertical expansion (beauty, home goods, food & beverage)
- White-label OEM for enterprise SaaS partners
- "RetailFlux for Suppliers" — invert the platform to give vendors visibility
- Marketplace of pre-built workflows + agents

---

## How to Use This Document

Every future session begins by reading this file. To request a new session:

> *"Build out Session 27 from `docs/RETAILFLUX_V2_STRATEGY.md` (Period-Over-Period Comparison Engine)."*

The session description provides all required deliverables: objective, schema changes, APIs, frontend changes, tests, observability, RBAC, charts, complexity, dependencies, and risks.

Maintain this document. After each session:
- Mark the session ✅ Done in Section 14
- Append any architectural decisions to `docs/adr/`
- Update CLAUDE.md "Session History" with the standard entry format

---

*End of strategy document.*
