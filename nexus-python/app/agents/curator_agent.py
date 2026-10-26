"""Curator Agent — 采集简报生成节点：汇总内容、LLM 生成采集简报摘要"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Content
from app.core.config import settings
from app.agents.state import NexusState, CuratorResult


async def run_curator(state: NexusState, db: AsyncSession) -> NexusState:
    """
    Curator Agent 节点：生成采集简报摘要。

    1. 查询最近 24 小时的非重复内容
    2. 汇总并调用 LLM 生成采集简报
    3. 无 LLM 时降级为原始列表
    """
    stored_ids = state.get("connector", {}).get("stored_ids", [])
    if not stored_ids:
        state["curator"] = CuratorResult(
            report="本次未发现新增内容，无需重复推送。", item_count=0
        )
        state["status"] = "completed"
        state["next_node"] = "__end__"
        return state
    since = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(Content)
        .where(
            Content.created_at >= since,
            Content.id.in_(stored_ids),
            Content.subscription_id == state["subscription_id"],
            Content.status == 1,
            Content.is_duplicate == 0,
        )
        .order_by(Content.created_at.desc())
        .limit(50)
    )
    contents = result.scalars().all()

    if not contents:
        report = (
            f"# 采集简报 ({datetime.utcnow().strftime('%Y-%m-%d')})\n\n今日无新增内容"
        )
        state["curator"] = CuratorResult(report=report, item_count=0)
        state["next_node"] = "__end__"
        state["status"] = "completed"
        return state

    items_text = "\n".join(
        f"- [{c.source_platform}] [{(c.title or '')[:160]}]({c.source_url}): {(c.summary or '')[:100]}"
        for c in contents[:20]
    )

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_text = (
        f"# 采集简报 ({date_str})\n\n共采集 {len(contents)} 条内容:\n\n{items_text}"
    )

    if settings.llm.api_key and state.get("enable_ai", False):
        try:
            from app.services.llm import chat

            report_text = await chat(
                f"请根据以下本次采集内容生成简洁的中文简报（200字以内），保留重要事实：\n\n{items_text}",
                max_tokens=500,
            )
            print(f"[Curator] LLM report generated for task {state.get('task_id')}")
        except Exception as e:
            print(f"[Curator] LLM report generation failed: {e}")

    from app.models import Notification
    from app.services.push import dispatch_report

    stored = state.get("connector", {}).get("stored_count", 0)
    duplicates = state.get("connector", {}).get("duplicate_count", 0)
    db.add(
        Notification(
            user_id=state["user_id"],
            type="task",
            title=f"采集完成：新增 {stored} 条内容",
            content=f"本次去重 {duplicates} 条，可在内容中心阅读。",
            related_id=state["task_id"],
            is_read=0,
        )
    )
    await db.commit()
    state["curator"] = CuratorResult(report=report_text, item_count=len(contents))
    await dispatch_report(state["user_id"], state["task_id"], report_text)
    state["next_node"] = "__end__"
    state["status"] = "completed"
    return state
