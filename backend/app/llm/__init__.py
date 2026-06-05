import threading
import time
import httpx
from sqlalchemy import select
from app.llm.openai_provider import OpenAIProvider
from app.llm.base import LLMResponse
from app.config import get_settings

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
                    "model": r.model,
                    "api_key": r.api_key,
                    "base_url": r.base_url or "https://api.openai.com/v1",
                    "provider_type": r.provider_type,
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
    def __init__(self, model: str = None, api_key: str = None):
        settings = get_settings()
        super().__init__(
            model=model or settings.CLAUDE_MODEL,
            api_key=api_key or settings.CLAUDE_API_KEY,
            base_url="https://api.anthropic.com/v1",
        )

    async def chat(self, messages, system="", temperature=0.7, max_tokens=4096):
        msgs = [{"role": "system", "content": system}] if system else []
        msgs.extend([{"role": m.role, "content": m.content} for m in messages])
        timeout = httpx.Timeout(10.0, connect=10.0, read=300.0, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": self.model, "messages": msgs, "max_tokens": max_tokens, "temperature": temperature},
            )
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"Claude error: {data['error']}")
            content = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
            return LLMResponse(
                content=content, model=data.get("model", self.model),
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason", ""),
            )


async def get_llm(prefer: str = "openai") -> OpenAIProvider:
    providers = get_cached_providers()
    if providers:
        if prefer == "claude":
            claude = next((p for p in providers if p["provider_type"] == "claude"), None)
            if claude and claude["api_key"]:
                return ClaudeProvider(model=claude["model"], api_key=claude["api_key"])
        p = providers[0]
        return OpenAIProvider(model=p["model"], api_key=p["api_key"], base_url=p["base_url"])

    settings = get_settings()
    if prefer == "claude" and settings.CLAUDE_API_KEY:
        return ClaudeProvider()
    if settings.OPENAI_API_KEY:
        return OpenAIProvider()
    if settings.DEEPSEEK_API_KEY:
        return OpenAIProvider(model=settings.DEEPSEEK_MODEL, api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    raise RuntimeError("没有可用的 LLM 配置。请在「模型管理」中添加供应商，或设置 OPENAI_API_KEY 环境变量。")
