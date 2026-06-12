"""Agent Harness — 执行运行时：观测、重试、指标追踪"""

import asyncio
import time
import traceback
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from .metrics import MetricsStore, ExecutionRecord

# 全局单例
_global_store = MetricsStore()


def get_metrics_store() -> MetricsStore:
    return _global_store


class AgentHarness:
    """
    Agent 执行运行时（Harness）。

    包装 Agent 任务执行，提供：
    - 执行前/后钩子
    - 自动重试（可配置次数 + 退避策略）
    - 性能指标（耗时、成功率）
    - 错误追踪
    - 执行历史记录
    """

    def __init__(
        self,
        max_retries: int = 2,
        backoff_base: float = 1.5,
        metrics_store: MetricsStore | None = None,
    ):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.metrics = metrics_store or _global_store
        self._before_hooks: list[Callable] = []
        self._after_hooks: list[Callable] = []

    def on_before(self, hook: Callable) -> None:
        """注册执行前置钩子"""
        self._before_hooks.append(hook)

    def on_after(self, hook: Callable) -> None:
        """注册执行后置钩子"""
        self._after_hooks.append(hook)

    async def run(
        self,
        skill_name: str,
        task_id: str | None = None,
        **kwargs,
    ) -> Any:
        """
        执行一个 Agent Skill，带重试和全链路追踪。

        返回: SkillResult 或原始返回值
        """
        task_id = task_id or uuid.uuid4().hex
        from app.skills.registry import SkillRegistry

        # 需要从外部传入 registry 实例
        registry: SkillRegistry = kwargs.pop("_registry", None)
        if not registry:
            return ExecutionRecord(
                task_id=task_id,
                skill_name=skill_name,
                status="failed",
                start_time=datetime.utcnow(),
                error="No SkillRegistry provided",
            )

        rec = ExecutionRecord(
            task_id=task_id,
            skill_name=skill_name,
            status="running",
            start_time=datetime.utcnow(),
            metadata=kwargs.get("metadata", {}),
        )

        # 前置钩子
        for hook in self._before_hooks:
            try:
                hook(task_id=task_id, skill_name=skill_name, **kwargs)
            except Exception:
                pass

        last_error: str | None = None
        result: Any = None

        for attempt in range(self.max_retries + 1):
            try:
                start = time.perf_counter()
                result = await registry.invoke(skill_name, **kwargs)
                rec.duration_ms = (time.perf_counter() - start) * 1000

                if hasattr(result, "success") and result.success:
                    rec.status = "success"
                    rec.end_time = datetime.utcnow()
                    self.metrics.record(rec)
                    break
                elif hasattr(result, "success") and not result.success:
                    last_error = result.error or "Unknown error"
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.backoff_base ** attempt)
                    continue
                else:
                    rec.status = "success"
                    rec.end_time = datetime.utcnow()
                    self.metrics.record(rec)
                    break

            except Exception as e:
                last_error = str(e)
                rec.duration_ms = (time.perf_counter() - start) * 1000
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base ** attempt)

        if rec.status == "running":
            rec.status = "failed"
            rec.error = last_error
            rec.end_time = datetime.utcnow()
            self.metrics.record(rec)

        # 后置钩子
        for hook in self._after_hooks:
            try:
                hook(task_id=task_id, skill_name=skill_name, status=rec.status, result=result)
            except Exception:
                pass

        return result

    def wrap(self, skill_name: str):
        """装饰器：将任意异步函数包装为 Harness 管理的 Skill"""
        def decorator(func):
            @wraps(func)
            async def wrapper(**kwargs):
                task_id = kwargs.pop("_task_id", uuid.uuid4().hex)
                rec = ExecutionRecord(
                    task_id=task_id,
                    skill_name=skill_name,
                    status="running",
                    start_time=datetime.utcnow(),
                )
                last_error: str | None = None

                for attempt in range(self.max_retries + 1):
                    try:
                        start = time.perf_counter()
                        result = await func(**kwargs)
                        rec.duration_ms = (time.perf_counter() - start) * 1000
                        rec.status = "success"
                        rec.end_time = datetime.utcnow()
                        self.metrics.record(rec)
                        return result
                    except Exception as e:
                        last_error = str(e)
                        rec.duration_ms = (time.perf_counter() - start) * 1000
                        if attempt < self.max_retries:
                            time.sleep(self.backoff_base ** attempt)

                rec.status = "failed"
                rec.error = last_error
                rec.end_time = datetime.utcnow()
                self.metrics.record(rec)
                raise RuntimeError(f"Skill '{skill_name}' failed after {self.max_retries + 1} attempts: {last_error}")

            return wrapper
        return decorator


# ========== Middleware: 日志追踪 ==========

class LoggingMiddleware:
    """Harness 日志中间件：记录每次技能调用的入参/出参/耗时"""

    @staticmethod
    def before(task_id: str, skill_name: str, **kwargs) -> None:
        safe_kwargs = {k: str(v)[:100] for k, v in kwargs.items()}
        print(f"[Harness] ▶ {skill_name} | task={task_id[:8]} | args={safe_kwargs}")

    @staticmethod
    def after(task_id: str, skill_name: str, status: str, result: Any = None) -> None:
        result_preview = ""
        if hasattr(result, "duration_ms"):
            result_preview = f" | {result.duration_ms:.1f}ms"
        print(f"[Harness] ◀ {skill_name} | task={task_id[:8]} | {status}{result_preview}")
