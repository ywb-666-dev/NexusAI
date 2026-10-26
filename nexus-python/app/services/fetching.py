"""Bounded asynchronous fetching and source extraction shared by preview and Scout."""

import asyncio
import ipaddress
import os
import socket
import json
from urllib.parse import urlparse, urljoin, urldefrag
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx
import feedparser
from bs4 import BeautifulSoup

MAX_BYTES = 4 * 1024 * 1024


async def validate_url(url: str):
    parts = urlparse(url)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("仅支持不含账号密码的 HTTP/HTTPS 地址")
    if os.getenv("NEXUS_ALLOW_LOCAL_SOURCES") == "true":
        return
    loop = asyncio.get_running_loop()
    addresses = await loop.getaddrinfo(
        parts.hostname,
        parts.port or (443 if parts.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("采集地址不能指向本机或私有网络")


async def fetch(url: str) -> tuple[bytes, str]:
    for attempt in range(3):
        try:
            current = url
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(20, connect=8),
                follow_redirects=False,
                headers={"User-Agent": "NexusAI/1.0 (RSS content reader)"},
            ) as client:
                for _ in range(6):
                    await validate_url(current)
                    async with client.stream("GET", current) as response:
                        if response.is_redirect:
                            current = urljoin(current, response.headers["location"])
                            continue
                        response.raise_for_status()
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_BYTES:
                                raise ValueError("内容超过 4 MB，已停止读取")
                            chunks.append(chunk)
                        return b"".join(chunks), str(response.url)
                raise ValueError("重定向次数过多")
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        ) as exc:
            if isinstance(
                exc, httpx.HTTPStatusError
            ) and exc.response.status_code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            await asyncio.sleep(0.5 * 2**attempt)
    raise RuntimeError("采集失败")


def plain_text(html: str) -> str:
    if not html:
        return ""
    if "<" not in html:
        return html.strip()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "aside", "noscript"]
    ):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup
    return "\n".join(
        line.strip()
        for line in root.get_text("\n", strip=True).splitlines()
        if line.strip()
    )


def published(value):
    if not value:
        return None
    try:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
    except (ValueError, TypeError):
        return None


async def rss_items(url: str) -> list[dict]:
    data, final_url = await fetch(url)
    feed = feedparser.parse(data)
    if not feed.entries and (feed.bozo or not feed.get("version")):
        raise ValueError("该地址不是有效的 RSS/Atom 订阅源")
    items = []
    for entry in feed.entries[:50]:
        link = urldefrag(urljoin(final_url, entry.get("link", "")))[0]
        if not link.startswith(("http://", "https://")):
            continue
        html = (entry.get("content") or [{}])[0].get("value") or entry.get(
            "summary", ""
        )
        items.append(
            {
                "platform": "rss",
                "source_url": link,
                "title": plain_text(entry.get("title", "无标题"))[:500],
                "summary": plain_text(entry.get("summary", html))[:2000],
                "raw_html": html[:100000],
                "author": entry.get("author", "")[:100],
                "published_at": entry.get("published", entry.get("updated", "")),
            }
        )
    return items


async def web_item(url: str) -> dict:
    body, final_url = await fetch(url)
    soup = BeautifulSoup(body, "html.parser")
    title = soup.find("meta", property="og:title")
    author = soup.find("meta", attrs={"name": "author"}) or soup.find(
        "meta", property="article:author"
    )
    date = soup.find("meta", property="article:published_time") or soup.find(
        "meta", attrs={"name": "datePublished"}
    )
    text = plain_text(str(soup))
    return {
        "platform": "web",
        "source_url": final_url,
        "title": (
            title.get("content", "")
            if title
            else soup.title.get_text(strip=True) if soup.title else final_url
        )[:500],
        "summary": text[:2000],
        "raw_html": text[:100000],
        "author": str(author.get("content", ""))[:100] if author else "",
        "published_at": str(date.get("content", "")) if date else "",
    }


async def api_items(url: str) -> list[dict]:
    body, final_url = await fetch(url)
    data = json.loads(body)
    for _ in range(3):
        if isinstance(data, list):
            break
        if not isinstance(data, dict):
            raise ValueError("API 返回的数据格式不受支持")
        data = next(
            (
                data[k]
                for k in ("items", "articles", "news", "data")
                if isinstance(data.get(k), (list, dict))
            ),
            None,
        )
    if not isinstance(data, list):
        raise ValueError("API 需要返回文章数组，或 items/articles/news/data 字段")
    items = []
    for entry in data[:50]:
        if not isinstance(entry, dict):
            continue
        link = entry.get("url") or entry.get("link") or entry.get("source_url")
        if not isinstance(link, str):
            continue
        link = urldefrag(urljoin(final_url, link))[0]
        if not link.startswith(("http://", "https://")):
            continue
        content = (
            entry.get("content")
            or entry.get("description")
            or entry.get("summary")
            or ""
        )
        text = plain_text(
            content
            if isinstance(content, str)
            else json.dumps(content, ensure_ascii=False)
        )
        items.append(
            {
                "platform": "api",
                "source_url": link,
                "title": str(entry.get("title") or "无标题")[:500],
                "summary": text[:2000],
                "raw_html": text[:100000],
                "author": str(entry.get("author") or "")[:100],
                "published_at": str(
                    entry.get("publishedAt")
                    or entry.get("published_at")
                    or entry.get("published")
                    or ""
                ),
            }
        )
    return items
