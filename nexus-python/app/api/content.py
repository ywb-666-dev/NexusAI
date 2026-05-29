from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_db_session
from app.models import Content
from app.memory.milvus_client import milvus_client

router = APIRouter()


@router.get("")
async def list_contents(
    subscription_id: int | None = None,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """内容列表（分页）"""
    offset = (page - 1) * size

    stmt = select(Content).where(Content.status == 1)
    if subscription_id is not None:
        stmt = stmt.where(Content.subscription_id == subscription_id)
    stmt = stmt.order_by(Content.created_at.desc()).offset(offset).limit(size)

    result = await db.execute(stmt)
    items = result.scalars().all()

    count_stmt = select(func.count(Content.id)).where(Content.status == 1)
    if subscription_id is not None:
        count_stmt = count_stmt.where(Content.subscription_id == subscription_id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    data = []
    for item in items:
        data.append({
            "id": item.id,
            "subscription_id": item.subscription_id,
            "source_platform": item.source_platform,
            "source_url": item.source_url,
            "title": item.title,
            "summary": item.summary,
            "author": item.author,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
            "is_duplicate": item.is_duplicate,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {"code": 200, "data": {"items": data, "total": total, "page": page, "size": size}}


@router.get("/{content_id}")
async def get_content(content_id: str, db: AsyncSession = Depends(get_db_session)):
    """内容详情"""
    result = await db.execute(select(Content).where(Content.id == content_id, Content.status == 1))
    item = result.scalar_one_or_none()
    if item is None:
        return {"code": 404, "message": "Content not found"}

    return {"code": 200, "data": {
        "id": item.id,
        "subscription_id": item.subscription_id,
        "source_platform": item.source_platform,
        "source_url": item.source_url,
        "title": item.title,
        "summary": item.summary,
        "content_body": item.content_body,
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "content_hash": item.content_hash,
        "vector_id": item.vector_id,
        "is_duplicate": item.is_duplicate,
        "duplicate_of": item.duplicate_of,
        "related_contents": item.related_contents,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }}


@router.post("/{content_id}/search-similar")
async def search_similar(content_id: str, db: AsyncSession = Depends(get_db_session)):
    """语义相似搜索（Milvus）"""
    # 先查询目标内容的向量
    result = await db.execute(select(Content).where(Content.id == content_id))
    item = result.scalar_one_or_none()
    if item is None:
        return {"code": 404, "message": "Content not found"}

    try:
        # 通过 content_id 反查 Milvus 向量（简化：直接搜索相似）
        # 实际生产环境应缓存 embedding，此处用 content_hash 近似
        from app.agents.scout_agent import _get_embedding
        embedding = _get_embedding(item.title or "")
        hits = milvus_client.search_similar(
            embedding=embedding,
            top_k=6,
            threshold=settings.milvus.relate_threshold,
        )

        # 过滤自身，查询详情
        similar_ids = [h["content_id"] for h in hits if h["content_id"] != content_id][:5]
        if not similar_ids:
            return {"code": 200, "data": []}

        from sqlalchemy import or_
        conds = [Content.id == cid for cid in similar_ids]
        stmt = select(Content).where(or_(*conds), Content.status == 1)
        db_result = await db.execute(stmt)
        rows = db_result.scalars().all()

        data = []
        for row in rows:
            data.append({
                "id": row.id,
                "title": row.title,
                "source_platform": row.source_platform,
                "source_url": row.source_url,
                "summary": row.summary,
            })
        return {"code": 200, "data": data}
    except Exception as e:
        return {"code": 500, "message": f"Search failed: {str(e)}"}


from app.core.config import settings
