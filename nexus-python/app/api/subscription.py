from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

router = APIRouter()


@router.get("")
async def list_subscriptions(
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """订阅规则列表"""
    # TODO: Phase 7 实现分页查询
    return {"code": 200, "data": {"items": [], "total": 0}}


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: int, db: AsyncSession = Depends(get_db_session)
):
    """订阅规则详情"""
    # TODO: Phase 7 实现详情查询
    return {"code": 200, "data": {}}


@router.post("/{subscription_id}/trigger")
async def trigger_subscription(
    subscription_id: int, db: AsyncSession = Depends(get_db_session)
):
    """手动触发采集任务（调用 Scout Agent）"""
    # TODO: Phase 7 实现触发逻辑
    return {"code": 200, "data": {"message": "triggered"}}
