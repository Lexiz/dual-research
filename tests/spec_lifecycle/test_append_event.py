"""Tests for scripts.spec_lifecycle.append_event."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.append_event import append_event, read_events


def test_append_and_read(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    append_event(events_dir, "0156", "queued", {"by": "test"}, ts="2026-05-22T10:00:00Z")
    append_event(events_dir, "0156", "in_progress", None, ts="2026-05-22T11:00:00Z")
    events = read_events(events_dir, "0156")
    assert len(events) == 2
    assert events[0]["step"] == "queued"
    assert events[0]["data"]["by"] == "test"
    assert events[1]["step"] == "in_progress"


def test_read_missing_returns_empty(tmp_path: Path) -> None:
    assert read_events(tmp_path / "nope", "9999") == []


def test_malformed_line_skipped(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "0001.jsonl").write_text(
        '{"ts":"x","step":"a","data":{}}\nnot json\n{"ts":"y","step":"b","data":{}}\n'
    )
    events = read_events(events_dir, "0001")
    assert len(events) == 2
    assert [e["step"] for e in events] == ["a", "b"]
