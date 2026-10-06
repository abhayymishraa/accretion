# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.0@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 /uv /bin/uv
ENV UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project --no-editable

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /app/var/projects && chown -R app:app /app/var
COPY --from=builder /app/.venv /app/.venv
COPY main.py request_timing.py plans.py config.py exceptions.py models.py ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY agent/ ./agent/
# Only each kit's stack.json (.dockerignore); kit code lives in the E2B templates.
COPY sandbox/kits/ ./sandbox/kits/
COPY auth/ ./auth/
COPY db/ ./db/
COPY health/ ./health/
COPY projects/ ./projects/
COPY runs/ ./runs/
COPY files/ ./files/
COPY previews/ ./previews/
COPY skills/ ./skills/
COPY connections/ ./connections/
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=6s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)"
# Open SSE streams never close by themselves, so uvicorn would wait out the whole graceful timeout on
# every deploy. Clients resume from Last-Event-ID, so cutting them after 5 s loses nothing. Lifespan
# shutdown (stop runs, pause sandboxes) still runs in full after it; compose stop_grace_period covers both.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--timeout-graceful-shutdown", "5"]
