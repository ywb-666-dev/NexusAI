"""Exercise the real frontend without creating privileged users or sending messages."""

import json
import re
import uuid
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = "ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    response = httpx.post(
        "http://127.0.0.1:8080/api/java/auth/register",
        json={"username": name, "password": password},
        timeout=20,
    )
    assert response.json()["code"] == 200
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, timezone_id="Asia/Shanghai"
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        page.get_by_placeholder("用户名").fill(name)
        page.get_by_placeholder("密码", exact=True).fill(password)
        page.get_by_role("button", name="进入工作台").click()
        page.get_by_role("heading", name="让信息汇聚，让洞察发生").wait_for()
        page.locator(".ant-empty-description").filter(has_text="暂无数据").first.wait_for()
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(ROOT / ".runtime/dashboard.png"), full_page=True)
        for route, title in [
            ("contents", "你的内容中心"),
            ("tasks", "每一步都有迹可循"),
            ("notifications", "最新动态，不再错过"),
            ("push", "让重要内容主动抵达"),
            ("subscriptions", "建立你的信息雷达"),
        ]:
            page.goto("http://127.0.0.1:5173/" + route, wait_until="networkidle")
            page.get_by_role("heading", name=title).wait_for()
        page.get_by_role("button", name="新建订阅").click()
        modal = page.get_by_role("dialog")
        modal.get_by_placeholder("https://example.com/feed.xml").wait_for()
        assert modal.get_by_role("spinbutton").input_value() == "60"
        subscription_name = "浏览器验收_" + name
        modal.get_by_label("订阅名称").fill(subscription_name)
        modal.get_by_placeholder("https://example.com/feed.xml").fill(
            "https://hnrss.org/newest?count=3"
        )
        page.screenshot(
            path=str(ROOT / ".runtime/subscription-modal.png"), full_page=True
        )
        with page.expect_response(
            lambda r: "/api/java/subscriptions" in r.url and r.request.method == "POST"
        ) as saved:
            modal.get_by_role("button", name="保存订阅").click()
        assert saved.value.json()["code"] == 200
        modal.wait_for(state="hidden")
        row = page.get_by_role("row").filter(has_text=subscription_name)
        row.wait_for()
        row.get_by_role("button", name=re.compile(r"编\s*辑")).click()
        modal = page.get_by_role("dialog")
        assert (
            modal.get_by_placeholder("https://example.com/feed.xml").input_value()
            == "https://hnrss.org/newest?count=3"
        )
        modal.get_by_role("button", name=re.compile(r"取\s*消")).click()
        modal.wait_for(state="hidden")
        row.get_by_role("button", name=re.compile(r"暂\s*停")).click()
        row.get_by_role("button", name=re.compile(r"启\s*用")).wait_for()
        assert row.get_by_role("button", name=re.compile(r"采\s*集")).is_disabled()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.screenshot(path=str(ROOT / ".runtime/mobile.png"), full_page=True)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), "Mobile viewport overflows"
        page.get_by_role("button", name="切换主题").click()
        assert page.locator(".nexus-shell.light").count() == 1
        assert not errors, errors
        (ROOT / ".runtime/browser-result.json").write_text(
            json.dumps(
                {"result": "passed", "username": name, "page_errors": errors},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: browser login, all pages, subscription defaults/save/edit, pause, theme and mobile layout; no runtime page errors."
        )
        browser.close()


if __name__ == "__main__":
    main()
