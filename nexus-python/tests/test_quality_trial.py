import asyncio
from types import SimpleNamespace
from datetime import timedelta
import pytest
import httpx
from app.services.quality import assess_quality
from app.services import sources, trial
from app.agents import parser_agent
from app.api.subscription import TrialInput
from app.models.source import SourceHealth


@pytest.mark.parametrize(
    "text,title,kind,eligible",
    [
        ("", "Title", "empty", False),
        ("Just a moment... Checking your browser", "Just a moment", "blocked", False),
        (
            "首页\n登录\n注册\n联系我们\n隐私政策\n网站地图\n关于我们\n栏目一\n栏目二\n栏目三\n栏目四\n栏目五",
            "官网",
            "navigation",
            False,
        ),
        ("小版本更新发布。", "更新通知", "short", True),
        ("可阅读的文章摘要。" * 20, "文章标题", "summary", True),
        (
            "A discussion about captcha systems and security. " * 40,
            "How verification works",
            "body",
            True,
        ),
        (
            "Article URL: https://example.com/a\nComments URL: https://example.com/b\nPoints: 30",
            "Link",
            "metadata",
            True,
        ),
    ],
)
def test_quality_classification(text, title, kind, eligible):
    result = assess_quality(text, title)
    assert result["kind"] == kind and result["eligible"] == eligible
    assert 0 <= result["score"] <= 100


def test_parser_preserves_good_summary_when_article_is_challenge(monkeypatch):
    original = {
        "title": "Article",
        "summary": "An informative summary. " * 15,
        "raw_html": "An informative summary. " * 15,
        "source_url": "https://example.com/a",
    }

    async def scrape(url):
        return "Just a moment... checking your browser"

    monkeypatch.setattr(parser_agent, "_scrape_page", scrape)
    result = asyncio.run(parser_agent.prepare_items([original]))
    assert result["items"][0]["raw_html"] == original["raw_html"].strip()
    assert result["items"][0]["quality"]["extraction"] == "source"
    assert "quality" not in original


def test_parser_enriches_and_excludes_blocked_material(monkeypatch):
    async def scrape(url):
        if url.endswith("good"):
            return "Useful readable content. " * 100
        return "Just a moment..."

    monkeypatch.setattr(parser_agent, "_scrape_page", scrape)
    items = [
        {"title": "Good", "summary": "intro", "source_url": "https://example.com/good"},
        {
            "title": "Access denied",
            "raw_html": "Access denied",
            "source_url": "https://example.com/bad",
        },
    ]
    result = asyncio.run(
        parser_agent.run_parser({"scout": {"items": items}, "enable_ai": False})
    )
    assert len(result["parser"]["items"]) == 1
    assert (
        result["parser"]["scraped_count"] == 1
        and result["parser"]["rejected_count"] == 1
    )
    assert result["parser"]["items"][0]["quality"]["extraction"] == "page"


def test_health_backoff_history_and_recovery():
    row = SourceHealth(source_id="0123456789abcdef")
    sources.apply_observation(row, [], "failed", "bad", "timeout")
    first_delay = row.next_check_at - row.checked_at
    sources.apply_observation(row, [], "failed", "bad", "timeout")
    assert row.next_check_at - row.checked_at > first_delay
    assert row.consecutive_failures == 2
    for _ in range(25):
        sources.apply_observation(row, [], "failed", "bad", "timeout")
    assert row.next_check_at - row.checked_at <= timedelta(hours=26.4)
    assert len(row.history) == 20
    sources.apply_observation(row, [], "empty")
    assert row.consecutive_failures == 0 and row.last_success_at == row.checked_at
    assert row.successful_checks == 1 and row.total_checks == 28
    assert (
        timedelta(hours=6) <= row.next_check_at - row.checked_at <= timedelta(hours=6.6)
    )


@pytest.mark.parametrize(
    "code,kind",
    [
        (404, "not_found"),
        (403, "access_denied"),
        (429, "rate_limited"),
        (503, "http_error"),
    ],
)
def test_health_error_categories(code, kind):
    response = httpx.Response(code, request=httpx.Request("GET", "https://example.com"))
    assert (
        sources.classify_error(
            httpx.HTTPStatusError("error", request=response.request, response=response)
        )
        == kind
    )


def test_trial_uses_real_filter_and_quality_without_writes(monkeypatch):
    import app.services.fetching as fetching
    import app.core.dependencies as deps

    async def rss(url):
        return [
            {
                "title": "Python article",
                "summary": "Python programming content. " * 40,
                "source_url": "https://example.com/python",
                "platform": "rss",
            },
            {
                "title": "Other",
                "summary": "Different topic. " * 40,
                "source_url": "https://example.com/other",
                "platform": "rss",
            },
        ]

    def unexpected_write():
        raise AssertionError("Trial touched database")

    monkeypatch.setattr(fetching, "rss_items", rss)
    monkeypatch.setattr(deps, "get_session_factory", unexpected_write)
    result = asyncio.run(
        trial.trial_collect(
            [{"url": "https://example.com/feed", "platform": "rss"}], ["python"]
        )
    )
    assert result["collected_count"] == 2 and result["matched_count"] == 1
    assert (
        result["readable_count"] == 1
        and result["items"][0]["quality"]["kind"] == "body"
    )
    assert "task_id" not in result


def test_trial_reports_failed_sources_instead_of_claiming_empty_success(monkeypatch):
    import app.services.fetching as fetching

    async def rss(url):
        raise ValueError("not RSS")

    monkeypatch.setattr(fetching, "rss_items", rss)
    result = asyncio.run(
        trial.trial_collect(
            [{"url": "https://example.com/feed", "platform": "rss"}], []
        )
    )
    assert result["source_errors"][0]["error"] == "not RSS"
    assert result["readable_count"] == 0


def test_trial_releases_user_slot_on_error(monkeypatch):
    async def fail(*args):
        raise TimeoutError()

    monkeypatch.setattr(trial, "trial_collect", fail)
    with pytest.raises(Exception) as result:
        asyncio.run(trial.run_trial(-999, [], []))
    assert result.value.status_code == 504
    assert -999 not in trial.ACTIVE_USERS
    trial.RECENT.pop(-999, None)


def test_trial_limits_sources_and_protocols():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TrialInput(rss_feeds=[{"url": "file:///etc/passwd"}])
    with pytest.raises(ValidationError):
        TrialInput(rss_feeds=[{"url": "https://example.com"}] * 6)


def test_maintenance_only_checks_due_sources_and_one_per_host(monkeypatch):
    from app.services import source_maintenance as maintenance

    now = sources.utcnow()
    row = SourceHealth(
        source_id="future",
        status="available",
        checked_at=now,
        next_check_at=now + timedelta(hours=1),
    )

    class DB:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, *args):
            return SimpleNamespace(scalars=lambda: [row])

    monkeypatch.setattr(maintenance, "get_session_factory", lambda: DB)
    monkeypatch.setattr(
        maintenance,
        "catalog",
        lambda: {
            "sources": [
                {"id": "future", "homepage": "a"},
                {"id": "first", "homepage": "b"},
                {"id": "same-host", "homepage": "b"},
                {"id": "second", "homepage": "c"},
            ]
        },
    )
    observed = []

    async def check(sid):
        observed.append(sid)

    monkeypatch.setattr(maintenance, "check_source", check)
    assert asyncio.run(maintenance.maintenance_cycle()) == 2
    assert set(observed) == {"first", "second"}
