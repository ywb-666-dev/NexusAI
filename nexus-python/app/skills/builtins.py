"""内置 Agent Skills — 内容采集、翻译、摘要"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from .base import Skill, SkillResult


class ScoutSkill(Skill):
    """内容采集 Skill：RSS / Web / API 多源采集"""

    name = "scout"
    description = "多源内容采集：支持 RSS feed、网页抓取、API 调用"
    version = "1.0.0"
    tags = ["collection", "content", "rss", "web"]

    def __init__(self, mcp_pool: Any = None):
        self.mcp_pool = mcp_pool

    async def execute(self, **kwargs) -> SkillResult:
        from app.agents.scout_agent import run_scout_node

        state = {
            "keywords": kwargs.get("keywords", []),
            "source_platforms": kwargs.get("platforms", ["rss"]),
            "rss_feeds": kwargs.get("feeds", []),
        }
        state = await run_scout_node(state, self.mcp_pool)
        items = state.get("scout", {}).get("items", [])
        return SkillResult(success=True, data={"items": items, "count": len(items)})

    @staticmethod
    def _extract(mcp_result: Any, platform: str, keyword: str) -> list[dict]:
        data = mcp_result
        if hasattr(mcp_result, "content") and mcp_result.content:
            try:
                data = json.loads(mcp_result.content[0].text)
            except Exception:
                return []
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            return []
        items: list[dict] = []
        for item in data:
            d = (
                item
                if isinstance(item, dict)
                else item.model_dump() if hasattr(item, "model_dump") else None
            )
            if d:
                items.append(
                    {
                        "platform": platform,
                        "source_url": d.get("link", keyword),
                        "title": d.get("title", ""),
                        "summary": (d.get("summary", "") or "")[:2000],
                        "published_at": d.get("published_at", ""),
                        "raw_html": d.get("summary", ""),
                    }
                )
        return items


class TranslateSkill(Skill):
    """翻译 Skill：使用 LLM 将英文内容翻译为中文"""

    name = "translate"
    description = "LLM 内容翻译：将非中文内容翻译为中文"
    version = "1.0.0"
    tags = ["nlp", "translate", "llm"]

    async def execute(self, **kwargs) -> SkillResult:
        text = kwargs.get("text", "")
        if not text:
            return SkillResult(success=False, error="No text provided")

        try:
            from app.core.config import settings

            if not settings.llm.api_key:
                return SkillResult(
                    success=True, data={"translated": text, "source": "passthrough"}
                )

            from app.services.llm import chat

            translated = await chat(
                "将以下内容翻译为中文，只输出译文：\n\n" + text[:5000], max_tokens=2000
            )
            return SkillResult(
                success=True,
                data={"translated": translated, "source": "llm"},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e), data={"translated": text})


class SummarizeSkill(Skill):
    """摘要 Skill：使用 LLM 生成内容摘要和日报"""

    name = "summarize"
    description = "LLM 内容摘要：生成文章摘要或日报汇总"
    version = "1.0.0"
    tags = ["nlp", "summary", "llm"]

    async def execute(self, **kwargs) -> SkillResult:
        items_text = kwargs.get("items_text") or kwargs.get("text", "")
        style = kwargs.get("style", "daily_report")  # daily_report | article_summary

        if not items_text:
            return SkillResult(success=False, error="No content to summarize")

        try:
            from app.core.config import settings

            if not settings.llm.api_key:
                return SkillResult(
                    success=True,
                    data={"summary": items_text[:300], "source": "truncate"},
                )

            from app.services.llm import chat

            if style == "daily_report":
                prompt = f"根据以下内容生成一份简洁的中文简报（200字以内）：\n\n{items_text[:8000]}"
            else:
                prompt = f"为以下内容生成100字以内的中文摘要：\n\n{items_text[:5000]}"
            summary = await chat(prompt, max_tokens=500)
            return SkillResult(
                success=True,
                data={"summary": summary, "source": "llm"},
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                data={"summary": items_text[:300], "source": "fallback"},
            )


class DiscoverSourcesSkill(Skill):
    """Recommend from the shared, health-aware source catalog."""

    name = "discover_sources"
    description = "按主题检索数据源目录，返回真实检测状态与 RSS 地址"
    version = "2.0.0"
    tags = ["discovery", "rss", "catalog"]

    async def execute(self, **kwargs) -> SkillResult:
        from app.services.sources import list_sources

        topic = str(kwargs.get("topic", "")).strip()
        if not topic:
            return SkillResult(success=False, error="请输入关注主题")
        sources = await list_sources(topic)
        return SkillResult(
            success=True,
            data={
                "topic": topic,
                "keywords": kwargs.get("keywords", []),
                "suggested_name": topic[:100],
                "sources": sources[:50],
                "total_sources": len(sources),
                "recommended_platforms": ["rss"] if sources else [],
                "notice": "来自共享数据源目录；检测状态仅代表当前服务器最近一次观测。",
            },
        )


class DedupSkill(Skill):
    name = "dedup"
    description = "对输入内容执行精确去重"
    tags = ["dedup", "content"]

    async def execute(self, **kwargs):
        unique, duplicates, seen = [], [], set()
        for item in kwargs.get("items", []):
            key = hashlib.sha256(
                (item.get("title", "") + "\n" + item.get("summary", "")).encode()
            ).hexdigest()
            if key in seen:
                duplicates.append(item.get("id"))
            else:
                seen.add(key)
                unique.append(item)
        return SkillResult(
            success=True,
            data={
                "unique": unique,
                "duplicate_ids": duplicates,
                "unique_count": len(unique),
            },
        )
