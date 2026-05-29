from sqlalchemy import BigInteger, String, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(String(65535))
    is_read: Mapped[int] = mapped_column(default=0)
    related_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
    )
