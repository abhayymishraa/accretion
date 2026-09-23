"""Liveness and readiness probes."""

import asyncio

from fastapi import APIRouter
from sqlalchemy import text

from db.base import DbSession
from health.exceptions import DatabaseUnavailable
from health.schemas import Liveness, Readiness

router = APIRouter()


@router.get("/")
async def get_health() -> Liveness:
    return Liveness(message="Welcome", status="Healthy")


@router.get("/health/ready")
async def get_readiness(db: DbSession) -> Readiness:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=12)
    except Exception:
        raise DatabaseUnavailable from None
    return Readiness(status="ready")
