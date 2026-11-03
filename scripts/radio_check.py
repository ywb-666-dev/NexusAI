"""Real-model radio Q&A + private fixture, browser and speech-control acceptance.

No real notifications or collection; speech controls use a labelled browser stub only
when headless Chromium has no installed synthesis voices.
"""

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import httpx
from playwright.sync_api import sync_playwright
from sqlalchemy import select, func

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.core.dependencies import get_session_factory, close_db_engine
from app.models import Content, Subscription
from app.models.briefing import Briefing
from app.models.radio import RadioTurn


async def seed(uid):
    try:
        async with get_session_factory()() as db:
            sub = Subscription(
                user_id=uid,
                name="电台综合兴趣验收",
                status=0,
                rss_feeds=[
                    {
                        "url": "https://example.org/feed",
                        "platform": "rss",
                        "name": "公开测试来源",
                    }
                ],
            )
            db.add(sub)
            await db.flush()
            sources = []
            for key, title, body in [
                (
                    "film",
                    "周末电影节",
                    "电影节将于周六举行，现场安排导演交流活动。资料未提供地点、票价和余票信息。",
                ),
                (
                    "food",
                    "社区美食节",
                    "社区美食节提供不同地区的特色菜品，并设置文化交流环节。资料未说明是否需要预约。",
                ),
            ]:
                identifier = uuid.uuid4().hex
                sources.append(
                    {
                        "id": identifier,
                        "title": title,
                        "summary": body,
                        "body": body,
                        "url": "https://example.org/" + key,
                        "intent": "电影、文化和日常生活",
                        "reason": "合成验收资料",
                    }
                )
                db.add(
                    Content(
                        id=identifier,
                        subscription_id=sub.id,
                        source_platform="rss",
                        source_url=sources[-1]["url"],
                        title=title,
                        summary=body,
                        content_body=body,
                        status=1,
                        content_hash=hashlib.sha256(identifier.encode()).hexdigest(),
                    )
                )
            report = {
                "headline": "我的周末生活电台 · 验收节目",
                "overview": "了解电影文化与社区美食活动，出发前核实细节。",
                "sources": sources,
                "events": [
                    {
                        "title": s["title"],
                        "summary": s["summary"],
                        "attention": "建议查看原文并核实活动信息。",
                        "citations": [{"id": s["id"], "quote": s["summary"][:20]}],
                    }
                    for s in sources
                ],
            }
            bid = uuid.uuid4().hex
            db.add(
                Briefing(
                    id=bid,
                    user_id=uid,
                    status="ready",
                    hours=24,
                    period_start=datetime.utcnow(),
                    period_end=datetime.utcnow(),
                    report=report,
                )
            )
            await db.commit()
            return bid, sources
    finally:
        await close_db_engine()


def main():
    name, password = "radio_ui_" + uuid.uuid4().hex[:8], "NexusUI!2026"
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=110)

    def api(method, path, **kwargs):
        r = client.request(method, path, **kwargs)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["code"] == 200, data
        return data.get("data")

    def account(username):
        body = {"username": username, "password": password}
        api("POST", "/java/auth/register", json=body)
        return api("POST", "/java/auth/login", json=body)

    owner = account(name)
    foreign = account("radio_o_" + uuid.uuid4().hex[:8])
    client.headers["Authorization"] = "Bearer " + owner["token"]
    bid, sources = asyncio.run(seed(owner["user"]["id"]))
    path = f"/python/radio/{bid}/events/0"
    context = api("GET", path)
    assert (
        len(context["sources"]) == 1 and context["sources"][0]["id"] == sources[0]["id"]
    )
    assert (
        client.get(
            path, headers={"Authorization": "Bearer " + foreign["token"]}
        ).status_code
        == 404
    )
    assert (
        client.post(
            path + "/ask",
            headers={"Authorization": "Bearer " + foreign["token"]},
            json={"question": "你好"},
        ).status_code
        == 404
    )
    insufficient = api(
        "POST", path + "/ask", json={"question": "电影票具体多少钱？不要猜测。"}
    )
    assert insufficient["answer"]["insufficient"] is True
    time.sleep(3.1)
    simple = api("POST", path + "/ask", json={"question": "这件事讲简单一点"})
    assert simple["answer"]["citations"]
    assert len(api("GET", path)["turns"]) == 2
    api("PUT", path + "/preference", json={"dismissed": True})
    assert api("GET", path)["dismissed"] is True
    api("PUT", path + "/preference", json={"dismissed": False})
    followed = api("POST", path + "/follow")
    assert (
        api("POST", path + "/follow")["id"] == followed["id"]
        and followed["status"] == 0
    )
    subs = api("GET", "/java/subscriptions")["records"]
    draft = next(s for s in subs if s["id"] == followed["id"])
    assert (
        draft["status"] == 0
        and draft["rssFeeds"]
        and json.loads(draft["triggerConditions"])["semantic_filter"]["enabled"] is True
    )

    # Deliberately malformed provider output is isolated in-process, never changes real service config.
    async def failure_check():
        import app.core.dependencies as deps

        deps._async_session_factory = None
        from app.main import app
        from app.services import radio

        async def broken(*args, **kwargs):
            return '{"answer":"missing fields"}'

        try:
            async with get_session_factory()() as db:
                before = (
                    await db.execute(
                        select(func.count())
                        .select_from(RadioTurn)
                        .where(RadioTurn.briefing_id == bid)
                    )
                ).scalar()
            with patch.object(radio, "chat", broken):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://fixture",
                    headers={"Authorization": "Bearer " + owner["token"]},
                ) as c:
                    r = await c.post(
                        "/api" + path + "/ask", json={"question": "验证错误保护"}
                    )
                    assert r.status_code == 503, r.text
            async with get_session_factory()() as db:
                after = (
                    await db.execute(
                        select(func.count())
                        .select_from(RadioTurn)
                        .where(RadioTurn.briefing_id == bid)
                    )
                ).scalar()
                assert after == before
        finally:
            await close_db_engine()

    asyncio.run(failure_check())
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
        page.goto("http://127.0.0.1:5173/radio?id=" + bid, wait_until="networkidle")
        page.get_by_role("heading", name="听见你关心的世界").wait_for()
        page.wait_for_timeout(1500)
        native_voices = page.evaluate("window.speechSynthesis?.getVoices().length || 0")
        if not native_voices:
            page.evaluate(
                """() => {
              window.__speechTest = {played:0,paused:0,canceled:0};
              window.SpeechSynthesisUtterance = class { constructor(text) { this.text=text; } };
              const synth = window.speechSynthesis;
              Object.defineProperty(synth, 'getVoices', { value: () => [{name:'MOCK Chinese',voiceURI:'mock-zh',lang:'zh-CN',default:true}] });
              Object.defineProperty(synth, 'speak', { value: u => {window.__speechTest.played++; setTimeout(()=>u.onstart?.(),0);} });
              Object.defineProperty(synth, 'pause', { value: () => window.__speechTest.paused++ });
              Object.defineProperty(synth, 'resume', { value: () => {} });
              Object.defineProperty(synth, 'cancel', { value: () => window.__speechTest.canceled++ });
              synth.dispatchEvent(new Event('voiceschanged'));
            }"""
            )
        assert not errors, errors
        page.get_by_role("button", name=re.compile("开始收听")).click()
        page.get_by_role("button", name=re.compile("暂停收听")).wait_for()
        page.get_by_label("围绕当前事件追问").click()
        page.get_by_role("button", name=re.compile("继续收听")).wait_for()
        page.get_by_role("button", name="下一条", exact=True).click()
        page.get_by_role("heading", name="社区美食节", exact=True).wait_for()
        page.get_by_role("button", name="上一条", exact=True).click()
        page.get_by_role("heading", name="周末电影节", exact=True).wait_for()
        page.get_by_text("你问：这件事讲简单一点", exact=True).wait_for()
        page.screenshot(path=str(ROOT / ".runtime/radio-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        page.screenshot(path=str(ROOT / ".runtime/radio-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    result = {
        "result": "passed",
        "realModelGroundedAnswer": True,
        "realModelInsufficient": True,
        "history": True,
        "ownership": True,
        "pausedFollowIdempotent": True,
        "preference": True,
        "invalidModelNoWrite": True,
        "browser": True,
        "mobile390": True,
        "nativeVoiceCount": native_voices,
        "speechControlStub": not bool(native_voices),
    }
    (ROOT / ".runtime/radio-result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-model",
        required=True,
        action="store_true",
        help="Calls configured real model for two small synthetic Q&A cases.",
    )
    parser.parse_args()
    main()
