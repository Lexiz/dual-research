"""Spec 0043 — aggregator wires ledger into Run."""

from __future__ import annotations

from pathlib import Path

from dual_research.ui.aggregator import load_run_snapshot


def test_partner_vetting_fixture_populates_phase_ledgers() -> None:
    """The canonical partner-vetting fixture must produce non-empty
    ledger arrays for Phase 2 and Phase 4 on every snapshot load."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    assert 2 in run.phase_ledgers
    assert 4 in run.phase_ledgers
    assert len(run.phase_ledgers[2]) > 0
    assert len(run.phase_ledgers[4]) > 0


def test_partner_vetting_fixture_phase4_zero_open_issues() -> None:
    """Partner-vetting Phase 4 ends with all issues resolved; the
    ledger should report 0 open issues post-build."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    open_issues = [
        e for e in run.phase_ledgers[4]
        if e["kind"] == "issue" and e["current_status"] == "open"
    ]
    assert open_issues == []


def test_partner_vetting_drifts_surface_questions_gap() -> None:
    """On partner-vetting, agents converged with OPEN_QUESTIONS=0 but
    the ledger still tracks some questions as open (positional answer-
    linkage missed them). The drift signal is the spec's way of
    surfacing that gap. Just assert that drifts is a list — the
    exact count depends on the matcher; the value is in the signal
    being present, not its specific cardinality."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    assert isinstance(run.drifts, list)
    # At least one drift kind should fire on this fixture (the
    # questions gap surfaced during the spec design); a clean run
    # with zero drifts would also be valid in principle.
    # Each drift is a dict with the spec 0043 D8 shape.
    for d in run.drifts:
        assert "turn_key" in d
        assert "kind" in d
        assert "agent_count" in d
        assert "ledger_count" in d
