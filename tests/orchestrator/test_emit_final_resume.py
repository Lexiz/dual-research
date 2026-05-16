"""Spec 0036 — emit_final tolerates phase2_outcome=None on resume."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from dual_research.events import EventBus
from dual_research.orchestrator.finalize import (
    confidence_tag,
    emit_final,
    render_metadata_header,
)
from dual_research.orchestrator.phase4 import Phase4Outcome
from dual_research.persistence import Metrics, SessionContext, SessionDirectory


@pytest.fixture
def phase4_approved() -> Phase4Outcome:
    return Phase4Outcome(
        approved=True,
        rounds=1,
        final_draft_round=1,
        revisions=0,
        hard_capped=False,
    )


def test_confidence_tag_handles_none_phase2(phase4_approved: Phase4Outcome):
    """Returns MODERATE rather than crashing when phase2_outcome is None."""
    tag = confidence_tag(
        phase2_outcome=None,
        phase4_outcome=phase4_approved,
        soft_cap=6,
        hard_cap=12,
        repair_count=0,
    )
    assert tag == "MODERATE"


def test_render_metadata_header_handles_none_phase2(tmp_path: Path, phase4_approved: Phase4Outcome):
    """The metadata header substitutes a replay note in place of Phase 2 details."""
    session = SessionDirectory(root=tmp_path).ensure()
    state = session.load_state()
    transcript = session.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    header = render_metadata_header(
        ctx=ctx,
        phase2_outcome=None,
        phase4_outcome=phase4_approved,
        soft_cap=6,
        hard_cap=12,
        claude_model="claude-haiku-4-5",
        openai_model="gpt-4.1",
    )
    assert "replayed from prior run" in header
    assert "**APPROVED**" in header


@pytest.mark.asyncio
async def test_emit_final_succeeds_when_phase2_outcome_is_none(
    tmp_path: Path, phase4_approved: Phase4Outcome
):
    """End-to-end: emit_final with phase2_outcome=None writes final.md without raising."""
    session = SessionDirectory(root=tmp_path).ensure()
    # Seed brief + draft so current_draft_path resolves.
    session.brief_path.write_text("# Topic\n", encoding="utf-8")
    phase3 = session.root / "phase3"
    phase3.mkdir()
    (phase3 / "draft-v1.md").write_text("# Doc\n\nbody\n", encoding="utf-8")

    state = session.load_state()
    state.drafter = "claude"
    state.draft_round = 1
    session.save_state(state)

    transcript = session.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    bus = EventBus()

    final_path = await emit_final(
        ctx=ctx,
        event_bus=bus,
        out_path=None,
        phase2_outcome=None,  # ← spec 0036
        phase4_outcome=phase4_approved,
        soft_cap=6,
        hard_cap=12,
        claude_model="claude-haiku-4-5",
        openai_model="gpt-4.1",
    )
    assert final_path.is_file()
    text = final_path.read_text()
    assert "**APPROVED**" in text
    assert "replayed from prior run" in text
