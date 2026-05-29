FROM python:3.11-slim AS base

WORKDIR /app

# System deps (psycopg2, prophet dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Development stage ────────────────────────────────────────────────────────
FROM base AS development

COPY requirements.dev.txt .
RUN pip install --no-cache-dir -r requirements.dev.txt

# Source code is mounted as a volume in dev
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── Production stage ─────────────────────────────────────────────────────────
FROM base AS production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
