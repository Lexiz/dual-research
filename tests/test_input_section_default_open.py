"""Spec 0178 — InputSection rows must default open after outer group expands.

The two-level collapse pattern (outer section + inner per-piece) led to a
"clicked but got nothing" UX bug because system.* and prior_turns.* pieces
were default-collapsed at the inner level. This test locks in: the inner
CollapsibleSection inside InputSection has no per-key collapse heuristic.
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def test_no_is_default_collapsed_helper():
    text = JSX.read_text()
    assert "isDefaultCollapsed" not in text, (
        "isDefaultCollapsed reintroduces the two-click reveal regression "
        "(spec 0178). Inner per-piece CollapsibleSection rows must default "
        "open once the user has expanded the outer InputSectionGroup."
    )


def test_input_section_inner_default_open_unconditional():
    text = JSX.read_text()
    m = re.search(
        r"function\s+InputSection\b.*?<CollapsibleSection\s+([^>]*)>",
        text, re.DOTALL,
    )
    assert m is not None, (
        "InputSection / its inner CollapsibleSection not found — "
        "if the component was renamed or restructured, update this test."
    )
    props = m.group(1)
    assert re.search(r"defaultOpen=\{true\}", props), (
        f"InputSection inner CollapsibleSection must use defaultOpen={{true}}; "
        f"found: {props.strip()!r}. The inner collapse must not be gated by a "
        f"per-key heuristic — that produced the spec-0178 two-click bug."
    )
