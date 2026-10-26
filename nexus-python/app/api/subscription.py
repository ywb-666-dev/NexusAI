from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import select
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models import Subscription
from app.services.task_service import create_task, parse_list
from app.services.fetching import rss_items
from app.skills.builtins import DiscoverSourcesSkill

router = APIRouter()

from app.services.auto_sources import SourcePolicy, resolve_sources
from app.services.semantic import SemanticPolicy, SemanticError, compile_intent


class ResolveInput(SourcePolicy):
    limit: int = Field(default=5, ge=0, le=5)
    semantic_policy: SemanticPolicy | None = None


@router.post("/resolve-sources")
async def resolve(body: ResolveInput):
    if body.semantic_policy and body.semantic_policy.enabled:
        from app.services.auto_sources import resolve_semantic_sources

        try:
            return {
                "code": 200,
                "data": await resolve_semantic_sources(
                    body, body.semantic_policy, body.limit
                ),
            }
        except SemanticError as exc:
            raise HTTPException(503, str(exc))
    return {"code": 200, "data": await resolve_sources(body, body.limit)}


@router.get("/semantic-capabilities")
async def semantic_capabilities():
    from app.core.config import settings

    return {
        "code": 200,
        "data": {
            "configured": bool(settings.llm.api_key),
            "max_candidates": 40,
            "default_candidates": 20,
            "default_threshold": 75,
        },
    }


@router.post("/interpret")
async def interpret(body: SemanticPolicy):
    if not body.enabled:
        raise HTTPException(400, "请开启语义订阅")
    try:
        return {"code": 200, "data": {"plan": await compile_intent(body)}}
    except SemanticError as exc:
        raise HTTPException(503, str(exc))


class TrialFeed(BaseModel):
    url: str = Field(max_length=1000, pattern=r"^https?://[^\s]+$")
    platform: Literal["rss", "web", "api"] = "rss"


class TrialInput(BaseModel):
    rss_feeds: list[TrialFeed] = Field(default_factory=list, max_length=5)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    source_policy: SourcePolicy | None = None
    semantic_policy: SemanticPolicy | None = None


@router.post("/trial")
async def trial(body: TrialInput, request: Request):
    from app.services.trial import run_trial

    if any(not k.strip() or len(k) > 200 for k in body.keywords):
        raise HTTPException(422, "关键词长度必须为 1 到 200 字")
    feeds = [f.model_dump() for f in body.rss_feeds]
    semantic = (
        body.semantic_policy
        if body.semantic_policy and body.semantic_policy.enabled
        else None
    )
    try:
        plan = await compile_intent(semantic) if semantic else None
    except SemanticError as exc:
        raise HTTPException(503, str(exc))
    if body.source_policy and body.source_policy.mode == "auto":
        from app.services.auto_sources import resolve_subscription_sources

        try:
            feeds, _ = await resolve_subscription_sources(
                feeds,
                {
                    "source_policy": body.source_policy.model_dump(),
                    "semantic_filter": semantic.model_dump() if semantic else {},
                },
                semantic_plan=plan,
            )
        except SemanticError as exc:
            raise HTTPException(503, str(exc))
        except ValueError as exc:
            raise HTTPException(409, str(exc))
    if not feeds:
        raise HTTPException(400, "请填写关注主题并匹配来源，或手动添加来源")
    try:
        result = (
            await run_trial(
                current_user(request)["id"], feeds[:5], body.keywords, semantic, plan
            )
            if semantic
            else await run_trial(current_user(request)["id"], feeds[:5], body.keywords)
        )
    except SemanticError as exc:
        raise HTTPException(503, str(exc))
    result["resolved_sources"] = feeds
    return {"code": 200, "data": result}


class DiscoverInput(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    keywords: list[str] = Field(default_factory=list, max_length=20)


@router.post("/discover-sources")
async def discover(body: DiscoverInput):
    result = await DiscoverSourcesSkill().execute(
        topic=body.topic, keywords=body.keywords
    )
    return {
        "code": 200,
        "data": {
            **result.data,
            "keywords": body.keywords,
            "notice": "来源由内置目录推荐，请预览确认可访问性后添加；关注关键词可留空。",
        },
    }


@router.get("/preview-feed")
async def preview(url: str):
    try:
        items = await rss_items(url)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {
        "code": 200,
        "data": {
            "url": url,
            "entries": [
                {
                    "title": i["title"],
                    "link": i["source_url"],
                    "summary": i["summary"][:200],
                }
                for i in items[:5]
            ],
        },
    }


@router.get("")
async def list_subscriptions(request: Request):
    user = current_user(request)
    async with get_session_factory()() as db:
        subs = (
            (
                await db.execute(
                    select(Subscription)
                    .where(Subscription.user_id == user["id"])
                    .order_by(Subscription.id.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        return {"code": 200, "data": {"items": [serialize(s) for s in subs]}}


def serialize(sub):
    return {
        "id": sub.id,
        "name": sub.name,
        "keywords": parse_list(sub.keywords),
        "rss_feeds": parse_list(sub.rss_feeds),
        "status": sub.status,
    }


@router.get("/{subscription_id}")
async def detail(subscription_id: int, request: Request):
    async with get_session_factory()() as db:
        sub = await db.get(Subscription, subscription_id)
        if not sub or sub.user_id != current_user(request)["id"]:
            raise HTTPException(404, "订阅不存在")
        return {"code": 200, "data": serialize(sub)}


@router.post("/{subscription_id}/trigger")
async def trigger(subscription_id: int, request: Request):
    task_id = await create_task(
        subscription_id, current_user(request)["id"], request.app.state.supervisor
    )
    return {"code": 200, "data": {"task_id": task_id}}
