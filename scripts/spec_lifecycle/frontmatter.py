"""Shared YAML frontmatter I/O for specs, drafts, and handoffs.

A spec/draft/handoff file is structured as:

    ---
    key: value
    ...
    ---

    # Body markdown...

This module reads and writes that structure without disturbing body content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # PyYAML, already a project dependency
except ImportError as exc:  # pragma: no cover - signal at import time
    raise ImportError("PyYAML is required: add to pyproject if missing") from exc


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


@dataclass
class ParsedFile:
    """A file split into its frontmatter dict and body string."""

    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    path: Path | None = None

    @property
    def has_frontmatter(self) -> bool:
        return bool(self.frontmatter)


def parse(path: str | Path) -> ParsedFile:
    """Read a file and return its frontmatter + body. Tolerates files with no frontmatter."""
    p = Path(path)
    text = p.read_text()
    return parse_text(text, path=p)


def parse_text(text: str, *, path: Path | None = None) -> ParsedFile:
    """Parse from a string; useful for tests or in-memory composition."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return ParsedFile(frontmatter={}, body=text, path=path)
    raw_fm, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(raw_fm) or {}
    except yaml.YAMLError:
        # Malformed YAML — treat as no frontmatter rather than crashing
        return ParsedFile(frontmatter={}, body=text, path=path)
    if not isinstance(fm, dict):
        return ParsedFile(frontmatter={}, body=text, path=path)
    return ParsedFile(frontmatter=fm, body=body, path=path)


def dump(parsed: ParsedFile, *, path: str | Path | None = None) -> str:
    """Serialise back to text. Use `path` to override write target."""
    fm_text = yaml.safe_dump(
        parsed.frontmatter,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    ).rstrip()
    text = f"---\n{fm_text}\n---\n\n{parsed.body.lstrip()}"
    target = Path(path) if path is not None else parsed.path
    if target is not None:
        target.write_text(text)
    return text


def update_frontmatter(path: str | Path, updates: dict[str, Any]) -> ParsedFile:
    """Read, merge `updates` into frontmatter, write back, return the parsed file."""
    parsed = parse(path)
    parsed.frontmatter.update(updates)
    parsed.path = Path(path)
    dump(parsed)
    return parsed
