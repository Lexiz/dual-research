from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus
from dual_research.orchestrator.finalize import (
    confidence_tag,
    emit_final,
    render_metadata_header,
)
from dual_research.orchestrator.phase2 import Phase2Outcome
from dual_research.orchestrator.phase3 import current_draft_path, run_phase3
from dual_research.orchestrator.phase4 import run_phase4
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)
from dual_research.protocol import extract_revised_draft


class ScriptedAgent:
    def __init__(self, *, label: str, model_id: str, script: list[str]):
        self.label = label
        self.model_id = model_id
        self.provider = "anthropic" if label == "claude" else "openai"
        self._script = list(script)
        self._idx = 0

    async def run(self, prompt, *, max_output_tokens=8192, stream_to=None, stream_prefix="", audit_context=None):
        if self._idx >= len(self._script):
            raise RuntimeError(f"ScriptedAgent({self.label}) exhausted at call {self._idx + 1}")
        text = self._script[self._idx]
        self._idx += 1
        return AgentResult(
            text=text,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0001,
            duration_ms=10,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"stop_reason": "end_turn"},
        )


def _make_ctx(tmp_path: Path, *, drafter: str = "claude") -> tuple[SessionContext, EventBus]:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    # Seed phase1 drafts (Phase 3 reads them)
    p1 = sess.phase_dir("phase1")
    (p1 / "draft-claude.md").write_text("claude phase1 draft")
    (p1 / "draft-openai.md").write_text("openai phase1 draft")
    state = SessionState(
        phase="phase3",
        drafter=drafter,
        agreed_plan="1. **Title:** Background\n",
        final_surfaced_disagreements=[],
        draft_round=1,
    )
    ctx = SessionContext(
        session=sess, state=state, transcript=sess.open_transcript(), metrics=Metrics()
    )
    return ctx, EventBus()


# ---------- extract_revised_draft ----------


def test_extract_revised_draft_present() -> None:
    text = (
        "## Comments on the current draft\n\nfoo\n\n"
        "## Revised draft\n\nNEW DRAFT BODY\n\nMore content.\n\n"
        "## Status\nSTATUS: REVIEWING\nOPEN_ISSUES: 0\n"
    )
    body = extract_revised_draft(text)
    assert body is not None
    assert "NEW DRAFT BODY" in body
    assert "More content" in body
    assert "STATUS" not in body  # cut off at next ##


def test_extract_revised_draft_absent() -> None:
    text = "## Status\nSTATUS: REVIEWING\nOPEN_ISSUES: 1\n"
    assert extract_revised_draft(text) is None


# ---------- phase3 ----------


@pytest.mark.asyncio
async def test_phase3_writes_draft_and_advances_state(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path, drafter="openai")
    received: list[str] = []
    bus.subscribe(lambda e: received.append(e.kind))

    drafter_text = "## Summary\nFindings.\n\n## Sources\n[1] http://x\n"
    # Other agent's script is empty - it shouldn't be called in phase 3
    claude_agent = ScriptedAgent(label="claude", model_id="claude-sonnet-4-6", script=[])
    openai_agent = ScriptedAgent(label="openai", model_id="gpt-5.5", script=[drafter_text])

    outcome = await run_phase3(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="brief",
    )

    assert outcome.drafter == "openai"
    assert outcome.draft_chars == len(drafter_text)
    assert ctx.state.phase == "phase4"
    draft_file = ctx.session.phase_dir("phase3") / "draft-v1.md"
    assert draft_file.read_text() == drafter_text
    assert "phase3_complete" in received


@pytest.mark.asyncio
async def test_phase3_raises_without_drafter(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    ctx.state.drafter = None
    with pytest.raises(RuntimeError):
        await run_phase3(
            ctx=ctx,
            claude_agent=ScriptedAgent(label="claude", model_id="x", script=[]),
            openai_agent=ScriptedAgent(label="openai", model_id="y", script=[]),
            event_bus=bus,
            brief_content="brief",
        )


# ---------- current_draft_path ----------


def test_current_draft_path_routes_by_round(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    assert current_draft_path(sess, 1) == tmp_path / "phase3" / "draft-v1.md"
    assert current_draft_path(sess, 2) == tmp_path / "phase4" / "draft-v2.md"
    assert current_draft_path(sess, 5) == tmp_path / "phase4" / "draft-v5.md"


# ---------- phase4 convergence ----------


REVIEW_APPROVED_TURN = """## Answers to other's prior comments
(none — first round)

## Issue ledger (delta + currently open)
1. I-1: resolved on inspection.

## Evidence checked this round
- New research performed: (none)
- Claims checked against existing sources: (none)
- Factual issues found: (none)
- No new research because: draft self-contained.
- Corroboration on the other agent's claims:
  - Material [U] claims: (none)
  - Central [V] claims: (none)

## Comments on the current draft
(none)

## Disagreement carryover audit
- Final-surfaced disagreements from Phase 2: (none)
- Resolved disagreements that re-emerged: (none)
- New disagreements raised during review: (none)

## Substantive disagreements I'm holding
(none)

## Drafter revision note
(reviewer — no draft edits)

## Approval check
- ENDORSEMENT: draft satisfies brief.
- NON_BLOCKING_LIMITATIONS: none.
- STRONGEST_REMAINING_OBJECTION: minor wording.
- WHY_NON_BLOCKING: does not change recommendation.

## Status
STATUS: APPROVED
OPEN_ISSUES: 0
"""


@pytest.mark.asyncio
async def test_phase4_converges_in_round_1(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path, drafter="claude")
    ctx.state.phase = "phase4"
    # Seed phase3 draft (current draft at round 1)
    (ctx.session.phase_dir("phase3") / "draft-v1.md").write_text("INITIAL DRAFT")

    claude_agent = ScriptedAgent(
        label="claude", model_id="claude-sonnet-4-6", script=[REVIEW_APPROVED_TURN]
    )
    openai_agent = ScriptedAgent(
        label="openai", model_id="gpt-5.5", script=[REVIEW_APPROVED_TURN]
    )

    outcome = await run_phase4(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="brief",
        soft_cap=3,
        hard_cap=5,
    )

    assert outcome.approved is True
    assert outcome.rounds == 1
    assert outcome.revisions == 0
    assert outcome.final_draft_round == 1
    assert ctx.state.phase == "done"


# ---------- phase4 revision detection ----------


@pytest.mark.asyncio
async def test_phase4_drafter_revision_bumps_draft_round(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path, drafter="claude")
    ctx.state.phase = "phase4"
    (ctx.session.phase_dir("phase3") / "draft-v1.md").write_text("INITIAL DRAFT")

    received: list[dict] = []

    def sub(ev):
        if ev.kind == "phase4_draft_revised":
            received.append({"round": ev.round, "new_draft_round": ev.new_draft_round})

    bus.subscribe(sub)

    # Round 1: claude (drafter) revises. openai approves but mismatched → not yet approved.
    drafter_with_revision = """## Answers to openai's prior comments
1. addressed.

## Issue ledger (delta + currently open)
1. I-1: still open.

## Evidence checked this round
- New research performed: (none)
- Claims checked against existing sources: (none)
- Factual issues found: (none)
- No new research because: refining structure.
- Corroboration on the other agent's claims:
  - Material [U] claims: (none)
  - Central [V] claims: (none)

## Comments on the current draft
(none)

## Disagreement carryover audit
- Final-surfaced disagreements from Phase 2: (none)
- Resolved disagreements that re-emerged: (none)
- New disagreements raised during review: (none)

## Substantive disagreements I'm holding
(none)

## Revised draft

NEW IMPROVED DRAFT TEXT
With multiple lines.

## Drafter revision note
(a) tightened summary

## Approval check
(not ready) — waiting on openai

## Status
STATUS: REVIEWING
OPEN_ISSUES: 1
"""
    reviewer_turn = """## Answers to claude's prior comments
(none — first round)

## Issue ledger (delta + currently open)
1. I-1: open — phrasing in section 2.

## Evidence checked this round
- New research performed: (none)
- Claims checked against existing sources: (none)
- Factual issues found: (none)
- No new research because: structural feedback only.
- Corroboration on the other agent's claims:
  - Material [U] claims: (none)
  - Central [V] claims: (none)

## Comments on the current draft
1. tweak section 2

## Disagreement carryover audit
- Final-surfaced disagreements from Phase 2: (none)
- Resolved disagreements that re-emerged: (none)
- New disagreements raised during review: (none)

## Substantive disagreements I'm holding
(none)

## Drafter revision note
(reviewer — no draft edits)

## Approval check
(not ready) — issue I-1 open.

## Status
STATUS: REVIEWING
OPEN_ISSUES: 1
"""
    claude_agent = ScriptedAgent(
        label="claude",
        model_id="claude-sonnet-4-6",
        script=[drafter_with_revision, REVIEW_APPROVED_TURN],
    )
    openai_agent = ScriptedAgent(
        label="openai",
        model_id="gpt-5.5",
        script=[reviewer_turn, REVIEW_APPROVED_TURN],
    )

    outcome = await run_phase4(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="brief",
        soft_cap=3,
        hard_cap=4,
    )

    assert outcome.approved is True
    assert outcome.revisions == 1
    assert outcome.final_draft_round == 2
    assert received == [{"round": 1, "new_draft_round": 2}]
    revised_path = ctx.session.phase_dir("phase4") / "draft-v2.md"
    assert "NEW IMPROVED DRAFT TEXT" in revised_path.read_text()


# ---------- confidence_tag + render_metadata_header + emit_final ----------


def _p2(rounds=2, via_tiebreak=False, fsd_count=0, drafter="claude"):
    return Phase2Outcome(
        converged=True,
        rounds=rounds,
        drafter=drafter,
        agreed_plan="some plan",
        fsd_count=fsd_count,
        via_tiebreak=via_tiebreak,
        hard_capped=False,
    )


def _p4(rounds=1, approved=True, final_draft_round=1, revisions=0):
    from dual_research.orchestrator.phase4 import Phase4Outcome

    return Phase4Outcome(
        approved=approved,
        rounds=rounds,
        final_draft_round=final_draft_round,
        revisions=revisions,
        hard_capped=not approved,
    )


def test_confidence_tag_high_when_clean() -> None:
    tag = confidence_tag(
        phase2_outcome=_p2(rounds=2),
        phase4_outcome=_p4(rounds=2),
        soft_cap=6,
        hard_cap=12,
        repair_count=0,
    )
    assert tag == "HIGH"


def test_confidence_tag_moderate_on_softcap_cross() -> None:
    tag = confidence_tag(
        phase2_outcome=_p2(rounds=8),
        phase4_outcome=_p4(rounds=3),
        soft_cap=6,
        hard_cap=12,
        repair_count=0,
    )
    assert tag == "MODERATE"


def test_confidence_tag_low_on_unapproved() -> None:
    tag = confidence_tag(
        phase2_outcome=_p2(rounds=2),
        phase4_outcome=_p4(rounds=12, approved=False),
        soft_cap=6,
        hard_cap=12,
        repair_count=0,
    )
    assert tag == "LOW"


def test_metadata_header_renders_expected_fields(tmp_path: Path) -> None:
    ctx, _ = _make_ctx(tmp_path)
    # Seed some metrics
    from dual_research.agents.base import AgentResult, TokenUsage

    ctx.metrics.record(
        label="phase0-claude",
        result=AgentResult(
            text="",
            usage=TokenUsage(input_tokens=100, output_tokens=200),
            cost_usd=0.005,
            duration_ms=2000,
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            label="claude",
        ),
    )
    header = render_metadata_header(
        ctx=ctx,
        phase2_outcome=_p2(rounds=2),
        phase4_outcome=_p4(rounds=1),
        soft_cap=6,
        hard_cap=12,
        claude_model="claude-sonnet-4-6",
        openai_model="gpt-5.5",
    )
    assert "How this document was produced" in header
    assert "claude-sonnet-4-6" in header
    assert "gpt-5.5" in header
    assert "Outcome" in header
    assert "$0.0050" in header
    assert "Read with **HIGH confidence**" in header


@pytest.mark.asyncio
async def test_emit_final_writes_session_and_out(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    (ctx.session.phase_dir("phase3") / "draft-v1.md").write_text("# Final draft body\n\nMore.")
    ctx.state.draft_round = 1
    out_path = tmp_path / "out" / "final.md"

    written = await emit_final(
        ctx=ctx,
        event_bus=bus,
        out_path=out_path,
        phase2_outcome=_p2(rounds=2),
        phase4_outcome=_p4(rounds=1),
        soft_cap=6,
        hard_cap=12,
        claude_model="claude-sonnet-4-6",
        openai_model="gpt-5.5",
    )
    assert written.exists()
    assert "How this document was produced" in written.read_text()
    assert "# Final draft body" in written.read_text()
    assert out_path.exists()
    assert out_path.read_text() == written.read_text()
    assert ctx.state.final_emitted_to == str(out_path)
