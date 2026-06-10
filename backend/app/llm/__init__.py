import threading
import time
import httpx
from sqlalchemy import select
from app.llm.openai_provider import OpenAIProvider
from app.llm.base import LLMResponse
from app.config import get_settings
from app.services.llm_call_logger import record_llm_call

LLM_READ_TIMEOUT_SECONDS = 3600.0

_cache: list[dict] = []
_cache_lock = threading.Lock()
_cache_ts = 0.0
CACHE_TTL = 30


def refresh_provider_cache():
    global _cache, _cache_ts
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_async_refresh())
            return
    except RuntimeError:
        pass
    import asyncio as aio
    aio.run(_async_refresh())


async def async_refresh_provider_cache():
    await _async_refresh()


async def _async_refresh():
    global _cache, _cache_ts
    try:
        from app.database import async_session
        from app.models.llm_provider import LLMProvider
        async with async_session() as session:
            result = await session.execute(
                select(LLMProvider).where(LLMProvider.is_active == True).order_by(LLMProvider.sort_order)
            )
            rows = result.scalars().all()
            _cache = [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "model": r.model,
                    "api_key": r.api_key,
                    "base_url": r.base_url or "https://api.openai.com/v1",
                    "provider_type": r.provider_type,
                    "sort_order": r.sort_order or 0,
                }
                for r in rows
            ]
            _cache_ts = time.time()
    except Exception:
        pass


def get_cached_providers() -> list[dict]:
    global _cache, _cache_ts
    if not _cache or time.time() - _cache_ts > CACHE_TTL:
        refresh_provider_cache()
    return _cache


class ClaudeProvider(OpenAIProvider):
    def __init__(self, model: str = None, api_key: str = None, provider_id: str = "", provider_name: str = ""):
        settings = get_settings()
        super().__init__(
            model=model or settings.CLAUDE_MODEL,
            api_key=api_key or settings.CLAUDE_API_KEY,
            base_url="https://api.anthropic.com/v1",
            provider_id=provider_id,
            provider_name=provider_name,
            provider_type="claude",
        )

    async def chat(self, messages, system="", temperature=0.7, max_tokens=4096):
        msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        timeout = httpx.Timeout(10.0, connect=10.0, read=LLM_READ_TIMEOUT_SECONDS, write=30.0, pool=5.0)
        started = time.perf_counter()
        prompt_text = ("\n\nsystem:\n" + system if system else "") + "\n\n" + "\n\n".join(f"{m['role']}:\n{m['content']}" for m in msgs)
        payload = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json=payload,
                )
            except httpx.TimeoutException as e:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Claude 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                )
                raise RuntimeError(f"Claude 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）") from e
            data = resp.json()
            if resp.status_code != 200:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Claude API 返回 {resp.status_code}: {str(data)[:1000]}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                    response_metadata={"status_code": resp.status_code},
                )
                raise RuntimeError(f"Claude API 返回 {resp.status_code}: {str(data)[:300]}")
            if "error" in data:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Claude error: {data['error']}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                    response_metadata={"raw_error": data.get("error")},
                )
                raise RuntimeError(f"Claude error: {data['error']}")
            content = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
            usage = data.get("usage", {}) or {}
            input_tokens = usage.get("input_tokens", 0) or 0
            output_tokens = usage.get("output_tokens", 0) or 0
            total_tokens = input_tokens + output_tokens
            await record_llm_call(
                provider=self,
                request_type="chat",
                system_prompt=system,
                prompt=prompt_text,
                response_content=content,
                status="success",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                duration_ms=int((time.perf_counter() - started) * 1000),
                temperature=temperature,
                max_tokens=max_tokens,
                request_payload=payload,
                response_metadata={"finish_reason": data.get("stop_reason", ""), "usage": usage, "model": data.get("model", self.model)},
            )
            return LLMResponse(
                content=content, model=data.get("model", self.model),
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=data.get("stop_reason", ""),
                metadata={"usage": usage},
            )


class GeminiProvider(OpenAIProvider):
    def __init__(self, model: str = None, api_key: str = None, base_url: str = "", provider_id: str = "", provider_name: str = ""):
        settings = get_settings()
        self.model = model or settings.GEMINI_MODEL
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.provider_type = "gemini"

    async def chat(self, messages, system="", temperature=0.7, max_tokens=4096):
        parts = []
        if system:
            parts.append({"text": system})
        for msg in messages:
            parts.append({"text": msg.content})
        timeout = httpx.Timeout(10.0, connect=10.0, read=LLM_READ_TIMEOUT_SECONDS, write=30.0, pool=5.0)
        url = f"{self.base_url}/models/{self.model}:generateContent"
        started = time.perf_counter()
        prompt_text = "\n\n".join(part.get("text", "") for part in parts)
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                )
            except httpx.TimeoutException as e:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Gemini 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                )
                raise RuntimeError(f"Gemini 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）") from e
            data = resp.json()
            if resp.status_code != 200:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Gemini API 返回 {resp.status_code}: {str(data)[:1000]}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                    response_metadata={"status_code": resp.status_code},
                )
                raise RuntimeError(f"Gemini API 返回 {resp.status_code}: {str(data)[:300]}")
            if "error" in data:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"Gemini error: {data['error']}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload=payload,
                    response_metadata={"raw_error": data.get("error")},
                )
                raise RuntimeError(f"Gemini error: {data['error']}")
            candidate = (data.get("candidates") or [{}])[0]
            content = "".join(
                part.get("text", "")
                for part in (candidate.get("content", {}) or {}).get("parts", [])
            )
            usage = data.get("usageMetadata", {}) or {}
            input_tokens = usage.get("promptTokenCount", 0) or 0
            output_tokens = usage.get("candidatesTokenCount", 0) or 0
            total_tokens = usage.get("totalTokenCount", 0) or input_tokens + output_tokens
            await record_llm_call(
                provider=self,
                request_type="chat",
                system_prompt=system,
                prompt=prompt_text,
                response_content=content,
                status="success",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                duration_ms=int((time.perf_counter() - started) * 1000),
                temperature=temperature,
                max_tokens=max_tokens,
                request_payload=payload,
                response_metadata={"finish_reason": candidate.get("finishReason", ""), "usage": usage, "model": self.model},
            )
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=candidate.get("finishReason", ""),
                metadata={"usage": usage},
            )


def _provider_from_config(provider: dict) -> OpenAIProvider:
    provider_type = (provider.get("provider_type") or "openai").lower()
    model = provider.get("model") or None
    api_key = provider.get("api_key") or None
    base_url = provider.get("base_url") or ""
    if provider_type == "claude":
        return ClaudeProvider(model=model, api_key=api_key, provider_id=provider.get("id") or "", provider_name=provider.get("name") or "")
    if provider_type == "gemini":
        return GeminiProvider(model=model, api_key=api_key, base_url=base_url, provider_id=provider.get("id") or "", provider_name=provider.get("name") or "")
    if provider_type == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com/v1"
    return OpenAIProvider(model=model, api_key=api_key, base_url=base_url or "https://api.openai.com/v1", provider_id=provider.get("id") or "", provider_name=provider.get("name") or "", provider_type=provider_type)


async def get_llm(prefer: str = "openai") -> OpenAIProvider:
    providers = get_cached_providers()
    if providers:
        preferred = next((p for p in providers if p.get("provider_type") == prefer and p.get("api_key")), None)
        return _provider_from_config(preferred or providers[0])

    settings = get_settings()
    if prefer == "claude" and settings.CLAUDE_API_KEY:
        return ClaudeProvider(provider_name="环境变量 Claude")
    if prefer == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(provider_name="环境变量 Gemini")
    if settings.OPENAI_API_KEY:
        return OpenAIProvider(provider_name="环境变量 OpenAI", provider_type="openai")
    if settings.DEEPSEEK_API_KEY:
        return OpenAIProvider(model=settings.DEEPSEEK_MODEL, api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1", provider_name="环境变量 DeepSeek", provider_type="deepseek")
    raise RuntimeError("没有可用的 LLM 配置。请在「模型管理」中添加供应商，或设置 OPENAI_API_KEY 环境变量。")
