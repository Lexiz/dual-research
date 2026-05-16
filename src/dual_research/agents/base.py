from __future__ import annotations

import asyncio
import logging
import os
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, TextIO, TypeVar, runtime_checkable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentError(RuntimeError):
    pass


def web_search_enabled() -> bool:
    """Web search is on by default. Set DUAL_RESEARCH_NO_WEB_SEARCH=1 to disable."""
    return os.environ.get("DUAL_RESEARCH_NO_WEB_SEARCH", "").strip().lower() not in ("1", "true", "yes")


def cache_enabled() -> bool:
    """Prompt caching is on by default. Set DUAL_RESEARCH_NO_CACHE=1 to disable."""
    return os.environ.get("DUAL_RESEARCH_NO_CACHE", "").strip().lower() not in ("1", "true", "yes")


def _is_rate_limit(exc: Exception) -> bool:
    try:
        import anthropic
        if isinstance(exc, anthropic.RateLimitError):
            return True
    except ImportError:
        pass
    try:
        import openai
        if isinstance(exc, openai.RateLimitError):
            return True
    except ImportError:
        pass
    return getattr(exc, "status_code", None) == 429


def _extract_retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


async def with_rate_limit_retry(
    call: Callable[[], Awaitable[T]],
    *,
    agent_label: str,
    max_attempts: int = 3,
    base_backoff_seconds: float = 30.0,
    min_sleep: float = 5.0,
    max_sleep: float = 300.0,
) -> T:
    """Retry `call()` on 429. Honours Retry-After; falls back to exponential
    backoff with jitter. Clamps sleeps to [min_sleep, max_sleep]."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await call()
        except Exception as e:
            if not _is_rate_limit(e):
                raise
            last_exc = e
            if attempt == max_attempts - 1:
                break
            header_sleep = _extract_retry_after(e)
            if header_sleep is None:
                header_sleep = base_backoff_seconds * (2 ** attempt) + random.uniform(0, 5)
            sleep_for = max(min_sleep, min(max_sleep, header_sleep))
            logger.warning(
                "rate_limit on %s (attempt %d/%d); sleeping %.1fs",
                agent_label,
                attempt + 1,
                max_attempts,
                sleep_for,
            )
            await asyncio.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc


@dataclass(frozen=True)
class TokenUsage:
    """Per-call token accounting.

    Spec 0039 split ``cache_write_tokens`` by TTL tier so the 1h-cache
    write rate (2× input) can be priced separately from the 5m rate
    (1.25× input). The aggregate ``cache_write_tokens`` field is
    preserved as the sum so transcripts written by older versions still
    deserialise unchanged. Agents enforce
    ``cache_write_tokens == cache_write_5m_tokens + cache_write_1h_tokens``;
    when only the aggregate is available (older response shapes), it is
    credited entirely to the 5m bucket (the pre-beta default).
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_write_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            cache_write_5m_tokens=self.cache_write_5m_tokens + other.cache_write_5m_tokens,
            cache_write_1h_tokens=self.cache_write_1h_tokens + other.cache_write_1h_tokens,
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
        audit_context: dict | None = None,
    ) -> AgentResult: ...
