from __future__ import annotations

import pytest

from dual_research.protocol import (
    ProtocolParseError,
    all_substantive_gates_pass_except_drafter,
    assert_well_formed_plan_turn,
    assert_well_formed_review_turn,
    extract_canonical_fsd_items,
    is_plan_agreed,
    is_review_approved,
    normalized_hash,
    parse_turn,
)
from tests.protocol.fixtures import (
    CANONICAL_AGREED_PLAN,
    CANONICAL_AGREED_PLAN_WITH_FSD,
    PLAN_TURN_AGREED,
    PLAN_TURN_MALFORMED_MISSING_STATUS,
    PLAN_TURN_NEGOTIATING,
    REVIEW_TURN_APPROVED,
    REVIEW_TURN_MISSING_EVIDENCE_SECTION,
    REVIEW_TURN_REVIEWING,
    plan_turn_agreed,
)


# ---------- is_plan_agreed ----------


def test_is_plan_agreed_when_both_agree_same_plan_same_drafter() -> None:
    assert is_plan_agreed(plan_turn_agreed("claude"), plan_turn_agreed("claude")) is True


def test_is_plan_agreed_false_when_drafters_differ() -> None:
    assert is_plan_agreed(plan_turn_agreed("claude"), plan_turn_agreed("openai")) is False


def test_is_plan_agreed_false_when_only_one_agrees() -> None:
    assert is_plan_agreed(PLAN_TURN_AGREED, PLAN_TURN_NEGOTIATING.replace(
        "STATUS: NEGOTIATING", "STATUS: NEGOTIATING"
    )) is False


def test_is_plan_agreed_false_when_open_questions_nonzero() -> None:
    bad = plan_turn_agreed("claude").replace("OPEN_QUESTIONS: 0", "OPEN_QUESTIONS: 2")
    # bumping OPEN_QUESTIONS breaks well-formedness check only for missing fields, not for nonzero;
    # convergence gate just returns False
    assert is_plan_agreed(plan_turn_agreed("claude"), bad) is False


def test_is_plan_agreed_false_when_agreed_plan_hashes_differ() -> None:
    other = plan_turn_agreed("claude").replace(
        "**Title:** Background", "**Title:** Background (DIFFERENT)"
    )
    assert is_plan_agreed(plan_turn_agreed("claude"), other) is False


def test_is_plan_agreed_raises_parse_error_on_malformed() -> None:
    with pytest.raises(ProtocolParseError):
        is_plan_agreed(PLAN_TURN_MALFORMED_MISSING_STATUS, plan_turn_agreed("claude"))


# ---------- normalized_hash ----------


def test_normalized_hash_tolerates_whitespace_and_list_markers() -> None:
    a = "## Plan\n\n* item one\n*  item two\n"
    b = "## plan\n\n- item one\n-  item two"
    assert normalized_hash(a) == normalized_hash(b)


def test_normalized_hash_distinguishes_substance() -> None:
    a = "## Plan\n- item one\n"
    b = "## Plan\n- item TWO\n"
    assert normalized_hash(a) != normalized_hash(b)


def test_normalized_hash_none_is_none() -> None:
    assert normalized_hash(None) is None


# ---------- assert_well_formed_plan_turn ----------


def test_assert_well_formed_plan_turn_passes_on_good_turn() -> None:
    p = parse_turn(plan_turn_agreed("claude"))
    assert_well_formed_plan_turn(p, "claude")


def test_assert_well_formed_plan_turn_raises_on_missing_status() -> None:
    p = parse_turn(PLAN_TURN_MALFORMED_MISSING_STATUS)
    with pytest.raises(ProtocolParseError) as ei:
        assert_well_formed_plan_turn(p, "claude")
    assert any("STATUS" in e for e in ei.value.errors)


def test_assert_well_formed_plan_turn_raises_when_agreed_without_sro() -> None:
    bad = plan_turn_agreed("claude").replace(
        "STRONGEST_REMAINING_OBJECTION: caveat C could be overly cautious.",
        "STRONGEST_REMAINING_OBJECTION:",
    )
    p = parse_turn(bad)
    with pytest.raises(ProtocolParseError):
        assert_well_formed_plan_turn(p, "claude")


# ---------- is_review_approved ----------


def test_is_review_approved_when_both_approved_zero_issues() -> None:
    assert is_review_approved(REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED, round=2) is True


def test_is_review_approved_false_when_one_reviewing() -> None:
    assert is_review_approved(REVIEW_TURN_APPROVED, REVIEW_TURN_REVIEWING, round=2) is False


def test_is_review_approved_round1_carryover_required() -> None:
    no_audit = REVIEW_TURN_APPROVED.replace(
        "## Disagreement carryover audit", "## Other section"
    )
    with pytest.raises(ProtocolParseError):
        is_review_approved(no_audit, REVIEW_TURN_APPROVED, round=1)


def test_assert_well_formed_review_turn_missing_evidence_section_raises() -> None:
    p = parse_turn(REVIEW_TURN_MISSING_EVIDENCE_SECTION)
    with pytest.raises(ProtocolParseError) as ei:
        assert_well_formed_review_turn(p, "claude", round=2)
    assert any("Evidence checked" in e for e in ei.value.errors)


# ---------- all_substantive_gates_pass_except_drafter ----------


def test_tiebreak_check_passes_when_only_drafter_differs() -> None:
    c = plan_turn_agreed("claude")
    o = plan_turn_agreed("openai")
    check = all_substantive_gates_pass_except_drafter(c, o)
    assert check.passes is True
    assert check.claude_drafter == "claude"
    assert check.openai_drafter == "openai"
    assert check.agreed_plan is not None


def test_tiebreak_check_false_when_drafters_match() -> None:
    c = plan_turn_agreed("claude")
    o = plan_turn_agreed("claude")
    assert all_substantive_gates_pass_except_drafter(c, o).passes is False


def test_tiebreak_check_false_when_other_substantive_gate_fails() -> None:
    c = plan_turn_agreed("claude")
    o = plan_turn_agreed("openai").replace("BLOCKING_DISAGREEMENTS: 0", "BLOCKING_DISAGREEMENTS: 1")
    assert all_substantive_gates_pass_except_drafter(c, o).passes is False


# ---------- extract_canonical_fsd_items ----------


def test_extract_canonical_fsd_items_when_no_section() -> None:
    items = extract_canonical_fsd_items(CANONICAL_AGREED_PLAN)
    assert items == []


def test_extract_canonical_fsd_items_parses_block() -> None:
    items = extract_canonical_fsd_items(CANONICAL_AGREED_PLAN_WITH_FSD)
    assert len(items) == 1
    assert items[0].id == "FSD-1"
    assert items[0].title == "scope of caveat C"
    assert items[0].claude_position == "limited to enterprise tier"
    assert items[0].gpt_position == "applies to all tiers"
    assert "enterprise-only as starting point" in items[0].final_document_treatment
    assert items[0].affects_recommendation == "yes"
