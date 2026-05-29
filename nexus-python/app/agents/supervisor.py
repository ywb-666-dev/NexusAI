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


def _wrap(node_fn):
    """包装 async 节点，注入 mcp_pool 和 db_session"""
    def wrapper(state: ScoutState, mcp_pool: Any = None, db: AsyncSession = None):
        import asyncio
        return asyncio.run(node_fn(state, mcp_pool, db))
    return wrapper


def build_scout_agent(mcp_pool: Any, db: AsyncSession):
    """
    构建 Scout Agent LangGraph 状态机
    流程: fetch → parse → check_duplicate → [store → notify] | END
    """
    graph = StateGraph(ScoutState)

    # 注册节点
    graph.add_node("fetch", lambda s: _run_async(fetch_sources(s, mcp_pool, db)))
    graph.add_node("parse", lambda s: _run_async(parse_content(s, db)))
    graph.add_node("check_duplicate", lambda s: _run_async(check_duplicate(s, db)))
    graph.add_node("store", lambda s: _run_async(store_content(s, db)))
    graph.add_node("notify", lambda s: _run_async(notify(s, db)))
    graph.add_node("error", lambda s: _run_async(handle_error(s)))

    # 线性边
    graph.add_edge("fetch", "parse")
    graph.add_edge("parse", "check_duplicate")

    # 条件边：如果有内容且未出错则存储，否则直接结束
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


def _run_async(coro):
    """在同步上下文中运行异步协程"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # 如果已有事件循环，使用 run_coroutine_threadsafe 或 create_task
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()
