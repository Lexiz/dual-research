"""Spec 0034 — end-to-end aggregator wiring for questions + anchor IDs.

Asserts that:
- ``Run.questions`` populates from on-disk Phase 2 + Phase 4 turn files.
- ``Disagreement.raised_turn_key`` / ``closed_turn_key`` are threaded from
  the progression steps.
- ``phase_review_items[*]`` entries carry ``block_id`` resolved against
  the prior content.
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.ui.aggregator import load_run_snapshot


def _seed_session(tmp_path: Path) -> Path:
    session = tmp_path / "run-test"
    session.mkdir()
    (session / "brief.md").write_text("# Brief\n\nThe brief body.\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "phase": "phase2",
                "drafter": None,
                "agreed_plan": None,
                "final_surfaced_disagreements": [],
                "draft_round": 1,
                "final_emitted_to": None,
            }
        ),
        encoding="utf-8",
    )
    (session / "metrics.json").write_text(
        json.dumps({"total_cost_usd": 0.0}), encoding="utf-8"
    )
    (session / "transcript.jsonl").write_text("", encoding="utf-8")
    # Phase 1 drafts — prior content for Phase 2 round 1 anchor resolution.
    p1 = session / "phase1"
    p1.mkdir()
    (p1 / "draft-claude.md").write_text(
        "# Claude P1\n\nClaude proposes a NoSQL approach.\n",
        encoding="utf-8",
    )
    (p1 / "draft-openai.md").write_text(
        "# OpenAI P1\n\n## Findings\nSQLite is fine for low-concurrency reads.\n",
        encoding="utf-8",
    )
    return session


def _seed_phase2_turn(session: Path, round_n: int, agent: str, body: str) -> None:
    p2 = session / "phase2"
    p2.mkdir(exist_ok=True)
    rr = f"{round_n:02d}"
    (p2 / f"round-{rr}-{agent}.md").write_text(body, encoding="utf-8")


def test_questions_populate_on_run_snapshot(tmp_path: Path) -> None:
    session = _seed_session(tmp_path)
    _seed_phase2_turn(
        session,
        1,
        "claude",
        """## Summary
S.

## Open questions for openai
1. Have you measured concurrency under WAL mode?
> quote: SQLite is fine for low-concurrency reads.
""",
    )
    _seed_phase2_turn(
        session,
        1,
        "openai",
        "## Summary\nGPT.\n\n## Open questions for claude\n(none)\n",
    )

    run = load_run_snapshot(session)

    assert len(run.questions) == 1
    q = run.questions[0]
    assert q.id == "Q-c-r1-01"
    assert q.raised_turn_key == "phase2_round1_claude"
    assert q.phase == 2
    # Anchor pre-resolved against GPT's Phase 1 draft.
    assert q.block_id is not None


def test_questions_unanswered_when_no_round2_exists(tmp_path: Path) -> None:
    session = _seed_session(tmp_path)
    _seed_phase2_turn(
        session,
        1,
        "claude",
        "## Summary\nS.\n\n## Open questions for openai\n1. A question.\n",
    )

    run = load_run_snapshot(session)
    assert run.questions[0].status == "open"
    assert run.questions[0].answered_round is None


def test_disagreement_raised_turn_key_populated(tmp_path: Path) -> None:
    """Disagreements get raised_turn_key + closed_turn_key threaded from
    their progression steps."""
    session = _seed_session(tmp_path)
    # A round-1 turn with a D-1 anchor.
    _seed_phase2_turn(
        session,
        1,
        "claude",
        """## Summary
S.

## Substantive disagreements I'm holding
- D-1: SQLite vs Postgres — status: open
- (a) D-1: persistence choice
- (b) I claim: Postgres scales better
- (c) They claim: SQLite is fine
- (d) Why I'm not yet conceding: WAL benchmarks unclear
- (e) Materiality: changes the deployment story

## Open questions for openai
(none)
""",
    )
    _seed_phase2_turn(
        session, 1, "openai", "## Summary\nGPT.\n\n## Open questions for claude\n(none)\n"
    )

    run = load_run_snapshot(session)
    assert len(run.disagreements) >= 1
    d = run.disagreements[0]
    # Raised in round 1 by claude.
    assert d.raised_turn_key == "phase2_round1_claude"
    # Still open → no closed_turn_key.
    assert d.closed_turn_key is None


def test_review_items_carry_block_id(tmp_path: Path) -> None:
    """``phase_review_items[*]`` entries are dicts with ``block_id`` set
    when the agent's quote matched the prior content."""
    session = _seed_session(tmp_path)
    _seed_phase2_turn(
        session,
        1,
        "claude",
        """## Summary
S.

## Open questions for openai
1. Have you measured concurrency?
> quote: SQLite is fine for low-concurrency reads
""",
    )
    _seed_phase2_turn(
        session, 1, "openai", "## Summary\nGPT.\n\n## Open questions for claude\n(none)\n"
    )

    run = load_run_snapshot(session)
    items = run.phase_review_items.get("phase2_round1_claude", [])
    assert items, "Expected at least one review item"
    # The first item is a question with a verbatim quote → block_id resolved.
    assert items[0]["block_id"] is not None
