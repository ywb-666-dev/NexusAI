import asyncio
import os
from typing import Any

import httpx

from .current_news import CurrentNews
from datetime import datetime, timedelta


async def get_current_news() -> Any:
    item = CurrentNews(
        country="cn",
        language="zh",
        keywords="technology",
        category=["technology", "science"],
        page_number=1,
        limit=10,
        start_date=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        has_image=True,
        has_description=True,
    )
    try:
        return item.get_info()
    except Exception as e:
        print(f"Error getting current news: {e}")
        return None


async def get_hacker_news() -> Any:
    """从 Hacker News Firebase API 获取热门文章"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # 获取 Top 30 故事 ID
            resp = await client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json"
            )
            resp.raise_for_status()
            story_ids = resp.json()[:30]

            # 并发获取每个故事的详情
            async def fetch_story(sid: int) -> dict | None:
                try:
                    r = await client.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                    )
                    r.raise_for_status()
                    return r.json()
                except Exception:
                    return None

            stories = await asyncio.gather(*[fetch_story(sid) for sid in story_ids])
            articles = []
            for s in stories:
                if s and s.get("title") and s.get("url"):
                    articles.append({
                        "title": s["title"],
                        "link": s.get("url", f"https://news.ycombinator.com/item?id={s['id']}"),
                        "summary": s.get("text", "")[:500] if s.get("text") else "",
                        "published_at": datetime.fromtimestamp(s.get("time", 0)).isoformat(),
                    })
            print(f"[HN] Fetched {len(articles)} stories")
            return articles
    except Exception as e:
        print(f"[HN] Error: {e}")
        return None


async def get_newsapi_news() -> Any:
    """从 NewsAPI.org 获取头条新闻"""
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        print("[NewsAPI] No NEWSAPI_KEY configured, skipping")
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://newsapi.org/v2/top-headlines",
                params={"country": "us", "pageSize": 20, "apiKey": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            articles = []
            for a in data.get("articles", []):
                articles.append({
                    "title": a.get("title", ""),
                    "link": a.get("url", ""),
                    "summary": (a.get("description") or "")[:500],
                    "published_at": a.get("publishedAt", ""),
                })
            print(f"[NewsAPI] Fetched {len(articles)} articles")
            return articles
    except Exception as e:
        print(f"[NewsAPI] Error: {e}")
        return None


async def get_info() -> list:
    """并发获取三个新闻源的数据"""
    current, hacker, newsapi = await asyncio.gather(
        get_current_news(), get_hacker_news(), get_newsapi_news()
    )
    result = []
    if current:
        result.extend(current if isinstance(current, list) else [current])
    if hacker:
        result.extend(hacker)
    if newsapi:
        result.extend(newsapi)
    return result