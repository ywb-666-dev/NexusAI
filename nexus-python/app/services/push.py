"""Webhook delivery with durable results and bounded retries; never expose tokens in errors."""

import asyncio
import base64
import hashlib
import hmac
import time
from urllib.parse import urlparse, parse_qsl
import os
import httpx
from sqlalchemy import select
from app.core.dependencies import get_session_factory
from app.models.delivery import PushChannel, PushDelivery


def validate_webhook(provider, url):
    parsed = urlparse(url)
    if os.getenv("NEXUS_ALLOW_LOCAL_SOURCES") == "true" and parsed.hostname in (
        "127.0.0.1",
        "localhost",
    ):
        return
    hosts = {
        "feishu": ("open.feishu.cn", "open.larksuite.com"),
        "dingtalk": ("oapi.dingtalk.com",),
    }
    if (
        provider not in hosts
        or parsed.scheme != "https"
        or parsed.hostname not in hosts[provider]
        or parsed.username
        or parsed.password
    ):
        raise ValueError("请填写飞书或钉钉官方 HTTPS 机器人 Webhook")


def payload_for(channel, text):
    timestamp = str(int(time.time()))
    message = ('NexusAI 内容简报\n' + text).encode('utf-8')[:15000].decode('utf-8', errors='ignore')
    if channel.provider == "feishu":
        data = {
            "msg_type": "text",
            "content": {"text": message},
        }
        if channel.secret:
            key = f"{timestamp}\n{channel.secret}".encode()
            data.update(
                timestamp=timestamp,
                sign=base64.b64encode(
                    hmac.new(key, b"", hashlib.sha256).digest()
                ).decode(),
            )
        return data, {}
    params = {}
    if channel.secret:
        millis = str(int(time.time() * 1000))
        sign = base64.b64encode(
            hmac.new(
                channel.secret.encode(),
                f"{millis}\n{channel.secret}".encode(),
                hashlib.sha256,
            ).digest()
        ).decode()
        params = {"timestamp": millis, "sign": sign}
    return {
        "msgtype": "text",
        "text": {"content": message},
    }, params


async def send(channel, text):
    validate_webhook(channel.provider, channel.webhook)
    payload, params = payload_for(channel, text)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        query = dict(parse_qsl(urlparse(channel.webhook).query, keep_blank_values=True))
        query.update(params)
        response = await client.post(
            channel.webhook, json=payload, params=query or None
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code", result.get("errcode", result.get("StatusCode", 0))) != 0:
            raise RuntimeError("机器人拒绝消息，请检查签名、关键词和机器人权限")


async def dispatch_report(user_id, task_id, report):
    async with get_session_factory()() as db:
        channels = (
            (
                await db.execute(
                    select(PushChannel).where(
                        PushChannel.user_id == user_id, PushChannel.enabled == 1
                    )
                )
            )
            .scalars()
            .all()
        )
        for channel in channels:
            previous = (
                await db.execute(
                    select(PushDelivery).where(
                        PushDelivery.task_id == task_id,
                        PushDelivery.channel_id == channel.id,
                    )
                )
            ).scalar_one_or_none()
            if previous:
                continue
            delivery = PushDelivery(
                user_id=user_id,
                task_id=task_id,
                channel_id=channel.id,
                status="pending",
                attempts=0,
            )
            db.add(delivery)
            await db.commit()
            for attempt in range(3):
                delivery.attempts = attempt + 1
                try:
                    await send(channel, report)
                    delivery.status, delivery.error = "sent", None
                    break
                except Exception:
                    delivery.status, delivery.error = (
                        "failed",
                        "推送失败，请检查机器人配置或网络连接",
                    )
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
            await db.commit()
