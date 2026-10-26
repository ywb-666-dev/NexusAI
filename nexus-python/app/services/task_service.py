"""Single task entry for REST, schedules and message delivery."""

import asyncio
import json
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models import Subscription
from app.models.task import AgentTask
from app.core.dependencies import get_session_factory

BACKGROUND_TASKS: set[asyncio.Task] = set()
LIMIT = asyncio.Semaphore(3)


def parse_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return parse_list(json.loads(value))
        except ValueError:
            pass
    return []


def spawn(coro):
    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    return task


async def create_task(subscription_id: int, user_id: int, supervisor) -> str:
    async with get_session_factory()() as db:
        sub = (
            await db.execute(
                select(Subscription)
                .where(Subscription.id == subscription_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not sub or sub.user_id != user_id:
            raise HTTPException(404, "订阅不存在")
        if sub.status != 1:
            raise HTTPException(409, "订阅已暂停")
        conditions = (
            sub.trigger_conditions if isinstance(sub.trigger_conditions, dict) else {}
        )
        from app.services.auto_sources import resolve_subscription_sources
        from app.services.semantic import SemanticPolicy, compile_intent, SemanticError

        try:
            semantic = SemanticPolicy.model_validate(
                conditions.get("semantic_filter") or {}
            )
            plan = await compile_intent(semantic) if semantic.enabled else None
            feeds, resolution = await resolve_subscription_sources(
                parse_list(sub.rss_feeds), conditions, semantic_plan=plan
            )
        except SemanticError as exc:
            raise HTTPException(503, str(exc))
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        if resolution is not None:
            sub.rss_feeds = feeds
            sub.source_platforms = list(dict.fromkeys(f["platform"] for f in feeds))
        task_id = uuid.uuid4().hex
        state = {
            "task_id": task_id,
            "subscription_id": sub.id,
            "user_id": user_id,
            "keywords": parse_list(sub.keywords),
            "source_platforms": parse_list(sub.source_platforms),
            "rss_feeds": feeds,
            "source_resolution": resolution,
            "semantic_policy": semantic.model_dump() if semantic.enabled else None,
            "semantic_plan": plan,
            "enable_ai": bool(
                (
                    sub.trigger_conditions
                    if isinstance(sub.trigger_conditions, dict)
                    else {}
                ).get("enable_ai", False)
            ),
            "status": "queued",
            "next_node": "scout",
        }
        db.add(
            AgentTask(
                id=task_id,
                subscription_id=sub.id,
                user_id=user_id,
                active_key=str(sub.id),
                state=state,
                nodes={},
                status="queued",
            )
        )
        sub.last_run_at = datetime.utcnow()
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = (
                await db.execute(
                    select(AgentTask.id).where(
                        AgentTask.active_key == str(subscription_id)
                    )
                )
            ).scalar_one_or_none()
            if existing:
                return existing
            raise HTTPException(409, "此订阅已有采集任务正在执行")
    spawn(execute(supervisor, state))
    return task_id


async def save_state(state):
    task_id = state.get("task_id")
    async with get_session_factory()() as db:
        task = await db.get(AgentTask, task_id)
        if task:
            task.state = {**(task.state or {}), **compact_state(state)}
            task.status = (
                "failed"
                if state.get("status", "").startswith("error")
                else state.get("status", task.status)
            )
            task.error = state.get("error")
            if (
                task.status in ("completed", "failed", "rejected")
                or task.status.startswith("error")
                or task.status.startswith("completed:")
                or task.status.startswith("interrupted")
            ):
                task.active_key = None
            task.updated_at = datetime.utcnow()
            await db.commit()


def compact_state(state):
    """Recovery needs IDs and decisions; avoid triplicating full article bodies in JSON."""
    payload = dict(state)
    for key in ("scout", "parser", "connector"):
        if key in payload:
            payload[key] = {
                name: value for name, value in payload[key].items() if name != "items"
            }
    return json.loads(json.dumps(payload, default=str, ensure_ascii=False))


async def execute(supervisor, state):
    async with LIMIT:
        try:
            final = await asyncio.wait_for(
                supervisor.run(state),
                timeout=600 if state.get("semantic_policy") else 300,
            )
            await save_state(final)
            if not final.get("error"):
                async with get_session_factory()() as db:
                    sub = await db.get(Subscription, state["subscription_id"])
                    if sub:
                        sub.last_run_at = datetime.utcnow()
                    await db.commit()
        except asyncio.CancelledError:
            await save_state(
                {**state, "status": "failed", "error": "服务关闭，任务可重新触发"}
            )
            raise
        except Exception as exc:
            await save_state({**state, "status": "failed", "error": str(exc)[:1000]})


async def recover_tasks():
    """Never leave a previous process's active lease permanently locked."""
    async with get_session_factory()() as db:
        rows = (
            (
                await db.execute(
                    select(AgentTask).where(AgentTask.active_key.is_not(None))
                )
            )
            .scalars()
            .all()
        )
        for task in rows:
            task.status = "failed"
            task.error = "上次运行因服务重启中断，请重新触发"
            task.active_key = None
        from app.models.delivery import PushDelivery

        pending = (
            (
                await db.execute(
                    select(PushDelivery).where(PushDelivery.status == "pending")
                )
            )
            .scalars()
            .all()
        )
        for delivery in pending:
            delivery.status = "failed"
            delivery.error = (
                "上次投递因服务重启中断，结果未知；请先确认群消息，再手动重试"
            )
        await db.commit()
