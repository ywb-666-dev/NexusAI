from typing import Any
from .current_news import CurrentNews
from datetime import datetime,timedelta

async def get_current_news() -> Any:
    item = CurrentNews(
        country="cn",
        language="zh",
        keywords="technology",
        category=["technology", "science"],
        page_number=1,
        limit=10,
        start_date=(datetime.now()-timedelta(hours=2)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        has_image=True,
        has_description=True
    )
    try:
        res = item.get_info()   
        return res
    except Exception as e:
        print(f"Error getting current news: {e}")
        return None
    
async def get_hacker_news() -> Any:
    # TODO: 实际调用 Hacker News API
    return None

async def get_newsapi_news() -> Any:
    # TODO: 实际调用 NewsAPI
    return None

async def get_info() -> str:
    # 并发获取三个新闻源的数据（可选：用 asyncio.gather 并发执行）
    current = await get_current_news()
    hacker = await get_hacker_news()
    newsapi = await get_newsapi_news()
    result = []
    if current:
        result.append(current)
    if hacker:
        result.append(hacker)
    if newsapi:
        result.append(newsapi)
    return result