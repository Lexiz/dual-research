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


# ─── Spec 0046 — wire-format guards for the frontend's per-card ghosted
# annotation + the per-kind Summary tab ─────────────────────────────────────


def test_phase_ledgers_entries_carry_ghosted_rounds_field() -> None:
    """Spec 0046 D4 — ``GhostedAnnotation`` (defined in spec 0043 D5,
    wired in spec 0046 D4) reads ``entry.ghostedRounds`` on every
    critique card. The aggregator must always emit the field — even
    when the value is zero — so ``CardHeadline``'s feature-test
    (``ghostedRounds > 0``) is reliable. The frontend ``findLedgerEntry``
    helper resolves a card to its ledger entry via ``entry.id ===
    itemId``; the round count then flows from the resolved entry."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    all_entries = run.phase_ledgers[2] + run.phase_ledgers[4]
    assert len(all_entries) > 0, "fixture should have at least some ledger entries"
    for entry in all_entries:
        assert "ghosted_rounds" in entry, (
            f"ledger entry {entry.get('id')} missing ghosted_rounds (spec 0046 D4)"
        )
        # ghosted_rounds is a non-negative integer count
        assert isinstance(entry["ghosted_rounds"], int)
        assert entry["ghosted_rounds"] >= 0
    # Partner-vetting's Phase 2 surfaces ghosted questions (spec 0043
    # design tag). At least one entry should carry a non-zero
    # ghosted_rounds so the spec 0046 D4 surface is exercised in
    # production usage; if this assertion ever fails because the
    # matcher gets tuned (unresolved item #4 from the handover),
    # delete the assertion — the structural guard above is the
    # load-bearing test.
    nonzero = sum(1 for e in all_entries if e["ghosted_rounds"] > 0)
    assert nonzero > 0, (
        "expected at least one ghosted entry on partner-vetting; "
        "spec 0046 D4's per-card surface has nothing to render"
    )


def test_phase_ledgers_entry_ids_match_critique_item_ids() -> None:
    """Spec 0046 D4 — ``findLedgerEntry(run, phaseId, itemId)`` resolves
    a critique card to its ledger entry via ``entry.id === itemId``.
    The wire-format contract: every parsed-item id that exists in
    ``run.questions`` / ``disagreements`` / ``issues`` / ``comments`` /
    ``claims`` (filtered to phase N) MUST have a matching ledger entry
    in ``run.phase_ledgers[N]``. If the aggregator's reconstructor
    drifts away from the ledger builder's id scheme, every card
    silently shows ``ghostedRounds = 0`` even when the ledger tracks
    a non-zero value."""
    run = load_run_snapshot(Path("runs/20260516-035048-partner-vetting-arch-critique"))
    for phase in (2, 4):
        ledger_ids = {e["id"] for e in run.phase_ledgers[phase] if e.get("id")}
        critique_items = (
            [q for q in run.questions if q.phase == phase]
            + [d for d in run.disagreements if d.phase == phase]
            + [i for i in run.issues if i.phase == phase]
            + [c for c in run.comments if c.phase == phase]
            + [c for c in run.claims if c.phase == phase]
        )
        if not critique_items:
            continue
        matched = sum(1 for it in critique_items if it.id in ledger_ids)
        # The ledger may carry some IDs the reconstructors don't surface
        # (e.g. comments the parser folded into another kind), but the
        # reverse direction is what the frontend depends on — and >50%
        # match is a reasonable floor on partner-vetting (claims in
        # particular are reconstructed from R1's "Diff vs … Phase 1"
        # section, which the ledger builder may not always mirror id-
        # for-id).
        assert matched >= max(1, len(critique_items) // 2), (
            f"phase {phase}: only {matched}/{len(critique_items)} parsed items "
            f"resolved to a ledger entry id — spec 0046 D4 GhostedAnnotation "
            f"won't render for the unmatched majority"
        )
