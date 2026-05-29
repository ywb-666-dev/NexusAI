from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

router = APIRouter()


@router.get("")
async def list_notifications(
    user_id: int,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """通知列表"""
    # TODO: Phase 7 实现分页查询
    return {"code": 200, "data": {"items": [], "total": 0}}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int, db: AsyncSession = Depends(get_db_session)
):
    """标记通知为已读"""
    # TODO: Phase 7 实现更新逻辑
    return {"code": 200, "data": {"message": "marked as read"}}
