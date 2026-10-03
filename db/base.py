import ssl
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
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
    # No liveness test on checkout: it is one database round trip on every request. A connection
    # dropped by a database or pooler restart fails one request and SQLAlchemy then replaces the
    # pool; pool_recycle retires idle connections before the pooler or a NAT drops them.
    pool_pre_ping=False,
    # A chat page opens about six requests at once, beside the workers' own queries. Connections
    # beyond pool_size are closed when returned, so each burst past it paid a new connection
    # (~0.9 s measured in production) on every page load. Kept connections cover the burst.
    pool_size=10,
    max_overflow=5,
    pool_timeout=5,
    # Reconnecting costs a TLS handshake to the database region (~0.85 s measured in production),
    # paid by whichever request takes the expired connection. 300 s put that on the first request
    # after every few idle minutes.
    pool_recycle=1800,
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


# Sessions for work that never writes: no transaction, so no BEGIN and COMMIT round trips.
ReadSessionLocal = async_sessionmaker(
    engine.execution_options(isolation_level="AUTOCOMMIT"), class_=AsyncSession, expire_on_commit=False
)


def autocommit(request: Request) -> None:
    """Route dependency for routes that never write, or write in exactly one statement, which
    commits by itself: get_db then hands out a ReadSessionLocal session. A route with two writes
    that must succeed together keeps the transaction. Route dependencies resolve before
    parameters, so get_db sees the mark."""
    request.state.autocommit = True


Autocommit = Depends(autocommit)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # Creates a database session.
    factory = ReadSessionLocal if getattr(request.state, "autocommit", False) else AsyncSessionLocal
    async with factory() as session:
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
