"""Readiness checks."""

import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from health.exceptions import DatabaseUnavailable
from health.schemas import Readiness


async def readiness(db: AsyncSession) -> Readiness:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=12)
    except (SQLAlchemyError, OSError):  # OSError covers TimeoutError and a refused connection.
        raise DatabaseUnavailable from None
    return Readiness(status="ready")
