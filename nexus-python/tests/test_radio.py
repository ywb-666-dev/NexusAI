import asyncio
import json
import pytest
from app.services import radio

SOURCES = [
    {
        "id": "film",
        "title": "电影节活动",
        "summary": "电影节将于周六举行，现场安排导演交流活动。",
        "body": "",
        "url": "https://example.com/film",
    },
    {
        "id": "food",
        "title": "社区美食节",
        "summary": "社区美食节提供不同地区的特色菜品。",
        "body": "",
        "url": "https://example.com/food",
    },
]
EVENT = {
    "title": "电影节",
    "summary": "周六有导演交流",
    "citations": [{"id": "film", "quote": "电影节将于周六举行"}],
}


def answer(**changes):
    return {
        "answer": "资料说周六举行电影节，可以了解导演交流活动。",
        "insufficient": False,
        "limitations": "没有提供具体地点、票价和余票信息。",
        "citations": [{"id": "film", "quote": "电影节将于周六举行"}],
        **changes,
    }


def test_only_current_event_sources_are_exposed():
    _, sources = radio.event_context({"events": [EVENT], "sources": SOURCES}, 0)
    assert [s["id"] for s in sources] == ["film"]


@pytest.mark.parametrize("index", [-1, 1, 100])
def test_nonexistent_event_is_rejected(index):
    with pytest.raises(ValueError):
        radio.event_context({"events": [EVENT]}, index)


@pytest.mark.parametrize(
    "change",
    [
        {"citations": []},
        {"citations": [{"id": "foreign", "quote": "电影节将于周六举行"}]},
        {"citations": [{"id": "film", "quote": "虚构的免费电影票说明"}]},
        {"citations": [{"id": "film", "quote": "      "}]},
        {"answer": "   "},
        {"insufficient": "false"},
        {"citations": [{"id": "film", "quote": "电影节将于周六举行"}] * 2},
    ],
)
def test_invalid_answers_cannot_be_saved(change):
    with pytest.raises(ValueError):
        radio.validate_answer(answer(**change), SOURCES[:1])


def test_grounded_answer_and_insufficient_answer():
    assert radio.validate_answer(answer(), SOURCES)["citations"]
    assert radio.validate_answer(
        answer(answer="资料没有提供票价，无法确定。", insufficient=True, citations=[]),
        SOURCES,
    )["insufficient"]


def test_model_receives_bounded_history_and_untrusted_sources(monkeypatch):
    async def chat(prompt, **kwargs):
        data = json.loads(prompt.rsplit("\n", 1)[1])
        assert len(data["conversation_untrusted"]) == 4
        assert data["untrusted_sources"][0]["id"] == "film"
        assert kwargs["structured"] is True
        return json.dumps(answer())

    monkeypatch.setattr(radio, "chat", chat)
    assert asyncio.run(
        radio.answer(EVENT, SOURCES[:1], "讲简单一点", ["history"] * 10)
    )["answer"]


def test_missing_source_does_not_call_model(monkeypatch):
    async def chat(*args, **kwargs):
        raise AssertionError("Should not call model")

    monkeypatch.setattr(radio, "chat", chat)
    assert asyncio.run(radio.answer(EVENT, [], "票价？", []))["insufficient"]


def test_model_error_does_not_create_fabricated_answer(monkeypatch):
    async def chat(*args, **kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(radio, "chat", chat)
    with pytest.raises(RuntimeError):
        asyncio.run(radio.answer(EVENT, SOURCES[:1], "介绍", []))
