from datetime import datetime
from sqlalchemy import String, BigInteger, Integer, JSON, Text, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class RadioTurn(Base):
    __tablename__ = "radio_turn"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    briefing_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        Index(
            "idx_radio_history", "user_id", "briefing_id", "event_index", "created_at"
        ),
    )


class RadioFollow(Base):
    __tablename__ = "radio_follow"
    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    briefing_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
