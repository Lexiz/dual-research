"""Spec 0245 — RunRow archive-button source-pattern tests.

Source-pattern guards per spec 0206 §13 doctrine. The positive regex
locks the post-fix gating shape (`hover && isAdmin && !isArchived &&
!archivedView`); the absence regex locks out the pre-fix anatomy (the
archive button rendered unconditionally OR ungated on admin).
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)


def _run_list_jsx() -> str:
    return read_repo_text("src", "dual_research", "ui", "static", "run-list.jsx")


def test_archive_button_renders_inside_run_row() -> None:
    jsx = _run_list_jsx()
    # Post-fix anatomy: the archive button mounts under the
    # `showArchiveBtn` predicate, which is itself defined as
    # `hover && isAdmin && !isArchived && !archivedView`. Anchoring
    # both halves keeps the test bidirectional.
    assert_jsx_contains(
        jsx,
        r"const showArchiveBtn = hover && isAdmin && !isArchived && !archivedView;",
        msg="spec 0245 §2.3 — archive-button gate predicate must combine hover + isAdmin + !isArchived + !archivedView",
    )
    # Spec 0246 §2.12.2 moved the affordance onto `.run-card` — the button
    # now also carries the `rc-archive-btn` positioning class. The gate and
    # the canonical `<Icon.Archive />` glyph are unchanged.
    assert_jsx_contains(
        jsx,
        r"showArchiveBtn && \(\s*<button[\s\S]*?className=\"md-icon-btn rc-archive-btn\"[\s\S]*?<Icon\.Archive />",
        msg="spec 0245 §2.3 / 0246 §2.12.2 — archive button must render an `.md-icon-btn rc-archive-btn` with the canonical `<Icon.Archive />` glyph, gated on showArchiveBtn",
    )
    assert_jsx_contains(
        jsx,
        r"aria-label=\{`Archive run \$\{displayId\}`\}",
        msg="spec 0245 §2.3 — archive button aria-label must read 'Archive run <displayId>'",
    )


def test_pre_fix_anatomy_absent() -> None:
    import re
    jsx = _run_list_jsx()
    # Antipodal-absence: only one `<Icon.Archive />` render-site exists
    # in run-list.jsx, and it lives inside the showArchiveBtn-gated
    # `<button>`. A second occurrence — or an occurrence outside the
    # gate — re-introduces the pre-fix anatomy (the archive affordance
    # rendered ungated / always visible).
    occurrences = re.findall(r"<Icon\.Archive\s*/>", jsx)
    assert len(occurrences) == 1, (
        f"spec 0245 §2.3 — expected exactly one <Icon.Archive /> render-site in "
        f"run-list.jsx (inside the showArchiveBtn gate); found {len(occurrences)}"
    )
    # And the unarchive button has the same shape: exactly one render-site,
    # which lives inside showUnarchiveBtn. Symmetric guarantee.
    unarchive_occurrences = re.findall(r"<Icon\.ArchiveUp\s*/>", jsx)
    assert len(unarchive_occurrences) == 1, (
        f"spec 0245 §2.3 — expected exactly one <Icon.ArchiveUp /> render-site in "
        f"run-list.jsx (inside the showUnarchiveBtn gate); found {len(unarchive_occurrences)}"
    )
