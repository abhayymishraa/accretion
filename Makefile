.PHONY: redis backend frontend template-build format format-check lint typecheck check

redis:
	redis-cli -h 127.0.0.1 ping >/dev/null 2>&1 || docker start accretion-redis 2>/dev/null || docker run -d --name accretion-redis -p 127.0.0.1:6379:6379 redis:7-alpine --save "" --appendonly no

backend: redis
	uv run --env-file .env alembic upgrade head
	uv run --env-file .env python -m agent.storage.init_storage
	uv run --env-file .env uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 5

frontend:
	npm --prefix frontend run dev -- --port 3000

format:
	uv run ruff format .
	uv run ruff check . --fix

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

# The gate. Mirrors the frontend's format:check + lint.
check: format-check lint typecheck

# Builds the one sandbox template (E2B_API_KEY in .env) and moves TAG (default production) to it.
template-build:
	uv run --env-file .env python sandbox/templates.py $(or $(TAG),production)