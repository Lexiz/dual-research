"""Spec 0032 — Phase 2 prompts require a `## Summary` section.

Phase 0 / 1 / 3 / 4 prompts have always asked for one; Phase 2 was the
outlier, which caused empty timeline cards (no TL;DR to display on the
inline-unfold body added in spec 0030). This test pins the requirement.
"""

from __future__ import annotations

from dual_research.protocol.prompts import (
    negotiation_round1_prompt,
    negotiation_turn_prompt,
)


class TestPhase2SummarySection:
    def test_round1_prompt_includes_summary_section(self) -> None:
        prompt = negotiation_round1_prompt(
            brief_content="x",
            own_draft="y",
            other_draft="z",
            agent_name="claude",
            other_name="openai",
        )
        assert "## Summary" in prompt

    def test_turn_prompt_includes_summary_section(self) -> None:
        prompt = negotiation_turn_prompt(
            brief_content="x",
            own_draft="y",
            other_draft="z",
            prior_turns=[],
            agent_name="claude",
            other_name="openai",
            round=3,
            soft_cap=6,
            hard_cap=12,
        )
        assert "## Summary" in prompt

    def test_summary_section_appears_before_substantive_sections(self) -> None:
        """The TL;DR should be early in the agent's output, not after the
        long substantive sections (so the UI can extract it quickly and
        the agent doesn't bury it)."""
        prompt = negotiation_turn_prompt(
            brief_content="x",
            own_draft="y",
            other_draft="z",
            prior_turns=[],
            agent_name="claude",
            other_name="openai",
            round=3,
            soft_cap=6,
            hard_cap=12,
        )
        summary_idx = prompt.index("## Summary")
        plan_idx = prompt.index("## Plan as I currently propose it")
        assert summary_idx < plan_idx
