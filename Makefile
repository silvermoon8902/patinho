.PHONY: dev dev-down prod prod-down migrate migration test logs shell db-shell

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

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Testing
test:
	docker compose exec backend pytest

# Utilities
logs:
	docker compose logs -f

shell:
	docker compose exec backend bash

db-shell:
	docker compose exec db psql -U patinho
