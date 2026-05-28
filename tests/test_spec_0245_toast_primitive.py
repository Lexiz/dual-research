"""Spec 0245 — Toast primitive CSS-file sync + legacy retirement tests.

`.md-toast` is a DS primitive — per CLAUDE.md it lands in BOTH
`design-system/assets/styles/composed-components.css` (DS canonical)
AND `src/dual_research/ui/static/components.css` (live app). The pair
must stay in sync. The legacy `.tour-skip-toast` rule (live-app only)
is retired in the same commit.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import assert_jsx_contains, assert_jsx_lacks, read_repo_text


def test_toast_class_in_both_css_files() -> None:
    live = read_repo_text("src", "dual_research", "ui", "static", "components.css")
    ds = read_repo_text("design-system", "assets", "styles", "composed-components.css")
    # The host + the toast class must be present in both files.
    for name, text in (("live components.css", live), ("DS composed-components.css", ds)):
        assert_jsx_contains(
            text,
            r"\.md-toast-host\s*\{",
            msg=f"spec 0245 §2.4 — `.md-toast-host` must be declared in {name} (CLAUDE.md DS sync rule)",
        )
        assert_jsx_contains(
            text,
            r"\.md-toast\s*\{",
            msg=f"spec 0245 §2.4 — `.md-toast` must be declared in {name} (CLAUDE.md DS sync rule)",
        )
        assert_jsx_contains(
            text,
            r"\.md-toast--tone-ok\s*\{",
            msg=f"spec 0245 §2.4 — `.md-toast--tone-ok` must be declared in {name}",
        )
        assert_jsx_contains(
            text,
            r"\.md-toast--tone-error\s*\{",
            msg=f"spec 0245 §2.4 — `.md-toast--tone-error` must be declared in {name}",
        )


def test_legacy_tour_skip_toast_removed() -> None:
    live = read_repo_text("src", "dual_research", "ui", "static", "components.css")
    # The bespoke `.tour-skip-toast` rule + its dedicated keyframe must
    # both be gone — `useToast` is the only path now.
    assert_jsx_lacks(
        live,
        r"\.tour-skip-toast\s*\{",
        msg="spec 0245 §2.4 — `.tour-skip-toast` CSS class must be removed; useToast is the only path",
    )
    assert_jsx_lacks(
        live,
        r"@keyframes\s+tour-skip-fadein",
        msg="spec 0245 §2.4 — `tour-skip-fadein` keyframe must be removed alongside `.tour-skip-toast`",
    )
    # And the JSX that mounted the bespoke <SkipToast> wrapper must be
    # gone from onboarding.jsx — the tour dispatches via useToast now.
    onboarding = read_repo_text("src", "dual_research", "ui", "static", "onboarding.jsx")
    assert_jsx_lacks(
        onboarding,
        r"className=\"tour-skip-toast\"",
        msg="spec 0245 §2.4 — onboarding tour must no longer mount the `.tour-skip-toast` JSX",
    )
