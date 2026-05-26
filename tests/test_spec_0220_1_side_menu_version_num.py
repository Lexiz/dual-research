"""Spec 0220.1 — Changelog side-menu version-num column width fix.

Source-pattern tests (spec 0206 doctrine) that lock in the post-fix CSS
shape for ``.hiw-overlay__menu-list .menu-section-num`` in both the
live-app and design-system copies, plus antipodal-absence assertions
that the pre-fix ``width: 18px`` rule cannot return.

Pre-fix the rule lived only in the live-app file with ``width: 18px``,
which fit the legacy hand-curated 3-character versions (``0.5``,
``1.0``) but not the 6-character ``1.45.0`` shape that dominates the
auto-generated list shipped by spec 0220. The post-fix rule uses
``min-width: 48px`` (graceful overflow) plus a right margin, and now
also lands in ``design-system/assets/styles/composed-components.css``
per the CLAUDE.md two-file CSS sync rule.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

_LIVE_CSS = ("src", "dual_research", "ui", "static", "components.css")
_DS_CSS = ("design-system", "assets", "styles", "composed-components.css")


def test_menu_section_num_uses_min_width_in_live_css() -> None:
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_contains(
        css,
        r"\.hiw-overlay__menu-list\s+\.menu-section-num\s*\{[^}]*min-width:\s*48px",
        msg=(
            "The live-app `.hiw-overlay__menu-list .menu-section-num` rule "
            "must use `min-width: 48px` (spec 0220.1 §3). The legacy "
            "`width: 18px` overlapped the trailing `.0` of 6-character "
            "versions like `1.45.0` with the adjacent summary text."
        ),
    )
    assert_jsx_lacks(
        css,
        r"\.hiw-overlay__menu-list\s+\.menu-section-num\s*\{[^}]*\bwidth:\s*18px\b",
        msg=(
            "Pre-fix `.hiw-overlay__menu-list .menu-section-num { width: "
            "18px }` reintroduces the spec 0220.1 overlap regression — "
            "the side-menu version chip would collide with the summary "
            "text again on any release past v1.4.x."
        ),
    )


def test_menu_section_num_landed_in_design_system_css() -> None:
    css = read_repo_text(*_DS_CSS)
    assert_jsx_contains(
        css,
        r"\.hiw-overlay__menu-list\s+\.menu-section-num\s*\{[^}]*min-width:\s*48px",
        msg=(
            "The DS-side `.hiw-overlay__menu-list .menu-section-num` rule "
            "must mirror the live-app post-fix shape (CLAUDE.md two-file "
            "CSS sync rule + spec 0220.1 §3). Pre-fix the DS file had no "
            "`.menu-section-num` rule at all — this commit closes that "
            "DS-sync gap."
        ),
    )
    assert_jsx_lacks(
        css,
        r"\.hiw-overlay__menu-list\s+\.menu-section-num\s*\{[^}]*\bwidth:\s*18px\b",
        msg=(
            "DS-side `.hiw-overlay__menu-list .menu-section-num { width: "
            "18px }` would re-introduce the spec 0220.1 overlap regression "
            "on the canonical surface."
        ),
    )
