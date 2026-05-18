"""Spec 0091 — Phase 4 round-1 cannot-approve gate.

Two integration tests:
  - Round-1 APPROVED is silently downgraded → loop continues to r2 → r2's
    APPROVED wins.
  - The hard-cap is still respected even if every round emits APPROVED
    (just to verify the gate doesn't prevent termination forever).
"""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus
from dual_research.orchestrator.phase4 import run_phase4
from dual_research.persistence import Metrics, SessionContext, SessionDirectory


_APPROVED_TURN_BODY = """## Summary
Review approved.

STATUS: `APPROVED`
DRAFTER: `claude`
OPEN_ISSUES: `0`
BLOCKING_DISAGREEMENTS: `0`
DOMAIN_FIT_SELF: `5`
DOMAIN_FIT_OTHER: `5`
STRONGEST_REMAINING_OBJECTION: None.
WHY_NON_BLOCKING: All concerns addressed.

## Disagreement carryover audit
None.

## Evidence checked this round
None.

## Issue ledger (delta + currently open)
None.
"""


class _CountingAgent:
    def __init__(self, label: str, body: str):
        self.label = label
        self.provider = "test"
        self._body = body
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return f"{self.label}-model"

    async def run(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 8192,
        stream_to: TextIO | None = None,
        stream_prefix: str = "",
        audit_context: dict | None = None,
    ) -> AgentResult:
        self.call_count += 1
        return AgentResult(
            text=self._body,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost_usd=0.01,
            duration_ms=10,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"searches": 0},
        )


def _setup_session(tmp_path: Path) -> SessionContext:
    session = SessionDirectory(root=tmp_path).ensure()
    session.brief_path.write_text("# Brief\n", encoding="utf-8")
    phase3 = session.root / "phase3"
    phase3.mkdir()
    (phase3 / "draft-v1.md").write_text("# Draft v1\n", encoding="utf-8")
    state = session.load_state()
    state.drafter = "claude"
    state.draft_round = 1
    state.phase = "phase4"
    session.save_state(state)
    transcript = session.open_transcript()
    return SessionContext(
        session=session, state=state,
        transcript=transcript, metrics=Metrics(),
    )


@pytest.mark.asyncio
async def test_round_1_approved_is_downgraded_and_loop_continues(
    tmp_path: Path,
) -> None:
    """Spec 0091 § A core assertion. Both agents emit APPROVED in r1;
    the orchestrator downgrades to approved=False and continues to r2."""
    ctx = _setup_session(tmp_path)
    claude = _CountingAgent("claude", _APPROVED_TURN_BODY)
    openai = _CountingAgent("openai", _APPROVED_TURN_BODY)

    outcome = await run_phase4(
        ctx=ctx, claude_agent=claude, openai_agent=openai,
        event_bus=EventBus(), brief_content="# Brief\n",
        soft_cap=3, hard_cap=5,
    )

    # Round 1's APPROVED was downgraded; round 2's APPROVED terminates.
    assert outcome.approved is True
    assert outcome.rounds == 2
    # Each agent called once per round = 2 total.
    assert claude.call_count == 2
    assert openai.call_count == 2


@pytest.mark.asyncio
async def test_round_1_gate_does_not_prevent_termination_post_r1(
    tmp_path: Path,
) -> None:
    """Sanity: the round-1 gate must NOT block convergence in any
    subsequent round. r3 APPROVED should still terminate normally."""

    class _RoundAwareAgent(_CountingAgent):
        """Returns REVIEWING for round 1 and 2 (sniffed from the prompt's
        round line), APPROVED thereafter."""

        def __init__(self, label: str):
            super().__init__(label, _APPROVED_TURN_BODY)

        async def run(self, prompt: str, **kw) -> AgentResult:
            self.call_count += 1
            if self.call_count <= 2:
                body = _APPROVED_TURN_BODY.replace(
                    "STATUS: `APPROVED`", "STATUS: `REVIEWING`",
                ).replace("OPEN_ISSUES: `0`", "OPEN_ISSUES: `1`")
                body += "\n\n## Issue ledger (delta + currently open)\n1. **I-c-r1-01 — open:** placeholder issue\n"
            else:
                body = self._body
            return AgentResult(
                text=body,
                usage=TokenUsage(input_tokens=100, output_tokens=50),
                cost_usd=0.01,
                duration_ms=10,
                model_id=self.model_id,
                provider=self.provider,
                label=self.label,
                extras={"searches": 0},
            )

    ctx = _setup_session(tmp_path)
    claude = _RoundAwareAgent("claude")
    openai = _RoundAwareAgent("openai")

    outcome = await run_phase4(
        ctx=ctx, claude_agent=claude, openai_agent=openai,
        event_bus=EventBus(), brief_content="# Brief\n",
        soft_cap=5, hard_cap=8,
    )

    # Convergence in round 3 (round 1+2 REVIEWING, round 3 APPROVED).
    assert outcome.approved is True
    assert outcome.rounds == 3
