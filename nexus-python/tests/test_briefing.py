import asyncio
import copy
from datetime import datetime
from types import SimpleNamespace
import pytest
from app.services import briefing


def sources():
    return [
        {
            "id": "a",
            "title": "本地模型工具更新",
            "summary": "开放权重助手支持离线安装，测试机器使用16GB内存。",
            "body": "",
            "url": "https://example.com/a",
            "intent": "个人电脑离线助手",
            "reason": "有可复现实测",
            "score": 95,
            "subscription": "模型",
        },
        {
            "id": "b",
            "title": "安全修复",
            "summary": "开发工具修复认证绕过，维护者建议及时升级。",
            "body": "",
            "url": "https://example.com/b",
            "intent": "开发安全",
            "reason": "相关安全更新",
            "score": 90,
            "subscription": "安全",
        },
    ]


def outline():
    return {
        "headline": "个人情报",
        "overview": "离线工具与安全更新",
        "events": [
            {
                "title": "离线工具",
                "summary": "提供离线安装实测",
                "attention": "建议查看测试条件",
                "citations": [{"id": "a", "quote": "开放权重助手支持离线安装"}],
            }
        ],
        "omitted": [{"id": "b", "reason": "本期优先关注部署实操"}],
    }


def test_grounded_outline_covers_every_source():
    assert (
        briefing.validate_outline(outline(), sources())["events"][0]["citations"][0][
            "id"
        ]
        == "a"
    )


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "duplicate",
        "missing",
        "invented",
        "whitespace",
        "blank_summary",
        "unknown_omitted",
        "duplicate_omitted",
        "extra",
    ],
)
def test_invalid_briefing_never_becomes_report(change):
    raw = copy.deepcopy(outline())
    citation = raw["events"][0]["citations"][0]
    if change == "unknown":
        citation["id"] = "outside-user"
    elif change == "duplicate":
        raw["events"].append(copy.deepcopy(raw["events"][0]))
    elif change == "missing":
        raw["omitted"] = []
    elif change == "invented":
        citation["quote"] = "不存在的原文内容"
    elif change == "whitespace":
        citation["quote"] = "       "
    elif change == "blank_summary":
        raw["events"][0]["summary"] = "     "
    elif change == "unknown_omitted":
        raw["omitted"][0]["id"] = "outside-user"
    elif change == "duplicate_omitted":
        raw["omitted"].append({"id": "a", "reason": "重复"})
    elif change == "extra":
        raw["events"][0]["url"] = "https://invented.example"
    with pytest.raises(ValueError):
        briefing.validate_outline(raw, sources())


def test_source_dedup_and_only_semantic_recommendations():
    text = "The open-weight model can run offline on a personal laptop. " * 3

    def row(key, url, body=text, recommended=True, method="llm"):
        return (
            SimpleNamespace(
                id=key,
                source_url=url,
                content_body=body,
                summary=body,
                title=key,
                relevance={"recommended": recommended, "method": method},
            ),
            SimpleNamespace(name="test"),
        )

    rows = [
        row("a", "https://example.com/a?utm_source=one"),
        row("b", "https://example.com/a?utm_source=two", "different"),
        row("c", "https://else.example/a"),
        row("d", "https://example.com/d", "different", False),
        row("e", "https://example.com/e", "different", method="keyword"),
        row("f", "javascript:alert(1)", "different"),
    ]
    assert [s["id"] for s in briefing.make_sources(rows)] == ["a"]


def test_report_links_are_from_server_snapshots():
    raw = briefing.validate_outline(outline(), sources())
    text = briefing.report_text(SimpleNamespace(report={**raw, "sources": sources()}))
    assert "https://example.com/a" in text and "原文：本地模型工具更新" in text


@pytest.mark.parametrize(
    "now, enabled_at, enabled, expected",
    [
        (datetime(2026, 10, 26, 0), datetime(2026, 10, 25), True, "7:2026-10-26"),
        (datetime(2026, 10, 25, 23, 59), datetime(2026, 10, 25), True, None),
        (datetime(2026, 10, 26, 1), datetime(2026, 10, 26, 0, 1), True, None),
        (datetime(2026, 10, 27, 0), datetime(2026, 10, 26, 0, 1), True, "7:2026-10-27"),
        (datetime(2026, 10, 26, 0), datetime(2026, 10, 25), False, None),
    ],
)
def test_schedule_uses_shanghai_and_next_eight_am(now, enabled_at, enabled, expected):
    assert (
        briefing.due_key(
            SimpleNamespace(user_id=7, enabled_at=enabled_at, enabled=enabled), now
        )
        == expected
    )


def test_model_failure_is_not_a_fake_brief(monkeypatch):
    async def chat(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(briefing, "chat", chat)
    with pytest.raises(RuntimeError):
        asyncio.run(briefing.compose(sources()))


def test_model_receives_untrusted_sources_and_strict_output(monkeypatch):
    import json

    async def chat(prompt, **kwargs):
        assert (
            json.loads(prompt.rsplit("\n", 1)[1])["untrusted_sources"][0]["id"] == "a"
        )
        assert kwargs["structured"] is True
        return json.dumps(outline())

    monkeypatch.setattr(briefing, "chat", chat)
    assert asyncio.run(briefing.compose(sources()))["headline"] == "个人情报"
