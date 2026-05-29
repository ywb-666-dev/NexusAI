from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.dependencies import get_db_session
from app.models import Notification

router = APIRouter()


@router.get("")
async def list_notifications(
    user_id: int,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """通知列表（分页）"""
    offset = (page - 1) * size
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "user_id": item.user_id,
            "type": item.type,
            "title": item.title,
            "content": item.content,
            "is_read": item.is_read,
            "related_id": item.related_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {"code": 200, "data": {"items": data, "total": total, "page": page, "size": size}}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int, db: AsyncSession = Depends(get_db_session)
):
    """标记通知为已读"""
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(is_read=1)
    )
    await db.commit()
    return {"code": 200, "data": {"message": "marked as read"}}
