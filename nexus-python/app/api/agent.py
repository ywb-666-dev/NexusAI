import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db_session
from app.agents.scout_agent import get_task_status, run_scout_task
from app.models import Subscription
import json

router = APIRouter()


@router.post("/tasks")
async def create_task(
    subscription_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """触发 Scout Agent 采集任务"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
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

    return {"code": 200, "data": {"task_id": task_id, "status": "queued"}}


@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(task_id: str):
    """查询任务执行状态"""
    status = await get_task_status(task_id)
    return {"code": 200, "data": {"task_id": task_id, **status}}
