from __future__ import annotations

import json
import logging
import time
from typing import Any, TextIO

import anthropic
from anthropic import AsyncAnthropic

from dual_research.agents.base import (
    AgentError,
    AgentResult,
    TokenUsage,
    append_usage_debug,
    cache_enabled,
    web_search_enabled,
    with_rate_limit_retry,
)
from dual_research.agents.pricing import compute_full_cost
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT

logger = logging.getLogger(__name__)

# Spec 0143 §3.1 Step 3 — emit at most one "cache was intended but didn't
# engage" warning per process. The signal is high-value but noisy if every
# call logs it; the goal is "future regression is one log line away from
# observable," not "spam the console for every turn."
_CACHE_NON_ENGAGEMENT_WARNED = False


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

# Spec 0218 §3.4 — unlock 16K+ output tokens on Claude. Without this beta
# header the API caps responses at 8192 output tokens regardless of the
# `max_tokens` request value, which is the root cause of the phase-4
# STATUS-truncation regression. The beta only affects the output cap;
# cache + input semantics are unchanged.
OUTPUT_128K_BETA = "output-128k-2025-02-19"


class ClaudeAgent:
    provider = "anthropic"
    label = "claude"

    def __init__(self, *, api_key: str, spec: ModelSpec):
        if spec.provider != "anthropic":
            raise ValueError(f"ClaudeAgent requires an anthropic ModelSpec, got provider={spec.provider!r}")
        self._spec = spec
        headers = dict(spec.extra_headers) if spec.extra_headers else {}
        existing = headers.get("anthropic-beta", "")
        betas = [b.strip() for b in existing.split(",") if b.strip()]
        if cache_enabled() and EXTENDED_CACHE_TTL_BETA not in betas:
            betas.append(EXTENDED_CACHE_TTL_BETA)
        if OUTPUT_128K_BETA not in betas:
            betas.append(OUTPUT_128K_BETA)
        if betas:
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
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        # Spec 0148 D11 — defensive capture of extended-thinking
        # ``thinking_tokens``. Absent on the response (or 0) when
        # extended-thinking is not enabled in the model config, which
        # is the current production state; field is forward-ready for
        # when it gets turned on.
        thinking_tokens = getattr(u, "thinking_tokens", 0) or 0
        usage = TokenUsage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=cache_read,
            cache_write_tokens=cw_5m + cw_1h,
            cache_write_5m_tokens=cw_5m,
            cache_write_1h_tokens=cw_1h,
            reasoning_tokens=thinking_tokens,
        )
        searches = _count_web_searches(final_msg)
        text = "".join(text_parts)
        cost = compute_full_cost(self._spec.model_id, usage, searches)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # Spec 0143 §3.1 Step 3 — if cache_control was intended but the
        # API returned zero cache fields across the board, surface a
        # one-shot warning. Anchor-run data (Notion B03) hit this shape:
        # every Claude call recorded 0 cache_read/write AND the cost
        # matched plain input-rate arithmetic, proving cache_control
        # never engaged on the wire. The warning makes the next
        # regression observable from logs alone.
        cache_intended = cache_enabled() and CACHE_BREAKPOINT in prompt
        if cache_intended and cache_read == 0 and cw_total == 0:
            global _CACHE_NON_ENGAGEMENT_WARNED
            if not _CACHE_NON_ENGAGEMENT_WARNED:
                _CACHE_NON_ENGAGEMENT_WARNED = True
                logger.warning(
                    "anthropic cache_control intended but did not engage "
                    "(model=%s, input_tokens=%d, prompt_chars=%d). "
                    "Set DUAL_RESEARCH_DEBUG_USAGE=1 on the next run to "
                    "dump raw usage payloads to <session>/usage-debug.jsonl.",
                    self._spec.model_id, usage.input_tokens, len(prompt),
                )

        # Spec 0143 §3.1 Step 3 — best-effort raw-usage capture (off by
        # default; gated by DUAL_RESEARCH_DEBUG_USAGE). The audit_context
        # carries the session dir on every production call.
        if audit_context is not None:
            append_usage_debug(
                session_dir=audit_context.get("session_dir"),
                provider=self.provider,
                model_id=self._spec.model_id,
                label=str(audit_context.get("label", "")),
                usage_payload=u,
                extra={
                    "cache_intended": cache_intended,
                    "stop_reason": getattr(final_msg, "stop_reason", None),
                    "searches": searches,
                },
            )

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

        # Spec 0148 D14 — tool-definitions JSON, captured for the
        # ``system.tool_definitions`` row on the Consumption card. Only
        # present when web_search is enabled (the only tool we ship);
        # absent → key never lands in prompt_pieces → no row renders.
        if web_search_enabled():
            extras["tool_definitions_text"] = json.dumps(
                [WEB_SEARCH_TOOL], sort_keys=True
            )

        # Spec 0148 D13 — concatenated text of every web_search_tool_result
        # block returned this turn. The provider feeds search snippets
        # back to the model mid-generation; those snippets contribute
        # to the turn's input-token bill but the spec-0145 emitter
        # never broke them out as a piece. Surfaces a real
        # ``system.web_sources`` row on the Consumption card.
        if searches > 0:
            ws_text = _concat_web_search_results(final_msg)
            if ws_text:
                extras["web_sources_text"] = ws_text

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


def _concat_web_search_results(message) -> str:
    """Spec 0148 D13 — concatenate the text of every web_search_tool_result
    block on the final message.

    Anthropic returns each search result as a ``web_search_tool_result``
    content block whose ``content`` is a list of result objects with
    ``title`` / ``url`` / ``page_age`` / ``encrypted_content`` /
    ``type`` fields. Encrypted_content is opaque so we approximate the
    snippet bill by concatenating the surfaced title + url for each
    result; this under-counts the true token cost but produces a
    stable, deterministic input the token estimator can run over. If
    a future SDK exposes the decrypted snippet text, swap it in here.
    """
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) != "web_search_tool_result":
            continue
        results = getattr(block, "content", None) or []
        for r in results:
            title = getattr(r, "title", None) or ""
            url = getattr(r, "url", None) or ""
            if title or url:
                parts.append(f"{title}\n{url}")
    return "\n\n".join(parts)


def _build_content(prompt: str) -> Any:
    """Split a prompt on CACHE_BREAKPOINT markers and apply cache_control.

    Spec 0149 §5.3 (D02) — supports multiple CACHE_BREAKPOINT markers in a
    single prompt. Anthropic accepts up to four cache_control breakpoints
    and matches the longest stable prefix. Phase 2 / 3 / 4 prompts emit two
    markers (one after the brief, one after the drafts) so cache_read still
    engages when later-positioned content (e.g. the current draft in Phase 4)
    changes between rounds but the brief stays stable.

    When no marker is present OR cache is disabled, return the plain string
    (Anthropic accepts either str or a list of content blocks).
    """
    if not cache_enabled() or CACHE_BREAKPOINT not in prompt:
        return prompt.replace(CACHE_BREAKPOINT, "")

    chunks = prompt.split(CACHE_BREAKPOINT)
    blocks: list[dict] = []
    for i, chunk in enumerate(chunks):
        block: dict = {"type": "text", "text": chunk}
        if i < len(chunks) - 1:
            block["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
        blocks.append(block)
    return blocks
