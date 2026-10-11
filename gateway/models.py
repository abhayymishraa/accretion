"""ORM models owned by the gateway domain."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AppToken(Base):
    """A project's key to the platform services (email, sign-in). The app holds it in .env.json; the gateway
    finds the project by its hash. Deleting the project deletes the key."""

    __tablename__ = "app_tokens"
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Sealed plaintext, so every sandbox start writes the same key into .env.json.
    secret: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
