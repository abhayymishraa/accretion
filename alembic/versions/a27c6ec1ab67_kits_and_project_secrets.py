"""kits and project secrets: chats.kit and project_secrets

Revision ID: a27c6ec1ab67
Revises: 2e120c03f7df
Create Date: 2026-09-26

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a27c6ec1ab67"
down_revision: str | Sequence[str] | None = "2e120c03f7df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Spec 8 kits and spec 3 ProjectSecret. Only the column add is guarded, like dc1cc61a22ce:
    it alters an existing table. The new table needs no guard (repo migration rule).
    Projects from before kits are not carried over; the default is only there to fill the column."""
    op.create_table(
        "project_secrets",
        sa.Column("chat_id", sa.String(length=36), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chat_id"], ["chats.id"], name=op.f("fk_project_secrets_chat_id_chats"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chat_id", name=op.f("pk_project_secrets")),
    )
    inspector = sa.inspect(op.get_bind())
    if not any(c["name"] == "kit" for c in inspector.get_columns("chats")):
        op.add_column(
            "chats", sa.Column("kit", sa.String(length=64), server_default="vite-fastapi-postgres", nullable=False)
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if any(c["name"] == "kit" for c in inspector.get_columns("chats")):
        op.drop_column("chats", "kit")
    op.drop_table("project_secrets")
