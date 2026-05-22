"""Tests for scripts.spec_lifecycle.deferrals — spec 0158.

The ``## Deferred during implementation`` section is the input to the
``/dev-next`` step 25.5 deferred-spec subagent. The parser must:

- Return ``[]`` when the section is absent.
- Return ``[]`` when the section is present but empty.
- Return one item per ``-`` list entry, with title and context extracted.
- Handle bold and plain titles, em-dash / en-dash / hyphen separators.
- Handle multi-line continuation context indented under each item.
- Stop parsing at the next ``##`` heading.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.deferrals import (
    DeferredItem,
    parse_deferred_section,
    parse_handoff_file,
)


def test_section_absent_returns_empty() -> None:
    body = """# Handover — Spec 9999

## Summary

All good.

## File map

```
some/file.py
```
"""
    assert parse_deferred_section(body) == []


def test_section_present_but_empty_returns_empty() -> None:
    body = """# Handover

## Deferred during implementation

## File map
"""
    assert parse_deferred_section(body) == []


def test_two_items_bold_titles_em_dash() -> None:
    body = """# Handover — Spec 9999

## Deferred during implementation

- **Cache invalidation race** — saw the race on parallel writes at
  scripts/spec_lifecycle/append_event.py:33; couldn't reproduce
  deterministically before deploy deadline.
- **Validator cycle detection** — `depends_on` cycles aren't caught at
  spec-queue time; flagged in spec 0157 risks.

## File map

```
some/file.py
```
"""
    items = parse_deferred_section(body)
    assert len(items) == 2
    assert items[0].title == "Cache invalidation race"
    assert "append_event.py:33" in items[0].context
    assert items[1].title == "Validator cycle detection"
    assert "depends_on" in items[1].context


def test_single_item_plain_title() -> None:
    body = """## Deferred during implementation

- Backfill richer event histories on older specs - documented in spec 0153 §6.

## Next steps
"""
    items = parse_deferred_section(body)
    assert len(items) == 1
    assert items[0].title.startswith("Backfill")
    assert "spec 0153" in items[0].context


def test_section_stops_at_next_heading() -> None:
    body = """## Deferred during implementation

- **Item A** — context for A.

## Some other section

- **Item B** — this should NOT be captured as a deferral.
"""
    items = parse_deferred_section(body)
    assert [i.title for i in items] == ["Item A"]


def test_continuation_lines_join_into_context() -> None:
    body = """## Deferred during implementation

- **Long item** — first line of context;
  second line that continues the same item;
  third line still continuing.
- **Short item** — single line.
"""
    items = parse_deferred_section(body)
    assert len(items) == 2
    assert items[0].title == "Long item"
    # Context joined across continuation lines.
    assert "first line" in items[0].context
    assert "second line" in items[0].context
    assert "third line" in items[0].context
    assert items[1].title == "Short item"


def test_parse_handoff_file_round_trips(tmp_path: Path) -> None:
    """End-to-end: write a real handoff fixture, parse it from disk."""
    handoff = tmp_path / "2026-05-22-spec-9999-fixture.md"
    handoff.write_text(
        "---\nspec: \"9999\"\ndate: 2026-05-22\nversion: 1.0.0\npr: \"x\"\n---\n\n"
        "# Handover — Spec 9999\n\n"
        "## What landed\n\nA thing.\n\n"
        "## Deferred during implementation\n\n"
        "- **First deferral** — couldn't get to it; see file.py:10.\n"
        "- **Second deferral** — out of time.\n\n"
        "## File map\n\nDone.\n"
    )
    items = parse_handoff_file(handoff)
    assert len(items) == 2
    assert items[0] == DeferredItem(
        title="First deferral",
        context="couldn't get to it; see file.py:10.",
    )
    assert items[1] == DeferredItem(
        title="Second deferral",
        context="out of time.",
    )
