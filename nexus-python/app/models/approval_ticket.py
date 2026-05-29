from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ApprovalTicket(Base):
    __tablename__ = "approval_ticket"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action_type: Mapped[str | None] = mapped_column(String(50))
    risk_level: Mapped[int | None] = mapped_column()
    context: Mapped[dict | None] = mapped_column(String(65535))
    status: Mapped[int] = mapped_column(default=0)
    approved_by: Mapped[int | None] = mapped_column(BigInteger)
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime)
    comment: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
