"""Copilot RAG: conversations, messages, embeddings, usage tracking (Session 34).

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-24
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Conversation threads (one per user session or persistent thread)
    op.execute("""
        CREATE TABLE app.conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES app.companies(id),
            user_id UUID NOT NULL REFERENCES app.users(id),
            title TEXT,
            summary TEXT,
            message_count INT NOT NULL DEFAULT 0,
            total_tokens INT NOT NULL DEFAULT 0,
            last_message_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_conversations_user_id ON app.conversations(user_id)")
    op.execute("CREATE INDEX ix_conversations_company_id ON app.conversations(company_id)")
    op.execute("CREATE INDEX ix_conversations_last_message_at ON app.conversations(last_message_at DESC)")

    # Messages within a conversation
    op.execute("""
        CREATE TABLE app.conversation_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES app.conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            tool_used TEXT,
            rag_sources JSONB NOT NULL DEFAULT '[]',
            proposed_actions JSONB NOT NULL DEFAULT '[]',
            token_estimate INT NOT NULL DEFAULT 0,
            provider TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_conv_messages_conv_id ON app.conversation_messages(conversation_id, created_at)"
    )

    # Embeddings store — uses vector(768) when pgvector is installed, JSONB fallback otherwise.
    # RAG similarity search only works in production (where pgvector is available).
    op.execute("""
        DO $$
        DECLARE
            has_vector BOOLEAN := FALSE;
        BEGIN
            BEGIN
                CREATE EXTENSION IF NOT EXISTS vector;
                has_vector := TRUE;
            EXCEPTION WHEN OTHERS THEN
                has_vector := FALSE;
            END;

            IF has_vector THEN
                CREATE TABLE app.embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID NOT NULL REFERENCES app.companies(id),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (company_id, entity_type, entity_id)
                );
                CREATE INDEX ix_embeddings_company_type ON app.embeddings(company_id, entity_type);
                CREATE INDEX ix_embeddings_vector ON app.embeddings
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
            ELSE
                CREATE TABLE app.embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID NOT NULL REFERENCES app.companies(id),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding JSONB,
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (company_id, entity_type, entity_id)
                );
                CREATE INDEX ix_embeddings_company_type ON app.embeddings(company_id, entity_type);
            END IF;
        END $$;
    """)

    # Daily token usage per company (for cap enforcement)
    op.execute("""
        CREATE TABLE app.copilot_usage_daily (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES app.companies(id),
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            tokens_used INT NOT NULL DEFAULT 0,
            request_count INT NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (company_id, date)
        )
    """)
    op.execute(
        "CREATE INDEX ix_copilot_usage_company_date ON app.copilot_usage_daily(company_id, date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_copilot_usage_company_date")
    op.execute("DROP TABLE IF EXISTS app.copilot_usage_daily")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_company_type")
    op.execute("DROP TABLE IF EXISTS app.embeddings")
    op.execute("DROP INDEX IF EXISTS app.ix_conv_messages_conv_id")
    op.execute("DROP TABLE IF EXISTS app.conversation_messages")
    op.execute("DROP INDEX IF EXISTS app.ix_conversations_last_message_at")
    op.execute("DROP INDEX IF EXISTS app.ix_conversations_company_id")
    op.execute("DROP INDEX IF EXISTS app.ix_conversations_user_id")
    op.execute("DROP TABLE IF EXISTS app.conversations")
