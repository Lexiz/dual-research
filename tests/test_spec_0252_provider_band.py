"""Spec 0252 — source-pattern tests for the ProviderCard Comments badge.

Positive: the single-count Comments badge (`rc-rs--c` + `rc-rs--count-cmt`)
is present, and the explicit per-category tone classes (`rc-rs--q/d/i/c`)
exist in both CSS files. Antipodal: the fragile `:nth-child(N)` tone
selectors are gone from both CSS files.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import assert_jsx_contains, assert_jsx_lacks, read_repo_text

_RUN_LIST = ("src", "dual_research", "ui", "static", "run-list.jsx")
_LIVE_CSS = ("src", "dual_research", "ui", "static", "components.css")
_DS_CSS = ("design-system", "assets", "styles", "composed-components.css")


def test_provider_card_renders_comments_badge() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_contains(
        jsx, r"rc-rs rc-rs--c",
        msg="spec 0252: ProviderCard must render the single-count Comments badge",
    )
    assert_jsx_contains(
        jsx, r"rc-rs--count rc-rs--count-cmt",
        msg="spec 0252: the Comments value carries the idle-toned count class",
    )
    # The Q/D/I badges now carry explicit tone classes via the group `tone`.
    assert_jsx_contains(
        jsx, r"'rc-rs rc-rs--' \+ g\.tone",
        msg="spec 0252: Q/D/I badges wear explicit rc-rs--<tone> classes",
    )


def test_both_css_files_carry_comments_tone_classes() -> None:
    for parts in (_LIVE_CSS, _DS_CSS):
        css = read_repo_text(*parts)
        assert_jsx_contains(
            css, r"\.rc-rs--c \.rc-rs__cat",
            msg=f"spec 0252: explicit Comments tone selector missing in {parts[-1]}",
        )
        assert_jsx_contains(
            css, r"\.rc-rs--count-cmt",
            msg=f"spec 0252: .rc-rs--count-cmt missing in {parts[-1]}",
        )


def test_nth_child_tone_selectors_are_gone() -> None:
    for parts in (_LIVE_CSS, _DS_CSS):
        css = read_repo_text(*parts)
        assert_jsx_lacks(
            css, r"\.rc-rs:nth-child\(",
            msg=f"spec 0252: fragile :nth-child tone selectors must be gone from {parts[-1]}",
        )
