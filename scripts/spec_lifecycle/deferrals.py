"""Parse the ``## Deferred during implementation`` section out of a handoff body.

Spec 0158 introduces a handoff convention: the implementing agent appends a
``## Deferred during implementation`` section to the handoff doc when work
that was in scope at cycle start got dropped during implementation (for
complexity, risk, missing context, or blocking dependency reasons). The
``/dev-next`` step 24.5 deferred-spec subagent reads this section to author
follow-up specs or drafts.

This module exposes one function:

- :func:`parse_deferred_section` — extract the section's items as a list of
  ``DeferredItem`` records, or return ``[]`` if the section is absent or empty.

The parser is intentionally permissive: titles can be bold (`**title**`) or
plain, separators can be em-dash (`—`), en-dash (`–`), or hyphen (`-`), and
context can span continuation lines (indented under the item).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFERRED_HEADING_RE = re.compile(
    r"^##\s+Deferred\s+during\s+implementation\s*$",
    re.IGNORECASE | re.MULTILINE,
)
NEXT_HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)

# ``- **title** — context`` or ``- title — context`` or ``- title - context``
ITEM_HEAD_RE = re.compile(
    r"""
    ^\s*-\s+
    (?:\*\*(?P<bold_title>.+?)\*\*|(?P<plain_title>[^—–\-\n].*?))
    \s+[—–\-]\s+
    (?P<context>.+?)\s*$
    """,
    re.VERBOSE,
)
# Continuation: indented line that isn't a new list item.
CONTINUATION_RE = re.compile(r"^\s+(?!-\s)(?P<text>\S.*)$")
# Blank or new top-level list item — terminates current item's continuation.
NEW_ITEM_OR_BLANK_RE = re.compile(r"^\s*$|^\s*-\s+\S")


@dataclass(frozen=True)
class DeferredItem:
    """One entry from the ``## Deferred during implementation`` section."""

    title: str
    context: str


def parse_deferred_section(handoff_body: str) -> list[DeferredItem]:
    """Return the deferral list from a handoff body, or ``[]`` if absent/empty.

    A "deferred" item looks like::

        ## Deferred during implementation

        - **<short title>** — <one paragraph of context>
        - **<short title>** — <context>
          continuation line — context can wrap over multiple lines.

    Permissive: bold/plain titles, em-dash/en-dash/hyphen separators,
    continuation lines indented under each item.
    """
    if not handoff_body:
        return []

    heading_match = DEFERRED_HEADING_RE.search(handoff_body)
    if heading_match is None:
        return []

    # Find where the section ends — next `##` heading or EOF.
    section_start = heading_match.end()
    after = handoff_body[section_start:]
    next_heading_match = NEXT_HEADING_RE.search(after)
    section_body = (
        after[: next_heading_match.start()] if next_heading_match else after
    )

    items: list[DeferredItem] = []
    current_title: str | None = None
    current_context_parts: list[str] = []

    def _flush() -> None:
        if current_title is not None:
            text = " ".join(p.strip() for p in current_context_parts).strip()
            items.append(DeferredItem(title=current_title.strip(), context=text))

    for line in section_body.splitlines():
        head_match = ITEM_HEAD_RE.match(line)
        if head_match:
            _flush()
            current_title = (
                head_match.group("bold_title") or head_match.group("plain_title")
            )
            current_context_parts = [head_match.group("context")]
            continue

        if current_title is None:
            # Lines before the first list item (blank, prose) — skip.
            continue

        cont_match = CONTINUATION_RE.match(line)
        if cont_match:
            current_context_parts.append(cont_match.group("text"))
            continue

        if NEW_ITEM_OR_BLANK_RE.match(line):
            # Blank line ends continuation but keeps the item open until the
            # next item-head or end-of-section. We tolerate one blank line
            # between context paragraphs; multiple consecutive blanks close
            # the item.
            if current_context_parts and current_context_parts[-1] != "":
                current_context_parts.append("")
            continue

        # Anything else — bail on the current item; treat as section noise.

    _flush()
    return items


def parse_handoff_file(path: str | Path) -> list[DeferredItem]:
    """Read a handoff file from disk and parse its deferred section."""
    return parse_deferred_section(Path(path).read_text(encoding="utf-8"))
