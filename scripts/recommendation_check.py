"""Isolated user feedback, ranking, briefing and real browser acceptance. No model/push."""

import asyncio
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.models import Content, Subscription
from app.core.dependencies import get_session_factory, close_db_engine


async def check():
    name, password = "rec_ui_" + uuid.uuid4().hex[:8], "NexusUI!2026"
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8080/api", timeout=30
    ) as client:

        async def account(username):
            body = {"username": username, "password": password}
            assert (await client.post("/java/auth/register", json=body)).json()[
                "code"
            ] == 200
            return (await client.post("/java/auth/login", json=body)).json()["data"]

        owner, outsider = await account(name), await account(
            "rec_o_" + uuid.uuid4().hex[:8]
        )
        client.headers["Authorization"] = "Bearer " + owner["token"]

        async def api(method, path, **kwargs):
            r = await client.request(method, path, **kwargs)
            assert r.status_code == 200, r.text
            return r.json()["data"]

        ids = {}
        try:
            async with get_session_factory()() as db:
                sub = Subscription(
                    user_id=owner["user"]["id"], name="推荐算法验收", status=0
                )
                private = Subscription(
                    user_id=outsider["user"]["id"], name="其他用户", status=0
                )
                db.add_all([sub, private])
                await db.flush()
                for key, title, text, status, semantic, subscription in [
                    (
                        "a",
                        "candidate landscape photography",
                        "Photography camera travel scenery landscape",
                        1,
                        True,
                        sub,
                    ),
                    (
                        "b",
                        "candidate offline inference",
                        "Offline open weight model laptop deployment quantization inference",
                        1,
                        True,
                        sub,
                    ),
                    (
                        "h",
                        "history offline inference",
                        "Offline open weight model laptop deployment quantization inference",
                        1,
                        True,
                        sub,
                    ),
                    ("legacy", "candidate legacy", "Legacy", 1, False, sub),
                    ("pending", "candidate pending", "Pending", 2, True, sub),
                    ("foreign", "candidate private", "Private", 1, True, private),
                ]:
                    key_id = uuid.uuid4().hex
                    ids[key] = key_id
                    db.add(
                        Content(
                            id=key_id,
                            subscription_id=subscription.id,
                            title=title,
                            summary=text * 4,
                            content_body=text * 4,
                            source_platform="rss",
                            source_url=f"https://{key}.example.com/article",
                            status=status,
                            is_duplicate=0,
                            content_hash=hashlib.sha256(key_id.encode()).hexdigest(),
                            fetched_at=datetime.utcnow() - timedelta(minutes=1),
                            relevance=(
                                {"recommended": True, "method": "llm", "score": 90}
                                if semantic
                                else None
                            ),
                            quality={"score": 90},
                        )
                    )
                await db.commit()
            path = "/python/contents"
            cold = await api(
                "GET", path, params={"sort": "personalized", "search": "candidate"}
            )
            assert {r["id"] for r in cold["items"]} == {ids["a"], ids["b"]}
            assert all(r["recommendation"]["coldStart"] for r in cold["items"])

            async def feedback(key, **body):
                return await api("PUT", f"{path}/{ids[key]}/feedback", json=body)

            await feedback("h", liked=True)
            ranked = await api(
                "GET", path, params={"sort": "personalized", "search": "candidate"}
            )
            assert ranked["items"][0]["id"] == ids["b"]
            await feedback("b", saved=True, dismissed=True)
            hidden = await api(
                "GET", path, params={"sort": "personalized", "search": "candidate"}
            )
            assert [r["id"] for r in hidden["items"]] == [ids["a"]]
            saved = await api("GET", path, params={"sort": "latest", "saved": True})
            assert len(saved["items"]) == 1 and saved["items"][0]["id"] == ids["b"]
            r = await client.put(
                f"{path}/{ids['foreign']}/feedback", json={"liked": True}
            )
            assert r.status_code == 404
            r = await client.put(
                f"{path}/{ids['pending']}/feedback", json={"liked": True}
            )
            assert r.status_code == 404
            r = await client.put(f"{path}/{ids['a']}/feedback", json={"liked": "true"})
            assert r.status_code == 422
            from app.services import briefing
            from app.models.briefing import Briefing
            from app.services.task_service import BACKGROUND_TASKS

            seen = []

            async def compose(sources):
                seen.extend(s["id"] for s in sources)
                return {
                    "headline": "MOCK 验收简报",
                    "overview": "仅验证推荐资料选择",
                    "events": [],
                    "omitted": [],
                }

            with patch.object(briefing, "compose", compose):
                bid = await briefing.create_briefing(owner["user"]["id"])
                while BACKGROUND_TASKS:
                    await asyncio.gather(*list(BACKGROUND_TASKS))
            assert (
                ids["b"] not in seen
                and ids["foreign"] not in seen
                and ids["pending"] not in seen
            )
            async with get_session_factory()() as db:
                assert (await db.get(Briefing, bid)).status == "ready"
            await feedback("b", dismissed=False, saved=False)
            await feedback("h", liked=False)
            reset = await api("GET", path, params={"sort": "personalized"})
            assert all(r["recommendation"]["coldStart"] for r in reset["items"])
            return name, password
        finally:
            await close_db_engine()


def main():
    name, password = asyncio.run(check())
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
        page.goto("http://127.0.0.1:5173/contents", wait_until="networkidle")
        page.locator(".article-card").filter(has_text="candidate offline").click()
        drawer = page.locator(".ant-drawer-content")
        drawer.get_by_role("button", name=re.compile(r"^收\s*藏$"), exact=True).click()
        drawer.get_by_role("button", name="取消收藏", exact=True).wait_for()
        drawer.get_by_role("button", name=re.compile(r"^喜\s*欢$"), exact=True).click()
        drawer.get_by_role("button", name="取消喜欢", exact=True).wait_for()
        page.screenshot(
            path=str(ROOT / ".runtime/recommendation-desktop.png"), full_page=True
        )
        drawer.get_by_role("button", name="不感兴趣", exact=True).click()
        drawer.get_by_role("button", name="撤销不感兴趣", exact=True).wait_for()
        drawer.get_by_role("button", name="撤销不感兴趣", exact=True).click()
        drawer.get_by_role("button", name="不感兴趣", exact=True).wait_for()
        page.locator(".ant-drawer-close").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        page.screenshot(
            path=str(ROOT / ".runtime/recommendation-mobile.png"), full_page=True
        )
        assert not errors, errors
        browser.close()
    result = {
        "result": "passed",
        "positiveRanking": True,
        "negativeFiltering": True,
        "savedFilter": True,
        "clearFeedback": True,
        "ownership": True,
        "semanticGate": True,
        "mockBriefingSelection": True,
        "browser": True,
        "mobile390": True,
    }
    (ROOT / ".runtime/recommendation-result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
