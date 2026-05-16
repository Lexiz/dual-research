"""Verify the Phase 2 prompts mention the inline-quote anchor convention.

Belt-and-braces against accidental drift: spec 0027 adds a single
paragraph under "Open questions" + "Substantive disagreements" asking
agents to emit `> quote: …` / `> after: …` blockquote sub-lines under
each item. If those phrases disappear from the prompt, the UI's right-
pane comment cards lose their anchor data and the side-by-side modal
degrades to "un-anchored cards everywhere".
"""

from __future__ import annotations

from dual_research.protocol.prompts import (
    negotiation_round1_prompt,
    negotiation_turn_prompt,
)


def _round1() -> str:
    return negotiation_round1_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        agent_name="claude",
        other_name="openai",
    )


def _round_n() -> str:
    return negotiation_turn_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        round=3,
        soft_cap=6,
        hard_cap=12,
    )


def test_round1_mentions_quote_marker() -> None:
    text = _round1()
    assert "> quote:" in text
    assert "> after:" in text


def test_round_n_mentions_quote_marker_in_open_questions() -> None:
    text = _round_n()
    # Both markers documented somewhere in the prompt.
    assert "> quote:" in text
    assert "> after:" in text


def test_round_n_documents_anchor_under_disagreements() -> None:
    text = _round_n()
    # The anchor instructions land *inside* the substantive-disagreements
    # section, before "Final-surfaced disagreements".
    sub_idx = text.index("## Substantive disagreements I'm holding")
    final_idx = text.index("## Final-surfaced disagreements")
    block = text[sub_idx:final_idx]
    assert "> quote:" in block
    assert "> after:" in block
