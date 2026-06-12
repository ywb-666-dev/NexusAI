"""NexusAI Supervisor — LangGraph 5-Agent 状态机编排器

流程: Scout → Parser → Connector → Actor → Curator

支持：
- 条件边路由（每个节点完成后决定下一步）
- 人工审批中断（Actor 高风险时挂起，等待外部审批回调）
- 错误处理与降级
- Redis 实时状态同步（用于 WebSocket 推送到前端）
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Literal

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.agents.state import NexusState
from app.agents.scout_agent import (
    run_scout_node,
    _update_task_status,
    AGENT_NODES,
)
from app.agents.parser_agent import run_parser
from app.agents.connector_agent import run_connector
from app.agents.actor_agent import run_actor
from app.agents.curator_agent import run_curator


# ── 路由函数 ──

def _route_after_scout(state: NexusState) -> Literal["parser", "__end__"]:
    """Scout 完成后的路由"""
    if state.get("error"):
        return "__end__"
    items = state.get("scout", {}).get("items", [])
    if not items:
        # 无内容时跳过后续节点，直接结束
        state["status"] = "completed: no items"
        return "__end__"
    return "parser"


def _route_after_parser(state: NexusState) -> Literal["connector", "__end__"]:
    """Parser 完成后的路由"""
    if state.get("error"):
        return "__end__"
    return "connector"


def _route_after_connector(state: NexusState) -> Literal["actor", "__end__"]:
    """Connector 完成后的路由"""
    if state.get("error"):
        return "__end__"
    return "actor"


def _route_after_actor(state: NexusState) -> Literal["curator", "__interrupt__", "__end__"]:
    """Actor 完成后的路由：高风险时中断等待审批"""
    if state.get("error"):
        return "__end__"
    action = state.get("actor", {}).get("action", "proceed")
    if action == "approval_required":
        return "__interrupt__"
    return "curator"


def _route_after_curator(state: NexusState) -> Literal["__end__"]:
    return "__end__"


# ── Supervisor 类 ──

class NexusSupervisor:
    """
    NexusAI 5-Agent 编排器。

    持有 MCP Pool 和 DB Session Factory 引用，
    通过 LangGraph StateGraph 编排完整采集流水线。
    """

    def __init__(
        self,
        mcp_pool: Any = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.mcp_pool = mcp_pool
        self.session_factory = session_factory
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 5 节点状态机"""
        workflow = StateGraph(NexusState)

        # 添加五个 Agent 节点
        workflow.add_node("scout", self._scout_node)
        workflow.add_node("parser", self._parser_node)
        workflow.add_node("connector", self._connector_node)
        workflow.add_node("actor", self._actor_node)
        workflow.add_node("curator", self._curator_node)

        # 设置入口
        workflow.set_entry_point("scout")

        # 条件边：每个节点完成后决定下一步
        workflow.add_conditional_edges("scout", _route_after_scout, {
            "parser": "parser",
            "__end__": END,
        })
        workflow.add_conditional_edges("parser", _route_after_parser, {
            "connector": "connector",
            "__end__": END,
        })
        workflow.add_conditional_edges("connector", _route_after_connector, {
            "actor": "actor",
            "__end__": END,
        })
        workflow.add_conditional_edges("actor", _route_after_actor, {
            "curator": "curator",
            "__interrupt__": END,  # 中断时结束当前执行，等待 resume
            "__end__": END,
        })
        workflow.add_conditional_edges("curator", _route_after_curator, {
            "__end__": END,
        })

        return workflow.compile()

    # ── 各节点包装方法 ──

    async def _scout_node(self, state: NexusState) -> NexusState:
        """Scout 节点：采集原始内容 + Redis 状态同步"""
        task_id = state.get("task_id", "")
        status = state.get("status", "fetching")

        await _update_task_status(task_id, status, {"scout": "running"})

        try:
            state = await run_scout_node(state, mcp_pool=self.mcp_pool)
        except Exception as e:
            print(f"[Supervisor] Scout node error: {e}")
            state["error"] = f"Scout failed: {e}"
            state["status"] = f"error: {e}"
            await _update_task_status(task_id, state["status"], {"scout": "failed"})
            return state

        node_status = "success" if state.get("scout", {}).get("items") else "success"
        await _update_task_status(task_id, "parsing", {"scout": node_status, "parser": "running"})
        state["status"] = "parsing"
        return state

    async def _parser_node(self, state: NexusState) -> NexusState:
        """Parser 节点：清洗解析 + Redis 状态同步"""
        task_id = state.get("task_id", "")

        try:
            state = await run_parser(state, mcp_pool=self.mcp_pool)
        except Exception as e:
            print(f"[Supervisor] Parser node error: {e}")
            state["error"] = f"Parser failed: {e}"
            state["status"] = f"error: {e}"
            await _update_task_status(task_id, state["status"], {"scout": "success", "parser": "failed"})
            return state

        await _update_task_status(task_id, "storing", {
            "scout": "success", "parser": "success", "connector": "running",
        })
        state["status"] = "storing"
        return state

    async def _connector_node(self, state: NexusState) -> NexusState:
        """Connector 节点：去重存储 + Redis 状态同步"""
        task_id = state.get("task_id", "")

        if not self.session_factory:
            state["error"] = "No DB session factory configured"
            state["status"] = "error: no db"
            await _update_task_status(task_id, state["status"])
            return state

        try:
            async with self.session_factory() as db:
                state = await run_connector(state, db)
        except Exception as e:
            print(f"[Supervisor] Connector node error: {e}")
            state["error"] = f"Connector failed: {e}"
            state["status"] = f"error: {e}"
            await _update_task_status(task_id, state["status"], {
                "scout": "success", "parser": "success", "connector": "failed",
            })
            return state

        await _update_task_status(task_id, "deciding", {
            "scout": "success", "parser": "success", "connector": "success", "actor": "running",
        })
        state["status"] = "deciding"
        return state

    async def _actor_node(self, state: NexusState) -> NexusState:
        """Actor 节点：决策评估 + Redis 状态同步"""
        task_id = state.get("task_id", "")

        try:
            async with (self.session_factory() if self.session_factory else _null_ctx()) as db:
                state = await run_actor(state, db if self.session_factory else None)
        except Exception as e:
            print(f"[Supervisor] Actor node error: {e}")
            state["error"] = f"Actor failed: {e}"
            state["status"] = f"error: {e}"
            await _update_task_status(task_id, state["status"], {
                "scout": "success", "parser": "success", "connector": "success", "actor": "failed",
            })
            return state

        action = state.get("actor", {}).get("action", "proceed")
        if action == "approval_required":
            await _update_task_status(task_id, "interrupted: awaiting approval", {
                "scout": "success", "parser": "success", "connector": "success", "actor": "interrupted",
            })
        else:
            await _update_task_status(task_id, "curating", {
                "scout": "success", "parser": "success", "connector": "success",
                "actor": "success", "curator": "running",
            })
        state["status"] = "curating" if action != "approval_required" else "interrupted: awaiting approval"
        return state

    async def _curator_node(self, state: NexusState) -> NexusState:
        """Curator 节点：日报生成 + Redis 状态同步"""
        task_id = state.get("task_id", "")

        try:
            async with (self.session_factory() if self.session_factory else _null_ctx()) as db:
                state = await run_curator(state, db if self.session_factory else None)
        except Exception as e:
            print(f"[Supervisor] Curator node error: {e}")
            state["error"] = f"Curator failed: {e}"
            state["status"] = f"error: {e}"
            await _update_task_status(task_id, state["status"], {
                "scout": "success", "parser": "success", "connector": "success",
                "actor": "success", "curator": "failed",
            })
            return state

        await _update_task_status(task_id, "completed", {
            "scout": "success", "parser": "success", "connector": "success",
            "actor": "success", "curator": "success",
        })
        state["status"] = "completed"
        return state

    # ── 公开 API ──

    async def run(self, initial_state: NexusState) -> NexusState:
        """
        执行完整的 5-Agent 流水线。

        Args:
            initial_state: 包含 task_id, subscription_id, keywords, source_platforms 的初始状态

        Returns:
            最终 NexusState（包含所有阶段的输出）
        """
        if not self.mcp_pool:
            print("[Supervisor] WARNING: No MCP pool configured — Scout will have no tools")
        if not self.session_factory:
            print("[Supervisor] WARNING: No DB session factory — Connector/Actor/Curator will skip DB ops")

        result = await self.graph.ainvoke(initial_state)
        return result

    async def resume_after_approval(
        self,
        task_id: str,
        approved: bool,
        comment: str = "",
    ) -> NexusState:
        """
        审批后恢复执行。

        当 Actor 因高风险创建审批工单后，外部（Java 审批模块）审批完成后
        调用此方法恢复流程。通过则继续 Curator 阶段，拒绝则标记失败。
        """
        if not approved:
            await _update_task_status(task_id, "rejected", {
                "scout": "success", "parser": "success", "connector": "success", "actor": "failed",
            })
            return NexusState(
                task_id=task_id,
                status="rejected",
                error=f"Approval rejected: {comment}",
            )

        # 读取当前状态，从 Actor 之后继续
        status = await _get_task_state(task_id)
        resume_state = NexusState(
            task_id=task_id,
            subscription_id=status.get("subscription_id", 0),
            keywords=status.get("keywords", []),
            source_platforms=status.get("source_platforms", []),
            user_id=status.get("user_id"),
            scout=status.get("scout", {}),
            parser=status.get("parser", {}),
            connector=status.get("connector", {}),
            actor=status.get("actor", {}),
            next_node="curator",
            status="curating",
        )

        await _update_task_status(task_id, "curating", {
            "scout": "success", "parser": "success", "connector": "success",
            "actor": "success", "curator": "running",
        })

        # 从 Curator 节点继续执行
        state = await self._curator_node(resume_state)
        return state


async def _get_task_state(task_id: str) -> dict:
    """从 Redis 读取完整的任务状态（用于审批后恢复）"""
    try:
        from app.core.dependencies import get_redis_client
        redis = get_redis_client()
        data = await redis.get(f"agent:state:{task_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {}


class _null_ctx:
    """异步空上下文，当 db session factory 不可用时使用"""
    async def __aenter__(self): return None
    async def __aexit__(self, *args): pass
