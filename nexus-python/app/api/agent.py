import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.agents.supervisor import build_scout_agent
from app.agents.scout_agent import get_task_status
from app.models import Subscription

router = APIRouter()


@router.post("/tasks")
async def create_task(
    subscription_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """触发 Scout Agent 采集任务"""
    task_id = uuid.uuid4().hex

    # 查询订阅信息
    from sqlalchemy import select
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return {"code": 404, "message": "Subscription not found"}

    import json
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

    # 初始化状态
    initial_state = {
        "task_id": task_id,
        "subscription_id": subscription_id,
        "keywords": keywords,
        "source_platforms": platforms,
        "raw_items": [],
        "parsed_contents": [],
        "duplicate_ids": [],
        "stored_ids": [],
        "stored_count": 0,
        "duplicate_count": 0,
        "status": "queued",
        "error": None,
    }

    # 构建并运行 Agent（在后台执行，不阻塞响应）
    import asyncio
    mcp_pool = request.app.state.mcp_pool

    async def _run():
        try:
            agent = build_scout_agent(mcp_pool, db)
            agent.invoke(initial_state)
        except Exception as e:
            await get_task_status(task_id)  # ensure key exists
            from app.agents.scout_agent import _update_task_status
            await _update_task_status(task_id, f"error: {str(e)}")

    asyncio.create_task(_run())

    return {"code": 200, "data": {"task_id": task_id, "status": "queued"}}


@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(task_id: str):
    """查询任务执行状态"""
    status = await get_task_status(task_id)
    return {"code": 200, "data": {"task_id": task_id, **status}}
