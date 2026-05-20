"""Spec 0119 — sync test for the Python ↔ JS lifecycle-verb mapping.

The Python transition table in ``src/dual_research/contract/lifecycle.py``
is the source of truth for legal item-state transitions. The JS mirror
in ``src/dual_research/ui/static/lifecycle-verbs.js`` defines the short
verb that renders inside Chip labels on critique-card lifecycle rows.

This test asserts:

  1. Every agent-driven transition in ``TRANSITIONS`` (i.e. every
     (from, to) pair) has a verb in the JS table — otherwise the
     renderer would fall back to the raw target-state string.
  2. The JS table doesn't claim verbs for transitions Python doesn't
     allow (catch drift in the other direction).
  3. Every terminal state in ``TERMINAL_STATES`` is also marked
     terminal in the JS ``TERMINAL`` set.

The orchestrator-only ``* → capped`` transition is special-cased: the
JS verb is the literal ``'capped'`` regardless of source state.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.contract.lifecycle import TERMINAL_STATES, TRANSITIONS, State


# ─── JS verb-table parsing ───────────────────────────────────────────


# Matches a row like:
#     'open->addressed':         'addressed',
_VERB_ROW_RE = re.compile(
    r"""
    ^\s*
    '(?P<key>[a-z_]+->[a-z_]+)'
    \s*:\s*
    '(?P<verb>[^']+)'
    \s*,?\s*$
    """,
    re.VERBOSE,
)


def _parse_js_verb_table(text: str) -> dict[str, str]:
    in_table = False
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if not in_table:
            if "const VERBS = {" in line:
                in_table = True
            continue
        if line.strip().startswith("};"):
            break
        m = _VERB_ROW_RE.match(line)
        if not m:
            continue
        rows[m.group("key")] = m.group("verb")
    return rows


# Matches the ``new Set([...])`` initialiser of the TERMINAL set.
_TERMINAL_SET_RE = re.compile(
    r"new\s+Set\(\s*\[([^\]]+)\]\s*\)",
)


def _parse_js_terminal_set(text: str) -> set[str]:
    # Restrict to the file region just after `const TERMINAL`.
    idx = text.find("const TERMINAL")
    assert idx != -1, "Missing TERMINAL declaration in lifecycle-verbs.js"
    snippet = text[idx : idx + 400]
    m = _TERMINAL_SET_RE.search(snippet)
    assert m, "Failed to parse TERMINAL Set initialiser"
    items = m.group(1)
    return {
        token.strip().strip("'").strip('"')
        for token in items.split(",")
        if token.strip()
    }


# ─── Tests ───────────────────────────────────────────────────────────


def _js_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "src"
        / "dual_research"
        / "ui"
        / "static"
        / "lifecycle-verbs.js"
    )


def test_every_python_transition_has_a_js_verb() -> None:
    js_verbs = _parse_js_verb_table(_js_path().read_text(encoding="utf-8"))

    expected_keys = {
        f"{from_state.value}->{to_state.value}"
        for from_state, targets in TRANSITIONS.items()
        for to_state in targets
    }

    missing = expected_keys - js_verbs.keys()
    assert not missing, (
        "lifecycle-verbs.js is missing verbs for these Python-allowed "
        f"transitions: {sorted(missing)}"
    )


def test_js_table_has_no_phantom_transitions() -> None:
    js_verbs = _parse_js_verb_table(_js_path().read_text(encoding="utf-8"))

    legal_keys = {
        f"{from_state.value}->{to_state.value}"
        for from_state, targets in TRANSITIONS.items()
        for to_state in targets
    }

    phantom = js_verbs.keys() - legal_keys
    assert not phantom, (
        "lifecycle-verbs.js declares verbs for transitions Python does "
        f"NOT allow: {sorted(phantom)}"
    )


def test_terminal_set_matches() -> None:
    js_terminal = _parse_js_terminal_set(_js_path().read_text(encoding="utf-8"))
    py_terminal = {state.value for state in TERMINAL_STATES}
    assert js_terminal == py_terminal, (
        f"JS TERMINAL set {sorted(js_terminal)} disagrees with "
        f"Python TERMINAL_STATES {sorted(py_terminal)}"
    )


def test_capped_verb_is_canonical() -> None:
    """The orchestrator-only ``* → capped`` transition should yield the
    literal ``'capped'`` verb. The Python table doesn't list capped as
    a target (it lives outside the agent-driven table) — so we instead
    assert the JS function's behaviour by parsing the source.
    """
    text = _js_path().read_text(encoding="utf-8")
    # The behaviour we depend on is the early-return branch:
    #     if (toState === 'capped') return 'capped';
    assert "toState === 'capped'" in text, (
        "lifecycle-verbs.js should special-case toState==='capped' to "
        "return the literal 'capped' verb"
    )
    assert State.CAPPED.value == "capped"
