"""Health-aware automatic source selection; manual additions always take precedence."""

import asyncio
import re
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Annotated
from app.services.sources import list_sources, check_source, CATEGORY_TERMS


class SourcePolicy(BaseModel):
    mode: Literal["auto", "manual"] = "auto"
    topic: str = Field(default="", max_length=200)
    language: Literal["zh_first", "all"] = "zh_first"
    excluded_ids: list[Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]] = Field(
        default_factory=list, max_length=50
    )

    @model_validator(mode="after")
    def topic_required(self):
        self.topic = self.topic.strip()
        if self.mode == "auto" and not self.topic:
            raise ValueError("自动匹配需要填写关注主题")
        return self


def rank_source(source, policy):
    topic = policy.topic.lower()
    name = source["name"].lower()
    terms = [term for term in re.split(r"[\s,，、/]+", topic) if term]
    literal = any(
        (
            bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", name))
            if term.isascii() and len(term) <= 2
            else term in name
        )
        for term in terms
    )
    related = source["category"] in {
        key
        for key, words in CATEGORY_TERMS.items()
        if any(
            (
                bool(
                    re.search(
                        r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", topic
                    )
                )
                if word.isascii()
                else word in topic
            )
            for word in words
        )
    }
    domain_match = "." in topic and topic in source["url"].lower()
    if not literal and not related and not domain_match:
        return -1000
    generic_topic = (
        topic in CATEGORY_TERMS.get(source["category"], []) and topic != "python"
    )
    score = 80 if domain_match or (literal and not generic_topic) else 40
    health = source["health"]
    score += 30 if health["status"] == "available" else 0
    score += (health.get("quality_score") or 0) / 10
    score += (health.get("success_rate") or 0) / 20
    score += 15 if policy.language == "zh_first" and source["language"] == "zh" else 0
    return score


async def resolve_sources(policy: SourcePolicy, limit=5, *, allow_checks=True):
    if limit <= 0:
        return {
            "feeds": [],
            "sources": [],
            "notice": "额外来源已占满本订阅的 20 个位置，未加入系统来源。",
        }
    candidates = [
        s
        for s in await list_sources(policy.topic)
        if s["id"] not in policy.excluded_ids and rank_source(s, policy) >= 30
    ]
    candidates.sort(key=lambda s: (-rank_source(s, policy), s["id"]))
    usable = [
        s
        for s in candidates
        if s["health"]["status"] in {"available", "empty"}
        and not s["health"].get("stale")
    ]
    if not usable and allow_checks:
        # A fresh installation can validate a few matching candidates on demand.
        pending, hosts = [], set()
        for source in candidates:
            if source["health"]["status"] != "unchecked" or source["homepage"] in hosts:
                continue
            pending.append(source)
            hosts.add(source["homepage"])
            if len(pending) == 4:
                break
        if pending:
            await asyncio.gather(*(check_source(s["id"]) for s in pending))
            return await resolve_sources(policy, limit, allow_checks=False)
    chosen, hosts = [], set()
    for source in usable:
        if source["homepage"] in hosts:
            continue
        chosen.append(source)
        hosts.add(source["homepage"])
        if len(chosen) >= limit:
            break
    feeds = []
    for source in chosen:
        reasons = [
            "与关注主题匹配",
            (
                "最近检测可用"
                if source["health"]["status"] == "available"
                else "订阅格式有效，当前暂无条目"
            ),
        ]
        if policy.language == "zh_first" and source["language"] == "zh":
            reasons.append("优先中文")
        feeds.append(
            {
                "url": source["url"],
                "name": source["name"],
                "platform": source.get("platform", "rss"),
                "origin": "system",
                "sourceId": source["id"],
                "reason": "；".join(reasons),
            }
        )
    return {
        "feeds": feeds,
        "sources": chosen,
        "notice": (
            f"已自动匹配 {len(feeds)} 个来源；用户额外添加的来源会保留。"
            if feeds
            else "未找到近期检测可用的相关来源，请调整关注主题、稍后重试或手动添加来源。"
        ),
    }


async def resolve_semantic_sources(
    policy, semantic_policy, limit=5, *, allow_checks=True, plan=None
):
    from app.services.semantic import compile_intent

    plan = plan or await compile_intent(semantic_policy)
    queries = list(
        dict.fromkeys(
            [
                *plan["source_queries"],
                *(CATEGORY_TERMS[category][0] for category in plan["categories"]),
            ]
        )
    )[:6]
    groups = await asyncio.gather(
        *(
            resolve_sources(
                policy.model_copy(update={"topic": query}), limit, allow_checks=False
            )
            for query in queries
        )
    )
    if not any(group["feeds"] for group in groups) and allow_checks and queries:
        groups[0] = await resolve_sources(
            policy.model_copy(update={"topic": queries[0]}), limit, allow_checks=True
        )
    feeds, sources, hosts, seen = [], [], set(), set()
    # Interleave understood topics so a broad first category cannot consume all slots.
    for index in range(limit):
        for group in groups:
            if index >= len(group["feeds"]):
                continue
            feed = group["feeds"][index]
            source = group["sources"][index]
            if feed["sourceId"] in seen or source["homepage"] in hosts:
                continue
            feeds.append(
                {**feed, "reason": "根据订阅语义选择候选来源；文章还需逐条语义审核"}
            )
            sources.append(source)
            seen.add(feed["sourceId"])
            hosts.add(source["homepage"])
            if len(feeds) >= limit:
                break
        if len(feeds) >= limit:
            break
    return {
        "feeds": feeds,
        "sources": sources,
        "semantic_plan": plan,
        "notice": (
            f"已根据需求理解选择 {len(feeds)} 个候选来源；仅推荐语义审核通过的文章。"
            if feeds
            else "已理解订阅需求，但当前来源库没有健康的匹配来源，请额外添加来源或稍后重试。"
        ),
    }


async def resolve_subscription_sources(
    feeds, conditions, *, allow_checks=False, semantic_plan=None
):
    raw_policy = conditions.get("source_policy", {})
    if raw_policy.get("mode") != "auto":
        return list(feeds), None
    policy = SourcePolicy.model_validate(raw_policy)
    manual = [{**f, "origin": "manual"} for f in feeds if f.get("origin") != "system"]
    if len(manual) > 20:
        raise ValueError("每个订阅最多 20 个来源")
    limit = min(5, 20 - len(manual))
    from app.services.semantic import SemanticPolicy

    semantic = SemanticPolicy.model_validate(conditions.get("semantic_filter") or {})
    if semantic.enabled and limit:
        resolution = await resolve_semantic_sources(
            policy, semantic, limit, allow_checks=allow_checks, plan=semantic_plan
        )
    else:
        resolution = await resolve_sources(policy, limit, allow_checks=allow_checks)
    seen = {f["url"] for f in manual}
    combined = list(manual)
    for feed in resolution["feeds"]:
        if feed["url"] not in seen:
            combined.append(feed)
            seen.add(feed["url"])
    if not combined:
        raise ValueError(resolution["notice"])
    system_count = sum(f.get("origin") == "system" for f in combined)
    return combined, {
        "notice": (
            f"本次使用 {system_count} 个系统来源，并保留 {len(manual)} 个用户额外来源。"
            if resolution["feeds"]
            else resolution["notice"]
        ),
        "system_count": system_count,
        "manual_count": len(manual),
    }
