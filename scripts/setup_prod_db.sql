-- Run this ONCE in the Neon console (or via psql) before the first
-- `alembic upgrade head`.  Both extensions are idempotent — safe to re-run.

-- pgvector: required for the AI Copilot RAG pipeline (app/core/embeddings.py).
-- Neon free tier ships with the vector extension pre-installed.
CREATE EXTENSION IF NOT EXISTS vector;

-- uuid-ossp: provides gen_random_uuid() used by several Alembic migrations.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
