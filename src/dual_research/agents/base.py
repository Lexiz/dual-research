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


def _is_transient_error(exc: Exception) -> bool:
    """Transient network / streaming / server errors worth retrying.

    Most commonly: ``httpx.ReadError`` from a streaming response whose
    underlying TCP connection dropped mid-stream. The Anthropic and
    OpenAI SDKs DON'T retry these — their ``max_retries`` parameter only
    covers non-streaming requests, and once a streaming response has
    begun, the SDK hands the raw httpx stream to the caller. Without
    explicit retry here, a single transient network blip in the middle
    of a multi-minute phase-1 turn kills the whole run.

    Also catches 5xx server errors (which the SDKs likewise don't retry
    for streaming) and the SDK-wrapped ``APIConnectionError`` (which
    fires before any bytes have been streamed)."""
    # Underlying httpx-level network/protocol errors. These bubble up
    # raw through the SDK's streaming code path.
    try:
        import httpx
        if isinstance(exc, (
            httpx.ReadError,
            httpx.WriteError,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
        )):
            return True
    except ImportError:
        pass
    # SDK-wrapped connection errors (pre-stream-start failures).
    try:
        import anthropic
        if isinstance(exc, anthropic.APIConnectionError):
            return True
    except ImportError:
        pass
    try:
        import openai
        if isinstance(exc, openai.APIConnectionError):
            return True
    except ImportError:
        pass
    # 5xx server errors — transient by definition; retry.
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and 500 <= status < 600:
        return True
    return False


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
    transient_max_attempts: int = 4,
    transient_base_backoff_seconds: float = 2.0,
    transient_min_sleep: float = 1.0,
    transient_max_sleep: float = 30.0,
) -> T:
    """Retry ``call()`` on 429 OR transient network/streaming errors.

    Two distinct retry profiles share one loop:

    - **Rate-limit (429)**: honours ``Retry-After``; falls back to
      exponential backoff with jitter; long sleeps (30–300 s) because
      the upstream provider is throttling us deliberately.
    - **Transient (httpx.ReadError, APIConnectionError, 5xx, …)**: short,
      aggressive backoff (1–30 s) because network blips clear quickly.
      Streaming responses that drop mid-flight are the dominant cause
      of this branch — they used to kill multi-minute phase turns
      outright; now they retry transparently.

    Each error class has its own attempt budget, so a run that gets one
    rate-limit early doesn't burn the transient-error budget and vice
    versa."""
    last_exc: Exception | None = None
    rate_limit_attempts = 0
    transient_attempts = 0
    while True:
        try:
            return await call()
        except Exception as e:
            is_rate_limit = _is_rate_limit(e)
            is_transient = _is_transient_error(e) and not is_rate_limit
            if not (is_rate_limit or is_transient):
                raise
            last_exc = e

            if is_rate_limit:
                rate_limit_attempts += 1
                if rate_limit_attempts >= max_attempts:
                    break
                header_sleep = _extract_retry_after(e)
                if header_sleep is None:
                    header_sleep = base_backoff_seconds * (2 ** (rate_limit_attempts - 1)) + random.uniform(0, 5)
                sleep_for = max(min_sleep, min(max_sleep, header_sleep))
                logger.warning(
                    "rate_limit on %s (attempt %d/%d); sleeping %.1fs",
                    agent_label, rate_limit_attempts, max_attempts, sleep_for,
                )
            else:  # transient
                transient_attempts += 1
                if transient_attempts >= transient_max_attempts:
                    break
                raw_sleep = transient_base_backoff_seconds * (2 ** (transient_attempts - 1)) + random.uniform(0, 2)
                sleep_for = max(transient_min_sleep, min(transient_max_sleep, raw_sleep))
                logger.warning(
                    "transient %s on %s (attempt %d/%d); sleeping %.1fs",
                    type(e).__name__, agent_label,
                    transient_attempts, transient_max_attempts, sleep_for,
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
