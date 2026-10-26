"""Single scheduler; it uses the same durable admission path as manual requests."""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models import Subscription
from app.core.dependencies import get_session_factory
from app.services.task_service import create_task


async def start_scheduler(supervisor):
    await asyncio.sleep(30)
    while True:
        try:
            async with get_session_factory()() as db:
                subs = (
                    (
                        await db.execute(
                            select(Subscription)
                            .where(Subscription.status == 1)
                            .order_by(Subscription.priority, Subscription.id)
                        )
                    )
                    .scalars()
                    .all()
                )
            for sub in subs:
                conditions = (
                    sub.trigger_conditions
                    if isinstance(sub.trigger_conditions, dict)
                    else {}
                )
                try:
                    interval = min(
                        10080, max(15, int(conditions.get("interval_minutes", 60)))
                    )
                except (TypeError, ValueError):
                    interval = 60
                if sub.last_run_at and datetime.utcnow() - sub.last_run_at < timedelta(
                    minutes=interval
                ):
                    continue
                try:
                    await create_task(sub.id, sub.user_id, supervisor)
                except Exception as exc:
                    print(f"[Scheduler] Subscription {sub.id}: {exc}")
        except Exception as exc:
            print(f"[Scheduler] Poll failed: {exc}")
        await asyncio.sleep(60)
