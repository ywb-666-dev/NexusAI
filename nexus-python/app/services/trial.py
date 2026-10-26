"""Read-only subscription trial using the same Scout and Parser as real tasks."""

import asyncio
import time
from datetime import datetime, timezone
from app.agents.scout_agent import run_scout_node
from app.agents.parser_agent import prepare_items

ACTIVE_USERS: set[int] = set()
RECENT: dict[int, float] = {}
LIMIT = asyncio.Semaphore(3)


async def trial_collect(feeds, keywords, semantic_policy=None, semantic_plan=None):
    started = time.monotonic()
    state = await run_scout_node(
        {
            "rss_feeds": feeds,
            "keywords": keywords,
            "semantic_policy": (
                semantic_policy.model_dump() if semantic_policy else None
            ),
        },
        source_timeout=12,
        allow_all_failed=True,
    )
    scout = state["scout"]
    prepared = await prepare_items(scout["items"][:10], max_scrapes=3, scrape_timeout=8)
    semantic_result = None
    items = prepared["items"]
    if semantic_policy:
        from app.services.semantic import filter_articles

        filtered = await filter_articles(items, semantic_policy, semantic_plan)
        items, semantic_result = filtered["items"], filtered["summary"]
        semantic_result["unevaluated_count"] = max(
            0, scout["total_fetched"] - min(10, len(scout["items"]))
        )
    return {
        "semantic": semantic_result,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int((time.monotonic() - started) * 1000),
        "sources": scout["source_results"],
        "source_errors": scout["source_errors"],
        "collected_count": scout["collected_count"],
        "matched_count": scout["total_fetched"],
        "examined_count": min(10, len(scout["items"])),
        "readable_count": len(prepared["items"]),
        "rejected_count": prepared["rejected_count"],
        "rejected": prepared["rejected"],
        "quality_counts": prepared["quality_counts"],
        "items": [
            {
                "title": i.get("title", ""),
                "url": i["source_url"],
                "summary": i.get("summary", "")[:1200],
                "body_preview": i.get("raw_html", "")[:3000],
                "quality": i["quality"],
                "relevance": i.get("relevance"),
                "author": i.get("author", ""),
            }
            for i in items
        ],
        "notice": (
            "本次试采最多检查 5 个来源、评估前 10 条匹配内容并尝试补全其中 3 条正文。关键词匹配标题或源摘要。结果为候选样本；正式采集还会去重、风险审核和按需补全更多正文。不入库、不推送、不调用 AI。"
            if not semantic_policy
            else "语义试采会调用模型理解需求、审核前 10 条可读候选，并提供匹配和拒绝理由。不入库、不推送；正式采集仍会进一步去重与风险审核。"
        ),
    }


async def run_trial(user_id, feeds, keywords, semantic_policy=None, semantic_plan=None):
    from fastapi import HTTPException

    if user_id in ACTIVE_USERS:
        raise HTTPException(409, "已有试采正在运行，请等待结果")
    if time.monotonic() - RECENT.get(user_id, float("-inf")) < 10:
        raise HTTPException(429, "试采过于频繁，请稍后再试")
    if LIMIT.locked():
        raise HTTPException(429, "试采服务忙，请稍后重试")
    ACTIVE_USERS.add(user_id)
    RECENT[user_id] = time.monotonic()
    # Expire cooldown entries so ordinary account usage cannot grow memory forever.
    for key, moment in list(RECENT.items()):
        if time.monotonic() - moment > 120 and key not in ACTIVE_USERS:
            RECENT.pop(key, None)
    try:
        async with LIMIT:
            return await asyncio.wait_for(
                (
                    trial_collect(feeds, keywords, semantic_policy, semantic_plan)
                    if semantic_policy
                    else trial_collect(feeds, keywords)
                ),
                timeout=240 if semantic_policy else 40,
            )
    except TimeoutError:
        raise HTTPException(504, "试采超时，请减少来源数量后重试")
    finally:
        ACTIVE_USERS.discard(user_id)
