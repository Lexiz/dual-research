"""Spec 0122 follow-up — parser tolerance for real-world agent output.

Two regressions surfaced during the 20260520-025406 deep-research run:

1. **Glued-on body text.** Agents sometimes emit the operation block
   opener and the response body on the same line without a newline:
   ``### ADDRESS Q-plan-c-01The rest of the response...``. The pre-fix
   ``OP_ADDRESS_RE`` used ``\\s+(?P<id>\\S+)\\s*$`` which required the
   line to end immediately after the ID, so the entire ADDRESS was
   silently dropped.

2. **Duplicate section headings.** Agents occasionally write a private
   reasoning preamble that includes its own ``## Stance`` and
   ``## Addressing items raised against me`` lines before the canonical
   structured turn. The naive ``pattern.search(...)`` picked the FIRST
   occurrence, which contained the freeform reasoning and none of the
   real operation blocks.

Both regressions caused phase 2 r2 (claude) in that run to parse as
zero ADDRESS blocks instead of the actual six, leading to two items
incorrectly capped via ghost_cap. After the fix every item resolves
organically through its full lifecycle.
"""

from __future__ import annotations

from dual_research.contract.operations import (
    AddressBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.protocol.parse import parse_turn_v2


def test_address_block_with_glued_body_on_opener_line():
    """The opener line ``### ADDRESS Q-plan-c-01<body...>`` should still
    parse the ID cleanly. The trailing text becomes opener-adjacent
    content; the body comes from the ``response: |`` field as usual."""
    text = """\
## Stance
.

## Addressing items raised against me

### ADDRESS Q-plan-c-01The agent forgot to insert a newline here.
response: |
  Substantive response goes here.
proposes_status: addressed

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [Q-plan-c-01]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
"""
    parsed = parse_turn_v2(text)
    addrs = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    assert len(addrs) == 1
    assert addrs[0].item_id == "Q-plan-c-01"
    assert "Substantive response" in addrs[0].response


def test_resolve_and_withdraw_tolerate_glued_body():
    """Same tolerance must apply to RESOLVE / WITHDRAW (the other
    raiser-side operations)."""
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items

### RESOLVE D-plan-c-01Glued-on rationale that should be ignored.
reason: |
  Counterpart accepted my correction.

### WITHDRAW Q-plan-c-02also glued
reason: |
  Question no longer relevant after upstream concession.

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: [D-plan-c-01]
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: [Q-plan-c-02]
OPEN_QUESTIONS: 0
"""
    parsed = parse_turn_v2(text)
    resolves = [b for b in parsed.blocks if isinstance(b, ResolveBlock)]
    withdraws = [b for b in parsed.blocks if isinstance(b, WithdrawBlock)]
    assert len(resolves) == 1
    assert resolves[0].item_id == "D-plan-c-01"
    assert "Counterpart accepted" in resolves[0].reason
    assert len(withdraws) == 1
    assert withdraws[0].item_id == "Q-plan-c-02"
    assert "no longer relevant" in withdraws[0].reason


def test_duplicate_section_heading_prefers_block_dense_occurrence():
    """When a section heading matches multiple times (e.g. private
    reasoning preamble + canonical structured turn), the parser must
    pick the occurrence whose body actually contains operation blocks.
    """
    text = """\
## Stance
First-pass reasoning — what's my read of the prior round?

## Addressing items raised against me

(No actual ADDRESS blocks here; this is the preamble's stub.)

## Stance
The canonical structure now follows.

## Addressing items raised against me

### ADDRESS D-plan-g-01
response: |
  I accept the correction.
proposes_status: addressed

### ADDRESS D-plan-g-02
response: |
  Same here.
proposes_status: addressed

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [D-plan-g-01, D-plan-g-02]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
"""
    parsed = parse_turn_v2(text)
    addrs = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    # Without the duplicate-heading fix, the parser would lock onto the
    # FIRST ``## Addressing items raised against me`` and find zero
    # ADDRESS blocks. With the fix it picks the section body that
    # contains operation block openers.
    assert len(addrs) == 2
    assert {a.item_id for a in addrs} == {"D-plan-g-01", "D-plan-g-02"}


def test_single_section_unchanged_legacy_behaviour():
    """Sanity: turns with one section heading per type still parse the
    same as before — no regression introduced by the duplicate-heading
    handling.
    """
    text = """\
## Stance
Concise position.

## Addressing items raised against me

### ADDRESS D-plan-g-01
response: |
  Accepted.
proposes_status: addressed

## Ratifying my own items
(none)

## New items I'm raising

### RAISE
kind: disagreement
body: |
  New disagreement here.
anchor_type: none
anchor_text: ""
evidence_required: false

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [D-plan-c-04]
ADDRESSED_THIS_TURN: [D-plan-g-01]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
"""
    parsed = parse_turn_v2(text)
    addrs = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    raises = [b for b in parsed.blocks if not isinstance(b, (AddressBlock, ResolveBlock, WithdrawBlock))]
    assert len(addrs) == 1
    assert addrs[0].item_id == "D-plan-g-01"
    assert len(raises) == 1
