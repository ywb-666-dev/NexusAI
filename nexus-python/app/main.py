import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.mcp_servers import MCPPool, SERVERS
from app.memory.milvus_client import milvus_client
from app.core.dependencies import close_db_engine, close_redis_client


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


from app.api import agent, content, subscription, notification

app.include_router(agent.router, prefix="/api/python/agent", tags=["agent"])
app.include_router(content.router, prefix="/api/python/contents", tags=["content"])
app.include_router(subscription.router, prefix="/api/python/subscriptions", tags=["subscription"])
app.include_router(notification.router, prefix="/api/python/notifications", tags=["notification"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
