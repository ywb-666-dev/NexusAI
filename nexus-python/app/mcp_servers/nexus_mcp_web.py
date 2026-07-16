from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
from app.mcp_servers.article import Article
from bs4 import BeautifulSoup
server = FastMCP("web")
@server.tool("scrape_page", description="Playwright 渲染页面，返回 HTML 或截图")
async def scrape_page(
        url: str,
        wait_for_selector: str | None = None,
        actions: list[dict] | None = None,
        timeout: int = 30000,
) -> Article:
    
    playwright = None
    browser = None
    context = None

    try:
        # 1. 启动异步 Playwright（绝对不能在 async def 里用 sync_playwright）
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # 2. 导航到目标页，设置超时
        response = await page.goto(url, timeout=timeout, wait_until="networkidle")

        # 如果 HTTP 状态码异常，提前暴露
        if response and response.status >= 400:
            raise RuntimeError(f"页面返回错误状态码: {response.status}, URL: {url}")

        # 3. 等待指定元素出现（关键！现代网站内容靠 JS 异步加载）
        if wait_for_selector:
            await page.wait_for_selector(
                wait_for_selector,
                timeout=timeout // 2,  # 等待时间给一半，另一半留给 goto
                state="attached"
            )

        # 4. 执行自动化操作序列（翻页、点击、输入等）
        if actions:
            for idx, action in enumerate(actions):
                action_type = action.get("type")

                if action_type == "click":
                    selector = action.get("selector")
                    await page.click(selector)
                    # 点击后等一小会儿让页面反应
                    await page.wait_for_timeout(500)

                elif action_type == "scroll":
                    # 向下滚动指定像素，触发懒加载
                    amount = action.get("amount", 800)
                    await page.evaluate(f"window.scrollBy(0, {amount})")
                    await page.wait_for_timeout(800)

                elif action_type == "input":
                    # 在输入框填入内容（如搜索关键词）
                    selector = action.get("selector")
                    value = action.get("value", "")
                    await page.fill(selector, value)

                elif action_type == "press":
                    # 按键（如回车触发搜索）
                    key = action.get("key", "Enter")
                    await page.keyboard.press(key)
                    await page.wait_for_timeout(1000)

                elif action_type == "wait":
                    # 硬等待（毫秒）
                    ms = action.get("ms", 1000)
                    await page.wait_for_timeout(ms)

                elif action_type == "evaluate":
                    # 执行任意 JS 表达式
                    script = action.get("script")
                    await page.evaluate(script)

                else:
                    raise ValueError(f"未知的 action 类型: {action_type}，索引: {idx}")

        # 5. 再次等待页面稳定（操作后可能有二次加载）
        await page.wait_for_load_state("networkidle")

        # 6. 提取结果
        content = await page.content()
        soup = BeautifulSoup(content, 'lxml')  
        for tag in soup(['script', 'style']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        title = await page.title()
        final_url = page.url
        return Article(
            title=title,
            link=final_url,
            summary=text[:500]
        )

    except Exception as e:
        # 包装成统一异常，带上 URL 方便上层定位
        raise RuntimeError(f"页面采集失败 [{url}]: {e}") from e

    finally:
        # 7. 资源释放：无论成功失败，必须关闭浏览器，防止内存泄漏
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

if __name__ == "__main__":
    import asyncio
    test_url = "https://jwc.zuel.edu.cn/main.htm#:~:text=%E3%80%90%E6%95%99%E5%8A%A1%E4%B8%80%E6%9C%AC%E9%80%9A%E3%80%91%E7%8B%AC%E5%B1%9E%E4%BA%8E"
    result = asyncio.run(scrape_page(test_url))
    print(result)
@server.tool("search_rss_feeds", description="Search for RSS feeds by topic using DuckDuckGo HTML search (fast, no API key required)")
async def search_rss_feeds(
        topic: str,
        max_results: int = 15,
) -> list[dict]:
    """Search DuckDuckGo Lite for RSS feeds related to a topic."""
    import httpx
    from bs4 import BeautifulSoup

    results = []
    seen = set()

    queries = [f"{topic} RSS feed", f"{topic} site:reddit.com RSS"]
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for query in queries:
            if len(results) >= max_results:
                break
            try:
                resp = await client.get(
                    "https://lite.duckduckgo.com/lite/",
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for row in soup.find_all("tr"):
                    links = row.find_all("a", href=True)
                    snippet_el = row.find(class_="result-snippet")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    for link in links:
                        href = link.get("href", "")
                        title = link.get_text(strip=True)
                        if not href or not title or href in seen:
                            continue
                        is_feed = any(kw in href.lower() for kw in ["rss", "feed", "xml", "atom", "/feed/", "feedburner"])
                        is_title_match = any(kw in title.lower() for kw in ["rss", "feed"])
                        if not (is_feed or is_title_match):
                            continue
                        seen.add(href)
                        results.append({"url": href, "title": title[:200], "snippet": snippet[:300], "platform": "rss"})
                        if len(results) >= max_results:
                            break
            except Exception as e:
                print(f"[search_rss_feeds] {query}: {e}")
    return results
