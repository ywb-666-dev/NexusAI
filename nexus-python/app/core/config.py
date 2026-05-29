# app/core/config.py
"""
NexusAI Python 中台 - 全局配置中心
使用 Pydantic Settings 管理，支持 .env 文件与环境变量覆盖
"""

from functools import lru_cache
from typing import Literal, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM 与 Embedding 模型配置"""
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    api_key: str = Field(description="LLM API Key")
    base_url: str | None = Field(default=None, description="API 基础地址，本地模型需配置")
    chat_model: str = Field(default="gpt-4", description="对话模型名")
    
    # Embedding 运行时切换
    embedding_provider: Literal["openai", "bge"] = Field(
        default="openai", 
        description="Embedding 提供商：openai / bge"
    )
    embedding_model: str = Field(
        default="text-embedding-3", 
        description="Embedding 模型名"
    )
    embedding_api_key: str | None = Field(
        default=None, 
        description="Embedding 专用 API Key（如与主 Key 不同）"
    )
    embedding_dimensions: int = Field(
        default=1536, 
        description="向量维度：OpenAI=1536, BGE=1024"
    )
    
    @field_validator("embedding_dimensions", mode="after")
    @classmethod
    def validate_dimensions(cls, v: int, info) -> int:
        """根据 provider 自动校验/修正维度"""
        provider = info.data.get("embedding_provider")
        if provider == "openai" and v != 1536:
            return 1536
        if provider == "bge" and v != 1024:
            return 1024
        return v


class MilvusSettings(BaseSettings):
    """Milvus 向量数据库配置"""
    model_config = SettingsConfigDict(env_prefix="MILVUS_")
    
    host: str = Field(default="localhost", description="Milvus 服务地址")
    port: int = Field(default=19530, description="Milvus gRPC 端口")
    collection: str = Field(
        default="nexus_content_vectors", 
        description="集合名称"
    )
    
    # 相似度阈值（业务核心参数）
    dedup_threshold: float = Field(
        default=0.92, 
        ge=0.0, 
        le=1.0, 
        description="语义去重阈值：高于此值视为重复"
    )
    relate_threshold: float = Field(
        default=0.75, 
        ge=0.0, 
        le=1.0, 
        description="关联推荐阈值：0.75~0.92 区间建立关联"
    )
    top_k: int = Field(default=5, description="相似检索返回数量")


class RocketMQSettings(BaseSettings):
    """RocketMQ 消息队列配置"""
    model_config = SettingsConfigDict(env_prefix="ROCKETMQ_")
    
    nameserver: str = Field(
        default="localhost:9876", 
        description="NameServer 地址，多个用分号分隔"
    )
    producer_group: str = Field(
        default="nexus-python-producers", 
        description="生产者 Group"
    )
    consumer_group: str = Field(
        default="nexus-scout-consumers", 
        description="消费者 Group"
    )
    
    # Topic 名称集中管理
    topic_task_trigger: str = Field(default="nexus-task-trigger")
    topic_content_parsed: str = Field(default="nexus-content-parsed")
    topic_action_required: str = Field(default="nexus-action-required")
    topic_notification: str = Field(default="nexus-notification")
    topic_daily_report: str = Field(default="nexus-daily-report")
    topic_dead_letter: str = Field(default="nexus-dead-letter")


class PlaywrightSettings(BaseSettings):
    """Playwright 浏览器自动化配置"""
    model_config = SettingsConfigDict(env_prefix="PLAYWRIGHT_")
    
    headless: bool = Field(
        default=True, 
        description="是否无头模式，调试可设为 False"
    )
    max_concurrent_browsers: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="并发浏览器实例上限，防止内存打爆"
    )
    timeout_ms: int = Field(
        default=30000, 
        description="单个页面操作超时（毫秒）"
    )
    navigation_timeout_ms: int = Field(
        default=30000, 
        description="页面导航超时（毫秒）"
    )
    
    # User-Agent 池（反爬基础策略）
    user_agents: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ],
        description="User-Agent 轮换池"
    )
    
    # 代理池预留（Phase 2 反爬升级）
    proxy_pool: List[str] = Field(
        default=[], 
        description="代理地址列表，如 http://user:pass@host:port"
    )
    proxy_enabled: bool = Field(
        default=False, 
        description="是否启用代理池"
    )


class DatabaseSettings(BaseSettings):
    """SQL Server 异步数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=1433)
    database: str = Field(default="NexusAI")
    username: str = Field(default="nexus_app_user")
    password: str = Field(default="")
    
    # 异步连接池参数
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="超出 pool_size 的最大连接数")
    pool_timeout: int = Field(default=30, description="获取连接超时秒数")
    echo: bool = Field(
        default=False, 
        description="是否打印 SQL 语句（调试开启）"
    )
    
    @property
    def async_url(self) -> str:
        """构建 SQLAlchemy 异步连接串"""
        return (
            f"mssql+aioodbc://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?driver=ODBC+Driver+17+for+SQL+Server"
        )


class RedisSettings(BaseSettings):
    """Redis 缓存与中间状态配置"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0, ge=0, le=15)
    password: str | None = Field(default=None)
    
    # Key 前缀规范（全局统一，防止冲突）
    prefix_agent_status: str = Field(
        default="agent:status", 
        description="Agent 状态前缀，实际 key: agent:status:{taskId}"
    )
    prefix_mcp_health: str = Field(
        default="mcp:health", 
        description="MCP 健康检查前缀，实际 key: mcp:health:{serverName}"
    )
    prefix_idempotent: str = Field(
        default="idempotent:task", 
        description="幂等 Token 前缀"
    )
    prefix_jwt_blacklist: str = Field(
        default="jwt:blacklist", 
        description="JWT 黑名单前缀"
    )
    prefix_rate_limit: str = Field(
        default="ratelimit", 
        description="限流计数前缀"
    )
    prefix_bloom_url: str = Field(
        default="bloom:url", 
        description="URL 布隆过滤器前缀"
    )
    prefix_distributed_lock: str = Field(
        default="lock:collection", 
        description="分布式锁前缀"
    )
    
    # TTL 配置（秒）
    ttl_agent_status: int = Field(default=3600, description="Agent 状态缓存 1 小时")
    ttl_idempotent: int = Field(default=86400, description="幂等 Token 24 小时")
    ttl_jwt_blacklist: int = Field(default=86400, description="JWT 黑名单与 Token 过期一致")


class Settings(BaseSettings):
    """全局配置根节点"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未定义的环境变量，防止冲突
    )
    
    # 环境标识
    env: Literal["development", "testing", "production"] = Field(
        default="development", 
        alias="NEXUS_ENV"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    
    # 服务配置
    app_name: str = Field(default="nexus-python", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    
    # 嵌套子配置
    llm: LLMSettings = Field(default_factory=LLMSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    rocketmq: RocketMQSettings = Field(default_factory=RocketMQSettings)
    playwright: PlaywrightSettings = Field(default_factory=PlaywrightSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    
    # 日志
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", 
        alias="LOG_LEVEL"
    )
    json_logs: bool = Field(
        default=False, 
        alias="JSON_LOGS", 
        description="是否输出结构化 JSON 日志"
    )


@lru_cache
def get_settings() -> Settings:
    """单例获取配置，避免重复解析环境变量"""
    return Settings()


# 全局导出，供其他模块直接导入
settings = get_settings()