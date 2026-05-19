"""Spec 0114 — new-protocol parser tests.

Exercises ``parse_turn_v2`` against synthetic turn texts representing
every operation block type, the phase artifacts, the status footer
counters and action arrays, and the specific bug pattern from
runs/20260519-132908-backend-language-choice/phase4/round-03-claude.md
(spec 0114 § Parser updates).
"""

from __future__ import annotations

from dual_research.contract.categories import Category
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    RaiseBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.protocol.parse import (
    EVIDENCE_CHECKED_SECTION_RE,
    assign_raise_ids,
    extract_agreed_draft_acceptance,
    extract_agreed_interpretation_body,
    extract_agreed_plan_body,
    extract_drafter_from_agreed_plan,
    parse_turn_v2,
)


# ─── RAISE blocks ─────────────────────────────────────────────────────


def test_raise_block_basic():
    text = """\
## Stance
position.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
### RAISE
kind: question
body: |
  what does X mean here?
anchor_type: quote
anchor_text: the verbatim span
evidence_required: true
> quote: the verbatim span

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 1
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    assert parsed.status == "IN_PROGRESS"
    raises = [b for b in parsed.blocks if isinstance(b, RaiseBlock)]
    assert len(raises) == 1
    rb = raises[0]
    assert rb.kind == Category.QUESTION
    assert rb.body == "what does X mean here?"
    assert rb.anchor_type == "quote"
    assert rb.anchor_text == "the verbatim span"
    assert rb.evidence_required is True
    assert rb.blockquote_anchor == "the verbatim span"


def test_raise_block_disagreement_no_evidence():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
### RAISE
kind: disagreement
body: |
  i think the plan misses point Y.
anchor_type: after
anchor_text: Approach
evidence_required: false

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 1
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    raises = [b for b in parsed.blocks if isinstance(b, RaiseBlock)]
    assert raises[0].kind == Category.DISAGREEMENT
    assert raises[0].anchor_type == "after"
    assert raises[0].anchor_text == "Approach"
    assert raises[0].evidence_required is False


def test_raise_block_missing_kind_skipped():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
### RAISE
body: |
  malformed — no kind line.
anchor_type: none
anchor_text:
evidence_required: false

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    assert [b for b in parsed.blocks if isinstance(b, RaiseBlock)] == []


# ─── ADDRESS blocks ──────────────────────────────────────────────────


def test_address_block_with_evidence():
    text = """\
## Stance
.

## Addressing items raised against me
### ADDRESS D-plan-g-04
response: |
  the pkg.go.dev page corroborates the May 11 2026 figure.
evidence:
  - url: https://pkg.go.dev/github.com/anthropics/anthropic-sdk-go
    title: anthropic-sdk-go
    search_query: anthropic-sdk-go pkg.go.dev
    fetched_at: 2026-05-19T12:00:00Z
    evidence_event_id: srvtoolu_abc
    content_excerpt: |
      Published: May 11, 2026
      License: MIT
      Imported by: 372
proposes_status: addressed

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [D-plan-g-04]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 1
"""
    parsed = parse_turn_v2(text)
    addrs = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    assert len(addrs) == 1
    ab = addrs[0]
    assert ab.item_id == "D-plan-g-04"
    assert "pkg.go.dev page corroborates" in ab.response
    assert ab.proposes_status == "addressed"
    assert len(ab.evidence) == 1
    ev = ab.evidence[0]
    assert ev.url == "https://pkg.go.dev/github.com/anthropics/anthropic-sdk-go"
    assert ev.evidence_event_id == "srvtoolu_abc"
    assert "Published: May 11, 2026" in ev.content_excerpt
    assert ev.item_id == "D-plan-g-04"


def test_address_block_acknowledged_proposed():
    text = """\
## Stance
.

## Addressing items raised against me
### ADDRESS Q-plan-c-03
response: |
  i see no clean resolution path — propose mutual acknowledge.
proposes_status: acknowledged_proposed

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [Q-plan-c-03]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 1
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    addrs = [b for b in parsed.blocks if isinstance(b, AddressBlock)]
    assert addrs[0].proposes_status == "acknowledged_proposed"


# ─── RESOLVE / WITHDRAW / ACKNOWLEDGE blocks ─────────────────────────


def test_resolve_block():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
### RESOLVE Q-plan-c-02
reason: |
  the page-age evidence convinced me; mark this resolved.

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: [Q-plan-c-02]
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    resolves = [b for b in parsed.blocks if isinstance(b, ResolveBlock)]
    assert resolves[0].item_id == "Q-plan-c-02"
    assert "page-age evidence" in resolves[0].reason


def test_withdraw_block():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
### WITHDRAW D-plan-c-03
reason: |
  duplicate of D-plan-c-02; retracting.

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: [D-plan-c-03]
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    withdraws = [b for b in parsed.blocks if isinstance(b, WithdrawBlock)]
    assert withdraws[0].item_id == "D-plan-c-03"
    assert "duplicate" in withdraws[0].reason
    assert parsed.withdrawn_this_turn == ["D-plan-c-03"]


def test_acknowledge_in_ratifying_section():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
### ACKNOWLEDGE D-plan-c-01
reason: |
  no path to resolution in this run; concede mutual ack.

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: [D-plan-c-01]
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    acks = [b for b in parsed.blocks if isinstance(b, AcknowledgeBlock)]
    assert acks[0].item_id == "D-plan-c-01"
    assert acks[0].section == "ratifying"


def test_acknowledge_in_addressing_section_marks_section():
    text = """\
## Stance
.

## Addressing items raised against me
### ACKNOWLEDGE Q-plan-g-05
reason: |
  i see no path; proposing mutual ack as addressee.

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)
    acks = [b for b in parsed.blocks if isinstance(b, AcknowledgeBlock)]
    assert acks[0].section == "addressing"


# ─── Action arrays + counters ────────────────────────────────────────


def test_action_arrays_and_counters_review_phase():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [I-review-c-01, C-review-c-02]
ADDRESSED_THIS_TURN: [I-review-g-04]
RESOLVED_THIS_TURN: [Q-review-c-03]
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 2
OPEN_DISAGREEMENTS: 1
OPEN_ISSUES: 5
OPEN_COMMENTS: 1
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 1
ADDRESSED_COMMENTS: 0
"""
    parsed = parse_turn_v2(text)
    assert parsed.raised_this_turn == ["I-review-c-01", "C-review-c-02"]
    assert parsed.addressed_this_turn == ["I-review-g-04"]
    assert parsed.resolved_this_turn == ["Q-review-c-03"]
    assert parsed.counters["OPEN_ISSUES"] == 5
    assert parsed.counters["OPEN_COMMENTS"] == 1
    assert parsed.counters["ADDRESSED_ISSUES"] == 1


# ─── Phase artifact extraction ───────────────────────────────────────


def test_extract_agreed_interpretation_body():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Phase artifact

### AGREED_INTERPRETATION

#### Scope
- In scope:
  - X
- Out of scope:
  - Y

#### Approach
Some approach.

#### Carry-forward items
- [Q-input-c-04] acknowledged: open question — research in phase 1

## Status
STATUS: AGREED
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    body = extract_agreed_interpretation_body(text)
    assert body is not None
    assert "Scope" in body
    assert "Approach" in body
    assert "Q-input-c-04" in body


def test_extract_agreed_plan_and_drafter():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Phase artifact

### AGREED_PLAN

#### Sections
1. Title: Background
   Key claims:
   - X is true.
2. Title: Recommendation
   Key claims:
   - Y is recommended.

#### Carry-forward items (from phase 2)
- [D-plan-g-04] acknowledged: language choice — surfaced disagreements section

#### Drafter
DRAFTER: claude

## Status
STATUS: AGREED
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    body = extract_agreed_plan_body(text)
    assert body is not None
    assert "Recommendation" in body
    drafter = extract_drafter_from_agreed_plan(body)
    assert drafter == "claude"


def test_extract_agreed_draft_acceptance():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Phase artifact

### AGREED_DRAFT_ACCEPTANCE

draft_version: v7
draft_hash: ab12cd34ef56
endorsement: |
  This draft satisfies the brief.

## Status
STATUS: AGREED
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
OPEN_ISSUES: 0
OPEN_COMMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 0
ADDRESSED_COMMENTS: 0
"""
    accept = extract_agreed_draft_acceptance(text)
    assert accept is not None
    version, digest, endorsement = accept
    assert version == 7
    assert digest == "ab12cd34ef56"
    assert endorsement == "This draft satisfies the brief."


# ─── ID assignment ───────────────────────────────────────────────────


def test_assign_raise_ids_stamps_action_array():
    text = """\
## Stance
.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
### RAISE
kind: question
body: |
  q1.
anchor_type: none
anchor_text:
evidence_required: false

### RAISE
kind: question
body: |
  q2.
anchor_type: none
anchor_text:
evidence_required: false

### RAISE
kind: disagreement
body: |
  d1.
anchor_type: none
anchor_text:
evidence_required: false

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 2
OPEN_DISAGREEMENTS: 1
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
    parsed = parse_turn_v2(text)

    counters = {Category.QUESTION: 0, Category.DISAGREEMENT: 0}

    def next_seq(kind):
        counters[kind] += 1
        return counters[kind]

    stamped = assign_raise_ids(
        parsed,
        phase=2,
        raiser="c",
        next_seq_provider=next_seq,
    )
    assert stamped.raised_this_turn == [
        "Q-plan-c-01",
        "Q-plan-c-02",
        "D-plan-c-01",
    ]


# ─── The bug pattern from spec 0114 § Parser updates ─────────────────


def test_evidence_checked_glued_to_body_matches():
    """Spec 0114 verified-against-real-bug check.

    The pre-0114 regex used a plain ``\\b`` after ``round``; the agent
    glued the heading to the body with no newline (``## Evidence
    checked this roundThe search…``), causing the legacy parser to
    miss the section. The 0114 fix uses ``(?=\\b|[A-Z])`` so the glued
    case matches.
    """
    glued = "## Evidence checked this roundThe search confirms the key facts."
    assert EVIDENCE_CHECKED_SECTION_RE.search(glued) is not None


def test_evidence_checked_with_space_still_matches():
    spaced = "## Evidence checked this round\nbody"
    assert EVIDENCE_CHECKED_SECTION_RE.search(spaced) is not None


def test_evidence_checked_lowercase_continuation_does_not_false_positive():
    """A lowercase continuation (``roundup`` etc.) should NOT match."""
    bad = "## Evidence checked this roundup notes\nbody"
    assert EVIDENCE_CHECKED_SECTION_RE.search(bad) is None


def test_evidence_checked_real_bug_file_pattern():
    """Real bug pattern from the run audited in spec 0114."""
    # The actual line from runs/20260519-132908-backend-language-choice/
    # phase4/round-03-claude.md, abbreviated:
    real = (
        "## Evidence checked this roundThe search confirms the key facts. "
        "The pkg.go.dev page for `github.com/anthropics/anthropic-sdk-go` shows "
        "Published: May 11, 2026..."
    )
    m = EVIDENCE_CHECKED_SECTION_RE.search(real)
    assert m is not None
    assert m.start() == 0
