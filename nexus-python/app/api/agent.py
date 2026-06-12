"""Agent API — 触发采集任务、查询状态、审批恢复"""

import asyncio
import json
import uuid

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db_session, get_redis_client
from app.agents.scout_agent import _update_task_status, get_task_status, AGENT_NODES
from app.agents.state import NexusState
from app.models import Subscription

router = APIRouter()


def _get_supervisor(request: Request):
    """从 app state 获取 NexusSupervisor"""
    return request.app.state.supervisor


def _get_session_factory(request: Request):
    """从 app state 获取 DB session factory"""
    return request.app.state.db_session_factory


@router.post("/tasks")
async def create_task(
    subscription_id: int,
    request: Request,
):
    """通过 Supervisor 触发完整的 5-Agent 采集流水线"""
    # 查询订阅
    factory = _get_session_factory(request)
    async with factory() as db:
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            return {"code": 404, "message": "Subscription not found"}

        keywords = sub.keywords if isinstance(sub.keywords, list) else []
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

    task_id = uuid.uuid4().hex
    supervisor = _get_supervisor(request)

    # 构建初始状态
    initial_state: NexusState = NexusState(
        task_id=task_id,
        subscription_id=subscription_id,
        keywords=keywords,
        source_platforms=platforms,
        user_id=sub.user_id if sub else None,
        next_node="scout",
        status="queued",
    )

    # 持久化初始状态到 Redis（用于审批恢复）
    await _save_task_state(task_id, initial_state, subscription_id, keywords, platforms)

    # 异步执行流水线（后台运行，不阻塞 HTTP 响应）
    asyncio.create_task(_run_pipeline(supervisor, initial_state))

    return {"code": 200, "data": {"task_id": task_id, "status": "queued"}}


async def _save_task_state(
    task_id: str,
    state: NexusState,
    subscription_id: int,
    keywords: list[str],
    platforms: list[str],
) -> None:
    """将完整任务状态持久化到 Redis"""
    try:
        redis = get_redis_client()
        payload = {
            "task_id": task_id,
            "subscription_id": subscription_id,
            "keywords": keywords,
            "source_platforms": platforms,
            "user_id": state.get("user_id"),
            "scout": state.get("scout", {}),
            "parser": state.get("parser", {}),
            "connector": state.get("connector", {}),
            "actor": state.get("actor", {}),
            "curator": state.get("curator", {}),
            "status": state.get("status"),
            "updated_at": None,
        }
        await redis.setex(
            f"agent:state:{task_id}",
            3600,
            json.dumps(payload, ensure_ascii=False, default=str),
        )
    except Exception:
        pass


async def _run_pipeline(supervisor, state: NexusState) -> None:
    """后台执行 Supervisor 流水线"""
    try:
        final_state = await supervisor.run(state)
        task_id = final_state.get("task_id", "")
        status = final_state.get("status", "unknown")
        print(f"[Agent API] Pipeline finished: {task_id} → {status}")

        # 持久化最终状态
        await _save_task_state(
            task_id, final_state,
            final_state.get("subscription_id", 0),
            final_state.get("keywords", []),
            final_state.get("source_platforms", []),
        )
    except Exception as e:
        print(f"[Agent API] Pipeline error: {e}")
        import traceback
        traceback.print_exc()


@router.get("/tasks")
async def list_tasks(page: int = 1, size: int = 20):
    """列出最近的 Agent 任务及其状态"""
    redis = get_redis_client()
    keys = await redis.keys("agent:status:*")
    tasks = []
    for key in keys:
        task_id = key.split(":")[-1] if isinstance(key, str) else key.decode().split(":")[-1]
        data = await redis.get(key)
        if data:
            try:
                status = json.loads(data)
                status["task_id"] = task_id
                tasks.append(status)
            except Exception:
                tasks.append({"task_id": task_id, "status": "unknown"})
    tasks.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    total = len(tasks)
    start = (page - 1) * size
    items = tasks[start:start + size]
    return {"code": 200, "data": {"items": items, "total": total, "page": page, "size": size}}


@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(task_id: str):
    """查询任务执行状态（5 节点）"""
    status = await get_task_status(task_id)
    return {"code": 200, "data": {"task_id": task_id, **status}}


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: str,
    request: Request,
    approved: bool = True,
    comment: str = "",
):
    """审批回调：Java 审批完成后恢复 Agent 状态机执行"""
    status = await get_task_status(task_id)
    if status.get("status") != "interrupted: awaiting approval":
        return {"code": 400, "message": "Task is not in interrupted state"}

    supervisor = _get_supervisor(request)

    if approved:
        asyncio.create_task(_resume_after_approval(supervisor, task_id, approved, comment))
        return {"code": 200, "data": {"task_id": task_id, "status": "resumed"}}
    else:
        await _update_task_status(task_id, "rejected", {
            "scout": "success", "parser": "success", "connector": "success", "actor": "failed",
        })
        return {"code": 200, "data": {"task_id": task_id, "status": "rejected"}}


async def _resume_after_approval(
    supervisor,
    task_id: str,
    approved: bool,
    comment: str,
) -> None:
    """后台恢复执行（审批通过后）"""
    try:
        final_state = await supervisor.resume_after_approval(task_id, approved, comment)
        status = final_state.get("status", "unknown")
        print(f"[Agent API] Resume finished: {task_id} → {status}")
    except Exception as e:
        print(f"[Agent API] Resume error: {e}")
        import traceback
        traceback.print_exc()
