from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel,Field


class NexusAIException(Exception):
    """基类，所有自定义异常的父类"""

    def __init__(
            self,
            message: str = "",
            task_id: str | None = None,
            timestamp: datetime | None = None,
    ):
        super().__init__(message)
        self.task_id = task_id
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"task_id={self.task_id}, "
            f"timestamp={self.timestamp}, "
            f"message={self.args[0]!r})"
        )


class AgentExecutionError(NexusAIException):
    """Agent 内部错误"""

    def __init__(
            self,
            message: str = "",
            node_name: str = "",
            traceback: str | None = None,
            **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.node_name = node_name
        self.traceback = traceback


class MCPConnectionError(NexusAIException):
    """工具调用失败"""

    def __init__(
            self,
            message: str = "",
            server_name: str = "",
            tool_name: str = "",
            **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.server_name = server_name
        self.tool_name = tool_name


class MilvusOperationError(NexusAIException):
    """向量库异常"""

    def __init__(
            self,
            message: str = "",
            collection_name: str = "",
            operation: str = "",
            **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.collection_name = collection_name
        self.operation = operation


class RiskInterruption(NexusAIException):
    """Actor Agent 触发人工审批时的特殊异常"""

    def __init__(
            self,
            message: str = "",
            risk_level: int = 0,
            action_type: str = "",
            context: dict[str, Any] | None = None,
            **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.risk_level = risk_level
        self.action_type = action_type
        self.context = context or {}

class ErrorInfo(BaseModel):
    """用于 API 响应和日志的结构化错误信息"""
    message:str=Field(description="报错消息")
    task_id:str=Field(description="任务ID")
    timestamp:datetime=Field(
        default=datetime.now(timezone.utc),
        description="时间戳"
    )
    traceback:str=Field(
        default="",
        description="异常堆栈字符串"
    )
    node_name:str=Field(
        default="",
        description="agent节点名"
    )

def error_to_model(exc:NexusAIException)->ErrorInfo:
    return ErrorInfo(
        message=str(exc),
        task_id=str(exc.task_id),
        timestamp=getattr(exc, 'timestamp', None),
        traceback=getattr(exc, 'traceback', None),
    )
