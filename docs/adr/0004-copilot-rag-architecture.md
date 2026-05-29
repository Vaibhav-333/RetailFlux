# ADR-0004: Copilot RAG Architecture — pgvector on Neon over External Vector DB

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

The Executive AI Copilot (Session 34) requires Retrieval-Augmented Generation (RAG) to ground its answers in the company's actual data rather than relying on the LLM's general knowledge. RAG requires:

1. **A vector store** — indexed embeddings of company-specific content (AI insights history, task descriptions, SKU master data, audit summaries, comments).
2. **An embedding model** — converts query text + documents into vectors for similarity search.
3. **A retrieval layer** — queries the vector store at inference time and injects the top-k matches into the system prompt.

The central infrastructure decision: **where to store and query the embeddings?**

RetailFlux has a hard constraint: **zero paid infrastructure**. The v3 stack must run entirely on free tiers. This rules out Pinecone ($0 on Starter with significant query limits), Weaviate Cloud (free tier has 14-day sandbox), and managed Chroma (paid).

---

## Decision

Use **pgvector on Neon** (the existing free-tier Postgres) as the vector store. Embeddings are generated via Gemini `text-embedding-004` (free tier, 1,536 dimensions, 1,500 requests/min).

### Architecture

```
User query
    ↓
Gemini text-embedding-004 → query vector (1536-dim float32)
    ↓
pgvector cosine similarity search on app.embeddings table
  (ivfflat index, lists=100, probes=10)
    ↓
Top-k documents (k=4) injected into system prompt
    ↓
Gemini 2.5 Flash Lite → grounded answer → SSE stream
```

### Schema

```sql
CREATE TABLE app.embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL,         -- tenant isolation
  source_type TEXT NOT NULL,         -- 'insight' | 'task' | 'sku' | 'comment' | 'audit'
  source_id TEXT NOT NULL,
  content TEXT NOT NULL,             -- original text (for context injection)
  embedding vector(1536),            -- pgvector column; JSONB fallback on local Windows PG
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(company_id, source_type, source_id)
);
CREATE INDEX ON app.embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Graceful degradation
On environments without the pgvector extension (local Windows PostgreSQL, CI), the `embedding` column falls back to `JSONB` and the retrieval layer uses keyword matching instead of cosine similarity. This is enforced by a `PGVECTOR_AVAILABLE` flag in `app/core/embeddings.py` that is set at startup by attempting a `vector` type probe.

### Tenant isolation
Every embedding row has `company_id`. The retrieval query always includes `WHERE company_id = :company_id` as a mandatory filter before the cosine similarity sort. There is no cross-tenant leakage path.

---

## Alternatives Considered

### Pinecone (free Starter tier)
Pinecone's Starter tier allows 1 index, 100K vectors, and 100K queries/month — enough for a demo. The managed service handles scaling, indexing, and replication.

**Rejected** because:
- The Starter tier was restructured during v3 development; limits have changed repeatedly.
- Adding an external vector service introduces a new failure domain. If Pinecone is unavailable, the Copilot is unavailable.
- RetailFlux's data (insights, tasks, SKUs, comments) already lives in Postgres. Shipping vectors to an external service doubles the write path and creates sync complexity.
- Free tier limits (100K vectors) could be exceeded by a moderately active company within months.

### Chroma (self-hosted)
Chroma is an open-source vector DB that runs in-process or as a local server. Zero cost, no external dependency.

**Rejected** because:
- Self-hosting Chroma on Render's free tier (512MB RAM) would consume memory otherwise allocated to the FastAPI workers.
- Chroma's persistence on Render is ephemeral (no persistent disk on free tier); the index would rebuild on every deploy.
- Adding Chroma as a sidecar service on Render would require a paid plan.

### Qdrant Cloud (free tier)
Qdrant offers a free forever 1GB cluster. High performance, excellent Python client.

**Rejected** for the same co-location reason as Pinecone: data already in Postgres; adding a third persistence layer increases operational complexity with no benefit at this scale.

### In-memory embeddings (numpy cosine similarity)
Load all embeddings into memory at startup, do numpy cosine similarity on every query. Zero infrastructure, maximum speed for small catalogs.

**Rejected** because it doesn't survive process restarts (Render restarts workers on inactivity), and memory usage scales linearly with embedding count (50K embeddings × 1536 dims × 4 bytes ≈ 300MB — close to the 512MB limit).

---

## Consequences

**Positive:**
- **Zero additional infrastructure cost** — Neon free tier (0.5GB storage, serverless compute) is already in the stack for the main Postgres data.
- **Transactional consistency** — embedding inserts happen in the same transaction as the source data write; no eventual consistency lag.
- **Co-located queries** — the retrieval SQL runs on the same Postgres connection pool as all other queries; no extra network hop.
- **Neon free tier pgvector support confirmed** — `vector` extension is available on Neon's free tier as of migration 0010.

**Negative / Trade-offs:**
- **50K embedding limit** — Neon free tier caps at 0.5GB. At 1536 dims × float32 (6KB/embedding), ~80K embeddings fit before hitting storage limits. A moderately active company could hit this within 6–12 months of heavy use.
- **ivfflat vs. hnsw** — `ivfflat` requires `VACUUM ANALYZE` after bulk inserts to update the index. `hnsw` (exact ANN, no rebuild needed) is more appropriate but requires pgvector ≥ 0.5.0 which is available on Neon. **Recommendation:** migrate to `hnsw` in v3.x.
- **Embedding latency** — Gemini `text-embedding-004` has ~100–200ms latency per call. The retrieval step adds this to the copilot first-token time. Mitigated by embedding at write time (Celery backfill job), so queries are always against pre-computed vectors.
- **Local dev degradation** — Windows PostgreSQL without pgvector falls back to keyword matching, which gives lower retrieval quality during local development. Developers can install pgvector for Windows or use Docker.

**Follow-ons:**
- v3.x: migrate ivfflat index to hnsw for better recall without rebuild overhead.
- v3.x: add embedding count monitor to Observability dashboard with alert at 70% capacity.
- v3.x: implement embedding TTL — expire embeddings for source documents deleted > 90 days ago.
- v3.x: multi-vector retrieval — embed query as both a question and a keyword set, merge results.
