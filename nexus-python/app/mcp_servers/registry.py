import os
from .config import ServerConfig

# 从 nexus-python 的全局配置读取敏感信息
# 如果你的 core/config.py 里没有这些字段，会自动降级到环境变量
try:
    from app.core.config import settings
except Exception:
    settings = None


def _get(key: str, default: str = "") -> str:
    """优先从 settings 读取，其次环境变量"""
    if settings is not None:
        val = getattr(settings, key, None)
        if val is not None:
            return str(val)
    return os.getenv(key, default)


SERVERS: dict[str, ServerConfig] = {
    "email": ServerConfig(
        name="email",
        command="python",
        args=["-m", "app.mcp_servers.nexus_mcp_emails"],
        env={
            "SMTP_HOST": _get("SMTP_HOST", "smtp.qq.com"),
            "SMTP_PORT": _get("SMTP_PORT", "465"),
            "SMTP_USER": _get("SMTP_USER", ""),
            "SMTP_PASS": _get("SMTP_PASS", ""),
        },
        idle_ttl=600,
    ),
    "web": ServerConfig(
        name="web",
        command="python",
        args=["-m", "app.mcp_servers.nexus_mcp_web"],
        idle_ttl=7200,
    ),
    "rss": ServerConfig(
        name="rss",
        command="python",
        args=["-m", "app.mcp_servers.nexus_mcp_rss"],
        idle_ttl=7200,
    ),
    "api": ServerConfig(
        name="api",
        command="python",
        args=["-m", "app.mcp_servers.nexus_mcp_api"],
        idle_ttl=7200,  # 2 小时，适配每小时轮询
    ),
}