"""Spec 0223 — Phase 4 turn cards render all four category Δ chips.

Source-pattern tests per design-system/SPEC.md §13 (no DOM-rendering).

Pre-fix shape: `item.phase` was never set on timeline turn rows in
`live-data.jsx`; the `chipCategories` ternary at `run-detail.jsx:1199`
read it via `?? null` and fell into the two-category Q+D else branch
for every phase. Phase 0 + Phase 2 happened to need Q+D; Phase 4 was
silently broken.

Post-fix shape: `attachItemStats` in `live-data.jsx` sets
`item.phase = phase` alongside `item.statsPhase`, so the existing
four-category branch in `chipCategories` (which was already correct)
actually fires for Phase 4 turn rows.
"""

from __future__ import annotations

import re

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)


def test_run_detail_chip_categories_branches_to_four_for_phase_4() -> None:
    """Positive: the Phase 4 chipCategories branch lists all four categories."""
    jsx = read_repo_text(
        "src", "dual_research", "ui", "static", "run-detail.jsx"
    )
    assert_jsx_contains(
        jsx,
        re.compile(
            r"chipCategories\s*=\s*\([^)]*phase\w*\s*===\s*4[^)]*\)\s*"
            r"\?\s*\[\s*'questions'\s*,\s*'disagreements'\s*,\s*"
            r"'issues'\s*,\s*'comments'\s*\]",
            re.DOTALL,
        ),
        msg=(
            "Phase 4 chipCategories branch must list all four categories "
            "['questions','disagreements','issues','comments'] — spec 0223"
        ),
    )


def test_run_detail_two_chip_fallback_only_on_non_phase_4_else_branch() -> None:
    """Antipodal: no `phase === 4` ternary pairs with the two-category list.

    Locks against a future revert that drops I + C from Phase 4 turn
    cards. The two-category list must remain ONLY as the else branch.
    """
    jsx = read_repo_text(
        "src", "dual_research", "ui", "static", "run-detail.jsx"
    )
    assert_jsx_lacks(
        jsx,
        re.compile(
            r"chipCategories\s*=\s*\([^)]*phase\w*\s*===\s*4[^)]*\)\s*"
            r"\?\s*\[\s*'questions'\s*,\s*'disagreements'\s*\]\s*:",
            re.DOTALL,
        ),
        msg=(
            "Phase 4 branch must not collapse back to the two-category "
            "Q+D fallback — spec 0223"
        ),
    )


def test_run_detail_per_turn_chip_render_uses_raised_closed_as_add_sub() -> None:
    """Positive: the chipCategories map still drives the per-Chip add/sub.

    Anchors spec-0133 §5.9 slim-Δ presentation so a future "show only
    standing totals" regression flags here.
    """
    jsx = read_repo_text(
        "src", "dual_research", "ui", "static", "run-detail.jsx"
    )
    assert_jsx_contains(
        jsx,
        re.compile(
            r"chipCategories\.map\(\(cat\)\s*=>\s*\{",
            re.DOTALL,
        ),
        msg=(
            "chipCategories must still drive a per-Chip map at the render "
            "site (spec 0133 §5.9 slim-Δ presentation)"
        ),
    )
    assert_jsx_contains(
        jsx,
        re.compile(
            r"add=\{c\.raised\}.*?sub=\{c\.closed\}",
            re.DOTALL,
        ),
        msg=(
            "Per-Chip props must still carry add={c.raised} sub={c.closed} "
            "(slim-Δ anatomy)"
        ),
    )


def test_live_data_sets_item_phase_on_turn_rows() -> None:
    """Positive: attachItemStats sets `item.phase` on turn rows.

    The root-cause fix: without this, Phase 4 turn rows render with
    `item.phase === undefined` and the chipCategories ternary falls to
    the two-category else branch.
    """
    jsx = read_repo_text(
        "src", "dual_research", "ui", "static", "live-data.jsx"
    )
    assert_jsx_contains(
        jsx,
        re.compile(
            r"item\.phase\s*=\s*phase\s*;",
        ),
        msg=(
            "live-data.jsx must set `item.phase = phase` in attachItemStats "
            "so the chipCategories ternary fires its four-category branch "
            "for Phase 4 — spec 0223"
        ),
    )


def test_live_data_item_phase_assignment_inside_turn_branch() -> None:
    """Positive: the `item.phase = phase` assignment lives inside the
    turn/turn-live branch of attachItemStats, not in a divider/preflight
    branch where it would be wrong.
    """
    jsx = read_repo_text(
        "src", "dual_research", "ui", "static", "live-data.jsx"
    )
    # Locate the turn-branch block, then assert item.phase = phase
    # appears within ~30 lines of the kind check.
    turn_branch_match = re.search(
        r"if\s*\(item\.kind\s*===\s*'turn'\s*\|\|\s*"
        r"item\.kind\s*===\s*'turn-live'\)\s*\{",
        jsx,
    )
    assert turn_branch_match is not None, (
        "could not locate the turn/turn-live branch in attachItemStats"
    )
    start = turn_branch_match.end()
    # Read a generous window after the branch opens.
    window = jsx[start : start + 2000]
    assert re.search(r"item\.phase\s*=\s*phase\s*;", window), (
        "item.phase = phase must live inside the turn/turn-live branch "
        "of attachItemStats — spec 0223"
    )
