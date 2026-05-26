"""Spec 0228 — ProtocolViolation emission on state-machine-invalid ops.

Locks in that every ``apply_turn`` rejection driven by a state-machine
guard (``ent.current_state``, ``ent.raiser``, ``is_terminal(…)``) emits a
``ProtocolViolation`` so the verifier's I4.4 invariant — flipped from
``reporting`` to ``gating`` in this spec — can fire on it.

Six new emission sites per spec 0228 §2.1:

- ``resolve_wrong_raiser``        — RESOLVE by non-raiser.
- ``resolve_from_non_addressed``  — RESOLVE on item not in ``addressed`` (the
                                    dead-fixture smoking gun).
- ``withdraw_wrong_raiser``       — WITHDRAW by non-raiser.
- ``withdraw_terminal_state``     — WITHDRAW on a terminal-state item.
- ``acknowledge_terminal_state``  — ACKNOWLEDGE on a terminal-state item.
- ``address_already_addressed``   — ADDRESS on already-addressed (idempotent).

Plus the dead-fixture replay test asserting all four r2-claude RESOLVE
ops from ``20260526-102321-backend-language-choice`` emit one
``resolve_from_non_addressed`` each.

The two pre-0228 emission sites (``raiser_self_address`` and
``terminal_state_re_address``) get checks that the new structured
fields (``op_kind`` / ``expected_state`` / ``reason``) are populated.

Drop semantics are unchanged across the board: the rejection emits an
event AND the ledger item's state stays unchanged. Behavioural change
limited to observability.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.events import ProtocolViolation
from dual_research.orchestrator.deep_research import (
    DeepResearchPhase,
    LedgerEntryV2,
)
from dual_research.protocol.parse import parse_turn_v2


# ─── Helpers ───────────────────────────────────────────────────────────


def _seed_phase_with_item(
    *,
    raiser: str,
    current_state: State,
    item_id: str = "D-plan-g-01",
    kind: Category = Category.DISAGREEMENT,
    phase_no: int = 2,
) -> tuple[DeepResearchPhase, LedgerEntryV2]:
    phase = DeepResearchPhase(phase=phase_no, agent_turn=lambda req: "")
    entry = LedgerEntryV2(
        id=item_id,
        kind=kind,
        phase=phase_no,
        raiser=raiser,
        body="x.",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=current_state,
        raised_round=1,
    )
    phase.state.ledger.append(entry)
    return phase, entry


def _only_violation(violations) -> ProtocolViolation:
    assert len(violations) == 1, f"expected exactly one violation, got {violations!r}"
    pv = violations[0]
    assert isinstance(pv, ProtocolViolation)
    return pv


# ─── Per-site unit tests (spec 0228 §2.1, six new sites) ───────────────


def test_resolve_wrong_raiser_emits_protocol_violation():
    """RESOLVE issued by the non-raiser is rejected (state machine
    requires raiser ownership). Pre-0228 the rejection silent-``continue``'d;
    post-0228 it emits ``resolve_wrong_raiser``."""
    phase, entry = _seed_phase_with_item(
        raiser="openai", current_state=State.ADDRESSED,
    )
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### RESOLVE D-plan-g-01\n"
        "reason: closing this.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "resolve_wrong_raiser"
    assert pv.op_kind == "resolve"
    assert pv.item_id == "D-plan-g-01"
    assert pv.agent == "claude"
    assert pv.phase == 2
    assert pv.round == 2
    assert pv.from_state == "addressed"
    assert pv.expected_state == ""
    assert "raised by openai" in pv.reason
    assert pv.dropped_block  # raw text snapshot
    # Drop semantics — item stays addressed.
    assert entry.current_state == State.ADDRESSED


def test_resolve_from_non_addressed_emits_protocol_violation():
    """RESOLVE on an item still in ``open`` is the dead-fixture smoking
    gun (four such ops on round-02-claude.md). Emits
    ``resolve_from_non_addressed`` with expected_state='addressed'."""
    phase, entry = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN,
    )
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### RESOLVE D-plan-g-01\n"
        "reason: closing.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "resolve_from_non_addressed"
    assert pv.op_kind == "resolve"
    assert pv.from_state == "open"
    assert pv.expected_state == "addressed"
    assert "expected 'addressed'" in pv.reason
    assert entry.current_state == State.OPEN


def test_withdraw_wrong_raiser_emits_protocol_violation():
    """WITHDRAW must be emitted by the item's raiser. Emits
    ``withdraw_wrong_raiser``."""
    phase, entry = _seed_phase_with_item(
        raiser="openai", current_state=State.OPEN,
    )
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### WITHDRAW D-plan-g-01\n"
        "reason: dropping.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "withdraw_wrong_raiser"
    assert pv.op_kind == "withdraw"
    assert pv.from_state == "open"
    assert "raised by openai" in pv.reason
    assert entry.current_state == State.OPEN


def test_withdraw_terminal_state_emits_protocol_violation():
    """WITHDRAW on a terminal-state item is the sibling rejection to
    terminal_state_re_address. Emits ``withdraw_terminal_state`` with
    expected_state='open,addressed'."""
    phase, entry = _seed_phase_with_item(
        raiser="claude", current_state=State.RESOLVED,
    )
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### WITHDRAW D-plan-g-01\n"
        "reason: dropping.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=3, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "withdraw_terminal_state"
    assert pv.op_kind == "withdraw"
    assert pv.from_state == "resolved"
    assert pv.expected_state == "open,addressed"
    assert "terminal-state item" in pv.reason
    assert entry.current_state == State.RESOLVED


def test_acknowledge_terminal_state_emits_protocol_violation():
    """ACKNOWLEDGE on a terminal-state item is rejected. Emits
    ``acknowledge_terminal_state``."""
    phase, entry = _seed_phase_with_item(
        raiser="openai", current_state=State.WITHDRAWN,
    )
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### ACKNOWLEDGE D-plan-g-01\n"
        "reason: ack.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=3, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "acknowledge_terminal_state"
    assert pv.op_kind == "acknowledge"
    assert pv.from_state == "withdrawn"
    assert pv.expected_state == "open,addressed"
    assert entry.current_state == State.WITHDRAWN


def test_address_already_addressed_emits_protocol_violation():
    """ADDRESS on an already-addressed item is the "ADDRESS on non-open"
    sibling. Pre-0228 this short-circuited silently as a "no-op";
    post-0228 it emits ``address_already_addressed``. The drop semantics
    are unchanged (no duplicate transition, item stays addressed)."""
    phase, entry = _seed_phase_with_item(
        raiser="openai", current_state=State.ADDRESSED,
    )
    parsed = parse_turn_v2(
        "## Addressing items raised against me\n"
        "### ADDRESS D-plan-g-01\n"
        "response: more thoughts.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=3, is_closeout_round=False,
    )
    assert transitions == []
    pv = _only_violation(violations)
    assert pv.violation_code == "address_already_addressed"
    assert pv.op_kind == "address"
    assert pv.from_state == "addressed"
    assert pv.expected_state == "open"
    assert entry.current_state == State.ADDRESSED


# ─── Pre-0228 sites retain behaviour + carry the new fields ────────────


def test_terminal_state_re_address_carries_op_kind_and_expected_state():
    """Spec 0141's ADDRESS-on-terminal emission gets the new structured
    fields from spec 0228."""
    phase, entry = _seed_phase_with_item(
        raiser="openai", current_state=State.RESOLVED,
    )
    parsed = parse_turn_v2(
        "## Addressing items raised against me\n"
        "### ADDRESS D-plan-g-01\n"
        "response: re-opening.\n"
    )
    _, _, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=3, is_closeout_round=False,
    )
    pv = _only_violation(violations)
    assert pv.violation_code == "terminal_state_re_address"
    assert pv.op_kind == "address"
    assert pv.expected_state == "open,addressed"
    assert pv.from_state == "resolved"


def test_raiser_self_address_carries_op_kind():
    """Spec 0216's raiser-self-ADDRESS emission gets the new structured
    fields (expected_state is empty — the issue is the actor, not the
    state)."""
    phase, _ = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN,
    )
    parsed = parse_turn_v2(
        "## Addressing items raised against me\n"
        "### ADDRESS D-plan-g-01\n"
        "response: my own item.\n"
    )
    _, _, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    pv = _only_violation(violations)
    assert pv.violation_code == "raiser_self_address"
    assert pv.op_kind == "address"
    assert pv.expected_state == ""
    assert "only the other agent may address" in pv.reason


# ─── ent is None silent path is preserved (parser/validator concern) ───


def test_resolve_unknown_item_stays_silent():
    """Per spec 0228 §2.1 identification rule, ``ent is None`` is NOT a
    state-machine guard — it's a parser/validator concern. The
    rejection stays silent (no ProtocolViolation)."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### RESOLVE D-plan-g-99\n"  # unknown id
        "reason: closing.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    assert violations == []


def test_withdraw_unknown_item_stays_silent():
    """Same as above for WITHDRAW."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### WITHDRAW D-plan-g-99\n"
        "reason: dropping.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    assert violations == []


def test_acknowledge_unknown_item_stays_silent():
    """Same as above for ACKNOWLEDGE."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    parsed = parse_turn_v2(
        "## Ratifying my own items\n"
        "### ACKNOWLEDGE D-plan-g-99\n"
        "reason: ack.\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="", parsed=parsed, agent="claude", round=2, is_closeout_round=False,
    )
    assert transitions == []
    assert violations == []


# ─── Replay test against the dead-fixture round-02-claude transcript ───


_DEAD_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures" / "anchor-runs"
    / "20260526-102321-backend-language-choice"
    / "phase2" / "round-02-claude.md"
)


def test_dead_fixture_round_02_claude_emits_four_resolve_from_non_addressed():
    """Spec 0228 §6 replay test — load the dead-fixture round-02-claude
    turn (claude turning first; openai has not yet addressed claude's
    four items that round, so they're still ``open``), feed it through
    ``apply_turn`` against a phase state seeded with the four items in
    ``open``, and assert exactly four ``resolve_from_non_addressed``
    events fire (one per dropped RESOLVE)."""
    assert _DEAD_FIXTURE.is_file(), f"missing fixture: {_DEAD_FIXTURE}"

    text = _DEAD_FIXTURE.read_text(encoding="utf-8")
    parsed = parse_turn_v2(text)

    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    expected_ids = ("D-plan-c-02", "D-plan-c-04", "D-plan-c-05", "Q-plan-c-01")
    # Seed the four items as openable claude raises. (Claude's raises in
    # round 1; they reach round 2 still in ``open`` because openai
    # hadn't ADDRESSED them yet.)
    for item_id in expected_ids:
        kind = Category.QUESTION if item_id.startswith("Q-") else Category.DISAGREEMENT
        phase.state.ledger.append(LedgerEntryV2(
            id=item_id,
            kind=kind,
            phase=2,
            raiser="claude",
            body="seeded.",
            anchor_type="none",
            anchor_text="",
            evidence_required=False,
            current_state=State.OPEN,
            raised_round=1,
        ))

    _, _, violations, _ = phase.apply_turn(
        text=text,
        parsed=parsed,
        agent="claude",
        round=2,
        is_closeout_round=False,
    )

    # Exactly four resolve_from_non_addressed events on the four named
    # items; other violation codes may also fire (e.g. ADDRESS-related)
    # but we assert specifically on the dead-fixture smoking gun.
    rfna = [
        v for v in violations
        if isinstance(v, ProtocolViolation)
        and v.violation_code == "resolve_from_non_addressed"
    ]
    assert len(rfna) == 4, (
        f"expected four resolve_from_non_addressed events, got "
        f"{[(v.violation_code, v.item_id) for v in rfna]}"
    )
    cited_ids = {v.item_id for v in rfna}
    assert cited_ids == set(expected_ids), (
        f"expected ids {set(expected_ids)}, got {cited_ids}"
    )
    for v in rfna:
        assert v.from_state == "open"
        assert v.expected_state == "addressed"
        assert v.op_kind == "resolve"
        assert v.agent == "claude"
        assert v.phase == 2
        assert v.round == 2
