"""Liveness and readiness probes."""

from fastapi import APIRouter

from db.base import Autocommit, DbSession
from health import service
from health.schemas import Liveness, Readiness

router = APIRouter()


@router.get("/")
async def get_health() -> Liveness:
    return Liveness(message="Welcome", status="Healthy")


@router.get("/health/ready", dependencies=[Autocommit])
async def get_readiness(db: DbSession) -> Readiness:
    return await service.readiness(db)
