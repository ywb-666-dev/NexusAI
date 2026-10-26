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


async def run(limit=0):
    groups = defaultdict(list)
    for source in catalog()["sources"][: limit or None]:
        groups[source["homepage"]].append(source)
    results = []
    semaphore = asyncio.Semaphore(4)

    async def group(items):
        for source in items:
            async with semaphore:
                result = await check_source(source["id"])
            results.append({"name": source["name"], "url": source["url"], **result})
            print(f"[{len(results)}] {source['name']}: {result['status']}", flush=True)
            # Avoid bursts to publishers with several subject feeds.
            await asyncio.sleep(3 if "rss.arxiv.org" in source["url"] else 0.3)

    try:
        await asyncio.gather(*(group(items) for items in groups.values()))
        data = {
            "counts": dict(Counter(r["status"] for r in results)),
            "sources": results,
        }
        output = ROOT / ".runtime/source-check-result.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(data["counts"], ensure_ascii=False), flush=True)
    finally:
        await close_db_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    asyncio.run(run(parser.parse_args().limit))
