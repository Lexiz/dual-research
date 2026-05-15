"""Spec 0016: negotiation_turn_prompt now includes a canonical D-N anchor
example so agents emit a format the disagreement parser can recognise.
"""

from __future__ import annotations

from dual_research.protocol import negotiation_turn_prompt


def test_negotiation_turn_prompt_contains_canonical_disagreement_format() -> None:
    p = negotiation_turn_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=6,
        hard_cap=12,
    )
    # The example block must specify the open-form anchor verbatim.
    assert "- D-N: <short label> — status: open" in p
    # And the terminal-form anchor's structural shape.
    assert "**D-N (<short label>):**" in p
    assert "<terminal-state>" in p
    # And the whitelisted terminal-state values must all appear.
    for state in ("resolved", "non_blocking_limitation", "conceded", "accepted"):
        assert state in p
