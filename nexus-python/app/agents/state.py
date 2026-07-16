"""NexusAI 5-Agent State Machine — 共享状态定义"""

from typing import TypedDict, Annotated
from operator import add


class ScoutResult(TypedDict, total=False):
    """Scout Agent 输出：原始采集项"""
    items: list[dict]
    total_fetched: int


class ParserResult(TypedDict, total=False):
    """Parser Agent 输出：清洗后的内容"""
    items: list[dict]
    cleaned_count: int
    scraped_count: int
    translated_count: int


class ConnectorResult(TypedDict, total=False):
    """Connector Agent 输出：去重与关联"""
    items: list[dict]
    stored_count: int
    duplicate_count: int
    related_groups: list[list[str]]


class ActorResult(TypedDict, total=False):
    """Actor Agent 输出：决策结果"""
    action: str  # "proceed" | "approval_required" | "skip" | "reject"
    risk_level: int  # 1=低 2=中 3=高
    reason: str
    approval_id: int | None


class CuratorResult(TypedDict, total=False):
    """Curator Agent 输出：日报"""
    report: str
    item_count: int


class NexusState(TypedDict, total=False):
    """
    NexusAI 5-Agent 共享状态。

    流程: Scout → Parser → Connector → Actor → Curator
    每个 Agent 节点读取上游输出，写入自身结果。
    """
    # ── 输入参数 ──
    task_id: str
    subscription_id: int
    keywords: list[str]
    source_platforms: list[str]
    user_id: int | None
    rss_feeds: list[dict]  # [{url, name, platform}]

    # ── 各节点输出 ──
    scout: ScoutResult
    parser: ParserResult
    connector: ConnectorResult
    actor: ActorResult
    curator: CuratorResult

    # ── 流转控制 ──
    next_node: str
    error: str | None
    status: str  # queued → fetching → parsing → storing → deciding → curating → completed

    # ── 通知收集 (Annotated list for LangGraph reducer) ──
    notifications: Annotated[list[dict], add]
