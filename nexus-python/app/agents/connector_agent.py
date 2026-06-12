"""Connector Agent — 关联去重节点：语义去重、内容存储、关联图"""

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.memory.milvus_client import milvus_client
from app.models import Content, Notification, Subscription
from app.core.config import settings
from app.agents.state import NexusState, ConnectorResult


def _get_embedding(text: str) -> list[float]:
    """获取文本的 embedding 向量"""
    try:
        import openai
        emb_key = settings.llm.embedding_api_key or settings.llm.api_key
        client = openai.OpenAI(
            api_key=emb_key,
            base_url=settings.llm.base_url,
        )
        resp = client.embeddings.create(
            model=settings.llm.embedding_model,
            input=text[:8000],
        )
        return resp.data[0].embedding
    except Exception as e:
        print(f"[Embedding] Failed: {e}")
        return []


async def run_connector(state: NexusState, db: AsyncSession) -> NexusState:
    """
    Connector Agent 节点：去重、关联、存储。

    1. SHA-256 硬去重
    2. Milvus 语义去重（相似度 > 阈值）
    3. 内容关联发现
    4. 写入 DB、创建通知
    """
    items: list[dict] = state.get("parser", {}).get("items", [])
    if not items:
        state["connector"] = ConnectorResult(
            items=[], stored_count=0, duplicate_count=0, related_groups=[],
        )
        state["next_node"] = "actor"
        return state

    stored_count = 0
    duplicate_count = 0

    for item in items:
        try:
            content_text = f"{item.get('title', '')}\n{item.get('summary', '')}"[:2000]
            c_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

            # 硬去重
            result = await db.execute(
                select(Content).where(Content.content_hash == c_hash)
            )
            if result.scalar_one_or_none():
                duplicate_count += 1
                continue

            cid = str(uuid.uuid4())
            embedding = _get_embedding(content_text)
            vector_id: str | None = None
            is_duplicate = 0
            duplicate_of: str | None = None
            related_contents: str | None = None

            # Milvus 语义去重与关联
            if embedding:
                try:
                    vector_ids = milvus_client.insert_vectors([{
                        "content_id": cid,
                        "embedding": embedding,
                    }])
                    if vector_ids:
                        vector_id = vector_ids[0]

                    # 高相似度去重 (>0.92)
                    similar = milvus_client.search_similar(
                        embedding=embedding,
                        top_k=3,
                        threshold=settings.milvus.dedup_threshold,
                    )
                    for hit in similar:
                        if hit["content_id"] != cid:
                            is_duplicate = 1
                            duplicate_of = hit["content_id"]
                            break

                    # 关联内容 (0.75~0.92)
                    related = milvus_client.search_similar(
                        embedding=embedding,
                        top_k=6,
                        threshold=settings.milvus.relate_threshold,
                    )
                    related_ids = [
                        r["content_id"] for r in related
                        if r["content_id"] != cid and r["content_id"] != duplicate_of
                    ][:5]
                    if related_ids:
                        related_contents = json.dumps(related_ids)
                except Exception as e:
                    print(f"[Connector] Milvus ops skipped: {e}")

            if is_duplicate:
                duplicate_count += 1
                try:
                    milvus_client.delete_by_content_id(cid)
                except Exception:
                    pass

            db_content = Content(
                id=cid,
                subscription_id=state.get("subscription_id"),
                source_platform=item.get("platform", ""),
                source_url=item.get("source_url", ""),
                title=(item.get("title", "") or "")[:500],
                summary=(item.get("summary", "") or "")[:2000],
                content_body=item.get("raw_html", ""),
                author=item.get("author", ""),
                content_hash=c_hash,
                vector_id=vector_id,
                status=1,
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
                related_contents=related_contents,
            )
            db.add(db_content)
            stored_count += 1
        except Exception as e:
            print(f"[Connector] Store failed for item: {e}")

    if stored_count > 0:
        await db.commit()

        # 创建通知
        sub_result = await db.execute(
            select(Subscription.user_id).where(
                Subscription.id == state.get("subscription_id")
            )
        )
        user_id = sub_result.scalar()
        if user_id:
            notification = Notification(
                user_id=user_id,
                type="task",
                title=f"采集完成: {state.get('task_id', '')[:8]}",
                content=f"新增 {stored_count} 条内容，去重 {duplicate_count} 条",
                is_read=0,
                related_id=state.get("task_id", ""),
            )
            db.add(notification)
            await db.commit()

    print(f"[Connector] Stored {stored_count} items, {duplicate_count} duplicates")

    state["connector"] = ConnectorResult(
        items=items,
        stored_count=stored_count,
        duplicate_count=duplicate_count,
        related_groups=[],
    )
    state["next_node"] = "actor"
    return state
