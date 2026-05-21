"""Spec 0143 §3.1 — per-agent capture parity.

Two regression-pins:

1. **OpenAI reasoning_tokens passthrough** — when the Responses API
   returns ``usage.output_tokens_details.reasoning_tokens``, the GptAgent
   must surface it on ``AgentResult.usage.reasoning_tokens`` AND keep
   ``output_tokens`` unchanged. Folding reasoning into output_tokens
   would double-bill (the Responses API already includes reasoning in
   ``output_tokens`` — verified by the anchor-run invoice reconciliation
   in spec 0143 §1).

2. **Anthropic cache_control reaches the wire** — when
   ``cache_enabled()`` is True and ``CACHE_BREAKPOINT`` appears in the
   prompt, the kwargs handed to ``messages.stream`` must carry a content
   list with a ``cache_control`` block. Defensive pin: the anchor run
   was the canary for "cache_control silently not applied," and this
   test asserts the agent's request-building path can't regress that.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from dual_research.agents.anthropic_agent import _build_content
from dual_research.agents.openai_agent import GptAgent
from dual_research.agents.base import TokenUsage
from dual_research.config import ModelSpec
from dual_research.protocol import CACHE_BREAKPOINT


# ─────────────────────────── OpenAI passthrough ────────────────────────────


class _FakeStream:
    """Minimal async iterator over canned Responses-API streaming events."""

    def __init__(self, events: list[Any]):
        self._events = events

    def __aiter__(self):
        async def _gen():
            for e in self._events:
                yield e
        return _gen()


class _FakeResponses:
    def __init__(self, events: list[Any]):
        self._events = events

    async def create(self, **kwargs: Any) -> _FakeStream:
        return _FakeStream(self._events)


class _FakeOpenAIClient:
    def __init__(self, events: list[Any]):
        self.responses = _FakeResponses(events)


@pytest.mark.asyncio
async def test_openai_reasoning_tokens_captured_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capture reasoning_tokens; do NOT alter output_tokens."""
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    monkeypatch.setenv("DUAL_RESEARCH_NO_WEB_SEARCH", "1")  # keep events small

    completed = SimpleNamespace(
        type="response.completed",
        response=SimpleNamespace(
            model="gpt-5.5-2026-04-23",
            usage=SimpleNamespace(
                input_tokens=1000,
                output_tokens=2702,                    # already includes reasoning
                input_tokens_details=SimpleNamespace(cached_tokens=200),
                output_tokens_details=SimpleNamespace(reasoning_tokens=1500),
            ),
        ),
    )
    delta = SimpleNamespace(type="response.output_text.delta", delta="hello")

    spec = ModelSpec(provider="openai", model_id="gpt-5.5-2026-04-23", context_window=400_000)
    agent = GptAgent(api_key="sk-test", spec=spec)
    agent._client = _FakeOpenAIClient([delta, completed])  # type: ignore[assignment]

    result = await agent.run("prompt", stream_to=None)

    assert result.usage.reasoning_tokens == 1500
    # output_tokens stays as the API returned it — NOT (output + reasoning).
    # Folding would double-bill, since the Responses API includes
    # reasoning inside output_tokens already.
    assert result.usage.output_tokens == 2702
    # Cached tokens still subtracted from input (existing contract).
    assert result.usage.cache_read_tokens == 200
    assert result.usage.input_tokens == 800


@pytest.mark.asyncio
async def test_openai_reasoning_tokens_default_zero_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the response has no output_tokens_details, reasoning_tokens=0."""
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    monkeypatch.setenv("DUAL_RESEARCH_NO_WEB_SEARCH", "1")

    completed = SimpleNamespace(
        type="response.completed",
        response=SimpleNamespace(
            model="gpt-5-mini",
            usage=SimpleNamespace(
                input_tokens=500,
                output_tokens=100,
                input_tokens_details=None,
                output_tokens_details=None,
            ),
        ),
    )
    spec = ModelSpec(provider="openai", model_id="gpt-5-mini", context_window=400_000)
    agent = GptAgent(api_key="sk-test", spec=spec)
    agent._client = _FakeOpenAIClient([completed])  # type: ignore[assignment]

    result = await agent.run("prompt")
    assert result.usage.reasoning_tokens == 0
    assert result.usage.output_tokens == 100


# ─────────────────────────── Anthropic kwargs ──────────────────────────────


def test_anthropic_build_content_carries_cache_control_when_intended(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_build_content`` must emit a content list with a cache_control
    block whenever cache_enabled() AND CACHE_BREAKPOINT is in the prompt.

    The anchor run (Notion B03) saw cache_control silently not engage on
    the wire — both ``cache_read_tokens`` AND ``cache_write_tokens`` came
    back zero AND the cost matched plain-input arithmetic. This pin
    catches future refactors that accidentally strip the cache_control
    block before it reaches ``messages.stream``.
    """
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    prompt = f"stable prefix here{CACHE_BREAKPOINT}per-turn body"
    content = _build_content(prompt)

    assert isinstance(content, list), "must be a content-blocks list when caching is engaged"
    assert len(content) == 2
    assert content[0]["text"] == "stable prefix here"
    assert content[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert content[1]["text"] == "per-turn body"
    assert "cache_control" not in content[1]


def test_token_usage_reasoning_tokens_sums() -> None:
    """Spec 0143 — reasoning_tokens must sum across ``__add__``."""
    a = TokenUsage(input_tokens=100, output_tokens=50, reasoning_tokens=10)
    b = TokenUsage(input_tokens=200, output_tokens=80, reasoning_tokens=25)
    c = a + b
    assert c.input_tokens == 300
    assert c.output_tokens == 130
    assert c.reasoning_tokens == 35
