"""Actor Agent — 决策行动节点：风险评估、审批触发、动作决策"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import ApprovalTicket, Content
from app.agents.state import NexusState, ActorResult


# 敏感关键词（高风险标记）
_SENSITIVE_KEYWORDS = [
    "exploit", "漏洞", "CVE-", "zero-day", "0day",
    "数据泄露", "data breach", "credential", "ransomware",
]

_LOW_RISK_THRESHOLD = 5  # 少于5条新内容 → 低风险
_HIGH_RISK_THRESHOLD = 20  # 超过20条 → 高风险


def _assess_risk(stored_count: int, items: list[dict]) -> tuple[int, str]:
    """
    评估采集内容的综合风险等级。

    返回: (risk_level, reason)
        risk_level: 1=低, 2=中, 3=高
    """
    risk_score = 1
    reasons: list[str] = []

    # 数量因素
    if stored_count >= _HIGH_RISK_THRESHOLD:
        risk_score = max(risk_score, 3)
        reasons.append(f"大量新内容({stored_count}条)")
    elif stored_count >= _LOW_RISK_THRESHOLD:
        risk_score = max(risk_score, 2)
        reasons.append(f"中等数量新内容({stored_count}条)")

    # 敏感关键词检测
    sensitive_matches: list[str] = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        for keyword in _SENSITIVE_KEYWORDS:
            if keyword.lower() in text.lower():
                sensitive_matches.append(keyword)
    if sensitive_matches:
        risk_score = max(risk_score, 3)
        unique_matches = list(set(sensitive_matches))[:5]
        reasons.append(f"匹配敏感关键词: {', '.join(unique_matches)}")

    return risk_score, "; ".join(reasons) if reasons else "常规内容"


async def run_actor(state: NexusState, db: AsyncSession) -> NexusState:
    """
    Actor Agent 节点：风险评估与决策。

    1. 分析 Connector 输出的内容风险
    2. 高风险 → 创建审批工单，等待人工介入
    3. 中/低风险 → 自动通过，直接进入 Curator
    """
    stored_count = state.get("connector", {}).get("stored_count", 0)
    items = state.get("connector", {}).get("items", [])

    if stored_count == 0:
        state["actor"] = ActorResult(
            action="skip",
            risk_level=1,
            reason="无新增内容",
            approval_id=None,
        )
        state["next_node"] = "curator"
        return state

    risk_level, reason = _assess_risk(stored_count, items)

    if risk_level >= 3:
        # 高风险：创建审批工单，中断流程
        try:
            ticket = ApprovalTicket(
                task_id=state.get("task_id", ""),
                action_type="content_publish",
                risk_level=risk_level,
                status=0,  # pending
                comment=f"自动风险评估: {reason}",
            )
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)

            state["actor"] = ActorResult(
                action="approval_required",
                risk_level=risk_level,
                reason=reason,
                approval_id=ticket.id,
            )
            state["next_node"] = "__interrupt__"
            state["status"] = "interrupted: awaiting approval"
        except Exception as e:
            print(f"[Actor] Failed to create approval ticket: {e}")
            state["actor"] = ActorResult(
                action="proceed",
                risk_level=risk_level,
                reason=f"审批创建失败，自动通过: {e}",
                approval_id=None,
            )
            state["next_node"] = "curator"
    else:
        state["actor"] = ActorResult(
            action="proceed",
            risk_level=risk_level,
            reason=reason,
            approval_id=None,
        )
        state["next_node"] = "curator"

    return state
