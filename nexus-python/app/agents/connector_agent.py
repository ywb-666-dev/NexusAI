"""Store canonical content as pending until the risk decision is made."""

import hashlib
import uuid
import re
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.models import Content
from app.models.task import AgentTask
from app.agents.state import NexusState
from app.services.fetching import published


async def run_connector(state: NexusState, db) -> NexusState:
    items = state.get("parser", {}).get("items", [])
    ids, duplicate_count = [], 0
    seen = set()
    for item in items:
        normalized = re.sub(
            r"\s+",
            " ",
            item.get("title", "")
            + "\n"
            + item.get("raw_html", item.get("summary", "")),
        ).strip()
        key = hashlib.sha256(
            f"{state['subscription_id']}:{normalized}".encode()
        ).hexdigest()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        exists = (
            await db.execute(
                select(Content)
                .where(
                    Content.subscription_id == state["subscription_id"],
                    or_(
                        Content.content_hash == key,
                        Content.source_url == item["source_url"],
                    ),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if exists:
            previous_task = (
                await db.get(AgentTask, exists.task_id)
                if exists.task_id and exists.status == 2
                else None
            )
            if previous_task and previous_task.status == "failed":
                exists.task_id = state["task_id"]
                ids.append(exists.id)
                continue
            duplicate_count += 1
            continue
        cid = str(uuid.uuid4())
        content = Content(
            id=cid,
            subscription_id=state["subscription_id"],
            task_id=state["task_id"],
            source_platform=item["platform"],
            source_url=item["source_url"][:1000],
            title=item.get("title", "")[:500],
            summary=item.get("summary", "")[:2000],
            translated_summary=item.get("translated_summary"),
            content_body=item.get("raw_html", ""),
            author=item.get("author", "")[:100],
            published_at=published(item.get("published_at")),
            content_hash=key,
            status=2,
            is_duplicate=0,
            related_contents=[],
        )
        try:
            async with db.begin_nested():
                db.add(content)
                await db.flush()
            ids.append(cid)
        except IntegrityError:
            duplicate_count += 1
    await db.commit()
    state["connector"] = {
        "stored_ids": ids,
        "stored_count": len(ids),
        "duplicate_count": duplicate_count,
        "items": items,
        "related_groups": [],
    }
    state["next_node"] = "actor"
    return state
