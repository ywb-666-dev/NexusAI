"""Scout Agent — 侦察采集节点：RSS / Web / API 多源内容采集"""

import asyncio
import json
from datetime import datetime
from typing import Any

from app.agents.state import NexusState, ScoutResult
import feedparser


AGENT_NODES = ["scout", "parser", "connector", "actor", "curator"]


# ============== Redis 状态管理 ==============


async def _update_task_status(
    task_id: str,
    status: str,
    node_states: dict[str, str] | None = None,
) -> None:
    """更新任务状态到 Redis，包含 5 个 Agent 节点的状态"""
    try:
        from app.core.dependencies import get_session_factory
        from app.models.task import AgentTask

        async with get_session_factory()() as db:
            task = await db.get(AgentTask, task_id)
            if task:
                task.status = status
                nodes = dict(task.nodes or {})
                for name, value in (node_states or {}).items():
                    nodes[name] = {
                        "status": value,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                task.nodes = nodes
                await db.commit()
    except Exception as exc:
        print(f"[Task state] {exc}")
    try:
        from app.core.dependencies import get_redis_client

        redis = get_redis_client()
        data = {
            "task_id": task_id,
            "status": status,
            "nodes": {},
            "updated_at": datetime.utcnow().isoformat(),
        }
        for node in AGENT_NODES:
            data["nodes"][node] = {"status": "idle", "timestamp": None}
        if node_states:
            for node, ns in node_states.items():
                data["nodes"][node] = {
                    "status": ns,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        await redis.setex(
            f"agent:status:{task_id}",
            3600,
            json.dumps(data, ensure_ascii=False),
        )
    except Exception:
        pass


async def get_task_status(task_id: str) -> dict:
    """从 Redis 查询任务状态"""
    try:
        from app.core.dependencies import get_redis_client

        redis = get_redis_client()
        data = await redis.get(f"agent:status:{task_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {"status": "unknown"}


# ============== MCP 结果提取 ==============


def _extract_articles(mcp_result: Any) -> list[dict]:
    """
    从 MCP CallToolResult / raw list / raw dict 中提取文章 dict 列表。
    兼容 MCP SDK 的 CallToolResult、Pydantic 模型、原生 list/dict 等返回形式。
    """
    data: Any = mcp_result

    if hasattr(mcp_result, "content") and mcp_result.content:
        if hasattr(mcp_result.content[0], "text"):
            try:
                data = json.loads(mcp_result.content[0].text)
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            return []

    if isinstance(data, dict):
        data = [data]
    elif hasattr(data, "model_dump"):
        data = [data.model_dump()]
    elif hasattr(data, "dict"):
        data = [data.dict()]
    elif not isinstance(data, list):
        return []

    result: list[dict] = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
        elif hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif hasattr(item, "dict"):
            result.append(item.dict())
        else:
            continue
    return result


# ============== RSS 降级 ==============


async def _rss_fallback(keyword: str, raw_items: list[dict]) -> None:
    """feedparser 直调降级，MCP RSS 不可用时使用"""
    try:
        from bs4 import BeautifulSoup

        loop = asyncio.get_running_loop()
        d = await loop.run_in_executor(None, feedparser.parse, keyword)
        if not d.entries:
            return
        for entry in d.entries:
            author = ""
            if entry.get("author_detail"):
                author = entry["author_detail"].get("name", "")
            elif entry.get("author"):
                author = entry["author"] if isinstance(entry["author"], str) else ""
            summary_html = entry.get("summary", "") or entry.get("description", "")

            plain_summary = ""
            try:
                plain_summary = BeautifulSoup(summary_html, "html.parser").get_text(
                    separator="\n", strip=True
                )
            except Exception:
                plain_summary = summary_html

            raw_items.append(
                {
                    "platform": "rss",
                    "source_url": entry.get("link", keyword),
                    "title": entry.get("title", ""),
                    "summary": plain_summary[:2000],
                    "published_at": entry.get("published", "")
                    or entry.get("updated", ""),
                    "author": author,
                    "raw_html": summary_html,
                }
            )
        print(f"[Scout] RSS fallback '{keyword}': {len(d.entries)} items")
    except Exception as e:
        print(f"[Scout] RSS fallback also failed '{keyword}': {e}")


# ============== Scout 节点主函数 ==============


async def run_scout_node(
    state: NexusState,
    mcp_pool: Any = None,
    *,
    source_timeout=22,
    allow_all_failed=False,
) -> NexusState:
    from app.services.fetching import rss_items, web_item, api_items
    from app.services.task_service import parse_list

    feeds = parse_list(state.get("rss_feeds"))
    if not feeds:
        feeds = [
            {
                "url": k,
                "platform": (
                    "rss" if "rss" in state.get("source_platforms", []) else "web"
                ),
            }
            for k in state.get("keywords", [])
            if k.startswith(("http://", "https://"))
        ]
    if not feeds:
        raise ValueError("订阅没有可采集的源地址，请编辑订阅添加 RSS 或网页源")
    semaphore = asyncio.Semaphore(3)

    async def collect(source):
        url = source.get("url", "")
        try:
            if mcp_pool and source.get("platform", "rss") == "rss":
                from app.services.fetching import validate_url

                await validate_url(url)
                try:
                    response = await asyncio.wait_for(
                        mcp_pool.call_tool("rss", "fetch_rss", {"url": url}),
                        timeout=20,
                    )
                    articles = _extract_articles(response)
                    items = [
                        {
                            "platform": "rss",
                            "source_url": a.get("link", ""),
                            "title": a.get("title", ""),
                            "summary": a.get("summary", ""),
                            "raw_html": a.get("summary", ""),
                            "author": "",
                            "published_at": a.get("published_at", ""),
                        }
                        for a in articles
                        if a.get("link")
                    ]
                except Exception:
                    items = await rss_items(url)
            else:
                platform = source.get("platform", "rss")
                if platform == "rss":
                    items = await rss_items(url)
                elif platform == "api":
                    items = await api_items(url)
                elif platform == "web":
                    items = [await web_item(url)]
                else:
                    raise ValueError("不支持的采集源类型")
            return items, None
        except Exception as exc:
            return [], {"url": url, "error": str(exc)[:500]}

    async def bounded_collect(source):
        async with semaphore:
            try:
                return await asyncio.wait_for(collect(source), timeout=source_timeout)
            except TimeoutError:
                return [], {"url": source.get("url", ""), "error": "来源请求超时"}

    results = await asyncio.gather(*(bounded_collect(f) for f in feeds[:20]))
    items, errors = [], []
    seen = set()
    for batch, error in results:
        if error:
            errors.append(error)
        for item in batch:
            if item["source_url"] not in seen:
                seen.add(item["source_url"])
                items.append(item)
    if not items and errors and not allow_all_failed:
        raise RuntimeError("所有采集源均失败：" + "; ".join(e["error"] for e in errors))
    collected_count = len(items)
    keywords = [
        k.lower()
        for k in state.get("keywords", [])
        if not k.startswith(("http://", "https://"))
    ]
    if keywords:
        items = [
            i
            for i in items
            if any(k in (i["title"] + " " + i["summary"]).lower() for k in keywords)
        ]
    state["scout"] = {
        "items": items[:100],
        "total_fetched": len(items),
        "source_errors": errors,
        "collected_count": collected_count,
        "source_results": [
            {
                "url": source.get("url", ""),
                "count": len(batch),
                "error": error["error"] if error else None,
            }
            for source, (batch, error) in zip(feeds[:20], results)
        ],
    }
    state["next_node"] = "parser"
    return state


# ============== 向后兼容：完整流水线包装器 ==============


async def run_scout_task(
    task_id: str,
    subscription_id: int,
    keywords: list[str],
    source_platforms: list[str],
    mcp_pool: Any,
    db,
    rss_feeds: list[dict] | None = None,
) -> None:
    """
    向后兼容的完整 5-Agent 流水线包装器。

    供 scheduler / subscription API / MQ consumer 等已有调用方使用。
    内部依次执行 Scout → Parser → Connector → Actor → Curator。
    """
    from app.agents.parser_agent import run_parser as _parser
    from app.agents.connector_agent import run_connector as _connector
    from app.agents.actor_agent import run_actor as _actor
    from app.agents.curator_agent import run_curator as _curator

    state: NexusState = NexusState(
        task_id=task_id,
        subscription_id=subscription_id,
        keywords=keywords,
        rss_feeds=rss_feeds or [],
        source_platforms=source_platforms,
        next_node="scout",
        status="queued",
    )

    try:
        # ── Scout ──
        await _update_task_status(task_id, "fetching", {"scout": "running"})
        state = await run_scout_node(state, mcp_pool=mcp_pool)
        items = state.get("scout", {}).get("items", [])
        if not items:
            await _update_task_status(
                task_id, "completed: no items found", {"scout": "success"}
            )
            return
        await _update_task_status(
            task_id, "parsing", {"scout": "success", "parser": "running"}
        )

        # ── Parser ──
        state = await _parser(state, mcp_pool=mcp_pool)
        await _update_task_status(
            task_id,
            "storing",
            {"scout": "success", "parser": "success", "connector": "running"},
        )

        # ── Connector ──
        state = await _connector(state, db)
        await _update_task_status(
            task_id,
            "deciding",
            {
                "scout": "success",
                "parser": "success",
                "connector": "success",
                "actor": "running",
            },
        )

        # ── Actor ──
        state = await _actor(state, db)
        action = state.get("actor", {}).get("action", "proceed")
        if action == "approval_required":
            await _update_task_status(
                task_id,
                "interrupted: awaiting approval",
                {
                    "scout": "success",
                    "parser": "success",
                    "connector": "success",
                    "actor": "interrupted",
                },
            )
            return
        await _update_task_status(
            task_id,
            "curating",
            {
                "scout": "success",
                "parser": "success",
                "connector": "success",
                "actor": "success",
                "curator": "running",
            },
        )

        # ── Curator ──
        state = await _curator(state, db)
        await _update_task_status(
            task_id,
            "completed",
            {
                "scout": "success",
                "parser": "success",
                "connector": "success",
                "actor": "success",
                "curator": "success",
            },
        )

    except Exception as e:
        print(f"[Pipeline] Task {task_id} failed: {e}")
        import traceback

        traceback.print_exc()
        await _update_task_status(task_id, f"error: {str(e)}")
