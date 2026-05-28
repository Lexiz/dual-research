"""Spec 0252 — source-pattern tests for the How-it-works / Changelog nav.

Positive: the nav labels are wrapped in `.menu-section-lbl`, and the
anchor is a two-column flex row in both CSS files. Antipodal: the
`(e.summary||'').slice(0, 30)` hard-slice is gone from how-it-works.jsx.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import assert_jsx_contains, assert_jsx_lacks, read_repo_text

_HIW = ("src", "dual_research", "ui", "static", "how-it-works.jsx")
_LIVE_CSS = ("src", "dual_research", "ui", "static", "components.css")
_DS_CSS = ("design-system", "assets", "styles", "composed-components.css")


def test_nav_labels_wrapped_in_label_span() -> None:
    jsx = read_repo_text(*_HIW)
    assert_jsx_contains(
        jsx, r'<span className="menu-section-lbl">',
        msg="spec 0252: nav labels must be wrapped in .menu-section-lbl",
    )


def test_changelog_30char_slice_is_gone() -> None:
    jsx = read_repo_text(*_HIW)
    assert_jsx_lacks(
        jsx, r"\.slice\(0, 30\)",
        msg="spec 0252: the 30-char changelog summary slice must be removed (CSS clamps length)",
    )


def test_both_css_files_define_flex_anchor_and_label() -> None:
    for parts in (_LIVE_CSS, _DS_CSS):
        css = read_repo_text(*parts)
        assert_jsx_contains(
            css, r"\.menu-section-lbl",
            msg=f"spec 0252: .menu-section-lbl rule missing in {parts[-1]}",
        )
        # The controlling `li a` rule is a flex row.
        assert_jsx_contains(
            css, r"\.hiw-overlay__menu-list li a",
            msg=f"spec 0252: the controlling `li a` rule must exist in {parts[-1]}",
        )
        assert_jsx_contains(
            css, r"display:\s*flex;\s*align-items:\s*flex-start",
            msg=f"spec 0252: the nav anchor must be a flex-start row in {parts[-1]}",
        )
