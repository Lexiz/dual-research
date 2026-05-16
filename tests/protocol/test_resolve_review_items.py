"""Spec 0034 — pre-resolved anchor IDs on ReviewItems.

``resolve_review_items`` is the parse-time replacement for the
render-time ``findBlockWithText`` scan. Given a turn's text and the
prior content's BlockRecords, it walks the extracted items and stamps
``block_id`` on the ones whose ``quote``/``after`` anchor matches a
prior block.
"""

from __future__ import annotations

from dual_research.protocol.blocks import assign_block_ids
from dual_research.protocol.parse import resolve_review_items


PRIOR_CONTENT = """# GPT Phase 1 Draft

## Summary
We propose using SQLite for the persistence layer.

## Detailed findings
SQLite is fine for low-concurrency reads.
Postgres would be overkill at this scale.
"""


def _prior_blocks():
    _, records = assign_block_ids(PRIOR_CONTENT)
    return records


class TestVerbatimQuoteResolves:
    def test_full_phrase_match_sets_block_id(self) -> None:
        turn = """## Open questions for openai
1. Have you tested under high concurrency?
> quote: SQLite is fine for low-concurrency reads.
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert len(items) == 1
        # The matching block is b-5 (the "Detailed findings" body
        # paragraph that joins the two SQLite sentences).
        assert items[0].block_id is not None

    def test_substring_quote_still_matches(self) -> None:
        """The anchor doesn't have to be a full block — substring matches."""
        turn = """## Open questions for openai
1. Why SQLite?
> quote: low-concurrency reads
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert items[0].block_id is not None

    def test_whitespace_tolerance(self) -> None:
        turn = """## Open questions for openai
1. Q.
> quote:   SQLite   is   fine  for  low-concurrency  reads
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert items[0].block_id is not None

    def test_case_insensitive(self) -> None:
        turn = """## Open questions for openai
1. Q.
> quote: SQLITE IS FINE FOR LOW-CONCURRENCY READS
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert items[0].block_id is not None


class TestParaphrasedQuoteFails:
    def test_paraphrased_quote_yields_null_block_id(self) -> None:
        turn = """## Open questions for openai
1. Q.
> quote: SQLite cannot handle anything but trivial workloads
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert items[0].block_id is None
        # The original quote is preserved for the frontend's text-scan fallback.
        assert "cannot handle" in items[0].quote


class TestAfterAnchor:
    def test_after_heading_resolves_to_heading_block(self) -> None:
        turn = """## Open questions for openai
1. Where's the migration plan?
> after: Detailed findings
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert items[0].block_id is not None
        # Should resolve to the heading block (b-4 = "Detailed findings").
        # Look up the records to confirm.
        records = _prior_blocks()
        target = next((r for r in records if r.text == "Detailed findings"), None)
        assert target is not None
        assert items[0].block_id == target.id


class TestEmptyPriorBlocks:
    def test_no_prior_blocks_returns_items_with_null_block_id(self) -> None:
        turn = """## Open questions for openai
1. Q.
> quote: anything
"""
        items = resolve_review_items(turn, [])
        assert len(items) == 1
        assert items[0].block_id is None
        # Other fields preserved.
        assert items[0].quote == "anything"


class TestItemWithoutAnchor:
    def test_no_quote_no_after_no_block_id(self) -> None:
        turn = """## Open questions for openai
1. A general question without an anchor.
"""
        items = resolve_review_items(turn, _prior_blocks())
        assert len(items) == 1
        assert items[0].block_id is None
        assert items[0].quote is None
        assert items[0].after is None
