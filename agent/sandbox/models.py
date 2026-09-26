"""ORM models owned by the sandbox group."""

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ProjectSecret(Base):
    """The project's generated .env values, encrypted (spec 3). Written into the sandbox at start."""

    __tablename__ = "project_secrets"
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
