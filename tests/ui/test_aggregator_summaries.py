"""Summary-card extraction in the aggregator — spec 0025.

The aggregator now populates `Run.brief_summary` (heuristic TL;DR of
brief.md) and `Run.phase_summaries` (per-turn `## Summary` body keyed by
`phase{N}_<agent>` or `phase{N}_round{R}_<agent>`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dual_research.ui import load_run_snapshot


def _minimal_session(session: Path) -> None:
    """Skeleton state.json + transcript.jsonl so the aggregator runs cleanly."""
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


def test_brief_summary_synthesised_from_brief_body(tmp_path: Path) -> None:
    session = tmp_path / "20260515-100000-summary-test"
    session.mkdir()
    (session / "brief.md").write_text(
        "# Compare SQLite vs Postgres\n\n"
        "We need a real-world performance comparison. "
        "Specifically for a single-tenant API.\n",
        encoding="utf-8",
    )
    _minimal_session(session)
    run = load_run_snapshot(session)
    assert run.brief_summary is not None
    assert run.brief_summary.startswith("We need a real-world performance comparison")


def test_brief_summary_uses_explicit_summary_section(tmp_path: Path) -> None:
    """If the brief itself carries a `## Summary` it wins over the heuristic."""
    session = tmp_path / "20260515-100000-explicit-summary"
    session.mkdir()
    (session / "brief.md").write_text(
        "# Some brief\n\n"
        "## Summary\n\n"
        "One-liner that should win.\n\n"
        "## Body\n\n"
        "Lots of other prose that the heuristic would otherwise grab.\n",
        encoding="utf-8",
    )
    _minimal_session(session)
    run = load_run_snapshot(session)
    assert run.brief_summary == "One-liner that should win."


def test_phase1_summaries_extracted_per_agent(tmp_path: Path) -> None:
    session = tmp_path / "20260515-100000-p1"
    session.mkdir()
    (session / "brief.md").write_text("# Topic\n\nBody\n", encoding="utf-8")
    _minimal_session(session)
    (session / "phase1").mkdir()
    (session / "phase1" / "draft-claude.md").write_text(
        "## Summary\n\nClaude's first take.\n\n## Body\n\n...\n",
        encoding="utf-8",
    )
    (session / "phase1" / "draft-openai.md").write_text(
        "## Summary\n\nOpenAI's first take.\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert run.phase_summaries["phase1_claude"] == "Claude's first take."
    # UI vocabulary: openai → gpt at the keys.
    assert run.phase_summaries["phase1_gpt"] == "OpenAI's first take."


def test_phase2_summaries_keyed_by_round_and_agent(tmp_path: Path) -> None:
    session = tmp_path / "20260515-100000-p2"
    session.mkdir()
    (session / "brief.md").write_text("# Topic\n\n", encoding="utf-8")
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.md").write_text(
        "STATUS: NEGOTIATING\n\n## Summary of my position\n\n"
        "I think Postgres for everything.\n",
        encoding="utf-8",
    )
    (session / "phase2" / "round-01-openai.md").write_text(
        "STATUS: NEGOTIATING\n\n## Summary\n\n"
        "SQLite for read-heavy paths.\n",
        encoding="utf-8",
    )
    (session / "phase2" / "round-02-claude.md").write_text(
        "STATUS: NEGOTIATING\n\n## Summary\n\nClaude round 2.\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert run.phase_summaries["phase2_round1_claude"] == "I think Postgres for everything."
    assert run.phase_summaries["phase2_round1_gpt"] == "SQLite for read-heavy paths."
    assert run.phase_summaries["phase2_round2_claude"] == "Claude round 2."


def test_missing_summary_section_does_not_create_key(tmp_path: Path) -> None:
    session = tmp_path / "20260515-100000-nosum"
    session.mkdir()
    (session / "brief.md").write_text("# Topic\n\n", encoding="utf-8")
    _minimal_session(session)
    (session / "phase1").mkdir()
    (session / "phase1" / "draft-claude.md").write_text(
        "STATUS: WORKING\n\n## Body\n\nNo summary at all.\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert "phase1_claude" not in run.phase_summaries


def test_malformed_round_files_skipped(tmp_path: Path) -> None:
    """`.malformed-N.md` files are repair artefacts, not real turns."""
    session = tmp_path / "20260515-100000-malformed"
    session.mkdir()
    (session / "brief.md").write_text("# Topic\n", encoding="utf-8")
    _minimal_session(session)
    (session / "phase2").mkdir()
    (session / "phase2" / "round-01-claude.malformed-1.md").write_text(
        "## Summary\n\nShould be ignored.\n",
        encoding="utf-8",
    )
    run = load_run_snapshot(session)
    assert run.phase_summaries == {}
