from sqlalchemy import BigInteger, String, DateTime, JSON, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    keywords: Mapped[dict | None] = mapped_column(JSON)
    source_platforms: Mapped[str | None] = mapped_column(String(500))
    match_mode: Mapped[int] = mapped_column(default=1)
    trigger_conditions: Mapped[dict | None] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(default=2)
    status: Mapped[int] = mapped_column(default=1)
    cron_expression: Mapped[str | None] = mapped_column(String(100))
    last_run_at: Mapped[DateTime | None] = mapped_column(DateTime)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_subscription_user_status", "user_id", "status"),
    )
