"""Authenticated, durable task API."""

import json
from fastapi import APIRouter, Request, HTTPException, Query
from sqlalchemy import select, func
from app.core.auth import current_user
from app.core.dependencies import get_session_factory
from app.models.task import AgentTask
from app.models import ApprovalTicket, Content, Notification
from app.services.task_service import create_task as enqueue, save_state, spawn

router = APIRouter()


async def owned_task(task_id, user):
    async with get_session_factory()() as db:
        task = await db.get(AgentTask, task_id)
        if not task or (task.user_id != user["id"] and user["role"] != "admin"):
            raise HTTPException(404, "任务不存在")
        return task


@router.post("/tasks")
async def create_task(subscription_id: int, request: Request):
    user = current_user(request)
    task_id = await enqueue(subscription_id, user["id"], request.app.state.supervisor)
    return {"code": 200, "data": {"task_id": task_id, "status": "queued"}}


@router.get("/tasks")
async def list_tasks(
    request: Request, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)
):
    user = current_user(request)
    async with get_session_factory()() as db:
        query = select(AgentTask)
        if user["role"] != "admin":
            query = query.where(AgentTask.user_id == user["id"])
        total = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar()
        rows = (
            (
                await db.execute(
                    query.order_by(AgentTask.created_at.desc())
                    .offset((page - 1) * size)
                    .limit(size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "code": 200,
            "data": {"items": [serialize(t) for t in rows], "total": total},
        }


def serialize(task):
    state = task.state or {}
    return {
        "task_id": task.id,
        "subscription_id": task.subscription_id,
        "status": task.status,
        "nodes": task.nodes or {},
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "counts": {
            k: state.get("connector", {}).get(k, 0)
            for k in ["stored_count", "duplicate_count"]
        },
        "source_errors": state.get("scout", {}).get("source_errors", []),
        "report": state.get("curator", {}).get("report", ""),
    }


@router.get("/tasks/{task_id}/status")
async def status(task_id: str, request: Request):
    return {
        "code": 200,
        "data": serialize(await owned_task(task_id, current_user(request))),
    }


@router.post("/tasks/{task_id}/retry")
async def retry(task_id: str, request: Request):
    user = current_user(request)
    task = await owned_task(task_id, user)
    if task.status not in ["failed"] and not task.status.startswith("error"):
        raise HTTPException(409, "仅失败的任务可重试，拒绝的内容不会自动重新发布")
    new_id = await enqueue(
        task.subscription_id, user["id"], request.app.state.supervisor
    )
    return {"code": 200, "data": {"task_id": new_id}}


@router.post("/tasks/{task_id}/resume")
async def resume(
    task_id: str, request: Request, approved: bool | None = None, comment: str = ""
):
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    async with get_session_factory()() as db:
        task = (
            await db.execute(
                select(AgentTask).where(AgentTask.id == task_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not task:
            raise HTTPException(404, "任务不存在")
        if task.status != "interrupted: awaiting approval":
            raise HTTPException(409, "任务不在待审状态")
        ticket = (
            await db.execute(
                select(ApprovalTicket).where(ApprovalTicket.task_id == task_id)
            )
        ).scalar_one_or_none()
        if not ticket or ticket.status not in (1, 2):
            raise HTTPException(409, "请先在审批中心处理工单")
        if approved is None:
            approved = ticket.status == 1
        if ticket.status != (1 if approved else 2):
            raise HTTPException(409, "审批结果不一致")
        state = dict(task.state)
        ids = state.get("connector", {}).get("stored_ids", [])
        if ids:
            from sqlalchemy import update

            await db.execute(
                update(Content)
                .where(Content.id.in_(ids), Content.status == 2)
                .values(status=1 if approved else 0)
            )
        state["status"] = "curating" if approved else "rejected"
        task.status = state["status"]
        if not approved:
            db.add(Notification(user_id=task.user_id, type='approval', title='内容审核未通过',
                                content=ticket.comment or '管理员已拒绝发布该批内容', related_id=task_id, is_read=0))
        await db.commit()
    await save_state(state)
    if approved:
        spawn(resume_curator(request.app.state.supervisor, state))
    return {"code": 200, "data": {"task_id": task_id, "status": state["status"]}}


async def resume_curator(supervisor, state):
    try:
        state = await supervisor._curator_node(state)
    except Exception as exc:
        state.update(status="failed", error=str(exc))
    await save_state(state)
