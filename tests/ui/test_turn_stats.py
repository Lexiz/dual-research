"""Tests for the per-turn protocol-stat parser (spec 0013)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from dual_research.ui.turn_stats import build_phase_stats

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "runs"
FIXTURE_CACHE_RUN = FIXTURE_ROOT / "20260515-124552-cache-multi-round"

requires_fixture = pytest.mark.skipif(
    not FIXTURE_CACHE_RUN.exists(),
    reason="cache-multi-round fixture run not present",
)


# ─── Synthetic tests ──────────────────────────────────────────────────────────


def _make_phase0(tmp_path: Path, agent: str, body: str) -> None:
    d = tmp_path / "phase0"
    d.mkdir(exist_ok=True)
    (d / f"preflight-{agent}.md").write_text(body, encoding="utf-8")


def _make_phase1(tmp_path: Path, agent: str, body: str) -> None:
    d = tmp_path / "phase1"
    d.mkdir(exist_ok=True)
    (d / f"draft-{agent}.md").write_text(body, encoding="utf-8")


def _make_round(tmp_path: Path, phase: int, round_n: int, agent: str, body: str) -> None:
    d = tmp_path / f"phase{phase}"
    d.mkdir(exist_ok=True)
    (d / f"round-{round_n:02d}-{agent}.md").write_text(body, encoding="utf-8")


class TestBuildPhaseStatsSynthetic:
    def test_empty_dir_returns_empty(self, tmp_path):
        ps = build_phase_stats(tmp_path)
        assert ps.phase0 == {}
        assert ps.phase1 == {}
        assert ps.phase2 == {}
        assert ps.phase4 == {}

    def test_phase0_preflight_parsed(self, tmp_path):
        _make_phase0(tmp_path, "claude", "STATUS: BRIEF_OK\nBRIEF_ISSUES: 2\n")
        _make_phase0(tmp_path, "openai", "STATUS: BRIEF_NEEDS_INPUT\nBRIEF_ISSUES: 5\n")
        ps = build_phase_stats(tmp_path)
        # openai → gpt at the UI layer
        assert ps.phase0["claude"].status == "BRIEF_OK"
        assert ps.phase0["claude"].brief_issues == 2
        assert ps.phase0["gpt"].status == "BRIEF_NEEDS_INPUT"
        assert ps.phase0["gpt"].brief_issues == 5

    def test_phase1_drafts_parse_negotiation_markers_when_present(self, tmp_path):
        _make_phase1(tmp_path, "claude", dedent("""\
            # Independent plan — claude
            STATUS: NEGOTIATING
            OPEN_QUESTIONS: 3
            BLOCKING_DISAGREEMENTS: 1
        """))
        ps = build_phase_stats(tmp_path)
        s = ps.phase1["claude"]
        assert s.status == "NEGOTIATING"
        assert s.open_questions == 3
        assert s.blocking == 1

    def test_phase2_rounds_keyed_by_round(self, tmp_path):
        _make_round(tmp_path, 2, 1, "claude", "STATUS: NEGOTIATING\nOPEN_QUESTIONS: 4\nBLOCKING_DISAGREEMENTS: 2\n")
        _make_round(tmp_path, 2, 1, "openai", "STATUS: NEGOTIATING\nOPEN_QUESTIONS: 5\nBLOCKING_DISAGREEMENTS: 0\n")
        _make_round(tmp_path, 2, 2, "claude", "STATUS: AGREED\nOPEN_QUESTIONS: 0\n")
        ps = build_phase_stats(tmp_path)
        assert sorted(ps.phase2.keys()) == [1, 2]
        assert ps.phase2[1]["claude"].open_questions == 4
        assert ps.phase2[1]["gpt"].open_questions == 5
        assert ps.phase2[2]["claude"].status == "AGREED"
        assert "gpt" not in ps.phase2[2]  # openai round-02 file absent

    def test_phase4_uses_open_issues_field(self, tmp_path):
        _make_round(tmp_path, 4, 1, "claude", "STATUS: REVIEWING\nOPEN_ISSUES: 3\n")
        _make_round(tmp_path, 4, 1, "openai", "STATUS: APPROVED\nOPEN_ISSUES: 0\n")
        ps = build_phase_stats(tmp_path)
        assert ps.phase4[1]["claude"].open_issues == 3
        assert ps.phase4[1]["gpt"].open_issues == 0
        assert ps.phase4[1]["gpt"].status == "APPROVED"

    def test_malformed_round_files_are_ignored(self, tmp_path):
        # round-NN-{agent}.malformed-K.md should NOT be picked up.
        d = tmp_path / "phase2"
        d.mkdir()
        (d / "round-02-claude.malformed-1.md").write_text("STATUS: GARBAGE\n", encoding="utf-8")
        (d / "round-02-claude.md").write_text("STATUS: AGREED\n", encoding="utf-8")
        ps = build_phase_stats(tmp_path)
        assert ps.phase2[2]["claude"].status == "AGREED"

    def test_partial_file_returns_partial_stats(self, tmp_path):
        # Missing OPEN_QUESTIONS marker → field stays None, others still parse.
        _make_round(tmp_path, 2, 1, "claude", "STATUS: NEGOTIATING\nBLOCKING_DISAGREEMENTS: 1\n")
        ps = build_phase_stats(tmp_path)
        s = ps.phase2[1]["claude"]
        assert s.status == "NEGOTIATING"
        assert s.open_questions is None
        assert s.blocking == 1


# ─── Fixture golden ───────────────────────────────────────────────────────────


@requires_fixture
class TestBuildPhaseStatsFixture:
    def test_cache_multi_round_phase0(self):
        ps = build_phase_stats(FIXTURE_CACHE_RUN)
        assert "claude" in ps.phase0 and "gpt" in ps.phase0
        # Both agents flagged some brief issues during preflight.
        assert ps.phase0["claude"].brief_issues is not None
        assert ps.phase0["gpt"].brief_issues is not None

    def test_cache_multi_round_phase2_status_progression(self):
        ps = build_phase_stats(FIXTURE_CACHE_RUN)
        assert sorted(ps.phase2.keys()) == [1, 2, 3, 4, 5]
        # Round 1 should be NEGOTIATING for both; round 5 should be AGREED for both.
        assert ps.phase2[1]["claude"].status == "NEGOTIATING"
        assert ps.phase2[1]["gpt"].status == "NEGOTIATING"
        assert ps.phase2[5]["claude"].status == "AGREED"
        assert ps.phase2[5]["gpt"].status == "AGREED"

    def test_cache_multi_round_phase4_final_approved(self):
        ps = build_phase_stats(FIXTURE_CACHE_RUN)
        last_round = max(ps.phase4.keys())
        # The run completed cleanly — final review round should be APPROVED both sides.
        assert ps.phase4[last_round]["claude"].status == "APPROVED"
        assert ps.phase4[last_round]["gpt"].status == "APPROVED"
