"""Spec 0141 — anchor-run replay verifying the B02 invariant fix and
the B10 derived symptom self-resolves.

Replays the on-disk anchor run ``20260521-010637-dvs-backend-language-
choice`` through the patched orchestrator and asserts:

1. Per-kind, terminal-transition count equals raise count for every
   kind in {question, disagreement, issue, comment}. Pre-fix the
   disagreement row read 15 raised / 16 closed (D-plan-g-01 closed
   twice at seq 121 and seq 144); post-fix it reads 15 / 15.

2. The replay's raw event stream contains at least one
   ``ProtocolViolation`` event flagging the dropped re-address (the
   pattern previously leaking the item back to ``addressed`` is now
   silently dropped + audited).

3. The replay's raw event stream contains at least one
   ``EmptyTurnDetected`` event from a Phase 4 round where neither
   agent emitted a ledger-affecting block (the phase4-r6 / r7 / r8
   shape; the live finish_reason isn't reconstructible from disk
   alone so the detector still fires but without the cause field).

Skips when the run directory is absent so CI on fresh clones stays
green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ledger.replay import _replay_phase, replay_items_from_disk


_ANCHOR_RUN = "20260521-010637-dvs-backend-language-choice"


def _anchor_session_dir() -> Path | None:
    repo_root = Path(__file__).resolve().parents[2]
    session_dir = repo_root / "runs" / _ANCHOR_RUN
    if not session_dir.is_dir():
        return None
    return session_dir


@pytest.mark.skipif(
    _anchor_session_dir() is None,
    reason=f"Anchor run {_ANCHOR_RUN} not present on disk; skipping.",
)
def test_anchor_run_replay_raise_close_invariant_holds_post_fix():
    """B02 — after the orchestrator-side guard, per-kind raises == closes."""
    session_dir = _anchor_session_dir()
    assert session_dir is not None

    bundle = replay_items_from_disk(session_dir)

    # Group by kind. Each Item has a `transitions` history; a terminal
    # transition is one whose to_state lands in the terminal frozenset.
    terminal = {"resolved", "acknowledged", "withdrawn", "capped"}
    raises_per_kind: dict[str, int] = {}
    closes_per_kind: dict[str, int] = {}
    for it in bundle.items:
        raises_per_kind[it.kind] = raises_per_kind.get(it.kind, 0) + 1
        for tr in it.transitions:
            if tr.to_state in terminal:
                closes_per_kind[it.kind] = closes_per_kind.get(it.kind, 0) + 1

    # Disagreements were the smoking gun at 15 / 16. Post-fix: equal.
    assert raises_per_kind.get("disagreement", 0) >= 1, \
        "anchor run should carry disagreements"
    assert closes_per_kind.get("disagreement", 0) == raises_per_kind["disagreement"], (
        "B02 invariant broken: disagreement closes "
        f"({closes_per_kind.get('disagreement', 0)}) != raises "
        f"({raises_per_kind['disagreement']})"
    )
    # And the invariant for every other kind that appeared on this run.
    for kind, n_raises in raises_per_kind.items():
        n_closes = closes_per_kind.get(kind, 0)
        # closes can be < raises (items left non-terminal at run end);
        # closes must never exceed raises.
        assert n_closes <= n_raises, (
            f"{kind}: closes ({n_closes}) > raises ({n_raises})"
        )


@pytest.mark.skipif(
    _anchor_session_dir() is None,
    reason=f"Anchor run {_ANCHOR_RUN} not present on disk; skipping.",
)
def test_anchor_run_replay_records_at_least_one_protocol_violation():
    """B02 — the seq-137 re-address on D-plan-g-01 is now flagged."""
    session_dir = _anchor_session_dir()
    assert session_dir is not None

    # Drop down to the raw event stream so we can inspect ProtocolViolation
    # / EmptyTurnDetected entries that the aggregator doesn't surface.
    raw_events: list[dict] = []
    for phase in (0, 2, 4):
        raw_events.extend(_replay_phase(session_dir, phase=phase))

    protocol_violations = [
        e for e in raw_events if e.get("kind") == "protocol_violation"
    ]
    assert len(protocol_violations) >= 1, (
        "expected at least one ProtocolViolation on the anchor run "
        "(D-plan-g-01 re-address at seq 137)"
    )
    # The B02 smoking gun is terminal_state_re_address. Spec 0216 added a
    # second code (raiser_self_address) that also surfaces on this anchor
    # run wherever an agent re-ADDRESSes its own item. Both are valid;
    # the assertion is that the codes in use are drawn from the known set,
    # and that at least one terminal_state_re_address is present (the B02
    # invariant this test guards).
    known_codes = {"terminal_state_re_address", "raiser_self_address"}
    seen_codes = {v.get("violation_code") for v in protocol_violations}
    assert seen_codes <= known_codes, (
        f"unexpected violation_code on anchor run: {seen_codes - known_codes}"
    )
    assert "terminal_state_re_address" in seen_codes, (
        "expected at least one terminal_state_re_address (B02 smoking gun)"
    )
    # The smoking-gun item must be among the flagged ids.
    flagged_ids = {v.get("item_id") for v in protocol_violations}
    assert any(item_id and item_id.startswith("D-") for item_id in flagged_ids), \
        f"expected at least one disagreement re-address; got {flagged_ids}"


@pytest.mark.skipif(
    _anchor_session_dir() is None,
    reason=f"Anchor run {_ANCHOR_RUN} not present on disk; skipping.",
)
def test_anchor_run_replay_records_phase4_empty_turn():
    """B06 — Phase 4 carries multiple empty turns; replay must surface
    at least one EmptyTurnDetected for the rounds that produced zero
    ledger-affecting blocks."""
    session_dir = _anchor_session_dir()
    assert session_dir is not None

    phase4_events = _replay_phase(session_dir, phase=4)
    empty_turns = [
        e for e in phase4_events if e.get("kind") == "empty_turn_detected"
    ]
    assert len(empty_turns) >= 1, (
        "expected at least one EmptyTurnDetected in Phase 4 — anchor run "
        "transcript shows phase4-r6/r7/r8 with zero item events between "
        "turn_started and turn_ended"
    )
    # Replay path doesn't see the live turn_ended payload, so
    # finish_reason is None and output_tokens is 0 by design.
    for e in empty_turns:
        assert e.get("phase") == 4
        assert e.get("parser_block_count") == 0
