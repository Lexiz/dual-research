"""Tests for scripts.spec_lifecycle.pick_next_number.

Spec 0199 — decimal sub-numbering, `current_queue` returns spec-id strings
instead of `queue_position` ints, `next_queue_position` is gone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.spec_lifecycle.pick_next_number import (
    current_queue,
    format_spec_id,
    next_decimal_child,
    next_dev_number,
    next_draft_id,
    parse_spec_id,
)


def test_next_dev_number_empty_dir(tmp_path: Path) -> None:
    assert next_dev_number(tmp_path) == "0001"


def test_next_dev_number_skips_non_specs(tmp_path: Path) -> None:
    (tmp_path / "0001-foo.md").write_text("---\nkind: dev\n---\nbody\n")
    (tmp_path / "TEMPLATE.md").write_text("# template\n")
    (tmp_path / "0099-bar.md").write_text("---\nkind: dev\n---\nbody\n")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "draft-001-x.md").write_text("# x\n")
    assert next_dev_number(tmp_path) == "0100"


def test_next_dev_number_ignores_decimal_children(tmp_path: Path) -> None:
    """Spec 0199 §2.1 — decimal children do NOT advance the integer counter.

    Specs 0170, 0170.1, 0171 → next-integer is 0172, not 0171.1.
    """
    (tmp_path / "0170-a.md").write_text("---\nkind: dev\n---\n")
    (tmp_path / "0170.1-b.md").write_text("---\nkind: dev\n---\n")
    (tmp_path / "0171-c.md").write_text("---\nkind: dev\n---\n")
    assert next_dev_number(tmp_path) == "0172"


def test_next_draft_id(tmp_path: Path) -> None:
    drafts = tmp_path / "drafts"
    assert next_draft_id(drafts) == "001"
    drafts.mkdir(exist_ok=True)
    (drafts / "draft-005-x.md").write_text("---\nkind: draft\n---\n")
    assert next_draft_id(drafts) == "006"


def test_parse_spec_id_integer() -> None:
    assert parse_spec_id("0170") == (170, 0)
    assert parse_spec_id("0170-slug") == (170, 0)
    assert parse_spec_id("0170-slug.md") == (170, 0)


def test_parse_spec_id_decimal() -> None:
    assert parse_spec_id("0170.1") == (170, 1)
    assert parse_spec_id("0170.2-slug") == (170, 2)
    assert parse_spec_id("0170.10-slug.md") == (170, 10)


def test_parse_spec_id_two_level_decimal_rejected() -> None:
    with pytest.raises(ValueError, match="two-level"):
        parse_spec_id("0170.1.1")


def test_parse_spec_id_malformed() -> None:
    with pytest.raises(ValueError):
        parse_spec_id("")
    with pytest.raises(ValueError):
        parse_spec_id("abc")
    with pytest.raises(ValueError):
        parse_spec_id("170")  # not 4-digit


def test_format_spec_id_integer() -> None:
    assert format_spec_id(170) == "0170"
    assert format_spec_id(170, 0) == "0170"
    assert format_spec_id(1) == "0001"


def test_format_spec_id_decimal() -> None:
    assert format_spec_id(170, 1) == "0170.1"
    assert format_spec_id(170, 10) == "0170.10"


def test_format_spec_id_rejects_negative() -> None:
    with pytest.raises(ValueError):
        format_spec_id(-1)
    with pytest.raises(ValueError):
        format_spec_id(1, -1)


def test_next_decimal_child_first(tmp_path: Path) -> None:
    (tmp_path / "0170-a.md").write_text("---\nkind: dev\n---\n")
    assert next_decimal_child(tmp_path, "0170") == "0170.1"


def test_next_decimal_child_increments(tmp_path: Path) -> None:
    (tmp_path / "0170-a.md").write_text("---\nkind: dev\n---\n")
    (tmp_path / "0170.1-b.md").write_text("---\nkind: dev\n---\n")
    (tmp_path / "0170.3-d.md").write_text("---\nkind: dev\n---\n")
    # max + 1, not gap-fill — preserves chronology.
    assert next_decimal_child(tmp_path, "0170") == "0170.4"


def test_next_decimal_child_rejects_decimal_parent(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="decimal"):
        next_decimal_child(tmp_path, "0170.1")


def test_current_queue_orders_by_spec_id(tmp_path: Path) -> None:
    """Spec 0199 §2.1 — sort by `(parent, child)` tuple, not queue_position."""
    (tmp_path / "0103-c.md").write_text(
        '---\nkind: dev\nspec: "0103"\nstatus: queued\n---\n'
    )
    (tmp_path / "0101-a.md").write_text(
        '---\nkind: dev\nspec: "0101"\nstatus: queued\n---\n'
    )
    (tmp_path / "0102-b.md").write_text(
        '---\nkind: dev\nspec: "0102"\nstatus: deployed\n---\n'
    )
    queue = current_queue(tmp_path)
    assert [spec_id for spec_id, _ in queue] == ["0101", "0103"]


def test_current_queue_interleaves_decimals(tmp_path: Path) -> None:
    """Spec 0199 §3.2 Scenario 5 — `0170, 0170.1, 0171` ordering."""
    (tmp_path / "0171-c.md").write_text(
        '---\nkind: dev\nspec: "0171"\nstatus: queued\n---\n'
    )
    (tmp_path / "0170.1-b.md").write_text(
        '---\nkind: dev\nspec: "0170.1"\nstatus: queued\n---\n'
    )
    (tmp_path / "0170-a.md").write_text(
        '---\nkind: dev\nspec: "0170"\nstatus: queued\n---\n'
    )
    queue = current_queue(tmp_path)
    assert [spec_id for spec_id, _ in queue] == ["0170", "0170.1", "0171"]


def test_current_queue_ignores_queue_position(tmp_path: Path) -> None:
    """A lingering queue_position field must NOT influence ordering anymore."""
    (tmp_path / "0102-b.md").write_text(
        '---\nkind: dev\nspec: "0102"\nstatus: queued\nqueue_position: 1\n---\n'
    )
    (tmp_path / "0101-a.md").write_text(
        '---\nkind: dev\nspec: "0101"\nstatus: queued\nqueue_position: 99\n---\n'
    )
    queue = current_queue(tmp_path)
    # Sort by spec ID, not queue_position — 0101 leads 0102 even though its
    # queue_position is higher.
    assert [spec_id for spec_id, _ in queue] == ["0101", "0102"]
