"""Review-item extraction in the aggregator — spec 0027.

After load_run_snapshot, `Run.phase_review_items` contains structured
question / disagreement / resolved entries keyed by
`phase2_round{R}_<agent>`. The wire format serialises this as
`phaseReviewItems` (camelCase at the boundary).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from dual_research.ui import load_run_snapshot


def _minimal_session(session: Path) -> None:
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
    line = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "run_started",
            "session_dir": str(session),
            "slug": session.name,
            "model_tier": "test",
            "claude_model": "claude-haiku-4-5",
            "openai_model": "gpt-5-mini",
            "soft_cap": 3,
            "hard_cap": 5,
        }
    )
    (session / "transcript.jsonl").write_text(line + "\n", encoding="utf-8")
    (session / "brief.md").write_text("# Topic\n\nBody\n", encoding="utf-8")


def test_phase2_review_items_keyed_by_round_and_agent(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-review"
    session.mkdir()
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.md").write_text(
        dedent(
            """
            STATUS: NEGOTIATING

            ## Open questions for openai

            1. Why SQLite for the write path?
               > quote: SQLite is fine end-to-end at our scale
            2. What about replication?
               > after: 5. Reliability

            ## Substantive disagreements I'm holding

            - D-1: index strategy — status: open
              > quote: composite (created_at, status) is enough
            """
        ).strip(),
        encoding="utf-8",
    )
    (session / "phase2" / "round-01-openai.md").write_text(
        dedent(
            """
            STATUS: NEGOTIATING

            ## Open questions for claude

            1. Bare question with no anchor.
            """
        ).strip(),
        encoding="utf-8",
    )
    run = load_run_snapshot(session)

    claude_items = run.phase_review_items["phase2_round1_claude"]
    assert len(claude_items) == 3
    questions = [i for i in claude_items if i["kind"] == "question"]
    assert len(questions) == 2
    assert questions[0]["quote"] == "SQLite is fine end-to-end at our scale"
    assert questions[1]["after"] == "5. Reliability"
    disagreements = [i for i in claude_items if i["kind"] == "disagreement"]
    assert len(disagreements) == 1
    assert disagreements[0]["item_id"] == "D-1"

    gpt_items = run.phase_review_items["phase2_round1_gpt"]
    assert len(gpt_items) == 1
    assert gpt_items[0]["quote"] is None
    assert gpt_items[0]["after"] is None


def test_empty_phase2_directory_means_empty_review_items(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-empty"
    session.mkdir()
    _minimal_session(session)
    run = load_run_snapshot(session)
    assert run.phase_review_items == {}


def test_turn_with_no_anchored_sections_yields_no_key(tmp_path: Path) -> None:
    """If a turn file has no Open questions / Disagreements sections at all,
    the aggregator doesn't synthesise an empty key."""
    session = tmp_path / "20260516-100000-no-sections"
    session.mkdir()
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.md").write_text(
        "STATUS: NEGOTIATING\n\n## Plan as I currently propose it\n\n- foo\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert "phase2_round1_claude" not in run.phase_review_items


def test_malformed_round_files_skipped(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-mal"
    session.mkdir()
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.malformed-1.md").write_text(
        "## Open questions for openai\n\n1. ignored\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert run.phase_review_items == {}
