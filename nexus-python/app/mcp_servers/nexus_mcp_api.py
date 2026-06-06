import json
from typing import Any
from mcp.server.fastmcp import FastMCP
from api_news.news import get_info
from article import Article

server = FastMCP("api")

def build_article(item: dict) -> Article:
    """同步构建 Article，无 I/O 操作，直接返回"""
    return Article(
        title=item["title"],
        link=item["url"],
        summary=item["description"],
        published_at=item["published"]
    )

def parse_info(info: str) -> list[Article]:
    """同步解析 JSON 字符串，返回 Article 列表"""
    data = json.loads(info)         
    news_list = data["news"]
    return [build_article(item) for item in news_list]

@server.tool(
    "call_api",
    description="调用http请求获取新闻"
)
async def call_api() -> list[Article]:
    raw_data_list = await get_info()
    all_articles:list[Article] = []
    for info in raw_data_list:
        try:
            articles = parse_info(info)
        except Exception as e:
            print(f"Error processing API response: {e}")
            continue
        for article in articles:
            all_articles.append(article)
    return all_articles

if __name__ == "__main__":
    import asyncio
    articles = asyncio.run(call_api())
    for article in articles:
        print(f"Title: {article.title}, Link: {article.link}, Published At: {article.published_at}")