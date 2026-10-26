from fastapi import APIRouter, Request, HTTPException, Query
from sqlalchemy import select, func, or_, cast, Integer
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models import Content, Subscription

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
    sort: str = Query("latest", pattern="^(latest|relevance)$"),
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
    async with get_session_factory()() as db:
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
                "items": [serialize(r) for r in rows],
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
        return {"code": 200, "data": serialize(row)}
