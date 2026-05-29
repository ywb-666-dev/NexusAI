# app/core/dependencies.py
"""
全局依赖注入层
提供 FastAPI Depends 可用的异步 Session、Redis 客户端工厂，
以及应用生命周期所需的连接关闭钩子。
"""

from typing import AsyncGenerator
from redis.asyncio import ConnectionPool as RedisConnectionPool
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import settings

# ==========================================
# SQL Server - SQLAlchemy 异步连接池
# ==========================================

_async_engine = None
_async_session_factory: async_sessionmaker | None = None


def _get_async_engine():
    """懒加载创建异步引擎（单例）"""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.db.async_url,
            pool_size=settings.db.pool_size,
            max_overflow=settings.db.max_overflow,
            pool_timeout=settings.db.pool_timeout,
            echo=settings.db.echo,
            future=True,
        )
    return _async_engine


def _get_async_session_factory() -> async_sessionmaker:
    """懒加载创建 AsyncSession 工厂（单例）"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = _get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Depends 注入用：
    每个请求/任务独立获取一个 AsyncSession，退出时自动提交或回滚。
    """
    factory = _get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_engine() -> None:
    """应用关闭时释放 SQLAlchemy 连接池"""
    global _async_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None


# ==========================================
# Redis - 全局异步连接池
# ==========================================

_redis_pool: RedisConnectionPool | None = None
_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """
    获取 Redis 异步客户端（全局单例）。
    用于分布式锁、幂等 Token、JWT 黑名单、限流计数、Agent 状态缓存。
    """
    global _redis_client, _redis_pool
    if _redis_client is None:
        _redis_pool = RedisConnectionPool(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password or None,
            decode_responses=True,
            max_connections=50,
        )
        _redis_client = Redis(connection_pool=_redis_pool)
    return _redis_client


async def close_redis_client() -> None:
    """应用关闭时释放 Redis 连接池"""
    global _redis_client, _redis_pool
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


# ==========================================
# Milvus - 向量库连接（封装在 app/memory/）
# ==========================================
#
# Milvus 连接通过 pymilvus Connections.connect 建立，
# 具体封装位于 app/memory/milvus_client.py，
# 此处仅提供导入路径说明，避免在 core 层直接引入向量库细节。
#
# 使用方式：
#   from app.memory.milvus_client import get_milvus_client
#
# ==========================================