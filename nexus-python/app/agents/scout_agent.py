import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.state import ScoutState
from app.memory.milvus_client import milvus_client
from app.models import Subscription, Content, Notification
from app.core.dependencies import get_redis_client
from app.core.config import settings
import httpx
from bs4 import BeautifulSoup


# ============== Embedding helper ==============

def _get_embedding(text: str) -> list[float]:
    """
    获取文本的 embedding 向量。
    优先使用 EMBEDDING_API_KEY，未配置时降级到 LLM_API_KEY，失败时降级为随机向量（仅用于测试）。
    """
    try:
        import openai
        emb_key = settings.llm.embedding_api_key or settings.llm.api_key
        client = openai.OpenAI(
            api_key=emb_key,
            base_url=settings.llm.base_url,
        )
        resp = client.embeddings.create(
            model=settings.llm.embedding_model,
            input=text[:8000],
        )
        return resp.data[0].embedding
    except Exception:
        import random
        dim = settings.llm.embedding_dimensions
        return [random.uniform(-0.1, 0.1) for _ in range(dim)]


def _content_hash(text: str) -> str:
    """生成内容 SHA-256 哈希"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ============== Graph Nodes ==============

async def fetch_sources(state: ScoutState, mcp_pool: Any, db: AsyncSession) -> dict:
    """获取原始内容源：RSS 直接用 feedparser，Web 走 MCP Playwright"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "fetching")

    raw_items: list[dict] = []
    platforms = state.get("source_platforms", [])
    keywords = state.get("keywords", [])

    for keyword in keywords:
        # RSS: 直接用 feedparser（无需 MCP 子进程）
        if "rss" in platforms:
            try:
                import feedparser
                import asyncio
                loop = asyncio.get_event_loop()
                d = await loop.run_in_executor(None, feedparser.parse, keyword)
                if d.entries:
                    for entry in d.entries:
                        raw_items.append({
                            "platform": "rss",
                            "source_url": entry.get("link", keyword),
                            "title": entry.get("title", ""),
                            "summary": (entry.get("summary", "") or entry.get("description", ""))[:2000],
                            "published_at": entry.get("published", "") or entry.get("updated", ""),
                            "raw": {"html": entry.get("summary", "") or entry.get("description", "")},
                        })
                    print(f"[fetch_sources] RSS '{keyword}': {len(d.entries)} items")
            except Exception as e:
                print(f"[fetch_sources] RSS failed for '{keyword}': {e}")

        # Web: 尝试 MCP Playwright 抓取
        if "web" in platforms and keyword.startswith("http"):
            try:
                result = await mcp_pool.call_tool("web", "scrape_page", {"url": keyword})
                raw_items.append({
                    "platform": "web",
                    "source_url": result.get("url", keyword),
                    "title": result.get("title", ""),
                    "summary": result.get("html", "")[:500],
                    "published_at": "",
                    "raw": result,
                })
                print(f"[fetch_sources] Web '{keyword}': OK")
            except Exception as e:
                print(f"[fetch_sources] Web failed for '{keyword}': {e}")

    return {"raw_items": raw_items, "status": "fetched"}


async def parse_content(state: ScoutState, db: AsyncSession) -> dict:
    """将原始内容解析为结构化数据"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "parsing")

    parsed: list[dict] = []
    for item in state.get("raw_items", []):
        body = item.get("raw", {}).get("html", item.get("summary", ""))
        content_text = f"{item.get('title', '')}\n{item.get('summary', '')}\n{body}"[:2000]
        c_hash = _content_hash(content_text)

        parsed.append({
            "id": str(uuid.uuid4()),
            "subscription_id": state["subscription_id"],
            "source_platform": item.get("platform", "unknown"),
            "source_url": item.get("source_url", ""),
            "title": item.get("title", "")[:500],
            "summary": item.get("summary", "")[:2000],
            "content_body": body,
            "author": item.get("raw", {}).get("author", ""),
            "published_at": item.get("published_at", ""),
            "content_hash": c_hash,
            "embedding": _get_embedding(content_text),
        })

    return {"parsed_contents": parsed, "status": "parsed"}


async def check_duplicate(state: ScoutState, db: AsyncSession) -> dict:
    """使用 Milvus 进行语义去重检查"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "checking_duplicates")

    duplicates: list[str] = []
    for content in state.get("parsed_contents", []):
        try:
            similar = milvus_client.search_similar(
                embedding=content["embedding"],
                top_k=1,
                threshold=settings.milvus.dedup_threshold,
            )
            if similar:
                duplicates.append(content["id"])
        except Exception:
            pass

    return {
        "duplicate_ids": duplicates,
        "duplicate_count": len(duplicates),
        "status": "checked",
    }


async def store_content(state: ScoutState, db: AsyncSession) -> dict:
    """将非重复内容保存到 MySQL 和 Milvus"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "storing")

    stored_ids: list[str] = []
    duplicate_set = set(state.get("duplicate_ids", []))
    vectors_to_insert: list[dict] = []

    for content in state.get("parsed_contents", []):
        if content["id"] in duplicate_set:
            continue

        # MySQL 插入
        db_content = Content(
            id=content["id"],
            subscription_id=content["subscription_id"],
            source_platform=content["source_platform"],
            source_url=content["source_url"],
            title=content["title"],
            summary=content["summary"],
            content_body=content.get("content_body", ""),
            author=content.get("author", ""),
            content_hash=content["content_hash"],
            status=1,
            is_duplicate=0,
        )
        db.add(db_content)
        vectors_to_insert.append({
            "content_id": content["id"],
            "embedding": content["embedding"],
        })
        stored_ids.append(content["id"])

    await db.commit()

    # Milvus 插入
    if vectors_to_insert:
        try:
            vector_ids = milvus_client.insert_vectors(vectors_to_insert)
            # TODO: 将 vector_id 写回 content 表
        except Exception:
            pass

    return {
        "stored_ids": stored_ids,
        "stored_count": len(stored_ids),
        "status": "stored",
    }


async def notify(state: ScoutState, db: AsyncSession) -> dict:
    """发送通知：保存到 notification 表"""
    task_id = state["task_id"]
    await _update_task_status(task_id, "notifying")

    stored_count = state.get("stored_count", 0)
    if stored_count > 0:
        # 查询订阅的 user_id
        result = await db.execute(
            select(Subscription.user_id).where(Subscription.id == state["subscription_id"])
        )
        user_id = result.scalar()
        if user_id:
            notification = Notification(
                user_id=user_id,
                type="task",
                title=f"采集任务完成: {task_id[:8]}",
                content=f"新增 {stored_count} 条内容",
                is_read=0,
                related_id=task_id,
            )
            db.add(notification)
            await db.commit()

    await _update_task_status(task_id, "completed")
    return {"status": "completed"}


async def handle_error(state: ScoutState) -> dict:
    """错误处理节点"""
    task_id = state["task_id"]
    await _update_task_status(task_id, f"error: {state.get('error', 'unknown')}")
    return {"status": "error"}


# ============== Task execution ==============

async def _update_task_status(task_id: str, status: str) -> None:
    """更新任务状态到 Redis"""
    try:
        redis = get_redis_client()
        await redis.setex(
            f"agent:status:{task_id}",
            3600,
            json.dumps({"status": status, "updated_at": datetime.utcnow().isoformat()}),
        )
    except Exception:
        pass


async def get_task_status(task_id: str) -> dict:
    """从 Redis 查询任务状态"""
    try:
        redis = get_redis_client()
        data = await redis.get(f"agent:status:{task_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {"status": "unknown"}


# ---- MCP result extraction ----

def _extract_articles(mcp_result: Any) -> list[dict]:
    """从 MCP CallToolResult / raw list / raw dict 中提取文章 dict 列表。
    兼容 MCP SDK 的 CallToolResult、Pydantic 模型、原生 list/dict 等返回形式。
    """
    data: Any = mcp_result

    # MCP SDK CallToolResult (有 .content 属性)
    if hasattr(mcp_result, 'content') and mcp_result.content:
        if hasattr(mcp_result.content[0], 'text'):
            try:
                data = json.loads(mcp_result.content[0].text)
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            return []

    # 单篇文章 dict / Pydantic 模型
    if isinstance(data, dict):
        data = [data]
    elif hasattr(data, 'model_dump'):  # Pydantic v2
        data = [data.model_dump()]
    elif hasattr(data, 'dict'):  # Pydantic v1
        data = [data.dict()]
    elif not isinstance(data, list):
        return []

    # 归一化 list 内元素
    result: list[dict] = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
        elif hasattr(item, 'model_dump'):
            result.append(item.model_dump())
        elif hasattr(item, 'dict'):
            result.append(item.dict())
        else:
            continue
    return result


# ---- HTML strip ----

def _strip_html(html_text: str) -> str:
    """去掉 HTML 标签，返回纯文本"""
    try:
        return BeautifulSoup(html_text, "html.parser").get_text(separator="\n", strip=True)
    except Exception:
        return html_text


# ---- Metadata detection ----

_META_PATTERNS = [
    r"Article\s*URL\s*:\s*<a\s",
    r"Comments\s*URL\s*:\s*<a\s",
    r"Points?\s*:\s*\d+",
    r"#\s*Comments?\s*:\s*\d+",
]


def _is_metadata_only(summary: str) -> bool:
    """检测摘要是否只是 HN 风格的元数据（无实际内容）。支持 HTML 和纯文本。"""
    if not summary:
        return True
    # 先尝试作为 HTML 解析，纯文本则直接使用
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


# ---- Web scraper ----

def _scrape_page(url: str) -> str:
    """抓取网页并提取正文文本"""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除无用标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        # 优先从 <article> 或 <main> 提取
        content = soup.find("article") or soup.find("main") or soup.find("body")
        if not content:
            return ""

        text = content.get_text(separator="\n", strip=True)
        # 清理多余空行
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)[:3000]
    except Exception as e:
        print(f"[Scout] Scrape failed '{url}': {e}")
        return ""


# ---- Translation ----

# CJK unicode range
_CJK_RE = re.compile(r"[一-鿿㐀-䶿豈-﫿]")


def _is_chinese(text: str) -> bool:
    """检测文本中是否有足够的中文内容"""
    if not text:
        return False
    cjk_chars = len(_CJK_RE.findall(text))
    return cjk_chars > len(text) * 0.15  # 超过 15% 是中文字符


def _translate_to_chinese(text: str) -> str:
    """使用 LLM 将文本翻译为中文"""
    try:
        if not settings.llm.api_key:
            return text
        import openai
        client = openai.OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )
        prompt = (
            "请将以下英文内容翻译成中文，保持原意，只输出翻译结果不要额外说明：\n\n"
            + text[:1500]
        )
        resp = client.chat.completions.create(
            model=settings.llm.chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        translated = resp.choices[0].message.content.strip()
        print(f"[Scout] Translated: {text[:80]}... -> {translated[:80]}...")
        return translated
    except Exception as e:
        print(f"[Scout] Translation failed: {e}")
        return text


# ---- Task execution ----

async def run_scout_task(
    task_id: str,
    subscription_id: int,
    keywords: list[str],
    source_platforms: list[str],
    mcp_pool: Any,
    db: AsyncSession,
) -> None:
    """采集流水线：MCP RSS/Web/API → 网页刮取补全 → 翻译 → 去重存储"""
    try:
        await _update_task_status(task_id, "fetching")

        # Step 1: 通过 MCP 获取原始内容
        raw_items: list[dict] = []

        # --- RSS ---
        for keyword in keywords:
            if "rss" not in source_platforms:
                continue
            try:
                result = await mcp_pool.call_tool("rss", "fetch_rss", {"url": keyword})
                articles = _extract_articles(result)
                for a in articles:
                    summary = a.get("summary", "")
                    raw_items.append({
                        "platform": "rss",
                        "source_url": a.get("link", keyword),
                        "title": a.get("title", ""),
                        "summary": summary[:2000],
                        "published_at": a.get("published_at", ""),
                        "author": "",
                        "raw_html": summary,
                    })
                print(f"[Scout] MCP RSS '{keyword}': {len(articles)} items")
            except Exception as e:
                print(f"[Scout] MCP RSS failed '{keyword}', falling back: {e}")
                await _rss_fallback(keyword, raw_items)

        # --- Web ---
        for keyword in keywords:
            if "web" not in source_platforms or not keyword.startswith("http"):
                continue
            try:
                result = await mcp_pool.call_tool("web", "scrape_page", {"url": keyword})
                articles = _extract_articles(result)
                for a in articles:
                    summary = a.get("summary", "")
                    raw_items.append({
                        "platform": "web",
                        "source_url": a.get("link", keyword),
                        "title": a.get("title", ""),
                        "summary": summary[:2000],
                        "published_at": a.get("published_at", ""),
                        "author": "",
                        "raw_html": summary,
                    })
                print(f"[Scout] MCP Web '{keyword}': OK")
            except Exception as e:
                print(f"[Scout] MCP Web failed '{keyword}': {e}")

        # --- API ---
        if "api" in source_platforms:
            try:
                result = await mcp_pool.call_tool("api", "call_api", {})
                articles = _extract_articles(result)
                for a in articles:
                    summary = a.get("summary", "")
                    raw_items.append({
                        "platform": "api",
                        "source_url": a.get("link", ""),
                        "title": a.get("title", ""),
                        "summary": summary[:2000],
                        "published_at": a.get("published_at", ""),
                        "author": "",
                        "raw_html": summary,
                    })
                print(f"[Scout] MCP API: {len(articles)} items")
            except Exception as e:
                print(f"[Scout] MCP API failed: {e}")

        if not raw_items:
            await _update_task_status(task_id, "completed: no items found")
            return

        # Step 2: 对元数据-only 的内容通过 MCP web 抓取完整正文
        await _update_task_status(task_id, f"scraping {len(raw_items)} items")
        for item in raw_items:
            if not _is_metadata_only(item["raw_html"]):
                continue
            source_url = item["source_url"]
            if not source_url or not source_url.startswith("http"):
                continue
            print(f"[Scout] Metadata-only detected, scraping: {source_url}")
            try:
                result = await mcp_pool.call_tool("web", "scrape_page", {"url": source_url})
                articles = _extract_articles(result)
                if articles:
                    scraped_text = articles[0].get("summary", "")
                    if scraped_text:
                        item["summary"] = scraped_text[:2000]
                        item["raw_html"] = scraped_text
                        item["scraped"] = True
            except Exception:
                # Fallback to direct httpx scraping
                scraped = _scrape_page(source_url)
                if scraped:
                    item["summary"] = scraped[:2000]
                    item["raw_html"] = scraped
                    item["scraped"] = True

        # Step 3: 非中文内容翻译
        need_translation = settings.llm.api_key and any(
            not _is_chinese(item["summary"]) for item in raw_items
        )
        if need_translation:
            await _update_task_status(task_id, "translating")
            for item in raw_items:
                if not _is_chinese(item["summary"]):
                    item["summary"] = _translate_to_chinese(item["summary"])

        # Step 4: 去重 + 存储
        await _update_task_status(task_id, "storing")
        from sqlalchemy import select as sa_select

        stored = 0
        for item in raw_items:
            try:
                content_text = f"{item['title']}\n{item['summary']}"[:2000]
                c_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

                result = await db.execute(
                    sa_select(Content).where(Content.content_hash == c_hash)
                )
                if result.scalar_one_or_none():
                    continue

                cid = str(uuid.uuid4())
                db_content = Content(
                    id=cid,
                    subscription_id=subscription_id,
                    source_platform=item["platform"],
                    source_url=item["source_url"],
                    title=item["title"][:500],
                    summary=item["summary"][:2000],
                    content_body=item.get("raw_html", ""),
                    author=item.get("author", ""),
                    content_hash=c_hash,
                    status=1,
                    is_duplicate=0,
                )
                db.add(db_content)
                stored += 1
            except Exception as e:
                print(f"[Scout] Store failed: {e}")

        if stored > 0:
            await db.commit()
            print(f"[Scout] Stored {stored} new items")

            result = await db.execute(
                select(Subscription.user_id).where(Subscription.id == subscription_id)
            )
            user_id = result.scalar()
            if user_id:
                notification = Notification(
                    user_id=user_id,
                    type="task",
                    title=f"采集完成: {task_id[:8]}",
                    content=f"新增 {stored} 条内容",
                    is_read=0,
                    related_id=task_id,
                )
                db.add(notification)
                await db.commit()

        await _update_task_status(task_id, f"completed: {stored} items")

    except Exception as e:
        print(f"[Scout] Task failed: {e}")
        import traceback
        traceback.print_exc()
        await _update_task_status(task_id, f"error: {str(e)}")


async def _rss_fallback(keyword: str, raw_items: list[dict]) -> None:
    """feedparser 直调降级，MCP RSS 不可用时使用"""
    try:
        import feedparser as _feedparser
        loop = asyncio.get_running_loop()
        d = await loop.run_in_executor(None, _feedparser.parse, keyword)
        if not d.entries:
            return
        for entry in d.entries:
            author = ""
            if entry.get("author_detail"):
                author = entry["author_detail"].get("name", "")
            elif entry.get("author"):
                author = entry["author"] if isinstance(entry["author"], str) else ""
            summary_html = entry.get("summary", "") or entry.get("description", "")
            raw_items.append({
                "platform": "rss",
                "source_url": entry.get("link", keyword),
                "title": entry.get("title", ""),
                "summary": _strip_html(summary_html)[:2000],
                "published_at": entry.get("published", "") or entry.get("updated", ""),
                "author": author,
                "raw_html": summary_html,
            })
        print(f"[Scout] RSS fallback '{keyword}': {len(d.entries)} items")
    except Exception as e:
        print(f"[Scout] RSS fallback also failed '{keyword}': {e}")
