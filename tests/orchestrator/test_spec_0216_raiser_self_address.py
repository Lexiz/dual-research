"""Spec 0216 — raiser self-ADDRESS observability.

Locks in that when an agent emits an ADDRESS block targeting an item it
itself raised (protocol-forbidden — only the *other* agent's items can be
addressed), the orchestrator emits a
``ProtocolViolation(violation_code="raiser_self_address", …)`` event
*before* the silent drop. Drop semantics are preserved.

Pre-fix: silent ``continue`` at ``deep_research.py:378-381`` swallowed
the misuse; the dashboard and transcript showed nothing.

Smoking gun on disk: ``runs/20260521-010637-dvs-backend-language-choice/
phase2/round-04-claude.md`` — Claude (raiser of ``D-plan-c-05``)
re-ADDRESSed its own item in the "Addressing items raised against me"
section. The replay fixture below was copied from that file into
``tests/fixtures/raiser_self_address_replay/round-04-claude.md``.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State
from dual_research.contract.operations import AddressBlock
from dual_research.events import ProtocolViolation
from dual_research.orchestrator.deep_research import (
    DeepResearchPhase,
    LedgerEntryV2,
)
from dual_research.protocol.parse import parse_turn_v2
from dual_research.protocol.parse_v2 import ParsedTurnV2


_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "raiser_self_address_replay"


def _seed_phase_with_disagreement(
    *, raiser: str, current_state: State, item_id: str = "D-plan-g-01"
) -> tuple[DeepResearchPhase, LedgerEntryV2]:
    """Phase 2 DR phase with one disagreement seeded in ``current_state``."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    entry = LedgerEntryV2(
        id=item_id,
        kind=Category.DISAGREEMENT,
        phase=2,
        raiser=raiser,
        body="we hold X.",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=current_state,
        raised_round=1,
    )
    phase.state.ledger.append(entry)
    return phase, entry


def test_raiser_self_address_emits_protocol_violation_with_item_id_and_from_state():
    """Spec 0216 — agent ADDRESSes its own ``open`` item.

    Pre-fix: dropped silently with no event. Post-fix: emits a
    ``ProtocolViolation(violation_code="raiser_self_address", ...)`` and
    preserves the drop (item state stays ``open``).
    """
    phase, entry = _seed_phase_with_disagreement(
        raiser="claude", current_state=State.OPEN,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="I'm re-addressing my own item.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: I'm re-addressing my own item.\n",
        )],
    )

    raised, transitions, violations, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=3,
        is_closeout_round=False,
    )

    assert raised == []
    assert transitions == []
    assert len(violations) == 1
    pv = violations[0]
    assert isinstance(pv, ProtocolViolation)
    assert pv.violation_code == "raiser_self_address"
    assert pv.item_id == "D-plan-g-01"
    assert pv.from_state == "open"
    assert pv.agent == "claude"
    assert pv.phase == 2
    assert pv.round == 3
    assert pv.dropped_block  # non-empty raw-text snapshot
    # Drop semantics preserved — state unchanged.
    assert entry.current_state == State.OPEN


def test_raiser_self_address_emits_violation_when_own_item_is_addressed_state():
    """Spec 0216 smoking-gun scenario — raiser re-ADDRESSes own item
    already in ``addressed`` state (the failing-run pattern). Violation
    fires; item stays in ``addressed`` (no re-ADDRESS, no state regression).
    """
    phase, entry = _seed_phase_with_disagreement(
        raiser="claude", current_state=State.ADDRESSED,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="re-addressing.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: re-addressing.\n",
        )],
    )

    raised, transitions, violations, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=4,
        is_closeout_round=False,
    )

    assert transitions == []
    assert len(violations) == 1
    pv = violations[0]
    assert isinstance(pv, ProtocolViolation)
    assert pv.violation_code == "raiser_self_address"
    assert pv.from_state == "addressed"
    # State did not regress.
    assert entry.current_state == State.ADDRESSED


def test_replay_round04_claude_self_address_emits_violation():
    """Replay the real failing turn from the smoking-gun run.

    Fixture: ``tests/fixtures/raiser_self_address_replay/round-04-claude.md``,
    copied verbatim from ``runs/20260521-010637-dvs-backend-language-choice/
    phase2/round-04-claude.md``. Claude raised ``D-plan-c-05`` in an
    earlier round; OpenAI ADDRESSed it (state → ``addressed``); this turn
    is Claude re-ADDRESSing its own item.
    """
    text = (_FIXTURE_DIR / "round-04-claude.md").read_text()
    parsed = parse_turn_v2(text)
    # The fixture's "Addressing items raised against me" section
    # contains one ADDRESS block targeting D-plan-c-05.
    address_blocks = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    assert len(address_blocks) == 1
    assert address_blocks[0].item_id == "D-plan-c-05"

    phase, entry = _seed_phase_with_disagreement(
        raiser="claude", current_state=State.ADDRESSED, item_id="D-plan-c-05",
    )

    raised, transitions, violations, empty_turns = phase.apply_turn(
        text=text,
        parsed=parsed,
        agent="claude",
        round=4,
        is_closeout_round=False,
    )

    assert transitions == []
    self_addr = [v for v in violations
                 if isinstance(v, ProtocolViolation)
                 and v.violation_code == "raiser_self_address"]
    assert len(self_addr) == 1
    pv = self_addr[0]
    assert pv.item_id == "D-plan-c-05"
    assert pv.agent == "claude"
    assert pv.from_state == "addressed"
    assert entry.current_state == State.ADDRESSED


def test_other_agent_address_does_not_emit_raiser_self_address():
    """Negative — agent Y (not raiser) ADDRESSes item I. No
    ``raiser_self_address`` violation; state transitions normally to
    ``addressed``. Locks in we didn't broaden the gate.
    """
    phase, entry = _seed_phase_with_disagreement(
        raiser="openai", current_state=State.OPEN,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="here's my response.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: here's my response.\n",
        )],
    )

    raised, transitions, violations, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=3,
        is_closeout_round=False,
    )

    self_addr = [v for v in violations
                 if isinstance(v, ProtocolViolation)
                 and v.violation_code == "raiser_self_address"]
    assert self_addr == []
    # Happy-path transition occurred: open → addressed.
    assert entry.current_state == State.ADDRESSED
    assert len(transitions) == 1


def test_raiser_resolve_or_withdraw_does_not_emit_violation():
    """Negative — raiser legitimately ratifies their own item via
    RESOLVE / WITHDRAW (the prescribed actions for ``addressed`` items).
    No ``raiser_self_address`` violation.

    Spec 0216 §5 covers RESOLVE/ACKNOWLEDGE/WITHDRAW/counter-argument.
    RESOLVE and WITHDRAW are the two that route through the typed-block
    handlers in ``apply_turn``; ACKNOWLEDGE and counter-arguments are
    handled by other code paths and would never reach the
    ``raiser == agent`` branch in the ADDRESS handler.
    """
    from dual_research.contract.operations import ResolveBlock, WithdrawBlock

    for block_cls, raw, reason in [
        (ResolveBlock, "### RESOLVE D-plan-g-01\nreason: agreed.\n", "agreed."),
        (WithdrawBlock, "### WITHDRAW D-plan-g-01\nreason: stale.\n", "stale."),
    ]:
        phase, entry = _seed_phase_with_disagreement(
            raiser="claude", current_state=State.ADDRESSED,
        )
        parsed = ParsedTurnV2(status="IN_PROGRESS", blocks=[block_cls(
            item_id="D-plan-g-01", reason=reason, raw_text=raw,
        )])

        raised, transitions, violations, empty_turns = phase.apply_turn(
            text="", parsed=parsed, agent="claude", round=3,
            is_closeout_round=False,
        )
        self_addr = [v for v in violations
                     if isinstance(v, ProtocolViolation)
                     and v.violation_code == "raiser_self_address"]
        assert self_addr == [], (
            f"{block_cls.__name__}: unexpected raiser_self_address violation"
        )
