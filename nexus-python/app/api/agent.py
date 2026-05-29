from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

router = APIRouter()


@router.post("/tasks")
async def create_task(
    subscription_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """触发 Scout Agent 采集任务"""
    # TODO: Phase 6 实现 LangGraph Agent 调用
    return {"code": 200, "data": {"task_id": "placeholder", "status": "queued"}}


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """查询任务执行状态"""
    # TODO: Phase 6 实现状态查询
    return {"code": 200, "data": {"task_id": task_id, "status": "pending"}}
