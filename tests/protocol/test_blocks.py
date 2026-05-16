"""Spec 0034 — markdown block-ID assignment.

Block IDs are the single source of truth for side-by-side anchor
resolution: the backend assigns them via ``assign_block_ids``, embeds
``<!-- block-id: b-N -->`` HTML comments after each block, and the
frontend's Markdown renderer lifts the IDs onto rendered DOM nodes.

These tests lock the boundary heuristic — paragraph, heading,
top-level list item, fenced code, blockquote.
"""

from __future__ import annotations

from dual_research.protocol.blocks import assign_block_ids


class TestSequentialIds:
    def test_paragraph_block(self) -> None:
        rewritten, records = assign_block_ids("Just one paragraph.")
        assert len(records) == 1
        assert records[0].id == "b-1"
        assert records[0].text == "Just one paragraph."
        assert "<!-- block-id: b-1 -->" in rewritten

    def test_two_paragraphs(self) -> None:
        md = "First para.\n\nSecond para."
        _, records = assign_block_ids(md)
        assert [r.id for r in records] == ["b-1", "b-2"]
        assert records[0].text == "First para."
        assert records[1].text == "Second para."

    def test_heading_is_its_own_block(self) -> None:
        md = "# Heading\n\nPara."
        _, records = assign_block_ids(md)
        assert [r.id for r in records] == ["b-1", "b-2"]
        # Heading marker stripped in the text body.
        assert records[0].text == "Heading"

    def test_list_items_each_a_block(self) -> None:
        md = "- one\n- two\n- three"
        _, records = assign_block_ids(md)
        assert [r.id for r in records] == ["b-1", "b-2", "b-3"]
        assert records[0].text == "one"
        assert records[1].text == "two"
        assert records[2].text == "three"

    def test_numbered_list_items_each_a_block(self) -> None:
        md = "1. one\n2. two"
        _, records = assign_block_ids(md)
        assert len(records) == 2
        assert records[0].text == "one"


class TestFencedCode:
    def test_code_fence_is_atomic(self) -> None:
        md = "Para before.\n\n```python\nprint('hi')\n```\n\nPara after."
        _, records = assign_block_ids(md)
        ids = [r.id for r in records]
        assert ids == ["b-1", "b-2", "b-3"]
        # Code interior preserved verbatim (fences stripped).
        assert "print('hi')" in records[1].text


class TestBlockquote:
    def test_blockquote_lines_merged(self) -> None:
        md = "> first line\n> second line\n\nAfter."
        _, records = assign_block_ids(md)
        assert len(records) == 2
        # Blockquote markers stripped.
        assert "first line" in records[0].text
        assert "second line" in records[0].text
        assert "> " not in records[0].text


class TestComments:
    def test_comments_embedded_after_each_block(self) -> None:
        md = "# H\n\nPara."
        rewritten, _ = assign_block_ids(md)
        lines = rewritten.split("\n")
        # The comment line must IMMEDIATELY follow each block's last source
        # line — that's the contract the frontend lifts IDs from.
        assert lines == [
            "# H",
            "<!-- block-id: b-1 -->",
            "",
            "Para.",
            "<!-- block-id: b-2 -->",
        ]

    def test_pre_existing_comments_dropped(self) -> None:
        """Re-running on already-IDed markdown is idempotent — the old
        comments don't accumulate."""
        md = "Para.\n<!-- block-id: b-1 -->\n\nSecond."
        rewritten, records = assign_block_ids(md)
        # Two blocks, IDs re-assigned cleanly.
        assert [r.id for r in records] == ["b-1", "b-2"]
        # Old comment was filtered out before re-emission.
        assert rewritten.count("block-id: b-1") == 1


class TestEmpty:
    def test_empty_string(self) -> None:
        rewritten, records = assign_block_ids("")
        assert rewritten == ""
        assert records == []

    def test_whitespace_only(self) -> None:
        rewritten, records = assign_block_ids("\n\n   \n")
        assert records == []


class TestWhitespaceNormalisation:
    def test_paragraph_text_collapses_internal_whitespace(self) -> None:
        md = "Some   text   with   gaps."
        _, records = assign_block_ids(md)
        assert records[0].text == "Some text with gaps."

    def test_text_strips_outer_whitespace(self) -> None:
        md = "\n\nSome text.\n\n"
        _, records = assign_block_ids(md)
        assert records[0].text == "Some text."
