"""Spec 0180 — Consumption card V2 anatomy invariants.

The V2 anatomy splits the single combined `Total tokens` bar into two
stacked bars (total-input + total-output) and adds a parallel output
totals block. Cache-savings moves from the input totals to the output
totals. This test locks the structural changes so a defensive add-back
of the combined bar or the mislocated cache line gets caught.
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def _read():
    return JSX.read_text()


def test_no_combined_total_tokens_bar():
    text = _read()
    # The is-total combined bar from spec 0118 was the V1 anatomy.
    # V2 replaces it with --total-input + --total-output modifiers.
    assert "ccx-bar-row is-total" not in text and "is-total" not in text, (
        "ccx-bar-row.is-total reintroduces the V1 combined Total tokens bar — "
        "spec 0180 §3.2 replaced it with two stacked bars (--total-input + "
        "--total-output). If the combined bar is needed for a different reason, "
        "modify this test and name the spec that justifies it."
    )


def test_total_input_bar_present():
    text = _read()
    assert "ccx-bar-row--total-input" in text, (
        "Spec 0180 §3.2 requires the total-input bar (ccx-bar-row--total-input "
        "modifier) above the expanded gate so it's visible in collapsed state."
    )


def test_total_output_bar_present():
    text = _read()
    assert "ccx-bar-row--total-output" in text, (
        "Spec 0180 §3.2 requires the total-output bar (ccx-bar-row--total-output "
        "modifier) above the expanded gate so it's visible in collapsed state."
    )


def test_output_totals_block_present():
    text = _read()
    assert "ccx-totals--output" in text, (
        "Spec 0180 §3.6 requires the new output totals block "
        "(ccx-totals--output modifier). Without it, the V2 anatomy is "
        "asymmetric — input has totals, output doesn't."
    )


def test_cache_savings_in_output_totals_not_input():
    text = _read()
    # The cache-savings line must land inside the ccx-totals--output block,
    # not the input-only ccx-totals block. We assert: the substring
    # "cache savings" appears AFTER the first "ccx-totals--output" anchor.
    out_anchor = text.find("ccx-totals--output")
    cache_anchor = text.find("cache savings")
    assert out_anchor > 0, "ccx-totals--output anchor missing"
    assert cache_anchor > 0, "cache savings line missing entirely"
    assert cache_anchor > out_anchor, (
        "cache savings line must render inside ccx-totals--output (output totals "
        "block), not the input totals block. Spec 0180 §3.5/§3.6 moves it."
    )


def test_no_inline_grid_on_ccx_bar_row():
    text = _read()
    # The repeated inline grid styling at lines 2999-3003 and 3055-3060 is
    # forbidden by spec 0180 §3.7 — DS hygiene wants grid declarations
    # on the .ccx-bar-row class only.
    pattern = re.compile(
        r"<div\s+className=[\"`]ccx-bar-row[^\"`]*[\"`]\s+[^>]*style=\{\{[^}]*gridTemplateColumns",
        re.DOTALL,
    )
    matches = pattern.findall(text)
    assert not matches, (
        f"Found {len(matches)} ccx-bar-row JSX element(s) carrying an inline "
        f"gridTemplateColumns style — spec 0180 §3.7 forbids this. Move grid "
        f"declarations onto the .ccx-bar-row CSS class."
    )
