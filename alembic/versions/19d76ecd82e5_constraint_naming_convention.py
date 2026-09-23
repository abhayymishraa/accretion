"""constraint naming convention

Revision ID: 19d76ecd82e5
Revises: f362c4be2175
Create Date: 2026-09-23 17:41:47.109687

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19d76ecd82e5"
down_revision: str | Sequence[str] | None = "f362c4be2175"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (table, legacy name, convention name, columns)
RENAMES = [
    ("auth_identities", "auth_identities_user_id_provider_key", "uq_auth_identities_user_id", ["user_id", "provider"]),
    ("project_revisions", "project_revisions_object_key_key", "uq_project_revisions_object_key", ["object_key"]),
    ("sandbox_runtimes", "sandbox_runtimes_operation_id_key", "uq_sandbox_runtimes_operation_id", ["operation_id"]),
    ("sandbox_runtimes", "sandbox_runtimes_sandbox_id_key", "uq_sandbox_runtimes_sandbox_id", ["sandbox_id"]),
]


def _unique_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_unique_constraints(table) if c["name"]}


def _rename(table: str, frm: str, to: str, columns: list[str]) -> None:
    """Rename only if it is actually needed.

    Two kinds of database reach this migration: one created before Alembic,
    whose constraints carry names Postgres chose, and one built from the
    baseline, where they already follow the convention. An unguarded
    drop_constraint fails on the second.
    """
    present = _unique_names(table)
    if frm in present:
        op.drop_constraint(frm, table, type_="unique")
    if to not in present:
        op.create_unique_constraint(to, table, columns)


def upgrade() -> None:
    """Move constraint names onto the convention set on Base.metadata.

    Nothing about the data or the enforced rules changes; only the names, so
    a later migration can refer to a constraint by name.
    """
    for table, frm, to, columns in RENAMES:
        _rename(table, frm, to, columns)


def downgrade() -> None:
    """Restore the database-assigned names."""
    for table, frm, to, columns in RENAMES:
        _rename(table, to, frm, columns)
