"""Spec 0090 § B — prompt tightening for answer-format adherence.

The negotiation_turn_prompt and review_turn_prompt now include an
inline example showing the recommended numbered-list format with
the protocol ID inside the bold label. The parser accepts both
formats (numbered + bold-header) but the example nudges agents
toward the cleaner one for UI rendering consistency.
"""

from __future__ import annotations

from dual_research.protocol.prompts import negotiation_turn_prompt, review_turn_prompt


_BRIEF = "Some research brief."
_DRAFT_A = "## Draft A\nclaude's draft body"
_DRAFT_B = "## Draft B\nopenai's draft body"


def _build_p2(round: int = 2) -> str:
    return negotiation_turn_prompt(
        brief_content=_BRIEF,
        own_draft=_DRAFT_A,
        other_draft=_DRAFT_B,
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        round=round,
        soft_cap=6,
        hard_cap=12,
    )


def _build_p4(round: int = 2) -> str:
    return review_turn_prompt(
        brief_content=_BRIEF,
        draft_content="## Draft\nbody",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        drafter_name="claude",
        round=round,
        soft_cap=6,
        hard_cap=12,
    )


class TestPhase2AnswersInstruction:
    def test_format_requirement_mentioned(self) -> None:
        prompt = _build_p2()
        assert "Format requirement (spec 0090)" in prompt

    def test_inline_numbered_example_present(self) -> None:
        prompt = _build_p2()
        # The exact recommended example shape from the spec.
        assert "1. **Q-g-r1-01" in prompt
        assert "2. **Q-g-r1-02" in prompt

    def test_bold_header_form_also_acknowledged(self) -> None:
        prompt = _build_p2()
        # Bold-header alternative is documented as accepted.
        assert "Bold-header form is also accepted" in prompt
        assert "**Q-g-r1-03 — short title**" in prompt

    def test_cross_round_expectation_stated(self) -> None:
        prompt = _build_p2()
        # Agents are told to address not only the most-recent turn but
        # also standing items from prior rounds.
        assert "standing-items section" in prompt

    def test_ghosted_consequence_mentioned(self) -> None:
        prompt = _build_p2()
        # The penalty / signal for leaving a question unaddressed.
        assert "ghosted" in prompt


class TestPhase4AnswersInstruction:
    def test_format_requirement_mentioned(self) -> None:
        prompt = _build_p4()
        assert "Format requirement (spec 0090)" in prompt

    def test_inline_numbered_example_present(self) -> None:
        prompt = _build_p4()
        # P4 example uses C-N IDs.
        assert "1. **C-1" in prompt

    def test_id_alphabet_covers_cross_round_form(self) -> None:
        prompt = _build_p4()
        # The cross-round system ID (e.g. [I-g-r1-01]) is mentioned as
        # an acceptable ID format for referencing prior issues.
        assert "I-g-r1-01" in prompt


class TestPhase4IssueLedgerInstruction:
    def test_issue_ledger_format_requirement(self) -> None:
        prompt = _build_p4()
        # The issue ledger section now also has an ID-anchoring requirement.
        assert "Issue ledger" in prompt
        assert "OAI-P4-1 — resolved" in prompt
        assert "OAI-P4-2 — open" in prompt

    def test_id_anchored_dedup_explanation(self) -> None:
        prompt = _build_p4()
        # The "without an ID, the system can't dedupe" sentence is what
        # incentivises agents to consistently emit the ID.
        assert "dedupe" in prompt
