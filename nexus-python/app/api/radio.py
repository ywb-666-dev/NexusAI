import uuid
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, StrictBool, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models import Content, Subscription, ContentFeedback
from app.models.radio import RadioTurn, RadioFollow
from app.models.briefing import Briefing
from app.services import radio

router = APIRouter()


async def context(db, user_id, brief_id, index, lock=False):
    query = select(Briefing).where(Briefing.id == brief_id, Briefing.user_id == user_id)
    if lock:
        query = query.with_for_update()
    row = (await db.execute(query)).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "节目不存在")
    if row.status != "ready":
        raise HTTPException(409, "简报尚未完成，请完成后再收听")
    try:
        event, sources = radio.event_context(row.report or {}, index)
    except ValueError:
        raise HTTPException(404, "节目事件不存在")
    return row, event, sources


def turn_data(row):
    return {
        "id": row.id,
        "question": row.question,
        "answer": row.answer,
        "createdAt": row.created_at.isoformat() + "Z",
    }


@router.get("/{brief_id}/events/{index}")
async def event(brief_id: str, index: int, request: Request):
    uid = current_user(request)["id"]
    async with get_session_factory()() as db:
        _, event, sources = await context(db, uid, brief_id, index)
        turns = (
            (
                await db.execute(
                    select(RadioTurn)
                    .where(
                        RadioTurn.user_id == uid,
                        RadioTurn.briefing_id == brief_id,
                        RadioTurn.event_index == index,
                    )
                    .order_by(RadioTurn.created_at.desc(), RadioTurn.id)
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )
        feedback = (
            (
                await db.execute(
                    select(ContentFeedback).where(
                        ContentFeedback.user_id == uid,
                        ContentFeedback.content_id.in_([s["id"] for s in sources]),
                    )
                )
            )
            .scalars()
            .all()
        )
        dismissed = {f.content_id for f in feedback if f.dismissed}
        follow = await db.get(RadioFollow, (uid, brief_id, index))
        sub = await db.get(Subscription, follow.subscription_id) if follow else None
        return {
            "code": 200,
            "data": {
                "event": event,
                "sources": sources,
                "turns": [turn_data(t) for t in reversed(turns)],
                "dismissed": bool(sources)
                and all(s["id"] in dismissed for s in sources),
                "followId": (
                    sub.id if sub and sub.user_id == uid and sub.status != -1 else None
                ),
            },
        }


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=500)


@router.post("/{brief_id}/events/{index}/ask")
async def ask(brief_id: str, index: int, body: Question, request: Request):
    uid = current_user(request)["id"]
    async with get_session_factory()() as db:
        _, event, sources = await context(db, uid, brief_id, index)
        turns = (
            (
                await db.execute(
                    select(RadioTurn)
                    .where(
                        RadioTurn.user_id == uid,
                        RadioTurn.briefing_id == brief_id,
                        RadioTurn.event_index == index,
                    )
                    .order_by(RadioTurn.created_at.desc())
                    .limit(4)
                )
            )
            .scalars()
            .all()
        )
    radio.admit(uid)
    try:
        try:
            result = await radio.answer(
                event,
                sources,
                body.question,
                [
                    {"question": t.question, "answer": t.answer["answer"]}
                    for t in reversed(turns)
                ],
            )
        except Exception:
            raise HTTPException(
                503, "追问暂时未完成，可能是模型服务或引用校验失败，请稍后重试"
            ) from None
        async with get_session_factory()() as db:
            turn = RadioTurn(
                id=uuid.uuid4().hex,
                user_id=uid,
                briefing_id=brief_id,
                event_index=index,
                question=body.question,
                answer=result,
            )
            db.add(turn)
            await db.commit()
            await db.refresh(turn)
            return {"code": 200, "data": turn_data(turn)}
    finally:
        radio.ACTIVE.discard(uid)


class Preference(BaseModel):
    dismissed: StrictBool


@router.put("/{brief_id}/events/{index}/preference")
async def preference(brief_id: str, index: int, body: Preference, request: Request):
    uid = current_user(request)["id"]
    async with get_session_factory()() as db:
        _, _, sources = await context(db, uid, brief_id, index)
        ids = [s["id"] for s in sources]
        owned = (
            (
                await db.execute(
                    select(Content.id)
                    .join(Subscription, Content.subscription_id == Subscription.id)
                    .where(
                        Content.id.in_(ids),
                        Content.status == 1,
                        Subscription.user_id == uid,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not owned:
            raise HTTPException(409, "原文内容已不可用，无法更新偏好")
        for key in owned:
            stmt = insert(ContentFeedback).values(
                user_id=uid, content_id=key, dismissed=body.dismissed
            )
            await db.execute(
                stmt.on_duplicate_key_update(
                    dismissed=body.dismissed, updated_at=func.now()
                )
            )
        await db.commit()
        return {"code": 200}


@router.post("/{brief_id}/events/{index}/follow")
async def follow(brief_id: str, index: int, request: Request):
    """Create an idempotent paused semantic subscription, review before enabling."""
    from app.services.task_service import parse_list

    uid = current_user(request)["id"]
    async with get_session_factory()() as db:
        _, event, sources = await context(db, uid, brief_id, index, lock=True)
        existing = await db.get(RadioFollow, (uid, brief_id, index))
        old = await db.get(Subscription, existing.subscription_id) if existing else None
        if old and old.user_id == uid and old.status != -1:
            return {"code": 200, "data": {"id": old.id, "status": old.status}}
        subs = (
            (
                await db.execute(
                    select(Subscription)
                    .join(Content, Content.subscription_id == Subscription.id)
                    .where(
                        Subscription.user_id == uid,
                        Subscription.status != -1,
                        Content.id.in_([s["id"] for s in sources]),
                        Content.status == 1,
                    )
                )
            )
            .scalars()
            .all()
        )
        feeds, seen = [], set()
        for sub in subs:
            for feed in parse_list(sub.rss_feeds):
                if (
                    feed.get("url")
                    and feed["url"] not in seen
                    and feed.get("platform") in ("rss", "web", "api")
                ):
                    feeds.append({**feed, "origin": "manual"})
                    seen.add(feed["url"])
        if not feeds:
            raise HTTPException(409, "没有可复用的订阅来源，请到我的订阅中配置")
        sub = Subscription(
            user_id=uid,
            name=("追踪 · " + event["title"])[:100],
            status=0,
            keywords=[],
            source_platforms=list({f["platform"] for f in feeds[:20]}),
            rss_feeds=feeds[:20],
            trigger_conditions={
                "interval_minutes": 1440,
                "enable_ai": False,
                "source_policy": {"mode": "manual"},
                "semantic_filter": {
                    "enabled": True,
                    "intent": (
                        "持续关注以下事件的后续进展和实质变化，避免重复旧报道："
                        + event["title"]
                        + "。"
                        + event["summary"]
                    )[:1000],
                    "exclusions": "纯广告、无新增事实的重复报道",
                    "threshold": 75,
                    "max_candidates": 20,
                },
            },
        )
        db.add(sub)
        await db.flush()
        if existing:
            existing.subscription_id = sub.id
        else:
            db.add(
                RadioFollow(
                    user_id=uid,
                    briefing_id=brief_id,
                    event_index=index,
                    subscription_id=sub.id,
                )
            )
        await db.commit()
        return {"code": 200, "data": {"id": sub.id, "status": 0}}
