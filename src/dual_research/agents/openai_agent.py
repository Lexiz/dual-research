from __future__ import annotations

import time
from typing import Any, TextIO

import openai
from openai import AsyncOpenAI

from dual_research.agents.base import (
    AgentError,
    AgentResult,
    TokenUsage,
    append_usage_debug,
    web_search_enabled,
    with_rate_limit_retry,
)
from dual_research.agents.pricing import compute_full_cost
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT


# Spec 0036: pin search_context_size=high so the model receives the
# richest available page-content per result before generating. Closes
# the bulk of the "hallucinated citations even though search ran"
# failure mode that the community thread documents on Responses API.
WEB_SEARCH_TOOL = {"type": "web_search", "search_context_size": "high"}

# Spec 0036: surfacing the full retrieval URL list (not just citations)
# requires the include parameter. Without it, action.sources is omitted
# and the audit's negative-space (retrieved but uncited) is lost.
WEB_SEARCH_INCLUDE = ["web_search_call.action.sources"]


class GptAgent:
    provider = "openai"
    label = "openai"

    def __init__(self, *, api_key: str, spec: ModelSpec):
        if spec.provider != "openai":
            raise ValueError(f"GptAgent requires an openai ModelSpec, got provider={spec.provider!r}")
        self._spec = spec
        self._client = AsyncOpenAI(
            api_key=api_key,
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
        """Use the Responses API with optional web_search tool.

        Chat Completions doesn't expose web_search; the Responses API does.
        Streaming events of interest:
          - response.output_text.delta : incremental text
          - response.completed         : final response object with usage
        """
        start = time.perf_counter()
        text_parts: list[str] = []
        first_token = True
        final_usage = None
        final_model = self._spec.model_id
        searches = 0

        # OpenAI Responses API caches prefixes automatically (≥1024 token shared
        # prefix) — no explicit markers needed. Strip the sentinel so the prompt
        # reaches the model without it.
        clean_prompt = prompt.replace(CACHE_BREAKPOINT, "")
        kwargs: dict[str, Any] = {
            "model": self._spec.model_id,
            "input": clean_prompt,
            "stream": True,
            "max_output_tokens": max_output_tokens,
        }
        if web_search_enabled():
            kwargs["tools"] = [WEB_SEARCH_TOOL]
            kwargs["include"] = list(WEB_SEARCH_INCLUDE)

        # Spec 0036: capture the fully-assembled Response object so the
        # audit normaliser sees `action.sources` + citation annotations
        # (which arrive in chunks during streaming but are present on
        # the response.completed payload).
        final_response: Any = None

        async def _do_call():
            nonlocal text_parts, first_token, final_usage, final_model, searches, final_response
            text_parts = []
            first_token = True
            final_usage = None
            searches = 0
            final_response = None
            stream = await self._client.responses.create(**kwargs)
            async for event in stream:
                et = getattr(event, "type", "")
                if et == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        text_parts.append(delta)
                        if stream_to is not None:
                            if first_token and stream_prefix:
                                stream_to.write(stream_prefix)
                                first_token = False
                            stream_to.write(delta)
                            stream_to.flush()
                elif et == "response.output_item.added":
                    item = getattr(event, "item", None)
                    if item is not None and getattr(item, "type", None) == "web_search_call":
                        searches += 1
                elif et in ("response.completed", "response.incomplete", "response.failed"):
                    resp = getattr(event, "response", None)
                    if resp is not None:
                        final_usage = getattr(resp, "usage", None) or final_usage
                        final_model = getattr(resp, "model", None) or final_model
                        final_response = resp

        try:
            await with_rate_limit_retry(_do_call, agent_label=self.label)
        except openai.APIError as e:
            raise AgentError(f"OpenAI API error ({type(e).__name__}): {e}") from e

        if stream_to is not None and not first_token:
            stream_to.write("\n")
            stream_to.flush()

        if final_usage is None:
            raise AgentError("OpenAI stream ended without usage payload")

        input_tokens_total = getattr(final_usage, "input_tokens", 0) or 0
        output_tokens = getattr(final_usage, "output_tokens", 0) or 0
        cached = 0
        details = getattr(final_usage, "input_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0
        # Spec 0143 §3.1 Step 2 — capture reasoning_tokens as an
        # informational breakdown. The Responses API already includes
        # reasoning tokens inside ``output_tokens`` (verified against the
        # anchor run's invoice — re-pricing the captured tokens at
        # OpenAI's published rates reconciles to invoice exactly, which
        # would not be possible if reasoning were missing). The field
        # exists for the spec 0146 Consumption-card "of which reasoning"
        # breakdown — DO NOT fold into pricing or it will double-bill.
        reasoning = 0
        out_details = getattr(final_usage, "output_tokens_details", None)
        if out_details is not None:
            reasoning = getattr(out_details, "reasoning_tokens", 0) or 0

        usage = TokenUsage(
            input_tokens=max(0, input_tokens_total - cached),
            output_tokens=output_tokens,
            cache_read_tokens=cached,
            cache_write_tokens=0,
            cache_write_5m_tokens=0,
            cache_write_1h_tokens=0,
            reasoning_tokens=reasoning,
        )
        text = "".join(text_parts)
        cost = compute_full_cost(self._spec.model_id, usage, searches)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # Spec 0036: when an audit_context is supplied AND web search
        # fired at least once, capture the per-turn audit (queries +
        # consulted URLs + url_citation offsets). Requires the include
        # parameter set above so `action.sources` is populated.
        search_audit: dict | None = None
        if audit_context is not None and searches > 0 and final_response is not None:
            try:
                from dual_research.audit import normalize_openai_search_audit, audit_to_dict
                audit_obj = normalize_openai_search_audit(
                    final_response,
                    turn_key=str(audit_context.get("turn_key", "")),
                    phase=str(audit_context.get("phase", "")),
                    agent=str(audit_context.get("agent", self.label)),
                    label=str(audit_context.get("label", "")),
                )
                search_audit = audit_to_dict(audit_obj)
            except Exception:
                search_audit = None

        extras: dict = {"searches": searches}
        if search_audit is not None:
            extras["search_audit"] = search_audit

        # Spec 0143 §3.1 Step 3 — best-effort raw-usage capture (off by
        # default; gated by DUAL_RESEARCH_DEBUG_USAGE). Symmetric with
        # the Anthropic path so a future cost regression has both
        # providers' wire shapes recorded.
        if audit_context is not None:
            append_usage_debug(
                session_dir=audit_context.get("session_dir"),
                provider=self.provider,
                model_id=self._spec.model_id,
                label=str(audit_context.get("label", "")),
                usage_payload=final_usage,
                extra={"searches": searches},
            )

        return AgentResult(
            text=text,
            usage=usage,
            cost_usd=cost,
            duration_ms=duration_ms,
            model_id=final_model,
            provider=self.provider,
            label=self.label,
            extras=extras,
        )
