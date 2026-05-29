# RetailFlux API — entry point
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging_setup import configure_logging, logger
from app.core.audit_middleware import AuditMiddleware
from app.core.metrics_middleware import RequestMetricsMiddleware
from app.core.middleware import RequestIDMiddleware
from app.core.mongodb import close_mongo
from app.core.redis_client import close_redis

# Optional Prometheus instrumentation (graceful no-op if package not installed)
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instrumentator

    _PROMETHEUS = True
except ImportError:  # pragma: no cover
    _PROMETHEUS = False

# Init structured logging
configure_logging()

# Init Sentry (no-op when DSN is empty)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("RetailFlux API starting", environment=settings.ENVIRONMENT)
    yield
    logger.info("RetailFlux API shutting down")
    await close_redis()
    await close_mongo()


app = FastAPI(
    title="RetailFlux API",
    description="AI-powered business analytics & procurement intelligence for fashion companies.",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────
# Middlewares execute in reverse registration order; RequestID → Metrics → Audit.
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestMetricsMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, method=request.method, error=str(exc))
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
async def root_health() -> dict[str, str]:
    """Quick liveness probe (no DB checks) for load balancer / Render health checks."""
    return {"status": "ok", "service": "retailflux-api"}


# ─── Prometheus metrics (optional) ────────────────────────────────────────────
if _PROMETHEUS:
    _Instrumentator().instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["observability"],
    )
