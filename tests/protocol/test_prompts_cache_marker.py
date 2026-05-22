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


def _all_indices(haystack: str, needle: str) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + len(needle)


def test_cache_marker_present_in_phase_prompts() -> None:
    """Spec 0149 §5.3 (D02) — Phase 0/1 emit one breakpoint after the
    brief; Phase 2 / 3 / 4 emit TWO breakpoints (one after the brief,
    one after the drafts) so cache_read engages even when the
    draft-bearing section changes between rounds.
    """
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
    assert c.count(CACHE_BREAKPOINT) == 2
    bp_c = _all_indices(c, CACHE_BREAKPOINT)
    # First breakpoint after Brief, before the Phase 1 drafts.
    assert c.index("### Brief") < bp_c[0] < c.index("Your Phase 1 draft")
    # Second breakpoint after the drafts, before the Task.
    assert c.index("openai's Phase 1 draft") < bp_c[1] < c.index("## Task")

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
    assert d.count(CACHE_BREAKPOINT) == 2
    bp_d = _all_indices(d, CACHE_BREAKPOINT)
    assert d.index("### Brief") < bp_d[0] < d.index("Your Phase 1 draft")
    assert bp_d[1] < d.index("Prior Phase 2 conversation")

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
    assert e.count(CACHE_BREAKPOINT) == 2
    bp_e = _all_indices(e, CACHE_BREAKPOINT)
    assert e.index("### Brief") < bp_e[0] < e.index("Your Phase 1 draft")
    assert bp_e[1] < e.index("Full Phase 2 conversation")

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
    assert f.count(CACHE_BREAKPOINT) == 2
    bp_f = _all_indices(f, CACHE_BREAKPOINT)
    # Phase 4: first breakpoint after Brief, before the (mutable) draft.
    assert f.index("### Brief") < bp_f[0] < f.index("### Current draft")
    assert bp_f[1] < f.index("Prior Phase 4 review turns")


def test_cache_marker_absent_in_repair_prompt() -> None:
    p = repair_prompt(
        agent_name="claude",
        phase=2,
        errors=["missing STATUS:"],
        malformed_content="garbage",
    )
    assert CACHE_BREAKPOINT not in p
