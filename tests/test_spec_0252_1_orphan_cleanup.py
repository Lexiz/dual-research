"""Spec 0252.1 — orphaned chrome JSX declaration cleanup (source-pattern, spec 0206).

Spec 0252's universal-chrome cutover deleted ``RightCluster`` — the only caller
of ``DesignLanguageButton`` — and ``ActiveRunChip`` was already dead before that.
This test locks the post-deletion anatomy: neither dead function declaration
appears in ``app.jsx`` (antipodal-absence), while the live ``/language``-route
entry point (the avatar menu "Design language" item in ``run-list.jsx``) is
unaffected (positive assertion confirming no rendered behavior changed).
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

APP_JSX = ("src", "dual_research", "ui", "static", "app.jsx")
RUN_LIST_JSX = ("src", "dual_research", "ui", "static", "run-list.jsx")


def test_active_run_chip_declaration_deleted():
    """``ActiveRunChip`` declaration is gone from app.jsx (antipodal-absence)."""
    jsx = read_repo_text(*APP_JSX)
    assert_jsx_lacks(
        jsx,
        r"function ActiveRunChip\(",
        msg="Spec 0252.1: orphaned ActiveRunChip declaration must be deleted from app.jsx.",
    )


def test_design_language_button_declaration_deleted():
    """``DesignLanguageButton`` declaration is gone from app.jsx (antipodal-absence)."""
    jsx = read_repo_text(*APP_JSX)
    assert_jsx_lacks(
        jsx,
        r"function DesignLanguageButton\(",
        msg="Spec 0252.1: orphaned DesignLanguageButton declaration must be deleted from app.jsx.",
    )


def test_language_route_entry_point_preserved():
    """The avatar-menu 'Design language' item still navigates to the language route.

    Positive assertion: deleting the dead ``DesignLanguageButton`` lost nothing
    functional because the live entry point is the avatar menu MenuItem, not the
    orphaned chrome button.
    """
    jsx = read_repo_text(*RUN_LIST_JSX)
    assert_jsx_contains(
        jsx,
        r"navigate\('language'\)",
        msg="Spec 0252.1: the avatar-menu 'Design language' navigate('language') entry point must remain live.",
    )
    assert_jsx_contains(
        jsx,
        r'label="Design language"',
        msg="Spec 0252.1: the avatar-menu 'Design language' MenuItem label must remain live.",
    )
