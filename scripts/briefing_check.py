"""Real-model brief + full-stack browser checks. Uses isolated ordinary fixture users.

Never sends to real robots. Delivery tests patch the network sender in-process.
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
from playwright.sync_api import sync_playwright
from sqlalchemy import select, delete, func

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.core.dependencies import get_session_factory
from app.models import Content, Subscription, Notification
from app.models.briefing import Briefing
from app.models.delivery import PushChannel, PushDelivery
from app.services import briefing
from app.services.task_service import BACKGROUND_TASKS


def account(client, name, password):
    body = {"username": name, "password": password}
    response = client.post("/java/auth/register", json=body).json()
    assert response["code"] == 200, response
    data = client.post("/java/auth/login", json=body).json()["data"]
    client.headers["Authorization"] = "Bearer " + data["token"]
    return data


async def seed(user_id, foreign_id):
    async with get_session_factory()() as db:
        subs = [
            Subscription(user_id=user_id, name="模型部署验收", status=0),
            Subscription(user_id=user_id, name="开发安全验收", status=0),
            Subscription(user_id=foreign_id, name="其他用户私密", status=0),
        ]
        db.add_all(subs)
        await db.flush()
        fixtures = [
            (
                0,
                "Orion Runner 0.8 离线部署实测",
                "Orion Runner 0.8 是本验收的虚构模型工具。它提供开放权重助手的本地离线安装教程，测试在16GB内存电脑上运行，每秒14个token。请核实个人机器条件再尝试。",
                "a",
                True,
                1,
                0,
            ),
            (
                1,
                "另一份 Orion Runner 0.8 测试记录",
                "本验收虚构项目 Orion Runner 0.8 的另一份独立测试，记录离线安装步骤、量化配置和16GB内存电脑上的运行效果，每秒13个token。与另一来源的14个token有差异，需要核实测试条件。",
                "b",
                True,
                1,
                0,
            ),
            (
                1,
                "虚构工具 DevDesk 的安全公告",
                "本验收虚构开发工具 DevDesk 修复认证绕过问题，维护者建议将1.4版升级到1.4.1。文章列出受影响配置和升级后的检查步骤。本文没有说明 Orion Runner 项目的安全状况。",
                "c",
                True,
                1,
                0,
            ),
            (
                1,
                "重复地址的部署记录",
                "这一条与第一篇地址相同，应该精确去重。",
                "a",
                True,
                1,
                0,
            ),
            (0, "未通过语义筛选", "不应出现在简报中。", "rejected", False, 1, 0),
            (0, "仍在等待审批", "不应出现在简报中。", "pending", True, 2, 0),
            (0, "范围外的旧内容", "不应出现在24小时简报中。", "old", True, 1, 3),
            (
                2,
                "其他用户私密文章",
                "其他用户内容绝不能出现在简报中。",
                "private",
                True,
                1,
                0,
            ),
        ]
        ids = []
        for subindex, title, text, slug, recommended, status, days in fixtures:
            key = uuid.uuid4().hex
            ids.append(key)
            db.add(
                Content(
                    id=key,
                    subscription_id=subs[subindex].id,
                    source_platform="web",
                    source_url="https://example.org/briefing-fixture/" + slug,
                    title=title,
                    summary=text,
                    content_body=text,
                    status=status,
                    is_duplicate=0,
                    content_hash=hashlib.sha256(key.encode()).hexdigest(),
                    fetched_at=datetime.utcnow() - timedelta(days=days, minutes=1),
                    relevance={
                        "recommended": recommended,
                        "method": "llm",
                        "score": 95 - subindex,
                        "intent": "关注个人电脑模型部署实操与开发工具安全修复",
                        "reason": "这是独立的简报验收资料，语义结果为测试预置",
                    },
                )
            )
        await db.commit()
        return ids


async def delivery_and_failure(user_id, identifier, token):
    from app.main import app
    from app.services import push
    from app.api import push as push_api

    sent = []
    channels = []
    headers = {"Authorization": "Bearer " + token}

    async def mock_send(channel, text):
        sent.append(channel.provider)
        assert "https://example.org/briefing-fixture/" in text

    try:
        async with get_session_factory()() as db:
            for provider in ("feishu", "dingtalk"):
                channel = PushChannel(
                    user_id=user_id,
                    provider=provider,
                    name="MOCK ONLY " + provider,
                    webhook="https://example.invalid/mock-only",
                    enabled=1,
                )
                db.add(channel)
                await db.flush()
                channels.append(channel.id)
            await db.commit()
        with patch.object(push, "send", mock_send), patch.object(
            push_api, "send", mock_send
        ):
            # Repeated requests may race, but must claim each report/channel only once.
            await asyncio.gather(
                briefing.deliver(user_id, identifier),
                briefing.deliver(user_id, identifier),
            )
            assert sorted(sent) == ["dingtalk", "feishu"], sent
            async with get_session_factory()() as db:
                records = (
                    (
                        await db.execute(
                            select(PushDelivery).where(
                                PushDelivery.user_id == user_id,
                                PushDelivery.channel_id.in_(channels),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(records) == 2 and all(r.status == "sent" for r in records)
                record = records[0]
                record.status = "failed"
                delivery_id = record.id
                await db.commit()
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://fixture",
                headers=headers,
            ) as api:
                response = await api.post(
                    f"/api/python/push/deliveries/{delivery_id}/retry"
                )
                assert (
                    response.status_code == 200
                    and response.json()["data"]["status"] == "sent"
                ), response.text
                response = await api.put(
                    "/api/python/briefings/preferences",
                    json={"enabled": True, "pushEnabled": True},
                )
                assert response.status_code == 200
            async with get_session_factory()() as db:
                original = await db.get(Briefing, identifier)
                plan = {
                    k: original.report[k]
                    for k in ("headline", "overview", "events", "omitted")
                }

            async def mock_compose(*args):
                return plan

            with patch.object(briefing, "compose", mock_compose):
                schedule_key = f"{user_id}:fixture-{uuid.uuid4().hex[:8]}"
                scheduled_id = await briefing.create_briefing(
                    user_id, schedule_key=schedule_key
                )
                while BACKGROUND_TASKS:
                    await asyncio.gather(*list(BACKGROUND_TASKS))
                assert (
                    await briefing.create_briefing(user_id, schedule_key=schedule_key)
                    == scheduled_id
                )
            async with get_session_factory()() as db:
                scheduled = await db.get(Briefing, scheduled_id)
                records = (
                    (
                        await db.execute(
                            select(PushDelivery).where(
                                PushDelivery.task_id == "briefing:" + scheduled_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert (
                    scheduled.status == "ready"
                    and len(records) == 2
                    and all(r.status == "sent" for r in records)
                )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://fixture",
                headers=headers,
            ) as api:
                await api.put(
                    "/api/python/briefings/preferences",
                    json={"enabled": False, "pushEnabled": False},
                )

        async def bad_compose(*args):
            raise ValueError("mock invalid model output")

        with patch.object(briefing, "compose", bad_compose):
            failed_id = await briefing.create_briefing(user_id)
            await asyncio.gather(*list(BACKGROUND_TASKS))
        async with get_session_factory()() as db:
            failed = await db.get(Briefing, failed_id)
            assert (
                failed.status == "failed"
                and failed.report is None
                and failed.active_key is None
            )
            count = (
                await db.execute(
                    select(func.count())
                    .select_from(Notification)
                    .where(
                        Notification.user_id == user_id,
                        Notification.related_id == failed_id,
                    )
                )
            ).scalar()
            assert count == 0
            interrupted_id = uuid.uuid4().hex
            now = datetime.utcnow()
            db.add(
                Briefing(
                    id=interrupted_id,
                    user_id=user_id,
                    status="generating",
                    active_key=str(user_id),
                    hours=24,
                    period_start=now - timedelta(hours=24),
                    period_end=now,
                )
            )
            interrupted_delivery = PushDelivery(
                user_id=user_id,
                task_id="briefing:" + interrupted_id,
                channel_id=channels[0],
                status="pending",
                attempts=0,
            )
            db.add(interrupted_delivery)
            await db.commit()
            pending_id = interrupted_delivery.id
        await briefing.recover(user_id=user_id)
        async with get_session_factory()() as db:
            interrupted = await db.get(Briefing, interrupted_id)
            pending = await db.get(PushDelivery, pending_id)
            previous = await db.get(Briefing, identifier)
            assert interrupted.status == "failed" and interrupted.active_key is None
            assert pending.status == "failed" and previous.status == "ready"
        return {
            "mockDelivery": "passed",
            "mockIdempotentChannels": 2,
            "mockRetry": "passed",
            "mockDailyIdempotency": "passed",
            "mockAutomaticPush": "passed",
            "mockModelFailure": "passed",
            "recovery": "passed",
        }
    finally:
        from app.models.briefing import BriefingPreference

        async with get_session_factory()() as db:
            pref = await db.get(BriefingPreference, user_id)
            if pref:
                pref.enabled = pref.push_enabled = 0
            await db.execute(
                delete(PushChannel).where(
                    PushChannel.id.in_(channels), PushChannel.user_id == user_id
                )
            )
            await db.commit()


def main():
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=20)
    foreign = httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=20)
    name = "brief_ui_" + uuid.uuid4().hex[:8]
    password = "NexusUI!2026"
    data = account(client, name, password)
    other = account(foreign, "brief_o_" + uuid.uuid4().hex[:8], password)
    # Login response user shape is shared by the frontend.
    user_id, foreign_id = data["user"]["id"], other["user"]["id"]

    async def initialize():
        import app.core.dependencies as deps
        from app.core.dependencies import close_db_engine

        try:
            return await seed(user_id, foreign_id)
        finally:
            await close_db_engine()
            deps._async_session_factory = None

    ids = asyncio.run(initialize())
    prefs = client.get("/python/briefings/preferences").json()["data"]
    assert prefs["enabled"] is False and prefs["pushEnabled"] is False
    response = client.post("/python/briefings", json={"hours": 24})
    assert response.status_code == 200, response.text
    identifier = response.json()["data"]["id"]
    repeated = client.post("/python/briefings", json={"hours": 24}).json()["data"]["id"]
    assert (
        repeated == identifier
    ), "Repeated admission should reuse the active generation"
    print("Real-model generation started; isolated fixture articles only.", flush=True)
    started = time.monotonic()
    for _ in range(120):
        response = client.get("/python/briefings/" + identifier)
        assert response.status_code == 200, response.text
        row = response.json()["data"]
        if row["status"] in ("ready", "failed"):
            break
        time.sleep(2)
    assert row["status"] == "ready", row
    report = row["report"]
    assert report["availableCount"] == 4 and report["deduplicatedCount"] == 1, report
    assert {s["id"] for s in report["sources"]} == set(ids[:3]), report
    assert len(report["events"]) == 2, report
    assert any(
        {c["id"] for c in event["citations"]} == set(ids[:2])
        for event in report["events"]
    ), report
    assert foreign.get("/python/briefings/" + identifier).status_code == 404
    assert foreign.post("/python/briefings/" + identifier + "/push").status_code == 404
    assert client.post("/python/briefings/" + identifier + "/push").status_code == 409

    async def checks():
        from app.core.dependencies import close_db_engine

        try:
            return await delivery_and_failure(user_id, identifier, data["token"])
        finally:
            await close_db_engine()

    mocked = asyncio.run(checks())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        page.get_by_placeholder("用户名").fill(name)
        page.get_by_placeholder("密码", exact=True).fill(password)
        page.get_by_role("button", name="进入工作台").click()
        page.wait_for_url("**/dashboard")
        page.goto(
            "http://127.0.0.1:5173/briefings?id=" + identifier, wait_until="networkidle"
        )
        page.get_by_role("heading", name="把信息整理成值得关注的重点").wait_for()
        page.get_by_text("查看 2 篇原文与依据", exact=True).click()
        page.get_by_role(
            "link", name="Orion Runner 0.8 离线部署实测", exact=True
        ).wait_for()
        page.screenshot(
            path=str(ROOT / ".runtime/briefing-desktop.png"), full_page=True
        )
        with page.expect_download() as download:
            page.get_by_role("button", name="导出 Markdown").click()
        assert download.value.suggested_filename.endswith(".md")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(700)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth + 1"
        ), "Mobile overflow"
        page.screenshot(path=str(ROOT / ".runtime/briefing-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    result = {
        "result": "passed",
        "realModel": {"sources": 3, "events": 2, "mergedMultiSourceEvent": True},
        "publishedOnly": True,
        "ownership": "passed",
        "activeAdmission": "passed",
        "browser": "passed",
        "mobile390": "passed",
        "seconds": round(time.monotonic() - started, 1),
        **mocked,
    }
    (ROOT / ".runtime/briefing-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-model",
        action="store_true",
        required=True,
        help="Calls configured real model on a small synthetic fixture set.",
    )
    parser.parse_args()
    main()
