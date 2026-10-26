"""Exercise the running stack using a local RSS/webhook fixture, never a real group.

Start application services with NEXUS_ALLOW_LOCAL_SOURCES=true only for this test.
All data is scoped to uniquely named e2e accounts. No existing rows are removed.
"""

import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.core.config import settings
import pymysql

RECEIVED = []
RECEIVED_QUERIES = []
FAIL_HOOK = True
BODY = (
    "这是一段用于验证正文解析的公开测试内容。订阅系统需要可靠采集内容，保留来源、作者和时间，支持去重、审批与通知。"
    * 3
)


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/broken"):
            self.send_response(503)
            self.end_headers()
            return
        if self.path.startswith("/article"):
            body = f"<html><title>测试正文</title><article><p>{BODY}</p><script>bad()</script></article></html>"
        else:
            time.sleep(0.6)
            risky = self.path.startswith("/risk")
            titles = (
                ["CVE-2099-0001 风险测试"]
                if risky
                else ["NexusAI 内容采集验证", "NexusAI 正文解析验证"]
            )
            entries = "".join(
                f'<item><title>{title}</title><link>http://127.0.0.1:{self.server.server_port}/article/{"risk" if risky else "normal"}/{i}</link><description><![CDATA[<p>{BODY}</p>]]></description><author>测试作者</author><pubDate>Sun, 25 Oct 2026 12:00:00 +0800</pubDate></item>'
                for i, title in enumerate(titles)
            )
            body = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>验证源</title>{entries}</channel></rss>'
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_POST(self):
        from urllib.parse import urlparse, parse_qs

        RECEIVED_QUERIES.append(parse_qs(urlparse(self.path).query))
        RECEIVED.append(
            json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {
            "code": 123 if self.path.startswith("/hook-failure") and FAIL_HOOK else 0,
            "msg": "mock response",
        }
        self.wfile.write(json.dumps(payload).encode())


def api(client, method, path, **kwargs):
    response = client.request(method, "http://127.0.0.1:8080/api" + path, **kwargs)
    response.raise_for_status()
    result = response.json()
    assert result.get("code") == 200, (path, result)
    return result.get("data")


def account(client, name):
    api(
        client,
        "POST",
        "/java/auth/register",
        json={
            "username": name,
            "password": "NexusE2E!2026",
            "email": name + "@example.com",
        },
    )
    result = api(
        client,
        "POST",
        "/java/auth/login",
        json={"username": name, "password": "NexusE2E!2026"},
    )
    client.headers["Authorization"] = "Bearer " + result["token"]
    return result


def wait_task(client, task_id):
    for _ in range(180):
        task = api(client, "GET", f"/python/agent/tasks/{task_id}/status")
        if task["status"] not in [
            "queued",
            "fetching",
            "parsing",
            "storing",
            "deciding",
            "curating",
        ]:
            return task
        time.sleep(0.25)
    raise AssertionError("Task timed out")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    fixture = f"http://127.0.0.1:{server.server_port}"
    prefix = "e2e_" + uuid.uuid4().hex[:7]
    with httpx.Client(timeout=25) as owner, httpx.Client(
        timeout=25
    ) as stranger, httpx.Client(timeout=25) as admin:
        owner_info = account(owner, prefix + "a")
        account(stranger, prefix + "b")
        admin_user = os.getenv("E2E_ADMIN_USER")
        admin_password = os.getenv("E2E_ADMIN_PASSWORD")
        if not admin_user or not admin_password:
            raise RuntimeError(
                "Set E2E_ADMIN_USER and E2E_ADMIN_PASSWORD to an authorized test reviewer account."
            )
        admin_info = api(
            admin,
            "POST",
            "/java/auth/login",
            json={"username": admin_user, "password": admin_password},
        )
        admin.headers["Authorization"] = "Bearer " + admin_info["token"]
        api(
            owner,
            "POST",
            "/python/push/channels",
            json={
                "name": "本地模拟飞书",
                "provider": "feishu",
                "webhook": fixture + "/hook",
                "secret": "fixture-secret",
            },
        )

        api(
            owner,
            "POST",
            "/python/push/channels",
            json={
                "name": "本地模拟钉钉",
                "provider": "dingtalk",
                "webhook": fixture + "/hook?access_token=fixture-token",
                "secret": "fixture-secret",
            },
        )

        def subscription(name, path):
            payload = {
                "name": prefix + name,
                "keywords": [],
                "sourcePlatforms": ["rss"],
                "rssFeeds": [
                    {"url": fixture + path, "name": "fixture", "platform": "rss"}
                ],
                "matchMode": 1,
                "priority": 2,
                "triggerConditions": json.dumps(
                    {"interval_minutes": 10080, "enable_ai": False}
                ),
            }
            api(owner, "POST", "/java/subscriptions", json=payload)
            rows = api(owner, "GET", "/java/subscriptions")["records"]
            sub = next(r for r in rows if r["name"] == payload["name"])
            assert sub["rssFeeds"][0]["url"] == fixture + path
            return sub

        normal = subscription("normal", "/feed")
        first = api(
            owner,
            "POST",
            f"/java/subscriptions/{normal['id']}/trigger",
        )["task_id"]
        second = api(
            owner,
            "POST",
            f"/java/subscriptions/{normal['id']}/trigger",
        )["task_id"]
        assert first == second, "Concurrent requests must reuse the active task"
        task = wait_task(owner, first)
        assert task["status"] == "completed", task
        assert task["counts"]["stored_count"] == 2, task
        feed = api(owner, "GET", "/python/contents")
        assert feed["total"] == 2
        assert "<script>" not in feed["items"][0]["contentBody"]
        assert api(stranger, "GET", "/python/contents")["total"] == 0
        denied = stranger.get(
            f"http://127.0.0.1:8080/api/python/agent/tasks/{first}/status"
        )
        assert denied.status_code == 404
        other = api(stranger, "GET", "/java/contents")
        assert other["total"] == 0
        assert api(owner, "GET", "/java/notifications/unread-count") >= 1
        assert any(item.get("msg_type") == "text" for item in RECEIVED)
        assert any(item.get("msgtype") == "text" for item in RECEIVED)
        assert any(
            q.get("access_token") == ["fixture-token"] and "sign" in q
            for q in RECEIVED_QUERIES
        )
        assert api(owner, "GET", "/python/push/deliveries")[0]["status"] == "sent"
        repeat = api(
            owner,
            "POST",
            f"/java/subscriptions/{normal['id']}/trigger",
        )["task_id"]
        task = wait_task(owner, repeat)
        assert (
            task["counts"]["stored_count"] == 0
            and task["counts"]["duplicate_count"] == 2
        ), task
        failing_channel = api(
            owner,
            "POST",
            "/python/push/channels",
            json={
                "name": "失败重试验证",
                "provider": "feishu",
                "webhook": fixture + "/hook-failure",
                "secret": "fixture-secret",
            },
        )
        risk = subscription("risk", "/risk")
        task_id = api(
            owner, "POST", "/python/agent/tasks", params={"subscription_id": risk["id"]}
        )["task_id"]
        task = wait_task(owner, task_id)
        assert task["status"] == "interrupted: awaiting approval", task
        assert (
            api(owner, "GET", "/python/contents")["total"] == 2
        ), "Pending content leaked"
        tickets = api(admin, "GET", "/java/approvals/pending")["records"]
        ticket = next(t for t in tickets if t["taskId"] == task_id)
        api(
            admin,
            "POST",
            f"/java/approvals/{ticket['id']}/approve",
            json={"comment": "本地端到端验证通过"},
        )
        assert wait_task(owner, task_id)["status"] == "completed"
        assert api(owner, "GET", "/python/contents")["total"] == 3
        failed_delivery = next(
            d
            for d in api(owner, "GET", "/python/push/deliveries")
            if d["channel_id"] == failing_channel["id"]
        )
        assert (
            failed_delivery["status"] == "failed" and failed_delivery["attempts"] == 3
        )
        global FAIL_HOOK
        FAIL_HOOK = False
        retried = api(
            owner, "POST", f"/python/push/deliveries/{failed_delivery['id']}/retry"
        )
        assert retried["status"] == "sent"
        reject_sub = subscription("reject", "/risk-reject")
        rejected_id = api(
            owner, "POST", f"/java/subscriptions/{reject_sub['id']}/trigger"
        )["task_id"]
        assert (
            wait_task(owner, rejected_id)["status"] == "interrupted: awaiting approval"
        )
        ticket = next(
            t
            for t in api(admin, "GET", "/java/approvals/pending")["records"]
            if t["taskId"] == rejected_id
        )
        api(
            admin,
            "POST",
            f"/java/approvals/{ticket['id']}/reject",
            json={"comment": "端到端拒绝流程验证"},
        )
        assert wait_task(owner, rejected_id)["status"] == "rejected"
        assert api(owner, "GET", "/python/contents")["total"] == 3
        broken = subscription("broken", "/broken")
        failed = api(
            owner,
            "POST",
            "/python/agent/tasks",
            params={"subscription_id": broken["id"]},
        )["task_id"]
        task = wait_task(owner, failed)
        assert task["status"].startswith("error") or task["status"] == "failed", task
        assert task["error"]
        print(
            "PASS: auth, source persistence, active-task admission, collection, parsing, dedup, tenant isolation, notification, signed mock delivery, approval resume, source failure"
        )
        (ROOT / ".runtime/e2e-result.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "owner": prefix + "a",
                    "reviewer": admin_user,
                    "task_id": first,
                    "approval_task_id": task_id,
                    "mock_deliveries": len(RECEIVED),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    server.shutdown()


if __name__ == "__main__":
    main()
