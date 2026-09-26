"""Alembic environment.

The URL and the metadata both come from the application, so a migration can
never run against a different database than the app, or against a stale copy
of the schema.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import agent.budget.models
import agent.context.models
import agent.sandbox.models
import agent.storage.models
import auth.models
import db.models
from alembic import context
from db.base import Base, database_url

config = context.config
config.set_main_option("sqlalchemy.url", database_url.render_as_string(hide_password=False))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importing a module registers its tables; one missing here is a table autogenerate will drop.
MODEL_MODULES = (
    agent.budget.models,
    agent.context.models,
    agent.sandbox.models,
    agent.storage.models,
    auth.models,
    db.models,
)

target_metadata = Base.metadata

# Objects that exist by migration but not in the ORM metadata. Without this,
# autogenerate proposes dropping them on every run -- including the partial
# full-text index, which no model can express.
MIGRATION_OWNED_INDEXES = {"ix_messages_context_order", "ix_messages_context_search"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "index" and name in MIGRATION_OWNED_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
