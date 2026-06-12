"""Skill API — 技能发现、调用、指标查询"""

from fastapi import APIRouter, Request, Query
from app.harness.base import get_metrics_store

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
    """调用一个 Skill"""
    registry = request.app.state.skill_registry
    result = await registry.invoke(name)
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
async def skill_metrics():
    """获取 Agent 执行指标：总次数、成功率、每 Skill 平均耗时"""
    store = get_metrics_store()
    return {"code": 200, "data": store.stats()}


@router.get("/skills/metrics/recent")
async def skill_metrics_recent(n: int = Query(default=20, le=100)):
    """获取最近 N 条执行记录"""
    store = get_metrics_store()
    return {"code": 200, "data": store.recent(n)}
