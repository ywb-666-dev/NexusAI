"""Parser Agent — 内容解析清洗节点：HTML→纯文本、元数据补全、翻译"""

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.agents.state import NexusState, ParserResult


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
        return BeautifulSoup(html_text, "html.parser").get_text(separator="\n", strip=True)
    except Exception:
        return html_text


def _is_metadata_only(summary: str) -> bool:
    """检测摘要是否只是 HN 风格的元数据（无实际内容）"""
    if not summary:
        return True
    plain = _strip_html(summary) if '<' in summary else summary
    lines = [l.strip() for l in plain.split("\n") if l.strip()]
    meaningful = [
        l for l in lines
        if not re.match(r"^(Article\s*URL|Comments?\s*URL|Points?|#\s*Comments?)\s*[:：]", l, re.IGNORECASE)
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


def _scrape_page(url: str) -> str:
    """抓取网页并提取正文文本"""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        content = soup.find("article") or soup.find("main") or soup.find("body")
        if not content:
            return ""
        text = content.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)[:3000]
    except Exception:
        return ""


async def _translate_to_chinese(text: str) -> str:
    """使用 LLM 将文本翻译为中文"""
    try:
        if not settings.llm.api_key:
            return text
        import openai
        client = openai.OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )
        prompt = f"请将以下英文内容翻译成中文，保持原意，只输出翻译结果不要额外说明：\n\n{text[:1500]}"
        resp = client.chat.completions.create(
            model=settings.llm.chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return text


async def run_parser(state: NexusState, mcp_pool: Any = None) -> NexusState:
    """
    Parser Agent 节点：清洗 Scout 采集的原始内容。

    1. 对元数据-only 的内容通过 MCP web 或直接抓取补全正文
    2. 非中文内容调用 LLM 翻译
    """
    raw_items: list[dict] = state.get("scout", {}).get("items", [])
    if not raw_items:
        state["status"] = "parsing: no items"
        state["parser"] = ParserResult(items=[], cleaned_count=0, scraped_count=0, translated_count=0)
        state["next_node"] = "connector"
        return state

    scraped_count = 0
    translated_count = 0

    # Step 1: 对元数据-only 的内容补全正文
    for item in raw_items:
        if not _is_metadata_only(item.get("raw_html", "")):
            continue
        source_url = item.get("source_url", "")
        if not source_url or not source_url.startswith("http"):
            continue

        scraped_text = ""
        if mcp_pool:
            try:
                result = await mcp_pool.call_tool("web", "scrape_page", {"url": source_url})
                articles = _extract_articles_from_mcp(result)
                if articles:
                    scraped_text = articles[0].get("summary", "")
            except Exception:
                pass

        if not scraped_text:
            scraped_text = _scrape_page(source_url)

        if scraped_text:
            item["summary"] = scraped_text[:2000]
            item["raw_html"] = scraped_text
            item["scraped"] = True
            scraped_count += 1

    # Step 2: 非中文内容翻译
    if settings.llm.api_key:
        for item in raw_items:
            if not _is_chinese(item.get("summary", "")):
                item["summary"] = await _translate_to_chinese(item["summary"])
                translated_count += 1

    state["parser"] = ParserResult(
        items=raw_items,
        cleaned_count=len(raw_items),
        scraped_count=scraped_count,
        translated_count=translated_count,
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
