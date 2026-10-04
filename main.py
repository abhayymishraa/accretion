"""The Accretion API application.

Composition only: middleware, lifespan and router registration. Endpoints live
in their domain's `router.py`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.run import bus
from agent.run.service import agent_service
from agent.storage.storage import StorageError
from auth.router import router as auth_router
from auth.router import users_router
from auth.social import configure_sessions, social_router
from config import settings
from db.base import engine
from files.router import router as files_router
from health.router import router as health_router
from previews.router import router as previews_router
from projects.router import router as projects_router
from request_timing import request_timing
from runs.router import router as runs_router
from skills.router import router as skills_router


@asynccontextmanager
async def lifespan(app):
    await agent_service.startup()
    try:
        yield
    finally:
        await agent_service.shutdown()
        await bus.client.aclose()
        await engine.dispose()


app = FastAPI(title="Accretion", lifespan=lifespan)
app.middleware("http")(request_timing)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Server-Timing"],
)

configure_sessions(app)


@app.exception_handler(StorageError)
async def storage_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


for domain_router in (
    auth_router,
    social_router,
    users_router,
    health_router,
    projects_router,
    runs_router,
    files_router,
    previews_router,
    skills_router,
):
    app.include_router(domain_router)
