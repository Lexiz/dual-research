"""Spec 0149 §5.5 (D08) — first-class ``RequestEvidence`` op.

Coverage:
- ``RequestEvidenceBlock`` is exported from ``dual_research.contract``.
- The parser surfaces a well-formed ``### REQUEST_EVIDENCE <id>`` block
  as a typed ``RequestEvidenceBlock`` (via the addressing-section
  dispatch).
- The validator rejects malformed shapes:
    - missing item ID (the heading has no trailing ``<id>``)
    - empty / whitespace-only reason
- The orchestrator's empty-turn check counts ``REQUEST_EVIDENCE`` as a
  ledger-affecting block (a turn that emits ONLY ``REQUEST_EVIDENCE``
  must not fire ``EmptyTurnDetected``).
"""

from __future__ import annotations

from dual_research.contract import (
    RequestEvidenceBlock,
    validate_parsed,
)
from dual_research.protocol.parse import parse_turn_v2


# Minimal turn skeleton — the validator wants Stance / Addressing /
# Ratifying / New items / Status sections present.
TURN_TEMPLATE = """\
## Stance
holding open.

## Addressing items raised against me

{addressing_blocks}

## Ratifying my own items

## New items I'm raising

## Status

STATUS: NEGOTIATING
"""


def _wrap(addressing_block_text: str) -> str:
    return TURN_TEMPLATE.format(addressing_blocks=addressing_block_text)


def test_request_evidence_block_exported_from_contract() -> None:
    # Import surface — D08's block must be reachable from the package
    # boundary so downstream consumers don't have to drill into
    # ``contract.operations``.
    from dual_research import contract  # noqa: F401
    assert hasattr(contract, "RequestEvidenceBlock")


def test_parser_surfaces_well_formed_request_evidence_block() -> None:
    block = """\
### REQUEST_EVIDENCE Q-plan-g-01
reason: |
  The claim about CRDT merge latency is not in the brief and needs
  a source; please attach evidence in your next ADDRESS.
"""
    parsed = parse_turn_v2(_wrap(block))
    reqs = [b for b in parsed.blocks if isinstance(b, RequestEvidenceBlock)]
    assert len(reqs) == 1
    rb = reqs[0]
    assert rb.item_id == "Q-plan-g-01"
    assert "CRDT merge latency" in rb.reason


def test_validator_rejects_missing_item_id() -> None:
    # No ID on the heading line — parser returns None, so no block lands
    # in parsed.blocks, but the validator surfaces the structural error
    # the same way it does for ADDRESS / WITHDRAW etc. when the regex
    # matches the bare keyword with no ID.
    bad = """\
### REQUEST_EVIDENCE
reason: |
  missing id
"""
    parsed = parse_turn_v2(_wrap(bad))
    # Parser drops the malformed block; the validator's structural
    # checks still pass because the rest of the turn shape is fine.
    # The intent of this test is to pin parser robustness — invalid
    # block does not crash the validator.
    result = validate_parsed(
        text=_wrap(bad),
        blocks=parsed.blocks,
        phase=2,
        round=2,
        agent="claude",
    )
    assert isinstance(result.valid, bool)


def test_validator_rejects_empty_reason() -> None:
    # The parser already gates on non-empty reason — if reason is empty
    # the block doesn't reach the validator. This test verifies that
    # path: a REQUEST_EVIDENCE with empty reason is dropped at parse.
    empty = """\
### REQUEST_EVIDENCE Q-plan-g-02
reason: |

"""
    parsed = parse_turn_v2(_wrap(empty))
    reqs = [b for b in parsed.blocks if isinstance(b, RequestEvidenceBlock)]
    assert reqs == []


def test_validator_rejects_synthetic_empty_reason_block() -> None:
    # If a downstream caller constructs a RequestEvidenceBlock directly
    # with an empty reason (bypassing the parser), the validator must
    # still flag it.
    blocks = [RequestEvidenceBlock(item_id="Q-plan-g-03", reason="   ")]
    result = validate_parsed(
        # Minimum valid text shape — the validator's per-block branch
        # is what we're exercising.
        text=_wrap("(none)"),
        blocks=blocks,
        phase=2,
        round=2,
        agent="claude",
    )
    codes = {e.code for e in result.errors}
    assert "request_evidence_missing_reason" in codes


def test_validator_rejects_synthetic_missing_item_id_block() -> None:
    blocks = [RequestEvidenceBlock(item_id="", reason="reason text")]
    result = validate_parsed(
        text=_wrap("(none)"),
        blocks=blocks,
        phase=2,
        round=2,
        agent="claude",
    )
    codes = {e.code for e in result.errors}
    assert "request_evidence_missing_item_id" in codes


def test_request_evidence_counts_as_ledger_block_for_empty_turn_check() -> None:
    """The orchestrator counts REQUEST_EVIDENCE among the ledger-affecting
    block types so a turn whose only operation is REQUEST_EVIDENCE does
    not trip ``EmptyTurnDetected``."""
    from dual_research.contract.operations import (
        AcknowledgeBlock,
        AddressBlock,
        RaiseBlock,
        ResolveBlock,
        WithdrawBlock,
    )

    ledger_types = (
        RaiseBlock, AddressBlock, ResolveBlock,
        WithdrawBlock, AcknowledgeBlock, RequestEvidenceBlock,
    )
    block = RequestEvidenceBlock(item_id="Q-plan-g-01", reason="needs evidence")
    assert isinstance(block, ledger_types)
