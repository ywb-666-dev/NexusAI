import asyncio
import json
import pytest
from app.services import semantic

PLAN = {
    "summary": "关注个人设备的开放模型实用教程",
    "include": ["个人设备离线推理", "开放权重", "部署或性能实测"],
    "exclude": ["融资与广告", "云端API"],
    "source_queries": ["人工智能", "开源"],
    "categories": ["ai", "dev"],
}


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    semantic.PLANS.values.clear()
    semantic.JUDGMENTS.values.clear()
    monkeypatch.setattr(semantic.settings.llm, "api_key", "test-key")
    yield
    semantic.PLANS.values.clear()
    semantic.JUDGMENTS.values.clear()


def article(
    title="Guide",
    body="A fully offline open-weight model runs on a personal laptop. Benchmark: 14 tokens per second.",
):
    return {
        "title": title,
        "summary": body,
        "raw_html": body,
        "source_url": "https://example.com/article",
        "platform": "rss",
    }


def verdict(id="0", **kwargs):
    return {
        "id": id,
        "score": 90,
        "matches": True,
        "excluded": False,
        "reason": "符合个人电脑离线使用及性能实测需求",
        "evidence": ["A fully offline open-weight model"],
        **kwargs,
    }


def test_plan_uses_model_and_caches_understanding(monkeypatch):
    calls = []

    async def chat(*args, **kwargs):
        calls.append(1)
        return json.dumps(PLAN)

    monkeypatch.setattr(semantic, "chat", chat)

    async def run():
        policy = semantic.SemanticPolicy(
            enabled=True, intent="关注个人电脑离线文字助手"
        )
        assert (await semantic.compile_intent(policy))["categories"] == ["ai", "dev"]
        assert await semantic.compile_intent(policy) == PLAN

    asyncio.run(run())
    assert len(calls) == 1


def test_unconfigured_model_never_falls_back(monkeypatch):
    monkeypatch.setattr(semantic.settings.llm, "api_key", "")
    with pytest.raises(semantic.SemanticError, match="未退回关键词"):
        asyncio.run(
            semantic.compile_intent(
                semantic.SemanticPolicy(enabled=True, intent="大模型")
            )
        )


@pytest.mark.parametrize(
    "change",
    [
        {"score": "90"},
        {"score": True},
        {"score": 101},
        {"matches": "true"},
        {"id": "unknown"},
        {"evidence": []},
        {"evidence": ["Fabricated quote does not exist"]},
        {"evidence": ["      "]},
        {"evidence": ["A\n\n\n\n\nf"]},
        {"reason": "      "},
    ],
)
def test_invalid_model_results_cannot_be_published(change):
    with pytest.raises(semantic.SemanticError):
        semantic.validate_verdicts(
            {"items": [verdict(**change)]}, [semantic.article_input(article(), 0)]
        )


def test_missing_and_duplicate_judgments_fail_closed():
    inputs = [semantic.article_input(article(), 0)]
    for raw in [
        {"items": []},
        {"items": [verdict(), verdict()]},
        {"result": [verdict()]},
    ]:
        with pytest.raises(semantic.SemanticError):
            semantic.validate_verdicts(raw, inputs)


def test_evidence_allows_real_quotes_with_normalized_whitespace():
    result = semantic.validate_verdicts(
        {"items": [verdict(evidence=["A fully\n\n offline open-weight model"])]},
        [semantic.article_input(article(), 0)],
    )
    assert result["0"]["matches"] is True


def test_intent_plan_rejects_blank_interpretation():
    with pytest.raises(ValueError):
        semantic.IntentPlan.model_validate({**PLAN, "include": ["   "]})


def test_exclusion_overrides_high_score_and_cache_avoids_repeat_cost(monkeypatch):
    calls = []

    async def chat(*args, **kwargs):
        calls.append(1)
        return json.dumps(
            {"items": [verdict(excluded=True, reason="命中明确排除条件")]}
        )

    monkeypatch.setattr(semantic, "chat", chat)

    async def run():
        policy = semantic.SemanticPolicy(
            enabled=True, intent="离线助手", exclusions="不看云服务"
        )
        first = await semantic.filter_articles([article()], policy, PLAN)
        second = await semantic.filter_articles([article()], policy, PLAN)
        assert first["items"] == [] and first["summary"]["rejected_count"] == 1
        assert second["summary"]["cache_hits"] == 1

    asyncio.run(run())
    assert len(calls) == 1


def test_synonym_article_survives_irrelevant_legacy_keywords(monkeypatch):
    from app.agents.scout_agent import run_scout_node
    from app.services import fetching

    async def rss(url):
        return [article()]

    monkeypatch.setattr(fetching, "rss_items", rss)
    result = asyncio.run(
        run_scout_node(
            {
                "rss_feeds": [{"url": "https://example.com/feed", "platform": "rss"}],
                "keywords": ["本地部署"],
                "semantic_policy": {"enabled": True},
            }
        )
    )
    assert len(result["scout"]["items"]) == 1


def test_semantic_candidates_are_interleaved_across_sources(monkeypatch):
    from app.agents.scout_agent import run_scout_node
    from app.services import fetching

    async def rss(url):
        return [{**article(), "source_url": url + str(i)} for i in range(25)]

    monkeypatch.setattr(fetching, "rss_items", rss)
    feeds = [
        {"url": "https://one.example/feed", "platform": "rss"},
        {"url": "https://two.example/feed", "platform": "rss"},
    ]
    result = asyncio.run(
        run_scout_node({"rss_feeds": feeds, "semantic_policy": {"enabled": True}})
    )
    assert "two.example" in result["scout"]["items"][1]["source_url"]


def test_threshold_budget_sorting_and_explanations(monkeypatch):
    async def chat(prompt, **kwargs):
        data = json.loads(prompt.rsplit("\n", 1)[1])
        return json.dumps(
            {
                "items": [
                    verdict(a["id"], score=70 + int(a["id"]) * 5)
                    for a in data["untrusted_articles"]
                ]
            }
        )

    monkeypatch.setattr(semantic, "chat", chat)
    policy = semantic.SemanticPolicy(
        enabled=True, intent="离线助手", threshold=80, max_candidates=5
    )
    rows = [{**article(), "title": str(i)} for i in range(8)]
    result = asyncio.run(semantic.filter_articles(rows, policy, PLAN))
    assert [i["relevance"]["score"] for i in result["items"]] == [90, 85, 80]
    assert result["summary"]["unevaluated_count"] == 3
    assert result["items"][0]["relevance"]["method"] == "llm"


def test_model_failure_does_not_return_unfiltered_items(monkeypatch):
    async def chat(*args, **kwargs):
        raise RuntimeError("service down")

    monkeypatch.setattr(semantic, "chat", chat)
    with pytest.raises(semantic.SemanticError, match="未退回关键词"):
        asyncio.run(
            semantic.filter_articles(
                [article()], semantic.SemanticPolicy(enabled=True, intent="助手"), PLAN
            )
        )


def test_semantic_trial_uses_same_filter_and_never_opens_database(monkeypatch):
    from app.services import fetching, trial
    import app.core.dependencies as deps

    async def rss(url):
        return [{**article(), "raw_html": article()["raw_html"] * 20}]

    async def chat(*args, **kwargs):
        return json.dumps({"items": [verdict()]})

    def db():
        raise AssertionError("trial wrote database")

    monkeypatch.setattr(fetching, "rss_items", rss)
    monkeypatch.setattr(semantic, "chat", chat)
    monkeypatch.setattr(deps, "get_session_factory", db)
    result = asyncio.run(
        trial.trial_collect(
            [{"url": "https://example.com/feed", "platform": "rss"}],
            ["unmatched"],
            semantic.SemanticPolicy(enabled=True, intent="离线助手"),
            PLAN,
        )
    )
    assert result["semantic"]["accepted_count"] == 1
    assert result["items"][0]["relevance"]["score"] == 90


def test_failed_batch_cancels_other_model_requests(monkeypatch):
    async def run():
        started = asyncio.Event()
        closed = []

        async def chat(prompt, **kwargs):
            data = json.loads(prompt.rsplit("\n", 1)[1])
            if data["untrusted_articles"][0]["id"] == "0":
                await started.wait()
                raise RuntimeError("provider failed")
            started.set()
            try:
                await asyncio.sleep(30)
            finally:
                closed.append(True)

        monkeypatch.setattr(semantic, "chat", chat)
        with pytest.raises(semantic.SemanticError):
            await semantic.filter_articles(
                [{**article(), "title": str(i)} for i in range(6)],
                semantic.SemanticPolicy(enabled=True, intent="助手"),
                PLAN,
            )
        assert closed == [True]

    asyncio.run(run())


def test_deepseek_semantic_calls_use_bounded_structured_mode(monkeypatch):
    import openai
    from types import SimpleNamespace
    from app.services.llm import chat

    received = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0 and kwargs["timeout"] == 75
            self.chat = SimpleNamespace(completions=self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def create(self, **kwargs):
            received.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))
                ]
            )

    monkeypatch.setattr(openai, "AsyncOpenAI", Client)
    monkeypatch.setattr(semantic.settings.llm, "base_url", "https://api.deepseek.com")
    asyncio.run(chat("Return JSON", structured=True))
    assert received[0]["extra_body"]["thinking"]["type"] == "disabled"
    assert received[0]["response_format"]["type"] == "json_object"
