"""Real-stack regression for read-only trial, quality persistence and source health.

Run services with NEXUS_ALLOW_LOCAL_SOURCES=true only during this fixture test.
No privileged account or real robot is used. The created subscription is paused.
"""

import json
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BODY = (
    "这是一篇介绍 Python 开发实践的文章。内容包含环境配置、可维护代码、自动化验证及项目组织方法，帮助读者完成实际开发任务。"
    * 35
)
SUMMARY = (
    "This is a useful short summary of Python development practices and software testing. "
    * 3
)


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/broken":
            self.send_response(503)
            self.end_headers()
            return
        root = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/feed":
            entries = [
                ("Python Nexus 正文", "good", "简短导语"),
                ("Python Nexus 验证示例", "blocked", "Just a moment..."),
                ("Python Nexus 摘要", "summary", SUMMARY),
            ]
            text = (
                '<rss version="2.0"><channel><title>Fixture</title>'
                + "".join(
                    f"<item><title>{title}</title><link>{root}/{path}</link><description><![CDATA[<p>{body}</p>]]></description></item>"
                    for title, path, body in entries
                )
                + "</channel></rss>"
            )
            content_type = "application/xml"
        else:
            text = f'<html><title>Article</title><article>{BODY if self.path=="/good" else "Just a moment... checking your browser"}</article></html>'
            content_type = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())


def api(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    body = response.json()
    assert body["code"] == 200, body
    return body["data"]


def account():
    name = "quality_ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=60)
    api(
        client,
        "POST",
        "/java/auth/register",
        json={"username": name, "password": password},
    )
    token = api(
        client,
        "POST",
        "/java/auth/login",
        json={"username": name, "password": password},
    )["token"]
    client.headers["Authorization"] = "Bearer " + token
    return client, name, password


def main():
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{fixture.server_port}"
    owner, _, _ = account()
    subscription = None
    try:
        body = {
            "rss_feeds": [
                {"url": root + "/feed", "platform": "rss"},
                {"url": root + "/broken", "platform": "rss"},
            ],
            "keywords": ["python"],
        }
        result = api(owner, "POST", "/python/subscriptions/trial", json=body)
        assert result["collected_count"] == 3 and result["matched_count"] == 3
        assert result["readable_count"] == 2 and result["rejected_count"] == 1
        assert len(result["source_errors"]) == 1
        assert {i["quality"]["kind"] for i in result["items"]} == {"body", "summary"}
        assert api(owner, "GET", "/python/contents")["total"] == 0
        assert api(owner, "GET", "/python/agent/tasks")["total"] == 0
        assert api(owner, "GET", "/java/subscriptions")["total"] == 0
        assert api(owner, "GET", "/java/notifications/unread-count") == 0
        api(
            owner,
            "POST",
            "/java/subscriptions",
            json={
                "name": "质量验收_" + uuid.uuid4().hex[:8],
                "rssFeeds": [{"url": root + "/feed", "platform": "rss"}],
                "keywords": ["python"],
                "sourcePlatforms": ["rss"],
                "status": 1,
                "priority": 2,
                "matchMode": 1,
                "triggerConditions": json.dumps(
                    {"interval_minutes": 10080, "enable_ai": False}
                ),
            },
        )
        subscription = api(owner, "GET", "/java/subscriptions")["records"][0]
        task_id = api(
            owner, "POST", f"/java/subscriptions/{subscription['id']}/trigger"
        )["task_id"]
        for _ in range(80):
            task = api(owner, "GET", f"/python/agent/tasks/{task_id}/status")
            if task["status"] in {"completed", "failed"}:
                break
            time.sleep(0.5)
        assert task["status"] == "completed", task
        assert task["quality"]["rejected_count"] == 1
        content = api(owner, "GET", "/python/contents")
        assert content["total"] == 2
        assert all(i["quality"]["eligible"] for i in content["items"])
        assert {i["quality"]["kind"] for i in content["items"]} == {"body", "summary"}
        catalog = api(owner, "GET", "/python/sources", params={"q": "IT之家"})
        sid = catalog["items"][0]["id"]
        checked = api(owner, "POST", "/python/sources/check", json={"ids": [sid]})[
            "items"
        ][0]
        assert (
            checked["total_checks"] >= 1
            and checked["next_check_at"]
            and checked["history"]
        )
        browser_client, name, password = account()
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("http://127.0.0.1:5173/login")
            page.get_by_placeholder("用户名").fill(name)
            page.get_by_placeholder("密码", exact=True).fill(password)
            page.get_by_role("button", name="进入工作台").click()
            page.get_by_role("heading", name="让信息汇聚，让洞察发生").wait_for()
            page.goto("http://127.0.0.1:5173/subscriptions", wait_until="networkidle")
            page.get_by_role("button", name="新建订阅").click()
            modal = page.get_by_role("dialog")
            modal.get_by_role("radio", name="关键词筛选（兼容）", exact=True).check()
            modal.get_by_role("radio", name="手动配置", exact=True).check()
            modal.get_by_placeholder("https://example.com/feed.xml").fill(
                root + "/feed"
            )
            modal.get_by_role("button", name="试采预览", exact=True).click()
            drawer = page.locator(".ant-drawer-content")
            drawer.get_by_role("heading", name="匹配的候选内容").wait_for(timeout=60000)
            drawer.get_by_text("正文片段", exact=True).wait_for()
            drawer.get_by_text(
                "已拦截 1 条异常样本，正式采集使用相同规则", exact=True
            ).wait_for()
            page.screenshot(
                path=str(ROOT / ".runtime/trial-preview.png"), full_page=True
            )
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            drawer.locator(".ant-drawer-close").click()
            modal.get_by_role("button", name=re.compile(r"取\s*消")).click()
            page.goto("http://127.0.0.1:5173/sources", wait_until="networkidle")
            page.get_by_text("自动巡检已关闭", exact=False).wait_for()
            page.screenshot(
                path=str(ROOT / ".runtime/source-maintenance.png"), full_page=True
            )
            assert not errors, errors
            browser.close()
        assert api(browser_client, "GET", "/java/subscriptions")["total"] == 0
        assert api(browser_client, "GET", "/python/contents")["total"] == 0
        browser_client.close()
        (ROOT / ".runtime/quality-trial-result.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "trial_readable": 2,
                    "rejected": 1,
                    "task_id": task_id,
                    "page_errors": errors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: trial without database/push/AI effects, partial source failure, quality rejection/enrichment, real task persistence, health history, browser trial and mobile layout."
        )
    finally:
        if subscription:
            subscription["status"] = 0
            api(
                owner,
                "PUT",
                f"/java/subscriptions/{subscription['id']}",
                json=subscription,
            )
        fixture.shutdown()
        fixture.server_close()
        owner.close()


if __name__ == "__main__":
    main()
