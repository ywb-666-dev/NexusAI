"""Skill 注册中心 — 技能发现、管理、调用"""

from typing import Type

from .base import Skill, SkillResult


class SkillRegistry:
    """
    Skill 注册中心，管理所有可用技能。

    支持按名称获取、按标签筛选、列出全部技能。
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册一个 Skill 实例"""
        if not skill.name:
            raise ValueError("Skill must have a non-empty name")
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> None:
        """移除一个 Skill"""
        self._skills.pop(name, None)

    def get(self, name: str) -> Skill | None:
        """按名称获取 Skill"""
        return self._skills.get(name)

    def list_all(self) -> list[dict]:
        """列出所有已注册 Skill"""
        return [s.to_dict() for s in self._skills.values()]

    def list_by_tag(self, tag: str) -> list[dict]:
        """按标签筛选 Skill"""
        return [s.to_dict() for s in self._skills.values() if tag in s.tags]

    async def invoke(self, name: str, **kwargs) -> SkillResult:
        """按名称调用 Skill"""
        skill = self._skills.get(name)
        if not skill:
            return SkillResult(success=False, error=f"Skill not found: {name}")
        import time
        start = time.perf_counter()
        try:
            result = await skill.execute(**kwargs)
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return SkillResult(success=False, error=str(e), duration_ms=duration_ms)

    def __len__(self) -> int:
        return len(self._skills)
