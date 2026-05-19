"""Tests for queue_v2.reason — alignment-note detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.queue_v2 import parse_spec, reason


def _make_parsed(
    spec: str = "0093",
    files_touched: list[str] | None = None,
    css_anchors: list[str] | None = None,
    handover_read_paths: list[str] | None = None,
) -> parse_spec.ParsedSpec:
    return parse_spec.ParsedSpec(
        spec=spec,
        slug="dummy",
        title="t",
        label="refactoring",
        version_bump="PATCH",
        target_version="0.72.2",
        file_path=f"specs/{spec}-dummy.md",
        handover_read_paths=handover_read_paths or [],
        files_touched=files_touched or [],
        notion_issues=[],
        design_anchors=[],
        acceptance=[],
        visual_matrix=[],
        css_anchors=css_anchors or [],
        backend_touched=False,
        raw_sections={},
    )


def test_no_notes_when_clean(tmp_path: Path) -> None:
    (tmp_path / "handoffs").mkdir()
    parsed = _make_parsed(files_touched=["src/foo/bar.css"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert notes == []


def test_missing_handover_read_halts(tmp_path: Path) -> None:
    (tmp_path / "handoffs").mkdir()
    parsed = _make_parsed(handover_read_paths=["handoffs/never-existed.md"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert len(notes) == 1
    assert "did not finish cleanly" in notes[0]


def test_handover_read_present_no_note(tmp_path: Path) -> None:
    (tmp_path / "handoffs").mkdir()
    target = tmp_path / "handoffs" / "exists.md"
    target.write_text("# placeholder\n")
    parsed = _make_parsed(handover_read_paths=["handoffs/exists.md"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert notes == []


def test_files_touched_overlap_with_recent_handover(tmp_path: Path) -> None:
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    # The previous arc handover mentions the path inside backticks.
    (handoffs / "2026-05-18-prior.md").write_text(
        "# previous spec\n\nTouched `src/dual_research/ui/static/tokens.css`.\n"
    )
    parsed = _make_parsed(files_touched=["src/dual_research/ui/static/tokens.css"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert len(notes) == 1
    assert "previous spec" in notes[0]
    assert "tokens.css" in notes[0]


def test_css_anchor_collision_with_recent_handover(tmp_path: Path) -> None:
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    (handoffs / "2026-05-18-prior.md").write_text(
        "# previous\n\nIntroduced `.t-display-l` for the M3 type scale.\n"
    )
    parsed = _make_parsed(css_anchors=[".t-display-l → #type"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert any(".t-display-l" in n for n in notes)


def test_unrelated_handover_text_produces_no_note(tmp_path: Path) -> None:
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    (handoffs / "2026-05-18-prior.md").write_text("# prior\n\nNo overlap here.\n")
    parsed = _make_parsed(files_touched=["src/foo.css"], css_anchors=[".foo"])
    notes = reason.detect_alignment_notes(parsed, tmp_path)
    assert notes == []
