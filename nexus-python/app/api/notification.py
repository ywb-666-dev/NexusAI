from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, update
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models import Notification

router = APIRouter()


@router.get("")
async def notifications(request: Request):
    async with get_session_factory()() as db:
        rows = (
            (
                await db.execute(
                    select(Notification)
                    .where(Notification.user_id == current_user(request)["id"])
                    .order_by(Notification.created_at.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        return {
            "code": 200,
            "data": {
                "items": [
                    {
                        "id": n.id,
                        "title": n.title,
                        "content": n.content,
                        "is_read": n.is_read,
                    }
                    for n in rows
                ]
            },
        }


@router.post("/{notification_id}/read")
async def mark(notification_id: int, request: Request):
    async with get_session_factory()() as db:
        n = await db.get(Notification, notification_id)
        if not n or n.user_id != current_user(request)["id"]:
            raise HTTPException(404, "通知不存在")
        n.is_read = 1
        await db.commit()
    return {"code": 200}
