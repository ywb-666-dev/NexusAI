from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

router = APIRouter()


@router.get("")
async def list_contents(
    subscription_id: int | None = None,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """内容列表"""
    # TODO: Phase 7 实现分页查询
    return {"code": 200, "data": {"items": [], "total": 0}}


@router.get("/{content_id}")
async def get_content(content_id: str, db: AsyncSession = Depends(get_db_session)):
    """内容详情"""
    # TODO: Phase 7 实现详情查询
    return {"code": 200, "data": {}}


@router.post("/{content_id}/search-similar")
async def search_similar(content_id: str, db: AsyncSession = Depends(get_db_session)):
    """语义相似搜索（Milvus）"""
    # TODO: Phase 6 实现 Milvus 向量检索
    return {"code": 200, "data": []}
