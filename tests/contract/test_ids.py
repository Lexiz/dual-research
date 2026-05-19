"""Spec 0114 — stable item ID format / parse roundtrip tests."""

from __future__ import annotations

import pytest

from dual_research.contract.categories import Category
from dual_research.contract.ids import (
    agent_name,
    format_id,
    is_well_formed,
    parse_id,
    raiser_letter,
)


def test_format_roundtrip_question_claude_input():
    s = format_id(Category.QUESTION, 0, "c", 1)
    assert s == "Q-input-c-01"
    kind, phase, raiser, seq = parse_id(s)
    assert kind == Category.QUESTION
    assert phase == 0
    assert raiser == "c"
    assert seq == 1


def test_format_roundtrip_disagreement_gpt_plan():
    s = format_id(Category.DISAGREEMENT, 2, "g", 4)
    assert s == "D-plan-g-04"
    kind, phase, raiser, seq = parse_id(s)
    assert kind == Category.DISAGREEMENT
    assert phase == 2
    assert raiser == "g"
    assert seq == 4


def test_format_roundtrip_issue_review():
    s = format_id(Category.ISSUE, 4, "c", 12)
    assert s == "I-review-c-12"
    kind, phase, raiser, seq = parse_id(s)
    assert kind == Category.ISSUE
    assert phase == 4
    assert raiser == "c"
    assert seq == 12


def test_format_accepts_agent_name_for_raiser():
    """``format_id`` accepts ``claude``/``openai``/``gpt`` as well as ``c``/``g``."""
    assert format_id(Category.COMMENT, 4, "claude", 7) == "C-review-c-07"
    assert format_id(Category.COMMENT, 4, "openai", 7) == "C-review-g-07"
    assert format_id(Category.COMMENT, 4, "gpt", 7) == "C-review-g-07"


def test_seq_two_digit_padding():
    assert format_id(Category.QUESTION, 0, "c", 1).endswith("-01")
    assert format_id(Category.QUESTION, 0, "c", 99).endswith("-99")


def test_parse_rejects_malformed():
    for bad in [
        "",
        "Q-input-c",
        "Q-input-c-1",       # one-digit seq
        "Q-input-c-100",     # three-digit seq
        "X-input-c-01",      # bad kind
        "Q-other-c-01",      # bad phase
        "Q-input-x-01",      # bad raiser
        "Q_input_c_01",      # wrong delimiter
        " Q-input-c-01",     # leading whitespace
    ]:
        with pytest.raises(ValueError):
            parse_id(bad)
        assert not is_well_formed(bad)


def test_format_rejects_phase_without_token():
    """Phase 1 and 3 cannot raise items and have no token."""
    with pytest.raises(ValueError):
        format_id(Category.QUESTION, 1, "c", 1)
    with pytest.raises(ValueError):
        format_id(Category.QUESTION, 3, "c", 1)


def test_format_rejects_seq_out_of_range():
    with pytest.raises(ValueError):
        format_id(Category.QUESTION, 0, "c", 0)
    with pytest.raises(ValueError):
        format_id(Category.QUESTION, 0, "c", 100)


def test_raiser_letter_translates():
    assert raiser_letter("claude") == "c"
    assert raiser_letter("openai") == "g"
    assert raiser_letter("gpt") == "g"
    with pytest.raises(ValueError):
        raiser_letter("anthropic")


def test_agent_name_translates():
    assert agent_name("c") == "claude"
    assert agent_name("g") == "openai"
    with pytest.raises(ValueError):
        agent_name("z")


def test_is_well_formed():
    assert is_well_formed("Q-input-c-01")
    assert is_well_formed("I-review-g-99")
    assert not is_well_formed("Q-input-c-0")
    assert not is_well_formed("not-an-id")
