import asyncio
import json
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from app.mcp_servers import MCPPool, SERVERS
from app.memory.milvus_client import milvus_client
from app.core.dependencies import close_db_engine, close_redis_client, get_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时注册各类连接池，停机时优雅关闭"""
    # ===== Startup =====
    # MCP Pool
    pool = MCPPool()
    for cfg in SERVERS.values():
        pool.register(cfg)
    asyncio.create_task(pool._health_check_loop())
    asyncio.create_task(pool._gc_loop())
    app.state.mcp_pool = pool

    # Milvus
    try:
        milvus_client.connect()
    except Exception as e:
        print(f"[Startup] Milvus connect warning: {e}")

    # RocketMQ Consumer（在后台线程启动，避免阻塞主事件循环）
    try:
        from app.messaging.consumer import NexusMQConsumer
        consumer = NexusMQConsumer(pool)
        app.state.mq_consumer = consumer
        thread = threading.Thread(target=consumer.start, daemon=True)
        thread.start()
    except Exception as e:
        print(f"[Startup] MQ consumer warning: {e}")

    # Scheduler: 每小时轮询活跃订阅并触发采集
    try:
        from app.scheduler import start_scheduler
        scheduler_task = asyncio.create_task(start_scheduler(pool))
        app.state.scheduler_task = scheduler_task
        print("[Startup] Scheduler started (hourly poll)")
    except Exception as e:
        print(f"[Startup] Scheduler warning: {e}")

    # Supervisor: 5-Agent LangGraph 状态机编排器
    try:
        from app.agents.supervisor import NexusSupervisor
        from app.core.dependencies import get_session_factory

        db_session_factory = get_session_factory()
        app.state.db_session_factory = db_session_factory

        supervisor = NexusSupervisor(
            mcp_pool=pool,
            session_factory=db_session_factory,
        )
        app.state.supervisor = supervisor
        print("[Startup] NexusSupervisor initialized (5-agent state machine)")
    except Exception as e:
        print(f"[Startup] Supervisor warning: {e}")

    # Skill Registry: 注册 Agent 技能
    try:
        from app.skills import SkillRegistry
        from app.skills.builtins import ScoutSkill, TranslateSkill, SummarizeSkill, DiscoverSourcesSkill
        from app.harness.base import AgentHarness, LoggingMiddleware

        skill_registry = SkillRegistry()
        skill_registry.register(ScoutSkill(mcp_pool=pool))
        skill_registry.register(TranslateSkill())
        skill_registry.register(SummarizeSkill())
        skill_registry.register(DedupSkill())
        skill_registry.register(DiscoverSourcesSkill())

        harness = AgentHarness(max_retries=2)
        harness.on_before(LoggingMiddleware.before)
        harness.on_after(LoggingMiddleware.after)

        app.state.skill_registry = skill_registry
        app.state.harness = harness
        print(f"[Startup] Skill Registry: {len(skill_registry)} skills registered")
    except Exception as e:
        print(f"[Startup] Skill system warning: {e}")

    yield

    # ===== Shutdown =====
    # Scheduler
    if hasattr(app.state, "scheduler_task"):
        app.state.scheduler_task.cancel()
        try:
            await app.state.scheduler_task
        except asyncio.CancelledError:
            pass

    # MQ Consumer
    if hasattr(app.state, "mq_consumer"):
        try:
            app.state.mq_consumer.stop()
        except Exception as e:
            print(f"[Shutdown] MQ consumer stop error: {e}")

    # MCP Pool
    await pool.close_all()

    # Milvus
    try:
        milvus_client.disconnect()
    except Exception as e:
        print(f"[Shutdown] Milvus disconnect error: {e}")

    # DB Engine
    try:
        await close_db_engine()
    except Exception as e:
        print(f"[Shutdown] DB engine dispose error: {e}")

    # Redis
    try:
        await close_redis_client()
    except Exception as e:
        print(f"[Shutdown] Redis close error: {e}")


app = FastAPI(
    title="NexusAI Python 中台",
    description="Agent 编排 / 向量检索 / MCP 工具管理",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """服务健康检查"""
    return {"status": "ok", "service": "nexus-python"}


@app.get("/api/python/mcp/servers")
async def mcp_servers_status(request: Request):
    """查询所有 MCP Server 的注册与在线状态"""
    pool: MCPPool = request.app.state.mcp_pool
    return {
        "code": 200,
        "data": pool.get_status(),
    }


@app.get("/api/python/mcp/servers/{name}/health")
async def mcp_server_health(name: str, request: Request):
    """查询指定 MCP Server 的实时健康状态"""
    pool: MCPPool = request.app.state.mcp_pool
    if name not in pool._registry:
        return {"code": 404, "message": f"Server '{name}' not registered"}

    wrapper = pool._clients.get(name)
    is_connected = wrapper.is_alive() if wrapper else False

    return {
        "code": 200,
        "data": {
            "name": name,
            "connected": is_connected,
            "last_used": wrapper.last_used.isoformat() if wrapper and wrapper.last_used else None,
        },
    }


@app.websocket("/api/python/ws/agent/{task_id}")
async def agent_status_websocket(websocket: WebSocket, task_id: str):
    """WebSocket 实时推送 Agent 任务状态（5 节点状态机）"""
    await websocket.accept()
    redis = get_redis_client()
    key = f"agent:status:{task_id}"
    last_status: str | None = None
    try:
        while True:
            try:
                data = await redis.get(key)
                if isinstance(data, bytes):
                    current = data.decode()
                else:
                    current = data
                if current != last_status:
                    last_status = current
                    if current:
                        await websocket.send_text(current)
                    else:
                        await websocket.send_text(json.dumps({
                            "task_id": task_id,
                            "status": "unknown",
                            "nodes": {n: {"status": "idle", "timestamp": None} for n in ["scout", "parser", "connector", "actor", "curator"]},
                            "updated_at": None,
                        }))
                await asyncio.sleep(0.5)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[WS] Error for {task_id}: {e}")
                await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


from app.api import agent, content, subscription, notification, skill

app.include_router(agent.router, prefix="/api/python/agent", tags=["agent"])
app.include_router(content.router, prefix="/api/python/contents", tags=["content"])
app.include_router(subscription.router, prefix="/api/python/subscriptions", tags=["subscription"])
app.include_router(notification.router, prefix="/api/python/notifications", tags=["notification"])
app.include_router(skill.router, prefix="/api/python", tags=["skills"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
