from datetime import datetime
from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    Text,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class PushChannel(Base):
    __tablename__ = "push_channel"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(20))
    webhook: Mapped[str] = mapped_column(Text)
    secret: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class PushDelivery(Base):
    __tablename__ = "push_delivery"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    task_id: Mapped[str] = mapped_column(String(64))
    channel_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("task_id", "channel_id", name="uq_delivery_task_channel"),
    )
