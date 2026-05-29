from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "RetailFlux"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://retailflux:retailflux_dev@localhost:5432/retailflux"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # MongoDB
    MONGODB_URL: str = "mongodb://retailflux:retailflux_dev@localhost:27017/retailflux?authSource=admin"
    MONGODB_DATABASE: str = "retailflux"

    # MinIO / R2
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "retailflux"
    MINIO_SECRET_KEY: str = "retailflux_dev"
    MINIO_USE_SSL: bool = False
    MINIO_BUCKET_UPLOADS: str = "retailflux-uploads"

    # LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # Email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@retailflux.app"

    # Frontend URL (used for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    # Monitoring
    SENTRY_DSN: str = ""

    # Rate limiting
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "30/hour"
    RATE_LIMIT_AI: str = "60/hour"

    # Copilot / RAG
    COPILOT_DAILY_TOKEN_CAP: int = 100_000  # tokens per company per day
    COPILOT_EMBED_MODEL: str = "models/text-embedding-004"
    COPILOT_EMBED_DIM: int = 768

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
