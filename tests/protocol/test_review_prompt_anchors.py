"""Verify the Phase 4 review prompt mentions the inline-quote convention.

Belt-and-braces against accidental drift: spec 0028 adds the same one-
paragraph anchor hint that 0027 added to Phase 2, under three Phase 4
sections (Issue ledger / Comments on the current draft / Substantive
disagreements). If those phrases disappear, the UI's Phase 4 side-by-
side modal degrades to "un-anchored cards everywhere".
"""

from __future__ import annotations

from dual_research.protocol.prompts import review_turn_prompt


def _prompt(*, role: str = "REVIEWER") -> str:
    # `role` is derived inside the prompt from agent_name vs drafter_name.
    drafter = "openai" if role == "REVIEWER" else "claude"
    return review_turn_prompt(
        brief_content="brief",
        draft_content="# Draft\n\nbody",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        drafter_name=drafter,
        round=2,
        soft_cap=6,
        hard_cap=12,
    )


def test_reviewer_prompt_mentions_quote_marker() -> None:
    text = _prompt(role="REVIEWER")
    assert "> quote:" in text
    assert "> after:" in text


def test_drafter_prompt_mentions_quote_marker() -> None:
    text = _prompt(role="DRAFTER")
    assert "> quote:" in text
    assert "> after:" in text


def test_marker_lives_inside_comments_section() -> None:
    text = _prompt()
    comments_idx = text.index("## Comments on the current draft")
    carryover_idx = text.index("## Disagreement carryover audit")
    block = text[comments_idx:carryover_idx]
    assert "> quote:" in block
    assert "> after:" in block


def test_marker_lives_inside_issue_ledger_section() -> None:
    text = _prompt()
    issues_idx = text.index("## Issue ledger (delta + currently open)")
    evidence_idx = text.index("## Evidence checked this round")
    block = text[issues_idx:evidence_idx]
    assert "> quote:" in block
    assert "> after:" in block


def test_marker_lives_inside_substantive_disagreements_section() -> None:
    text = _prompt()
    disagreements_idx = text.index("## Substantive disagreements I'm holding")
    revision_idx = text.index("## Drafter revision note")
    block = text[disagreements_idx:revision_idx]
    assert "> quote:" in block
    assert "> after:" in block
