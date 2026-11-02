from datetime import datetime, timedelta
from types import SimpleNamespace as Obj
from app.services.recommendation import rank, features

NOW = datetime(2026, 11, 2)


def item(key, text="本地模型离线部署性能测试", **changes):
    return Obj(
        **{
            "id": key,
            "title": text,
            "summary": text * 4,
            "source_url": f"https://{key}.example.com/article",
            "subscription_id": 1,
            "relevance": {"recommended": True, "method": "llm", "score": 90},
            "quality": {"score": 90},
            "published_at": NOW,
            "fetched_at": NOW,
            **changes,
        }
    )


def feedback(**changes):
    return Obj(
        **{
            "liked": False,
            "saved": False,
            "dismissed": False,
            "updated_at": NOW,
            **changes,
        }
    )


def test_cold_start_is_deterministic_and_explained():
    rows = [item("b"), item("a")]
    result = rank(rows, [], NOW)
    assert [c.id for c, _ in result] == [c.id for c, _ in rank(rows[::-1], [], NOW)]
    assert result[0][1]["coldStart"] and result[0][1]["reasons"]


def test_positive_feedback_promotes_related_content():
    a, b = item("a", "旅行摄影风景相机"), item("b")
    result = rank([a, b], [(item("history"), feedback(liked=True, saved=True))], NOW)
    assert result[0][0].id == "b"
    assert result[0][1]["components"]["interest"] > 50


def test_negative_feedback_reduces_related_topics_and_hides_article():
    history = item("history")
    result = rank(
        [item("a"), item("b", "旅行摄影相机风景"), history],
        [(history, feedback(dismissed=True))],
        NOW,
    )
    assert result[0][0].id == "b" and "history" not in [c.id for c, _ in result]


def test_cleared_feedback_restores_cold_start():
    assert rank([item("a")], [(item("history"), feedback())], NOW)[0][1]["coldStart"]


def test_semantic_rejections_and_legacy_items_cannot_be_promoted():
    assert (
        rank(
            [
                item(
                    "a", relevance={"recommended": False, "method": "llm", "score": 100}
                ),
                item("b", relevance=None),
            ],
            [],
            NOW,
        )
        == []
    )


def test_old_publication_is_not_freshened_by_new_fetch():
    old = item("a", published_at=NOW - timedelta(days=70))
    result = rank([old, item("b")], [], NOW)
    assert result[0][0].id == "b"


def test_diversity_and_exact_url_dedup():
    rows = [
        item("a"),
        item("b"),
        item("c", "旅行摄影相机风景"),
        item("d", source_url="https://a.example.com/article#duplicate"),
    ]
    result = rank(rows, [], NOW)
    assert len(result) == 3
    assert result[1][0].id == "c"


def test_chinese_bigrams_and_english_tokens():
    assert "本地" in features(item("a", "本地模型 Python deployment"))
    assert "python" in features(item("a", "本地模型 Python deployment"))
