"""Spec 0246.1 — theme-persistence key reconciliation (refactoring).

Locks the localStorage theme key on the canonical hyphen form `dr-theme`
(matching spec 0246 §2.9 / Scenario 3) plus the one-time read-migration that
sweeps the legacy `dr.theme` value. Source-pattern tests per the UI test
doctrine (design-system/SPEC.md §13, spec 0206).
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

APP_JSX = read_repo_text("src", "dual_research", "ui", "static", "app.jsx")


def test_canonical_theme_key_present():
    # Positive: the canonical hyphen key is now in use.
    assert_jsx_contains(
        APP_JSX,
        r"THEME_KEY\s*=\s*'dr-theme'",
        msg="app.jsx must define THEME_KEY = 'dr-theme' as the canonical theme-persistence key",
    )


def test_legacy_key_read_migration_present():
    # Migration positive: legacy read-fallback + one-time sweep both present,
    # so a future edit can't drop the migration and strand saved preferences.
    assert_jsx_contains(
        APP_JSX,
        r"getItem\('dr\.theme'\)",
        msg="app.jsx must keep a getItem('dr.theme') fallback read for the one-time migration",
    )
    assert_jsx_contains(
        APP_JSX,
        r"removeItem\('dr\.theme'\)",
        msg="app.jsx must sweep the legacy key via removeItem('dr.theme') after first render",
    )


def test_legacy_key_no_longer_written():
    # Antipodal absence: the legacy key is never written again. The only
    # `dr.theme` references left are the read-migration fallback and the sweep.
    assert_jsx_lacks(
        APP_JSX,
        r"setItem\('dr\.theme'",
        msg="app.jsx must not write the legacy 'dr.theme' key — persistence is on 'dr-theme'",
    )
