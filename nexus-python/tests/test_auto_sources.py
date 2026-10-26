import asyncio
import pytest
from app.services import auto_sources as auto


def source(
    sid,
    name="AI Blog",
    language="en",
    status="available",
    host=None,
    category="ai",
    stale=False,
):
    return {
        "id": sid,
        "name": name,
        "url": f"https://{host or sid+'.example.com'}/feed",
        "homepage": f"https://{host or sid+'.example.com'}",
        "language": language,
        "category": category,
        "health": {
            "status": status,
            "stale": stale,
            "quality_score": 80,
            "success_rate": 90,
        },
    }


def test_auto_prefers_healthy_chinese_and_distinct_hosts(monkeypatch):
    rows = [
        source("a"),
        source("b", name="中文 AI", language="zh"),
        source("c", host="a.example.com"),
        source("d", status="failed"),
        source("e", stale=True),
        source("f", name="Gaming", category="life"),
    ]

    async def listing(*args):
        return rows

    monkeypatch.setattr(auto, "list_sources", listing)
    result = asyncio.run(auto.resolve_sources(auto.SourcePolicy(topic="人工智能"), 5))
    assert result["feeds"][0]["sourceId"] == "b"
    assert len(result["feeds"]) == 2
    assert all(f["origin"] == "system" for f in result["feeds"])


def test_auto_never_matches_ai_inside_unrelated_word(monkeypatch):
    async def listing(*args):
        return [source("a", name="Trail of Bits", category="security")]

    monkeypatch.setattr(auto, "list_sources", listing)
    assert (
        asyncio.run(auto.resolve_sources(auto.SourcePolicy(topic="AI")))["feeds"] == []
    )


def test_exclusion_and_user_sources_survive_refresh(monkeypatch):
    sid = "0123456789abcdef"
    rows = [source(sid), source("fedcba9876543210")]

    async def listing(*args):
        return rows

    monkeypatch.setattr(auto, "list_sources", listing)
    manual = {"url": rows[1]["url"], "platform": "rss", "name": "My preferred name"}
    previous = {
        "url": "https://old.example.com/feed",
        "origin": "system",
        "platform": "rss",
    }
    feeds, resolution = asyncio.run(
        auto.resolve_subscription_sources(
            [manual, previous],
            {"source_policy": {"mode": "auto", "topic": "AI", "excluded_ids": [sid]}},
        )
    )
    assert len(feeds) == 1 and feeds[0]["name"] == "My preferred name"
    assert feeds[0]["origin"] == "manual" and resolution["manual_count"] == 1


def test_unknown_topic_does_not_get_unrelated_fallback(monkeypatch):
    async def listing(*args):
        return []

    monkeypatch.setattr(auto, "list_sources", listing)
    with pytest.raises(ValueError, match="未找到"):
        asyncio.run(
            auto.resolve_subscription_sources(
                [], {"source_policy": {"mode": "auto", "topic": "unknown subject"}}
            )
        )


def test_manual_only_never_calls_automatic_selection(monkeypatch):
    async def unexpected(*args):
        raise AssertionError("manual subscription was changed")

    monkeypatch.setattr(auto, "list_sources", unexpected)
    feeds = [{"url": "https://example.com/custom", "platform": "web"}]
    assert asyncio.run(auto.resolve_subscription_sources(feeds, {})) == (feeds, None)


def test_fresh_installation_checks_only_bounded_candidates(monkeypatch):
    rows = [source(str(i), status="unchecked") for i in range(8)]
    checked = []

    async def listing(*args):
        return rows

    async def check(sid):
        checked.append(sid)
        next(s for s in rows if s["id"] == sid)["health"]["status"] = "available"

    monkeypatch.setattr(auto, "list_sources", listing)
    monkeypatch.setattr(auto, "check_source", check)
    result = asyncio.run(auto.resolve_sources(auto.SourcePolicy(topic="AI")))
    assert len(checked) == 4 and len(result["feeds"]) == 4


def test_trial_resolution_never_checks_or_writes_health(monkeypatch):
    async def listing(*args):
        return [source("a", status="unchecked")]

    async def check(*args):
        raise AssertionError("trial wrote health")

    monkeypatch.setattr(auto, "list_sources", listing)
    monkeypatch.setattr(auto, "check_source", check)
    with pytest.raises(ValueError):
        asyncio.run(
            auto.resolve_subscription_sources(
                [], {"source_policy": {"mode": "auto", "topic": "AI"}}
            )
        )


def test_manual_capacity_is_preserved(monkeypatch):
    async def listing(*args):
        raise AssertionError("no slots for system sources")

    monkeypatch.setattr(auto, "list_sources", listing)
    manual = [{"url": f"https://example.com/{i}", "platform": "rss"} for i in range(20)]
    feeds, result = asyncio.run(
        auto.resolve_subscription_sources(
            manual, {"source_policy": {"mode": "auto", "topic": "AI"}}
        )
    )
    assert len(feeds) == 20 and result["system_count"] == 0


def test_policy_rejects_invalid_or_missing_configuration():
    from pydantic import ValidationError

    for value in [
        {"topic": " "},
        {"topic": "AI", "language": "unknown"},
        {"topic": "AI", "excluded_ids": ["anything"]},
    ]:
        with pytest.raises(ValidationError):
            auto.SourcePolicy.model_validate(value)


def test_empty_matches_finish_without_a_running_parser(monkeypatch):
    from app.agents import supervisor

    observed = []

    async def scout(state, **kwargs):
        return {**state, "scout": {"items": []}}

    async def update(task_id, status, nodes):
        observed.append((status, nodes))

    monkeypatch.setattr(supervisor, "run_scout_node", scout)
    monkeypatch.setattr(supervisor, "_update_task_status", update)
    result = asyncio.run(supervisor.NexusSupervisor()._scout_node({"task_id": "test"}))
    assert result["status"] == "completed: no items"
    assert observed[-1][1]["parser"] == "skipped"


def test_generic_ai_topic_respects_chinese_preference(monkeypatch):
    async def listing(*args):
        return [
            source("en", name="AI Blog"),
            source("zh", name="量子位", language="zh"),
        ]

    monkeypatch.setattr(auto, "list_sources", listing)
    result = asyncio.run(
        auto.resolve_sources(auto.SourcePolicy(topic="AI", language="zh_first"))
    )
    assert result["feeds"][0]["sourceId"] == "zh"
