from __future__ import annotations

from dual_research.protocol import (
    extract_fenced_section,
    parse_preflight_turn,
    parse_turn,
)
from tests.protocol.fixtures import (
    PLAN_TURN_AGREED,
    PLAN_TURN_NEGOTIATING,
    REVIEW_TURN_APPROVED,
)


def test_parse_agreed_plan_turn() -> None:
    p = parse_turn(PLAN_TURN_AGREED)
    assert p.status == "AGREED"
    assert p.drafter == "claude"
    assert p.open_questions == 0
    assert p.blocking_disagreements == 0
    assert p.final_surfaced_disagreements == 0
    assert p.domain_fit_self == 4
    assert p.domain_fit_other == 4
    assert p.agreed_plan is not None
    assert "Title:" in p.agreed_plan
    assert p.strongest_remaining_objection is True
    assert p.why_non_blocking is True


def test_parse_negotiating_plan_turn() -> None:
    p = parse_turn(PLAN_TURN_NEGOTIATING)
    assert p.status == "NEGOTIATING"
    assert p.drafter == "claude"
    assert p.open_questions == 1
    assert p.blocking_disagreements == 1
    assert p.final_surfaced_disagreements == 0
    # The agreed_plan section exists but holds "(not agreed)" — this is by
    # design; convergence checks gate on STATUS != AGREED, not on plan content.
    assert p.agreed_plan == "(not agreed)"


def test_parse_review_approved_turn() -> None:
    p = parse_turn(REVIEW_TURN_APPROVED)
    assert p.status == "APPROVED"
    assert p.open_issues == 0
    assert p.evidence_checked_section is True
    assert p.carryover_audit_section is True
    assert p.strongest_remaining_objection is True
    assert p.why_non_blocking is True


def test_parse_preflight_turn_ok() -> None:
    text = "## Brief clarity\n\nOK\n\n## Status\nSTATUS: BRIEF_OK\nBRIEF_ISSUES: 0"
    p = parse_preflight_turn(text)
    assert p.status == "BRIEF_OK"
    assert p.brief_issues == 0


def test_parse_preflight_turn_needs_input() -> None:
    text = "## Status\nSTATUS: BRIEF_NEEDS_INPUT\nBRIEF_ISSUES: 3"
    p = parse_preflight_turn(text)
    assert p.status == "BRIEF_NEEDS_INPUT"
    assert p.brief_issues == 3


def test_extract_fenced_section_basic() -> None:
    text = "## Foo\n\nfoo body\n\n## Bar\n\nbar body\n"
    assert extract_fenced_section(text, "Foo") == "foo body"
    assert extract_fenced_section(text, "Bar") == "bar body"
    assert extract_fenced_section(text, "Missing") is None


def test_extract_fenced_section_with_indented_subheadings() -> None:
    text = "## Plan\n\n### Section\n\nbody1\n\n### Section 2\n\nbody2\n\n## Next\n\nignored\n"
    section = extract_fenced_section(text, "Plan")
    assert section is not None
    assert "body1" in section
    assert "body2" in section
    assert "ignored" not in section


def test_parser_tolerates_decoration() -> None:
    text = "> - `STATUS: AGREED`\n> - `OPEN_QUESTIONS: 0`\n> - `BLOCKING_DISAGREEMENTS: 0`\n> - `FINAL_SURFACED_DISAGREEMENTS: 0`\n> - `DRAFTER: claude`"
    p = parse_turn(text)
    assert p.status == "AGREED"
    assert p.open_questions == 0
    assert p.blocking_disagreements == 0
    assert p.final_surfaced_disagreements == 0
    assert p.drafter == "claude"


def test_missing_fields_parse_as_none() -> None:
    p = parse_turn("just some prose")
    assert p.status is None
    assert p.drafter is None
    assert p.open_questions is None
    assert p.open_issues is None
    assert p.blocking_disagreements is None
    assert p.final_surfaced_disagreements is None
