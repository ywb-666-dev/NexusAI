"""Verify source discovery, real previews, OPML and subscription handoff in Chromium."""

import json
import re
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = "source_ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=30)
    assert (
        client.post(
            "/java/auth/register", json={"username": name, "password": password}
        ).json()["code"]
        == 200
    )
    token = client.post(
        "/java/auth/login", json={"username": name, "password": password}
    ).json()["data"]["token"]
    client.headers["Authorization"] = "Bearer " + token
    assert client.get("/python/sources").json()["data"]["stats"]["total"] >= 200
    assert httpx.get("http://127.0.0.1:8080/api/python/sources").status_code == 401
    assert (
        client.post("/python/sources/check", json={"ids": ["unknown"]}).status_code
        == 400
    )
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
        page.goto("http://127.0.0.1:5173/sources", wait_until="networkidle")
        page.get_by_role("heading", name="构建你的信息版图").wait_for()
        search = page.get_by_placeholder("名称、主题或域名")
        for source_name in ["少数派", "IT之家"]:
            search.fill(source_name)
            search.press("Enter")
            row = page.get_by_role("row").filter(has_text=source_name)
            row.get_by_role("checkbox").check()
        page.get_by_role("button", name="加入订阅").click()
        modal = page.get_by_role("dialog")
        sub_name = "数据源验收_" + name
        modal.get_by_placeholder("例如：AI 与科技动态").fill(sub_name)
        modal.get_by_role("button", name="保存订阅").click()
        modal.wait_for(state="hidden")
        subscriptions = client.get("/java/subscriptions").json()["data"]["records"]
        sub = next(s for s in subscriptions if s["name"] == sub_name)
        assert len(sub["rssFeeds"]) == 2
        # Existing subscription handoff must preserve its options and deduplicate URLs.
        row = page.get_by_role("row").filter(has_text="IT之家")
        row.get_by_role("checkbox").check()
        page.get_by_role("button", name="加入订阅").click()
        modal.locator(".ant-select-selector").click()
        page.get_by_title(sub_name, exact=True).click()
        modal.get_by_role("button", name="保存订阅").click()
        modal.wait_for(state="hidden")
        updated = next(
            s
            for s in client.get("/java/subscriptions").json()["data"]["records"]
            if s["id"] == sub["id"]
        )
        assert (
            len(updated["rssFeeds"]) == 2
            and updated["triggerConditions"] == sub["triggerConditions"]
        )
        row.get_by_role("button", name="预览与检测").click()
        drawer = page.locator(".ant-drawer-content")
        drawer.get_by_role("button", name="检测此来源").click()
        drawer.get_by_role("link").first.wait_for(timeout=120000)
        drawer.locator(".ant-drawer-close").click()
        with page.expect_download() as download:
            page.get_by_role("button", name="导出 OPML").click()
        path = ROOT / ".runtime/source-export.opml"
        download.value.save_as(path)
        assert len(ET.parse(path).findall(".//outline")) == 1
        search.fill("")
        search.press("Enter")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(ROOT / ".runtime/sources.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        page.screenshot(path=str(ROOT / ".runtime/sources-mobile.png"), full_page=True)
        assert not errors, errors
        # Leave this test's real-source subscription paused after verification.
        updated["status"] = 0
        assert (
            client.put("/java/subscriptions/" + str(sub["id"]), json=updated).json()[
                "code"
            ]
            == 200
        )
        browser.close()
    (ROOT / ".runtime/sources-browser-result.json").write_text(
        json.dumps(
            {"result": "passed", "page_errors": errors, "selected_sources": 2}, indent=2
        ),
        encoding="utf-8",
    )
    print(
        "PASS: catalog auth/search, cross-page selection, new/existing subscription merge, feed preview/check, OPML and mobile layout."
    )


if __name__ == "__main__":
    main()
