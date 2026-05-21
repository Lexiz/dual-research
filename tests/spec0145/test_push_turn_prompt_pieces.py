"""Spec 0145 §5.2 — push-CLI per-piece persistence.

`_push_turn_prompt_pieces` is the helper that converts a single
`turn_ended` event's `prompt_pieces` dict into one row per
`(artifact_id, tokens)` pair, with `attachment_id` parsed for
attachment rows and `display_title` resolved via the contemporaneous
attachments.json. Tests drive it directly to keep coverage independent
of the full push pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.persistence.remote import (
    _iter_turn_prompt_pieces_rows,
    _load_attachments_title_map,
    _push_turn_prompt_pieces,
)


class TestLoadAttachmentsTitleMap:
    def test_missing_attachments_json_returns_empty(self, tmp_path: Path) -> None:
        assert _load_attachments_title_map(tmp_path) == {}

    def test_empty_bundle_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "attachments.json").write_text(
            json.dumps({"attachments": []}), encoding="utf-8",
        )
        assert _load_attachments_title_map(tmp_path) == {}

    def test_resolves_titles_keyed_by_canonical_id(self, tmp_path: Path) -> None:
        (tmp_path / "attachments.json").write_text(
            json.dumps({
                "attachments": [
                    {
                        "kind": "file",
                        "source": "spec.md",
                        "rel_path": "attachments/spec.md",
                        "title": "Project spec",
                        "sha256": "deadbeef" + "0" * 56,
                    },
                ],
            }),
            encoding="utf-8",
        )
        m = _load_attachments_title_map(tmp_path)
        assert m == {"deadbeef": "Project spec"}


class TestPushTurnPromptPiecesHelper:
    def test_emits_one_row_per_piece(self) -> None:
        prompt_pieces = {
            "system.task.plan_negotiation": 1903,
            "user_prompt.message": 5251,
            "phase1.claude": 10971,
        }
        rows = list(_push_turn_prompt_pieces(
            "run-123",
            "phase2_round1_claude",
            prompt_pieces,
            title_for_id={},
        ))
        assert len(rows) == 3
        artifact_ids = sorted(r["artifact_id"] for r in rows)
        assert artifact_ids == sorted(prompt_pieces.keys())
        # tokens round-trip; attachment_id is None for non-attachment rows.
        sys_row = next(r for r in rows if r["artifact_id"] == "system.task.plan_negotiation")
        assert sys_row["tokens"] == 1903
        assert sys_row["attachment_id"] is None
        assert sys_row["display_title"] == "Plan-negotiation instructions"
        assert sys_row["run_id"] == "run-123"
        assert sys_row["turn_key"] == "phase2_round1_claude"

    def test_parses_attachment_id_from_canonical_template(self) -> None:
        rows = list(_push_turn_prompt_pieces(
            "run-1",
            "phase0_claude",
            {"user_prompt.attachment.abc12345": 42},
            title_for_id={"abc12345": "My document"},
        ))
        assert len(rows) == 1
        row = rows[0]
        assert row["artifact_id"] == "user_prompt.attachment.abc12345"
        assert row["attachment_id"] == "abc12345"
        assert row["display_title"] == "Attachment · My document"
        assert row["tokens"] == 42

    def test_falls_back_to_attachment_id_when_title_missing(self) -> None:
        rows = list(_push_turn_prompt_pieces(
            "run-1",
            "phase0_claude",
            {"user_prompt.attachment.zz": 1},
            title_for_id={},
        ))
        # display_name() returns "Attachment · zz" when no title is mapped.
        assert rows[0]["display_title"] == "Attachment · zz"

    def test_empty_pieces_yields_no_rows(self) -> None:
        assert list(_push_turn_prompt_pieces("r", "k", {}, {})) == []

    def test_non_integer_token_is_skipped(self) -> None:
        rows = list(_push_turn_prompt_pieces(
            "r", "k",
            {"user_prompt.message": "not-a-number", "phase1.claude": 100},
            {},
        ))
        # Only the int-coercible row makes it through.
        assert [r["artifact_id"] for r in rows] == ["phase1.claude"]


class TestIterTurnPromptPiecesRows:
    def test_filters_non_turn_ended_events(self, tmp_path: Path) -> None:
        event_rows = [
            {
                "kind": "phase_entered",
                "payload": {"phase": "phase2", "prompt_pieces": {"x": 1}},
            },
            {
                "kind": "turn_ended",
                "payload": {
                    "agent": "claude",
                    "phase": "phase2",
                    "label": "phase2-r1-claude",
                    "prompt_pieces": {"user_prompt.message": 100},
                },
            },
        ]
        rows = list(_iter_turn_prompt_pieces_rows("r", tmp_path, event_rows))
        assert len(rows) == 1
        assert rows[0]["turn_key"] == "phase2_round1_claude"
        assert rows[0]["artifact_id"] == "user_prompt.message"

    def test_empty_prompt_pieces_yields_nothing(self, tmp_path: Path) -> None:
        event_rows = [{
            "kind": "turn_ended",
            "payload": {
                "agent": "claude",
                "phase": "phase1",
                "label": "phase1-claude",
                "prompt_pieces": {},
            },
        }]
        assert list(_iter_turn_prompt_pieces_rows("r", tmp_path, event_rows)) == []

    def test_missing_required_fields_yields_nothing(self, tmp_path: Path) -> None:
        # No agent → can't derive turn_key → skip.
        event_rows = [{
            "kind": "turn_ended",
            "payload": {"phase": "phase1", "label": "x", "prompt_pieces": {"k": 1}},
        }]
        assert list(_iter_turn_prompt_pieces_rows("r", tmp_path, event_rows)) == []

    def test_threads_attachment_titles_into_display_title(self, tmp_path: Path) -> None:
        (tmp_path / "attachments.json").write_text(
            json.dumps({
                "attachments": [{
                    "kind": "file",
                    "source": "spec.md",
                    "rel_path": "attachments/spec.md",
                    "title": "Project spec",
                    "sha256": "abc12345" + "0" * 56,
                }],
            }),
            encoding="utf-8",
        )
        event_rows = [{
            "kind": "turn_ended",
            "payload": {
                "agent": "claude",
                "phase": "phase0",
                "label": "phase0-r1-claude",
                "prompt_pieces": {"user_prompt.attachment.abc12345": 99},
            },
        }]
        rows = list(_iter_turn_prompt_pieces_rows("r", tmp_path, event_rows))
        assert len(rows) == 1
        assert rows[0]["attachment_id"] == "abc12345"
        assert rows[0]["display_title"] == "Attachment · Project spec"
