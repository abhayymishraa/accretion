"""ORM models owned by authentication."""

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)
    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(24), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
