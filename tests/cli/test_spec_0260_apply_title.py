"""Spec 0260 — `--name` doubles as the run display title by overriding the
first H1 of ``brief.md`` at the single write chokepoint (cli.py:400).

The display title is derived from the first ``# `` H1 of ``brief.md`` in both
UIs, so overriding that H1 with ``--name`` propagates to local and hosted
surfaces alike. These tests exercise ``_apply_title`` — the transform applied
verbatim at the ``brief.md`` write point — including the round-trip through a
written file to assert the on-disk first H1 the renderers read.
"""
from __future__ import annotations

from pathlib import Path

from dual_research.cli import _apply_title


def _first_h1(text: str) -> str:
    for line in text.split("\n"):
        if line.startswith("# "):
            return line
    return ""


def test_named_run_first_h1_becomes_name_on_disk(tmp_path: Path) -> None:
    """CLI-level: after the write transform, brief.md's first H1 equals --name
    (covers the "H1 present → replace" branch against a `# Research brief`)."""
    content = "# Research brief\n\nWhich backend language should we use?\n"
    brief_path = tmp_path / "brief.md"
    brief_path.write_text(_apply_title(content, "GPU inference cost"), encoding="utf-8")

    assert _first_h1(brief_path.read_text(encoding="utf-8")) == "# GPU inference cost"


def test_unnamed_run_first_h1_unchanged_on_disk(tmp_path: Path) -> None:
    """CLI-level: when --name is absent, brief.md's first H1 is left unchanged
    (the transform returns content verbatim)."""
    content = "# Research brief\n\nWhich backend language should we use?\n"
    brief_path = tmp_path / "brief.md"
    brief_path.write_text(_apply_title(content, None), encoding="utf-8")

    written = brief_path.read_text(encoding="utf-8")
    assert _first_h1(written) == "# Research brief"
    assert written == content  # bit-for-bit pass-through


def test_no_h1_gets_name_prepended() -> None:
    """Unit: a brief with no H1 gets `# {name}` prepended (no-H1 fallback)."""
    content = "Which backend language should we use?\n"
    result = _apply_title(content, "GPU inference cost")

    assert result.startswith("# GPU inference cost\n\n")
    assert content in result


def test_only_first_h1_replaced() -> None:
    """Unit: only the first H1 is replaced; a later `# ` heading is untouched."""
    content = "# Research brief\n\n## Background\n\n# Appendix\n"
    result = _apply_title(content, "GPU inference cost")

    assert result == "# GPU inference cost\n\n## Background\n\n# Appendix\n"


def test_empty_name_is_passthrough() -> None:
    """An empty-string --name is falsy and must pass through verbatim."""
    content = "# Research brief\n\nbody\n"
    assert _apply_title(content, "") == content
