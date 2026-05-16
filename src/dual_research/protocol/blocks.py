"""Spec 0034 — markdown block-ID assignment.

Splits a markdown document into top-level "blocks" (paragraph, heading,
list-item, fenced code, blockquote), assigns each one a stable sequential
ID (``b-1``, ``b-2``, …), and returns:

- The rewritten markdown with HTML comments embedded after each block:
  ``<!-- block-id: b-N -->``. The frontend markdown renderer detects
  these comments and lifts the IDs onto rendered DOM nodes; the parser
  uses the records below to pre-resolve ``> quote:`` / ``> after:``
  anchors at parse time so the side-by-side viewer can navigate via
  ``document.getElementById`` rather than scanning DOM text.

- A list of :class:`BlockRecord` carrying each block's ID, plain-text
  body (with markdown punctuation stripped for matching), and its first
  line's 0-indexed position in the source.

Boundary heuristic:
- Top-level blank-line-separated chunks are independent blocks.
- Each ATX heading (``#`` through ``######``) is its own block.
- Each top-level list item (``- ``, ``* ``, ``1. `` …) is its own block,
  including any sub-bullets that hang off it via indentation.
- Fenced code blocks (``` … ```) are atomic.
- Top-level blockquote chunks (``> …``) are atomic; the quote markers
  are stripped for the BlockRecord's text body.

Single source of truth: the frontend renderer must agree with this
module on block boundaries. The frontend reads boundaries off the
embedded HTML comments; it does not re-segment. Drift between the two
is therefore impossible by construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BlockRecord:
    """One markdown block with a stable ID + its plain text for matching."""

    id: str         # "b-1", "b-2", …
    text: str       # plain-text body (markdown punctuation stripped)
    line_start: int  # 0-indexed line in the source markdown


# A block-id HTML comment we emit on rewrite. The frontend renderer
# detects this exact shape and lifts the ID onto the next DOM node.
_BLOCK_ID_COMMENT_RE = re.compile(r"^<!--\s*block-id:\s*(b-\d+)\s*-->\s*$")


def _is_blank(line: str) -> bool:
    return not line.strip()


def _is_atx_heading(line: str) -> bool:
    s = line.lstrip()
    return bool(re.match(r"^#{1,6}\s+\S", s))


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```") or line.lstrip().startswith("~~~")


def _is_top_level_list_item(line: str) -> bool:
    # Top-level (no leading indent) bullet/numbered item.
    if line.startswith((" ", "\t")):
        return False
    return bool(re.match(r"^(?:[-*+]|\d+[.)])\s+\S", line))


def _is_blockquote(line: str) -> bool:
    return line.lstrip().startswith(">")


def _strip_block_text(lines: list[str]) -> str:
    """Render a block's source lines as the plain-text body anchor-resolution
    matches against. Strips heading markers, list markers, blockquote markers,
    and collapses whitespace. Code-fence interiors are preserved verbatim.
    """
    if not lines:
        return ""
    out_lines: list[str] = []
    # If the block opens a fence, preserve interior literally.
    first = lines[0].lstrip()
    if first.startswith("```") or first.startswith("~~~"):
        # Drop the opening + closing fence lines.
        inner = []
        for ln in lines[1:]:
            if ln.lstrip().startswith("```") or ln.lstrip().startswith("~~~"):
                break
            inner.append(ln)
        return "\n".join(inner).strip()
    for ln in lines:
        s = ln
        # Strip ATX heading prefix.
        s = re.sub(r"^\s*#{1,6}\s+", "", s)
        # Strip bullet/numbered markers on the first line of a list item.
        s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
        # Strip blockquote markers.
        s = re.sub(r"^\s*>\s?", "", s)
        out_lines.append(s)
    text = "\n".join(out_lines).strip()
    # Collapse internal runs of whitespace to single spaces — anchor
    # matching is whitespace-tolerant.
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _segment_blocks(source: str) -> list[tuple[int, list[str]]]:
    """Walk the source lines and group them into block-shaped chunks.

    Returns a list of ``(line_start, lines)`` tuples in document order.
    Pre-existing ``<!-- block-id: … -->`` comments are dropped (stale IDs
    from a prior pass don't propagate).
    """
    raw_lines = source.splitlines()
    # Drop pre-existing block-id comments so repeated calls are idempotent.
    lines: list[tuple[int, str]] = [
        (i, ln) for i, ln in enumerate(raw_lines)
        if not _BLOCK_ID_COMMENT_RE.match(ln)
    ]

    blocks: list[tuple[int, list[str]]] = []
    i = 0
    n = len(lines)
    while i < n:
        idx, ln = lines[i]
        if _is_blank(ln):
            i += 1
            continue
        # Heading: single-line block.
        if _is_atx_heading(ln):
            blocks.append((idx, [ln]))
            i += 1
            continue
        # Fenced code: consume until matching closer.
        if _is_fence(ln):
            chunk = [ln]
            i += 1
            while i < n:
                _, ln2 = lines[i]
                chunk.append(ln2)
                if _is_fence(ln2):
                    i += 1
                    break
                i += 1
            blocks.append((idx, chunk))
            continue
        # Top-level list item: consume the item + any indented continuation.
        if _is_top_level_list_item(ln):
            chunk = [ln]
            i += 1
            while i < n:
                _, ln2 = lines[i]
                if _is_blank(ln2):
                    # A blank inside a list-item separates items only if the
                    # next non-blank is itself a top-level list item or a new
                    # block kind. Peek ahead.
                    j = i + 1
                    while j < n and _is_blank(lines[j][1]):
                        j += 1
                    if j >= n:
                        # Trailing blanks — close the item.
                        break
                    _, nxt = lines[j]
                    if _is_top_level_list_item(nxt) or _is_atx_heading(nxt) or _is_fence(nxt):
                        break
                    if not nxt.startswith((" ", "\t")):
                        # Sibling paragraph at top level → new block.
                        break
                    # Otherwise the blank is internal whitespace; absorb.
                    chunk.append(ln2)
                    i += 1
                    continue
                if _is_top_level_list_item(ln2) and not ln2.startswith((" ", "\t")):
                    # Next top-level item starts; close this one.
                    break
                if _is_atx_heading(ln2) or _is_fence(ln2):
                    break
                chunk.append(ln2)
                i += 1
            blocks.append((idx, chunk))
            continue
        # Blockquote: consume contiguous ``> …`` lines.
        if _is_blockquote(ln):
            chunk = [ln]
            i += 1
            while i < n:
                _, ln2 = lines[i]
                if not _is_blockquote(ln2):
                    break
                chunk.append(ln2)
                i += 1
            blocks.append((idx, chunk))
            continue
        # Otherwise: paragraph — consume contiguous non-blank, non-special
        # lines.
        chunk = [ln]
        i += 1
        while i < n:
            _, ln2 = lines[i]
            if _is_blank(ln2):
                break
            if _is_atx_heading(ln2) or _is_fence(ln2):
                break
            if _is_top_level_list_item(ln2):
                break
            if _is_blockquote(ln2):
                break
            chunk.append(ln2)
            i += 1
        blocks.append((idx, chunk))
    return blocks


def assign_block_ids(markdown: str) -> tuple[str, list[BlockRecord]]:
    """Walk ``markdown`` by block, emit IDs + comments, return both."""
    if not markdown:
        return "", []
    blocks = _segment_blocks(markdown)
    records: list[BlockRecord] = []
    out_lines: list[str] = []
    # We rewrite by replaying the source line-by-line, inserting block-id
    # comments after each block's last line. To keep the original spacing,
    # walk the source lines and consult a map from line index → block-end
    # marker.
    raw_lines = markdown.splitlines()
    # Strip any pre-existing block-id comments from the rewrite output.
    filtered_lines = [ln for ln in raw_lines if not _BLOCK_ID_COMMENT_RE.match(ln)]
    # Build a mapping from each block's last source-line index → assigned
    # ID. Note: line indices below are relative to ``filtered_lines``,
    # which is what ``_segment_blocks`` walked.
    end_to_id: dict[int, str] = {}
    for i, (start_idx, chunk) in enumerate(blocks):
        block_id = f"b-{i + 1}"
        records.append(BlockRecord(
            id=block_id,
            text=_strip_block_text(chunk),
            line_start=start_idx,
        ))
        end_to_id[start_idx + len(chunk) - 1] = block_id
    for idx, ln in enumerate(filtered_lines):
        out_lines.append(ln)
        if idx in end_to_id:
            out_lines.append(f"<!-- block-id: {end_to_id[idx]} -->")
    return "\n".join(out_lines), records
