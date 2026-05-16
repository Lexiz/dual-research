"""Spec 0034 — first-class Question reconstruction.

``reconstruct_questions(session_dir, phase=N)`` walks every Phase N
turn file, extracts numbered questions from each agent's
``## Open questions for X`` section, assigns stable IDs
(``Q-c-r1-01`` shape), and threads answer linkage by positional match
with verbatim-text confirmation.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.ui.questions import reconstruct_questions


def _seed_phase2_round_file(
    phase_dir: Path, round_n: int, agent: str, body: str
) -> Path:
    rr = f"{round_n:02d}"
    path = phase_dir / f"round-{rr}-{agent}.md"
    path.write_text(body, encoding="utf-8")
    return path


CLAUDE_R1_TURN = """## Summary
Claude's round 1 summary.

## Open questions for openai
1. Have you load-tested SQLite under WAL mode?
> quote: SQLite handles low-concurrency reads

2. What's your migration plan to Postgres?

## Sources
"""

GPT_R1_TURN = """## Summary
GPT round 1.

## Open questions for claude
1. Have you considered Postgres backup overhead?
"""

GPT_R2_TURN = """## Summary
GPT round 2.

## Answers to claude's open questions
1. Yes, we load-tested SQLite under WAL mode with 1000 concurrent readers.
2. Migration plan TBD.

## Open questions for claude
1. Is your benchmark methodology documented?

## Sources
"""


def test_round1_questions_have_ids(tmp_path: Path) -> None:
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase_dir, 1, "openai", GPT_R1_TURN)

    questions = reconstruct_questions(tmp_path, phase=2)

    # Two from Claude + one from GPT.
    assert len(questions) == 3
    ids = [q.id for q in questions]
    assert ids == ["Q-c-r1-01", "Q-c-r1-02", "Q-g-r1-01"]


def test_round1_questions_anchor_to_raised_turn_key(tmp_path: Path) -> None:
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase_dir, 1, "openai", GPT_R1_TURN)

    questions = reconstruct_questions(tmp_path, phase=2)
    by_id = {q.id: q for q in questions}
    assert by_id["Q-c-r1-01"].raised_turn_key == "phase2_round1_claude"
    assert by_id["Q-c-r1-01"].raised_by == "claude"
    assert by_id["Q-g-r1-01"].raised_turn_key == "phase2_round1_gpt"
    assert by_id["Q-g-r1-01"].raised_by == "gpt"


def test_round1_questions_status_open_when_no_round2_answers(tmp_path: Path) -> None:
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase_dir, 1, "openai", GPT_R1_TURN)

    questions = reconstruct_questions(tmp_path, phase=2)
    for q in questions:
        assert q.status == "open"
        assert q.answered_round is None
        assert q.answered_turn_key is None


def test_round2_answers_thread_back_to_round1_questions(tmp_path: Path) -> None:
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase_dir, 1, "openai", GPT_R1_TURN)
    _seed_phase2_round_file(phase_dir, 2, "openai", GPT_R2_TURN)
    _seed_phase2_round_file(
        phase_dir,
        2,
        "claude",
        "## Summary\nC.\n\n## Open questions for openai\n(none)\n",
    )

    questions = reconstruct_questions(tmp_path, phase=2)
    by_id = {q.id: q for q in questions}
    # Claude's two questions are now answered by GPT's round-2 turn.
    assert by_id["Q-c-r1-01"].status == "answered"
    assert by_id["Q-c-r1-01"].answered_round == 2
    assert by_id["Q-c-r1-01"].answered_by == "gpt"
    assert by_id["Q-c-r1-01"].answered_turn_key == "phase2_round2_gpt"
    # The answer body excerpt is preserved.
    assert "WAL mode" in by_id["Q-c-r1-01"].answer_body


def test_verbatim_answer_match_is_tagged(tmp_path: Path) -> None:
    """When the answer text references the question's first words, the match
    is confirmed as ``verbatim`` instead of just ``positional``."""
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase_dir, 1, "openai", GPT_R1_TURN)
    _seed_phase2_round_file(phase_dir, 2, "openai", GPT_R2_TURN)
    _seed_phase2_round_file(
        phase_dir,
        2,
        "claude",
        "## Summary\nC.\n\n## Open questions for openai\n(none)\n",
    )

    questions = reconstruct_questions(tmp_path, phase=2)
    by_id = {q.id: q for q in questions}
    # GPT's answer "Yes, we load-tested SQLite under WAL mode..." includes
    # the question's first words "Have you load-tested SQLite under WAL"
    # — well, the match is on the first 6 words of the question.
    # Q-c-r1-01 first 6 words: "have you load-tested sqlite under wal"
    # Should match GPT's answer.
    assert by_id["Q-c-r1-01"].match == "verbatim"


def test_partial_answers_leave_trailing_questions_open(tmp_path: Path) -> None:
    """If round N+1 has fewer answers than the prior round had questions,
    the trailing ones stay open."""
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    # Claude raises 3 questions, GPT answers only 1.
    claude_three_q = """## Summary
S.

## Open questions for openai
1. First Q.
2. Second Q.
3. Third Q.
"""
    gpt_one_answer = """## Summary
S.

## Answers to claude's open questions
1. Answer to the first one.

## Open questions for claude
(none)
"""
    _seed_phase2_round_file(phase_dir, 1, "claude", claude_three_q)
    _seed_phase2_round_file(phase_dir, 1, "openai", "## Summary\ngpt\n")
    _seed_phase2_round_file(phase_dir, 2, "openai", gpt_one_answer)

    questions = [q for q in reconstruct_questions(tmp_path, phase=2) if q.raised_by == "claude"]
    by_id = {q.id: q for q in questions}
    assert by_id["Q-c-r1-01"].status == "answered"
    assert by_id["Q-c-r1-02"].status == "open"
    assert by_id["Q-c-r1-03"].status == "open"


def test_phase4_uses_phase4_path(tmp_path: Path) -> None:
    """Phase 4 reconstruct walks the phase4 directory."""
    phase4 = tmp_path / "phase4"
    phase4.mkdir()
    _seed_phase2_round_file(  # naming is generic enough
        phase4,
        1,
        "claude",
        "## Summary\nP4 C.\n\n## Open questions for openai\n1. Phase-4 question.\n",
    )
    questions = reconstruct_questions(tmp_path, phase=4)
    assert len(questions) == 1
    assert questions[0].phase == 4
    assert questions[0].raised_turn_key == "phase4_round1_claude"


def test_phase4_answers_section_uses_prior_comments_heading(tmp_path: Path) -> None:
    """Spec 0040 D1 — Phase 4 round R+1 answers questions raised in
    round R via a ``## Answers to {other}'s prior comments`` section
    (the protocol's Phase 4 phrasing, distinct from Phase 2's
    ``open questions``). The reconstructed Question must transition
    to ``status='answered'`` with both ``answered_round`` and
    ``answered_turn_key`` populated — pre-spec the regex only matched
    ``open questions`` so every Phase 4 question stayed open.
    """
    phase4 = tmp_path / "phase4"
    phase4.mkdir()
    _seed_phase2_round_file(
        phase4,
        1,
        "claude",
        "## Summary\nP4 C.\n\n"
        "## Open questions for openai\n"
        "1. Should we materialise the cost split on the runs table?\n",
    )
    _seed_phase2_round_file(
        phase4,
        1,
        "openai",
        "## Summary\nP4 G.\n",
    )
    _seed_phase2_round_file(
        phase4,
        2,
        "openai",
        "## Summary\nP4 G r2.\n\n"
        "## Answers to claude's prior comments\n"
        "1. Yes — adding a NUMERIC column avoids JSONB filter complexity.\n",
    )

    questions = reconstruct_questions(tmp_path, phase=4)
    by_id = {q.id: q for q in questions}
    q = by_id["Q-c-r1-01"]
    assert q.status == "answered"
    assert q.answered_round == 2
    assert q.answered_by == "gpt"
    assert q.answered_turn_key == "phase4_round2_gpt"


def test_phase4_issue_ledger_only_produces_no_questions(tmp_path: Path) -> None:
    """Spec 0041 D2 — when a Phase 4 turn only has an Issue ledger
    section (no ``## Open questions for X``), the question
    reconstructor returns zero. Pre-spec the parser bucketed Issue
    ledger items under ``kind="question"`` and inflated the count."""
    phase4 = tmp_path / "phase4"
    phase4.mkdir()
    _seed_phase2_round_file(
        phase4, 1, "claude",
        "## Issue ledger (delta + currently open)\n\n"
        "**C-1** — `open` — A draft-level concern.\n",
    )
    assert reconstruct_questions(tmp_path, phase=4) == []


def test_phase2_answers_open_questions_heading_still_recognised(tmp_path: Path) -> None:
    """Spec 0040 D1 regression guard — the Phase 2 ``open questions``
    phrasing must continue to work after the regex accepts both forms.
    """
    phase2 = tmp_path / "phase2"
    phase2.mkdir()
    _seed_phase2_round_file(phase2, 1, "claude", CLAUDE_R1_TURN)
    _seed_phase2_round_file(phase2, 1, "openai", GPT_R1_TURN)
    _seed_phase2_round_file(phase2, 2, "openai", GPT_R2_TURN)

    questions = [q for q in reconstruct_questions(tmp_path, phase=2)
                 if q.raised_by == "claude"]
    by_id = {q.id: q for q in questions}
    assert by_id["Q-c-r1-01"].status == "answered"
    assert by_id["Q-c-r1-01"].answered_turn_key == "phase2_round2_gpt"


def test_empty_directory_returns_empty_list(tmp_path: Path) -> None:
    assert reconstruct_questions(tmp_path, phase=2) == []
    (tmp_path / "phase2").mkdir()
    assert reconstruct_questions(tmp_path, phase=2) == []


def test_question_with_quote_anchor_preserved(tmp_path: Path) -> None:
    phase_dir = tmp_path / "phase2"
    phase_dir.mkdir()
    _seed_phase2_round_file(phase_dir, 1, "claude", CLAUDE_R1_TURN)

    questions = reconstruct_questions(tmp_path, phase=2)
    q1 = next(q for q in questions if q.id == "Q-c-r1-01")
    # The `> quote:` anchor from the turn is preserved on the Question.
    assert q1.quote == "SQLite handles low-concurrency reads"
