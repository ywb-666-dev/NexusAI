import asyncio
from datetime import datetime

from .config import ServerConfig
from .client_wrapper import ClientWrapper


class MCPPool:
    """MCP Server 连接池：懒加载、复用、异常重连"""

    def __init__(self):
        self._registry: dict[str, ServerConfig] = {}
        self._clients: dict[str, ClientWrapper] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._running = True

    def register(self, config: ServerConfig) -> None:
        """注册 Server 配置（只注册，不启动进程）"""
        self._registry[config.name] = config
        self._locks[config.name] = asyncio.Lock()

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        """统一调用入口：懒加载 + 连接复用 + 一次异常重连"""
        if server_name not in self._registry:
            raise ValueError(f"Unknown MCP server: {server_name}")

        # 懒加载：首次调用或连接死亡时创建
        wrapper = self._clients.get(server_name)
        if wrapper is None or not wrapper.is_alive():
            async with self._locks[server_name]:
                # 双重检查
                wrapper = self._clients.get(server_name)
                if wrapper is None or not wrapper.is_alive():
                    cfg = self._registry[server_name]
                    wrapper = ClientWrapper(cfg)
                    await wrapper.connect()
                    self._clients[server_name] = wrapper

        try:
            return await wrapper.call_tool(tool_name, arguments)
        except Exception:
            # 调用失败：关闭旧连接，重建一次后重试
            await wrapper.close()
            self._clients.pop(server_name, None)

            async with self._locks[server_name]:
                cfg = self._registry[server_name]
                wrapper = ClientWrapper(cfg)
                await wrapper.connect()
                self._clients[server_name] = wrapper
                return await wrapper.call_tool(tool_name, arguments)

    def get_status(self) -> dict:
        """查询所有注册 Server 的当前状态"""
        return {
            name: {
                "registered": True,
                "connected": name in self._clients and self._clients[name].is_alive(),
                "last_used": (
                    self._clients[name].last_used.isoformat()
                    if name in self._clients and self._clients[name].last_used
                    else None
                ),
            }
            for name in self._registry
        }

    async def close_all(self) -> None:
        """优雅关闭所有活跃连接"""
        self._running = False
        for wrapper in list(self._clients.values()):
            await wrapper.close()
        self._clients.clear()

    # ========== 后台守护任务（骨架已留，内部逻辑待补） ==========

    async def _health_check_loop(self) -> None:
        """每 30 秒检查一次所有活跃连接的健康状态"""
        while self._running:
            await asyncio.sleep(self._registry[list(self._registry)[0]].health_check_interval if self._registry else 30)
            for name, wrapper in list(self._clients.items()):
                ok = await wrapper.health_check()
                if not ok and wrapper._health_fail_count >= 3:
                    await wrapper.close()
                    self._clients.pop(name, None)

    async def _gc_loop(self) -> None:
        """每 60 秒回收空闲超时的连接"""
        while self._running:
            await asyncio.sleep(60)
            now = datetime.now()
            for name, wrapper in list(self._clients.items()):
                cfg = self._registry[name]
                if wrapper.last_used and (now - wrapper.last_used).total_seconds() > cfg.idle_ttl:
                    await wrapper.close()
                    self._clients.pop(name, None)