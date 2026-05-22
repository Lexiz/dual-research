"""Regression test for spec 0157 — `depends_on` in dev-spec frontmatter.

The auto-decomposition flow writes inter-spec dependencies into the
``depends_on`` field. The field already exists (spec 0155 carries
``depends_on: ["0154"]``); this test locks in that the validator accepts it
unchanged so the new flow doesn't regress on the field's contract.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.validator import validate_dev_spec


def _write_spec(path: Path, *, depends_on: str = "[]") -> None:
    """Drop a minimal-shape, validator-passing dev spec at ``path``."""
    body = (
        "# Spec 9999 — fixture\n\n"
        "## 1. Context\n\n"
        "Body cites `scripts/spec_lifecycle/validator.py:68` for the validator\n"
        "entrypoint and `scripts/spec_lifecycle/pick_next_number.py:16` for the\n"
        "number picker. Plus a third reference to `scripts/spec_lifecycle/stages.py`\n"
        "for good measure.\n\n"
        "## 2. Proposed change\n\nDo the thing.\n\n"
        "## 3. UX / Behavior\n\nVisible behavior is the same.\n\n"
        "## 4. Data / Schema deltas\n\nNone.\n\n"
        "## 5. Out of scope\n\nUnrelated cleanup.\n\n"
        "## 6. Test plan\n\n"
        "- [ ] Test: behavior is preserved at `tests/spec_lifecycle/test_stages.py:1`.\n"
        "- [ ] Manual: render dashboard and confirm new spec appears in the queue table.\n\n"
        "## 7. Risks\n\nNone of consequence.\n"
    )
    path.write_text(
        "---\n"
        'kind: dev\n'
        'spec: "9999"\n'
        "slug: fixture\n"
        "title: Fixture spec\n"
        "type: new-feature\n"
        "label: new-feature\n"
        "version_bump: MINOR\n"
        "target_version: 9.9.9\n"
        "status: queued\n"
        "queue_position: 1\n"
        f"depends_on: {depends_on}\n"
        "complexity: S\n"
        "created: 2026-05-22\n"
        'queued_at: "2026-05-22T00:00:00Z"\n'
        "---\n\n" + body
    )


def test_validator_accepts_depends_on_chain(tmp_path: Path) -> None:
    """The decomposition flow writes chains like `depends_on: ["0154", "0156"]`.
    Validator must accept the field as-is."""
    path = tmp_path / "9999-fixture.md"
    _write_spec(path, depends_on='["0154", "0156"]')
    result = validate_dev_spec(path)
    assert result.ok, f"validator rejected depends_on chain: {result.errors}"


def test_validator_accepts_empty_depends_on(tmp_path: Path) -> None:
    """The single-spec case ships `depends_on: []`. Still valid."""
    path = tmp_path / "9999-fixture.md"
    _write_spec(path, depends_on="[]")
    result = validate_dev_spec(path)
    assert result.ok, f"validator rejected empty depends_on: {result.errors}"


def test_validator_accepts_single_dep(tmp_path: Path) -> None:
    """Most chains are length-1 (B depends on A). Validator accepts."""
    path = tmp_path / "9999-fixture.md"
    _write_spec(path, depends_on='["0154"]')
    result = validate_dev_spec(path)
    assert result.ok, f"validator rejected single-dep depends_on: {result.errors}"
