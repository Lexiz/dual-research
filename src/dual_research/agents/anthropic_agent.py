from __future__ import annotations

import time
from typing import Any, TextIO

import anthropic
from anthropic import AsyncAnthropic

from dual_research.agents.base import (
    AgentError,
    AgentResult,
    TokenUsage,
    cache_enabled,
    web_search_enabled,
    with_rate_limit_retry,
)
from dual_research.agents.pricing import compute_cost
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT


WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 10,
}

# 1-hour cache TTL via the extended-cache-ttl-2025-04-11 beta.
# Falls back to the default 5-minute TTL if the beta is rejected by the API.
EXTENDED_CACHE_TTL_BETA = "extended-cache-ttl-2025-04-11"


class ClaudeAgent:
    provider = "anthropic"
    label = "claude"

    def __init__(self, *, api_key: str, spec: ModelSpec):
        if spec.provider != "anthropic":
            raise ValueError(f"ClaudeAgent requires an anthropic ModelSpec, got provider={spec.provider!r}")
        self._spec = spec
        headers = dict(spec.extra_headers) if spec.extra_headers else {}
        if cache_enabled():
            # Merge cache beta into existing anthropic-beta header if present.
            existing = headers.get("anthropic-beta", "")
            betas = [b.strip() for b in existing.split(",") if b.strip()]
            if EXTENDED_CACHE_TTL_BETA not in betas:
                betas.append(EXTENDED_CACHE_TTL_BETA)
            headers["anthropic-beta"] = ",".join(betas)
        self._client = AsyncAnthropic(
            api_key=api_key,
            default_headers=headers,
            max_retries=3,
            timeout=600.0,
        )

    @property
    def model_id(self) -> str:
        return self._spec.model_id

    async def run(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 8192,
        stream_to: TextIO | None = None,
        stream_prefix: str = "",
    ) -> AgentResult:
        start = time.perf_counter()
        text_parts: list[str] = []
        first_token = True
        kwargs: dict = {
            "model": self._spec.model_id,
            "max_tokens": max_output_tokens,
            "messages": [{"role": "user", "content": _build_content(prompt)}],
        }
        if web_search_enabled():
            kwargs["tools"] = [WEB_SEARCH_TOOL]

        async def _do_call():
            nonlocal text_parts, first_token
            text_parts = []
            first_token = True
            async with self._client.messages.stream(**kwargs) as stream:
                async for delta in stream.text_stream:
                    text_parts.append(delta)
                    if stream_to is not None:
                        if first_token and stream_prefix:
                            stream_to.write(stream_prefix)
                            first_token = False
                        stream_to.write(delta)
                        stream_to.flush()
                return await stream.get_final_message()

        try:
            final_msg = await with_rate_limit_retry(_do_call, agent_label=self.label)
        except anthropic.APIError as e:
            raise AgentError(f"Anthropic API error ({type(e).__name__}): {e}") from e

        if stream_to is not None and not first_token:
            stream_to.write("\n")
            stream_to.flush()

        u = final_msg.usage
        usage = TokenUsage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )
        searches = _count_web_searches(final_msg)
        text = "".join(text_parts)
        cost = compute_cost(self._spec.model_id, usage)
        duration_ms = int((time.perf_counter() - start) * 1000)

        return AgentResult(
            text=text,
            usage=usage,
            cost_usd=cost,
            duration_ms=duration_ms,
            model_id=final_msg.model or self._spec.model_id,
            provider=self.provider,
            label=self.label,
            extras={
                "stop_reason": getattr(final_msg, "stop_reason", None),
                "searches": searches,
            },
        )


def _count_web_searches(message) -> int:
    """Count `server_tool_use` web_search blocks in the final message content."""
    n = 0
    for block in getattr(message, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "server_tool_use" and getattr(block, "name", None) == "web_search":
            n += 1
    return n


def _build_content(prompt: str) -> Any:
    """Split a prompt on CACHE_BREAKPOINT and apply cache_control.

    When the marker is absent OR cache is disabled, return the plain string
    (Anthropic accepts either str or a list of content blocks).
    """
    if not cache_enabled() or CACHE_BREAKPOINT not in prompt:
        return prompt.replace(CACHE_BREAKPOINT, "")

    prefix, suffix = prompt.split(CACHE_BREAKPOINT, 1)
    return [
        {
            "type": "text",
            "text": prefix,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        },
        {"type": "text", "text": suffix},
    ]
