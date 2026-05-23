"""Pick the next dev spec number atomically.

The repo is the source of truth: scan `specs/NNNN-*.md`, return max + 1 zero-padded.
The skill that calls this is expected to commit + push the new file immediately; if
the push fails (parallel session won the race), retry by recomputing.

Spec 0199 §2.1 — IDs are either `NNNN` (integer parent) or `NNNN.M` (parent + single
decimal child). One decimal level only; `0170.1.1` is forbidden by grammar. Queue
order is intrinsic to the ID: sort by `(parent, child)` tuple with child defaulting
to 0 for plain integers.
"""

from __future__ import annotations

import re
from pathlib import Path

# Spec 0199 §2.1 — strict 4-digit parent + optional one-level decimal child.
SPEC_ID_RE = re.compile(r"^(\d{4})(?:\.(\d+))?-")

# Legacy alias kept for any external readers; the new code paths use SPEC_ID_RE.
SPEC_FILE_RE = SPEC_ID_RE


def parse_spec_id(name_or_id: str) -> tuple[int, int]:
    """Parse a filename stem or bare ID into `(parent, child)`.

    Accepts `"0170"`, `"0170.1"`, `"0170-slug"`, `"0170.1-slug"`. Returns
    `(parent_int, child_int)` with `child=0` for plain integers. Raises
    `ValueError` on malformed input; two-level decimals (`0170.1.1`) raise
    with a dedicated message so callers can distinguish the grammar
    violation from a generic parse failure.
    """
    if not name_or_id:
        raise ValueError(f"empty spec id: {name_or_id!r}")
    # Strip filename extension if present.
    stem = name_or_id
    if stem.endswith(".md"):
        stem = stem[:-3]
    # Two-level decimal check first — the bare-ID prefix (everything before
    # the first `-`) must not contain more than one dot.
    bare = stem.split("-", 1)[0]
    if bare.count(".") > 1:
        raise ValueError(f"two-level decimal IDs are forbidden: {name_or_id!r}")
    # Match either a full filename stem (`NNNN[.M]-slug`) or a bare ID (`NNNN[.M]`).
    m = re.match(r"^(\d{4})(?:\.(\d+))?(?:-|$)", stem)
    if not m:
        raise ValueError(f"malformed spec id: {name_or_id!r}")
    parent = int(m.group(1))
    child_raw = m.group(2)
    child = int(child_raw) if child_raw is not None else 0
    return (parent, child)


def format_spec_id(parent: int, child: int = 0) -> str:
    """Inverse of `parse_spec_id`. `(170, 0) → "0170"`, `(170, 1) → "0170.1"`."""
    if parent < 0 or child < 0:
        raise ValueError(f"spec id components must be non-negative: ({parent}, {child})")
    if child == 0:
        return f"{parent:04d}"
    return f"{parent:04d}.{child}"


def _scan_spec_ids(specs_dir: str | Path) -> list[tuple[int, int, Path]]:
    """Return `[(parent, child, path), …]` for every `NNNN[.M]-*.md` in `specs_dir`."""
    p = Path(specs_dir)
    out: list[tuple[int, int, Path]] = []
    for entry in p.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        m = SPEC_ID_RE.match(entry.name)
        if not m:
            continue
        parent = int(m.group(1))
        child = int(m.group(2)) if m.group(2) else 0
        out.append((parent, child, entry))
    return out


def next_dev_number(specs_dir: str | Path) -> str:
    """Return the next zero-padded 4-digit dev spec number as a string.

    Considers only parent IDs — decimal children do not advance the integer
    counter. Specs `0170`, `0170.1`, `0171` → next is `0172`.
    """
    parents: set[int] = {parent for parent, _, _ in _scan_spec_ids(specs_dir)}
    nxt = (max(parents) + 1) if parents else 1
    return format_spec_id(nxt, 0)


def next_decimal_child(specs_dir: str | Path, parent: str) -> str:
    """Return the next decimal child ID for `parent`.

    `next_decimal_child('specs', '0170')` returns `"0170.1"` when no children
    exist, `"0170.2"` when `0170.1-*.md` exists, etc. Raises `ValueError` if
    `parent` itself contains a decimal — only one nesting level is permitted.
    """
    parent_parsed = parse_spec_id(parent)
    if parent_parsed[1] != 0:
        raise ValueError(
            f"cannot create decimal child of a decimal spec: {parent!r} "
            "— one-level grammar only (spec 0199 §2.1)"
        )
    parent_int = parent_parsed[0]
    children: list[int] = [
        child
        for p, child, _ in _scan_spec_ids(specs_dir)
        if p == parent_int and child > 0
    ]
    nxt = (max(children) + 1) if children else 1
    return format_spec_id(parent_int, nxt)


def next_draft_id(drafts_dir: str | Path) -> str:
    """Return the next zero-padded 3-digit draft id as a string."""
    p = Path(drafts_dir)
    p.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"^draft-(\d{3})-")
    numbers: list[int] = []
    for entry in p.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        m = pattern.match(entry.name)
        if m:
            numbers.append(int(m.group(1)))
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{nxt:03d}"


def current_queue(specs_dir: str | Path) -> list[tuple[str, dict]]:
    """Return `[(spec_id, frontmatter), …]` for all queued dev specs.

    Spec 0199 §2.1 — sorted by `parse_spec_id(filename)` ascending. The
    returned key is the spec ID string (e.g. `"0170"`, `"0170.1"`), not the
    legacy `queue_position` integer.
    """
    from .frontmatter import parse

    items: list[tuple[tuple[int, int], str, dict]] = []
    for parent, child, entry in _scan_spec_ids(specs_dir):
        fm = parse(entry).frontmatter
        if fm.get("kind") == "dev" and fm.get("status") == "queued":
            spec_id = format_spec_id(parent, child)
            items.append(((parent, child), spec_id, fm))
    items.sort(key=lambda t: t[0])
    return [(spec_id, fm) for _, spec_id, fm in items]
