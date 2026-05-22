"""Spec 0149 §5.5 (D17) — address-side citation-contract tightening.

The contract lives in ``COMMON_PREAMBLE`` so it lands in every phase
prompt (Phase 1 research and Phase 2/3 drafting are the ones that
actually emit ``[N]`` citations; the language is universal so an agent
who flips between phases never sees inconsistent rules).
"""

from __future__ import annotations

from dual_research.protocol import (
    drafting_prompt,
    negotiation_round1_prompt,
    research_prompt,
)


_HEADING = "Citation contract (spec 0149 §5.5 — D17)"
_KEY_PHRASES = (
    "Only emit an inline `[N]` citation when N references a source you actually consulted",
    "Do not emit `[N]` to reference your own prior reasoning",
    "Every `[N]` you write must round-trip",
    "cited_url_not_in_consulted_sources",
)


def test_citation_contract_present_in_research_prompt() -> None:
    p = research_prompt(brief_content="brief", agent_name="claude")
    assert _HEADING in p
    for phrase in _KEY_PHRASES:
        assert phrase in p, f"missing phrase: {phrase!r}"


def test_citation_contract_present_in_negotiation_round1_prompt() -> None:
    p = negotiation_round1_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        agent_name="claude",
        other_name="openai",
    )
    assert _HEADING in p


def test_citation_contract_present_in_drafting_prompt() -> None:
    p = drafting_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        agreed_plan_block="plan",
        final_surfaced_disagreements=[],
    )
    assert _HEADING in p
