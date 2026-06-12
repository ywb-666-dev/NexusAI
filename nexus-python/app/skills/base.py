"""Agent Skill 基类 — 可复用的 Agent 能力单元"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: float = 0
    metadata: dict = field(default_factory=dict)


class Skill(ABC):
    """
    Agent Skill 抽象基类。

    每个 Skill 是一个可发现、可组合的能力单元，
    遵循 name + description + tags 自描述模式。
    """

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = []

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """执行 Skill，返回 SkillResult"""
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
        }
