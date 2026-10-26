"""Parser Agent — 内容解析清洗节点：HTML→纯文本、元数据补全、翻译"""

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.agents.state import NexusState, ParserResult
import asyncio
from collections import Counter
from app.services.fetching import plain_text
from app.services.quality import assess_quality


# CJK unicode range
_CJK_RE = re.compile(r"[一-鿿㐀-䶿豈-﫿]")

_META_PATTERNS = [
    r"Article\s*URL\s*:\s*<a\s",
    r"Comments\s*URL\s*:\s*<a\s",
    r"Points?\s*:\s*\d+",
    r"#\s*Comments?\s*:\s*\d+",
]


def _strip_html(html_text: str) -> str:
    """去掉 HTML 标签，返回纯文本"""
    try:
        return BeautifulSoup(html_text, "html.parser").get_text(
            separator="\n", strip=True
        )
    except Exception:
        return html_text


def _is_metadata_only(summary: str) -> bool:
    """检测摘要是否只是 HN 风格的元数据（无实际内容）"""
    if not summary:
        return True
    plain = _strip_html(summary) if "<" in summary else summary
    lines = [l.strip() for l in plain.split("\n") if l.strip()]
    meaningful = [
        l
        for l in lines
        if not re.match(
            r"^(Article\s*URL|Comments?\s*URL|Points?|#\s*Comments?)\s*[:：]",
            l,
            re.IGNORECASE,
        )
        and not re.match(r"^\d+\s*points?", l, re.IGNORECASE)
        and not re.match(r"^\d+\s*comments?", l, re.IGNORECASE)
        and not re.match(r"^https?://", l.strip())
        and len(l.strip()) > 10
    ]
    return sum(len(l) for l in meaningful) < 50


def _is_chinese(text: str) -> bool:
    """检测文本中是否有足够的中文内容"""
    if not text:
        return False
    cjk_chars = len(_CJK_RE.findall(text))
    return cjk_chars > len(text) * 0.15


async def _scrape_page(url: str) -> str:
    """抓取网页并提取正文文本"""
    try:
        from app.services.fetching import fetch

        body, _ = await fetch(url)
        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        ):
            tag.decompose()
        content = soup.find("article") or soup.find("main") or soup.find("body")
        if not content:
            return ""
        text = content.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)[:100000]
    except Exception:
        return ""


async def _translate_to_chinese(text: str) -> str:
    try:
        from app.services.llm import chat

        return await chat(
            "将以下内容翻译成中文，只输出译文：\n\n" + text[:1500], max_tokens=1500
        )
    except Exception:
        return text


async def prepare_items(raw_items, *, max_scrapes=20, scrape_timeout=12):
    """Bounded enrichment and quality checks, with no writes or model requests."""
    items = [dict(item) for item in raw_items]
    for item in items:
        item["raw_html"] = plain_text(item.get("raw_html") or item.get("summary", ""))[
            :100000
        ]
        item["summary"] = plain_text(item.get("summary", ""))[:2000]
        item["quality"] = assess_quality(item["raw_html"], item.get("title", ""))
        item["quality"]["extraction"] = "source"
    candidates = [
        i
        for i in items
        if i["quality"]["kind"] != "body"
        and i.get("source_url", "").startswith(("https://", "http://"))
    ][:max_scrapes]
    semaphore = asyncio.Semaphore(3)

    async def enrich(item):
        async with semaphore:
            try:
                body = await asyncio.wait_for(
                    _scrape_page(item["source_url"]), timeout=scrape_timeout
                )
                quality = assess_quality(body, item.get("title", ""))
                if quality["eligible"] and quality["score"] > item["quality"]["score"]:
                    item["raw_html"], item["summary"] = body[:100000], body[:2000]
                    item["quality"] = {**quality, "extraction": "page"}
                    item["scraped"] = True
                elif item["quality"]["eligible"]:
                    item["quality"]["reasons"].append(
                        "正文补全未获得更完整内容，保留来源内容"
                    )
            except Exception:
                item["quality"]["reasons"].append("正文补全失败，保留来源内容")

    await asyncio.gather(*(enrich(item) for item in candidates))
    rejected = [
        {
            "title": i.get("title", ""),
            "url": i.get("source_url", ""),
            "quality": i["quality"],
        }
        for i in items
        if not i["quality"]["eligible"]
    ]
    return {
        "items": [i for i in items if i["quality"]["eligible"]],
        "scraped_count": sum(bool(i.get("scraped")) for i in items),
        "rejected_count": len(rejected),
        "rejected": rejected[:20],
        "quality_counts": dict(Counter(i["quality"]["kind"] for i in items)),
    }


async def run_parser(state: NexusState, mcp_pool: Any = None) -> NexusState:
    """
    Parser Agent 节点：清洗 Scout 采集的原始内容。

    1. 使用与试采共享的有界正文补全和质量判断，拦截异常页面
    2. 开启 AI 时，对非中文内容调用 LLM 翻译
    """
    raw_items: list[dict] = state.get("scout", {}).get("items", [])
    if not raw_items:
        state["status"] = "parsing: no items"
        state["parser"] = ParserResult(
            items=[], cleaned_count=0, scraped_count=0, translated_count=0
        )
        state["next_node"] = "connector"
        return state

    prepared = await prepare_items(raw_items)
    raw_items = prepared["items"]
    scraped_count = prepared["scraped_count"]
    translated_count = 0
    # Step 2: 非中文内容翻译
    if settings.llm.api_key and state.get("enable_ai", False):
        import asyncio

        targets = [
            item for item in raw_items if not _is_chinese(item.get("summary", ""))
        ][:10]
        results = await asyncio.gather(
            *(_translate_to_chinese(item["summary"]) for item in targets)
        )
        for item, translated in zip(targets, results):
            if translated != item["summary"]:
                item["translated_summary"] = translated
                translated_count += 1

    state["parser"] = ParserResult(
        items=raw_items,
        cleaned_count=len(raw_items),
        scraped_count=scraped_count,
        translated_count=translated_count,
        rejected_count=prepared["rejected_count"],
        quality_counts=prepared["quality_counts"],
        rejected=prepared["rejected"],
    )
    state["next_node"] = "connector"
    return state


def _extract_articles_from_mcp(mcp_result: Any) -> list[dict]:
    """从 MCP 结果中提取文章列表"""
    import json

    data = mcp_result
    if hasattr(mcp_result, "content") and mcp_result.content:
        if hasattr(mcp_result.content[0], "text"):
            try:
                data = json.loads(mcp_result.content[0].text)
            except Exception:
                return []
    if isinstance(data, dict):
        data = [data]
    elif hasattr(data, "model_dump"):
        data = [data.model_dump()]
    elif not isinstance(data, list):
        return []
    result: list[dict] = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
        elif hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif hasattr(item, "dict"):
            result.append(item.dict())
    return result
