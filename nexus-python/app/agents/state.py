from typing import TypedDict, Annotated
import operator


class ScoutState(TypedDict):
    """Scout Agent LangGraph 共享状态"""
    task_id: str
    subscription_id: int
    keywords: list[str]
    source_platforms: list[str]
    raw_items: Annotated[list[dict], operator.add]
    parsed_contents: Annotated[list[dict], operator.add]
    duplicate_ids: Annotated[list[str], operator.add]
    stored_ids: Annotated[list[str], operator.add]
    stored_count: int
    duplicate_count: int
    status: str
    error: str | None
