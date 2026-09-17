"""Create the initial WebBuilder schema without deleting existing tables or data."""

import asyncio

from sqlalchemy import text

from db.base import Base, engine
import db.models  # Register the application's tables with Base.metadata.


async def migrate():
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT pg_advisory_xact_lock(73142026)"))
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR(280) NOT NULL DEFAULT ''"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            for column in ('latest_saved_revision_id', 'latest_verified_revision_id'):
                await connection.execute(text(f'ALTER TABLE chats ADD COLUMN IF NOT EXISTS {column} VARCHAR(36)'))
            await connection.execute(text('ALTER TABLE runs ADD COLUMN IF NOT EXISTS log_key VARCHAR(512)'))
            await connection.execute(text('ALTER TABLE runs ADD COLUMN IF NOT EXISTS log_sha256 VARCHAR(64)'))
            await connection.execute(text("ALTER TABLE runs ADD COLUMN IF NOT EXISTS workflow JSON NOT NULL DEFAULT '{}'"))
            await connection.execute(text('ALTER TABLE sandbox_runtimes ADD COLUMN IF NOT EXISTS spend_id VARCHAR(36)'))
            for column in ('uploaded_ops', 'downloaded_ops'):
                await connection.execute(text(f'ALTER TABLE storage_usage ADD COLUMN IF NOT EXISTS {column} INTEGER NOT NULL DEFAULT 0'))
            await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_context_search ON messages USING gin (to_tsvector('simple', content)) WHERE role IN ('user', 'assistant')"))
            await connection.execute(text('CREATE INDEX IF NOT EXISTS ix_messages_context_order ON messages (chat_id, created_at, id)'))
            # Keep old JSON for rollback until the run's diagnostic archive is verified.
            # Archived/pruned runs must never have old events resurrected by a later migration.
            await connection.execute(text('''
                INSERT INTO run_events (run_id, sequence, payload, created_at)
                SELECT r.id, e.ordinality, e.value, r.created_at
                FROM runs r, json_array_elements(CASE WHEN json_typeof(r.events) = 'array'
                    THEN r.events ELSE '[]'::json END) WITH ORDINALITY e(value, ordinality)
                WHERE r.log_sha256 IS NULL
                ON CONFLICT (run_id, sequence) DO NOTHING
            '''))
        print("WebBuilder initial schema is ready")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
