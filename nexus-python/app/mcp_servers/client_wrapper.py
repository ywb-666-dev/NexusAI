import os
import asyncio
from datetime import datetime
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import ServerConfig


class ClientWrapper:
    """封装单个 MCP Server 子进程 + ClientSession 的完整生命周期"""

    def __init__(self, config: ServerConfig):
        self.cfg = config
        self.session: ClientSession | None = None
        self._stack = AsyncExitStack()
        self.last_used: datetime | None = None
        self._health_fail_count = 0
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """启动子进程并完成 MCP handshake"""
        async with self._lock:
            if self.is_alive():
                return

            # 如果之前有半开连接，先彻底清理
            if self.session is not None:
                await self.close()
                self._stack = AsyncExitStack()

            params = StdioServerParameters(
                command=self.cfg.command,
                args=self.cfg.args,
                env={**os.environ, **self.cfg.env},
                cwd=self.cfg.cwd,
            )

            read_stream, write_stream = await self._stack.enter_async_context(
                stdio_client(params)
            )
            self.session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()

            self.last_used = datetime.now()
            self._health_fail_count = 0

    async def call_tool(self, tool_name: str, arguments: dict):
        """透传调用工具，自动更新最后使用时间"""
        if not self.is_alive():
            await self.connect()

        self.last_used = datetime.now()
        result = await self.session.call_tool(tool_name, arguments)
        self._health_fail_count = 0
        return result

    async def health_check(self) -> bool:
        """Ping 检测：可用 list_tools() 验证通道是否存活"""
        if not self.is_alive():
            return False
        try:
            await self.session.list_tools()
            self._health_fail_count = 0
            return True
        except Exception:
            self._health_fail_count += 1
            return False

    def is_alive(self) -> bool:
        """判断当前连接是否可用"""
        if self.session is None:
            return False
        return self._health_fail_count < 3

    async def close(self) -> None:
        """优雅关闭 Session 并终止子进程"""
        await self._stack.aclose()
        self.session = None
        self.last_used = None
        self._health_fail_count = 0