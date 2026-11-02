from fastapi import APIRouter, Request, HTTPException, Query
from sqlalchemy import select, func, or_, cast, Integer
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models import Content, Subscription
from app.models.feedback import ContentFeedback
from pydantic import BaseModel, StrictBool
from sqlalchemy.dialects.mysql import insert
from app.services.recommendation import rank, feedback_data

router = APIRouter()


@router.get("/pending/{content_id}")
async def pending_content(content_id: str, request: Request):
    if current_user(request)["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    async with get_session_factory()() as db:
        row = await db.get(Content, content_id)
        if not row or row.status != 2:
            raise HTTPException(404, "待审内容不存在")
        return {"code": 200, "data": serialize(row)}


def serialize(c):
    return {
        "id": c.id,
        "subscriptionId": c.subscription_id,
        "sourcePlatform": c.source_platform,
        "sourceUrl": c.source_url,
        "title": c.title,
        "summary": c.summary,
        "translatedSummary": c.translated_summary,
        "quality": c.quality,
        "relevance": c.relevance,
        "contentBody": c.content_body,
        "author": c.author,
        "status": c.status,
        "fetchedAt": c.fetched_at.isoformat() + "Z" if c.fetched_at else None,
        "publishedAt": c.published_at.isoformat() + "Z" if c.published_at else None,
    }


@router.get("")
async def list_contents(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=200),
    platform: str = "",
    subscription_id: int | None = None,
    sort: str = Query("latest", pattern="^(latest|relevance|personalized)$"),
    saved: bool = False,
):
    user = current_user(request)
    query = (
        select(Content)
        .join(Subscription, Content.subscription_id == Subscription.id)
        .where(Subscription.user_id == user["id"], Content.status == 1)
    )
    if search:
        query = query.where(
            or_(
                Content.title.contains(search, autoescape=True),
                Content.summary.contains(search, autoescape=True),
            )
        )
    if platform:
        query = query.where(Content.source_platform == platform)
    if subscription_id:
        query = query.where(Content.subscription_id == subscription_id)
    if saved:
        query = query.join(
            ContentFeedback,
            (ContentFeedback.content_id == Content.id)
            & (ContentFeedback.user_id == user["id"]),
        ).where(ContentFeedback.saved == True)
    async with get_session_factory()() as db:
        history = (
            await db.execute(
                select(Content, ContentFeedback)
                .join(Subscription, Content.subscription_id == Subscription.id)
                .join(
                    ContentFeedback,
                    (ContentFeedback.content_id == Content.id)
                    & (ContentFeedback.user_id == user["id"]),
                )
                .where(
                    Subscription.user_id == user["id"],
                    Content.status == 1,
                    or_(
                        ContentFeedback.liked == True,
                        ContentFeedback.saved == True,
                        ContentFeedback.dismissed == True,
                    ),
                )
                .order_by(ContentFeedback.updated_at.desc(), Content.id)
                .limit(200)
            )
        ).all()
        feedback = {c.id: feedback_data(f) for c, f in history}
        if sort == "personalized":
            pool = query.where(
                Content.is_duplicate == 0,
                func.json_extract(Content.relevance, "$.recommended") == True,
                func.json_unquote(func.json_extract(Content.relevance, "$.method"))
                == "llm",
            )
            count = (
                await db.execute(select(func.count()).select_from(pool.subquery()))
            ).scalar()
            candidates = (
                (
                    await db.execute(
                        pool.order_by(Content.fetched_at.desc(), Content.id).limit(500)
                    )
                )
                .scalars()
                .all()
            )
            feedback = {
                f.content_id: feedback_data(f)
                for f in (
                    await db.execute(
                        select(ContentFeedback).where(
                            ContentFeedback.user_id == user["id"],
                            ContentFeedback.content_id.in_([c.id for c in candidates]),
                        )
                    )
                ).scalars()
            }
            # Exclude dismissed articles even if their feedback is older than the profile budget.
            dismissed = set(
                (
                    await db.execute(
                        select(ContentFeedback.content_id).where(
                            ContentFeedback.user_id == user["id"],
                            ContentFeedback.dismissed == True,
                        )
                    )
                ).scalars()
            )
            import asyncio

            ranked = await asyncio.to_thread(
                rank, [c for c in candidates if c.id not in dismissed], history
            )
            return {
                "code": 200,
                "data": {
                    "items": [
                        {
                            **serialize(c),
                            "feedback": feedback.get(c.id, {}),
                            "recommendation": explanation,
                        }
                        for c, explanation in ranked[(page - 1) * size : page * size]
                    ],
                    "total": len(ranked),
                    "page": page,
                    "size": size,
                    "coverage": {
                        "poolLimit": 500,
                        "available": count,
                        "sampled": len(candidates),
                    },
                },
            }
        total = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar()
        order = [Content.fetched_at.desc(), Content.id]
        if sort == "relevance":
            order = [
                func.date(Content.fetched_at).desc(),
                func.coalesce(
                    cast(func.json_extract(Content.relevance, "$.score"), Integer), 0
                ).desc(),
                Content.fetched_at.desc(),
                Content.id,
            ]
        rows = (
            (
                await db.execute(
                    query.order_by(*order).offset((page - 1) * size).limit(size)
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
                        **serialize(r),
                        "feedback": feedback_data(
                            await db.get(ContentFeedback, (user["id"], r.id))
                        ),
                    }
                    for r in rows
                ],
                "total": total,
                "page": page,
                "size": size,
            },
        }


@router.get("/{content_id}")
async def detail(content_id: str, request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        row = (
            await db.execute(
                select(Content)
                .join(Subscription, Content.subscription_id == Subscription.id)
                .where(
                    Content.id == content_id,
                    Subscription.user_id == user["id"],
                    Content.status == 1,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "内容不存在")
        return {
            "code": 200,
            "data": {
                **serialize(row),
                "feedback": feedback_data(
                    await db.get(ContentFeedback, (user["id"], row.id))
                ),
            },
        }


class FeedbackInput(BaseModel):
    liked: StrictBool | None = None
    saved: StrictBool | None = None
    dismissed: StrictBool | None = None


@router.put("/{content_id}/feedback")
async def feedback(content_id: str, body: FeedbackInput, request: Request):
    user = current_user(request)
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "请选择反馈操作")
    async with get_session_factory()() as db:
        row = (
            await db.execute(
                select(Content.id)
                .join(Subscription, Content.subscription_id == Subscription.id)
                .where(
                    Content.id == content_id,
                    Subscription.user_id == user["id"],
                    Content.status == 1,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "内容不存在")
        stmt = insert(ContentFeedback).values(
            user_id=user["id"], content_id=content_id, **changes
        )
        await db.execute(stmt.on_duplicate_key_update(**changes, updated_at=func.now()))
        await db.commit()
        return {
            "code": 200,
            "data": feedback_data(
                await db.get(ContentFeedback, (user["id"], content_id))
            ),
        }
