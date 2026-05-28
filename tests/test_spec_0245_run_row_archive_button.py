"""Spec 0245 — admin archive affordance source-pattern tests.

Source-pattern guards per spec 0206 §13 doctrine. Spec 0245 introduced an
admin-only archive affordance on the run row; spec 0248 §2.3 replaced the
floating `.rc-archive-btn` icon button + full-screen confirm `Modal` with
the inline `.rc-tray` (prompt → confirm in place). These tests lock the
*capability* in its current (tray) form — the admin/view gate and the
endpoint wiring — and assert the superseded floating-button anatomy is
gone. The tray's own anatomy is locked by ``test_spec_0248_all_runs.py``.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)


def _run_list_jsx() -> str:
    return read_repo_text("src", "dual_research", "ui", "static", "run-list.jsx")


def test_admin_archive_affordance_gated_and_wired() -> None:
    jsx = _run_list_jsx()
    # Post-spec-0248 anatomy: the archive tray mounts under an admin +
    # active-view gate; the restore tray under an admin + archived gate.
    assert_jsx_contains(
        jsx,
        r"const showArchiveTray = isAdmin && !isArchived && !archivedView;",
        msg="spec 0245/0248 §2.3 — archive tray gate must combine isAdmin + !isArchived + !archivedView",
    )
    assert_jsx_contains(
        jsx,
        r"const showRestoreTray = isAdmin && isArchived;",
        msg="spec 0245/0248 §2.3 — restore tray gate must combine isAdmin + isArchived",
    )
    # The archive / restore actions hit the canonical endpoints unchanged.
    assert_jsx_contains(
        jsx,
        r"/api/runs/\$\{encodeURIComponent\(target\.id\)\}/archive`, \{ method: 'POST' \}",
        msg="spec 0245 — archive must POST /api/runs/{id}/archive",
    )
    assert_jsx_contains(
        jsx,
        r"/api/runs/\$\{encodeURIComponent\(target\.id\)\}/archive`, \{ method: 'DELETE' \}",
        msg="spec 0245 — restore must DELETE /api/runs/{id}/archive",
    )


def test_pre_fix_floating_button_anatomy_absent() -> None:
    jsx = _run_list_jsx()
    # Antipodal-absence: the spec-0248 rewrite removed the floating icon
    # button entirely — neither the positioning class nor the icon-button
    # render-site may survive.
    assert_jsx_lacks(
        jsx,
        r"rc-archive-btn",
        msg="spec 0248 §2.3 — the floating .rc-archive-btn must be removed (replaced by .rc-tray)",
    )
    assert_jsx_lacks(
        jsx,
        r"<Icon\.Archive\s*/>",
        msg="spec 0248 §2.3 — the floating archive icon-button render-site must be gone",
    )
