"""Pick the next dev spec number atomically.

The repo is the source of truth: scan `specs/NNNN-*.md`, return max + 1 zero-padded.
The skill that calls this is expected to commit + push the new file immediately; if
the push fails (parallel session won the race), retry by recomputing.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC_FILE_RE = re.compile(r"^(\d{4})-")


def next_dev_number(specs_dir: str | Path) -> str:
    """Return the next zero-padded 4-digit dev spec number as a string."""
    p = Path(specs_dir)
    numbers: list[int] = []
    for entry in p.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        m = SPEC_FILE_RE.match(entry.name)
        if m:
            numbers.append(int(m.group(1)))
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{nxt:04d}"


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


def current_queue(specs_dir: str | Path) -> list[tuple[int, dict]]:
    """Return `[(queue_position, frontmatter), …]` for all queued dev specs, sorted."""
    from .frontmatter import parse

    items: list[tuple[int, dict]] = []
    for entry in sorted(Path(specs_dir).iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if not SPEC_FILE_RE.match(entry.name):
            continue
        fm = parse(entry).frontmatter
        if fm.get("kind") == "dev" and fm.get("status") == "queued":
            pos = int(fm.get("queue_position", 0) or 0)
            items.append((pos, fm))
    items.sort(key=lambda t: t[0])
    return items


def next_queue_position(specs_dir: str | Path) -> int:
    """Next queue_position to assign — max + 1, or 1 if queue empty."""
    queue = current_queue(specs_dir)
    if not queue:
        return 1
    return max(pos for pos, _ in queue) + 1
