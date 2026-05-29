from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import asyncio

from app.services.mcp_servers import MCPPool, SERVERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时注册 MCP Pool，停机时优雅关闭"""
    # ===== Startup =====
    pool = MCPPool()
    for cfg in SERVERS.values():
        pool.register(cfg)

    # 启动后台守护任务
    asyncio.create_task(pool._health_check_loop())
    asyncio.create_task(pool._gc_loop())

    app.state.mcp_pool = pool
    yield

    # ===== Shutdown =====
    await pool.close_all()


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


# ============================================================
# 后续你的路由不要全写在这里，用 app.include_router() 拆分出去
# 例如：
# from app.api import agent, content
# app.include_router(agent.router, prefix="/api/python/agent")
# app.include_router(content.router, prefix="/api/python/contents")
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)