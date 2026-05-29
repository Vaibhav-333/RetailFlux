from fastapi import APIRouter

from app.core.config import settings
from app.core.database import engine
from app.core.mongodb import get_mongo_db
from app.core.redis_client import get_redis
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    services: dict[str, ServiceStatus] = {}

    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        services["postgres"] = ServiceStatus(status="ok")
    except Exception as exc:
        services["postgres"] = ServiceStatus(status="error", detail=str(exc))

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        services["redis"] = ServiceStatus(status="ok")
    except Exception as exc:
        services["redis"] = ServiceStatus(status="error", detail=str(exc))

    # MongoDB
    try:
        db = get_mongo_db()
        await db.command("ping")
        services["mongodb"] = ServiceStatus(status="ok")
    except Exception as exc:
        services["mongodb"] = ServiceStatus(status="error", detail=str(exc))

    all_ok = all(s.status == "ok" for s in services.values())
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        environment=settings.ENVIRONMENT,
        services=services,
    )
