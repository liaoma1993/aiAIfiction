import asyncio
import random
import json
from datetime import datetime, timezone
import uuid
from typing import Coroutine, Any
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import async_session
from app.models.chapter import GenerationTask

_tasks: dict[str, dict] = {}
INTERRUPTED_BY_RESTART = "服务重启，后台任务已中断，请重新发起"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_db_task(task: GenerationTask) -> dict:
    config = task.precision_config or {}
    result = task.result_summary or {}
    error = task.error_message
    if task.status == "failed" and not error:
        error = "任务失败，但旧记录没有保存具体错误；常见原因是 LLM 请求超时或服务中断，请重新发起"
    return {
        "id": str(task.id),
        "status": task.status,
        "result": result.get("result"),
        "error": error,
        "progress": (task.progress or 0) / 100,
        "progress_label": config.get("progress_label", ""),
        "detail": config.get("detail", {}),
        "task_type": task.task_type,
        "project_id": str(task.project_id) if task.project_id else None,
        "chapter_id": str(task.chapter_id) if task.chapter_id else None,
        "meta": config.get("meta", {}),
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "updated_at": task.updated_at.isoformat() if task.updated_at else "",
    }


def _task_fingerprint(task_type: str | None, project_id: str | None, meta: dict | None) -> str:
    meta = meta or {}
    normalized_meta = {
        k: v for k, v in meta.items()
        if k not in {"retry_of"} and v not in (None, "", [], {})
    }
    return json.dumps(
        {
            "task_type": task_type or "ai",
            "project_id": project_id or "",
            "meta": normalized_meta,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _task_fingerprint_from_dict(task: dict) -> str:
    return _task_fingerprint(task.get("task_type"), task.get("project_id"), task.get("meta") or {})


def _parse_task_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _find_running_duplicate(task_type: str, project_id: str | None, meta: dict | None) -> str | None:
    fingerprint = _task_fingerprint(task_type, project_id, meta)
    for task_id, task in _tasks.items():
        if task.get("status") not in {"running", "cancelling"}:
            continue
        if _task_fingerprint_from_dict(task) == fingerprint:
            return task_id
    return None


def _dedupe_task_list(tasks: list[dict]) -> list[dict]:
    result = []
    seen_recent: dict[str, datetime] = {}
    for task in tasks:
        fingerprint = _task_fingerprint_from_dict(task)
        created_at = _parse_task_time(task.get("created_at"))
        previous_time = seen_recent.get(fingerprint)
        if previous_time and created_at:
            gap = abs((previous_time - created_at).total_seconds())
            if gap <= 10 and task.get("status") in {"completed", "failed"}:
                continue
        if created_at:
            seen_recent[fingerprint] = created_at
        result.append(task)
    return result


async def _persist_create(task_id: str, task_type: str, project_id: str | None, meta: dict | None):
    if not project_id:
        return
    async with async_session() as db:
        existing = (await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))).scalar_one_or_none()
        if existing:
            return
        db.add(GenerationTask(
            id=task_id,
            project_id=project_id,
            chapter_id=(meta or {}).get("chapter_id"),
            task_type=task_type,
            status="running",
            progress=0,
            precision_config={"meta": meta or {}, "progress_label": "", "detail": {}},
            result_summary={},
            celery_task_id=task_id,
        ))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
        except OperationalError:
            await db.rollback()
            raise


async def _persist_create_with_retry(task_id: str, task_type: str, project_id: str | None, meta: dict | None, attempts: int = 3):
    for i in range(attempts):
        try:
            await _persist_create(task_id, task_type, project_id, meta)
            return
        except OperationalError:
            if i == attempts - 1:
                return
            await asyncio.sleep(0.25 * (i + 1) + random.uniform(0, 0.1))
        except Exception:
            return


async def _persist_update(task_id: str, **updates):
    async with async_session() as db:
        task = (await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))).scalar_one_or_none()
        if not task:
            memory = _tasks.get(task_id)
            if memory and memory.get("project_id"):
                task = GenerationTask(
                    id=task_id,
                    project_id=memory.get("project_id"),
                    chapter_id=(memory.get("meta") or {}).get("chapter_id"),
                    task_type=memory.get("task_type", "ai"),
                    status=memory.get("status", "running"),
                    progress=max(0, min(100, int((memory.get("progress") or 0) * 100))),
                    precision_config={
                        "meta": memory.get("meta") or {},
                        "progress_label": memory.get("progress_label", ""),
                        "detail": memory.get("detail", {}),
                    },
                    result_summary={},
                    celery_task_id=task_id,
                )
                db.add(task)
        if not task:
            return
        if "status" in updates:
            task.status = updates["status"]
        if "progress" in updates:
            task.progress = max(0, min(100, int((updates["progress"] or 0) * 100)))
        if "error" in updates:
            task.error_message = updates["error"]
        config = task.precision_config or {}
        if "progress_label" in updates:
            config["progress_label"] = updates["progress_label"] or ""
        if "detail" in updates:
            config["detail"] = updates["detail"] or {}
        if "meta" in updates:
            config["meta"] = updates["meta"] or {}
        task.precision_config = config
        if "result" in updates:
            task.result_summary = {"result": updates["result"]}
        try:
            await db.commit()
        except OperationalError:
            await db.rollback()
            raise


async def _persist_update_with_retry(task_id: str, attempts: int = 3, **updates):
    for i in range(attempts):
        try:
            await _persist_update(task_id, **updates)
            return
        except OperationalError:
            if i == attempts - 1:
                return
            await asyncio.sleep(0.25 * (i + 1) + random.uniform(0, 0.1))
        except Exception:
            return


def _schedule(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(coro)


def _schedule_retry(coro_factory, attempts: int = 3, delay: float = 0.25):
    async def _retry():
        for i in range(attempts):
            try:
                await coro_factory()
                return
            except OperationalError:
                if i == attempts - 1:
                    return
                await asyncio.sleep(delay * (i + 1) + random.uniform(0, 0.1))
            except Exception:
                return

    _schedule(_retry())


def start_task(coro: Coroutine, task_type: str = "ai", project_id: str | None = None, meta: dict | None = None, task_id: str | None = None, timeout: int = 3600) -> str:
    if task_id is None:
        duplicate_id = _find_running_duplicate(task_type, project_id, meta or {})
        if duplicate_id:
            try:
                coro.close()
            except Exception:
                pass
            return duplicate_id
    if task_id is None:
        task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "id": task_id,
        "status": "running",
        "result": None,
        "error": None,
        "progress": 0,
        "progress_label": "",
        "task_type": task_type,
        "project_id": project_id,
        "meta": meta or {},
        "created_at": _now(),
        "updated_at": _now(),
    }

    async def _runner():
        try:
            await _persist_create_with_retry(task_id, task_type, project_id, meta or {})
            result = await asyncio.wait_for(coro, timeout=timeout)
            _tasks[task_id]["status"] = "completed"
            _tasks[task_id]["result"] = result
            await _persist_update_with_retry(task_id, status="completed", progress=1, result=result)
        except asyncio.TimeoutError:
            _tasks[task_id]["status"] = "failed"
            hours = timeout // 3600
            minutes = (timeout % 3600) // 60
            if minutes == 0:
                text = f"{hours}小时"
            else:
                text = f"{hours}小时{minutes}分钟"
            error = f"AI 生成超时（{text}）"
            _tasks[task_id]["error"] = error
            detail = {"stage": "timeout", "timeout_seconds": timeout, "error_type": "TimeoutError"}
            _tasks[task_id]["detail"] = detail
            await _persist_update_with_retry(task_id, status="failed", error=error, detail=detail)
        except Exception as e:
            error = str(e) or e.__class__.__name__ or "后台任务失败，未返回具体错误"
            detail = {"stage": "failed", "error_type": e.__class__.__name__}
            _tasks[task_id]["status"] = "failed"
            _tasks[task_id]["error"] = error
            _tasks[task_id]["detail"] = detail
            await _persist_update_with_retry(task_id, status="failed", error=error, detail=detail)
        finally:
            _tasks[task_id]["updated_at"] = _now()

    asyncio.create_task(_runner())
    return task_id


def get_task(task_id: str) -> dict | None:
    return _tasks.get(task_id)


async def get_task_persisted(task_id: str) -> dict | None:
    if task_id in _tasks:
        return _tasks[task_id]
    async with async_session() as db:
        task = (await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))).scalar_one_or_none()
        return _format_db_task(task) if task else None


async def recover_interrupted_tasks() -> int:
    """Mark persisted running tasks as interrupted after a process restart."""
    async with async_session() as db:
        tasks = (await db.execute(
            select(GenerationTask).where(GenerationTask.status.in_(["running", "cancelling"]))
        )).scalars().all()
        for task in tasks:
            if str(task.id) in _tasks:
                continue
            task.status = "failed"
            task.error_message = INTERRUPTED_BY_RESTART
            config = task.precision_config or {}
            config["progress_label"] = INTERRUPTED_BY_RESTART
            detail = config.get("detail") or {}
            detail["interrupted_reason"] = "process_restart"
            config["detail"] = detail
            task.precision_config = config
        if tasks:
            await db.commit()
        return len(tasks)


def update_progress(task_id: str, progress: float, label: str = "", detail: dict | None = None):
    if task_id in _tasks:
        _tasks[task_id]["progress"] = progress
        _tasks[task_id]["progress_label"] = label
        if detail is not None:
            _tasks[task_id]["detail"] = detail
        _tasks[task_id]["updated_at"] = _now()
    _schedule_retry(lambda: _persist_update(task_id, progress=progress, progress_label=label, detail=detail or {}))


def cancel_task(task_id: str):
    if task_id in _tasks and _tasks[task_id]["status"] == "running":
        _tasks[task_id]["status"] = "cancelling"
        _tasks[task_id]["updated_at"] = _now()
        _schedule_retry(lambda: _persist_update(task_id, status="cancelling"))
        return True
    return False


def is_cancelled(task_id: str) -> bool:
    return _tasks.get(task_id, {}).get("status") in ("cancelling", "cancelled")


def list_tasks(project_id: str | None = None) -> list[dict]:
    tasks = list(_tasks.values())
    if project_id:
        tasks = [t for t in tasks if t.get("project_id") == project_id]
    return sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)


async def list_tasks_persisted(project_id: str | None = None) -> list[dict]:
    async with async_session() as db:
        stmt = select(GenerationTask)
        if project_id:
            stmt = stmt.where(GenerationTask.project_id == project_id)
        stmt = stmt.order_by(GenerationTask.created_at.desc())
        persisted = [_format_db_task(t) for t in (await db.execute(stmt)).scalars().all()]
    by_id = {t["id"]: t for t in persisted}
    for task in list_tasks(project_id):
        by_id[task["id"]] = {**by_id.get(task["id"], {}), **task}
    for task_id, task in list(by_id.items()):
        if task.get("status") in {"running", "cancelling"} and task_id not in _tasks:
            task["status"] = "failed"
            task["error"] = task.get("error") or INTERRUPTED_BY_RESTART
            task["progress_label"] = INTERRUPTED_BY_RESTART
            detail = task.get("detail") or {}
            detail["interrupted_reason"] = "process_restart"
            task["detail"] = detail
    return _dedupe_task_list(sorted(by_id.values(), key=lambda t: t.get("created_at", ""), reverse=True))
