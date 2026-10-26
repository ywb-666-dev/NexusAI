"""Single-instance, paced source maintenance independent of subscription collection."""

import asyncio
import logging
import os
from datetime import datetime
from sqlalchemy import select
from app.core.dependencies import get_session_factory
from app.models.source import SourceHealth
from app.services.sources import catalog, check_source, next_due, utcnow


def enabled():
    return os.getenv("SOURCE_HEALTH_ENABLED", "true").lower() == "true"


async def maintenance_cycle():
    async with get_session_factory()() as db:
        rows = {
            row.source_id: row
            for row in (await db.execute(select(SourceHealth))).scalars()
        }
    now = utcnow()
    due = [
        s
        for s in catalog()["sources"]
        if s["id"] not in rows or next_due(rows[s["id"]]) <= now
    ]
    due.sort(
        key=lambda s: (next_due(rows[s["id"]]) if s["id"] in rows else datetime.min)
    )
    selected, hosts = [], set()
    for source in due:
        if source["homepage"] in hosts:
            continue
        selected.append(source)
        hosts.add(source["homepage"])
        if len(selected) == 4:
            break
    results = await asyncio.gather(
        *(check_source(s["id"]) for s in selected), return_exceptions=True
    )
    for result in results:
        if isinstance(result, Exception):
            logging.warning("Source check failed: %s", result)
    return len(selected)


async def run_maintenance():
    await asyncio.sleep(45)
    while True:
        try:
            if enabled():
                await maintenance_cycle()
        except Exception:
            logging.exception("Source maintenance cycle failed")
        await asyncio.sleep(60)
