"""Agent Benchmark Runner — 标准化性能基准测试"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .metrics import MetricsStore, ExecutionRecord


@dataclass
class BenchmarkCase:
    """单个基准测试用例"""
    name: str
    description: str
    skill_name: str
    inputs: dict[str, Any]
    expected_fields: list[str] = field(default_factory=list)
    min_score: float = 0.0
    max_duration_ms: float = 5000.0
    tags: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """单个基准测试的执行结果"""
    case_name: str
    skill_name: str
    passed: bool
    score: float
    duration_ms: float
    output_fields: list[str] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    """一次完整的基准测试运行"""
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    results: list[BenchmarkResult] = field(default_factory=list)
    total_score: float = 0.0
    pass_rate: float = 0.0
    avg_duration_ms: float = 0.0
    summary: str = ""


class AgentBenchmarkRunner:
    """
    标准化 Agent 基准测试运行器。

    支持：
    - 单个 Skill 的基准测试
    - 完整 Skill 集合的批量测评
    - 评分与对比
    - 结果导出
    """

    def __init__(self, registry=None, metrics_store: MetricsStore | None = None):
        self.registry = registry
        self.metrics = metrics_store or MetricsStore()
        self._preset_suites: dict[str, list[BenchmarkCase]] = {}

    def register_suite(self, name: str, cases: list[BenchmarkCase]) -> None:
        """注册一个预设基准测试套件"""
        self._preset_suites[name] = cases

    def get_suite(self, name: str) -> list[BenchmarkCase]:
        return self._preset_suites.get(name, [])

    def list_suites(self) -> list[dict]:
        return [
            {"name": name, "case_count": len(cases)}
            for name, cases in self._preset_suites.items()
        ]

    async def run_case(self, case: BenchmarkCase) -> BenchmarkResult:
        """执行单个基准测试用例"""
        if not self.registry:
            return BenchmarkResult(
                case_name=case.name,
                skill_name=case.skill_name,
                passed=False,
                score=0.0,
                duration_ms=0,
                error="No SkillRegistry configured",
            )

        start = time.perf_counter()
        try:
            result = await self.registry.invoke(case.skill_name, **case.inputs)
            duration_ms = (time.perf_counter() - start) * 1000

            if not result.success:
                return BenchmarkResult(
                    case_name=case.name,
                    skill_name=case.skill_name,
                    passed=False,
                    score=0.0,
                    duration_ms=duration_ms,
                    error=result.error or "Skill returned failure",
                )

            data = result.data or {}
            output_fields = list(data.keys()) if isinstance(data, dict) else []

            field_match = 0
            if case.expected_fields:
                matches = sum(1 for f in case.expected_fields if f in output_fields)
                field_match = matches / len(case.expected_fields) if case.expected_fields else 1.0

            duration_ok = duration_ms <= case.max_duration_ms
            duration_score = min(1.0, case.max_duration_ms / max(duration_ms, 1))

            score = round((field_match * 0.6 + duration_score * 0.4), 2)
            passed = score >= case.min_score

            return BenchmarkResult(
                case_name=case.name,
                skill_name=case.skill_name,
                passed=passed,
                score=score,
                duration_ms=round(duration_ms, 1),
                output_fields=output_fields,
                metadata={"field_match": round(field_match, 2), "duration_score": round(duration_score, 2)},
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                case_name=case.name,
                skill_name=case.skill_name,
                passed=False,
                score=0.0,
                duration_ms=round(duration_ms, 1),
                error=str(e),
            )

    async def run_suite(self, name: str) -> BenchmarkRun:
        """运行整个预设套件"""
        cases = self.get_suite(name)
        if not cases:
            return BenchmarkRun(
                run_id=name,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary=f"Suite '{name}' not found",
            )

        run = BenchmarkRun(run_id=name, started_at=datetime.utcnow())
        results = []
        for case in cases:
            res = await self.run_case(case)
            results.append(res)

        run.results = results
        run.finished_at = datetime.utcnow()
        run.total_score = round(sum(r.score for r in results) / max(len(results), 1), 2)
        run.pass_rate = round(sum(1 for r in results if r.passed) / max(len(results), 1) * 100, 1)
        run.avg_duration_ms = round(sum(r.duration_ms for r in results) / max(len(results), 1), 1)

        passed_count = sum(1 for r in results if r.passed)
        run.summary = (
            f"Suite '{name}': {passed_count}/{len(results)} passed, "
            f"score={run.total_score}, pass_rate={run.pass_rate}%, "
            f"avg={run.avg_duration_ms}ms"
        )
        return run

    async def compare_skills(
        self,
        skill_names: list[str],
        inputs: dict[str, Any],
        iterations: int = 3,
    ) -> list[dict]:
        """横向对比多个 Skill 的性能"""
        comparisons: list[dict] = []
        for name in skill_names:
            durations: list[float] = []
            successes = 0
            for _ in range(iterations):
                case = BenchmarkCase(
                    name=f"compare-{name}",
                    description=f"Comparison run for {name}",
                    skill_name=name,
                    inputs=inputs,
                )
                res = await self.run_case(case)
                durations.append(res.duration_ms)
                if res.passed:
                    successes += 1

            comparisons.append({
                "skill_name": name,
                "iterations": iterations,
                "success_rate": round(successes / iterations * 100, 1),
                "avg_duration_ms": round(sum(durations) / len(durations), 1),
                "min_duration_ms": round(min(durations), 1),
                "max_duration_ms": round(max(durations), 1),
            })

        comparisons.sort(key=lambda x: (x["success_rate"], -x["avg_duration_ms"]), reverse=True)
        return comparisons

    def build_presets(self) -> None:
        """构建内置预设基准测试套件"""
        self.register_suite("smoke", [
            BenchmarkCase(
                name="scout-basic",
                description="Scout Skill basic RSS collection",
                skill_name="scout",
                inputs={"keywords": ["https://hnrss.org/frontpage"], "platforms": ["rss"]},
                expected_fields=["items", "count"],
                min_score=0.3,
                max_duration_ms=15000,
                tags=["rss", "smoke"],
            ),
            BenchmarkCase(
                name="translate-basic",
                description="Translate Skill basic translation",
                skill_name="translate",
                inputs={"text": "Hello, this is a test sentence for translation."},
                expected_fields=["translated"],
                min_score=0.4,
                max_duration_ms=10000,
                tags=["translate", "smoke"],
            ),
            BenchmarkCase(
                name="summarize-basic",
                description="Summarize Skill basic summary",
                skill_name="summarize",
                inputs={"items_text": "Item 1: AI news about LLM\nItem 2: New open source release", "style": "daily_report"},
                expected_fields=["summary"],
                min_score=0.4,
                max_duration_ms=10000,
                tags=["summary", "smoke"],
            ),
            BenchmarkCase(
                name="dedup-basic",
                description="Dedup Skill with sample items",
                skill_name="dedup",
                inputs={"items": [
                    {"id": "1", "title": "Test article", "summary": "This is a test article about AI"},
                    {"id": "2", "title": "Test article", "summary": "This is a test article about AI"},
                ]},
                expected_fields=["unique", "duplicate_ids", "unique_count"],
                min_score=0.5,
                max_duration_ms=5000,
                tags=["dedup", "smoke"],
            ),
        ])

        self.register_suite("performance", [
            BenchmarkCase(
                name="scout-perf-rss",
                description="Scout Skill RSS performance test",
                skill_name="scout",
                inputs={"keywords": ["https://hnrss.org/frontpage"], "platforms": ["rss"]},
                expected_fields=["items", "count"],
                min_score=0.3,
                max_duration_ms=8000,
                tags=["rss", "performance"],
            ),
            BenchmarkCase(
                name="dedup-perf-100",
                description="Dedup Skill with 100 items",
                skill_name="dedup",
                inputs={"items": [
                    {"id": str(i), "title": f"Article {i % 20}", "summary": f"Test content variant {i % 10}"}
                    for i in range(100)
                ]},
                expected_fields=["unique", "duplicate_ids"],
                min_score=0.5,
                max_duration_ms=3000,
                tags=["dedup", "performance"],
            ),
        ])

        self.register_suite("accuracy", [
            BenchmarkCase(
                name="dedup-exact-duplicate",
                description="Dedup should detect exact duplicates",
                skill_name="dedup",
                inputs={"items": [
                    {"id": "a", "title": "Same Title", "summary": "Same content"},
                    {"id": "b", "title": "Same Title", "summary": "Same content"},
                ]},
                expected_fields=["unique", "duplicate_ids"],
                min_score=0.7,
                max_duration_ms=5000,
                tags=["dedup", "accuracy"],
            ),
            BenchmarkCase(
                name="translate-non-chinese",
                description="Translate should handle non-Chinese text",
                skill_name="translate",
                inputs={"text": "Artificial intelligence is transforming industries worldwide."},
                expected_fields=["translated"],
                min_score=0.4,
                max_duration_ms=10000,
                tags=["translate", "accuracy"],
            ),
        ])
