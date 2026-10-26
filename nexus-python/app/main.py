"""NexusAI AI service: lifecycle, authenticated routes and task status stream."""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from sqlalchemy import text
from app.core.auth import current_user, decode_user
from app.core.dependencies import (
    get_session_factory,
    close_db_engine,
    close_redis_client,
)
from app.agents.supervisor import NexusSupervisor
from app.services.task_service import BACKGROUND_TASKS, recover_tasks
from app.models.task import AgentTask


@asynccontextmanager
async def lifespan(app):
    from app.skills import SkillRegistry
    from app.skills.builtins import (
        ScoutSkill,
        TranslateSkill,
        SummarizeSkill,
        DiscoverSourcesSkill,
        DedupSkill,
    )
    from app.harness.base import AgentHarness

    app.state.mcp_pool = None
    if os.getenv("MCP_ENABLED", "false").lower() == "true":
        from app.mcp_servers import MCPPool, SERVERS

        pool = MCPPool()
        for config in SERVERS.values():
            pool.register(config)
        app.state.mcp_pool = pool
    app.state.db_session_factory = get_session_factory()
    app.state.supervisor = NexusSupervisor(
        app.state.mcp_pool, app.state.db_session_factory
    )
    registry = SkillRegistry()
    for skill in [
        ScoutSkill(app.state.mcp_pool),
        TranslateSkill(),
        SummarizeSkill(),
        DedupSkill(),
        DiscoverSourcesSkill(),
    ]:
        registry.register(skill)
    app.state.skill_registry, app.state.harness = registry, AgentHarness()
    await recover_tasks()
    from app.services import briefing as briefing_service

    await briefing_service.recover()
    briefing_scheduler = asyncio.create_task(briefing_service.scheduler())
    from app.scheduler import start_scheduler

    scheduler = asyncio.create_task(start_scheduler(app.state.supervisor))
    from app.services.source_maintenance import run_maintenance

    source_maintenance = asyncio.create_task(run_maintenance())
    try:
        yield
    finally:
        scheduler.cancel()
        briefing_scheduler.cancel()
        source_maintenance.cancel()
        for task in list(BACKGROUND_TASKS):
            task.cancel()
        await asyncio.gather(
            scheduler,
            briefing_scheduler,
            source_maintenance,
            *list(BACKGROUND_TASKS),
            return_exceptions=True
        )
        if app.state.mcp_pool:
            await app.state.mcp_pool.close_all()
        await close_db_engine()
        await close_redis_client()


app = FastAPI(title="NexusAI 内容采集中台", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    return JSONResponse(
        {"code": 422, "message": "请求参数不合法，请检查输入字段"}, status_code=422
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.exception("Request failed: %s %s", request.method, request.url.path)
    return JSONResponse(
        {"code": 500, "message": "服务暂时不可用，请稍后重试"}, status_code=500
    )


@app.middleware("http")
async def authenticate(request: Request, call_next):
    if request.url.path.startswith("/api/python/"):
        try:
            request.state.user = current_user(request)
        except HTTPException as exc:
            return JSONResponse(
                {"code": exc.status_code, "message": exc.detail},
                status_code=exc.status_code,
            )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        {"code": exc.status_code, "message": exc.detail}, status_code=exc.status_code
    )


@app.get("/health")
async def health():
    try:
        async with get_session_factory()() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "nexus-python", "database": "ok"}
    except Exception:
        return JSONResponse(
            {"status": "degraded", "database": "unavailable"}, status_code=503
        )


@app.websocket("/api/python/ws/agent/{task_id}")
async def task_socket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        # Credentials arrive as the first frame, never in URLs or access logs.
        credentials = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        user = decode_user(credentials.get("token", ""))
        from app.api.agent import owned_task, serialize

        previous = None
        while True:
            data = serialize(await owned_task(task_id, user))
            if data != previous:
                await websocket.send_json(data)
                previous = data
            if data["status"] in ("completed", "failed", "rejected") or data[
                "status"
            ].startswith(("interrupted", "error", "completed:")):
                break
            await asyncio.sleep(1)
        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1008)


from app.api import (
    agent,
    content,
    subscription,
    notification,
    skill,
    push,
    sources,
    briefing,
)

app.include_router(briefing.router, prefix="/api/python/briefings", tags=["briefings"])

app.include_router(sources.router, prefix="/api/python/sources", tags=["sources"])

app.include_router(agent.router, prefix="/api/python/agent", tags=["tasks"])
app.include_router(content.router, prefix="/api/python/contents", tags=["contents"])
app.include_router(
    subscription.router, prefix="/api/python/subscriptions", tags=["subscriptions"]
)
app.include_router(
    notification.router, prefix="/api/python/notifications", tags=["notifications"]
)
app.include_router(skill.router, prefix="/api/python", tags=["skills"])
app.include_router(push.router, prefix="/api/python/push", tags=["push"])
