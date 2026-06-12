"""Agent 执行指标存储 — 内存 + Redis 双写"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutionRecord:
    """单次执行记录"""
    task_id: str
    skill_name: str
    status: str  # running | success | failed
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsStore:
    """
    内存指标存储，追踪 Agent 执行历史。

    关键指标：
    - 总执行次数 / 成功 / 失败
    - 每 Skill 平均耗时
    - 最近 N 条执行记录
    """

    def __init__(self, max_records: int = 200):
        self._records: list[ExecutionRecord] = []
        self._max_records = max_records

    def record(self, rec: ExecutionRecord) -> None:
        self._records.append(rec)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

    def stats(self) -> dict:
        total = len(self._records)
        if total == 0:
            return {"total": 0, "success_rate": 0, "avg_duration_ms": 0, "by_skill": {}}

        success = sum(1 for r in self._records if r.status == "success")
        failed = sum(1 for r in self._records if r.status == "failed")
        durations = [r.duration_ms for r in self._records if r.duration_ms > 0]
        avg_dur = sum(durations) / len(durations) if durations else 0

        by_skill: dict[str, dict] = {}
        for r in self._records:
            if r.skill_name not in by_skill:
                by_skill[r.skill_name] = {"total": 0, "success": 0, "failed": 0, "durations": []}
            by_skill[r.skill_name]["total"] += 1
            by_skill[r.skill_name]["success"] += 1 if r.status == "success" else 0
            by_skill[r.skill_name]["failed"] += 1 if r.status == "failed" else 0
            if r.duration_ms > 0:
                by_skill[r.skill_name]["durations"].append(r.duration_ms)

        for skill, data in by_skill.items():
            durs = data.pop("durations", [])
            data["avg_duration_ms"] = sum(durs) / len(durs) if durs else 0

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 1),
            "avg_duration_ms": round(avg_dur, 1),
            "by_skill": by_skill,
        }

    def recent(self, n: int = 20) -> list[dict]:
        return [
            {
                "task_id": r.task_id,
                "skill_name": r.skill_name,
                "status": r.status,
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "duration_ms": r.duration_ms,
                "error": r.error,
            }
            for r in self._records[-n:]
        ]
