"""Spec 0117 — sync test for the Python ↔ JS artifact registries.

The Python registry in ``src/dual_research/contract/artifacts.py`` is
the source of truth. The JSX mirror in
``src/dual_research/ui/static/artifacts.jsx`` is consumed by the UI for
display-name resolution at render time.

This test parses both and asserts they are identical (same canonical
IDs in the same order, same display templates). If either drifts, CI
fails.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.contract.artifacts import REGISTRY

# ─── JS registry parsing ─────────────────────────────────────────────


# Matches a row like:
#   ['system.preamble',                       'Methodology preamble'],
# Allows single- or double-quoted entries (the JS file uses single
# quotes for entries without apostrophes and double quotes for entries
# like "Claude's research plan"); both quote styles must round-trip.
_ROW_RE = re.compile(
    r"""
    ^\s*\[
    \s*(?P<id_q>['"])(?P<id>.*?)(?P=id_q)\s*,
    \s*(?P<disp_q>['"])(?P<disp>.*?)(?P=disp_q)\s*
    \]\s*,?\s*$
    """,
    re.VERBOSE,
)


def _parse_js_registry(text: str) -> list[tuple[str, str]]:
    in_registry = False
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not in_registry:
            if "const REGISTRY = [" in line:
                in_registry = True
            continue
        stripped = line.strip()
        if stripped.startswith("];"):
            break
        m = _ROW_RE.match(line)
        if not m:
            continue
        rows.append((m.group("id"), m.group("disp")))
    return rows


def test_python_and_js_registries_match():
    js_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "dual_research"
        / "ui"
        / "static"
        / "artifacts.jsx"
    )
    assert js_path.is_file(), f"JS registry not found at {js_path}"

    js_rows = _parse_js_registry(js_path.read_text(encoding="utf-8"))
    py_rows = [(defn.id_template, defn.display_template) for defn in REGISTRY]

    assert js_rows, "Failed to parse any rows from artifacts.jsx"
    assert js_rows == py_rows, (
        "Python REGISTRY and JS REGISTRY are out of sync.\n"
        f"  Python row count: {len(py_rows)}\n"
        f"  JS row count:     {len(js_rows)}\n"
        f"  First difference: {next(((p, j) for p, j in zip(py_rows, js_rows) if p != j), None)}"
    )
