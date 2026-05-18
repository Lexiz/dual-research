"""Spec 0036 — Phase 4 skips already-completed rounds during --resume."""
from __future__ import annotations

from pathlib import Path
from typing import TextIO

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus
from dual_research.orchestrator.phase4 import run_phase4
from dual_research.persistence import Metrics, SessionContext, SessionDirectory


class _CountingAgent:
    """Test agent that counts calls so we can assert skipped rounds."""

    def __init__(self, label: str, response_text: str):
        self.label = label
        self.provider = "test"
        self._response_text = response_text
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
            text=self._response_text,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost_usd=0.01,
            duration_ms=10,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"searches": 0},
        )


# A well-formed Phase 4 turn body with STATUS: APPROVED so is_review_approved
# returns True without us needing to fight the protocol validator.
_APPROVED_TURN_BODY = """## Summary
Review approved.

STATUS: `APPROVED`
DRAFTER: `claude`
OPEN_ISSUES: `0`
BLOCKING_DISAGREEMENTS: `0`
DOMAIN_FIT_SELF: `5`
DOMAIN_FIT_OTHER: `5`
STRONGEST_REMAINING_OBJECTION: None - draft meets all requirements.
WHY_NON_BLOCKING: All prior concerns addressed.

## Disagreement carryover audit

None.

## Evidence checked this round

No new evidence required for approval.

## Issue ledger (delta + currently open)

None.

## Comments on the current draft

None.

## Substantive disagreements I'm holding

None.

## Resolved or non-blocking differences

None.

## Final-surfaced disagreements

None.
"""


@pytest.mark.asyncio
async def test_phase4_skips_round_when_turn_files_exist(tmp_path: Path) -> None:
    """Pre-populate round-01 AND round-02 turn files with APPROVED;
    assert no API calls happen because both rounds are skipped via
    the resume replay. Spec 0091 § A applies to r1 even in the resume
    path: r1 APPROVED is downgraded, the loop continues to r2, which
    then converges via the pre-populated r2 files."""
    session = SessionDirectory(root=tmp_path).ensure()
    session.brief_path.write_text("# T\n", encoding="utf-8")

    # Seed Phase 3 draft so current_draft_path resolves.
    phase3 = session.root / "phase3"
    phase3.mkdir()
    (phase3 / "draft-v1.md").write_text("# Doc\n\nbody\n", encoding="utf-8")

    state = session.load_state()
    state.drafter = "claude"
    state.draft_round = 1
    state.phase = "phase4"
    session.save_state(state)

    # Pre-populate both round 1 and round 2 with approved turns.
    # Round 1 is skipped (resume) then downgraded by spec 0091 § A;
    # round 2 is also skipped (resume) and its APPROVED terminates.
    phase4 = session.root / "phase4"
    phase4.mkdir()
    (phase4 / "round-01-claude.md").write_text(_APPROVED_TURN_BODY, encoding="utf-8")
    (phase4 / "round-01-openai.md").write_text(_APPROVED_TURN_BODY, encoding="utf-8")
    (phase4 / "round-02-claude.md").write_text(_APPROVED_TURN_BODY, encoding="utf-8")
    (phase4 / "round-02-openai.md").write_text(_APPROVED_TURN_BODY, encoding="utf-8")

    transcript = session.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    claude = _CountingAgent("claude", _APPROVED_TURN_BODY)
    openai = _CountingAgent("openai", _APPROVED_TURN_BODY)

    outcome = await run_phase4(
        ctx=ctx,
        claude_agent=claude,
        openai_agent=openai,
        event_bus=EventBus(),
        brief_content="# T\n",
        soft_cap=3,
        hard_cap=5,
    )

    # Both rounds had files on disk → no API calls. Convergence lands
    # in r2 (the earliest round that's allowed to terminate).
    assert claude.call_count == 0
    assert openai.call_count == 0
    assert outcome.approved is True
    assert outcome.rounds == 2


@pytest.mark.asyncio
async def test_phase4_runs_normally_when_files_missing(tmp_path: Path) -> None:
    """Without pre-populated files, the agent IS called.

    Spec 0091 § A: r1 APPROVED is silently downgraded, so the agent
    is called in r2 too. Convergence lands in r2 at the earliest.
    """
    session = SessionDirectory(root=tmp_path).ensure()
    session.brief_path.write_text("# T\n", encoding="utf-8")
    phase3 = session.root / "phase3"
    phase3.mkdir()
    (phase3 / "draft-v1.md").write_text("# Doc\n", encoding="utf-8")

    state = session.load_state()
    state.drafter = "claude"
    state.draft_round = 1
    state.phase = "phase4"
    session.save_state(state)

    transcript = session.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    claude = _CountingAgent("claude", _APPROVED_TURN_BODY)
    openai = _CountingAgent("openai", _APPROVED_TURN_BODY)

    outcome = await run_phase4(
        ctx=ctx,
        claude_agent=claude,
        openai_agent=openai,
        event_bus=EventBus(),
        brief_content="# T\n",
        soft_cap=3,
        hard_cap=5,
    )
    # No files → agents are called for r1, but r1 APPROVED is downgraded
    # so the loop continues to r2, agents called again, r2 terminates.
    assert claude.call_count == 2
    assert openai.call_count == 2
    assert outcome.approved is True
