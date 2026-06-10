from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from app.database import async_session
from app.models.llm_call_log import LLMCallLog


_llm_context: ContextVar[dict[str, Any]] = ContextVar("llm_call_context", default={})


@contextmanager
def llm_call_context(**kwargs):
    current = dict(_llm_context.get() or {})
    current.update({k: v for k, v in kwargs.items() if v not in (None, "")})
    token = _llm_context.set(current)
    try:
        yield
    finally:
        _llm_context.reset(token)


def get_llm_call_context() -> dict[str, Any]:
    return dict(_llm_context.get() or {})


def _clip(text: Any, limit: int = 600000) -> str:
    value = "" if text is None else str(text)
    return value if len(value) <= limit else value[:limit] + "\n...[truncated]"


async def record_llm_call(
    *,
    provider: Any,
    request_type: str,
    system_prompt: str,
    prompt: str,
    response_content: str = "",
    status: str = "success",
    error_message: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    duration_ms: int = 0,
    temperature: float | str = "",
    max_tokens: int = 0,
    request_payload: dict | None = None,
    response_metadata: dict | None = None,
) -> None:
    context = get_llm_call_context()
    try:
        async with async_session() as db:
            db.add(
                LLMCallLog(
                    project_id=context.get("project_id") or None,
                    project_name=_clip(context.get("project_name") or context.get("title") or "", 200),
                    task_id=_clip(context.get("task_id") or "", 36),
                    function_name=_clip(context.get("function_name") or "", 100),
                    provider_id=_clip(getattr(provider, "provider_id", "") or "", 36),
                    provider_name=_clip(getattr(provider, "provider_name", "") or "", 100),
                    provider_type=_clip(getattr(provider, "provider_type", "") or "", 30),
                    model_name=_clip(getattr(provider, "model", "") or "", 120),
                    request_type=_clip(request_type or "chat", 30),
                    status=_clip(status or "success", 20),
                    system_prompt=_clip(system_prompt),
                    prompt=_clip(prompt),
                    response_content=_clip(response_content),
                    error_message=_clip(error_message),
                    input_tokens=int(input_tokens or 0),
                    output_tokens=int(output_tokens or 0),
                    total_tokens=int(total_tokens or input_tokens or 0) if not output_tokens else int(total_tokens or input_tokens + output_tokens),
                    duration_ms=int(duration_ms or 0),
                    temperature=str(temperature or ""),
                    max_tokens=int(max_tokens or 0),
                    request_payload=request_payload or {},
                    response_metadata=response_metadata or {},
                )
            )
            await db.commit()
    except Exception:
        # Logging must never break generation.
        return
