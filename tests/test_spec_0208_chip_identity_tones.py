"""Spec 0208 — identity-chip tones promoted into the base Chip primitive.

Source-pattern tests (spec 0206 doctrine) that lock in the structural
rule: ``<Chip tone="claude">`` and ``<Chip tone="gpt">`` render the same
on every surface because the readable 30 % ``color-mix`` treatment lives
in the BASE chip rule, not in per-container overrides.

The post-fix shape (positive assertions) and the pre-fix shape
(antipodal-absence assertions) are paired per anatomical contract so any
regression that re-introduces a scoped identity-tone override or drops
the global treatment fails CI before it reaches production.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

_LIVE_CSS = ("src", "dual_research", "ui", "static", "components.css")
_DS_CSS = ("design-system", "assets", "styles", "composed-components.css")
_DS_SPEC = ("design-system", "SPEC.md")


def test_live_app_base_rule_carries_30pct_tint() -> None:
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_contains(
        css,
        r"\.chip\.tone-claude\s*\{[^}]*color-mix\(in srgb, var\(--p-sable\) 30%, transparent\)",
        msg=(
            "The live-app base rule `.chip.tone-claude` must render the 30% "
            "color-mix tint over --p-sable (spec 0208 §3.1). Without this "
            "the critique card head + DS gallery + how-it-works pane fall "
            "back to the dim 8%-rgba treatment from --claude-bg."
        ),
    )
    assert_jsx_contains(
        css,
        r"\.chip\.tone-gpt\s*\{[^}]*color-mix\(in srgb, var\(--p-sage\)\s*30%, transparent\)",
        msg=(
            "The live-app base rule `.chip.tone-gpt` must render the 30% "
            "color-mix tint over --p-sage (spec 0208 §3.1)."
        ),
    )


def test_ds_side_base_rule_carries_30pct_tint() -> None:
    css = read_repo_text(*_DS_CSS)
    assert_jsx_contains(
        css,
        r"\.chip\.tone-claude\s*\{[^}]*color-mix\(in srgb, var\(--p-sable\) 30%, transparent\)",
        msg=(
            "The DS-side base rule `.chip.tone-claude` must mirror the "
            "live-app 30% tint (CLAUDE.md two-file rule + spec 0208 §3.1). "
            "Before spec 0208 the DS file had no base claude/gpt rule at "
            "all — its scoped `.tl-card-head` override was stranded."
        ),
    )
    assert_jsx_contains(
        css,
        r"\.chip\.tone-gpt\s*\{[^}]*color-mix\(in srgb, var\(--p-sage\)\s*30%, transparent\)",
        msg="The DS-side base rule `.chip.tone-gpt` must mirror the live-app 30% tint.",
    )


def test_no_scoped_identity_overrides_in_live_css() -> None:
    css = read_repo_text(*_LIVE_CSS)
    assert_jsx_lacks(
        css,
        r"\.tl-card-head\s+\.chip\.tone-claude\s*\{",
        msg=(
            "Spec 0208 §3.3 deleted the `.tl-card-head .chip.tone-claude` "
            "scoped override — the base rule provides the same treatment "
            "now. Re-adding the scope is forbidden per the §3 Primitives "
            "structural rule (identity chips render the same on every "
            "surface)."
        ),
    )
    assert_jsx_lacks(
        css,
        r"\.tl-card-head\s+\.chip\.tone-gpt\s*\{",
        msg="Spec 0208 §3.3 deleted the `.tl-card-head .chip.tone-gpt` scoped override.",
    )
    assert_jsx_lacks(
        css,
        r"\.item-card__lifecycle-section\s+\.lc-row-chips\s+\.chip\.tone-claude\s*\{",
        msg=(
            "Spec 0208 §3.3 deleted the `.lc-row-chips .chip.tone-claude` "
            "scoped override. The base rule now tints lifecycle-row chips "
            "the same as every other surface."
        ),
    )
    assert_jsx_lacks(
        css,
        r"\.item-card__lifecycle-section\s+\.lc-row-chips\s+\.chip\.tone-gpt\s*\{",
        msg="Spec 0208 §3.3 deleted the `.lc-row-chips .chip.tone-gpt` scoped override.",
    )


def test_no_scoped_identity_overrides_in_ds_css() -> None:
    css = read_repo_text(*_DS_CSS)
    assert_jsx_lacks(
        css,
        r"\.tl-card-head\s+\.chip\.tone-claude\s*\{",
        msg="DS-side mirror of the deleted `.tl-card-head .chip.tone-claude` override (spec 0208 §3.3).",
    )
    assert_jsx_lacks(
        css,
        r"\.tl-card-head\s+\.chip\.tone-gpt\s*\{",
        msg="DS-side mirror of the deleted `.tl-card-head .chip.tone-gpt` override (spec 0208 §3.3).",
    )
    assert_jsx_lacks(
        css,
        r"\.item-card__lifecycle-section\s+\.lc-row-chips\s+\.chip\.tone-claude\s*\{",
        msg="DS-side mirror of the deleted `.lc-row-chips .chip.tone-claude` override (spec 0208 §3.3).",
    )
    assert_jsx_lacks(
        css,
        r"\.item-card__lifecycle-section\s+\.lc-row-chips\s+\.chip\.tone-gpt\s*\{",
        msg="DS-side mirror of the deleted `.lc-row-chips .chip.tone-gpt` override (spec 0208 §3.3).",
    )


def test_global_light_mode_backstop_present() -> None:
    """Identity chips read --md-on-{primary,secondary}-container globally in light mode."""
    for parts, label in ((_LIVE_CSS, "components.css"), (_DS_CSS, "composed-components.css")):
        css = read_repo_text(*parts)
        assert_jsx_contains(
            css,
            r"body\.light\s+\.chip\.tone-claude\b[^{]*\{[^}]*color:\s*var\(--md-on-primary-container\)",
            msg=(
                f"{label}: spec 0208 §3.2 promoted the light-mode identity-chip "
                "text colour from `.tl-card-head`-scoped to global. "
                "`body.light .chip.tone-claude { color: var(--md-on-primary-container) }` "
                "must be present so every surface reads the same token."
            ),
        )
        assert_jsx_contains(
            css,
            r"body\.light\s+\.chip\.tone-gpt\b[^{]*\{[^}]*color:\s*var\(--md-on-secondary-container\)",
            msg=(
                f"{label}: `body.light .chip.tone-gpt`'s color must resolve to "
                "`var(--md-on-secondary-container)` (spec 0208 §3.2)."
            ),
        )


def test_no_hex_backstop_in_chip_rules() -> None:
    """The defensive hex backstop (#3b2810 / #0a322d) is gone — token-driven only."""
    for parts, label in ((_LIVE_CSS, "components.css"), (_DS_CSS, "composed-components.css")):
        css = read_repo_text(*parts)
        assert_jsx_lacks(
            css,
            r"#3b2810",
            msg=(
                f"{label}: spec 0208 §3.2 dropped the defensive hex backstop "
                "(`#3b2810` for claude). Identity-chip text colour now reads "
                "directly from `--md-on-primary-container`. CLAUDE.md forbids "
                "hex codes in this file regardless."
            ),
        )
        assert_jsx_lacks(
            css,
            r"#0a322d",
            msg=(
                f"{label}: spec 0208 §3.2 dropped the defensive hex backstop "
                "(`#0a322d` for gpt). Identity-chip text colour now reads "
                "directly from `--md-on-secondary-container`."
            ),
        )


def test_spec_md_chip_polish_table_no_longer_lists_identity_tones() -> None:
    """The §4.4 chip-polish table is shrunk to the two System-only rows."""
    spec = read_repo_text(*_DS_SPEC)
    assert_jsx_lacks(
        spec,
        r"\|\s*`\.chip\.tone-claude`",
        msg=(
            "design-system/SPEC.md §4.4 chip-polish table must no longer list "
            "`.chip.tone-claude` (spec 0208 §3.4) — identity chips are documented "
            "in the new structural rule below §3 Primitives, not in the "
            "timeline-scoped polish table."
        ),
    )
    assert_jsx_lacks(
        spec,
        r"\|\s*`\.chip\.tone-gpt`",
        msg=(
            "design-system/SPEC.md §4.4 chip-polish table must no longer list "
            "`.chip.tone-gpt` (spec 0208 §3.4)."
        ),
    )


def test_spec_md_carries_identity_rendering_rule() -> None:
    spec = read_repo_text(*_DS_SPEC)
    assert_jsx_contains(
        spec,
        r"Identity-chip rendering rule.*spec 0208",
        msg=(
            "design-system/SPEC.md must carry the spec 0208 structural rule "
            "below §3 Primitives — identity chips render the same on every "
            "surface; per-container overrides for identity tones are "
            "forbidden."
        ),
    )
