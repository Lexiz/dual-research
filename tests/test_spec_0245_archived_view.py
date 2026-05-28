"""Spec 0245 — Archived-view toggle + archived-row treatment tests.

Source-pattern guards per spec 0206 §13. Locks the admin-only gating
of the Active/Archived toggle and the `.run-row--archived` class
application on rows whose `deletedAt` is non-null.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)


def _run_list_jsx() -> str:
    return read_repo_text("src", "dual_research", "ui", "static", "run-list.jsx")


def test_archived_view_toggle_renders_admin_only() -> None:
    jsx = _run_list_jsx()
    # Post-fix: the Active/Archived TabGroup mounts only under
    # `isAdmin && ...`; both Tab options are present inside it.
    assert_jsx_contains(
        jsx,
        r"isAdmin && \(\s*<div className=\"ar-chrome__tabs\" data-testid=\"archived-view-toggle\">",
        msg="spec 0245 §2.3 / 0246 §2.12.1 — Active/Archived toggle must mount only for admins (isAdmin && ...)",
    )
    # Spec 0246 §2.12.1 restyled the toggle as an `.ar-tab` segmented control
    # in the new chrome; the state setter is threaded as `onArchivedView`.
    assert_jsx_contains(
        jsx,
        r"onClick=\{\(\) => onArchivedView\(false\)\}[\s\S]*?>Active",
        msg="spec 0245 §2.3 / 0246 §2.12.1 — toggle must include an Active option that calls onArchivedView(false)",
    )
    assert_jsx_contains(
        jsx,
        r"onClick=\{\(\) => onArchivedView\(true\)\}[\s\S]*?>Archived",
        msg="spec 0245 §2.3 / 0246 §2.12.1 — toggle must include an Archived option that calls onArchivedView(true)",
    )


def test_archived_row_has_dimmed_opacity_class() -> None:
    jsx = _run_list_jsx()
    # Spec 0246 §2.12.3 — the dimmed archived state moved to `.run-card--archived`
    # (the card-layout analogue of `.run-row--archived`); opacity 0.65 lives in CSS.
    assert_jsx_contains(
        jsx,
        r"isArchived \? 'run-card--archived'",
        msg="spec 0245 §2.3 / 0246 §2.12.3 — archived cards must apply `.run-card--archived` for the dimmed treatment",
    )
    # Antipodal-absence: the inline `opacity: 0.65` (or 0.65 with px
    # / decimals) that pre-fix anatomy might have used as a one-off
    # is forbidden — the value must live in CSS where the DS owns it.
    assert_jsx_lacks(
        jsx,
        r"opacity:\s*0\.65",
        msg="spec 0245 §2.3 — opacity 0.65 belongs in `.run-row--archived` CSS, not inline on a row",
    )
