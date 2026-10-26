from collections import Counter
from xml.etree import ElementTree as ET
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.services.sources import catalog, list_sources, check_source
import asyncio

router = APIRouter()


@router.get("")
async def sources(
    q: str = Query("", max_length=200),
    category: str = "",
    language: str = "",
    status: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
):
    items = await list_sources(q, category, language, status)
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
async def export(q: str = "", category: str = "", language: str = "", status: str = ""):
    root = ET.Element("opml", version="2.0")
    ET.SubElement(ET.SubElement(root, "head"), "title").text = "NexusAI 数据源目录"
    body = ET.SubElement(root, "body")
    for source in await list_sources(q, category, language, status):
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
        headers={"Content-Disposition": 'attachment; filename="nexusai-sources.opml"'},
    )
