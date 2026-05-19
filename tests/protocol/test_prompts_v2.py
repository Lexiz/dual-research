"""Spec 0114 — new Deep Research prompt functions return well-formed text.

These tests exercise the prompt builders on synthetic inputs and confirm:
- The preamble and per-phase content both appear.
- The required section headings are present.
- The status-footer counters match the phase (review adds OPEN_ISSUES /
  OPEN_COMMENTS).
- The operation-block reference is included.
- The closeout-request section flips the constraints language on.
"""

from __future__ import annotations

from dual_research.protocol.prompts import (
    DEEP_RESEARCH_PREAMBLE,
    PriorTurn,
    closeout_request_section,
    drafting_prompt_v2,
    input_negotiation_prompt_v2,
    plan_negotiation_round1_prompt_v2,
    plan_negotiation_round_n_prompt_v2,
    preflight_prompt_v2,
    research_plan_prompt_v2,
    review_round1_prompt_v2,
    review_round_n_prompt_v2,
)


def _preamble_present(text: str) -> bool:
    return "Deep Research run" in text and "Source tagging" in text


def test_preflight_v2_has_preamble_and_round1_sections():
    text = preflight_prompt_v2(
        brief_content="THE BRIEF",
        agent_name="claude",
        other_name="openai",
    )
    assert _preamble_present(text)
    assert "Phase 0 (input): brief critique — round 1" in text
    assert "## Stance" in text
    assert "## Addressing items raised against me" in text
    assert "## Ratifying my own items" in text
    assert "## New items I'm raising" in text
    assert "## Status" in text
    # Round 1 cannot converge; phase-artifact heading template MUST NOT appear
    # (it may be name-dropped in prose as the convergence target).
    assert "### AGREED_INTERPRETATION" not in text
    # The brief is inlined
    assert "THE BRIEF" in text
    # Operation block reference
    assert "### RAISE" in text
    assert "### ADDRESS" in text


def test_input_negotiation_v2_status_footer_phase0_no_issues():
    text = input_negotiation_prompt_v2(
        brief_content="B",
        prior_turns=[
            PriorTurn(agent="openai", round=1, content="openai's r1 content"),
        ],
        standing_items="- [Q-input-g-01] open: ...",
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=2,
        hard_cap=4,
    )
    assert "round 2" in text
    assert "soft cap 2, hard cap 4" in text
    assert "OPEN_QUESTIONS:" in text
    assert "OPEN_DISAGREEMENTS:" in text
    # Phase 0 must NOT include issues/comments counters
    assert "OPEN_ISSUES" not in text
    assert "OPEN_COMMENTS" not in text
    # Prior turn inlined
    assert "openai's r1 content" in text
    # Standing items section
    assert "[Q-input-g-01]" in text
    # AGREED_INTERPRETATION template appears for the AGREED branch
    assert "AGREED_INTERPRETATION" in text


def test_input_negotiation_v2_closeout_section_appears():
    closeout = closeout_request_section(
        items=[
            {
                "id": "Q-input-c-02",
                "kind": "question",
                "body": "what is the canonical scope?",
                "current_state": "addressed",
                "addressed_by": "openai",
            },
        ],
        agent_name="claude",
        remaining_budget=1,
    )
    text = input_negotiation_prompt_v2(
        brief_content="B",
        prior_turns=[],
        standing_items="",
        agent_name="claude",
        other_name="openai",
        round=4,
        soft_cap=2,
        hard_cap=4,
        is_closeout_round=True,
        closeout_request=closeout,
    )
    assert "## Closeout request" in text
    assert "1" in text  # budget
    assert "RAISE blocks will be" in text
    assert "[Q-input-c-02]" in text


def test_research_plan_v2_is_production_no_operation_blocks():
    text = research_plan_prompt_v2(
        brief_content="B",
        agreed_interpretation="### AGREED_INTERPRETATION\n…",
        agent_name="claude",
    )
    assert _preamble_present(text)
    assert "Phase 1 (research-plan)" in text
    assert "## 1. Summary" in text
    assert "## 2. My thesis" in text
    assert "## 3. Detailed findings" in text
    assert "## 4. Sources" in text
    # Old phase 1 sections are explicitly forbidden (the prompt names
    # them in a "do not include" sentence).
    assert "Do not include" in text
    assert "Claims I expect" in text  # named in the do-not-include line
    # AGREED_INTERPRETATION header inlined as input context
    assert "### AGREED_INTERPRETATION" in text


def test_plan_negotiation_round1_v2_blocks_agreed():
    text = plan_negotiation_round1_prompt_v2(
        brief_content="B",
        agreed_interpretation="### AGREED_INTERPRETATION",
        own_plan="my plan",
        other_plan="other plan",
        agent_name="claude",
        other_name="openai",
    )
    assert "Phase 2 (negotiate-plan): plan negotiation — round 1" in text
    assert "STATUS: AGREED is not\nallowed in round 1" in text
    assert "my plan" in text
    assert "other plan" in text
    # Round 1 must NOT include phase-artifact heading template
    assert "### AGREED_PLAN" not in text


def test_plan_negotiation_round_n_v2_includes_drafter_and_artifact():
    text = plan_negotiation_round_n_prompt_v2(
        brief_content="B",
        agreed_interpretation="A",
        own_plan="P1",
        other_plan="P2",
        prior_turns=[PriorTurn(agent="claude", round=1, content="claude r1")],
        standing_items="(none)",
        agent_name="openai",
        other_name="claude",
        round=3,
        soft_cap=4,
        hard_cap=8,
    )
    assert "round 3" in text
    assert "soft cap 4, hard cap 8" in text
    assert "AGREED_PLAN" in text
    assert "DRAFTER: claude | openai" in text
    # Phase 2 status footer doesn't include issues/comments counters
    assert "OPEN_ISSUES" not in text
    assert "claude r1" in text


def test_drafting_v2_inlines_carry_forward_items():
    text = drafting_prompt_v2(
        brief_content="B",
        agreed_interpretation="AI",
        own_plan="P1",
        other_plan="P2",
        agreed_plan="### AGREED_PLAN",
        carry_forward_items=[
            {
                "id": "D-plan-g-04",
                "kind": "disagreement",
                "body": "language X vs Y",
                "current_state": "acknowledged",
            },
        ],
        prior_phase2_turns=[],
        agent_name="claude",
        other_name="openai",
    )
    assert "Phase 3 (draft)" in text
    assert "[D-plan-g-04]" in text
    assert "## 6. Confidence ledger" in text
    # No operation block content
    assert "### RAISE" not in text


def test_review_round1_v2_has_phase4_counters():
    text = review_round1_prompt_v2(
        brief_content="B",
        draft_content="THE DRAFT",
        drafter_name="claude",
        agent_name="claude",
        other_name="openai",
    )
    assert "Phase 4 (review-draft)" in text
    assert "acting as DRAFTER" in text
    # Phase 4 counter set includes issues + comments
    assert "OPEN_ISSUES" in text
    assert "OPEN_COMMENTS" in text
    assert "ADDRESSED_ISSUES" in text
    assert "ADDRESSED_COMMENTS" in text
    # Draft inlined
    assert "THE DRAFT" in text


def test_review_round_n_v2_role_distinguishes_reviewer():
    text = review_round_n_prompt_v2(
        brief_content="B",
        draft_content="THE DRAFT",
        drafter_name="claude",
        prior_turns=[],
        standing_items="(none)",
        agent_name="openai",
        other_name="claude",
        round=2,
        soft_cap=4,
        hard_cap=8,
        draft_version=2,
    )
    assert "acting as REVIEWER" in text
    assert "v2" in text
    assert "AGREED_DRAFT_ACCEPTANCE" in text
    assert "## Revised draft" in text


def test_closeout_request_handles_empty_items():
    text = closeout_request_section(
        items=[],
        agent_name="claude",
        remaining_budget=2,
    )
    assert "(none — see below)" in text
    assert "## Closeout request" in text


def test_closeout_request_remaining_budget_appears():
    text = closeout_request_section(
        items=[],
        agent_name="openai",
        remaining_budget=1,
    )
    assert "**1**" in text


def test_deep_research_preamble_constant_exposes_failure_modes():
    """The preamble must explicitly call out both sycophancy and adversarialism."""
    assert "Sycophancy" in DEEP_RESEARCH_PREAMBLE
    assert "Adversarialism" in DEEP_RESEARCH_PREAMBLE
    assert "evidence_required" in DEEP_RESEARCH_PREAMBLE
