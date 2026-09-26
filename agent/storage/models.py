"""ORM models owned by storage."""

from datetime import date

from sqlalchemy import (
    Date,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class StorageUsage(Base):
    __tablename__ = "storage_usage"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    uploaded: Mapped[int] = mapped_column(Integer, default=0)
    downloaded: Mapped[int] = mapped_column(Integer, default=0)
    # Daily operation caps; persistence.reserve_transfer reads them as f"{direction}_ops".
    uploaded_ops: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    downloaded_ops: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
