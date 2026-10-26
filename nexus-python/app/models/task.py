"""Durable collection tasks; Redis is only a projection of this state."""

from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, JSON, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AgentTask(Base):
    __tablename__ = "agent_task"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subscription_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="queued")
    active_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    nodes: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (Index("idx_task_user_created", "user_id", "created_at"),)
