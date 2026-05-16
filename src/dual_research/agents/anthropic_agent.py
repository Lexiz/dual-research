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
from dual_research.agents.pricing import compute_full_cost
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT


WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 10,
}

# 1-hour cache TTL via the extended-cache-ttl-2025-04-11 beta.
# Falls back to the default 5-minute TTL if the beta is rejected by the API.
#
# Spec 0039 prices the 1h tier at 2× input (vs 1.25× for 5m); the longer
# TTL is deliberately chosen because our multi-round phases re-read the
# same drafts/plans across 30+ minutes of wall time, where the 5m tier
# would expire mid-phase. Anthropic reports the per-TTL token split on
# the response (``usage.cache_creation.ephemeral_5m_input_tokens`` /
# ``ephemeral_1h_input_tokens``) so we can price each tier exactly.
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
        audit_context: dict | None = None,
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
        cw_total = getattr(u, "cache_creation_input_tokens", 0) or 0
        cc = getattr(u, "cache_creation", None)
        if cc is not None:
            cw_5m = getattr(cc, "ephemeral_5m_input_tokens", 0) or 0
            cw_1h = getattr(cc, "ephemeral_1h_input_tokens", 0) or 0
        else:
            # Older response shape (or the beta was rejected) — credit the
            # aggregate to the 5m bucket. Matches pre-beta API behaviour.
            cw_5m = cw_total
            cw_1h = 0
        if cw_total and cw_5m + cw_1h != cw_total:
            # Defensive: trust the per-TTL breakdown over the aggregate
            # (the API is the source of truth for the split). Logging
            # would be useful here but the agents stay quiet — pricing
            # already comes out right from the breakdown.
            pass
        usage = TokenUsage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=cw_5m + cw_1h,
            cache_write_5m_tokens=cw_5m,
            cache_write_1h_tokens=cw_1h,
        )
        searches = _count_web_searches(final_msg)
        text = "".join(text_parts)
        cost = compute_full_cost(self._spec.model_id, usage, searches)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # Spec 0036: when an audit_context is supplied AND web search
        # fired at least once, capture the per-turn audit payload
        # (queries + retrieved sources + citations with cited_text) so
        # the aggregator can persist it to session_dir/searches/.
        search_audit: dict | None = None
        if audit_context is not None and searches > 0:
            try:
                from dual_research.audit import normalize_anthropic_search_audit, audit_to_dict
                audit_obj = normalize_anthropic_search_audit(
                    final_msg,
                    turn_key=str(audit_context.get("turn_key", "")),
                    phase=str(audit_context.get("phase", "")),
                    agent=str(audit_context.get("agent", self.label)),
                    label=str(audit_context.get("label", "")),
                )
                search_audit = audit_to_dict(audit_obj)
            except Exception:
                # Defensive — never fail the call because of audit capture.
                search_audit = None

        extras: dict = {
            "stop_reason": getattr(final_msg, "stop_reason", None),
            "searches": searches,
        }
        if search_audit is not None:
            extras["search_audit"] = search_audit

        return AgentResult(
            text=text,
            usage=usage,
            cost_usd=cost,
            duration_ms=duration_ms,
            model_id=final_msg.model or self._spec.model_id,
            provider=self.provider,
            label=self.label,
            extras=extras,
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
