import json
import asyncio
import uuid
from typing import Any

from app.agents.scout_agent import run_scout_task
from app.core.dependencies import get_db_session, close_db_engine
from app.core.config import settings


class NexusMQConsumer:
    """RocketMQ 消费者封装：消费 nexus-task-trigger 并启动 Scout Agent"""

    def __init__(self, mcp_pool: Any):
        self.mcp_pool = mcp_pool
        self._consumer = None
        self._running = False

    def start(self):
        """启动消费者（阻塞方法，建议在后台线程运行）"""
        try:
            from rocketmq.client import PushConsumer
        except ImportError:
            print("[MQ] rocketmq-client-python not installed, skipping consumer")
            return

        try:
            self._consumer = PushConsumer(settings.rocketmq.consumer_group)
            self._consumer.set_name_server_address(settings.rocketmq.nameserver)
            self._consumer.subscribe(
                settings.rocketmq.topic_task_trigger,
                callback=self._on_message,
                expression="*",
            )
            self._consumer.start()
            self._running = True
            print(f"[MQ] Consumer started: group={settings.rocketmq.consumer_group}, topic={settings.rocketmq.topic_task_trigger}")
        except Exception as e:
            print(f"[MQ] Consumer start failed (is RocketMQ running?): {e}")
            self._consumer = None
            self._running = False

    def stop(self):
        """优雅关闭消费者"""
        if self._consumer:
            self._consumer.shutdown()
            self._running = False
            print("[MQ] Consumer stopped")

    def _on_message(self, msg):
        """消息回调（同步上下文，后台线程）"""
        try:
            body = json.loads(msg.body)
            subscription_id = body.get("subscriptionId")
            keywords = body.get("keywords", [])
            platforms = body.get("sourcePlatforms", [])
            task_id = body.get("taskId") or uuid.uuid4().hex

            print(f"[MQ] Received task trigger: taskId={task_id}, subscriptionId={subscription_id}")

            # 在独立的事件循环中执行异步 Agent（避免与主循环冲突）
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._handle_task(task_id, subscription_id, keywords, platforms))
            finally:
                loop.close()
        except Exception as e:
            print(f"[MQ] Message handling error: {e}")

    async def _handle_task(self, task_id: str, subscription_id: int, keywords: list, platforms: list):
        """异步处理：创建 DB Session 并运行 Scout Agent"""
        async for db in get_db_session():
            try:
                await run_scout_task(
                    task_id=task_id,
                    subscription_id=subscription_id,
                    keywords=keywords,
                    source_platforms=platforms,
                    mcp_pool=self.mcp_pool,
                    db=db,
                )
            except Exception as e:
                print(f"[MQ] Agent execution error: {e}")
            finally:
                await db.close()
            break
