"""Spec 0091 § B — drafter-engagement requirement is present in the
rendered review_turn_prompt and review_input_bundle system text."""

from __future__ import annotations

from dual_research.protocol.prompts import review_turn_prompt


def _build(round: int = 1, drafter: str = "claude", agent: str = "claude") -> str:
    return review_turn_prompt(
        brief_content="# Brief\nbody",
        draft_content="# Draft\nbody",
        prior_turns=[],
        agent_name=agent,
        other_name="openai" if agent == "claude" else "claude",
        drafter_name=drafter,
        round=round,
        soft_cap=6,
        hard_cap=12,
    )


class TestDrafterEngagementBlockPresent:
    def test_present_for_drafter_turn(self) -> None:
        prompt = _build(round=1, drafter="claude", agent="claude")
        assert "Drafter engagement requirement (spec 0091)" in prompt
        assert "you may NOT emit `STATUS: APPROVED` in round 1" in prompt
        assert "Round 1 is for engagement, not termination" in prompt

    def test_present_for_reviewer_turn_as_well(self) -> None:
        """The rule is informational for the reviewer too — they need
        to know APPROVED in r1 will get rejected so they don't waste
        a turn debating an invalid outcome."""
        prompt = _build(round=1, drafter="openai", agent="claude")
        assert "Drafter engagement requirement (spec 0091)" in prompt

    def test_present_in_round_2_too(self) -> None:
        """The instruction is part of the static section structure;
        it appears every round so the prompt template is uniform."""
        prompt = _build(round=2, drafter="claude", agent="claude")
        assert "Drafter engagement requirement (spec 0091)" in prompt
        assert "From round 2 onward APPROVED becomes available" in prompt

    def test_phase_2_round_1_rule_referenced(self) -> None:
        """Cross-reference to Phase 2's existing rule helps the agent
        understand the symmetry."""
        prompt = _build()
        assert "round 1 cannot agree" in prompt
