from __future__ import annotations

from dual_research.protocol import (
    CACHE_BREAKPOINT,
    drafting_prompt,
    negotiation_round1_prompt,
    negotiation_turn_prompt,
    preflight_prompt,
    repair_prompt,
    research_prompt,
    review_turn_prompt,
)


def test_cache_marker_present_in_phase_prompts() -> None:
    brief = "test brief"
    a = preflight_prompt(brief_content=brief, agent_name="claude")
    assert a.count(CACHE_BREAKPOINT) == 1
    assert a.index("## Inputs") < a.index(CACHE_BREAKPOINT) < a.index("## Task")

    b = research_prompt(brief_content=brief, agent_name="claude")
    assert b.count(CACHE_BREAKPOINT) == 1

    c = negotiation_round1_prompt(
        brief_content=brief,
        own_draft="own",
        other_draft="other",
        agent_name="claude",
        other_name="openai",
    )
    assert c.count(CACHE_BREAKPOINT) == 1

    d = negotiation_turn_prompt(
        brief_content=brief,
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=6,
        hard_cap=12,
    )
    assert d.count(CACHE_BREAKPOINT) == 1
    # The breakpoint is between the drafts and the prior-turns section.
    assert d.index(CACHE_BREAKPOINT) < d.index("Prior Phase 2 conversation")

    e = drafting_prompt(
        brief_content=brief,
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        agreed_plan_block="plan",
        final_surfaced_disagreements=[],
    )
    assert e.count(CACHE_BREAKPOINT) == 1
    assert e.index(CACHE_BREAKPOINT) < e.index("Full Phase 2 conversation")

    f = review_turn_prompt(
        brief_content=brief,
        draft_content="draft",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        drafter_name="claude",
        round=1,
        soft_cap=6,
        hard_cap=12,
    )
    assert f.count(CACHE_BREAKPOINT) == 1
    assert f.index(CACHE_BREAKPOINT) < f.index("Prior Phase 4 review turns")


def test_cache_marker_absent_in_repair_prompt() -> None:
    p = repair_prompt(
        agent_name="claude",
        phase=2,
        errors=["missing STATUS:"],
        malformed_content="garbage",
    )
    assert CACHE_BREAKPOINT not in p
