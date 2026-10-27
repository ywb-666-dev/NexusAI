import asyncio
import json
from types import SimpleNamespace
from datetime import datetime
import pytest
from app.services import fetching, source_discovery as discovery, sources


def test_github_release_adapter_uses_public_permalink_and_release_notes(monkeypatch):
    body = [
        {
            "url": "https://api.github.com/repos/org/repo/releases/1",
            "html_url": "https://github.com/org/repo/releases/tag/v1",
            "name": "Release 1",
            "body": "Run the model offline on a laptop.\n## Changes",
            "author": {"login": "maintainer"},
            "published_at": "2026-10-26T00:00:00Z",
        },
        {"html_url": "https://github.com/org/repo/releases/tag/draft", "draft": True},
    ]
    result = fetching.parse_api(
        json.dumps(body), "https://api.github.com/repos/org/repo/releases?per_page=10"
    )
    assert len(result) == 1
    assert result[0]["source_url"] == body[0]["html_url"]
    assert result[0]["raw_html"] == body[0]["body"]
    assert result[0]["author"] == "maintainer"
    assert result[0]["published_at"] == "2026-10-26T00:00:00Z"


@pytest.mark.parametrize("version", ["1", "1.1"])
def test_json_feed_html_text_author_and_dates(version):
    body = {
        "version": "https://jsonfeed.org/version/" + version,
        "title": "Example",
        "items": [
            {
                "url": "/article",
                "title": "Guide",
                "content_html": "<p>Usable body<script>ignore()</script></p>",
                "authors": [{"name": "A"}, {"name": "B"}],
                "date_published": "2026-10-25T12:00:00Z",
            },
            {
                "external_url": "https://example.com/second",
                "content_text": "Plain text entry",
            },
        ],
    }
    items = fetching.parse_api(json.dumps(body), "https://example.com/feed.json")
    assert len(items) == 2 and items[0]["source_url"] == "https://example.com/article"
    assert items[0]["raw_html"] == "Usable body" and items[0]["author"] == "A, B"
    assert items[0]["published_at"] == "2026-10-25T12:00:00Z"
    assert items[1]["raw_html"] == "Plain text entry"


def test_empty_json_feed_is_valid_but_malformed_is_not():
    assert (
        fetching.parse_api(
            json.dumps(
                {
                    "version": "https://jsonfeed.org/version/1.1",
                    "title": "No items",
                    "items": [],
                }
            ),
            "https://example.com/feed",
        )
        == []
    )
    with pytest.raises(ValueError):
        fetching.parse_api(
            '{"version":"https://jsonfeed.org/version/1.1","items":[]}',
            "https://example.com/feed",
        )


def test_generic_json_api_remains_supported():
    result = fetching.parse_api(
        '{"data":{"articles":[{"title":"Item","url":"/a","content":"body"}]}}',
        "https://example.com/api",
    )
    assert result[0]["source_url"] == "https://example.com/a"


def test_json_feed_plain_text_is_not_mistaken_for_html():
    body = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Math",
        "items": [
            {
                "url": "https://example.com/math",
                "content_text": "Use <model> and x < 3 in plain text.",
            }
        ],
    }
    assert (
        fetching.parse_api(json.dumps(body), "https://example.com/feed")[0]["raw_html"]
        == body["items"][0]["content_text"]
    )


def test_api_without_readable_links_is_not_claimed_to_be_empty_feed():
    with pytest.raises(ValueError, match="原文地址"):
        fetching.parse_api(
            '[{"id":"a","title":"No original URL","content":"content"}]',
            "https://example.com/api",
        )


def test_discovery_respects_base_dedup_and_six_source_budget():
    body = (
        '<html><head><base href="https://feeds.example.com/sub/">'
        + "".join(
            f'<link rel="alternate" type="application/rss+xml" href="{i}.xml">'
            for i in range(9)
        )
        + '<link rel="alternate" type="text/html" href="not-a-feed"></head></html>'
    )
    found = discovery.advertised_feeds(body, "https://example.com")
    assert len(found) == 6 and found[0]["url"] == "https://feeds.example.com/sub/0.xml"
    assert (
        discovery.advertised_feeds(
            '<html><head><link rel="alternate" type="application/rss+xml" href="javascript:alert(1)"></head></html>',
            "https://example.com",
        )
        == []
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/org/repo",
        "https://github.com/org/repo.git",
        "https://github.com/org/repo/releases",
    ],
)
def test_github_repository_discovery(url):
    assert (
        discovery.github_releases(url)
        == "https://api.github.com/repos/org/repo/releases?per_page=10"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com.evil.example/org/repo",
        "https://github.com@evil.example/org/repo",
        "https://github.com/org/repo/issues/1",
        "https://github.com/topics/ai",
        "file://github.com/org/repo",
    ],
)
def test_discovery_never_treats_unrelated_urls_as_repositories(url):
    assert discovery.github_releases(url) is None


def test_discovery_verifies_feeds_but_does_not_open_database(monkeypatch):
    import app.core.dependencies as dependencies

    def database():
        raise AssertionError(
            "Discovery must not create subscriptions or health records"
        )

    monkeypatch.setattr(dependencies, "get_session_factory", database)
    calls = []

    async def fetch(url):
        calls.append(url)
        if url.endswith("feed.json"):
            return (
                b'{"version":"https://jsonfeed.org/version/1.1","title":"feed","items":[]}',
                url,
            )
        return (
            b'<html><head><link rel="alternate" type="application/feed+json" href="/feed.json"></head></html>',
            url,
        )

    monkeypatch.setattr(discovery, "fetch", fetch)
    result = asyncio.run(discovery.discover("https://example.com"))
    assert calls == ["https://example.com", "https://example.com/feed.json"]
    assert result["sources"][0]["platform"] == "api"
    assert result["sources"][0]["health"]["status"] == "empty"


def test_direct_feed_discovery_reuses_fetched_response(monkeypatch):
    calls = []

    async def fetch(url):
        calls.append(url)
        return b'<rss version="2.0"><channel><title>Feed</title></channel></rss>', url

    monkeypatch.setattr(discovery, "fetch", fetch)
    result = asyncio.run(discovery.discover("https://example.com/rss"))
    assert len(calls) == 1 and result["sources"][0]["health"]["status"] == "empty"


def test_private_discovered_address_is_blocked_by_shared_fetcher(monkeypatch):
    import socket

    monkeypatch.delenv("NEXUS_ALLOW_LOCAL_SOURCES", raising=False)

    async def fake_dns(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]

    async def run():
        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", fake_dns)
        result = await discovery.probe("http://internal.example/feed")
        assert result["health"]["status"] == "failed"
        assert result["health"]["error_kind"] == "blocked_address"

    asyncio.run(run())


def test_discovery_reports_github_quota_without_claiming_success(monkeypatch):
    import httpx

    async def fetch(url):
        response = httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0"},
            request=httpx.Request("GET", url),
        )
        response.raise_for_status()

    monkeypatch.setattr(discovery, "fetch", fetch)
    result = asyncio.run(discovery.discover("https://github.com/org/repo"))
    health = result["sources"][0]["health"]
    assert health["status"] == "failed" and health["error_kind"] == "rate_limited"
    assert "配额" in health["error"]


def test_automatic_sources_preserve_api_type(monkeypatch):
    from app.services import auto_sources as auto

    async def listing(*args):
        return [
            {
                "id": "0123456789abcdef",
                "name": "Ollama",
                "url": "https://api.github.com/repos/ollama/ollama/releases",
                "platform": "api",
                "homepage": "https://api.github.com",
                "category": "ai",
                "language": "en",
                "health": {"status": "available", "stale": False},
            }
        ]

    monkeypatch.setattr(auto, "list_sources", listing)
    result = asyncio.run(auto.resolve_sources(auto.SourcePolicy(topic="Ollama")))
    assert result["feeds"][0]["platform"] == "api"


def test_directory_filter_and_metadata_cover_all_new_types():
    data = sources.catalog()["sources"]
    assert len(data) >= 330
    assert len(sources.search_sources(platform="api")) >= 40
    assert {s["kind"] for s in data} >= {
        "github",
        "jsonfeed",
        "podcast",
        "academic",
        "publisher",
    }
    assert all(s["platform"] == "api" for s in sources.search_sources(platform="api"))


def test_stop_infrastructure_only_accepts_exact_project_data_paths():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts/dev.py"
    spec = importlib.util.spec_from_file_location("project_dev", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.owns_infra(
        "mysqld.exe", ["mysqld.exe", "--datadir=" + str(module.RUNTIME / "mysql")]
    )
    assert module.owns_infra(
        "redis-server.exe", ["redis-server.exe", "--dir", str(module.RUNTIME)]
    )
    assert not module.owns_infra(
        "mysqld.exe", ["mysqld.exe", "--datadir=D:/OtherProject/mysql"]
    )
    assert not module.owns_infra(
        "mysqld.exe", ["mysqld.exe", "--datadir=.runtime/mysql"]
    )
    assert not module.owns_infra("redis-server.exe", ["redis-server.exe"])
