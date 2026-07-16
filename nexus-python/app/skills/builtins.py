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
        "sports": [
            {"url": "https://www.espn.com/espn/rss/news", "name": "ESPN", "platform": "rss"},
            {"url": "https://www.bbc.com/sport/rss.xml", "name": "BBC Sport", "platform": "rss"},
            {"url": "https://www.reddit.com/r/sports/.rss", "name": "Reddit r/sports", "platform": "rss"},
            {"url": "https://www.reddit.com/r/soccer/.rss", "name": "Reddit r/soccer", "platform": "rss"},
        ],
        "sports": [
            {"url": "https://www.espn.com/espn/rss/news", "name": "ESPN Top News", "platform": "rss"},
            {"url": "https://www.skysports.com/rss/12040", "name": "Sky Sports", "platform": "rss"},
            {"url": "https://bleacherreport.com/rss", "name": "Bleacher Report", "platform": "rss"},
            {"url": "https://www.bbc.com/sport/rss.xml", "name": "BBC Sport", "platform": "rss"},
            {"url": "https://www.reddit.com/r/sports/.rss", "name": "Reddit r/sports", "platform": "rss"},
            {"url": "https://www.reddit.com/r/soccer/.rss", "name": "Reddit r/soccer", "platform": "rss"},
            {"url": "https://www.reddit.com/r/worldcup/.rss", "name": "Reddit r/worldcup", "platform": "rss"},
        ],
        "news": [
            {"url": "https://feeds.bbci.co.uk/news/rss.xml", "name": "BBC News", "platform": "rss"},
            {"url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "name": "NYT Home", "platform": "rss"},
            {"url": "https://www.reddit.com/r/worldnews/.rss", "name": "Reddit r/worldnews", "platform": "rss"},
            {"url": "https://feeds.reuters.com/reuters/topNews", "name": "Reuters Top News", "platform": "rss"},
        ],
        "finance": [
            {"url": "https://www.reddit.com/r/stocks/.rss", "name": "Reddit r/stocks", "platform": "rss"},
            {"url": "https://www.reddit.com/r/investing/.rss", "name": "Reddit r/investing", "platform": "rss"},
            {"url": "https://feeds.bloomberg.com/markets/news.rss", "name": "Bloomberg Markets", "platform": "rss"},
        ],
        "health": [
            {"url": "https://www.reddit.com/r/health/.rss", "name": "Reddit r/health", "platform": "rss"},
            {"url": "https://www.medicalnewstoday.com/newsfeeds", "name": "Medical News Today", "platform": "rss"},
        ],
        "gaming": [
            {"url": "https://www.reddit.com/r/gaming/.rss", "name": "Reddit r/gaming", "platform": "rss"},
            {"url": "https://www.reddit.com/r/Games/.rss", "name": "Reddit r/Games", "platform": "rss"},
            {"url": "https://www.pcgamer.com/rss/", "name": "PC Gamer", "platform": "rss"},
        ],
        "science": [
            {"url": "https://www.reddit.com/r/science/.rss", "name": "Reddit r/science", "platform": "rss"},
            {"url": "https://rss.arxiv.org/rss/physics", "name": "arXiv Physics", "platform": "rss"},
            {"url": "https://www.sciencedaily.com/rss/all.xml", "name": "Science Daily", "platform": "rss"},
        ],
        "entertainment": [
            {"url": "https://www.reddit.com/r/movies/.rss", "name": "Reddit r/movies", "platform": "rss"},
            {"url": "https://variety.com/feed/", "name": "Variety", "platform": "rss"},
        ],
        "design": [
            {"url": "https://www.reddit.com/r/design/.rss", "name": "Reddit r/design", "platform": "rss"},
            {"url": "https://www.smashingmagazine.com/feed/", "name": "Smashing Magazine", "platform": "rss"},
        ],
        "education": [
            {"url": "https://www.reddit.com/r/education/.rss", "name": "Reddit r/education", "platform": "rss"},
            {"url": "https://www.coursera.org/blog/feed", "name": "Coursera Blog", "platform": "rss"},
        ],
    }

    async def execute(self, **kwargs) -> SkillResult:
        topic = kwargs.get("topic", "")
        keywords_input = kwargs.get("keywords", [])
        mcp_pool = kwargs.get("mcp_pool", None)

        if not topic and not keywords_input:
            return SkillResult(success=False, error="No topic or keywords provided")

        # 合并关键词列表
        if isinstance(keywords_input, str):
            keywords_input = [k.strip() for k in keywords_input.split(",") if k.strip()]
        all_keywords: list[str] = list(keywords_input)

        # 基于主题/关键词匹配已知源
        matched_sources: list[dict] = []
        seen_urls: set[str] = set()

        # Direct category mapping for Chinese keywords
        _CHINESE_CAT = {
            "世界杯": "sports", "足球": "sports", "篮球": "sports", "NBA": "sports",
            "股票": "finance", "比特币": "finance", "投资": "finance",
            "游戏": "gaming", "电影": "entertainment", "音乐": "entertainment",
            "健康": "health", "疫情": "health", "科学": "science",
        }
        search_terms = [topic.lower()] + [k.lower() for k in all_keywords]
        for kw in all_keywords + [topic]:
            for ck, cat in _CHINESE_CAT.items():
                if ck in kw:
                    search_terms.append(cat); print("[DEBUG_CHK] search_terms BEFORE expand:", search_terms)
        _KW_MAP = {
            "sports": ["世界杯","足球","篮球","NBA","联赛","比赛","网球","F1","奥运会","排球","泳泳"],
            "news": ["新闻","头条","国际","时事"],
            "finance": ["股票","基金","比特币","加密货币","BTC","ETH","投资","理财","A股","经济"],
            "health": ["健康","医学","疫情","减肥","健身","养生"],
            "gaming": ["游戏","手游","端游","PS5","Xbox","Switch","Steam","电竞","LOL","英雄联盟"],
            "science": ["科学","物理","化学","生物","太空","量子","基因","天文"],
            "entertainment": ["电影","音乐","娱乐","明星","综艺","剧集","动漫","韩剧","美剧"],
            "design": ["设计","UI","UX","平面","室内"],
            "education": ["教育","学习","课程","考试","留学","研究生"],
        }
        expanded_terms = list(search_terms)
        
        # Hard-coded: if topic contains sports keywords, add sports feeds
        _SPORTS_KW = ["世界杯","足球","篮球","NBA","英超","西甲","欧冠","网球","F1","奥运会","排球","游泳","棒球","橄榄球","高尔夫"]
        if any(kw in topic.lower() for kw in _SPORTS_KW) or any(any(kw in k.lower() for kw in _SPORTS_KW) for k in all_keywords):
            sports_feeds = [
                {"url": "https://www.espn.com/espn/rss/news", "name": "ESPN", "platform": "rss"},
                {"url": "https://www.bbc.com/sport/rss.xml", "name": "BBC Sport", "platform": "rss"},
                {"url": "https://www.reddit.com/r/sports/.rss", "name": "Reddit r/sports", "platform": "rss"},
                {"url": "https://www.reddit.com/r/soccer/.rss", "name": "Reddit r/soccer", "platform": "rss"},
            ]
            for f in sports_feeds:
                if f["url"] not in seen_urls:
                    seen_urls.add(f["url"])
                    matched_sources.append(dict(f))

        for term in search_terms:
            for cat, kws in _KW_MAP.items():
                if any(kw in term for kw in kws):
                    expanded_terms.append(cat)
        search_terms = list(dict.fromkeys(expanded_terms)); print("[DEBUG_CHK] search_terms AFTER expand:", search_terms)
        
        # Hard-coded: if topic contains sports keywords, add sports feeds
        _SPORTS_KW = ["世界杯","足球","篮球","NBA","英超","西甲","欧冠","网球","F1","奥运会","排球","游泳","棒球","橄榄球","高尔夫"]
        if any(kw in topic.lower() for kw in _SPORTS_KW) or any(any(kw in k.lower() for kw in _SPORTS_KW) for k in all_keywords):
            sports_feeds = [
                {"url": "https://www.espn.com/espn/rss/news", "name": "ESPN", "platform": "rss"},
                {"url": "https://www.bbc.com/sport/rss.xml", "name": "BBC Sport", "platform": "rss"},
                {"url": "https://www.reddit.com/r/sports/.rss", "name": "Reddit r/sports", "platform": "rss"},
                {"url": "https://www.reddit.com/r/soccer/.rss", "name": "Reddit r/soccer", "platform": "rss"},
            ]
            for f in sports_feeds:
                if f["url"] not in seen_urls:
                    seen_urls.add(f["url"])
                    matched_sources.append(dict(f))

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
                "sources": [
                    {"id": str(idx), "url": s["url"], "name": s["name"],
                     "platform": s["platform"], "description": "Built-in source",
                     "relevance": 0.9, "source_type": "builtin"}
                    for idx, s in enumerate(matched_sources)
                ],
                "total_sources": len(matched_sources),
                "recommended_platforms": list(set(s["platform"] for s in matched_sources)),
            },
        )
