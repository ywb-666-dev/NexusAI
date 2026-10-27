"""Real public-source and browser checks; isolated ordinary user, no model or robot calls."""

import json
import time
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=65)
    name, password = "cover_ui_" + uuid.uuid4().hex[:8], "NexusUI!2026"

    def api(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        body = response.json()
        assert body["code"] == 200, body
        return body.get("data")

    body = {"username": name, "password": password}
    api("POST", "/java/auth/register", json=body)
    client.headers["Authorization"] = (
        "Bearer " + api("POST", "/java/auth/login", json=body)["token"]
    )
    try:
        all_sources = api("GET", "/python/sources")
        assert (
            all_sources["stats"]["total"] == 348 and all_sources["stats"]["api"] == 43
        )
        apis = api("GET", "/python/sources", params={"platform": "api", "size": 100})
        assert apis["total"] == 43 and all(
            s["platform"] == "api" for s in apis["items"]
        )
        exported = client.get(
            "/python/sources/export.json", params={"platform": "api"}
        ).json()
        assert len(exported["sources"]) == 43
        opml = client.get("/python/sources/export.opml")
        outlines = ET.fromstring(opml.content).findall(".//outline")
        assert len(outlines) == 305 and all(
            "api.github.com" not in o.get("xmlUrl", "") for o in outlines
        )
        assert opml.headers["x-nexus-skipped-sources"] == "43"
        match = api(
            "POST",
            "/python/subscriptions/resolve-sources",
            json={"mode": "auto", "topic": "Ollama", "language": "all"},
        )
        assert match["feeds"] and match["feeds"][0]["platform"] == "api"
        discovered = api(
            "POST",
            "/python/sources/discover",
            json={"url": "https://www.zhangxinxu.com/wordpress/"},
        )
        assert any(
            s["health"]["status"] in ("available", "empty")
            for s in discovered["sources"]
        ), discovered
        assert api("GET", "/java/subscriptions")["total"] == 0
        assert api("GET", "/python/agent/tasks")["total"] == 0
        assert api("GET", "/java/notifications/unread-count") == 0
        assert (
            client.post(
                "/python/sources/discover", json={"url": "https://example.org"}
            ).status_code
            == 429
        )
        source_url = "https://api.github.com/repos/astral-sh/ruff/releases?per_page=2"
        payload = {
            "name": "来源扩展验收",
            "keywords": [],
            "rssFeeds": [
                {"url": source_url, "platform": "api", "name": "Ruff Releases"}
            ],
            "sourcePlatforms": ["api"],
            "priority": 2,
            "status": 0,
            "triggerConditions": json.dumps(
                {
                    "source_policy": {"mode": "manual"},
                    "semantic_filter": {"enabled": False},
                    "enable_ai": False,
                    "interval_minutes": 10080,
                }
            ),
        }
        api("POST", "/java/subscriptions", json=payload)
        sub = api("GET", "/java/subscriptions")["records"][0]
        assert sub["rssFeeds"][0]["platform"] == "api"
        sub["status"] = 1
        api("PUT", "/java/subscriptions/" + str(sub["id"]), json=sub)
        tid = api("POST", f"/java/subscriptions/{sub['id']}/trigger")["task_id"]
        for _ in range(100):
            task = api("GET", f"/python/agent/tasks/{tid}/status")
            if task["status"] in ("completed", "failed") or task["status"].startswith(
                "interrupted"
            ):
                break
            time.sleep(0.5)
        assert (
            task["status"] == "completed" and task["counts"]["stored_count"] > 0
        ), task
        contents = api("GET", "/python/contents")["items"]
        assert contents and all(
            c["sourcePlatform"] == "api"
            and c["sourceUrl"].startswith("https://github.com/astral-sh/ruff/releases/")
            for c in contents
        )
        sub["status"] = 0
        api("PUT", "/java/subscriptions/" + str(sub["id"]), json=sub)
        time.sleep(10)  # Explicit discovery cooldown; never send bursts to publishers.
        feed = api(
            "POST",
            "/python/sources/discover",
            json={"url": "https://daringfireball.net/feeds/json"},
        )
        assert (
            feed["sources"][0]["platform"] == "api"
            and feed["sources"][0]["health"]["status"] == "available"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("http://127.0.0.1:5173/login")
            page.get_by_placeholder("用户名").fill(name)
            page.get_by_placeholder("密码", exact=True).fill(password)
            page.get_by_role("button", name="进入工作台").click()
            page.wait_for_url("**/dashboard")
            page.goto("http://127.0.0.1:5173/sources", wait_until="networkidle")
            page.locator(
                '.ant-select[aria-label="来源类型"] .ant-select-selector'
            ).click()
            page.get_by_title("API / JSON Feed", exact=True).click()
            page.get_by_placeholder("名称、主题或域名").fill("Ruff")
            page.get_by_placeholder("名称、主题或域名").press("Enter")
            page.get_by_role("row").filter(has_text="Ruff Python").wait_for()
            with page.expect_download() as download:
                page.get_by_role("button", name="导出 JSON").click()
            assert download.value.suggested_filename.endswith(".json")
            page.get_by_role("button", name="从网站发现来源").click()
            modal = page.get_by_role("dialog")
            modal.get_by_label("待发现的网站地址").fill(
                "https://github.com/astral-sh/ruff"
            )
            time.sleep(10)
            with page.expect_response(
                lambda r: r.url.endswith("/python/sources/discover")
                and r.request.method == "POST"
            ) as response:
                modal.get_by_role("button", name="发现来源", exact=True).click()
            discovered_in_browser = response.value.json()
            use = modal.get_by_role("button", name="使用此来源创建或加入订阅")
            use.wait_for(timeout=50000)
            assert use.is_enabled(), discovered_in_browser
            page.screenshot(
                path=str(ROOT / ".runtime/source-discovery-desktop.png"), full_page=True
            )
            use.click()
            modal = page.get_by_role("dialog")
            modal.locator(".ant-select:has(#target) .ant-select-selector").click()
            page.get_by_title(sub["name"] + "（已暂停）", exact=True).click()
            modal.get_by_role("button", name="保存订阅").click()
            modal.wait_for(state="hidden")
            updated = api("GET", "/java/subscriptions")["records"][0]
            assert (
                updated["status"] == 0
                and len(updated["rssFeeds"]) == 2
                and all(f["platform"] == "api" for f in updated["rssFeeds"])
            )
            assert updated["triggerConditions"] == sub["triggerConditions"]
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(400)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            page.screenshot(
                path=str(ROOT / ".runtime/source-coverage-mobile.png"), full_page=True
            )
            assert not errors, errors
            browser.close()
        result = {
            "result": "passed",
            "catalog": 348,
            "apiSources": 43,
            "rssExport": 305,
            "websiteDiscovery": "passed",
            "jsonFeedDiscovery": "passed",
            "githubDiscovery": "passed",
            "readOnlyDiscovery": "passed",
            "autoApiType": "passed",
            "publishedReleases": len(contents),
            "browser": "passed",
            "mobile390": "passed",
        }
        (ROOT / ".runtime/source-coverage-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        for sub in api("GET", "/java/subscriptions")["records"]:
            sub["status"] = 0
            api("PUT", "/java/subscriptions/" + str(sub["id"]), json=sub)
        client.close()


if __name__ == "__main__":
    main()
