from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMMessage:
    role: str
    content: str


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_json(self, messages: list[LLMMessage], system: str = "", temperature: float = 0.5, max_tokens: int = 4096) -> dict:
        ...
