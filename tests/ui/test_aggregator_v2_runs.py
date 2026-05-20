"""Spec 0122 — end-to-end load of a v2 (post-spec-0114) run.

Uses the on-disk fixture at
``runs/20260520-025406-pv-backend-language-choice`` — the run that
prompted spec 0122. The legacy reconstructors return zero on this run
(its round files use the new section schema); the v2 path should
surface every item via the replay-from-disk backfill.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ui.aggregator import load_run_snapshot


_FIXTURE_RUN = Path(__file__).resolve().parents[2] / "runs" / "20260520-025406-pv-backend-language-choice"


@pytest.mark.skipif(not _FIXTURE_RUN.is_dir(), reason="fixture run not present in this checkout")
def test_deadlocked_v2_run_surfaces_items_via_replay() -> None:
    run = load_run_snapshot(_FIXTURE_RUN)

    # Status comes from the run_completed exit_code=51 in the transcript.
    assert run.status == "deadlocked"

    # The legacy reconstructors would return zero on this run. The
    # spec-0122 replay-from-disk fallback restores all four typed lists.
    assert len(run.questions) > 0, "questions populated via replay"
    assert len(run.disagreements) > 0, "disagreements populated via replay"
    assert len(run.issues) > 0, "issues populated via replay"

    # phase_ledgers must be non-empty for both interaction phases — these
    # are what the frontend's chip-deltas computation reads.
    assert len(run.phase_ledgers[2]) > 0
    assert len(run.phase_ledgers[4]) > 0

    # Spec 0115 — Item bundle on phase_stats is the canonical source.
    assert len(run.phase_stats.items) > 0

    # The "suspected miss" banner is suppressed for v2 runs.
    assert run.disagreements_parse_suspected_miss is False


@pytest.mark.skipif(not _FIXTURE_RUN.is_dir(), reason="fixture run not present in this checkout")
def test_no_op_round_still_carries_standing_chips() -> None:
    """Regression: in this run, phase 2 round 5 has both agents emitting
    ``STATUS: AGREED`` with empty operation arrays. Before the spec-0122
    carry-forward fix, ``items.py`` produced no ``turn_category_stats``
    entry for that round and the timeline cards rendered no chips at
    all — instead of the carry-forward ``0 +0/-0`` chips on top of the
    prior round's standing totals.
    """
    run = load_run_snapshot(_FIXTURE_RUN)
    r5 = run.phase_stats.phase2.get(5) or {}
    assert "claude" in r5 and "gpt" in r5, "both agents should have a slot for r5"

    claude_cats = r5["claude"].categories
    gpt_cats = r5["gpt"].categories
    assert claude_cats is not None, "claude r5 must have categories populated"
    assert gpt_cats is not None, "gpt r5 must have categories populated"

    # By end of r4 (after spec-0122 parser-tolerance fix recovered the
    # operation blocks claude's r2 turn emitted with a glued-on body):
    # Claude D=3 standing (D-plan-c-01, -02, -03 addressed in r2; the
    # other 4 closed by r3-r4), GPT Q=0 / D=0 (the parser recovery means
    # both questions + four disagreements close by r3). r5 had no
    # operations from either agent, so r5 standing == r4 standing and
    # raised/closed are zero across the board.
    assert claude_cats.disagreements.standing == 3
    assert claude_cats.disagreements.raised == 0
    assert claude_cats.disagreements.closed == 0
    assert gpt_cats.questions.raised == 0
    assert gpt_cats.questions.closed == 0
    # GPT's open count is the carry-forward from r4 — both questions
    # have been resolved by that point, so 0.
    assert gpt_cats.questions.standing == 0
    assert gpt_cats.disagreements.standing == 0


@pytest.mark.skipif(not _FIXTURE_RUN.is_dir(), reason="fixture run not present in this checkout")
def test_disagreements_carry_progression_and_resolution() -> None:
    run = load_run_snapshot(_FIXTURE_RUN)
    # Every disagreement carries at least the initial "raised" step.
    for d in run.disagreements:
        assert d.progression, f"disagreement {d.id} has no progression"
        assert d.progression[0].action == "raised"
    # At least one disagreement reached a terminal state on this run.
    terminal = [d for d in run.disagreements if d.status != "open"]
    assert terminal, "expected at least one closed disagreement"
