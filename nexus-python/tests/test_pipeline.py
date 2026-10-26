import asyncio
import base64
import hashlib
import hmac
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import fetching
from app.agents.scout_agent import run_scout_node
from app.agents.actor_agent import run_actor, _assess_risk
from app.skills.builtins import DedupSkill, SummarizeSkill
from app.services.push import payload_for, validate_webhook
from app.core.auth import decode_user


def run(coro):
    return asyncio.run(coro)


def test_rejects_private_networks(monkeypatch):
    monkeypatch.delenv("NEXUS_ALLOW_LOCAL_SOURCES", raising=False)
    with pytest.raises(ValueError):
        run(fetching.validate_url("http://127.0.0.1/admin"))
    with pytest.raises(ValueError):
        run(fetching.validate_url("file:///etc/passwd"))
    with pytest.raises(ValueError):
        run(fetching.validate_url("https://user:pass@example.com"))


def test_rss_preserves_body_and_normalizes_links(monkeypatch):
    async def fetch(url):
        return (
            b"""<rss version="2.0"><channel><item><title>Example</title><link>/article#fragment</link><description><![CDATA[<p>body<script>bad()</script></p>]]></description><pubDate>Sun, 25 Oct 2026 12:00:00 +0800</pubDate></item></channel></rss>""",
            "https://example.com/feed",
        )

    monkeypatch.setattr(fetching, "fetch", fetch)
    items = run(fetching.rss_items("https://example.com/feed"))
    assert items[0]["source_url"] == "https://example.com/article"
    assert items[0]["summary"] == "body"
    assert "<p>body</p>" == items[0]["raw_html"]  # feedparser sanitizes active markup
    assert fetching.published(items[0]["published_at"]).hour == 4


def test_invalid_feed_is_reported(monkeypatch):
    async def fetch(url):
        return b"<html><body>not a feed</body></html>", url

    monkeypatch.setattr(fetching, "fetch", fetch)
    with pytest.raises(ValueError):
        run(fetching.rss_items("https://example.com"))


def test_one_failed_source_does_not_lose_good_content(monkeypatch):
    async def rss(url):
        if "bad" in url:
            raise RuntimeError("source down")
        return [
            {
                "source_url": "https://example.com/article",
                "title": "Python release",
                "summary": "new features",
                "platform": "rss",
            }
        ]

    monkeypatch.setattr(fetching, "rss_items", rss)
    state = {
        "rss_feeds": [
            {"url": "https://example.com/good"},
            {"url": "https://example.com/bad"},
        ],
        "keywords": ["Python"],
    }
    result = run(run_scout_node(state))
    assert result["scout"]["total_fetched"] == 1
    assert len(result["scout"]["source_errors"]) == 1


def test_all_failed_sources_fail_task(monkeypatch):
    async def rss(url):
        raise RuntimeError("source down")

    monkeypatch.setattr(fetching, "rss_items", rss)
    with pytest.raises(RuntimeError):
        run(run_scout_node({"rss_feeds": [{"url": "https://example.com/feed"}]}))


def test_sensitive_content_requires_review():
    assert _assess_risk(1, [{"title": "CVE-2026-1234", "summary": ""}])[0] == 3
    assert _assess_risk(20, [])[0] == 3
    assert _assess_risk(1, [{"title": "Python news"}])[0] == 1


def test_approval_insert_failure_never_auto_publishes():
    class BrokenDB:
        def add(self, obj):
            raise RuntimeError("database unavailable")

        async def rollback(self):
            pass

    state = {
        "task_id": "x",
        "user_id": 1,
        "connector": {"stored_count": 20, "items": [], "stored_ids": ["x"]},
    }
    with pytest.raises(RuntimeError):
        run(run_actor(state, BrokenDB()))
    assert state.get("actor", {}).get("action") != "proceed"


def test_exact_dedup_skill():
    result = run(
        DedupSkill().execute(
            items=[
                {"id": "a", "title": "same"},
                {"id": "b", "title": "same"},
                {"id": "c", "title": "different"},
            ]
        )
    )
    assert result.data["unique_count"] == 2
    assert result.data["duplicate_ids"] == ["b"]


def test_summarize_accepts_frontend_text_field(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings.llm, "api_key", "")
    result = run(
        SummarizeSkill().execute(text="source content", style="article_summary")
    )
    assert result.success
    assert result.data["summary"] == "source content"
    assert result.data["source"] == "truncate"


@pytest.mark.parametrize("provider", ["feishu", "dingtalk"])
def test_signed_webhook_payload(provider, monkeypatch):
    monkeypatch.setattr("app.services.push.time.time", lambda: 1700000000)
    channel = SimpleNamespace(provider=provider, secret="test-secret")
    payload, params = payload_for(channel, "test")
    if provider == "feishu":
        expected = base64.b64encode(
            hmac.new(b"1700000000\ntest-secret", b"", hashlib.sha256).digest()
        ).decode()
        assert payload["sign"] == expected
        assert payload["msg_type"] == "text"
    else:
        expected = base64.b64encode(
            hmac.new(
                b"test-secret", b"1700000000000\ntest-secret", hashlib.sha256
            ).digest()
        ).decode()
        assert params["sign"] == expected
        assert payload["msgtype"] == "text"


def test_push_host_allowlist(monkeypatch):
    monkeypatch.delenv("NEXUS_ALLOW_LOCAL_SOURCES", raising=False)
    with pytest.raises(ValueError):
        validate_webhook("feishu", "https://example.com/secret")
    validate_webhook("feishu", "https://open.feishu.cn/open-apis/bot/v2/hook/token")


def test_auth_requires_expiry():
    import jwt
    import os

    token = jwt.encode(
        {"sub": "1"},
        os.getenv("JWT_SECRET", "nexus-ai-local-secret-key-2026-32chars!!"),
        algorithm="HS256",
    )
    with pytest.raises(Exception) as exc:
        decode_user(token)
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "provider,code_field", [("feishu", "code"), ("dingtalk", "errcode")]
)
def test_webhook_error_body_and_dingtalk_token(monkeypatch, provider, code_field):
    from app.services import push
    import httpx

    seen = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json, params):
            seen.append(params)
            return httpx.Response(
                200, json={code_field: 123}, request=httpx.Request("POST", url)
            )

    monkeypatch.setattr(push.httpx, "AsyncClient", Client)
    monkeypatch.setattr(push, "validate_webhook", lambda *args: None)
    channel = SimpleNamespace(
        provider=provider,
        webhook="https://example.com/hook?access_token=keep-me",
        secret="test-secret",
    )
    with pytest.raises(RuntimeError):
        run(push.send(channel, "test"))
    assert seen[0]["access_token"] == "keep-me"
    if provider == "dingtalk":
        assert "timestamp" in seen[0] and "sign" in seen[0]


def test_json_api_source_mapping(monkeypatch):
    async def fetch(url):
        return (
            b'{"articles":[{"title":"API title","url":"/story","description":"<p>Clean content</p>"}]}',
            url,
        )

    monkeypatch.setattr(fetching, "fetch", fetch)
    result = run(fetching.api_items("https://example.com/api"))
    assert result[0]["source_url"] == "https://example.com/story"
    assert result[0]["summary"] == "Clean content"
    assert result[0]["platform"] == "api"


def test_model_client_is_closed_and_returns_real_output(monkeypatch):
    import openai
    from app.core.config import settings
    from app.services.llm import chat

    closed = []

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            closed.append(True)

        async def create(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "system"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="模型输出"))]
            )

    monkeypatch.setattr(settings.llm, "api_key", "test-only")
    monkeypatch.setattr(openai, "AsyncOpenAI", Client)
    assert run(chat("测试资料")) == "模型输出"
    assert closed == [True]


def test_retry_reuses_unpublished_content_after_failed_task():
    from app.agents.connector_agent import run_connector

    content = SimpleNamespace(id="stored-id", task_id="old-task", status=2)

    class DB:
        async def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: content)

        async def get(self, model, key):
            return SimpleNamespace(status="failed")

        async def commit(self):
            pass

    state = {
        "task_id": "new-task",
        "subscription_id": 1,
        "parser": {
            "items": [
                {
                    "title": "title",
                    "summary": "body",
                    "source_url": "https://example.com/article",
                    "platform": "rss",
                }
            ]
        },
    }
    result = run(run_connector(state, DB()))
    assert result["connector"]["stored_ids"] == ["stored-id"]
    assert content.task_id == "new-task"


def test_persisted_task_state_omits_duplicate_article_bodies():
    from app.services.task_service import compact_state

    original = {
        "scout": {"items": [{"body": "large"}], "source_errors": []},
        "connector": {
            "items": [{"body": "large"}],
            "stored_ids": ["id"],
            "stored_count": 1,
        },
    }
    persisted = compact_state(original)
    assert "items" not in persisted["scout"]
    assert persisted["connector"]["stored_ids"] == ["id"]
    assert original["scout"]["items"]  # serialization does not mutate graph state
