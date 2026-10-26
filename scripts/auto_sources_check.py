"""Verify automatic sources through Java, Python admission and Chromium without admin."""

import json
import re
import time
import uuid
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = "auto_ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=70)

    def api(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        body = response.json()
        assert body["code"] == 200, body
        return body["data"]

    api("POST", "/java/auth/register", json={"username": name, "password": password})
    client.headers["Authorization"] = (
        "Bearer "
        + api(
            "POST", "/java/auth/login", json={"username": name, "password": password}
        )["token"]
    )
    created = []
    try:
        invalid = client.post(
            "/java/subscriptions",
            json={
                "name": "empty_manual_" + name,
                "rssFeeds": [],
                "triggerConditions": json.dumps({"source_policy": {"mode": "manual"}}),
            },
        ).json()
        assert invalid["code"] == 4000 and invalid["message"], invalid
        unknown = client.post(
            "/java/subscriptions",
            json={
                "name": "unknown_" + name,
                "rssFeeds": [],
                "triggerConditions": json.dumps(
                    {
                        "source_policy": {
                            "mode": "auto",
                            "topic": "no_related_topic_" + uuid.uuid4().hex,
                        }
                    }
                ),
            },
        ).json()
        assert unknown["code"] == 4000 and "未找到" in unknown["message"], unknown
        policy = {
            "mode": "auto",
            "topic": "人工智能",
            "language": "zh_first",
            "excluded_ids": [],
        }
        payload = {
            "name": "自动来源接口验收_" + name,
            "rssFeeds": [],
            "keywords": ["no_matching_fixture_" + uuid.uuid4().hex],
            "priority": 2,
            "status": 0,
            "matchMode": 1,
            "triggerConditions": json.dumps(
                {"interval_minutes": 10080, "enable_ai": False, "source_policy": policy}
            ),
        }
        api("POST", "/java/subscriptions", json=payload)
        row = api("GET", "/java/subscriptions")["records"][0]
        created.append(row["id"])
        assert row["status"] == 0 and 1 <= len(row["rssFeeds"]) <= 5
        assert all(f["origin"] == "system" and f["sourceId"] for f in row["rssFeeds"])
        manual = {
            "url": row["rssFeeds"][0]["url"],
            "name": "用户指定名称",
            "platform": "rss",
            "origin": "manual",
        }
        row["rssFeeds"].append(manual)
        api("PUT", f"/java/subscriptions/{row['id']}", json=row)
        row = api("GET", f"/java/subscriptions/{row['id']}")
        assert len({f["url"] for f in row["rssFeeds"]}) == len(row["rssFeeds"])
        assert any(
            f["origin"] == "manual" and f["name"] == "用户指定名称"
            for f in row["rssFeeds"]
        )
        excluded = next(
            f["sourceId"] for f in row["rssFeeds"] if f["origin"] == "system"
        )
        conditions = json.loads(row["triggerConditions"])
        conditions["source_policy"]["excluded_ids"] = [excluded]
        row["triggerConditions"] = json.dumps(conditions)
        row["status"] = 1
        api("PUT", f"/java/subscriptions/{row['id']}", json=row)
        row = api("GET", f"/java/subscriptions/{row['id']}")
        assert excluded not in {f.get("sourceId") for f in row["rssFeeds"]}
        task_id = api("POST", f"/java/subscriptions/{row['id']}/trigger")["task_id"]
        for _ in range(100):
            task = api("GET", f"/python/agent/tasks/{task_id}/status")
            if task["status"].startswith("completed") or task["status"] == "failed":
                break
            time.sleep(0.6)
        assert task["status"].startswith("completed"), task
        assert (
            task["source_resolution"]["manual_count"] == 1
            and task["source_resolution"]["system_count"] >= 1
        )
        assert api("GET", "/python/contents")["total"] == 0
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
            assert modal.get_by_role(
                "radio", name="系统自动匹配（推荐）", exact=True
            ).is_checked()
            assert modal.get_by_placeholder("https://example.com/feed.xml").count() == 0
            modal.get_by_label("关注主题", exact=True).fill("少数派")
            modal.get_by_text("来源语言偏好", exact=True).click()
            modal.get_by_text("系统来源", exact=True).wait_for(timeout=45000)
            assert modal.get_by_label("订阅名称", exact=True).input_value() == "少数派"
            page.screenshot(
                path=str(ROOT / ".runtime/automatic-sources.png"), full_page=True
            )
            modal.get_by_role("button", name="试采预览", exact=True).click()
            drawer = page.locator(".ant-drawer-content")
            drawer.get_by_role("heading", name="来源读取结果").wait_for(timeout=65000)
            drawer.locator(".ant-drawer-close").click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            page.set_viewport_size({"width": 1440, "height": 1000})
            modal.get_by_role("button", name="保存订阅", exact=True).click()
            modal.wait_for(state="hidden", timeout=60000)
            saved = next(
                r
                for r in api("GET", "/java/subscriptions")["records"]
                if r["name"] == "少数派"
            )
            created.append(saved["id"])
            assert saved["rssFeeds"] and all(
                f["origin"] == "system" for f in saved["rssFeeds"]
            )
            record = page.get_by_role("row").filter(has_text="少数派")
            record.get_by_role("button", name=re.compile(r"编\s*辑")).click()
            modal.get_by_label("关注主题", exact=True).wait_for()
            assert modal.get_by_label("关注主题", exact=True).input_value() == "少数派"
            assert modal.get_by_placeholder("https://example.com/feed.xml").count() == 0
            assert not errors, errors
            browser.close()
        (ROOT / ".runtime/auto-sources-result.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "task_id": task_id,
                    "page_errors": errors,
                    "system_sources": task["source_resolution"]["system_count"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: create without feed URLs, source provenance, manual precedence, exclusions, task refresh, auto trial and browser save/edit/mobile."
        )
    finally:
        for sid in created:
            current = api("GET", f"/java/subscriptions/{sid}")
            current["status"] = 0
            api("PUT", f"/java/subscriptions/{sid}", json=current)
        client.close()


if __name__ == "__main__":
    main()
