from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TextIO, runtime_checkable


class AgentError(RuntimeError):
    pass


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_write_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )


@dataclass(frozen=True)
class AgentResult:
    text: str
    usage: TokenUsage
    cost_usd: float
    duration_ms: int
    model_id: str
    provider: str
    label: str
    extras: dict[str, Any] | None = None


@runtime_checkable
class AgentCall(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def provider(self) -> str: ...

    async def run(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 8192,
        stream_to: TextIO | None = None,
        stream_prefix: str = "",
    ) -> AgentResult: ...
