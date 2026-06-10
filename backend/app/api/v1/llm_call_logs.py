from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.llm_call_log import LLMCallLog
from app.models.user import User


router = APIRouter(prefix="/llm-call-logs", tags=["llm-call-logs"])


def _row(log: LLMCallLog, include_text: bool = False) -> dict:
    data = {
        "id": log.id,
        "project_id": log.project_id,
        "project_name": log.project_name,
        "task_id": log.task_id,
        "function_name": log.function_name,
        "provider_id": log.provider_id,
        "provider_name": log.provider_name,
        "provider_type": log.provider_type,
        "model_name": log.model_name,
        "request_type": log.request_type,
        "status": log.status,
        "input_tokens": log.input_tokens,
        "output_tokens": log.output_tokens,
        "total_tokens": log.total_tokens,
        "duration_ms": log.duration_ms,
        "temperature": log.temperature,
        "max_tokens": log.max_tokens,
        "error_message": log.error_message,
        "created_at": log.created_at,
        "updated_at": log.updated_at,
    }
    if include_text:
        data.update({
            "system_prompt": log.system_prompt,
            "prompt": log.prompt,
            "response_content": log.response_content,
            "request_payload": log.request_payload or {},
            "response_metadata": log.response_metadata or {},
        })
    else:
        data.update({
            "prompt_preview": (log.prompt or "")[:300],
            "response_preview": (log.response_content or "")[:300],
        })
    return data


@router.get("")
async def list_llm_call_logs(
    project_id: str | None = None,
    project_name: str | None = None,
    function_name: str | None = None,
    model_name: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LLMCallLog)
    count_stmt = select(func.count(LLMCallLog.id))
    filters = []
    if project_id:
        filters.append(LLMCallLog.project_id == project_id)
    if project_name:
        filters.append(LLMCallLog.project_name.ilike(f"%{project_name}%"))
    if function_name:
        filters.append(LLMCallLog.function_name == function_name)
    if model_name:
        filters.append(LLMCallLog.model_name.ilike(f"%{model_name}%"))
    if status:
        filters.append(LLMCallLog.status == status)
    if q:
        pattern = f"%{q}%"
        filters.append(
            LLMCallLog.prompt.ilike(pattern)
            | LLMCallLog.response_content.ilike(pattern)
            | LLMCallLog.function_name.ilike(pattern)
            | LLMCallLog.project_name.ilike(pattern)
        )
    for condition in filters:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(
        stmt.order_by(LLMCallLog.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    return {"logs": [_row(log) for log in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/summary")
async def llm_call_log_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total_calls = (await db.execute(select(func.count(LLMCallLog.id)))).scalar_one()
    total_tokens = (await db.execute(select(func.coalesce(func.sum(LLMCallLog.total_tokens), 0)))).scalar_one()
    input_tokens = (await db.execute(select(func.coalesce(func.sum(LLMCallLog.input_tokens), 0)))).scalar_one()
    output_tokens = (await db.execute(select(func.coalesce(func.sum(LLMCallLog.output_tokens), 0)))).scalar_one()
    failed_calls = (await db.execute(select(func.count(LLMCallLog.id)).where(LLMCallLog.status == "failed"))).scalar_one()
    by_model = (await db.execute(
        select(
            LLMCallLog.model_name,
            func.count(LLMCallLog.id),
            func.coalesce(func.sum(LLMCallLog.total_tokens), 0),
        )
        .group_by(LLMCallLog.model_name)
        .order_by(func.count(LLMCallLog.id).desc())
        .limit(12)
    )).all()
    by_function = (await db.execute(
        select(
            LLMCallLog.function_name,
            func.count(LLMCallLog.id),
            func.coalesce(func.sum(LLMCallLog.total_tokens), 0),
        )
        .group_by(LLMCallLog.function_name)
        .order_by(func.count(LLMCallLog.id).desc())
        .limit(20)
    )).all()
    return {
        "total_calls": total_calls,
        "failed_calls": failed_calls,
        "success_rate": round(((total_calls - failed_calls) / total_calls) * 100, 1) if total_calls else 100,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "by_model": [{"model_name": r[0] or "未知", "call_count": r[1], "total_tokens": r[2]} for r in by_model],
        "by_function": [{"function_name": r[0] or "未知", "call_count": r[1], "total_tokens": r[2]} for r in by_function],
    }


@router.get("/{log_id}")
async def get_llm_call_log(log_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    log = (await db.execute(select(LLMCallLog).where(LLMCallLog.id == log_id))).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "调用记录不存在")
    return {"log": _row(log, include_text=True)}
