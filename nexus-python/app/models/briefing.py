"""Private, durable cross-subscription intelligence briefs."""

from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, JSON, Text, Integer, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Briefing(Base):
    __tablename__ = "briefing"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    active_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    schedule_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    hours: Mapped[int] = mapped_column(Integer, default=24)
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    report: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_briefing_user_created", "user_id", "created_at"),)


class BriefingPreference(Base):
    __tablename__ = "briefing_preference"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    enabled: Mapped[int] = mapped_column(Integer, default=0)
    push_enabled: Mapped[int] = mapped_column(Integer, default=0)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime)
