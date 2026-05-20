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
def test_disagreements_carry_progression_and_resolution() -> None:
    run = load_run_snapshot(_FIXTURE_RUN)
    # Every disagreement carries at least the initial "raised" step.
    for d in run.disagreements:
        assert d.progression, f"disagreement {d.id} has no progression"
        assert d.progression[0].action == "raised"
    # At least one disagreement reached a terminal state on this run.
    terminal = [d for d in run.disagreements if d.status != "open"]
    assert terminal, "expected at least one closed disagreement"
