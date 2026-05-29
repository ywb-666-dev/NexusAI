from fastapi import Request
from app.mcp_servers import MCPPool


class MCPService:
    """对 Agent 暴露业务语义接口，屏蔽底层 Pool 细节"""

    def __init__(self, pool: MCPPool):
        self.pool = pool

    async def send_email(self, from_addr: str, to: str, subject: str, text: str):
        return await self.pool.call_tool(
            "email", "send_email",
            {"from_addr": from_addr, "to": to, "subject": subject, "text": text}
        )

    async def scrape_page(self, url: str, wait_for: str | None = None):
        return await self.pool.call_tool(
            "web", "scrape_page",
            {"url": url, "wait_for_selector": wait_for}
        )

    async def fetch_rss(self, url: str):
        return await self.pool.call_tool(
            "rss", "fetch_rss",
            {"url": url}
        )

    async def call_api(self, endpoint: str, method: str = "GET", params: dict | None = None):
        return await self.pool.call_tool(
            "api", "call_api",
            {"endpoint": endpoint, "method": method, "params": params or {}}
        )


def get_mcp_service(request: Request) -> MCPService:
    """FastAPI Depends 用工厂函数"""
    return MCPService(request.app.state.mcp_pool)