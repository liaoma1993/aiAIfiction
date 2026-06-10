import json
import time
import httpx
from app.llm.base import BaseLLMProvider, LLMResponse, LLMMessage
from app.config import get_settings
from app.services.llm_call_logger import record_llm_call

LLM_READ_TIMEOUT_SECONDS = 3600.0


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model: str = None, api_key: str = None, base_url: str = "https://api.openai.com/v1", provider_id: str = "", provider_name: str = "", provider_type: str = "openai"):
        settings = get_settings()
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url.rstrip("/")
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.provider_type = provider_type

    async def chat(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> LLMResponse:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend([{"role": m.role, "content": m.content} for m in messages])

        timeout = httpx.Timeout(10.0, connect=10.0, read=LLM_READ_TIMEOUT_SECONDS, write=30.0, pool=5.0)
        started = time.perf_counter()
        prompt_text = "\n\n".join(f"{m['role']}:\n{m['content']}" for m in msgs)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens},
                )
            except httpx.TimeoutException as e:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"LLM 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload={"messages": msgs},
                )
                raise RuntimeError(f"LLM 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）") from e
            if resp.status_code != 200:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"API 返回 {resp.status_code}: {resp.text[:1000]}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload={"messages": msgs},
                    response_metadata={"status_code": resp.status_code},
                )
                raise RuntimeError(f"API 返回 {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            if "error" in data:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"LLM error: {data['error']}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload={"messages": msgs},
                    response_metadata={"raw_error": data.get("error")},
                )
                raise RuntimeError(f"LLM error: {data['error']}")
            if "choices" not in data:
                await record_llm_call(
                    provider=self,
                    request_type="chat",
                    system_prompt=system,
                    prompt=prompt_text,
                    status="failed",
                    error_message=f"API 返回异常: {json.dumps(data, ensure_ascii=False)[:1000]}",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_payload={"messages": msgs},
                    response_metadata=data,
                )
                raise RuntimeError(f"API 返回异常: {json.dumps(data, ensure_ascii=False)[:300]}")
            choice = data["choices"][0]
            usage = data.get("usage", {}) or {}
            content = choice["message"]["content"]
            input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
            output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
            total_tokens = usage.get("total_tokens", 0) or input_tokens + output_tokens
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
                request_payload={"messages": msgs},
                response_metadata={"finish_reason": choice.get("finish_reason", ""), "usage": usage, "model": data.get("model", self.model)},
            )
            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=choice.get("finish_reason", ""),
                metadata={"usage": usage},
            )

    async def chat_json(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.5, max_tokens: int = 4096) -> dict:
        resp = await self.chat(messages, system, temperature, max_tokens)
        content = resp.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)
