"""RAG retrieval — searches pgvector embeddings and formats context for the LLM."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import search_similar


async def retrieve_context(
    db: AsyncSession,
    *,
    query: str,
    company_id: str,
    entity_types: list[str] | None = None,
    n: int = 5,
) -> tuple[str, list[dict[str, Any]]]:
    """Return a formatted context string + raw sources list.

    *entity_types* can filter to e.g. ["task", "insight", "sku"]; None = all types.
    """
    hits = await search_similar(
        db,
        query_text=query,
        company_id=company_id,
        entity_types=entity_types,
        limit=n,
    )

    if not hits:
        return "", []

    lines = ["[Relevant context from your company data]"]
    for hit in hits:
        label = f"{hit['entity_type'].upper()} · {hit['entity_id']}"
        lines.append(f"\n--- {label} ---\n{hit['content'][:600]}")

    return "\n".join(lines), hits
