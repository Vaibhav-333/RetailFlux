from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str  # "ok" | "error"
    detail: str = ""


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str = "1.0.0"
    environment: str
    services: dict[str, ServiceStatus]
