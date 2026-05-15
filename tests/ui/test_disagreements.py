"""Tests for the disagreement reconstruction parser.

Golden tests reuse a checked-in fixture session directory; format-edge tests
use synthetic markdown files written to ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from dual_research.ui.disagreements import (
    _parse_section,
    mark_deadlocked_open,
    reconstruct,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "runs"
FIXTURE_CACHE_RUN = FIXTURE_ROOT / "20260515-124552-cache-multi-round"

# The fixture session dir lives under gitignored runs/. Skip fixture-dependent
# tests when it is not present (e.g. fresh clone / CI). Synthetic tests still run.
requires_fixture = pytest.mark.skipif(
    not FIXTURE_CACHE_RUN.exists(),
    reason="cache-multi-round fixture run not present",
)


# ─── Section parser (synthetic markdown) ─────────────────────────────────────


class TestParseSection:
    def test_open_form_single(self):
        section = dedent(
            """\
            - D-3: Compiler performance (tsc-go) — status: open
              - (a) D-3: "Compiler performance is no longer an objection."
              - (b) My position: gains are real but partial.
              - (c) Claude's position: compile overhead eliminated.
              - (d) Why I am not yet conceding: insufficient benchmarks.
              - (e) Materiality: affects the JS-exception window.
            """
        )
        out = _parse_section(section)
        assert len(out) == 1
        d = out[0]
        assert d["id"] == "d-03"
        assert d["status"] == "open"
        assert "Compiler performance" in d["label"]
        assert "Compiler performance" in d["point"]
        assert "gains are real" in d["my_position"]
        assert "compile overhead eliminated" in d["other_position"]
        assert "insufficient benchmarks" in d["why"]
        assert "JS-exception" in d["materiality"]

    def test_resolved_form_with_bold_and_parenthetical_label(self):
        section = dedent(
            """\
            - **D-1 (adoption numbers):** `resolved` — Conceded unsourced percentages.
            - **D-2 (Node.js native type stripping):** `resolved` — Production limitation acknowledged.
            """
        )
        out = _parse_section(section)
        assert len(out) == 2
        assert out[0]["id"] == "d-01"
        assert out[0]["status"] == "resolved"
        assert out[0]["label"] == "adoption numbers"
        assert "Conceded" in out[0]["resolution_note"]
        assert out[1]["label"] == "Node.js native type stripping"
        assert out[1]["status"] == "resolved"

    def test_resolved_form_with_period_separator(self):
        # round-03-claude.md style: "Resolved. <note>"
        section = dedent(
            """\
            - **D-1 (adoption numbers):** Resolved. Conceded unsourced percentages.
            """
        )
        out = _parse_section(section)
        assert len(out) == 1
        assert out[0]["status"] == "resolved"
        assert "Conceded" in out[0]["resolution_note"]

    def test_non_blocking_limitation(self):
        section = dedent(
            """\
            - **D-5 (team thresholds):** `non_blocking_limitation` — Both agree on broad strokes.
            """
        )
        out = _parse_section(section)
        assert len(out) == 1
        assert out[0]["status"] == "non_blocking_limitation"
        assert out[0]["label"] == "team thresholds"

    def test_multiple_disagreements_distinct_blocks(self):
        section = dedent(
            """\
            - D-1: First — status: open
              - (a) D-1: "first point"
              - (b) My position: pos1
            - D-2: Second — status: open
              - (a) D-2: "second point"
              - (b) My position: pos2
            """
        )
        out = _parse_section(section)
        assert [d["id"] for d in out] == ["d-01", "d-02"]
        assert out[0]["point"] == "first point"
        assert out[1]["point"] == "second point"

    def test_empty_section(self):
        assert _parse_section("") == []

    def test_h3_heading_anchor(self):
        # Claude's preferred mid-negotiation form: D-N entries as H3 headings.
        section = dedent(
            """\
            ### D-1: SQLite in production (categorical vs. conditional)

            - **Claude position:** narrow.
            - **OpenAI position:** broad.

            ### D-2: Concurrency semantics

            - **Claude position:** strict.
            """
        )
        out = _parse_section(section)
        ids = [d["id"] for d in out]
        assert ids == ["d-01", "d-02"]
        assert "SQLite in production" in out[0]["label"]

    def test_numbered_paren_anchor_with_status(self):
        # OpenAI's negotiation form: numbered list with closing paren.
        section = dedent(
            """\
            1) D-1: Scope of acceptable production use for SQLite — open
            2) D-2: Concurrency semantics — open
            """
        )
        out = _parse_section(section)
        assert [d["id"] for d in out] == ["d-01", "d-02"]
        assert out[0]["status"] == "open"
        assert "Scope" in out[0]["label"]

    def test_numbered_period_anchor_terminal(self):
        # OpenAI's resolved form: numbered with period + terminal-state.
        section = dedent(
            """\
            1. D-1: Operational cost — non_blocking_limitation. Evidence: managed pricing.
            2. D-2: Durability caveats — resolved. Both agree.
            """
        )
        out = _parse_section(section)
        statuses = {d["id"]: d["status"] for d in out}
        assert statuses == {"d-01": "non_blocking_limitation", "d-02": "resolved"}

    def test_prose_mentioning_d1_does_not_match(self):
        # Defensive: a passing reference to "D-1" inside running prose without
        # an anchor should NOT trip the parser.
        section = "Earlier in this round we labelled the contested point D-1, but it has since been dropped.\n"
        assert _parse_section(section) == []


def test_read_round_file_pulls_resolved_section(tmp_path):
    # Claude's late-round pattern: substantive section empty, entries live
    # under "## Resolved or non-blocking differences". The parser should pick
    # them up so they don't disappear from the timeline.
    from dual_research.ui.disagreements import _read_round_file

    body = dedent(
        """\
        ## Substantive disagreements I'm holding
        (None remaining. All prior disagreements have been resolved.)

        ## Resolved or non-blocking differences
        - **D-1 (SQLite production):** `resolved` — Both agents now accept the conditional framing.
        - **D-2 (WAL concurrency):** `resolved` — Documentation citation accepted.
        """
    )
    path = tmp_path / "round-04-claude.md"
    path.write_text(body, encoding="utf-8")
    entries = _read_round_file(path)
    ids = sorted(e["id"] for e in entries)
    assert ids == ["d-01", "d-02"]
    assert all(e["status"] == "resolved" for e in entries)


# ─── reconstruct() against the cache-multi-round fixture ──────────────────────


@requires_fixture
class TestReconstructFixture:
    def test_phase_2_yields_d_one_through_six(self):
        ds = reconstruct(FIXTURE_CACHE_RUN, phase=2)
        ids = sorted(d.id for d in ds)
        assert ids == ["d-01", "d-02", "d-03", "d-04", "d-05", "d-06"]

    def test_all_resolved(self):
        # The cache-multi-round run completed with all disagreements resolved.
        ds = reconstruct(FIXTURE_CACHE_RUN, phase=2)
        statuses = {d.id: d.status for d in ds}
        for d_id, status in statuses.items():
            assert status != "open", f"{d_id} unexpectedly open: {status}"
            assert status.startswith("resolved-"), f"{d_id} has odd status {status}"

    def test_progression_first_step_is_meaningful(self):
        ds = {d.id: d for d in reconstruct(FIXTURE_CACHE_RUN, phase=2)}
        # D-3 was the active negotiation thread; both agents touched it.
        d3 = ds["d-03"]
        assert d3.progression, "D-3 should have at least one progression step"
        # The progression includes at least one action from claude or gpt.
        agents_seen = {step.agent for step in d3.progression}
        assert agents_seen & {"claude", "gpt"}

    def test_short_label_populated(self):
        ds = reconstruct(FIXTURE_CACHE_RUN, phase=2)
        for d in ds:
            assert d.short_label, f"{d.id} has empty short_label"
            assert d.short_label != d.id, f"{d.id} fell back to its id"

    def test_no_phase_returns_empty(self):
        assert reconstruct(FIXTURE_CACHE_RUN, phase=1) == []
        assert reconstruct(FIXTURE_CACHE_RUN, phase=3) == []


# ─── reconstruct() with a synthetic phase directory ──────────────────────────


def _write_phase2_round(
    tmp_path: Path, round_n: int, agent: str, body: str
) -> None:
    p2 = tmp_path / "phase2"
    p2.mkdir(exist_ok=True)
    (p2 / f"round-{round_n:02d}-{agent}.md").write_text(body, encoding="utf-8")


class TestReconstructSynthetic:
    def test_missing_phase_dir(self, tmp_path):
        assert reconstruct(tmp_path, phase=2) == []

    def test_single_round_open_disagreement(self, tmp_path):
        body = dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: Scope — status: open
              - (a) D-1: "scope debate"
              - (b) My position: narrow scope
              - (c) Other's position: broad scope
            """
        )
        _write_phase2_round(tmp_path, 1, "claude", body)
        ds = reconstruct(tmp_path, phase=2)
        assert len(ds) == 1
        assert ds[0].id == "d-01"
        assert ds[0].status == "open"
        assert ds[0].raised_by == "claude"
        assert ds[0].opened_round == 1

    def test_concession_attributes_resolution_to_other_agent(self, tmp_path):
        # Claude raises D-1 in round 1 (open). Claude concedes in round 2.
        round1 = dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: A point — status: open
              - (a) D-1: "the point"
              - (b) My position: claude view
            """
        )
        round2 = dedent(
            """\
            ## Substantive disagreements I'm holding

            - **D-1 (a point):** `resolved` — Conceded after review.
            """
        )
        _write_phase2_round(tmp_path, 1, "claude", round1)
        _write_phase2_round(tmp_path, 2, "claude", round2)
        ds = reconstruct(tmp_path, phase=2)
        assert len(ds) == 1
        # Claude conceded, so the disagreement is resolved in gpt's favor.
        assert ds[0].status == "resolved-gpt"
        assert ds[0].closed_round == 2

    def test_deadlock_tagging(self, tmp_path):
        body = dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: Stuck — status: open
              - (a) D-1: "stuck point"
              - (b) My position: pos
            """
        )
        _write_phase2_round(tmp_path, 1, "claude", body)
        ds = reconstruct(tmp_path, phase=2)
        tagged = mark_deadlocked_open(ds, hard_cap_hit=True)
        assert tagged[0].status == "open"
        assert tagged[0].deadlocked is True

    def test_deadlock_skips_resolved(self, tmp_path):
        body = dedent(
            """\
            ## Substantive disagreements I'm holding

            - **D-1 (point):** `resolved` — Done.
            """
        )
        _write_phase2_round(tmp_path, 1, "claude", body)
        ds = reconstruct(tmp_path, phase=2)
        tagged = mark_deadlocked_open(ds, hard_cap_hit=True)
        assert tagged[0].deadlocked is False  # was resolved, not deadlocked

    def test_invalid_phase_returns_empty(self, tmp_path):
        # Only phases 2 and 4 are negotiation/review phases.
        assert reconstruct(tmp_path, phase=1) == []
        assert reconstruct(tmp_path, phase=3) == []
