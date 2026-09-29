.PHONY: backend frontend template-build format format-check lint typecheck check

backend:
	uv run --env-file .env alembic upgrade head
	uv run --env-file .env python -m agent.storage.init_storage
	uv run --env-file .env uvicorn main:app --reload --port 8000

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