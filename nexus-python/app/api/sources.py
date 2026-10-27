from collections import Counter
from xml.etree import ElementTree as ET
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.core.auth import current_user
from app.services.sources import catalog, list_sources, check_source
import asyncio

router = APIRouter()


@router.get("")
async def sources(
    q: str = Query("", max_length=200),
    category: str = "",
    language: str = "",
    status: str = "",
    platform: str = Query("", pattern="^(|rss|api)$"),
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
):
    items = await list_sources(q, category, language, status, platform)
    all_items = await list_sources()
    from app.services.source_maintenance import enabled

    return {
        "code": 200,
        "data": {
            "items": items[(page - 1) * size : page * size],
            "total": len(items),
            "categories": catalog()["categories"],
            "maintenance": {"enabled": enabled(), "poll_seconds": 60, "batch_size": 4},
            "stats": {
                "total": len(all_items),
                **Counter(s["health"]["status"] for s in all_items),
                "hosts": len({s["homepage"] for s in all_items}),
                "chinese": sum(s["language"] == "zh" for s in all_items),
                "rss": sum(s["platform"] == "rss" for s in all_items),
                "api": sum(s["platform"] == "api" for s in all_items),
            },
        },
    }


class CheckInput(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=20)


@router.post("/check")
async def check(body: CheckInput):
    valid = {s["id"] for s in catalog()["sources"]}
    if any(sid not in valid for sid in body.ids):
        raise HTTPException(400, "包含未知的数据源")
    results = await asyncio.gather(
        *(check_source(sid) for sid in dict.fromkeys(body.ids))
    )
    return {"code": 200, "data": {"items": results}}


@router.get("/export.opml")
async def export(
    q: str = "",
    category: str = "",
    language: str = "",
    status: str = "",
    platform: str = "",
):
    root = ET.Element("opml", version="2.0")
    ET.SubElement(ET.SubElement(root, "head"), "title").text = "NexusAI 数据源目录"
    body = ET.SubElement(root, "body")
    skipped = 0
    for source in await list_sources(q, category, language, status, platform):
        if source["platform"] != "rss":
            skipped += 1
            continue
        ET.SubElement(
            body,
            "outline",
            text=source["name"],
            title=source["name"],
            type="rss",
            xmlUrl=source["url"],
            htmlUrl=source["homepage"],
        )
    return Response(
        ET.tostring(root, encoding="utf-8", xml_declaration=True),
        media_type="application/xml",
        headers={
            "Content-Disposition": 'attachment; filename="nexusai-sources.opml"',
            "X-Nexus-Skipped-Sources": str(skipped),
        },
    )


@router.get("/export.json")
async def export_json(
    q: str = "",
    category: str = "",
    language: str = "",
    status: str = "",
    platform: str = "",
):
    import json

    records = [
        {key: value for key, value in source.items() if key != "health"}
        for source in await list_sources(q, category, language, status, platform)
    ]
    return Response(
        json.dumps({"version": 2, "sources": records}, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="nexusai-sources.json"'},
    )


class DiscoverInput(BaseModel):
    url: str = Field(max_length=1000, pattern=r"^https?://[^\s]+$")


@router.post("/discover")
async def discover(body: DiscoverInput, request: Request):
    from app.services.source_discovery import run_discovery

    return {
        "code": 200,
        "data": await run_discovery(current_user(request)["id"], body.url),
    }
