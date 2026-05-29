# RetailFlux — start the FastAPI dev server locally (no Docker required)
# Prerequisites: PostgreSQL 16 service running (installed via winget)
# Usage: .\start-api.ps1

Set-Location "$PSScriptRoot\apps\api"

$env:DATABASE_URL   = "postgresql+asyncpg://retailflux:retailflux_dev@localhost:5432/retailflux"
$env:REDIS_URL      = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "redis://localhost:6379/1"
$env:MONGODB_URL    = "mongodb://localhost:27017/retailflux"
$env:MONGODB_DATABASE = "retailflux"
$env:SECRET_KEY     = "dev-secret-key-change-before-production"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:MINIO_ACCESS_KEY = "retailflux"
$env:MINIO_SECRET_KEY = "retailflux_dev"
$env:ENVIRONMENT    = "development"
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"   # get from https://aistudio.google.com
$env:GEMINI_MODEL   = "gemini-2.5-flash-lite"
$env:GROQ_API_KEY   = ""   # Or Groq key as fallback
$env:SENTRY_DSN     = ""
Write-Host "Starting RetailFlux API on http://localhost:8000 ..."
Write-Host "Docs: http://localhost:8000/docs"
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload