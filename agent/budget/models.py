"""ORM models owned by budgets."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SpendEntry(Base):
    """Content-free cost ledger; project/run deletion must not reset an allowance."""

    __tablename__ = "spend_entries"
    __table_args__ = (
        Index("ix_spend_user_window", "user_id", "ends_at", "starts_at"),
        CheckConstraint("amount_nanos >= 0 AND reserved_nanos >= 0", name="amounts_nonnegative"),
        CheckConstraint("ends_at >= starts_at", name="window_ordered"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # No run/chat foreign keys: deleting content must preserve incurred costs.
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default="reserved")
    reserved_nanos: Mapped[int] = mapped_column(BigInteger)
    amount_nanos: Mapped[int] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict[str, Any])
