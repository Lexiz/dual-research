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
        r"isAdmin && \(\s*<TabGroup variant=\"solid\" data-testid=\"archived-view-toggle\">",
        msg="spec 0245 §2.3 — Active/Archived toggle must mount only for admins (isAdmin && ...)",
    )
    assert_jsx_contains(
        jsx,
        r"onClick=\{\(\) => setArchivedView\(false\)\}[\s\S]*?>\s*Active",
        msg="spec 0245 §2.3 — toggle must include an Active option that calls setArchivedView(false)",
    )
    assert_jsx_contains(
        jsx,
        r"onClick=\{\(\) => setArchivedView\(true\)\}[\s\S]*?>\s*Archived",
        msg="spec 0245 §2.3 — toggle must include an Archived option that calls setArchivedView(true)",
    )


def test_archived_row_has_dimmed_opacity_class() -> None:
    jsx = _run_list_jsx()
    # Post-fix: archived rows carry the `.run-row--archived` class so
    # `opacity: 0.65` in components.css takes effect.
    assert_jsx_contains(
        jsx,
        r"className=\{isArchived \? 'run-row--archived' : undefined\}",
        msg="spec 0245 §2.3 — archived rows must apply the `.run-row--archived` CSS class for the dimmed treatment",
    )
    # Antipodal-absence: the inline `opacity: 0.65` (or 0.65 with px
    # / decimals) that pre-fix anatomy might have used as a one-off
    # is forbidden — the value must live in CSS where the DS owns it.
    assert_jsx_lacks(
        jsx,
        r"opacity:\s*0\.65",
        msg="spec 0245 §2.3 — opacity 0.65 belongs in `.run-row--archived` CSS, not inline on a row",
    )
