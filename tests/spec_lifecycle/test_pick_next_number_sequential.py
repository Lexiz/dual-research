"""Regression test for spec 0157 — sequential dev-number assignment.

The auto-decomposition flow in ``/spec-queue`` step 1d may call
``next_dev_number(specs_dir)`` N times in a single invocation, with each call
preceded by materializing the prior sub-spec on disk. This test locks in that
contract: numbers come back strictly sequential with no collisions when the
intermediate filesystem state is updated between calls.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.pick_next_number import next_dev_number


def _materialize_stub(specs_dir: Path, number: str) -> None:
    """Write a minimal-shape spec file so the next call sees it."""
    (specs_dir / f"{number}-stub.md").write_text(
        f'---\nkind: dev\nspec: "{number}"\nslug: stub\n---\nbody\n'
    )


def test_three_sequential_calls_are_strictly_increasing(tmp_path: Path) -> None:
    specs = tmp_path
    # Seed with one existing spec so we don't depend on the empty-dir default.
    _materialize_stub(specs, "0100")

    n1 = next_dev_number(specs)
    assert n1 == "0101"
    _materialize_stub(specs, n1)

    n2 = next_dev_number(specs)
    assert n2 == "0102"
    _materialize_stub(specs, n2)

    n3 = next_dev_number(specs)
    assert n3 == "0103"

    # Numbers are strictly increasing and have no duplicates.
    assert len({n1, n2, n3}) == 3
    assert [n1, n2, n3] == sorted([n1, n2, n3])


def test_sequential_calls_from_empty(tmp_path: Path) -> None:
    """Same contract when starting from an empty specs directory."""
    n1 = next_dev_number(tmp_path)
    assert n1 == "0001"
    _materialize_stub(tmp_path, n1)

    n2 = next_dev_number(tmp_path)
    assert n2 == "0002"
    _materialize_stub(tmp_path, n2)

    n3 = next_dev_number(tmp_path)
    assert n3 == "0003"
