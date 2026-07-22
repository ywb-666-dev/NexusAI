"""
定时轮询调度器：每小时检查所有活跃订阅并触发采集任务。
"""
import asyncio
import json
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import get_session_factory
from app.models import Subscription
from app.agents.scout_agent import run_scout_task, _update_task_status


_POLL_INTERVAL_SECONDS = 3600  # 1 小时


async def _collect_one(
    mcp_pool,
    sub: Subscription,
    sem: asyncio.Semaphore,
) -> None:
    """采集单个订阅，由信号量控制并发数"""
    async with sem:
        task_id = uuid.uuid4().hex
        keywords = sub.keywords if isinstance(sub.keywords, list) else []
        rss_feeds = sub.rss_feeds if isinstance(sub.rss_feeds, list) else []
        try:
            if isinstance(sub.keywords, str):
                keywords = json.loads(sub.keywords)
        except Exception:
            pass

        platforms = sub.source_platforms if isinstance(sub.source_platforms, list) else []
        try:
            if isinstance(sub.source_platforms, str):
                platforms = json.loads(sub.source_platforms)
        except Exception:
            pass

        try:
            if isinstance(sub.rss_feeds, str):
                rss_feeds = json.loads(sub.rss_feeds)
        except Exception:
            pass

        if not keywords and "api" not in platforms:
            print(f"[Scheduler] Skip sub {sub.id}: no keywords and not api platform")
            return

        factory = get_session_factory()
        async with factory() as db:
            try:
                print(f"[Scheduler] Triggering sub {sub.id} '{sub.name}'")
                await run_scout_task(
                    task_id=task_id,
                    subscription_id=sub.id,
                    keywords=keywords,
                    source_platforms=platforms,
                    mcp_pool=mcp_pool,
                    db=db,
                    rss_feeds=rss_feeds,
                )
                # Update last_run_at
                sub.last_run_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[Scheduler] Sub {sub.id} failed: {e}")


async def start_scheduler(mcp_pool) -> None:
    """后台轮询：查询 status=1 的订阅，逐个触发采集。

    延迟启动 30 秒，避免与 FastAPI startup 竞争。
    使用 Semaphore(3) 限制并发 MCP 子进程数。
    """
    print("[Scheduler] Waiting 30s before first poll...")
    await asyncio.sleep(30)

    sem = asyncio.Semaphore(3)
    iteration = 0

    while True:
        iteration += 1
        start_time = datetime.now()
        print(f"[Scheduler] === Poll iteration {iteration} at {start_time.isoformat()} ===")

        factory = get_session_factory()
        async with factory() as db:
            try:
                result = await db.execute(
                    select(Subscription).where(Subscription.status == 1)
                )
                subs = result.scalars().all()
                print(f"[Scheduler] {len(subs)} active subscriptions found")

                tasks = [
                    asyncio.create_task(_collect_one(mcp_pool, sub, sem))
                    for sub in subs
                ]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                print(f"[Scheduler] DB query failed: {e}")
            finally:
                await db.close()

        elapsed = (datetime.now() - start_time).total_seconds()
        sleep_time = max(10, _POLL_INTERVAL_SECONDS - elapsed)
        print(f"[Scheduler] Iteration took {elapsed:.0f}s, sleeping {sleep_time:.0f}s")
        await asyncio.sleep(sleep_time)
