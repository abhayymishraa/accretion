import ssl
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import MetaData
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

DATABASE_URL = settings.DATABASE_URL

database_url = make_url(DATABASE_URL).set(drivername="postgresql+psycopg")
connect_args = {
    "prepare_threshold": None,
    "connect_timeout": 10,
    "application_name": "webbuilder",
}
if database_url.query.get("sslmode") in {"require", "verify-ca", "verify-full"}:
    # Preserve libpq's channel_binding setting and verify the server certificate.
    connect_args["sslmode"] = "verify-full"
    connect_args["sslrootcert"] = ssl.get_default_verify_paths().cafile

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=2,
    max_overflow=2,
    pool_timeout=5,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args=connect_args,
)


# async_sessionmaker() creates a factory for new async sessions.
# Every time you call AsyncSessionLocal(), you get a new independent database session.
# class_=AsyncSession → ensures it returns async sessions (not sync ones).
# expire_on_commit=False → means objects remain “usable” even after commit.
# If it were True, SQLAlchemy would clear object state after a commit.

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Deterministic names for constraints and indexes. Without these, the database
# assigns its own, and a migration cannot refer to a constraint by name.
# Objects created before this was set keep the names the database gave them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Creates a database session.
    async with AsyncSessionLocal() as session:
        try:
            # “Pauses” the function and hands out the session object to whoever called get_db().
            yield session
            # When the route finishes using the session, Python returns control back to
            # get_db() — continuing after the yield line.
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbSession = Annotated[AsyncSession, Depends(get_db)]
