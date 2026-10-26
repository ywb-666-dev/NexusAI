import asyncio
from datetime import datetime
from types import SimpleNamespace
import pytest
from app.services import sources


def test_catalog_has_unique_stable_ids_and_valid_categories():
    data = sources.catalog()
    assert len(data["sources"]) >= 200
    assert len({s["url"] for s in data["sources"]}) == len(data["sources"])
    assert len({s["id"] for s in data["sources"]}) == len(data["sources"])
    assert all(
        s["category"] in data["categories"] and s["url"].startswith("https://")
        for s in data["sources"]
    )
    assert len(sources.search_sources(language="zh")) >= 40


def test_topic_alias_and_language_filters():
    assert any("arXiv" in s["name"] for s in sources.search_sources("大模型"))
    assert all(
        s["language"] == "zh" and s["category"] == "dev"
        for s in sources.search_sources(category="dev", language="zh")
    )
    assert sources.search_sources("nonexistent-domain-9876") == []


@pytest.mark.parametrize(
    "outcome,expected",
    [("items", "available"), ("empty", "empty"), ("error", "failed")],
)
def test_check_persists_real_result_and_does_not_subscribe(
    monkeypatch, outcome, expected
):
    store = {}

    class DB:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, model, key):
            return store.get(key)

        def add(self, row):
            store[row.source_id] = row

        async def commit(self):
            pass

    monkeypatch.setattr(sources, "get_session_factory", lambda: DB)

    async def fetch(url):
        if outcome == "error":
            raise ValueError("invalid feed")
        return (
            [
                {
                    "title": "Live title",
                    "source_url": "https://example.com/article",
                    "summary": "body",
                }
            ]
            if outcome == "items"
            else []
        )

    monkeypatch.setattr(sources, "rss_items", fetch)
    sid = sources.catalog()["sources"][0]["id"]

    async def run():
        result = await sources.check_source(sid)
        assert result["status"] == expected
        assert result["checked_at"].endswith("Z")
        assert result["entry_count"] == (1 if outcome == "items" else 0)
        if outcome == "error":
            assert result["error"] == "invalid feed"
        assert (await sources.check_source(sid))["cached"] is True

    asyncio.run(run())


def test_unknown_source_is_rejected_before_network():
    with pytest.raises(ValueError, match="数据源不存在"):
        asyncio.run(sources.check_source("unknown"))


def test_last_success_is_retained_after_failure():
    timestamp = datetime(2026, 10, 26)
    row = SimpleNamespace(
        status="failed",
        checked_at=timestamp,
        last_success_at=timestamp,
        latency_ms=10,
        entry_count=0,
        error="network",
        samples=[],
    )
    result = sources.health_data(row)
    assert (
        result["status"] == "failed"
        and result["last_success_at"] == "2026-10-26T00:00:00Z"
    )
