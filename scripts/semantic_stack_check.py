"""Full-stack semantic regression with a local, explicitly mocked model provider.

Actual semantic quality is evaluated separately by semantic_eval.py --real-model.
This script checks persistence, fail-closed behavior, UI and no side effects in trials.
It restores the normal application configuration before exiting.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "nexus-python/tests/fixtures/semantic_cases.json").read_text(
        encoding="utf-8"
    )
)
CASES = {case["id"]: case for case in FIXTURE["cases"]}
BY_TITLE = {case["title"]: case for case in FIXTURE["cases"]}
FAIL_JUDGMENT = False
MODEL_CALLS = 0
PLAN = {
    "summary": "关注个人电脑离线开放权重模型的实操与测试，排除宣传、融资和云服务",
    "include": ["个人设备离线运行", "开放权重", "操作教程或性能测试"],
    "exclude": ["融资广告", "云端依赖", "缺少实际操作"],
    "source_queries": ["人工智能", "开源"],
    "categories": ["ai", "dev"],
}


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, text, kind="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())

    def do_GET(self):
        root = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/feed":
            entries = "".join(
                f'<item><title>{case["title"]}</title><link>{root}/article/{case["id"]}</link><description><![CDATA[<p>{case["body"]}</p>]]></description></item>'
                for case in CASES.values()
            )
            self.send(
                f'<rss version="2.0"><channel><title>Semantic fixture</title>{entries}</channel></rss>',
                "application/xml",
            )
        else:
            case = CASES[self.path.rsplit("/", 1)[-1]]
            self.send(
                f'<html><title>{case["title"]}</title><article>{case["body"]*4}</article></html>',
                "text/html",
            )

    def do_POST(self):
        global MODEL_CALLS
        MODEL_CALLS += 1
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        data = json.loads(body["messages"][-1]["content"].rsplit("\n", 1)[1])
        if "untrusted_articles" not in data:
            content = json.dumps(PLAN, ensure_ascii=False)
        elif FAIL_JUDGMENT:
            content = "{invalid JSON"
        else:
            rows = []
            for article in data["untrusted_articles"]:
                case = BY_TITLE[article["title"]]
                rows.append(
                    {
                        "id": article["id"],
                        "score": (
                            95
                            if case["id"] == "offline_zh_synonym"
                            else 90 if case["expected"] else 10
                        ),
                        "matches": case["expected"],
                        "excluded": not case["expected"],
                        "reason": (
                            "符合离线个人设备实操需求"
                            if case["expected"]
                            else "不符合订阅限制或命中排除条件"
                        ),
                        "evidence": [(article["body"] or article["summary"])[:80]],
                    }
                )
            content = json.dumps({"items": rows}, ensure_ascii=False)
        self.send(
            json.dumps(
                {
                    "id": "fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "semantic-fixture",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )
        )


def dev(action, env):
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/dev.py"), action],
        cwd=ROOT,
        env=env,
        check=True,
    )


def check(root):
    global FAIL_JUDGMENT
    name = "semantic_ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=210)

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
    policy = FIXTURE["policy"]
    trial_body = {
        "rss_feeds": [{"url": root + "/feed", "platform": "rss"}],
        "source_policy": {"mode": "manual"},
        "keywords": ["a_word_that_does_not_exist"],
        "semantic_policy": policy,
    }
    started = time.monotonic()
    trial = api("POST", "/python/subscriptions/trial", json=trial_body)
    assert (
        trial["semantic"]["accepted_count"] == 2
        and trial["semantic"]["rejected_count"] == 6
    )
    assert (
        api("GET", "/python/contents")["total"] == 0
        and api("GET", "/python/agent/tasks")["total"] == 0
    )
    assert (
        api("GET", "/java/notifications/unread-count") == 0
        and api("GET", "/java/subscriptions")["total"] == 0
    )
    subs = []

    def create(title, sem):
        api(
            "POST",
            "/java/subscriptions",
            json={
                "name": title,
                "rssFeeds": [{"url": root + "/feed", "platform": "rss"}],
                "keywords": ["a_word_that_does_not_exist"],
                "priority": 2,
                "status": 0,
                "triggerConditions": json.dumps(
                    {
                        "interval_minutes": 10080,
                        "enable_ai": False,
                        "source_policy": {"mode": "manual"},
                        "semantic_filter": sem,
                    }
                ),
            },
        )
        row = next(
            r
            for r in api("GET", "/java/subscriptions")["records"]
            if r["name"] == title
        )
        subs.append(row["id"])
        row["status"] = 1
        api("PUT", f"/java/subscriptions/{row['id']}", json=row)
        return row

    def run_task(sub):
        tid = api("POST", f"/java/subscriptions/{sub['id']}/trigger")["task_id"]
        for _ in range(100):
            task = api("GET", f"/python/agent/tasks/{tid}/status")
            if task["status"] in {"completed", "failed"}:
                return task
            time.sleep(0.3)
        raise AssertionError("task timeout")

    try:
        good = create("Semantic good " + name, policy)
        task = run_task(good)
        assert (
            task["status"] == "completed" and task["semantic"]["accepted_count"] == 2
        ), task
        content = api("GET", "/python/contents", params={"sort": "relevance"})
        assert content["total"] == 2 and [
            r["relevance"]["score"] for r in content["items"]
        ] == [95, 90]
        assert all(
            r["relevance"]["method"] == "llm" and r["relevance"]["evidence"]
            for r in content["items"]
        )
        notifications = api("GET", "/java/notifications/unread-count")
        bad = create("Semantic failure " + name, {**policy, "threshold": 85})
        FAIL_JUDGMENT = True
        failed = run_task(bad)
        assert failed["status"] == "failed" and "JSON" in failed["error"], failed
        assert (
            api("GET", "/python/contents", params={"subscription_id": bad["id"]})[
                "total"
            ]
            == 0
        )
        assert api("GET", "/java/notifications/unread-count") == notifications
        FAIL_JUDGMENT = False
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
            assert modal.get_by_role(
                "radio", name="语义订阅（推荐）", exact=True
            ).is_checked()
            modal.get_by_role("radio", name="手动配置", exact=True).check()
            modal.get_by_label("订阅需求", exact=True).fill(policy["intent"])
            modal.get_by_label("不想看到的内容（可选）", exact=True).fill(
                policy["exclusions"]
            )
            modal.get_by_placeholder("https://example.com/feed.xml").fill(
                root + "/feed"
            )
            time.sleep(max(0, 10.2 - (time.monotonic() - started)))
            modal.get_by_role("button", name="试采预览", exact=True).click()
            drawer = page.locator(".ant-drawer-content")
            drawer.get_by_text("未推荐的内容及语义判断理由", exact=True).wait_for(
                timeout=180000
            )
            drawer.get_by_text("推荐理由 · 语义相关度 95/100", exact=True).wait_for()
            page.screenshot(
                path=str(ROOT / ".runtime/semantic-trial.png"), full_page=True
            )
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            drawer.locator(".ant-drawer-close").click()
            modal.get_by_role("button", name=re.compile(r"取\s*消")).click()
            page.goto("http://127.0.0.1:5173/contents", wait_until="networkidle")
            page.locator(".article-card").first.click()
            page.get_by_text("推荐理由 · 语义相关度 95/100", exact=True).wait_for()
            assert not errors, errors
            browser.close()
        output = {
            "result": "passed",
            "model_provider": "local fixture mock",
            "trial_recommended": 2,
            "rejected": 6,
            "failure_closed": True,
            "task_id": task["task_id"],
            "page_errors": errors,
            "mock_model_calls": MODEL_CALLS,
        }
        (ROOT / ".runtime/semantic-stack-result.json").write_text(
            json.dumps(output, indent=2), encoding="utf-8"
        )
        print(
            "PASS: semantic trial, no keyword gate, 2 published / 6 rejected, persisted reasons and evidence, ranking, malformed-model fail-closed, browser and mobile."
        )
    finally:
        FAIL_JUDGMENT = False
        for sid in subs:
            row = api("GET", f"/java/subscriptions/{sid}")
            row["status"] = 0
            api("PUT", f"/java/subscriptions/{sid}", json=row)
        client.close()


def main():
    normal = {
        **os.environ,
        "NEXUS_ALLOW_LOCAL_SOURCES": "false",
        "SOURCE_HEALTH_ENABLED": "true",
    }
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{fixture.server_port}"
    test = {
        **normal,
        "NEXUS_ALLOW_LOCAL_SOURCES": "true",
        "SOURCE_HEALTH_ENABLED": "false",
        "LLM_BASE_URL": root + "/v1",
        "LLM_API_KEY": "fixture-key",
    }
    try:
        dev("stop", normal)
        dev("start", test)
        check(root)
    finally:
        dev("stop", normal)
        fixture.shutdown()
        fixture.server_close()
        dev("start", normal)


if __name__ == "__main__":
    main()
