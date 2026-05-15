from __future__ import annotations

import time
from typing import TextIO

import openai
from openai import AsyncOpenAI

from dual_research.agents.base import AgentError, AgentResult, TokenUsage
from dual_research.agents.pricing import compute_cost
from dual_research.config import ModelSpec


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
        start = time.perf_counter()
        text_parts: list[str] = []
        first_token = True
        final_usage = None
        final_model = self._spec.model_id

        try:
            stream = await self._client.chat.completions.create(
                model=self._spec.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_output_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if chunk.choices:
                    delta_obj = chunk.choices[0].delta
                    delta = getattr(delta_obj, "content", None)
                    if delta:
                        text_parts.append(delta)
                        if stream_to is not None:
                            if first_token and stream_prefix:
                                stream_to.write(stream_prefix)
                                first_token = False
                            stream_to.write(delta)
                            stream_to.flush()
                if chunk.usage is not None:
                    final_usage = chunk.usage
                if chunk.model:
                    final_model = chunk.model
        except openai.APIError as e:
            raise AgentError(f"OpenAI API error ({type(e).__name__}): {e}") from e

        if stream_to is not None and not first_token:
            stream_to.write("\n")
            stream_to.flush()

        if final_usage is None:
            raise AgentError("OpenAI stream ended without usage payload — set stream_options include_usage")

        cached = 0
        details = getattr(final_usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0

        usage = TokenUsage(
            input_tokens=(final_usage.prompt_tokens or 0) - cached,
            output_tokens=final_usage.completion_tokens or 0,
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
            extras={"finish_reason": (chunk.choices[0].finish_reason if chunk.choices else None)},
        )
