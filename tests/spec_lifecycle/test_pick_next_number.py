"""Tests for scripts.spec_lifecycle.pick_next_number."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.pick_next_number import (
    next_dev_number,
    next_draft_id,
    next_queue_position,
    current_queue,
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


def test_next_draft_id(tmp_path: Path) -> None:
    drafts = tmp_path / "drafts"
    assert next_draft_id(drafts) == "001"
    drafts.mkdir(exist_ok=True)
    (drafts / "draft-005-x.md").write_text("---\nkind: draft\n---\n")
    assert next_draft_id(drafts) == "006"


def test_current_queue_orders_by_position(tmp_path: Path) -> None:
    (tmp_path / "0101-a.md").write_text(
        '---\nkind: dev\nspec: "0101"\nstatus: queued\nqueue_position: 3\n---\n'
    )
    (tmp_path / "0102-b.md").write_text(
        '---\nkind: dev\nspec: "0102"\nstatus: queued\nqueue_position: 1\n---\n'
    )
    (tmp_path / "0103-c.md").write_text(
        '---\nkind: dev\nspec: "0103"\nstatus: deployed\n---\n'
    )
    queue = current_queue(tmp_path)
    assert [pos for pos, _ in queue] == [1, 3]


def test_next_queue_position_empty(tmp_path: Path) -> None:
    assert next_queue_position(tmp_path) == 1


def test_next_queue_position_skips_deployed(tmp_path: Path) -> None:
    (tmp_path / "0101-a.md").write_text(
        '---\nkind: dev\nspec: "0101"\nstatus: queued\nqueue_position: 2\n---\n'
    )
    (tmp_path / "0102-b.md").write_text(
        '---\nkind: dev\nspec: "0102"\nstatus: deployed\n---\n'
    )
    assert next_queue_position(tmp_path) == 3
