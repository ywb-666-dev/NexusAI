from pydantic import BaseModel, Field
from typing import Literal


class ServerConfig(BaseModel):
    """描述一个 MCP Server 子进程的启动参数与运行时策略"""

    name: str
    command: str = "python"
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    transport: Literal["stdio"] = "stdio"

    # 运行时策略
    idle_ttl: int = 300              # 空闲超时（秒），超后自动关闭
    health_check_interval: int = 30  # 健康检查间隔（秒）
    max_retry: int = 3               # call_tool 失败重试次数
    max_instances: int = 1           # 同类型 Server 最大并发实例数（预留）