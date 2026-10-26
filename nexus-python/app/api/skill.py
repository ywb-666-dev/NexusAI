"""Skill API — 技能发现、调用、指标查询"""

from fastapi import APIRouter, Request, Query, HTTPException
from app.harness.base import get_metrics_store
from app.core.auth import current_user

router = APIRouter()


@router.get("/skills")
async def list_skills(request: Request, tag: str | None = Query(None)):
    """列出所有可用 Skill，支持按标签筛选"""
    registry = request.app.state.skill_registry
    if tag:
        skills = registry.list_by_tag(tag)
    else:
        skills = registry.list_all()
    return {"code": 200, "data": {"skills": skills, "total": len(skills)}}


@router.post("/skills/{name}/invoke")
async def invoke_skill(name: str, request: Request):
    """Invoke a Skill with optional parameters from request body."""
    registry = request.app.state.skill_registry
    body = {}
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "请输入 JSON 参数")
    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须为 JSON 对象")
    if any(key.startswith("_") for key in body):
        raise HTTPException(400, "参数名称不合法")
    if len(str(body.get("text", body.get("items_text", "")))) > 20000:
        raise HTTPException(400, "单次处理的文本不能超过 20000 字符")
    result = await request.app.state.harness.run(name, _registry=registry, **body)
    return {
        "code": 200 if result.success else 500,
        "data": {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "duration_ms": result.duration_ms,
        },
    }


@router.get("/skills/metrics")
async def skill_metrics(request: Request):
    """获取 Agent 执行指标：总次数、成功率、每 Skill 平均耗时"""
    if current_user(request)["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    store = get_metrics_store()
    return {"code": 200, "data": store.stats()}


@router.get("/skills/metrics/recent")
async def skill_metrics_recent(
    request: Request, n: int = Query(default=20, ge=1, le=100)
):
    """获取最近 N 条执行记录"""
    if current_user(request)["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    store = get_metrics_store()
    return {"code": 200, "data": store.recent(n)}
