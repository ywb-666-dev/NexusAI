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
        keywords = kwargs.get("keywords", [])
        platforms = kwargs.get("platforms", ["rss"])
        raw_items: list[dict] = []

        for keyword in keywords:
            if "rss" in platforms and self.mcp_pool:
                try:
                    result = await self.mcp_pool.call_tool("rss", "fetch_rss", {"url": keyword})
                    raw_items.extend(self._extract(result, "rss", keyword))
                except Exception as e:
                    print(f"[ScoutSkill] RSS failed '{keyword}': {e}")

            if "api" in platforms and self.mcp_pool:
                try:
                    result = await self.mcp_pool.call_tool("api", "call_api", {})
                    raw_items.extend(self._extract(result, "api", keyword))
                except Exception as e:
                    print(f"[ScoutSkill] API failed: {e}")

        return SkillResult(
            success=len(raw_items) > 0,
            data={"items": raw_items, "count": len(raw_items)},
        )

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
            d = item if isinstance(item, dict) else item.model_dump() if hasattr(item, "model_dump") else None
            if d:
                items.append({
                    "platform": platform,
                    "source_url": d.get("link", keyword),
                    "title": d.get("title", ""),
                    "summary": (d.get("summary", "") or "")[:2000],
                    "published_at": d.get("published_at", ""),
                    "raw_html": d.get("summary", ""),
                })
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
                return SkillResult(success=True, data={"translated": text, "source": "passthrough"})

            import openai
            client = openai.OpenAI(
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
            )
            resp = client.chat.completions.create(
                model=settings.llm.chat_model,
                messages=[{
                    "role": "user",
                    "content": f"请将以下内容翻译为中文，只输出译文：\n\n{text[:1500]}",
                }],
                temperature=0.3,
                max_tokens=1500,
            )
            translated = resp.choices[0].message.content.strip()
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
        items_text = kwargs.get("items_text", "")
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

            import openai
            client = openai.OpenAI(
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
            )

            if style == "daily_report":
                prompt = f"请根据以下今日采集的内容生成一份简洁日报（200字以内）：\n\n{items_text}"
            else:
                prompt = f"请为以下内容生成一段100字以内的摘要：\n\n{items_text[:1000]}"

            resp = client.chat.completions.create(
                model=settings.llm.chat_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            return SkillResult(
                success=True,
                data={"summary": resp.choices[0].message.content.strip(), "source": "llm"},
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                data={"summary": items_text[:300], "source": "fallback"},
            )


class DiscoverSourcesSkill(Skill):
    """源发现 Skill：根据主题自动搜索相关 RSS / Web / API 源"""

    name = "discover_sources"
    description = "AI 源发现：根据主题关键词自动发现相关 RSS 源、Web 源和 API 源"
    version = "1.0.0"
    tags = ["discovery", "rss", "web", "llm"]

    # 内置知名 RSS 源映射
    _KNOWN_FEEDS: dict[str, list[dict]] = {
        "ai": [
            {"url": "https://hnrss.org/frontpage", "name": "Hacker News Frontpage", "platform": "rss"},
            {"url": "https://rss.arxiv.org/rss/cs.AI", "name": "arXiv AI", "platform": "rss"},
            {"url": "https://rss.arxiv.org/rss/cs.CL", "name": "arXiv CL (NLP)", "platform": "rss"},
            {"url": "https://rss.arxiv.org/rss/cs.LG", "name": "arXiv Machine Learning", "platform": "rss"},
            {"url": "https://www.reddit.com/r/MachineLearning/.rss", "name": "Reddit r/MachineLearning", "platform": "rss"},
            {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog", "platform": "rss"},
            {"url": "https://blog.google/technology/ai/rss/", "name": "Google AI Blog", "platform": "rss"},
            {"url": "https://www.anthropic.com/blog/rss.xml", "name": "Anthropic Blog", "platform": "rss"},
            {"url": "https://arxiv.org/rss/cs.CV", "name": "arXiv Computer Vision", "platform": "rss"},
        ],
        "tech": [
            {"url": "https://hnrss.org/frontpage", "name": "Hacker News", "platform": "rss"},
            {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "platform": "rss"},
            {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "platform": "rss"},
            {"url": "https://arstechnica.com/feed/", "name": "Ars Technica", "platform": "rss"},
            {"url": "https://www.wired.com/feed/rss", "name": "WIRED", "platform": "rss"},
            {"url": "https://feeds.feedburner.com/TechCrunch/", "name": "TechCrunch (Feedburner)", "platform": "rss"},
        ],
        "security": [
            {"url": "https://krebsonsecurity.com/feed/", "name": "Krebs on Security", "platform": "rss"},
            {"url": "https://www.schneier.com/feed/", "name": "Schneier on Security", "platform": "rss"},
            {"url": "https://threatpost.com/feed/", "name": "Threatpost", "platform": "rss"},
            {"url": "https://www.darkreading.com/rss.xml", "name": "Dark Reading", "platform": "rss"},
        ],
        "programming": [
            {"url": "https://hnrss.org/frontpage", "name": "Hacker News", "platform": "rss"},
            {"url": "https://www.reddit.com/r/programming/.rss", "name": "Reddit r/programming", "platform": "rss"},
            {"url": "https://github.blog/feed/", "name": "GitHub Blog", "platform": "rss"},
            {"url": "https://stackoverflow.blog/feed/", "name": "Stack Overflow Blog", "platform": "rss"},
        ],
        "python": [
            {"url": "https://www.reddit.com/r/Python/.rss", "name": "Reddit r/Python", "platform": "rss"},
            {"url": "https://realpython.com/feed/", "name": "Real Python", "platform": "rss"},
            {"url": "https://pypi.org/rss/updates.xml", "name": "PyPI Updates", "platform": "rss"},
            {"url": "https://blog.jetbrains.com/pycharm/feed/", "name": "PyCharm Blog", "platform": "rss"},
        ],
        "business": [
            {"url": "https://www.economist.com/feeds/print-sections/77/business.xml", "name": "The Economist - Business", "platform": "rss"},
            {"url": "https://feeds.bloomberg.com/markets/news.rss", "name": "Bloomberg Markets", "platform": "rss"},
            {"url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "name": "CNBC Top News", "platform": "rss"},
        ],
        "startup": [
            {"url": "https://hnrss.org/frontpage", "name": "Hacker News", "platform": "rss"},
            {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "platform": "rss"},
            {"url": "https://www.producthunt.com/feed", "name": "Product Hunt", "platform": "rss"},
        ],
    }

    async def execute(self, **kwargs) -> SkillResult:
        topic = kwargs.get("topic", "")
        keywords_input = kwargs.get("keywords", [])

        if not topic and not keywords_input:
            return SkillResult(success=False, error="No topic or keywords provided")

        # 合并关键词列表
        if isinstance(keywords_input, str):
            keywords_input = [k.strip() for k in keywords_input.split(",") if k.strip()]
        all_keywords: list[str] = list(keywords_input)

        # 基于主题/关键词匹配已知源
        matched_sources: list[dict] = []
        seen_urls: set[str] = set()

        search_terms = [topic.lower()] + [k.lower() for k in all_keywords]
        for term in search_terms:
            for category, feeds in self._KNOWN_FEEDS.items():
                if category in term or any(
                    kw in category or category in kw
                    for kw in search_terms
                ):
                    for feed in feeds:
                        if feed["url"] not in seen_urls:
                            seen_urls.add(feed["url"])
                            matched_sources.append(dict(feed))

        # 如果关键词匹配不到内置分类，使用 LLM 推荐
        if not matched_sources:
            try:
                llm_sources = await self._llm_discover(topic, all_keywords)
                matched_sources = llm_sources
            except Exception as e:
                print(f"[DiscoverSources] LLM discovery failed: {e}")

        # 确保至少有一些通用源
        if not matched_sources:
            for cat in ["ai", "tech"]:
                for feed in self._KNOWN_FEEDS.get(cat, []):
                    if feed["url"] not in seen_urls:
                        seen_urls.add(feed["url"])
                        matched_sources.append(dict(feed))
                        if len(matched_sources) >= 5:
                            break
                if len(matched_sources) >= 5:
                    break

        rss_urls = [s["url"] for s in matched_sources if s["platform"] == "rss"]
        web_sources = [s["url"] for s in matched_sources if s["platform"] == "web"]
        api_sources = [s["url"] for s in matched_sources if s["platform"] == "api"]

        # 生成建议名称
        suggested_name = topic or ", ".join(all_keywords[:3])
        if suggested_name and len(suggested_name) < 15:
            suggested_name = f"{suggested_name} 动态监控"

        return SkillResult(
            success=True,
            data={
                "topic": topic,
                "keywords": all_keywords,
                "suggested_name": suggested_name,
                "rss_urls": rss_urls,
                "web_sources": web_sources,
                "api_sources": api_sources,
                "recommended_platforms": list(set(
                    s["platform"] for s in matched_sources
                )),
                "total_sources": len(matched_sources),
            },
        )

    async def _llm_discover(self, topic: str, keywords: list[str]) -> list[dict]:
        """使用 LLM 发现相关的 RSS 源"""
        from app.core.config import settings

        if not settings.llm.api_key:
            return []

        import openai
        client = openai.OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )
        keyword_str = ", ".join(keywords) if keywords else topic
        prompt = (
            f"请为以下主题推荐最多 8 个高质量的英文 RSS 订阅源 URL（必须是真实存在的 RSS/XML feed 地址）：\n"
            f"主题：{topic}\n关键词：{keyword_str}\n\n"
            f"请严格按以下 JSON 格式输出，不要输出其他内容：\n"
            f'[{{"url": "https://...", "name": "源名称", "platform": "rss"}}, ...]\n\n'
            f"优先推荐：Reddit 子版块 RSS、arXiv RSS、知名科技博客 RSS、Hacker News RSS。"
        )

        try:
            resp = client.chat.completions.create(
                model=settings.llm.chat_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content.strip()
            # 提取 JSON 数组
            import re
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                sources = json.loads(match.group())
                return sources
            return []
        except Exception:
            return []


class DedupSkill(Skill):
    """去重 Skill：语义相似度 + 硬哈希去重"""

    name = "dedup"
    description = "语义去重：Milvus 向量相似度 + SHA-256 哈希双重去重"
    version = "1.0.0"
    tags = ["content", "dedup", "milvus"]

    async def execute(self, **kwargs) -> SkillResult:
        items = kwargs.get("items", [])
        if not items:
            return SkillResult(success=True, data={"duplicates": [], "unique": []})

        try:
            from app.memory.milvus_client import milvus_client as mc
            from app.core.config import settings

            seen_hashes: set[str] = set()
            duplicates: list[str] = []
            unique: list[dict] = []

            for item in items:
                content_text = f"{item.get('title', '')}\n{item.get('summary', '')}"[:2000]
                c_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

                if c_hash in seen_hashes:
                    duplicates.append(item.get("id", c_hash))
                    continue
                seen_hashes.add(c_hash)

                # Milvus semantic check
                try:
                    emb = self._get_embedding(content_text)
                    similar = mc.search_similar(
                        embedding=emb,
                        top_k=1,
                        threshold=settings.milvus.dedup_threshold,
                    )
                    if similar:
                        duplicates.append(item.get("id", c_hash))
                        continue
                except Exception:
                    pass

                unique.append(item)

            return SkillResult(
                success=True,
                data={"unique": unique, "duplicate_ids": duplicates, "unique_count": len(unique)},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    @staticmethod
    def _get_embedding(text: str) -> list[float]:
        try:
            from app.core.config import settings
            import openai
            emb_key = settings.llm.embedding_api_key or settings.llm.api_key
            client = openai.OpenAI(api_key=emb_key, base_url=settings.llm.base_url)
            resp = client.embeddings.create(model=settings.llm.embedding_model, input=text[:8000])
            return resp.data[0].embedding
        except Exception:
            return []
