"""Explainable heuristics for extracted text, shared by real collection and trials.

The score measures extraction quality, not truthfulness or editorial authority.
"""

import re
from app.services.fetching import plain_text

LABELS = {
    "body": "正文片段",
    "summary": "摘要",
    "short": "内容过短",
    "metadata": "仅链接元数据",
    "blocked": "访问验证页",
    "navigation": "疑似导航页",
    "empty": "正文为空",
}


def assess_quality(text: str, title: str = "") -> dict:
    body = plain_text(text or "").strip()
    count = len(re.sub(r"\s", "", body))
    prefix = body[:500].lower()
    heading = title.strip().lower()
    challenge = re.compile(
        r"^(just a moment|access denied|attention required|checking your browser|verify (?:that )?you are human|安全验证|访问验证|人机验证)",
        re.I,
    )
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    nav_terms = sum(
        term in body
        for term in ("首页", "登录", "注册", "联系我们", "隐私政策", "网站地图")
    )
    if not count:
        kind, score, reasons = "empty", 0, ["没有提取到正文"]
    elif challenge.search(heading) or (
        count < 3000
        and (
            challenge.search(prefix)
            or ("verify you are human" in prefix and "captcha" in prefix)
        )
    ):
        kind, score, reasons = "blocked", 0, ["提取到访问验证或拒绝访问页面"]
    elif (
        len(lines) >= 12
        and nav_terms >= 3
        and sum(len(line) < 16 for line in lines) / len(lines) > 0.8
        and count < 1600
    ):
        kind, score, reasons = (
            "navigation",
            15,
            ["短导航项占比过高，未找到可靠文章正文"],
        )
    elif (
        re.search(
            r"(?:Article\s*URL|Comments?\s*URL|#\s*Comments?)\s*[:：]", body, re.I
        )
        and len(
            re.sub(
                r"https?://\S+|(?:Article\s*URL|Comments?\s*URL|Points?|#\s*Comments?)\s*[:：][^\n]*",
                "",
                body,
                flags=re.I,
            ).strip()
        )
        < 50
    ):
        kind, score, reasons = "metadata", 20, ["只有原文链接、评论或热度信息"]
    elif count < 80:
        kind, score, reasons = (
            "short",
            30,
            ["可读文字少于 80 字，可能只有标题或简短导语"],
        )
    elif count < 800:
        kind, score, reasons = "summary", 65, ["当前内容较短，按摘要展示"]
    else:
        kind, score, reasons = "body", 90, []
    if not title.strip():
        score = max(0, score - 10)
        reasons.append("缺少文章标题")
    return {
        "kind": kind,
        "label": LABELS[kind],
        "score": score,
        "characters": count,
        "eligible": kind not in {"blocked", "navigation", "empty"},
        "reasons": reasons,
        "method": "heuristic-v1",
    }
