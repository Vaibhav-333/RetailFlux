from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: Optional[AsyncIOMotorClient] = None  # type: ignore[type-arg]


def get_mongo_client() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    return get_mongo_client()[settings.MONGODB_DATABASE]


async def close_mongo() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


# Collection accessors — add more as needed
def raw_uploads_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["raw_uploads"]


def ge_reports_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["ge_reports"]


def ai_chat_sessions_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["ai_chat_sessions"]


def forecast_runs_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["forecast_runs"]


def productivity_daily_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["productivity_daily"]


def task_workload_snapshots_col():  # type: ignore[no-untyped-def]
    return get_mongo_db()["task_workload_snapshots"]
