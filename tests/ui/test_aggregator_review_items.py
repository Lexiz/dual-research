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


def test_turn_with_no_anchored_sections_yields_empty_bucket(tmp_path: Path) -> None:
    """Spec 0042 D7 — the aggregator ALWAYS creates a bucket for every
    turn file it walks, even when the parser finds no items. This
    resolves the prior absence-as-empty ambiguity: an empty list now
    means "we looked and there's nothing there"; a missing key now
    means "the turn file doesn't exist on disk."

    Pre-spec the same condition silently skipped key creation, which
    made it impossible for the frontend to distinguish "parser found
    nothing" from "never parsed."
    """
    session = tmp_path / "20260516-100000-no-sections"
    session.mkdir()
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.md").write_text(
        "STATUS: NEGOTIATING\n\n## Plan as I currently propose it\n\n- foo\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert run.phase_review_items.get("phase2_round1_claude") == []


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


# ─── Phase 4 + current_draft_path (spec 0028) ────────────────────────────────


def test_phase4_review_items_keyed_correctly(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-p4"
    session.mkdir()
    _minimal_session(session)
    (session / "phase4").mkdir()
    (session / "phase4" / "round-01-openai.md").write_text(
        dedent(
            """
            STATUS: REVIEWING

            ## Comments on the current draft

            1. (a) Findings section; (b) framing reads as causal; (c) reframe.
               > quote: density causes lower per-household retrofit cost
            2. (a) Disagreements; (b) FSD-2 missing; (c) add it.
               > after: 3. Disagreements left open

            ## Issue ledger (delta + currently open)

            1. I-1 status: open — Confidence ledger missing for baseline cohort.
               > after: 6. Confidence ledger
            """
        ).strip(),
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    key = "phase4_round1_gpt"
    assert key in run.phase_review_items
    items = run.phase_review_items[key]
    # Spec 0041 D1 — the parser now classifies the three Phase 4
    # sections under distinct kinds (issue / comment / question)
    # instead of bucketing all three under "question". The aggregator
    # surfaces them on this list in the order their sections appear.
    assert len(items) == 3
    kinds = sorted(i["kind"] for i in items)
    assert kinds == ["comment", "comment", "issue"]
    # Phase 2 keys still absent.
    assert all(k.startswith("phase4_") for k in run.phase_review_items.keys())


def test_current_draft_path_falls_back_to_phase3(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-p3only"
    session.mkdir()
    _minimal_session(session)
    (session / "phase3").mkdir()
    (session / "phase3" / "draft-v1.md").write_text("# Draft v1\n", encoding="utf-8")
    run = load_run_snapshot(session)
    assert run.current_draft_path == "phase3/draft-v1.md"


def test_current_draft_path_prefers_highest_phase4_revision(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-revisions"
    session.mkdir()
    _minimal_session(session)
    (session / "phase3").mkdir()
    (session / "phase3" / "draft-v1.md").write_text("v1\n", encoding="utf-8")
    (session / "phase4").mkdir()
    (session / "phase4" / "draft-v2.md").write_text("v2\n", encoding="utf-8")
    (session / "phase4" / "draft-v4.md").write_text("v4\n", encoding="utf-8")
    (session / "phase4" / "draft-v3.md").write_text("v3\n", encoding="utf-8")
    run = load_run_snapshot(session)
    assert run.current_draft_path == "phase4/draft-v4.md"


def test_current_draft_path_null_when_phase3_not_complete(tmp_path: Path) -> None:
    session = tmp_path / "20260516-100000-early"
    session.mkdir()
    _minimal_session(session)
    run = load_run_snapshot(session)
    assert run.current_draft_path is None
