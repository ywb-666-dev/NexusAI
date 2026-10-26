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


def health_data(row):
    if not row:
        return {
            "status": "unchecked",
            "checked_at": None,
            "last_success_at": None,
            "latency_ms": None,
            "entry_count": None,
            "error": None,
            "samples": [],
        }
    return {
        key: (
            (getattr(row, key).isoformat() + "Z" if getattr(row, key) else None)
            if key in {"checked_at", "last_success_at"}
            else getattr(row, key)
        )
        for key in [
            "status",
            "checked_at",
            "last_success_at",
            "latency_ms",
            "entry_count",
            "error",
            "samples",
        ]
    }


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
            except Exception as exc:
                items, status = [], "failed"
                error = (
                    "检测超时（22秒）"
                    if isinstance(exc, TimeoutError)
                    else str(exc) or type(exc).__name__
                )[:500]
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            async with get_session_factory()() as db:
                row = await db.get(SourceHealth, source_id)
                if row is None:
                    row = SourceHealth(source_id=source_id)
                    db.add(row)
                row.status, row.error, row.checked_at = status, error, now
                row.latency_ms = int((time.monotonic() - started) * 1000)
                row.entry_count = len(items)
                row.samples = [
                    {
                        "title": i["title"],
                        "url": i["source_url"],
                        "summary": i["summary"][:240],
                    }
                    for i in items[:5]
                ]
                if status in {"available", "empty"}:
                    row.last_success_at = now
                await db.commit()
                return {"id": source_id, **health_data(row), "cached": False}
