from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models.delivery import PushChannel, PushDelivery
from app.services.push import validate_webhook, send
from app.models.task import AgentTask

router = APIRouter()


class ChannelInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str
    webhook: str = Field(max_length=2000)
    secret: str = Field(default="", max_length=500)
    enabled: bool = True


@router.get("/channels")
async def channels(request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        rows = (
            (
                await db.execute(
                    select(PushChannel).where(PushChannel.user_id == user["id"])
                )
            )
            .scalars()
            .all()
        )
        return {
            "code": 200,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "provider": r.provider,
                    "enabled": bool(r.enabled),
                }
                for r in rows
            ],
        }


@router.post("/channels")
async def create(body: ChannelInput, request: Request):
    user = current_user(request)
    try:
        validate_webhook(body.provider, body.webhook)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    async with get_session_factory()() as db:
        channel = PushChannel(user_id=user["id"], **body.model_dump())
        db.add(channel)
        await db.commit()
    return {"code": 200, "data": {"id": channel.id}}


@router.delete("/channels/{channel_id}")
async def delete(channel_id: int, request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        channel = await db.get(PushChannel, channel_id)
        if not channel or channel.user_id != user["id"]:
            raise HTTPException(404, "推送渠道不存在")
        await db.delete(channel)
        await db.commit()
    return {"code": 200}


@router.post("/channels/{channel_id}/test")
async def test(channel_id: int, request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        channel = await db.get(PushChannel, channel_id)
        if not channel or channel.user_id != user["id"]:
            raise HTTPException(404, "推送渠道不存在")
    try:
        await send(channel, "这是一条由你手动发起的连接测试消息。")
    except Exception:
        raise HTTPException(502, "发送失败，请检查机器人地址、签名和网络")
    return {"code": 200}


@router.get("/deliveries")
async def deliveries(request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        rows = (
            (
                await db.execute(
                    select(PushDelivery)
                    .where(PushDelivery.user_id == user["id"])
                    .order_by(PushDelivery.id.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        return {
            "code": 200,
            "data": [
                {
                    "id": r.id,
                    "task_id": r.task_id,
                    "channel_id": r.channel_id,
                    "status": r.status,
                    "attempts": r.attempts,
                    "error": r.error,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
        }


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(delivery_id: int, request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        delivery = (
            await db.execute(
                select(PushDelivery)
                .where(PushDelivery.id == delivery_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not delivery or delivery.user_id != user["id"]:
            raise HTTPException(404, "投递记录不存在")
        if delivery.status != "failed":
            raise HTTPException(409, "仅失败的投递可重试")
        channel = await db.get(PushChannel, delivery.channel_id)
        if not channel or channel.user_id != user["id"] or not channel.enabled:
            raise HTTPException(409, "渠道已删除或停用")
        if delivery.task_id.startswith("briefing:"):
            from app.models.briefing import Briefing
            from app.services.briefing import report_text

            brief = await db.get(Briefing, delivery.task_id.removeprefix("briefing:"))
            report = (
                report_text(brief)
                if brief and brief.user_id == user["id"] and brief.status == "ready"
                else None
            )
        else:
            task = await db.get(AgentTask, delivery.task_id)
            report = (
                (task.state or {}).get("curator", {}).get("report")
                if task and task.user_id == user["id"]
                else None
            )
        if not report:
            raise HTTPException(409, "任务简报尚未生成")
        delivery.attempts += 1
        try:
            await send(channel, report)
            delivery.status, delivery.error = "sent", None
        except Exception:
            delivery.status, delivery.error = (
                "failed",
                "投递失败，请检查机器人配置和网络",
            )
        await db.commit()
        return {
            "code": 200,
            "data": {"status": delivery.status, "error": delivery.error},
        }
