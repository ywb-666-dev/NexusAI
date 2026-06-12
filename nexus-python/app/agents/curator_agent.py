"""Curator Agent — 日报生成节点：汇总内容、LLM 生成日报摘要"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Content
from app.core.config import settings
from app.agents.state import NexusState, CuratorResult


async def run_curator(state: NexusState, db: AsyncSession) -> NexusState:
    """
    Curator Agent 节点：生成日报摘要。

    1. 查询最近 24 小时的非重复内容
    2. 汇总并调用 LLM 生成日报
    3. 无 LLM 时降级为原始列表
    """
    since = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(Content)
        .where(
            Content.created_at >= since,
            Content.status == 1,
            Content.is_duplicate == 0,
        )
        .order_by(Content.created_at.desc())
        .limit(50)
    )
    contents = result.scalars().all()

    if not contents:
        report = f"# 日报 ({datetime.utcnow().strftime('%Y-%m-%d')})\n\n今日无新增内容"
        state["curator"] = CuratorResult(report=report, item_count=0)
        state["next_node"] = "__end__"
        state["status"] = "completed"
        return state

    items_text = "\n".join(
        f"- [{c.source_platform}] {c.title}: {(c.summary or '')[:100]}"
        for c in contents[:20]
    )

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_text = f"# 日报 ({date_str})\n\n共采集 {len(contents)} 条内容:\n\n{items_text}"

    if settings.llm.api_key:
        try:
            import openai
            client = openai.OpenAI(
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
            )
            resp = client.chat.completions.create(
                model=settings.llm.chat_model,
                messages=[{
                    "role": "user",
                    "content": f"请根据以下今日采集的内容生成一份简洁的日报摘要（200字以内）：\n\n{items_text}",
                }],
                temperature=0.3,
                max_tokens=500,
            )
            report_text = resp.choices[0].message.content.strip()
            print(f"[Curator] LLM report generated for task {state.get('task_id')}")
        except Exception as e:
            print(f"[Curator] LLM report generation failed: {e}")

    state["curator"] = CuratorResult(report=report_text, item_count=len(contents))
    state["next_node"] = "__end__"
    state["status"] = "completed"
    return state
