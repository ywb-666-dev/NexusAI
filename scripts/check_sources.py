"""Check bundled feeds from this server and persist observed health, without subscribing."""

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.services.sources import catalog, check_source
from app.core.dependencies import close_db_engine


async def run(limit=0, ids=None, force=False, output=None):
    groups = defaultdict(list)
    selected = [
        source for source in catalog()["sources"] if ids is None or source["id"] in ids
    ]
    if ids is not None and set(ids) - {s["id"] for s in selected}:
        raise ValueError("检测列表包含未知来源")
    for source in selected[: limit or None]:
        groups[source["homepage"]].append(source)
    results = []
    semaphore = asyncio.Semaphore(4)

    async def group(items):
        for source in items:
            async with semaphore:
                result = await check_source(source["id"], force=force)
            results.append({"name": source["name"], "url": source["url"], **result})
            print(f"[{len(results)}] {source['name']}: {result['status']}", flush=True)
            # Avoid bursts to publishers with several subject feeds.
            await asyncio.sleep(
                3
                if "rss.arxiv.org" in source["url"] or "api.github.com" in source["url"]
                else 0.3
            )

    try:
        await asyncio.gather(*(group(items) for items in groups.values()))
        data = {
            "counts": dict(Counter(r["status"] for r in results)),
            "sources": results,
        }
        destination = (
            Path(output) if output else ROOT / ".runtime/source-check-result.json"
        )
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(data["counts"], ensure_ascii=False), flush=True)
    finally:
        await close_db_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ids-file", help="JSON array of catalog source IDs to check")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    ids = (
        json.loads(Path(args.ids_file).read_text(encoding="utf-8"))
        if args.ids_file
        else None
    )
    asyncio.run(run(args.limit, ids=ids, force=args.force, output=args.output))
