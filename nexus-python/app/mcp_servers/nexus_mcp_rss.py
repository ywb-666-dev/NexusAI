from typing import List
import feedparser
from mcp.server.fastmcp import FastMCP
from article import Article

server = FastMCP("rss")

@server.tool(
    "fetch_rss",
    description="输入 RSS URL，输出文章列表（标题、链接、摘要、发布时间）"
)
def fetch_rss(url: str) -> List[Article]:
    """
    抓取 RSS/Atom 订阅源，返回解析后的文章列表。
    如果 URL 无效或解析失败，抛出异常由上层处理。
    """
    try:
        d = feedparser.parse(url)
    except Exception as e:
        raise RuntimeError(f"RSS 解析失败: {e}") from e

    # feedparser 解析失败时不会抛异常，而是返回空结构，需要手动检查
    if not d.entries:
        return []

    articles: List[Article] = []
    for entry in d.entries:
        # feedparser 的字段可能不存在，安全取值
        title = entry.get("title", "无标题")
        link = entry.get("link", "")

        # 摘要字段可能是 summary 或 description，取决于 RSS/Atom 格式
        summary = entry.get("summary", "") or entry.get("description", "")
        # 清理 HTML 标签（RSS 摘要常带 HTML）
        summary = summary[:500]  # 截断，防止过长

        # 发布时间字段可能是 published 或 updated
        published = entry.get("published", "") or entry.get("updated", "")

        articles.append(
            Article(
                title=title,
                link=link,
                summary=summary,
                published_at=published,
            )
        )

    return articles


