"""Agent Tester — 测试套件管理与评估框架"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .metrics import MetricsStore


@dataclass
class TestCase:
    """单个测试用例"""
    name: str
    description: str
    skill_name: str
    inputs: dict[str, Any]
    assertions: list[Callable[[Any], tuple[bool, str]]] = field(default_factory=list)
    timeout_ms: float = 30000
    tags: list[str] = field(default_factory=list)


@dataclass
class TestResult:
    """单个测试用例的执行结果"""
    test_name: str
    skill_name: str
    status: str  # passed | failed | error | timeout
    duration_ms: float = 0
    assertion_results: list[dict] = field(default_factory=list)
    error: str | None = None
    executed_at: datetime | None = None


@dataclass
class TestRun:
    """一次完整的测试运行"""
    run_id: str
    suite_name: str
    started_at: datetime
    finished_at: datetime | None = None
    results: list[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    errors: int = 0
    total_duration_ms: float = 0
    summary: str = ""


class AgentTester:
    """
    Agent 技能测试套件管理器。

    支持：
    - 测试用例注册与管理
    - 测试执行与断言验证
    - 通过/失败/错误分类统计
    - 测试报告生成
    - CI/CD 集成（退出码支持）
    """

    def __init__(self, registry=None, metrics_store: MetricsStore | None = None):
        self.registry = registry
        self.metrics = metrics_store or MetricsStore()
        self._suites: dict[str, list[TestCase]] = {}
        self._history: list[TestRun] = []

    def register_test(self, suite_name: str, test: TestCase) -> None:
        """注册单个测试用例到套件"""
        self._suites.setdefault(suite_name, []).append(test)

    def register_suite(self, suite_name: str, tests: list[TestCase]) -> None:
        """批量注册测试用例"""
        self._suites[suite_name] = self._suites.get(suite_name, []) + tests

    def list_suites(self) -> list[dict]:
        return [
            {
                "name": name,
                "test_count": len(tests),
                "skills": list(set(t.skill_name for t in tests)),
            }
            for name, tests in self._suites.items()
        ]

    def get_suite(self, name: str) -> list[TestCase]:
        return self._suites.get(name, [])

    async def run_test(self, test: TestCase) -> TestResult:
        """执行单个测试用例并验证断言"""
        if not self.registry:
            return TestResult(
                test_name=test.name,
                skill_name=test.skill_name,
                status="error",
                error="No SkillRegistry configured",
            )

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self.registry.invoke(test.skill_name, **test.inputs),
                timeout=test.timeout_ms / 1000,
            )
            duration_ms = (time.perf_counter() - start) * 1000

            if not result.success:
                return TestResult(
                    test_name=test.name,
                    skill_name=test.skill_name,
                    status="failed",
                    duration_ms=round(duration_ms, 1),
                    error=result.error or "Skill returned failure",
                    executed_at=datetime.utcnow(),
                )

            assertion_results: list[dict] = []
            all_passed = True
            for i, assertion in enumerate(test.assertions):
                try:
                    passed, detail = assertion(result.data)
                    assertion_results.append({"index": i, "passed": passed, "detail": detail})
                    if not passed:
                        all_passed = False
                except Exception as e:
                    assertion_results.append({"index": i, "passed": False, "detail": str(e)})
                    all_passed = False

            return TestResult(
                test_name=test.name,
                skill_name=test.skill_name,
                status="passed" if all_passed else "failed",
                duration_ms=round(duration_ms, 1),
                assertion_results=assertion_results,
                executed_at=datetime.utcnow(),
            )
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                test_name=test.name,
                skill_name=test.skill_name,
                status="timeout",
                duration_ms=round(duration_ms, 1),
                error=f"Timeout after {test.timeout_ms}ms",
                executed_at=datetime.utcnow(),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                test_name=test.name,
                skill_name=test.skill_name,
                status="error",
                duration_ms=round(duration_ms, 1),
                error=str(e),
                executed_at=datetime.utcnow(),
            )

    async def run_suite(self, suite_name: str) -> TestRun:
        """运行完整测试套件"""
        tests = self.get_suite(suite_name)
        if not tests:
            return TestRun(
                run_id=suite_name,
                suite_name=suite_name,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary=f"Suite '{suite_name}' not found",
            )

        run = TestRun(
            run_id=f"{suite_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            suite_name=suite_name,
            started_at=datetime.utcnow(),
        )

        for test in tests:
            res = await self.run_test(test)
            run.results.append(res)

        run.finished_at = datetime.utcnow()
        run.passed = sum(1 for r in run.results if r.status == "passed")
        run.failed = sum(1 for r in run.results if r.status == "failed")
        run.errors = sum(1 for r in run.results if r.status in ("error", "timeout"))
        run.total_duration_ms = round(sum(r.duration_ms for r in run.results), 1)

        total = len(run.results)
        run.summary = (
            f"Suite '{suite_name}': {run.passed} passed, {run.failed} failed, "
            f"{run.errors} errors out of {total} tests | "
            f"pass_rate={round(run.passed / max(total, 1) * 100, 1)}% | "
            f"total={run.total_duration_ms}ms"
        )

        self._history.append(run)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        return run

    async def run_all_suites(self) -> list[TestRun]:
        """运行所有已注册的测试套件"""
        runs: list[TestRun] = []
        for suite_name in self._suites:
            run = await self.run_suite(suite_name)
            runs.append(run)
        return runs

    def get_history(self, limit: int = 10) -> list[dict]:
        """获取最近的测试运行历史"""
        return [
            {
                "run_id": r.run_id,
                "suite_name": r.suite_name,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "passed": r.passed,
                "failed": r.failed,
                "errors": r.errors,
                "total_duration_ms": r.total_duration_ms,
                "summary": r.summary,
            }
            for r in self._history[-limit:]
        ]

    def build_evaluation(
        self,
        suite_name: str,
        skill_name: str,
        pivot_field: str,
        values: list[Any],
    ) -> list[TestCase]:
        """
        参数化测试构建器：为同一 Skill 的不同参数值生成测试矩阵。

        用于评估 Agent 在不同输入下的表现一致性。
        """
        tests: list[TestCase] = []
        for i, val in enumerate(values):
            # Copy base inputs and override the pivot field
            base_inputs = self._get_base_inputs(suite_name, skill_name)
            base_inputs[pivot_field] = val
            tests.append(TestCase(
                name=f"{skill_name}-{pivot_field}-{i}",
                description=f"Evaluation: {skill_name} with {pivot_field}={val}",
                skill_name=skill_name,
                inputs=base_inputs,
                tags=["evaluation", skill_name],
            ))
        return tests

    def _get_base_inputs(self, suite_name: str, skill_name: str) -> dict[str, Any]:
        """从已有套件中提取特定 Skill 的基础输入参数"""
        tests = self.get_suite(suite_name)
        for t in tests:
            if t.skill_name == skill_name:
                return dict(t.inputs)
        return {}

    # ========== 内置断言工厂 ==========

    @staticmethod
    def assert_field_exists(field: str) -> Callable[[Any], tuple[bool, str]]:
        """断言返回数据中包含指定字段"""
        def check(data: Any) -> tuple[bool, str]:
            if isinstance(data, dict) and field in data:
                return True, f"Field '{field}' exists"
            return False, f"Field '{field}' missing (got keys: {list(data.keys()) if isinstance(data, dict) else type(data)})"
        return check

    @staticmethod
    def assert_field_not_empty(field: str) -> Callable[[Any], tuple[bool, str]]:
        """断言字段值非空"""
        def check(data: Any) -> tuple[bool, str]:
            val = data.get(field) if isinstance(data, dict) else None
            if val is not None and val != "" and val != []:
                return True, f"Field '{field}' is not empty"
            return False, f"Field '{field}' is empty or missing"
        return check

    @staticmethod
    def assert_value_match(field: str, expected: Any) -> Callable[[Any], tuple[bool, str]]:
        """断言字段值与期望值匹配"""
        def check(data: Any) -> tuple[bool, str]:
            val = data.get(field) if isinstance(data, dict) else data
            if val == expected:
                return True, f"Field '{field}' == {expected}"
            return False, f"Field '{field}' == {val}, expected {expected}"
        return check

    @staticmethod
    def assert_count(field: str, op: str, value: int) -> Callable[[Any], tuple[bool, str]]:
        """断言集合字段数量符合条件 (op: >, >=, <, <=, ==)"""
        def check(data: Any) -> tuple[bool, str]:
            val = data.get(field) if isinstance(data, dict) else data
            length = len(val) if isinstance(val, (list, dict, str)) else (val if isinstance(val, (int, float)) else -1)
            if op == ">" and length > value: return True, f"count({field})={length} > {value}"
            if op == ">=" and length >= value: return True, f"count({field})={length} >= {value}"
            if op == "<" and length < value: return True, f"count({field})={length} < {value}"
            if op == "<=" and length <= value: return True, f"count({field})={length} <= {value}"
            if op == "==" and length == value: return True, f"count({field})={length} == {value}"
            return False, f"count({field})={length}, expected {op} {value}"
        return check

    def build_presets(self) -> None:
        """构建内置预设测试套件"""
        # Smoke test suite
        self.register_suite("smoke", [
            TestCase(
                name="scout-has-items",
                description="Scout Skill should return items list",
                skill_name="scout",
                inputs={"keywords": ["https://hnrss.org/frontpage"], "platforms": ["rss"]},
                assertions=[
                    self.assert_field_exists("items"),
                    self.assert_field_exists("count"),
                ],
                timeout_ms=20000,
                tags=["scout", "smoke"],
            ),
            TestCase(
                name="translate-returns-translated",
                description="Translate should return translated field",
                skill_name="translate",
                inputs={"text": "Hello world"},
                assertions=[self.assert_field_exists("translated")],
                timeout_ms=15000,
                tags=["translate", "smoke"],
            ),
            TestCase(
                name="summarize-returns-summary",
                description="Summarize should return summary field",
                skill_name="summarize",
                inputs={"items_text": "Sample content for testing", "style": "article_summary"},
                assertions=[self.assert_field_exists("summary")],
                timeout_ms=15000,
                tags=["summary", "smoke"],
            ),
            TestCase(
                name="dedup-returns-counts",
                description="Dedup should return unique and duplicate_ids",
                skill_name="dedup",
                inputs={"items": [{"id": "1", "title": "Test", "summary": "Test"}]},
                assertions=[
                    self.assert_field_exists("unique"),
                    self.assert_field_exists("duplicate_ids"),
                ],
                timeout_ms=10000,
                tags=["dedup", "smoke"],
            ),
        ])

        # Integration test suite
        self.register_suite("integration", [
            TestCase(
                name="scout-then-dedup",
                description="Scout collection results can be piped through Dedup",
                skill_name="dedup",
                inputs={"items": [
                    {"id": "a", "title": "Unique A", "summary": "Content A"},
                    {"id": "b", "title": "Unique B", "summary": "Content B"},
                    {"id": "c", "title": "Unique A", "summary": "Content A"},  # duplicate
                ]},
                assertions=[
                    self.assert_field_exists("unique"),
                    self.assert_field_exists("duplicate_ids"),
                    self.assert_count("unique_count", "==", 2),
                ],
                timeout_ms=10000,
                tags=["integration"],
            ),
        ])
