from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, StrictBool
from sqlalchemy import select, func
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models.briefing import Briefing, BriefingPreference
from app.models.delivery import PushChannel
from app.services import briefing as service
from app.services.task_service import spawn

router = APIRouter()


class GenerateInput(BaseModel):
    hours: Literal[24, 168] = 24


class PreferenceInput(BaseModel):
    enabled: StrictBool = False
    pushEnabled: StrictBool = False


@router.get("/preferences")
async def preferences(request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        row = await db.get(BriefingPreference, user["id"])
        return {
            "code": 200,
            "data": {
                "enabled": bool(row and row.enabled),
                "pushEnabled": bool(row and row.push_enabled),
                "time": "08:00",
                "timezone": "Asia/Shanghai",
            },
        }


@router.put("/preferences")
async def save_preferences(body: PreferenceInput, request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        row = await db.get(BriefingPreference, user["id"])
        if not row:
            row = BriefingPreference(user_id=user["id"], enabled=0, push_enabled=0)
            db.add(row)
        if body.enabled and not row.enabled:
            row.enabled_at = datetime.utcnow()
        row.enabled, row.push_enabled = body.enabled, body.pushEnabled
        await db.commit()
    return {"code": 200}


@router.get("")
async def list_briefings(
    request: Request, page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=50)
):
    user = current_user(request)
    async with get_session_factory()() as db:
        query = select(Briefing).where(Briefing.user_id == user["id"])
        total = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar()
        rows = (
            (
                await db.execute(
                    query.order_by(Briefing.created_at.desc(), Briefing.id)
                    .offset((page - 1) * size)
                    .limit(size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "code": 200,
            "data": {
                "items": [service.serialize(r, False) for r in rows],
                "total": total,
            },
        }


@router.post("")
async def generate(body: GenerateInput, request: Request):
    identifier = await service.create_briefing(current_user(request)["id"], body.hours)
    return {"code": 200, "data": {"id": identifier}}


async def owned(db, identifier, user_id):
    row = await db.get(Briefing, identifier)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "简报不存在")
    return row


@router.get("/{identifier}")
async def detail(identifier: str, request: Request):
    async with get_session_factory()() as db:
        row = await owned(db, identifier, current_user(request)["id"])
        return {"code": 200, "data": service.serialize(row)}


@router.post("/{identifier}/push")
async def push(identifier: str, request: Request):
    user_id = current_user(request)["id"]
    async with get_session_factory()() as db:
        row = await owned(db, identifier, user_id)
        if row.status != "ready" or not (row.report or {}).get("events"):
            raise HTTPException(409, "简报尚未完成或没有可推送的重点")
        channel = (
            await db.execute(
                select(PushChannel.id)
                .where(PushChannel.user_id == user_id, PushChannel.enabled == 1)
                .limit(1)
            )
        ).scalar_one_or_none()
        if channel is None:
            raise HTTPException(409, "请先在推送设置中添加并启用飞书或钉钉渠道")
    spawn(service.deliver(user_id, identifier))
    return {
        "code": 200,
        "message": "已提交投递；已投递过的渠道会跳过，可在推送设置查看结果和重试失败记录",
    }
