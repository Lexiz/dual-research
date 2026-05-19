"""Spec 0114 — turn validator structural tests."""

from __future__ import annotations

from dual_research.contract.categories import Category
from dual_research.contract.operations import (
    AddressBlock,
    RaiseBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.contract.validator import validate_parsed, validate_turn


# Minimal well-formed turn skeleton used by happy-path tests.
_VALID_TURN = """\
## Stance
This is my position.

## Addressing items raised against me
(none — first round)

## Ratifying my own items
(none — first round)

## New items I'm raising
### RAISE
kind: question
body: |
  This is my question.
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
OPEN_QUESTIONS: 1
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""


def test_valid_turn_passes_structural():
    r = validate_turn(_VALID_TURN, phase=0, round=1, agent="claude")
    assert r.valid is True
    assert r.errors == []


def test_missing_stance_section():
    text = _VALID_TURN.replace("## Stance\nThis is my position.\n\n", "")
    r = validate_turn(text, phase=0, round=1, agent="claude")
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "missing_section_stance" in codes


def test_missing_status_section():
    text = _VALID_TURN.split("## Status")[0]
    r = validate_turn(text, phase=0, round=1, agent="claude")
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "missing_section_status" in codes
    assert "missing_status_value" in codes


def test_agreed_in_round_one_rejected():
    text = _VALID_TURN.replace(
        "STATUS: IN_PROGRESS", "STATUS: AGREED"
    )
    r = validate_turn(text, phase=0, round=1, agent="claude")
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "agreed_in_round_one" in codes


def test_agreed_without_phase_artifact():
    text = _VALID_TURN.replace(
        "STATUS: IN_PROGRESS", "STATUS: AGREED"
    )
    r = validate_turn(text, phase=0, round=3, agent="claude")
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "agreed_without_phase_artifact" in codes


def test_invalid_status_value():
    text = _VALID_TURN.replace(
        "STATUS: IN_PROGRESS", "STATUS: NEGOTIATING"
    )
    r = validate_turn(text, phase=0, round=1, agent="claude")
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "invalid_status_value" in codes


def test_validate_parsed_rejects_address_without_response():
    block = AddressBlock(
        item_id="D-plan-g-04",
        response="",
        proposes_status="addressed",
        raw_text="",
    )
    r = validate_parsed(
        text=_VALID_TURN,
        blocks=[block],
        phase=2,
        round=2,
        agent="claude",
    )
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "address_missing_response" in codes


def test_validate_parsed_rejects_disallowed_category_in_phase_0():
    block = RaiseBlock(
        kind=Category.ISSUE,
        body="bug in draft",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        raw_text="",
    )
    r = validate_parsed(
        text=_VALID_TURN,
        blocks=[block],
        phase=0,
        round=1,
        agent="claude",
    )
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "raise_disallowed_category_for_phase" in codes


def test_validate_parsed_rejects_resolve_without_reason():
    block = ResolveBlock(item_id="Q-plan-c-02", reason="", raw_text="")
    r = validate_parsed(
        text=_VALID_TURN,
        blocks=[block],
        phase=2,
        round=2,
        agent="claude",
    )
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "resolve_missing_reason" in codes


def test_validate_parsed_rejects_withdraw_without_reason():
    block = WithdrawBlock(item_id="Q-plan-c-02", reason="", raw_text="")
    r = validate_parsed(
        text=_VALID_TURN,
        blocks=[block],
        phase=2,
        round=2,
        agent="claude",
    )
    assert r.valid is False
    codes = {e.code for e in r.errors}
    assert "withdraw_missing_reason" in codes


def test_closeout_raise_is_warning_not_error():
    """RAISE blocks in a closeout round produce a warning, not a hard error."""
    block = RaiseBlock(
        kind=Category.QUESTION,
        body="late question",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        raw_text="",
    )
    r = validate_parsed(
        text=_VALID_TURN,
        blocks=[block],
        phase=2,
        round=5,
        agent="claude",
        is_closeout_round=True,
    )
    closeout_errors = [e for e in r.errors if e.code == "closeout_violation_raise"]
    assert len(closeout_errors) == 1
    assert closeout_errors[0].severity == "warning"


def test_round_one_in_progress_with_evidence_required_optional():
    """Round-1 RAISE-only turn validates clean."""
    r = validate_turn(_VALID_TURN, phase=2, round=1, agent="claude")
    assert r.valid is True
