"""Unit tests for the Supabase data source (spec 0020)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.ui.datasource import SupabaseSessionData, latest_event_seq

from .supabase_fake import FakeSupabaseClient


def test_materialize_writes_files_and_transcript(tmp_path: Path) -> None:
    fake = FakeSupabaseClient(
        session_files=[
            {"run_id": "R1", "path": "brief.md", "content": "# Topic\n\nbody"},
            {"run_id": "R1", "path": "phase2/round-01-claude.md", "content": "claude r1"},
            {"run_id": "R1", "path": "phase2/round-01-openai.md", "content": "openai r1"},
            {"run_id": "R2", "path": "brief.md", "content": "# Other run\n"},
        ],
        events=[
            {"run_id": "R1", "seq": 0, "ts": "2026-05-15T16:00:00+00:00", "kind": "run_started", "payload": {"model_tier": "test"}},
            {"run_id": "R1", "seq": 1, "ts": "2026-05-15T16:01:00+00:00", "kind": "turn_ended", "payload": {"agent": "claude"}},
        ],
    )

    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        assert (tmp / "brief.md").read_text() == "# Topic\n\nbody"
        assert (tmp / "phase2/round-01-claude.md").read_text() == "claude r1"
        assert (tmp / "phase2/round-01-openai.md").read_text() == "openai r1"
        assert not (tmp / "../brief.md").exists()  # R2 file not included

        lines = (tmp / "transcript.jsonl").read_text().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["event"] == "run_started"
        assert first["ts"] == "2026-05-15T16:00:00+00:00"
        assert first["model_tier"] == "test"


def test_materialize_writes_empty_transcript_when_no_events(tmp_path: Path) -> None:
    fake = FakeSupabaseClient(
        session_files=[{"run_id": "R1", "path": "brief.md", "content": "# X"}],
        events=[],
    )
    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        assert (tmp / "transcript.jsonl").read_text() == ""


def test_materialize_cleans_up_on_exit() -> None:
    fake = FakeSupabaseClient(
        session_files=[{"run_id": "R1", "path": "brief.md", "content": "x"}],
        events=[],
    )
    captured: Path | None = None
    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        captured = tmp
        assert tmp.exists()
    assert captured is not None
    assert not captured.exists()


def test_latest_event_seq_returns_max(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSupabaseClient(
        events=[
            {"run_id": "R1", "seq": 0, "ts": "t", "kind": "k", "payload": {}},
            {"run_id": "R1", "seq": 1, "ts": "t", "kind": "k", "payload": {}},
            {"run_id": "R1", "seq": 5, "ts": "t", "kind": "k", "payload": {}},
            {"run_id": "R2", "seq": 99, "ts": "t", "kind": "k", "payload": {}},
        ],
    )
    assert latest_event_seq(fake, "R1") == 5


def test_latest_event_seq_returns_negative_one_when_no_events() -> None:
    fake = FakeSupabaseClient(events=[])
    assert latest_event_seq(fake, "R1") == -1


def test_materialize_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    from dual_research.ui import datasource

    monkeypatch.setattr(datasource, "SESSION_FILE_PAGE_SIZE", 2)
    files = [
        {"run_id": "R1", "path": f"phase2/round-{i:02d}-claude.md", "content": f"r{i}"}
        for i in range(1, 6)
    ]
    fake = FakeSupabaseClient(session_files=files, events=[])
    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        for i in range(1, 6):
            assert (tmp / f"phase2/round-{i:02d}-claude.md").read_text() == f"r{i}"


def test_materialize_restores_binary_blobs_byte_for_byte() -> None:
    """Spec 0025. `attachment_blobs` rows are base64-decoded and written
    under <tmp>/attachments/<name> so the aggregator + the
    attachment-blobs endpoint can read them identically to a real
    on-disk session-dir.
    """
    import base64

    raw_png = b"\x89PNG-fake-binary-content"
    raw_pdf = b"%PDF-1.4 fake"

    fake = FakeSupabaseClient(
        session_files=[
            {"run_id": "R1", "path": "brief.md", "content": "# topic\n"},
            {
                "run_id": "R1",
                "path": "attachments.json",
                "content": json.dumps({"attachments": []}),
            },
        ],
        attachment_blobs=[
            {
                "run_id": "R1",
                "rel_path": "attachments/abc-foo.png",
                "mime": "image/png",
                "size_bytes": len(raw_png),
                "content_b64": base64.b64encode(raw_png).decode("ascii"),
            },
            {
                "run_id": "R1",
                "rel_path": "attachments/xyz-bar.pdf",
                "mime": "application/pdf",
                "size_bytes": len(raw_pdf),
                "content_b64": base64.b64encode(raw_pdf).decode("ascii"),
            },
            {
                "run_id": "R2",
                "rel_path": "attachments/other.png",
                "mime": "image/png",
                "size_bytes": 4,
                "content_b64": base64.b64encode(b"OTHR").decode("ascii"),
            },
        ],
    )
    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        assert (tmp / "attachments/abc-foo.png").read_bytes() == raw_png
        assert (tmp / "attachments/xyz-bar.pdf").read_bytes() == raw_pdf
        # Other-run blob is filtered out by the eq("run_id", …) clause.
        assert not (tmp / "attachments/other.png").exists()


def test_materialize_no_blobs_is_clean() -> None:
    fake = FakeSupabaseClient(
        session_files=[{"run_id": "R1", "path": "brief.md", "content": "# X"}],
    )
    with SupabaseSessionData(fake, "R1").materialize() as tmp:
        # attachments/ is only created when there are blobs.
        assert not (tmp / "attachments").exists()
