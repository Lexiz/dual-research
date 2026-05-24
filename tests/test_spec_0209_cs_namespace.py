"""Spec 0209 — namespace the legacy how-it-works disclosure so it stops
bleeding into the canonical ``.cs-*`` DS primitive.

Source-pattern tests (spec 0206 doctrine). The contract is:

1. ``src/dual_research/ui/static/components.css`` carries exactly ONE
   ``.cs-body``-touching rule block — the modern primitive at lines
   ~1404-1444, whose only ``display`` declaration is
   ``.cs-body.cs-closed { display: none }``. Any future commit that
   reintroduces an unscoped ``.cs-body { display: none }`` (or a
   sibling unscoped ``.cs-section`` / ``.cs-header`` / ``.cs-chevron``
   / ``.cs-title`` rule) resurrects the legacy bleed and is caught
   here before it reaches production.

2. ``src/dual_research/ui/static/how-it-works.jsx`` uses the renamed
   ``hiw-cs-*`` class names and contains zero orphan references to
   the old ``cs-section`` / ``cs-body`` / ``cs-header`` / ``cs-chevron``
   / ``cs-title`` class names — the JSX side must stay in lockstep
   with the CSS rename.

The modern primitive's class names (``cs``, ``cs-header``, ``cs-body``,
``cs-chevron``, ``cs-title``, ``cs-body.cs-open``, ``cs-body.cs-closed``)
are preserved exactly — they are still emitted by ``shared.jsx`` and
by every modern call site (``run-detail.jsx``, ``design-language.jsx``).
The rename is one-sided: only the legacy how-it-works block changes.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

_LIVE_CSS = ("src", "dual_research", "ui", "static", "components.css")
_HIW_JSX = ("src", "dual_research", "ui", "static", "how-it-works.jsx")

# Rule-start anchors. ``(?![\w-])`` excludes selectors that would
# make the class name longer (e.g. ``.cs-section-foo``, ``.cs-bodyx``).
# The ``.cs-body`` variant also excludes a chained-state class — the
# modern primitive declares ``.cs-body.cs-open`` / ``.cs-body.cs-closed``
# (both legal); an unscoped ``.cs-body { … }`` is the pre-fix bleed.
_UNSCOPED_CS_SECTION = r"(?m)^\.cs-section(?![\w-])"
_UNSCOPED_CS_BODY = r"(?m)^\.cs-body(?![\w-])(?!\.)"


def test_components_css_has_no_unscoped_legacy_cs_section() -> None:
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_lacks(
        css,
        _UNSCOPED_CS_SECTION,
        msg=(
            "components.css must not contain an unscoped ``.cs-section`` rule. "
            "Spec 0209 renamed the legacy how-it-works disclosure block to "
            "``.hiw-cs-section`` because the unscoped name collided in the "
            "cascade with the modern CollapsibleSection primitive's `.cs-*` "
            "namespace. Reintroducing the unscoped name resurrects the "
            "computed-display: none bug that hid every modal section body."
        ),
    )


def test_components_css_has_no_unscoped_legacy_cs_body() -> None:
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_lacks(
        css,
        _UNSCOPED_CS_BODY,
        msg=(
            "components.css must not contain an unscoped ``.cs-body`` rule. "
            "The modern primitive only ever declares ``.cs-body.cs-open`` "
            "and ``.cs-body.cs-closed`` (both chained-state). An unscoped "
            "``.cs-body { … }`` rule is the spec 0209 legacy-bleed shape "
            "that set ``display: none`` on every open modern disclosure."
        ),
    )


def test_components_css_modern_closed_rule_present() -> None:
    """The canonical closed-state rule must still exist after the rename.

    Without ``.cs-body.cs-closed { display: none }`` the modern
    primitive would render closed bodies as visible — the opposite
    failure mode. Lock it in.
    """
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_contains(
        css,
        r"\.cs-body\.cs-closed\s*\{[^}]*display:\s*none",
        msg=(
            "components.css must still contain "
            "``.cs-body.cs-closed { display: none }`` — the modern "
            "CollapsibleSection primitive's canonical closed-state rule. "
            "Spec 0209 only renamed the legacy how-it-works block; the "
            "modern primitive must stay intact."
        ),
    )


def test_components_css_has_no_legacy_is_open_descendant_rule() -> None:
    """The smoking-gun rule that triggered the spec-0209 bleed was
    ``.cs-section.is-open .cs-body { display: block }`` — a legacy
    selector that targeted the wrong wrapper (``.cs-section`` instead
    of the modern ``.cs``) and so never actually fired, leaving the
    unscoped ``.cs-body { display: none }`` to win. Lock its absence
    in directly.

    The companion ``.cs-section.is-open .cs-chevron`` selector is the
    same anatomy — both must be gone post-rename. (Renamed counterparts
    use ``.hiw-cs-section.is-open .hiw-cs-…`` and are asserted present
    elsewhere in this module.)
    """
    css = read_repo_text(*_LIVE_CSS)
    for pattern in (
        r"\.cs-section\.is-open\s+\.cs-body",
        r"\.cs-section\.is-open\s+\.cs-chevron",
    ):
        assert_jsx_lacks(
            css,
            pattern,
            msg=(
                f"components.css must not contain ``{pattern}`` — that "
                "selector is the spec-0209 legacy disclosure pattern, "
                "which collided with the modern primitive's ``.cs`` "
                "wrapper and re-introduces the hidden-body bug."
            ),
        )


def test_components_css_has_renamed_hiw_cs_block() -> None:
    """The renamed legacy block must be present so the how-it-works
    page's existing visual still renders."""
    css = read_repo_text(*_LIVE_CSS)
    for selector in (
        r"\.hiw-cs-section\b",
        r"\.hiw-cs-header\b",
        r"\.hiw-cs-chevron\b",
        r"\.hiw-cs-title\b",
        r"\.hiw-cs-body\b",
        r"\.hiw-cs-section\.is-open\s+\.hiw-cs-body\s*\{[^}]*display:\s*block",
    ):
        assert_jsx_contains(
            css,
            selector,
            msg=(
                f"components.css must declare ``{selector}`` — the "
                "spec-0209-renamed legacy how-it-works disclosure block. "
                "Without these rules the How-It-Works page's collapsible "
                "sections render unstyled."
            ),
        )


def test_how_it_works_jsx_uses_renamed_classes() -> None:
    jsx = read_repo_text(*_HIW_JSX)
    # JSX consumer must emit the renamed classes on the legacy disclosure.
    assert_jsx_contains(
        jsx,
        r"'hiw-sec hiw-cs-section'",
        msg=(
            "how-it-works.jsx must wrap each <CollapsibleSection> in "
            "``hiw-sec hiw-cs-section`` (spec 0209 rename). The bare "
            "``cs-section`` class collides with the canonical DS "
            "primitive's namespace and re-introduces the legacy bleed."
        ),
    )
    for cls in ("hiw-cs-header", "hiw-cs-chevron", "hiw-cs-title", "hiw-cs-body"):
        assert_jsx_contains(
            jsx,
            rf'className="{cls}"',
            msg=(
                f"how-it-works.jsx must use ``className={cls!r}`` (spec 0209 "
                "rename). The renamed classes scope the legacy how-it-works "
                "disclosure away from the canonical ``.cs-*`` namespace."
            ),
        )


def test_how_it_works_jsx_has_no_orphan_legacy_class_names() -> None:
    """No ``cs-section`` / ``cs-body`` / ``cs-header`` / ``cs-chevron``
    / ``cs-title`` references survive in how-it-works.jsx.

    The substring search would false-match the renamed ``hiw-cs-…``
    classes, so we anchor each forbidden name with a word boundary on
    the left and exclude a leading ``-`` (which would mean ``hiw-cs-``).
    """
    jsx = read_repo_text(*_HIW_JSX)
    for cls in ("cs-section", "cs-header", "cs-chevron", "cs-title", "cs-body"):
        # Negative lookbehind ``(?<!-)`` rejects ``hiw-cs-…``; ``\b``
        # on the right ensures we don't match ``cs-section-foo``.
        pattern = rf"(?<!-){cls}\b"
        assert_jsx_lacks(
            jsx,
            pattern,
            msg=(
                f"how-it-works.jsx must contain no orphan ``{cls}`` "
                "references — every legacy how-it-works call site was "
                "renamed to ``hiw-cs-…`` in spec 0209. An orphan reference "
                "would emit the bare class into the DOM and target the "
                "(no-longer-existing) legacy rule, breaking the page."
            ),
        )
