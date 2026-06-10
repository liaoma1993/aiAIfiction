import json
import httpx
from app.llm.base import BaseLLMProvider, LLMResponse, LLMMessage
from app.config import get_settings

LLM_READ_TIMEOUT_SECONDS = 3600.0


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model: str = None, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        settings = get_settings()
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> LLMResponse:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend([{"role": m.role, "content": m.content} for m in messages])

        timeout = httpx.Timeout(10.0, connect=10.0, read=LLM_READ_TIMEOUT_SECONDS, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens},
                )
            except httpx.TimeoutException as e:
                raise RuntimeError(f"LLM 请求超时（读取超过 {int(LLM_READ_TIMEOUT_SECONDS)} 秒）") from e
            if resp.status_code != 200:
                raise RuntimeError(f"API 返回 {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"LLM error: {data['error']}")
            if "choices" not in data:
                raise RuntimeError(f"API 返回异常: {json.dumps(data, ensure_ascii=False)[:300]}")
            choice = data["choices"][0]
            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", self.model),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", ""),
            )

    async def chat_json(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.5, max_tokens: int = 4096) -> dict:
        resp = await self.chat(messages, system, temperature, max_tokens)
        content = resp.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)
