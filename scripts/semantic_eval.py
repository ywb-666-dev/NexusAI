"""Small semantic acceptance set using the configured real model. No content is published."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.services.semantic import SemanticPolicy, compile_intent, filter_articles


async def run():
    fixture = json.loads(
        (ROOT / "nexus-python/tests/fixtures/semantic_cases.json").read_text(
            encoding="utf-8"
        )
    )
    policy = SemanticPolicy.model_validate(fixture["policy"])
    items = [
        {
            "title": case["title"],
            "summary": case["body"],
            "raw_html": case["body"],
            "source_url": "https://fixture.example/" + case["id"],
        }
        for case in fixture["cases"]
    ]
    plan = await compile_intent(policy)
    result = await filter_articles(items, policy, plan)
    accepted = {item["source_url"]: item["relevance"] for item in result["items"]}
    rejected = {
        item["url"]: item["relevance"] for item in result["summary"]["rejected"]
    }
    rows = []
    for case in fixture["cases"]:
        url = "https://fixture.example/" + case["id"]
        verdict = accepted.get(url) or rejected[url]
        actual = url in accepted
        rows.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "recommended": actual,
                "score": verdict["score"],
                "reason": verdict["reason"],
                "passed": actual == case["expected"],
            }
        )
    data = {
        "result": "passed" if all(r["passed"] for r in rows) else "failed",
        "cases": len(rows),
        "correct": sum(r["passed"] for r in rows),
        "plan": plan,
        "results": rows,
    }
    output = ROOT / ".runtime/semantic-eval-result.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": data["result"],
                "cases": data["cases"],
                "correct": data["correct"],
                "scores": [
                    {"id": r["id"], "score": r["score"], "passed": r["passed"]}
                    for r in rows
                ],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if data["result"] != "passed":
        raise AssertionError(
            "Real model acceptance set failed; inspect .runtime/semantic-eval-result.json"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-model",
        action="store_true",
        required=True,
        help="Acknowledge this small evaluation calls the configured model service.",
    )
    parser.parse_args()
    asyncio.run(run())
