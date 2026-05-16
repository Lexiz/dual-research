from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus, Phase0Complete, Phase1Complete, PhaseEntered
from dual_research.orchestrator.phase0 import run_phase0
from dual_research.orchestrator.phase1 import run_phase1
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
    Transcript,
)


class StubAgent:
    """Canned-response agent for orchestrator tests."""

    def __init__(self, *, label: str, model_id: str, text: str):
        self.label = label
        self.model_id = model_id
        self.provider = "anthropic" if label == "claude" else "openai"
        self._text = text

    async def run(self, prompt, *, max_output_tokens=8192, stream_to=None, stream_prefix="", audit_context=None):
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


PREFLIGHT_OK = (
    "## Brief clarity\nFine.\n\n## Missing inputs\n(none)\n\n"
    "## Framing concerns\n(none)\n\n## Proposed scope\nresearch X.\n\n"
    "## Status\nSTATUS: BRIEF_OK\nBRIEF_ISSUES: 0\n"
)


PREFLIGHT_NEEDS_INPUT = (
    "## Brief clarity\nAmbiguous.\n\n## Missing inputs\n1. needs Y\n\n"
    "## Status\nSTATUS: BRIEF_NEEDS_INPUT\nBRIEF_ISSUES: 1\n"
)


PHASE1_DRAFT = (
    "## Summary\nFindings.\n\n## My thesis\n...\n\n## Sources\n[1] http://x\n"
)


def _make_ctx(tmp_path: Path) -> tuple[SessionContext, EventBus]:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    state = SessionState()
    transcript = sess.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=sess, state=state, transcript=transcript, metrics=metrics)
    return ctx, EventBus()


@pytest.mark.asyncio
async def test_phase0_brief_ok(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    received: list[str] = []

    def sub(ev):
        received.append(ev.kind)

    bus.subscribe(sub)
    outcome = await run_phase0(
        ctx=ctx,
        claude_agent=StubAgent(label="claude", model_id="claude-sonnet-4-6", text=PREFLIGHT_OK),
        openai_agent=StubAgent(label="openai", model_id="gpt-5.5", text=PREFLIGHT_OK),
        event_bus=bus,
        brief_content="brief content",
    )
    assert outcome.brief_needs_input is False
    assert outcome.claude_status == "BRIEF_OK"
    assert outcome.openai_status == "BRIEF_OK"
    assert (ctx.session.root / "phase0" / "preflight-claude.md").exists()
    assert (ctx.session.root / "phase0" / "preflight-openai.md").exists()
    assert "phase_entered" in received and "phase0_complete" in received and "phase_exited" in received


@pytest.mark.asyncio
async def test_phase0_needs_input_continues_anyway(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    outcome = await run_phase0(
        ctx=ctx,
        claude_agent=StubAgent(label="claude", model_id="claude-sonnet-4-6", text=PREFLIGHT_NEEDS_INPUT),
        openai_agent=StubAgent(label="openai", model_id="gpt-5.5", text=PREFLIGHT_OK),
        event_bus=bus,
        brief_content="brief content",
    )
    assert outcome.brief_needs_input is True
    # File still written; orchestrator did not abort
    assert (ctx.session.root / "phase0" / "preflight-claude.md").exists()


@pytest.mark.asyncio
async def test_phase1_writes_drafts(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    outcome = await run_phase1(
        ctx=ctx,
        claude_agent=StubAgent(label="claude", model_id="claude-sonnet-4-6", text=PHASE1_DRAFT),
        openai_agent=StubAgent(label="openai", model_id="gpt-5.5", text=PHASE1_DRAFT),
        event_bus=bus,
        brief_content="brief content",
    )
    assert outcome.claude_chars == len(PHASE1_DRAFT)
    assert outcome.openai_chars == len(PHASE1_DRAFT)
    assert Path(outcome.claude_path).read_text() == PHASE1_DRAFT
    assert Path(outcome.openai_path).read_text() == PHASE1_DRAFT
