from __future__ import annotations

import time
from typing import Any, TextIO

import openai
from openai import AsyncOpenAI

from dual_research.agents.base import AgentError, AgentResult, TokenUsage, web_search_enabled
from dual_research.agents.pricing import compute_cost
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT


WEB_SEARCH_TOOL = {"type": "web_search"}


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

        try:
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

        usage = TokenUsage(
            input_tokens=max(0, input_tokens_total - cached),
            output_tokens=output_tokens,
            cache_read_tokens=cached,
            cache_write_tokens=0,
        )
        text = "".join(text_parts)
        cost = compute_cost(self._spec.model_id, usage)
        duration_ms = int((time.perf_counter() - start) * 1000)

        return AgentResult(
            text=text,
            usage=usage,
            cost_usd=cost,
            duration_ms=duration_ms,
            model_id=final_model,
            provider=self.provider,
            label=self.label,
            extras={"searches": searches},
        )
