"""Explainable content-based ranking: TF-IDF profile, freshness and diversity.

Only ranks articles that passed semantic review. No extra model calls or cross-user data.
"""

import math
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse, urldefrag

VERSION = "content-tfidf-v1"


def features(item):
    text = ((item.title or "")[:300] + " " + (item.summary or "")[:600]).lower()
    terms = re.findall(r"[a-z][a-z0-9_+.-]{2,30}", text)
    for block in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.extend(block[i : i + 2] for i in range(len(block) - 1))
    return Counter(terms)


def cosine(a, b):
    return max(-1.0, min(1.0, sum(v * b.get(k, 0) for k, v in a.items())))


def normalize(vector):
    norm = math.sqrt(sum(v * v for v in vector.values()))
    return {k: v / norm for k, v in vector.items()} if norm else {}


def feedback_data(row):
    return {
        key: bool(getattr(row, key, False)) for key in ("liked", "saved", "dismissed")
    }


def rank(items, history, now=None, *, deduplicate=True):
    now = now or datetime.utcnow()
    eligible = [
        c
        for c in items
        if (c.relevance or {}).get("recommended") is True
        and (c.relevance or {}).get("method") == "llm"
    ]
    documents = {c.id: features(c) for c in [*eligible, *(c for c, _ in history)]}
    frequencies = Counter(term for doc in documents.values() for term in doc)
    vectors = {
        key: normalize(
            {
                term: (1 + math.log(count))
                * (1 + math.log((1 + len(documents)) / (1 + frequencies[term])))
                for term, count in doc.items()
            }
        )
        for key, doc in documents.items()
    }
    profile = Counter()
    feedback = {}
    for c, row in history:
        feedback[c.id] = feedback_data(row)
        weight = -3 if row.dismissed else 2 * int(row.liked) + 3 * int(row.saved)
        # Older explicit interests gradually lose weight, never inferred from unread items.
        age = (
            max(0, (now - row.updated_at).total_seconds() / 86400)
            if row.updated_at
            else 0
        )
        weight *= 2 ** (-age / 90)
        for term, value in vectors[c.id].items():
            profile[term] += weight * value
    profile = normalize(profile)
    cold = not profile
    pending = []
    for c in eligible:
        if feedback.get(c.id, {}).get("dismissed"):
            continue
        relevance = min(100, max(0, float((c.relevance or {}).get("score", 0))))
        quality = min(100, max(0, float((c.quality or {}).get("score", 50))))
        # Use actual publication time when present; newly fetched old stories are not new events.
        date = c.published_at or c.fetched_at or now
        freshness = 100 * 2 ** (-max(0, (now - date).total_seconds() / 86400) / 7)
        interest = 50 + 50 * cosine(profile, vectors[c.id]) if profile else 50
        base = 0.5 * relevance + 0.15 * quality + 0.15 * freshness + 0.2 * interest
        pending.append(
            (
                c,
                base,
                {
                    "semantic": round(relevance, 1),
                    "quality": round(quality, 1),
                    "freshness": round(freshness, 1),
                    "interest": round(interest, 1),
                },
            )
        )
    pending.sort(key=lambda entry: (-entry[1], entry[0].id))
    selected, seen, hosts, subscriptions = [], set(), Counter(), Counter()
    similarities = Counter()
    while pending:
        choices = []
        # Greedy MMR reranking, bounded to a 500 article pool by the caller.
        for c, base, scores in pending:
            similarity = similarities[c.id]
            host = urlparse(c.source_url).hostname or ""
            penalty = (
                12 * similarity
                + 4 * min(hosts[host], 2)
                + 2 * min(subscriptions[c.subscription_id], 2)
            )
            choices.append((base - penalty, c.id, c, scores, penalty))
        score, _, c, scores, penalty = min(choices, key=lambda e: (-e[0], e[1]))
        pending = [entry for entry in pending if entry[0].id != c.id]
        url = urldefrag(c.source_url)[0]
        if deduplicate and url in seen:
            continue
        seen.add(url)
        hosts[urlparse(c.source_url).hostname or ""] += 1
        subscriptions[c.subscription_id] += 1
        for remaining, _, _ in pending:
            similarities[remaining.id] = max(
                similarities[remaining.id], cosine(vectors[c.id], vectors[remaining.id])
            )
        reasons = ["已通过订阅语义筛选", "综合相关度、质量与时效"]
        if cold:
            reasons.append("暂无有效偏好，使用订阅相关度排序")
        elif scores["interest"] > 55:
            reasons.append("与喜欢或收藏的内容接近")
        elif scores["interest"] < 45:
            reasons.append("根据负反馈降低优先级")
        if penalty > 0:
            reasons.append("已考虑相似内容、来源和订阅多样性")
        selected.append(
            (
                c,
                {
                    "score": round(score, 2),
                    "components": scores,
                    "diversityPenalty": round(penalty, 2),
                    "reasons": reasons,
                    "coldStart": cold,
                    "version": VERSION,
                },
            )
        )
    return selected
