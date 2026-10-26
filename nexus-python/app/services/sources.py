"""Shared catalog and bounded feed checks. Health is observed from this server."""

import asyncio
import json
import re
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from sqlalchemy import select
from app.models.source import SourceHealth
from app.core.dependencies import get_session_factory
from app.services.fetching import rss_items

CHECK_LIMIT = asyncio.Semaphore(4)
LOCKS: dict[str, asyncio.Lock] = {}
CATEGORY_TERMS = {
    "ai": ["ai", "人工智能", "大模型", "机器学习", "llm", "agent", "rag"],
    "tech": ["tech", "科技", "数码"],
    "dev": ["编程", "开发", "开源", "programming", "python"],
    "security": ["安全", "漏洞", "security"],
    "science": ["科学", "学术", "论文", "science", "arxiv"],
    "news": ["新闻", "时事", "news"],
    "business": ["商业", "财经", "金融", "投资", "finance"],
    "design": ["设计", "产品", "design"],
    "life": ["生活", "文化", "游戏", "life"],
}


@lru_cache
def catalog():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "data/sources.json").read_text(
            encoding="utf-8"
        )
    )


def search_sources(query="", category="", language=""):
    words = query.lower().strip().split()
    related = (
        {
            key
            for key, terms in CATEGORY_TERMS.items()
            if any(
                (
                    bool(
                        re.search(
                            r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])",
                            query.lower(),
                        )
                    )
                    if term.isascii()
                    else term in query.lower()
                )
                for term in terms
            )
        }
        if query
        else set()
    )
    matches = []
    for source in catalog()["sources"]:
        if category and source["category"] != category:
            continue
        if language and source["language"] != language:
            continue
        haystack = " ".join(
            [source["name"], source["url"], source["description"], *source["tags"]]
        ).lower()
        if words and not (
            all(w in haystack for w in words) or source["category"] in related
        ):
            continue
        matches.append(dict(source))
    return matches


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def health_data(row):
    result = {}
    dates = {"checked_at", "last_success_at", "next_check_at", "latest_item_at"}
    defaults = {
        "status": "unchecked",
        "samples": [],
        "history": [],
        "total_checks": 0,
        "successful_checks": 0,
        "consecutive_failures": 0,
    }
    fields = [
        "status",
        "checked_at",
        "last_success_at",
        "latency_ms",
        "entry_count",
        "error",
        "samples",
        "total_checks",
        "successful_checks",
        "consecutive_failures",
        "error_kind",
        "next_check_at",
        "latest_item_at",
        "quality_score",
        "history",
    ]
    for key in fields:
        value = getattr(row, key, defaults.get(key)) if row else defaults.get(key)
        result[key] = value.isoformat() + "Z" if key in dates and value else value
    result["success_rate"] = (
        round(100 * (result["successful_checks"] or 0) / result["total_checks"])
        if result["total_checks"]
        else None
    )
    checked = getattr(row, "checked_at", None) if row else None
    result["stale"] = bool(checked and utcnow() - checked > timedelta(hours=48))
    return result


def classify_error(exc):
    import httpx

    text = str(exc).lower()
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (404, 410):
            return "not_found"
        if code == 429:
            return "rate_limited"
        if code in (401, 403, 406):
            return "access_denied"
        return "http_error"
    if "certificate" in text or "ssl" in text:
        return "tls"
    if "getaddrinfo" in text or "name resolution" in text:
        return "dns"
    if "私有网络" in text:
        return "blocked_address"
    if isinstance(exc, ValueError):
        return "invalid_feed"
    return "network"


def next_due(row):
    if row.next_check_at:
        return row.next_check_at
    if not row.checked_at:
        return datetime.min
    hours = 24 if row.status == "available" else 6 if row.status == "empty" else 0.25
    return row.checked_at + timedelta(hours=hours)


def apply_observation(row, items, status, error=None, error_kind=None, latency_ms=0):
    from app.services.quality import assess_quality
    from app.services.fetching import published

    now = utcnow()
    row.status, row.error, row.error_kind, row.checked_at = (
        status,
        error,
        error_kind,
        now,
    )
    row.latency_ms, row.entry_count = latency_ms, len(items)
    row.total_checks = (row.total_checks or 0) + 1
    success = status in {"available", "empty"}
    row.successful_checks = (row.successful_checks or 0) + int(success)
    row.consecutive_failures = 0 if success else (row.consecutive_failures or 0) + 1
    if success:
        row.last_success_at = now
    qualities = [
        assess_quality(i.get("raw_html") or i.get("summary", ""), i.get("title", ""))
        for i in items
    ]
    row.quality_score = (
        round(sum(q["score"] for q in qualities) / len(qualities))
        if qualities
        else None
    )
    dates = [date for item in items if (date := published(item.get("published_at")))]
    if dates:
        row.latest_item_at = max(dates)
    row.samples = [
        {
            "title": i["title"],
            "url": i["source_url"],
            "summary": i["summary"][:240],
            "quality": q,
        }
        for i, q in zip(items[:5], qualities[:5])
    ]
    minutes = (
        1440
        if status == "available"
        else (
            360
            if status == "empty"
            else min(1440, 15 * 2 ** min(row.consecutive_failures - 1, 7))
        )
    )
    jitter = int(row.source_id[:4], 16) / 65535 * 0.1
    row.next_check_at = now + timedelta(minutes=minutes * (1 + jitter))
    row.history = [
        *(row.history or []),
        {
            "checked_at": now.isoformat() + "Z",
            "status": status,
            "error_kind": error_kind,
            "entry_count": len(items),
            "quality_score": row.quality_score,
        },
    ][-20:]


async def list_sources(query="", category="", language="", status=""):
    async with get_session_factory()() as db:
        rows = {
            r.source_id: r for r in (await db.execute(select(SourceHealth))).scalars()
        }
    result = [
        {**source, "health": health_data(rows.get(source["id"]))}
        for source in search_sources(query, category, language)
    ]
    if status:
        result = [source for source in result if source["health"]["status"] == status]
    rank = {"available": 0, "empty": 1, "unchecked": 2, "failed": 3}
    return sorted(
        result,
        key=lambda s: (
            rank.get(s["health"]["status"], 3),
            s["language"] != "zh",
            s["name"],
        ),
    )


async def check_source(source_id: str, *, force=False):
    source = next((s for s in catalog()["sources"] if s["id"] == source_id), None)
    if not source:
        raise ValueError("数据源不存在")
    async with LOCKS.setdefault(source_id, asyncio.Lock()):
        async with get_session_factory()() as db:
            row = await db.get(SourceHealth, source_id)
            if (
                row
                and row.checked_at
                and not force
                and row.checked_at
                > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
            ):
                return {"id": source_id, **health_data(row), "cached": True}
        async with CHECK_LIMIT:
            started = time.monotonic()
            try:
                items = await asyncio.wait_for(rss_items(source["url"]), timeout=22)
                status, error = ("available" if items else "empty"), None
                error_kind = None
            except Exception as exc:
                items, status = [], "failed"
                error_kind = classify_error(exc)
                error = (
                    "检测超时（22秒）"
                    if isinstance(exc, TimeoutError)
                    else str(exc) or type(exc).__name__
                )[:500]
            async with get_session_factory()() as db:
                row = await db.get(SourceHealth, source_id)
                if row is None:
                    row = SourceHealth(source_id=source_id)
                    db.add(row)
                apply_observation(
                    row,
                    items,
                    status,
                    error,
                    error_kind,
                    int((time.monotonic() - started) * 1000),
                )
                await db.commit()
                return {"id": source_id, **health_data(row), "cached": False}
