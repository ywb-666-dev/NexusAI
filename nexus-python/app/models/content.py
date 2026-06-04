from sqlalchemy import BigInteger, String, DateTime, CHAR, JSON, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Content(Base):
    __tablename__ = "content"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    subscription_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(String(2000))
    content_body: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[DateTime | None] = mapped_column(DateTime)
    fetched_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    vector_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[int] = mapped_column(default=1)
    is_duplicate: Mapped[int] = mapped_column(default=0)
    duplicate_of: Mapped[str | None] = mapped_column(CHAR(36))
    related_contents: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_content_subscription", "subscription_id"),
        Index("idx_content_hash", "content_hash"),
        Index("idx_content_platform_duplicate", "source_platform", "is_duplicate"),
    )
