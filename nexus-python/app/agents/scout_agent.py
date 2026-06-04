import uuid
import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.state import ScoutState
from app.memory.milvus_client import milvus_client
from app.models import Subscription, Content, Notification
from app.core.dependencies import get_redis_client
from app.core.config import settings


# ============== Embedding helper ==============

def _get_embedding(text: str) -> list[float]:
    """
    获取文本的 embedding 向量。
    优先调用 OpenAI API，失败时降级为随机向量（仅用于测试）。
    """
    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )
        resp = client.embeddings.create(
            model=settings.llm.embedding_model,
            input=text[:8000],
        )
        return resp.data[0].embedding
    except Exception:
        import random
        dim = settings.milvus.embedding_dimensions
        return [random.uniform(-0.1, 0.1) for _ in range(dim)]


def _content_hash(text: str) -> str:
    """生成内容 SHA-256 哈希"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ============== Graph Nodes ==============

async def fetch_sources(state: ScoutState, mcp_pool: Any, db: AsyncSession) -> dict:
    """使用 MCP 工具获取原始内容源"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "fetching")

    raw_items: list[dict] = []
    platforms = state.get("source_platforms", [])
    keywords = state.get("keywords", [])

    # RSS 采集
    if "rss" in platforms:
        for keyword in keywords:
            try:
                result = await mcp_pool.call_tool("rss", "fetch_rss", {"url": keyword})
                if isinstance(result, list):
                    for item in result:
                        raw_items.append({
                            "platform": "rss",
                            "source_url": item.get("link", keyword),
                            "title": item.get("title", ""),
                            "summary": item.get("summary", ""),
                            "published_at": item.get("published_at", ""),
                            "raw": item,
                        })
            except Exception:
                pass

    # Web 采集（简化：把 keyword 当 URL 尝试抓取）
    if "web" in platforms:
        for keyword in keywords:
            if keyword.startswith("http"):
                try:
                    result = await mcp_pool.call_tool("web", "scrape_page", {"url": keyword})
                    raw_items.append({
                        "platform": "web",
                        "source_url": result.get("url", keyword),
                        "title": result.get("title", ""),
                        "summary": result.get("html", "")[:500],
                        "published_at": "",
                        "raw": result,
                    })
                except Exception:
                    pass

    return {"raw_items": raw_items, "status": "fetched"}


async def parse_content(state: ScoutState, db: AsyncSession) -> dict:
    """将原始内容解析为结构化数据"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "parsing")

    parsed: list[dict] = []
    for item in state.get("raw_items", []):
        body = item.get("raw", {}).get("html", item.get("summary", ""))
        content_text = f"{item.get('title', '')}\n{item.get('summary', '')}\n{body}"[:2000]
        c_hash = _content_hash(content_text)

        parsed.append({
            "id": str(uuid.uuid4()),
            "subscription_id": state["subscription_id"],
            "source_platform": item.get("platform", "unknown"),
            "source_url": item.get("source_url", ""),
            "title": item.get("title", "")[:500],
            "summary": item.get("summary", "")[:2000],
            "content_body": body,
            "author": item.get("raw", {}).get("author", ""),
            "published_at": item.get("published_at", ""),
            "content_hash": c_hash,
            "embedding": _get_embedding(content_text),
        })

    return {"parsed_contents": parsed, "status": "parsed"}


async def check_duplicate(state: ScoutState, db: AsyncSession) -> dict:
    """使用 Milvus 进行语义去重检查"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "checking_duplicates")

    duplicates: list[str] = []
    for content in state.get("parsed_contents", []):
        try:
            similar = milvus_client.search_similar(
                embedding=content["embedding"],
                top_k=1,
                threshold=settings.milvus.dedup_threshold,
            )
            if similar:
                duplicates.append(content["id"])
        except Exception:
            pass

    return {
        "duplicate_ids": duplicates,
        "duplicate_count": len(duplicates),
        "status": "checked",
    }


async def store_content(state: ScoutState, db: AsyncSession) -> dict:
    """将非重复内容保存到 MySQL 和 Milvus"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "storing")

    stored_ids: list[str] = []
    duplicate_set = set(state.get("duplicate_ids", []))
    vectors_to_insert: list[dict] = []

    for content in state.get("parsed_contents", []):
        if content["id"] in duplicate_set:
            continue

        # MySQL 插入
        db_content = Content(
            id=content["id"],
            subscription_id=content["subscription_id"],
            source_platform=content["source_platform"],
            source_url=content["source_url"],
            title=content["title"],
            summary=content["summary"],
            content_body=content.get("content_body", ""),
            author=content.get("author", ""),
            content_hash=content["content_hash"],
            status=1,
            is_duplicate=0,
        )
        db.add(db_content)
        vectors_to_insert.append({
            "content_id": content["id"],
            "embedding": content["embedding"],
        })
        stored_ids.append(content["id"])

    await db.commit()

    # Milvus 插入
    if vectors_to_insert:
        try:
            vector_ids = milvus_client.insert_vectors(vectors_to_insert)
            # TODO: 将 vector_id 写回 content 表
        except Exception:
            pass

    return {
        "stored_ids": stored_ids,
        "stored_count": len(stored_ids),
        "status": "stored",
    }


async def notify(state: ScoutState, db: AsyncSession) -> dict:
    """发送通知：保存到 notification 表"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "notifying")

    stored_count = state.get("stored_count", 0)
    if stored_count > 0:
        # 查询订阅的 user_id
        result = await db.execute(
            select(Subscription.user_id).where(Subscription.id == state["subscription_id"])
        )
        user_id = result.scalar()
        if user_id:
            notification = Notification(
                user_id=user_id,
                type="task",
                title=f"采集任务完成: {task_id[:8]}",
                content=f"新增 {stored_count} 条内容",
                is_read=0,
                related_id=task_id,
            )
            db.add(notification)
            await db.commit()

    await _update_task_status(task_id, "completed")
    return {"status": "completed"}


async def handle_error(state: ScoutState) -> dict:
    """错误处理节点"""
    task_id = state["task_id"]
    await _update_task_status(task_id, f"error: {state.get('error', 'unknown')}")
    return {"status": "error"}


# ============== Task execution ==============

async def _update_task_status(task_id: str, status: str) -> None:
    """更新任务状态到 Redis"""
    try:
        redis = get_redis_client()
        await redis.setex(
            f"agent:status:{task_id}",
            3600,
            json.dumps({"status": status, "updated_at": datetime.utcnow().isoformat()}),
        )
    except Exception:
        pass


async def get_task_status(task_id: str) -> dict:
    """从 Redis 查询任务状态"""
    try:
        redis = get_redis_client()
        data = await redis.get(f"agent:status:{task_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {"status": "unknown"}


async def run_scout_task(
    task_id: str,
    subscription_id: int,
    keywords: list[str],
    source_platforms: list[str],
    mcp_pool: Any,
    db: AsyncSession,
) -> None:
    """运行完整的 Scout Agent 采集流水线（异步入口）"""
    import asyncio
    from app.agents.supervisor import build_scout_agent

    initial_state = {
        "task_id": task_id,
        "subscription_id": subscription_id,
        "keywords": keywords,
        "source_platforms": source_platforms,
        "raw_items": [],
        "parsed_contents": [],
        "duplicate_ids": [],
        "stored_ids": [],
        "stored_count": 0,
        "duplicate_count": 0,
        "status": "queued",
        "error": None,
    }

    def _sync_invoke():
        agent = build_scout_agent(mcp_pool, db)
        return agent.invoke(initial_state)

    try:
        # 在独立线程池中运行同步 LangGraph，避免事件循环冲突
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_invoke)
    except Exception as e:
        await _update_task_status(task_id, f"error: {str(e)}")
