from typing import Any

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import ScoutState
from app.agents.scout_agent import (
    fetch_sources,
    parse_content,
    check_duplicate,
    store_content,
    notify,
    handle_error,
)


def _sync_node(node_fn, mcp_pool: Any, db: AsyncSession):
    """在同步节点中安全运行异步协程（线程隔离，无事件循环冲突）"""
    import asyncio

    def _run(state: ScoutState):
        # 每个节点在独立线程中执行，使用新事件循环
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(node_fn(state, mcp_pool, db))
        finally:
            loop.close()

    return _run


def build_scout_agent(mcp_pool: Any, db: AsyncSession):
    """
    构建 Scout Agent LangGraph 状态机
    流程: fetch → parse → check_duplicate → [store → notify] | END
    """
    graph = StateGraph(ScoutState)

    graph.add_node("fetch", _sync_node(fetch_sources, mcp_pool, db))
    graph.add_node("parse", _sync_node(parse_content, mcp_pool, db))
    graph.add_node("check_duplicate", _sync_node(check_duplicate, mcp_pool, db))
    graph.add_node("store", _sync_node(store_content, mcp_pool, db))
    graph.add_node("notify", _sync_node(notify, mcp_pool, db))
    graph.add_node("error", _sync_node(handle_error, mcp_pool, db))

    graph.add_edge("fetch", "parse")
    graph.add_edge("parse", "check_duplicate")

    def route_after_check(state: ScoutState):
        if state.get("error"):
            return "error"
        if state.get("parsed_contents"):
            return "store"
        return "notify"

    graph.add_conditional_edges(
        "check_duplicate",
        route_after_check,
        {"store": "store", "notify": "notify", "error": "error"},
    )

    graph.add_edge("store", "notify")
    graph.add_edge("notify", END)
    graph.add_edge("error", END)

    graph.set_entry_point("fetch")
    return graph.compile()
