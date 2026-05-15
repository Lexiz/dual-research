"""Notion block renderer attachment capture — spec 0025.

Drives `_render_blocks` directly with synthetic block payloads. The block
shapes match the Notion REST API. No HTTP traffic happens here — we
construct the renderer's inputs by hand and assert on the attachments
list it populates.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from dual_research.ingest.attachments import Attachment
from dual_research.ingest.notion import _render_blocks


class _StubClient:
    """`_render_blocks` only calls `get_block_children` for nested blocks.

    None of our test blocks have children, so the stub raises if called —
    which would surface a test bug rather than silently lose attachments.
    """

    async def get_block_children(self, block_id: str) -> list[dict]:  # noqa: D401
        raise AssertionError("not expected to be called in these tests")


def _run(blocks: list[dict[str, Any]]) -> tuple[str, list[Attachment]]:
    atts: list[Attachment] = []
    md = asyncio.run(
        _render_blocks(
            _StubClient(),
            blocks,
            depth=0,
            child_pages_out=[],
            attachments_out=atts,
        )
    )
    return md, atts


def test_image_block_emits_image_attachment() -> None:
    blocks = [
        {
            "id": "block-1",
            "type": "image",
            "image": {
                "file": {"url": "https://notion-static/img-1.png"},
                "caption": [{"plain_text": "architecture diagram", "annotations": {}}],
            },
        }
    ]
    md, atts = _run(blocks)
    assert "![architecture diagram](https://notion-static/img-1.png)" in md
    image_atts = [a for a in atts if a.kind == "image"]
    assert len(image_atts) == 1
    a = image_atts[0]
    assert a.url == "https://notion-static/img-1.png"
    assert a.title == "architecture diagram"
    assert a.caption == "architecture diagram"
    assert a.source == "notion:block-1"


def test_pdf_block_emits_pdf_attachment() -> None:
    blocks = [
        {
            "id": "block-pdf",
            "type": "pdf",
            "pdf": {
                "file": {"url": "https://notion-static/report.pdf"},
                "name": "Annual report 2026",
                "caption": [],
            },
        }
    ]
    md, atts = _run(blocks)
    pdfs = [a for a in atts if a.kind == "pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].title == "Annual report 2026"
    assert pdfs[0].url == "https://notion-static/report.pdf"


def test_bookmark_block_emits_link_attachment() -> None:
    blocks = [
        {
            "id": "bm-1",
            "type": "bookmark",
            "bookmark": {"url": "https://example.com/post"},
        }
    ]
    md, atts = _run(blocks)
    links = [a for a in atts if a.kind == "link"]
    assert len(links) == 1
    assert links[0].url == "https://example.com/post"


def test_inline_link_in_paragraph_emits_link_attachment() -> None:
    blocks = [
        {
            "id": "p-1",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "plain_text": "See ",
                        "annotations": {},
                    },
                    {
                        "plain_text": "the docs",
                        "annotations": {},
                        "href": "https://docs.example.com",
                    },
                ],
            },
        }
    ]
    md, atts = _run(blocks)
    assert "the docs" in md
    link_atts = [a for a in atts if a.kind == "link"]
    assert len(link_atts) == 1
    assert link_atts[0].url == "https://docs.example.com"
    assert link_atts[0].title == "the docs"


def test_repeated_url_dedupes() -> None:
    # An inline rich-text link plus a bookmark for the same URL → one entry.
    blocks = [
        {
            "id": "p-1",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"plain_text": "See it", "annotations": {}, "href": "https://example.com/x"},
                ],
            },
        },
        {
            "id": "bm-1",
            "type": "bookmark",
            "bookmark": {"url": "https://example.com/x"},
        },
    ]
    _md, atts = _run(blocks)
    matching = [a for a in atts if a.url == "https://example.com/x"]
    # First match (rich-text link) wins; bookmark is suppressed.
    assert len(matching) == 1


def test_table_row_emits_attachments_from_cell_links() -> None:
    blocks = [
        {
            "id": "tr-1",
            "type": "table_row",
            "table_row": {
                "cells": [
                    [
                        {
                            "plain_text": "link",
                            "annotations": {},
                            "href": "https://example.org/x",
                        }
                    ],
                ],
            },
        }
    ]
    _md, atts = _run(blocks)
    assert any(a.url == "https://example.org/x" for a in atts)


def test_no_attachments_for_plain_paragraph() -> None:
    blocks = [
        {
            "id": "p-1",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "just text", "annotations": {}}]},
        }
    ]
    md, atts = _run(blocks)
    assert "just text" in md
    assert atts == []
