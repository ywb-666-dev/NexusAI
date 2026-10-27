"""Read-only public feed discovery, bounded and using the shared safe fetcher."""

import asyncio
import hashlib
import json
import re
import time
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup
from fastapi import HTTPException
from app.services.fetching import fetch, parse_rss, parse_api
from app.services.sources import classify_error

LIMIT = asyncio.Semaphore(2)
ACTIVE = set()
RECENT = {}


def github_releases(url):
    p = urlparse(url)
    if (
        p.scheme not in ("http", "https")
        or p.hostname != "github.com"
        or p.username
        or p.password
    ):
        return None
    match = re.fullmatch(r"/([\w.-]+)/([\w.-]+)(?:/releases)?/?", p.path)
    if not match:
        return None
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if owner in {
        "features",
        "topics",
        "orgs",
        "settings",
        "login",
        "marketplace",
        "collections",
    } or repo in {".", ".."}:
        return None
    return f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=10"


def advertised_feeds(body, final_url):
    soup = BeautifulSoup(body, "html.parser")
    base = soup.find("base", href=True)
    base_url = urljoin(final_url, base["href"]) if base else final_url
    candidates, seen = [], set()
    for link in soup.select('head link[rel~="alternate"][href]'):
        kind = (link.get("type") or "").lower().split(";", 1)[0].strip()
        if kind not in {
            "application/rss+xml",
            "application/atom+xml",
            "application/feed+json",
        }:
            continue
        url = urldefrag(urljoin(base_url, link["href"]))[0]
        if urlparse(url).scheme not in ("http", "https") or url in seen:
            continue
        seen.add(url)
        candidates.append(
            {
                "url": url,
                "name": str(link.get("title") or "发现的订阅源")[:100],
                "platform": "api" if kind == "application/feed+json" else "rss",
            }
        )
        if len(candidates) == 6:
            break
    return candidates


async def probe(url, platform="rss", name="发现的订阅源", prefetched=None):
    identifier = hashlib.sha256(url.encode()).hexdigest()[:16]
    try:
        body, final = prefetched or await asyncio.wait_for(fetch(url), timeout=10)
        items = parse_api(body, final) if platform == "api" else parse_rss(body, final)
        status, error, kind = "available" if items else "empty", None, None
    except Exception as exc:
        kind = classify_error(exc)
        items, status = [], "failed"
        error = {
            "rate_limited": "站点请求配额或频率已达上限，请稍后重试；GitHub 公开 API 也受匿名请求配额限制。",
            "timeout": "来源读取超时，请稍后重试；未将超时结果标记为可用。",
            "blocked_address": "来源地址指向本机或私有网络，已停止读取。",
            "not_found": "该订阅地址不存在或已迁移，请检查原站提供的新地址。",
            "invalid_feed": "该地址没有返回当前支持的订阅格式或可读取的文章地址。",
            "access_denied": "站点拒绝访问，请确认来源是否公开可读。",
        }.get(kind, "发现的地址读取失败，请检查网络、访问限制或源格式。")
    return {
        "id": identifier,
        "url": url,
        "name": name,
        "platform": platform,
        "discovered": True,
        "description": "本次只读发现结果，未加入公共目录，也未创建订阅。",
        "homepage": f"https://{urlparse(url).hostname}",
        "category": "",
        "language": "",
        "health": {
            "status": status,
            "error": error,
            "error_kind": kind,
            "entry_count": len(items),
            "samples": [
                {
                    "title": i["title"],
                    "url": i["source_url"],
                    "summary": i["summary"][:240],
                }
                for i in items[:3]
            ],
        },
    }


async def discover(url):
    repo = github_releases(url)
    if repo:
        return {
            "sources": [
                await probe(
                    repo, "api", "GitHub Releases · " + urlparse(url).path.strip("/")
                )
            ],
            "notice": "读取公开项目发布说明，不下载安装包；匿名 API 请求受 GitHub 配额限制。",
        }
    body, final = await asyncio.wait_for(fetch(url), timeout=12)
    try:
        data = json.loads(body)
        jsonfeed = isinstance(data, dict) and data.get("version") in (
            "https://jsonfeed.org/version/1",
            "https://jsonfeed.org/version/1.1",
        )
    except (ValueError, UnicodeError):
        data, jsonfeed = None, False
    if jsonfeed:
        candidates = [
            {
                "url": final,
                "platform": "api",
                "name": str(data.get("title") or "JSON Feed")[:100],
            }
        ]
        direct = True
    else:
        try:
            parse_rss(body, final)
            candidates = [
                {"url": final, "platform": "rss", "name": "RSS / Atom 订阅源"}
            ]
            direct = True
        except ValueError:
            candidates, direct = advertised_feeds(body, final), False
    semaphore = asyncio.Semaphore(3)

    async def verify(source):
        async with semaphore:
            return await probe(**source, prefetched=(body, final) if direct else None)

    results = await asyncio.gather(*(verify(source) for source in candidates))
    return {
        "sources": results,
        "notice": (
            "只读取网页公开声明的前 6 个 RSS/Atom/JSON Feed 并实际验证；不扫描猜测路径，不创建订阅。"
            if results
            else "页面没有公开声明可识别的 RSS/Atom/JSON Feed，可换用网站的订阅页或直接添加公开网页来源。"
        ),
    }


async def run_discovery(user_id, url):
    now = time.monotonic()
    if user_id in ACTIVE or now - RECENT.get(user_id, -100) < 10:
        raise HTTPException(429, "请稍候再发现来源，同一用户最多一个进行中的请求")
    ACTIVE.add(user_id)
    RECENT[user_id] = now
    for key, value in list(RECENT.items()):
        if now - value > 3600:
            RECENT.pop(key, None)
    try:
        async with LIMIT:
            return await asyncio.wait_for(discover(url), timeout=40)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "无法读取该公开地址，请检查网络、地址或站点访问限制")
    finally:
        ACTIVE.discard(user_id)
