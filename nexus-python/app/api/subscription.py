import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_db_session
from app.models import Subscription
from app.agents.scout_agent import run_scout_task
import json

router = APIRouter()


@router.get("")
async def list_subscriptions(
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """订阅规则列表（分页）"""
    offset = (page - 1) * size
    stmt = select(Subscription).order_by(Subscription.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    count_stmt = select(func.count(Subscription.id))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    data = []
    for item in items:
        keywords = item.keywords
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except Exception:
                keywords = []
        elif not isinstance(keywords, list):
            keywords = []

        platforms = item.source_platforms
        if isinstance(platforms, str):
            try:
                platforms = json.loads(platforms)
            except Exception:
                platforms = []
        elif not isinstance(platforms, list):
            platforms = []

        data.append({
            "id": item.id,
            "user_id": item.user_id,
            "name": item.name,
            "keywords": keywords,
            "source_platforms": platforms,
            "match_mode": item.match_mode,
            "priority": item.priority,
            "status": item.status,
            "cron_expression": item.cron_expression,
            "last_run_at": item.last_run_at.isoformat() if item.last_run_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {"code": 200, "data": {"items": data, "total": total, "page": page, "size": size}}


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: int, db: AsyncSession = Depends(get_db_session)
):
    """订阅规则详情"""
    result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    item = result.scalar_one_or_none()
    if item is None:
        return {"code": 404, "message": "Subscription not found"}

    return {"code": 200, "data": {
        "id": item.id,
        "user_id": item.user_id,
        "name": item.name,
        "keywords": json.loads(item.keywords) if item.keywords else [],
        "source_platforms": json.loads(item.source_platforms) if item.source_platforms else [],
        "match_mode": item.match_mode,
        "trigger_conditions": item.trigger_conditions,
        "priority": item.priority,
        "status": item.status,
        "cron_expression": item.cron_expression,
        "last_run_at": item.last_run_at.isoformat() if item.last_run_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }}


@router.post("/{subscription_id}/trigger")
async def trigger_subscription(
    subscription_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """手动触发采集任务（调用 Scout Agent）"""
    result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        return {"code": 404, "message": "Subscription not found"}

    keywords = []
    platforms = []
    try:
        keywords = json.loads(sub.keywords) if sub.keywords else []
    except Exception:
        pass
    try:
        platforms = json.loads(sub.source_platforms) if sub.source_platforms else []
    except Exception:
        pass

    task_id = uuid.uuid4().hex
    mcp_pool = request.app.state.mcp_pool

    import asyncio
    asyncio.create_task(run_scout_task(
        task_id=task_id,
        subscription_id=subscription_id,
        keywords=keywords,
        source_platforms=platforms,
        mcp_pool=mcp_pool,
        db=db,
    ))

    return {"code": 200, "data": {"task_id": task_id, "message": "triggered"}}


@router.post("/discover-sources")
async def discover_sources(request: Request):
    """AI 自动发现 RSS / Web / API 源

    根据主题关键词，通过内置源库匹配 + LLM 推荐，
    返回可用的 RSS URL、Web 源和 API 源列表。
    """
    import json as _json
    from app.skills.builtins import DiscoverSourcesSkill

    # 解析请求体
    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass

    topic = body.get("topic", "")
    keywords = body.get("keywords", [])

    if not topic and not keywords:
        return {"code": 400, "message": "请提供 topic 或 keywords"}

    skill = DiscoverSourcesSkill()
    result = await skill.execute(topic=topic, keywords=keywords)

    return {
        "code": 200,
        "data": {
            "topic": topic,
            "keywords": keywords,
            **result.data,
        },
    }
