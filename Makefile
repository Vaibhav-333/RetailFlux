.PHONY: up down logs build test migrate seed lint typecheck clean help

# ─── Dev lifecycle ──────────────────────────────────────────────────────────
up:
	docker-compose up --build -d
	@echo "✓ Services started"
	@echo "  API:      http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  UI:       http://localhost:3000"
	@echo "  MinIO:    http://localhost:9001  (retailflux / retailflux_dev)"

down:
	docker-compose down

restart:
	docker-compose restart api worker web

logs:
	docker-compose logs -f api worker

logs-all:
	docker-compose logs -f

build:
	docker-compose build --no-cache

# ─── Database ───────────────────────────────────────────────────────────────
migrate:
	docker-compose exec api alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	docker-compose exec api alembic revision --autogenerate -m "$$name"

migrate-down:
	docker-compose exec api alembic downgrade -1

# ─── Testing ────────────────────────────────────────────────────────────────
test:
	docker-compose exec api pytest tests/ -v --tb=short

test-cov:
	docker-compose exec api pytest tests/ -v --cov=app --cov-report=term-missing

# ─── Code quality ───────────────────────────────────────────────────────────
lint:
	docker-compose exec api ruff check app/ tests/
	docker-compose exec api ruff format --check app/ tests/

typecheck:
	docker-compose exec api mypy app/
	cd apps/web && npx tsc --noEmit

format:
	docker-compose exec api ruff format app/ tests/

# ─── Seed data ──────────────────────────────────────────────────────────────
seed:
	docker-compose exec api python scripts/seed_demo.py

# ─── Utilities ──────────────────────────────────────────────────────────────
shell-api:
	docker-compose exec api bash

shell-db:
	docker-compose exec postgres psql -U retailflux -d retailflux

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

install-web:
	cd apps/web && npm install

help:
	@echo ""
	@echo "RetailFlux Dev Commands"
	@echo "────────────────────────────────────────"
	@echo "  make up           Start all services"
	@echo "  make down         Stop all services"
	@echo "  make logs         Follow api + worker logs"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make test         Run pytest"
	@echo "  make test-cov     Run pytest with coverage"
	@echo "  make lint         Run ruff linter"
	@echo "  make typecheck    Run mypy + tsc"
	@echo "  make seed         Seed demo data"
	@echo "  make shell-api    Bash into API container"
	@echo "  make shell-db     psql into Postgres"
	@echo "  make clean        Remove containers + volumes"
	@echo ""
