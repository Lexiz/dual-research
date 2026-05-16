"""Spec 0032 — force_verbatim_copy_prompt construction.

The repair prompt fires when both agents emit STATUS: AGREED but their
plan hashes drift. It hands the non-drafter the canonical plan and
demands byte-for-byte reproduction.
"""

from __future__ import annotations

import re

from dual_research.protocol.prompts import force_verbatim_copy_prompt


SAMPLE_PLAN = """1. **Title:** Background
   **Key claims:**
   - Topic X has shifted because of regulation Y.

2. **Title:** Analysis
   **Key claims:**
   - Approach A beats B on metric M.
"""


def _build(**overrides):
    defaults = dict(
        agent_name="openai",
        other_name="claude",
        drafter_name="claude",
        canonical_plan=SAMPLE_PLAN,
        round=4,
    )
    defaults.update(overrides)
    return force_verbatim_copy_prompt(**defaults)


class TestForceVerbatimCopyPrompt:
    def test_inlines_canonical_plan_block(self) -> None:
        out = _build()
        assert SAMPLE_PLAN in out

    def test_names_recipient_and_drafter(self) -> None:
        out = _build(agent_name="openai", drafter_name="claude")
        assert 'agent "openai"' in out
        assert "drafter (claude)" in out

    def test_forbids_paraphrasing_explicitly(self) -> None:
        out = _build()
        # Prompt text may wrap across newlines — match with \s+ between
        # "do not" and "paraphrase".
        assert re.search(r"(?i)do\s+not\s+paraphrase", out)

    def test_requires_standard_p2_sections(self) -> None:
        out = _build()
        # Collapse internal whitespace so the test is robust to the
        # prompt's natural line wrapping (e.g. `## Substantive\n
        # disagreements I'm holding`).
        flat = re.sub(r"\s+", " ", out)
        for section in (
            "## Summary",
            "## Answers to",
            "## What I researched since the last round",
            "## Open questions for",
            "## Plan as I currently propose it",
            "## Substantive disagreements I'm holding",
            "## Resolved or non-blocking differences",
            "## Agreement check",
            "## AGREED_PLAN",
            "## Drafter recommendation",
            "## Status",
        ):
            assert section in flat, f"missing section {section!r} in repair prompt"

    def test_warns_about_canonical_promotion_fallback(self) -> None:
        out = _build()
        # The agent should know what happens if it ignores the
        # instruction — orchestrator will canonical-promote. Prompt
        # may wrap "canonical\npromotion" across a line break.
        assert re.search(r"(?i)canonical\s+promotion", out)

    def test_round_number_appears_in_prompt(self) -> None:
        out = _build(round=7)
        assert "round 7" in out

    def test_status_block_is_pre_filled_to_agreed(self) -> None:
        """The prompt tells the agent exactly what STATUS / OQ / BD must
        emit so it doesn't accidentally flip to NEGOTIATING."""
        out = _build()
        assert "STATUS: AGREED" in out
        assert "OPEN_QUESTIONS: 0" in out
        assert "BLOCKING_DISAGREEMENTS: 0" in out
