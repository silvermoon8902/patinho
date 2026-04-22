.PHONY: help dev dev-down prod prod-down migrate migration seed test test-integration logs shell db-shell psql backup restore-verify lint format

.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Production
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Database
migrate:
	docker compose exec backend alembic upgrade head

migration: ## Create a new migration (usage: make migration msg="desc")
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

seed: ## Seed dev DB with demo users/leagues/bets
	docker compose exec backend python -m app.scripts.seed

# Testing
test: ## Run full pytest suite inside backend container
	docker compose exec backend pytest

test-integration: ## Run integration tests against $$PATINHO_URL
	@PATINHO_URL="$${PATINHO_URL:-http://localhost}" \
	  bash -c "cd backend && pytest tests/test_league_access.py tests/test_compliance.py tests/test_tournament_scoring.py -v"

lint: ## Run ruff + eslint
	docker compose exec backend ruff check app
	cd frontend && npm run lint || true

format: ## Auto-fix formatting (ruff)
	docker compose exec backend ruff check --fix app

backup: ## Run an ad-hoc DB backup (requires ops/pg_backup.sh)
	./ops/pg_backup.sh

restore-verify: ## Verify the latest backup restores cleanly
	./ops/pg_restore_verify.sh

# Utilities
logs: ## Tail all service logs
	docker compose logs -f

shell: ## Open a shell in the backend container
	docker compose exec backend bash

db-shell: ## Open psql in the db container
	docker compose exec db psql -U patinho

psql: db-shell ## Alias for db-shell
