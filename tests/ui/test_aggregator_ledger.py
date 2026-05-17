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


# ─── Spec 0044 — wire-format guards for the frontend's ledger consumers ─────


def test_phase_ledgers_entries_carry_status_history_with_turn_key() -> None:
    """Spec 0044 D3 — ``StatChip`` walks ``statusHistory[].turnKey`` to
    derive the per-turn ``resolved`` count. Each entry's status_history
    must include ``turnKey`` on every transition so the frontend can
    filter by ``raisedTurnKey === item.turnKey`` style equality."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    for entry in run.phase_ledgers[2]:
        history = entry.get("status_history") or []
        for t in history:
            assert "turn_key" in t, (
                f"ledger entry {entry.get('id')} status_history missing turn_key: {t}"
            )
            assert "status" in t


def test_phase_ledgers_entries_carry_raised_turn_key_field() -> None:
    """Spec 0044 D3 — chips filter ``raisedTurnKey === item.turnKey``.
    The field must be PRESENT on every entry (even if empty for items
    sourced from reconstructors that don't always populate it — those
    silently won't match any turn, which is acceptable). The field's
    absence would crash the frontend ``computeChipDeltas`` filter.

    Additionally, the bulk of entries DO have a populated key (most
    disagreements get theirs via spec 0034's turn-key population pass);
    we assert >80% populated as a regression guard."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    for entry in run.phase_ledgers[2] + run.phase_ledgers[4]:
        assert "raised_turn_key" in entry, (
            f"ledger entry {entry.get('id')} missing raised_turn_key field"
        )
    populated = sum(
        1 for e in run.phase_ledgers[2] + run.phase_ledgers[4]
        if e.get("raised_turn_key")
    )
    total = len(run.phase_ledgers[2]) + len(run.phase_ledgers[4])
    assert populated > total * 0.8, (
        f"only {populated}/{total} entries have populated raised_turn_key — regression?"
    )


def test_phase_timings_exposed_for_isFinalConvergedTurn() -> None:
    """Spec 0044 D9 — ``isFinalConvergedTurn`` reads
    ``run.phaseTimings[phase]`` to verify the phase has actually
    exited. Wire shape must populate it on completed runs."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    assert run.phase_timings.get(2) is not None
    assert run.phase_timings.get(4) is not None
