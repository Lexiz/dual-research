"""Spec 0114 — new-protocol parser output shape.

The new parser returns a ``ParsedTurnV2`` instead of the legacy
``ParsedTurn``. It carries typed operation blocks, the per-turn STATUS
value, the action-array IDs, and the optional phase artifact text.

The actual parser implementation lives in step 5 (``parse_turn_v2`` in
``protocol/parse.py``). closeout.py and the validator depend on this
shape and import it from here so the type contract is stable while the
parser is being built.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    OperationBlock,
    RaiseBlock,
    ResolveBlock,
    WithdrawBlock,
)


@dataclass(frozen=True)
class ParsedTurnV2:
    """Output of the new-protocol parser.

    ``blocks`` carries every operation block in turn order. ``status``
    is the ``STATUS:`` line value (``"IN_PROGRESS"`` / ``"AGREED"``) or
    ``None`` when malformed. Action-array fields are parsed from the
    ``RAISED_THIS_TURN`` / ``ADDRESSED_THIS_TURN`` / … lines in the
    status footer. The phase artifact body (``AGREED_INTERPRETATION``
    / ``AGREED_PLAN`` / ``AGREED_DRAFT_ACCEPTANCE``) is captured
    verbatim when present; absent in non-AGREED turns.

    ``counters`` is a flat dict of self-reported per-kind counts
    (``"OPEN_QUESTIONS"`` → int, etc.). Missing counters are absent
    from the dict, not zero — so the orchestrator can distinguish
    "agent reported 0" from "agent didn't emit the field at all".
    """

    status: str | None
    blocks: list[OperationBlock] = field(default_factory=list)
    raised_this_turn: list[str] = field(default_factory=list)
    addressed_this_turn: list[str] = field(default_factory=list)
    resolved_this_turn: list[str] = field(default_factory=list)
    acknowledged_this_turn: list[str] = field(default_factory=list)
    withdrawn_this_turn: list[str] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)
    phase_artifact: str | None = None
    revised_draft: str | None = None
    stance: str | None = None


def raise_blocks(parsed: ParsedTurnV2) -> list[RaiseBlock]:
    """Return only the RaiseBlocks from ``parsed.blocks``."""
    return [b for b in parsed.blocks if isinstance(b, RaiseBlock)]


def address_blocks(parsed: ParsedTurnV2) -> list[AddressBlock]:
    return [b for b in parsed.blocks if isinstance(b, AddressBlock)]


def resolve_blocks(parsed: ParsedTurnV2) -> list[ResolveBlock]:
    return [b for b in parsed.blocks if isinstance(b, ResolveBlock)]


def acknowledge_blocks(parsed: ParsedTurnV2) -> list[AcknowledgeBlock]:
    return [b for b in parsed.blocks if isinstance(b, AcknowledgeBlock)]


def withdraw_blocks(parsed: ParsedTurnV2) -> list[WithdrawBlock]:
    return [b for b in parsed.blocks if isinstance(b, WithdrawBlock)]
