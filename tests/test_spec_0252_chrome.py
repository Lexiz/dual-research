"""Spec 0252 — source-pattern tests for the universal chrome.

Positive: `AllRunsChrome` carries a `route` prop and `app.jsx` renders it
for non-list routes. Antipodal: the old 44 px `.md-appbar` chrome and its
right-cluster children (`ChromeBar` / `RightCluster` / `ChromeTab` /
`ConnectionPill` / `AppVersionChip`) are gone from `app.jsx`.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import assert_jsx_contains, assert_jsx_lacks, read_repo_text

_APP = ("src", "dual_research", "ui", "static", "app.jsx")
_RUN_LIST = ("src", "dual_research", "ui", "static", "run-list.jsx")


def test_allrunschrome_is_route_generic() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_contains(
        jsx, r"function AllRunsChrome\(\{[^}]*\broute\b",
        msg="spec 0252: AllRunsChrome must accept a `route` prop",
    )


def test_app_renders_universal_chrome_for_non_list_routes() -> None:
    jsx = read_repo_text(*_APP)
    assert_jsx_contains(
        jsx, r"<AllRunsChrome route=\{route\.view\}",
        msg="spec 0252: app.jsx must mount AllRunsChrome for non-list routes",
    )
    # #main reserves the 60 px universal-chrome height (was 44 px).
    assert_jsx_contains(
        jsx, r"calc\(100vh - 60px\)",
        msg="spec 0252: non-list #main height must account for the 60 px chrome",
    )


def test_old_chrome_components_are_gone() -> None:
    jsx = read_repo_text(*_APP)
    for decl in (
        r"function ChromeBar\(",
        r"function RightCluster\(",
        r"function ChromeTab\(",
        r"function ConnectionPill\(",
        r"function AppVersionChip\(",
    ):
        assert_jsx_lacks(
            jsx, decl,
            msg=f"spec 0252: dead chrome component {decl!r} must be deleted from app.jsx",
        )
    # The 44 px app bar JSX literal is gone too.
    assert_jsx_lacks(
        jsx, r'<header className="md-appbar">',
        msg="spec 0252: the old .md-appbar chrome must be gone",
    )
