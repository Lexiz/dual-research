"""Spec 0114 — production-wiring smoke tests for orchestrator/dr_run.py.

These confirm the new ``run_dr_phase*`` coroutines actually thread through
``run_one_call`` → file writes → event publishing for stub agents. They
don't re-verify the lifecycle math (that's covered by
``test_deep_research.py``); they verify the I/O glue between the pure
runner and the production infrastructure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus, Phase1Complete, PhaseEntered
from dual_research.orchestrator.dr_run import run_dr_phase1
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)


class StubAgent:
    """Canned-response agent for production wiring tests."""

    def __init__(self, *, label: str, model_id: str, text: str):
        self.label = label
        self.model_id = model_id
        self.provider = "anthropic" if label == "claude" else "openai"
        self._text = text

    async def run(
        self,
        prompt,
        *,
        max_output_tokens=8192,
        stream_to=None,
        stream_prefix="",
        audit_context=None,
    ):
        return AgentResult(
            text=self._text,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0001,
            duration_ms=42,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"stop_reason": "end_turn"},
        )


_PHASE1_DRAFT = (
    "## 1. Summary\nFindings overview.\n\n"
    "## 2. My thesis\nMy current judgment.\n\n"
    "## 3. Detailed findings\nThe substance with [V] tags inline.\n\n"
    "## 4. Sources\n[1] https://example.com\n"
)


def _make_ctx(tmp_path: Path) -> tuple[SessionContext, EventBus]:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    state = SessionState()
    state.agreed_interpretation = "(agreed interpretation body)"
    transcript = sess.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(
        session=sess, state=state, transcript=transcript, metrics=metrics,
    )
    return ctx, EventBus()


@pytest.mark.asyncio
async def test_dr_phase1_writes_drafts_and_emits_events(tmp_path: Path) -> None:
    """Confirm the new phase-1 runner writes both drafts and emits the
    expected events. Uses stub agents that return canned phase-1 output."""
    ctx, bus = _make_ctx(tmp_path)
    received: list[str] = []

    def sub(ev):
        received.append(ev.kind)

    bus.subscribe(sub)

    outcome = await run_dr_phase1(
        ctx=ctx,
        claude_agent=StubAgent(
            label="claude", model_id="claude-sonnet-4-6", text=_PHASE1_DRAFT,
        ),
        openai_agent=StubAgent(
            label="openai", model_id="gpt-5.5", text=_PHASE1_DRAFT,
        ),
        event_bus=bus,
        brief_content="the brief",
    )

    assert outcome.claude_chars == len(_PHASE1_DRAFT)
    assert outcome.openai_chars == len(_PHASE1_DRAFT)

    p1 = ctx.session.phase_dir("phase1")
    assert (p1 / "draft-claude.md").read_text() == _PHASE1_DRAFT
    assert (p1 / "draft-openai.md").read_text() == _PHASE1_DRAFT

    assert "phase_entered" in received
    assert "phase1_complete" in received
    assert "phase_exited" in received
