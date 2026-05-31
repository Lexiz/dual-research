from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.events import EventBus
from dual_research.orchestrator.finalize import (
    confidence_tag,
    emit_final,
    render_metadata_header,
)
from dual_research.orchestrator.phase2 import Phase2Outcome
from dual_research.orchestrator.phase3 import current_draft_path
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)
from dual_research.protocol import extract_revised_draft


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


# ---------- current_draft_path ----------


def test_current_draft_path_routes_by_round(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    assert current_draft_path(sess, 1) == tmp_path / "phase3" / "draft-v1.md"
    assert current_draft_path(sess, 2) == tmp_path / "phase4" / "draft-v2.md"
    assert current_draft_path(sess, 5) == tmp_path / "phase4" / "draft-v5.md"


# ---------- confidence_tag + render_metadata_header + emit_final ----------
#
# Spec 0257.1: the phase-4 convergence + revision-detection tests that
# exercised the legacy ``run_phase4`` runner were removed with that dead
# runner. Live Phase 4 behaviour is covered against ``run_dr_phase4``
# elsewhere; the ``Phase4Outcome`` contract assertions below stay.


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
