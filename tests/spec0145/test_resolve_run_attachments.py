"""Spec 0145 — `_resolve_run_attachments` + `_attachment_id` helpers.

The helpers convert `ingest.Attachment` (richer dataclass on disk) into
`prompt_pieces.Attachment` (minimal piece-emitter view threaded through
the protocol layer). Tests pin the canonical-ID derivation (sha256[:8]
preferred, slugified basename fallback) and the per-file content read
behaviour (text extensions get their bytes; binary extensions stay
empty so the heuristic estimator returns 0 tokens).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.ingest.attachments import Attachment as IngestAttachment
from dual_research.orchestrator.run import (
    _attachment_id,
    _read_attachment_text,
    _resolve_run_attachments,
)
from dual_research.protocol.prompt_pieces import Attachment as PieceAttachment


class TestAttachmentId:
    def test_sha256_prefix_preferred(self) -> None:
        ing = IngestAttachment(
            kind="file",
            source="foo.md",
            rel_path="attachments/abc.md",
            sha256="a3f4b9c2d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
        )
        assert _attachment_id(ing) == "a3f4b9c2"

    def test_slugifies_basename_when_no_sha(self) -> None:
        ing = IngestAttachment(
            kind="file",
            source="report.pdf",
            rel_path="attachments/some-report-2026.pdf",
            sha256=None,
        )
        assert _attachment_id(ing) == "some-report-2026"

    def test_fallback_when_no_metadata(self) -> None:
        ing = IngestAttachment(kind="link", source="", rel_path=None, sha256=None)
        assert _attachment_id(ing) == "attachment"


class TestReadAttachmentText:
    def test_reads_text_attachment(self, tmp_path: Path) -> None:
        att_dir = tmp_path / "attachments"
        att_dir.mkdir()
        (att_dir / "spec.md").write_text("# Heading\n\nbody", encoding="utf-8")
        ing = IngestAttachment(
            kind="file", source="spec.md", rel_path="attachments/spec.md",
        )
        assert _read_attachment_text(tmp_path, ing) == "# Heading\n\nbody"

    def test_binary_attachment_returns_empty(self, tmp_path: Path) -> None:
        att_dir = tmp_path / "attachments"
        att_dir.mkdir()
        (att_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        ing = IngestAttachment(
            kind="image", source="image.png", rel_path="attachments/image.png",
        )
        assert _read_attachment_text(tmp_path, ing) == ""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        ing = IngestAttachment(
            kind="file", source="missing.md", rel_path="attachments/missing.md",
        )
        assert _read_attachment_text(tmp_path, ing) == ""

    def test_no_rel_path_returns_empty(self) -> None:
        ing = IngestAttachment(kind="link", source="https://example.com", rel_path=None)
        assert _read_attachment_text(Path("/nonexistent"), ing) == ""


class TestResolveRunAttachments:
    def test_no_attachments_json_returns_empty_list(self, tmp_path: Path) -> None:
        assert _resolve_run_attachments(tmp_path) == []

    def test_empty_bundle_returns_empty_list(self, tmp_path: Path) -> None:
        (tmp_path / "attachments.json").write_text(
            json.dumps({"attachments": []}), encoding="utf-8",
        )
        assert _resolve_run_attachments(tmp_path) == []

    def test_roundtrips_to_piece_attachments(self, tmp_path: Path) -> None:
        att_dir = tmp_path / "attachments"
        att_dir.mkdir()
        (att_dir / "spec.md").write_text("Spec body", encoding="utf-8")
        bundle = {
            "attachments": [
                {
                    "kind": "file",
                    "source": "spec.md",
                    "rel_path": "attachments/spec.md",
                    "title": "Project spec",
                    "sha256": "deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe",
                },
                {
                    "kind": "link",
                    "source": "https://example.com/whitepaper",
                    "title": "Whitepaper link",
                },
            ],
        }
        (tmp_path / "attachments.json").write_text(
            json.dumps(bundle), encoding="utf-8",
        )
        out = _resolve_run_attachments(tmp_path)
        assert len(out) == 2
        assert isinstance(out[0], PieceAttachment)
        # sha256[:8] → "deadbeef"
        assert out[0].id == "deadbeef"
        assert out[0].title == "Project spec"
        assert out[0].content == "Spec body"
        # The link attachment has no rel_path or sha — falls back to source slug.
        assert out[1].id  # non-empty
        assert out[1].content == ""

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "attachments.json").write_text("{not json", encoding="utf-8")
        assert _resolve_run_attachments(tmp_path) == []
