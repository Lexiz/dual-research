"""Spec 0090 § A — answer-extraction + question-reconstruction overhaul.

Covers:
  - The new `_extract_answer_blocks` accepts numbered-list, bold-header,
    and H3 head formats.
  - ID-based primary matching (head ID → corresponding Q-N) plus
    positional fallback.
  - Multi-round look-ahead up to `MAX_ANSWER_LOOKAHEAD_ROUNDS = 5`.
  - First-match-wins semantics so a re-reference doesn't overwrite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ui.questions import (
    MAX_ANSWER_LOOKAHEAD_ROUNDS,
    _block_head_id,
    _extract_answer_blocks,
    _extract_answers_from_turn,
    reconstruct_questions,
)


# ─── Block-head ID extraction ───────────────────────────────────────────────


class TestBlockHeadId:
    @pytest.mark.parametrize("head, expected", [
        ("**Q-g-r1-01 — title**", "Q-g-r1-01"),
        ("1. **Q-g-r1-01 — title:** body", "Q-g-r1-01"),
        ("### Q-g-r2-03: title", "Q-g-r2-03"),
        ("**OAI-P4-1 (title):** body", "OAI-P4-1"),
        ("**OAI-1 — body**", "OAI-1"),
        ("**C-7** — open", "C-7"),
        ("**FSD-1: scope** body", "FSD-1"),
        ("**D-12** body", "D-12"),
        ("**[I-g-r1-01]** — resolved", "I-g-r1-01"),
        ("plain text no id", None),
    ])
    def test_extracts_first_id_token(self, head: str, expected: str | None) -> None:
        assert _block_head_id(head) == expected


# ─── Answer-block extraction ────────────────────────────────────────────────


class TestExtractAnswerBlocksNumberedList:
    """The pre-spec-0090 happy-path format that OpenAI tends to use."""

    def test_basic_numbered_list(self) -> None:
        turn = (
            "## Answers to claude's open questions\n\n"
            "1. **Q-c-r1-01 — title:** answer one body\n"
            "2. **Q-c-r1-02 — title:** answer two body\n\n"
            "## Next section\n"
        )
        blocks = _extract_answer_blocks(turn, other_name="claude")
        assert len(blocks) == 2
        assert blocks[0][0] == "Q-c-r1-01"
        assert "answer one body" in blocks[0][1]
        assert blocks[1][0] == "Q-c-r1-02"

    def test_numbered_list_without_ids_falls_back_to_no_id(self) -> None:
        turn = (
            "## Answers to claude's open questions\n\n"
            "1. plain answer one\n"
            "2. plain answer two\n\n"
            "## Next\n"
        )
        blocks = _extract_answer_blocks(turn, other_name="claude")
        assert len(blocks) == 2
        assert all(b[0] is None for b in blocks)


class TestExtractAnswerBlocksBoldHeader:
    """The pre-spec-0090 INVISIBLE format that Claude prefers — the
    regression that drove this spec."""

    def test_bold_header_per_question(self) -> None:
        turn = (
            "## Answers to openai's open questions\n\n"
            "**Q-g-r1-01 — Evidence vs. inference**\n\n"
            "Conceded partially. body line one.\n"
            "body line two.\n\n"
            "**Q-g-r1-02 — Kotlin Tier 1 status**\n\n"
            "Updated. body line.\n\n"
            "## Next section\n"
        )
        blocks = _extract_answer_blocks(turn, other_name="openai")
        assert len(blocks) == 2
        assert blocks[0][0] == "Q-g-r1-01"
        assert "Conceded partially" in blocks[0][1]
        assert "body line two" in blocks[0][1]
        assert blocks[1][0] == "Q-g-r1-02"
        assert "Updated" in blocks[1][1]


class TestExtractAnswerBlocksH3:
    def test_h3_heading_per_question(self) -> None:
        turn = (
            "## Answers to claude's open questions\n\n"
            "### Q-c-r2-01: title\n"
            "body line one\n"
            "body line two\n\n"
            "### Q-c-r2-02: title2\n"
            "more body\n\n"
            "## Done\n"
        )
        blocks = _extract_answer_blocks(turn, other_name="claude")
        assert len(blocks) == 2
        assert blocks[0][0] == "Q-c-r2-01"
        assert blocks[1][0] == "Q-c-r2-02"


class TestExtractAnswerBlocksMixedFormats:
    def test_one_turn_with_mixed_blocks(self) -> None:
        turn = (
            "## Answers to claude's open questions\n\n"
            "1. **Q-c-r1-01 — first:** numbered body\n"
            "**Q-c-r1-02 — second**\n\n"
            "bold-header body\n\n"
            "### Q-c-r1-03: third\n"
            "h3 body\n\n"
            "## Next\n"
        )
        blocks = _extract_answer_blocks(turn, other_name="claude")
        assert len(blocks) == 3
        assert [b[0] for b in blocks] == ["Q-c-r1-01", "Q-c-r1-02", "Q-c-r1-03"]


class TestBackwardCompatShim:
    def test_extract_answers_from_turn_returns_bodies_only(self) -> None:
        turn = (
            "## Answers to claude's open questions\n\n"
            "1. **Q-c-r1-01:** body one\n"
            "2. body two without id\n\n"
            "## Done\n"
        )
        answers = _extract_answers_from_turn(turn, other_name="claude")
        assert len(answers) == 2
        assert "body one" in answers[0]
        assert "body two" in answers[1]


# ─── reconstruct_questions: ID-based matching + multi-round look-ahead ─────


def _write_round(dir_path: Path, round_n: int, agent: str, body: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / f"round-{round_n:02d}-{agent}.md").write_text(body, encoding="utf-8")


_OPEN_QUESTIONS_SECTION = (
    "## Open questions for {other}\n"
    "1. Numbered question text\n"
    "   > quote: anchored span\n"
)


def _stub_turn_with_questions(other: str, n: int = 1) -> str:
    items = "".join(
        f"{i+1}. Question body {i+1}\n   > quote: anchor {i+1}\n"
        for i in range(n)
    )
    return (
        "## Summary\nsome summary\n\n"
        f"## Open questions for {other}\n{items}\n"
        "## Status\nSTATUS: NEGOTIATING\n"
    )


def _stub_turn_with_answers_bold_header(other: str, ids: list[str]) -> str:
    blocks = "\n\n".join(
        f"**{qid} — title**\n\nanswer body for {qid}"
        for qid in ids
    )
    return (
        f"## Summary\nsummary\n\n"
        f"## Answers to {other}'s open questions\n\n{blocks}\n\n"
        "## Open questions for whoever\n(none)\n\n"
        "## Status\nSTATUS: NEGOTIATING\n"
    )


class TestReconstructQuestionsIdBasedMatching:
    def test_bold_header_format_now_links_answers(self, tmp_path: Path) -> None:
        """Pre-spec-0090 this returned all questions as 'open'. Post-spec
        the bold-header answers are correctly linked by ID."""
        phase_dir = tmp_path / "phase2"
        _write_round(phase_dir, 1, "claude", _stub_turn_with_questions("openai", n=3))
        _write_round(phase_dir, 1, "openai", _stub_turn_with_questions("claude", n=2))
        # Round 2: each agent answers the other's questions in bold-header form.
        _write_round(phase_dir, 2, "claude",
                     _stub_turn_with_answers_bold_header("openai",
                         ["Q-g-r1-01", "Q-g-r1-02"]))
        _write_round(phase_dir, 2, "openai",
                     _stub_turn_with_answers_bold_header("claude",
                         ["Q-c-r1-01", "Q-c-r1-02", "Q-c-r1-03"]))

        qs = reconstruct_questions(tmp_path, phase=2)
        # 5 total (3 by claude + 2 by gpt), all should be answered.
        assert len(qs) == 5
        assert all(q.status == "answered" for q in qs)
        # Attribution: questions raised by claude → answered by gpt
        for q in qs:
            assert q.raised_by != q.answered_by

    def test_ids_out_of_order_still_matched(self, tmp_path: Path) -> None:
        """ID-based matching must work even if the answerer reorders."""
        phase_dir = tmp_path / "phase2"
        _write_round(phase_dir, 1, "claude", _stub_turn_with_questions("openai", n=3))
        _write_round(phase_dir, 1, "openai", _stub_turn_with_questions("claude", n=0))
        # Openai r2: answer claude's 3 questions in REVERSE order.
        _write_round(phase_dir, 2, "openai",
                     _stub_turn_with_answers_bold_header("claude",
                         ["Q-c-r1-03", "Q-c-r1-01", "Q-c-r1-02"]))
        _write_round(phase_dir, 2, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))

        qs = [q for q in reconstruct_questions(tmp_path, phase=2)
              if q.raised_by == "claude"]
        # All 3 of claude's questions get matched, despite reorder.
        assert {q.id for q in qs} == {"Q-c-r1-01", "Q-c-r1-02", "Q-c-r1-03"}
        assert all(q.status == "answered" for q in qs)

    def test_late_round_answer_within_lookahead_window(self, tmp_path: Path) -> None:
        """An answer in round N+3 must still be detected (N+3 ≤ N+5)."""
        phase_dir = tmp_path / "phase2"
        # Claude raises Q-c-r1-01 in round 1.
        _write_round(phase_dir, 1, "claude", _stub_turn_with_questions("openai", n=1))
        _write_round(phase_dir, 1, "openai", _stub_turn_with_questions("claude", n=0))
        # Rounds 2/3: openai is silent on claude's q.
        _write_round(phase_dir, 2, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))
        _write_round(phase_dir, 2, "openai",
                     _stub_turn_with_answers_bold_header("claude", []))
        _write_round(phase_dir, 3, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))
        _write_round(phase_dir, 3, "openai",
                     _stub_turn_with_answers_bold_header("claude", []))
        # Round 4: openai finally answers.
        _write_round(phase_dir, 4, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))
        _write_round(phase_dir, 4, "openai",
                     _stub_turn_with_answers_bold_header("claude", ["Q-c-r1-01"]))

        qs = reconstruct_questions(tmp_path, phase=2)
        q1 = next(q for q in qs if q.id == "Q-c-r1-01")
        assert q1.status == "answered"
        assert q1.answered_round == 4

    def test_first_match_wins_on_restatement(self, tmp_path: Path) -> None:
        """If openai answers Q-c-r1-01 in r2 and then references it again
        in r3, the earlier r2 answer keeps its answered_round."""
        phase_dir = tmp_path / "phase2"
        _write_round(phase_dir, 1, "claude", _stub_turn_with_questions("openai", n=1))
        _write_round(phase_dir, 1, "openai", _stub_turn_with_questions("claude", n=0))
        _write_round(phase_dir, 2, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))
        _write_round(phase_dir, 2, "openai",
                     _stub_turn_with_answers_bold_header("claude", ["Q-c-r1-01"]))
        _write_round(phase_dir, 3, "claude",
                     _stub_turn_with_answers_bold_header("openai", []))
        _write_round(phase_dir, 3, "openai",
                     _stub_turn_with_answers_bold_header("claude", ["Q-c-r1-01"]))

        qs = reconstruct_questions(tmp_path, phase=2)
        q1 = next(q for q in qs if q.id == "Q-c-r1-01")
        assert q1.status == "answered"
        assert q1.answered_round == 2  # first match wins


class TestPositionalFallback:
    def test_no_id_in_head_falls_back_to_position(self, tmp_path: Path) -> None:
        """Legacy / agent-without-ID format: positional matching still
        works against the most recent prior round's questions."""
        phase_dir = tmp_path / "phase2"
        _write_round(phase_dir, 1, "claude", _stub_turn_with_questions("openai", n=2))
        _write_round(phase_dir, 1, "openai", _stub_turn_with_questions("claude", n=0))
        # Openai r2: answers in numbered list WITHOUT IDs.
        _write_round(phase_dir, 2, "openai",
                     "## Answers to claude's open questions\n\n"
                     "1. answer body one\n"
                     "2. answer body two\n\n"
                     "## Status\nSTATUS: NEGOTIATING\n")
        _write_round(phase_dir, 2, "claude",
                     "## Status\nSTATUS: NEGOTIATING\n")

        qs = [q for q in reconstruct_questions(tmp_path, phase=2)
              if q.raised_by == "claude"]
        assert len(qs) == 2
        # Both should be answered via positional fallback.
        assert all(q.status == "answered" for q in qs)


def test_max_lookahead_constant_default() -> None:
    """If we accidentally change the default, the integration tests above
    that rely on N=4 still pass — but flag the tightening here."""
    assert MAX_ANSWER_LOOKAHEAD_ROUNDS >= 4
