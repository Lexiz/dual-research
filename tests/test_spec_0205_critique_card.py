"""Spec 0205 — regression-prevention tests for the P4 critique card.

Source-pattern tests (rather than Playwright DOM tests — the codebase has no
Playwright infra). Each test pins one of the five Bug N anatomies from the
spec by checking the JSX / CSS source for the post-fix pattern AND for the
absence of the pre-fix pattern. The contract a future change has to honour:

- Bug 1 — `.item-card__sources` carries an interior `padding-inline`; the
          expanded source excerpt is a `<blockquote>` (not `<pre>`) with the
          surface-container-low background + brand-toned left border.
- Bug 2 — `ItemCardIssueBody` / `ItemCardCommentBody` no longer render
          `<Markdown text={String(item.body)} />` as a standalone block
          above the lifecycle section; lifecycle leads, inline anchor below.
- Bug 3 — `.item-card__sources-hd` carries a leading `<Mdi name="link-variant" …>`
          glyph and the P3 ReviewCard's Sources chip carries the same glyph.
- Bug 4 — Bar 2 kind filter row renders four `<Chip>` instances inside a
          `.kind-chip-row` wrapper with `data-active` toggling; no
          `<Tab variant="kind">` / `<TabGroup variant="kind-tabs">` call sites.
- Bug 5 — ItemCard's `providerChip` reads both `item.raisedBy || item.raiser`
          and falls back to an `err`-toned `Unknown raiser` chip, not
          `<SystemChip />`.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_DETAIL_JSX = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"
COMPONENTS_CSS = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "components.css"
DS_COMPOSED_CSS = REPO_ROOT / "design-system" / "assets" / "styles" / "composed-components.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─── Bug 1 ─────────────────────────────────────────────────────────────────


def test_sources_segment_indents_inside_card_chrome() -> None:
    """`.item-card__sources` must carry horizontal interior padding (matching
    the lifecycle section's 16 px gutter) so the segment sits inside the card
    chrome instead of going full-bleed against the card frame."""
    for css in (COMPONENTS_CSS, DS_COMPOSED_CSS):
        text = _read(css)
        rule = re.search(r"\.item-card__sources\s*\{[^}]+\}", text)
        assert rule, f"missing .item-card__sources rule in {css.name}"
        body = rule.group(0)
        assert "padding" in body and "16px" in body, (
            f"{css.name}: .item-card__sources lost its 16 px interior gutter — "
            f"the Sources segment will go full-bleed again (Spec 0205 Bug 1)"
        )


def test_source_row_excerpt_is_blockquote_with_brand_border() -> None:
    """The expanded SourceRow's content excerpt must render as a
    `<blockquote>` with the DS surface-tint background + brand-toned left
    border. Pre-0205 it was a `<pre>` block that read as raw debug output."""
    jsx = _read(RUN_DETAIL_JSX)
    # Post-fix: blockquote in the excerpt-wrap (not pre).
    assert re.search(
        r'<blockquote className="source-row__excerpt"',
        jsx,
    ), "SourceRow content excerpt must render as <blockquote> (Spec 0205 Bug 1)"
    assert not re.search(
        r'<pre className="source-row__excerpt"',
        jsx,
    ), "SourceRow content excerpt must not be a <pre> block (Spec 0205 Bug 1)"

    for css in (COMPONENTS_CSS, DS_COMPOSED_CSS):
        text = _read(css)
        rule = re.search(r"\.source-row__excerpt\s*\{[^}]+\}", text)
        assert rule, f"missing .source-row__excerpt rule in {css.name}"
        body = rule.group(0)
        assert "border-left" in body and "var(--md-outline)" in body, (
            f"{css.name}: .source-row__excerpt lost its brand-toned left border "
            f"(Spec 0205 Bug 1)"
        )
        assert "--md-surface-container-low" in body, (
            f"{css.name}: .source-row__excerpt lost its surface-container-low "
            f"background tint (Spec 0205 Bug 1)"
        )


# ─── Bug 2 ─────────────────────────────────────────────────────────────────


def test_issue_and_comment_bodies_lead_with_lifecycle() -> None:
    """`ItemCardIssueBody` and `ItemCardCommentBody` must render
    `<ItemCardLifecycleSection />` as the FIRST child of the body div, with
    NO standalone `<Markdown text={item.body}/>` block above it. The
    lifecycle's raise row already carries `item.body` as its quote, so the
    standalone block was a duplicate."""
    jsx = _read(RUN_DETAIL_JSX)

    for body_fn in ("ItemCardIssueBody", "ItemCardCommentBody"):
        m = re.search(
            rf"function {body_fn}\([^)]+\)\s*\{{[\s\S]*?\n\}}\n",
            jsx,
        )
        assert m, f"could not locate {body_fn} function body"
        body = m.group(0)
        # Lifecycle section must be present in the body.
        assert "ItemCardLifecycleSection" in body, (
            f"{body_fn} no longer renders <ItemCardLifecycleSection /> "
            f"(Spec 0205 Bug 2)"
        )
        # Standalone Markdown body block must NOT appear.
        assert "Markdown text={String(item.body)}" not in body, (
            f"{body_fn} still renders a standalone <Markdown text={{item.body}}/> "
            f"block above lifecycle (Spec 0205 Bug 2 — lifecycle's raise row "
            f"already carries item.body as its quote; standalone block is a "
            f"duplicate)"
        )
        # Lifecycle must appear before the inline anchor blockquote within the body.
        lifecycle_idx = body.find("ItemCardLifecycleSection")
        quote_idx = body.find("item-card__quote-inline")
        if quote_idx != -1:
            assert lifecycle_idx < quote_idx, (
                f"{body_fn} renders the inline anchor blockquote ABOVE the "
                f"lifecycle section (Spec 0205 Bug 2 — lifecycle must lead)"
            )


# ─── Bug 3 ─────────────────────────────────────────────────────────────────


def test_sources_segment_header_carries_canonical_glyph() -> None:
    """`.item-card__sources-hd` must lead with `<Mdi name="link-variant" />`
    — the canonical sources family glyph already used by the head's
    evidence-required chip and the lifecycle's source-requested /
    source-provided chips, so every Sources surface shares one glyph."""
    jsx = _read(RUN_DETAIL_JSX)
    # Locate the segment header render.
    m = re.search(
        r'<div className="item-card__sources-hd">([\s\S]*?)</div>',
        jsx,
    )
    assert m, "could not locate .item-card__sources-hd render"
    header_body = m.group(1)
    assert 'Mdi name="link-variant"' in header_body, (
        ".item-card__sources-hd missing the canonical mdi:link-variant glyph "
        "(Spec 0205 Bug 3)"
    )


def test_reviewcard_sources_chip_carries_same_glyph() -> None:
    """The P3 ReviewCard's `Sources` chip must carry the same
    `mdi:link-variant` glyph so head + segment header share one icon
    across the P3 + P4 surfaces."""
    jsx = _read(RUN_DETAIL_JSX)
    # Find the ReviewCard Sources chip block.
    m = re.search(
        r'\{evidence\.length > 0 && \(\s*<Chip[\s\S]*?label="Sources"[\s\S]*?\)\}',
        jsx,
    )
    assert m, "could not locate ReviewCard Sources chip"
    chip = m.group(0)
    assert 'Mdi name="link-variant"' in chip, (
        "ReviewCard Sources chip missing the canonical mdi:link-variant glyph "
        "(Spec 0205 Bug 3)"
    )


# ─── Bug 4 ─────────────────────────────────────────────────────────────────


def test_kind_filter_row_uses_chip_primitive_not_tabs() -> None:
    """Bar 2 kind filter row must render four `<Chip>` instances inside a
    `.kind-chip-row` wrapper. The legacy `<TabGroup variant="kind-tabs">` +
    `<Tab variant="kind">` markup must not appear at any call site (only in
    the dead-code shared.jsx branches kept for legacy callers)."""
    jsx = _read(RUN_DETAIL_JSX)

    # Live call sites must NOT use the legacy variant=…  attributes.
    # (Comments referencing the old variants are fine — they are prose.)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", jsx)
    code_only = re.sub(r"//.*?(\r?\n)", r"\1", code_only)
    assert 'variant="kind-tabs"' not in code_only, (
        "Bar 2 kind filter row still renders <TabGroup variant=\"kind-tabs\"> "
        "(Spec 0205 Bug 4 — must use Chip primitive)"
    )
    assert 'variant="kind"' not in code_only, (
        "Bar 2 kind filter row still emits <Tab variant=\"kind\"> at a live "
        "call site (Spec 0205 Bug 4 — must use Chip primitive)"
    )

    # The new wrapper must exist with the four kinds + Chip + categoryBubble.
    m = re.search(
        r'<div className="kind-chip-row"[\s\S]*?\)\;\s*\}\)\}\s*</div>',
        jsx,
    )
    assert m, ".kind-chip-row wrapper not found (Spec 0205 Bug 4)"
    row = m.group(0)
    assert "_ITEM_KIND_TONE" in row, (
        ".kind-chip-row Chip does not pull tone from _ITEM_KIND_TONE (Spec "
        "0205 Bug 4 — single source of truth for tone/letter/label)"
    )
    assert "_ITEM_KIND_LETTER" in row and "categoryBubble" in row, (
        ".kind-chip-row Chip missing categoryBubble from _ITEM_KIND_LETTER "
        "(Spec 0205 Bug 4)"
    )
    assert "data-active" in row, (
        ".kind-chip-row Chip missing data-active toggle (Spec 0205 Bug 4)"
    )

    # Per-chip CSS active-state lift via [data-active="true"].
    for css in (COMPONENTS_CSS, DS_COMPOSED_CSS):
        text = _read(css)
        assert re.search(
            r'\.kind-chip-row\s+\.chip\[data-active="true"\]',
            text,
        ), (
            f"{css.name}: missing .kind-chip-row .chip[data-active=\"true\"] "
            f"lift rule (Spec 0205 Bug 4)"
        )


# ─── Bug 5 ─────────────────────────────────────────────────────────────────


def test_itemcard_provider_reads_both_raisedby_and_raiser() -> None:
    """`ItemCard.raisedByAgent` must read both `item.raisedBy` and
    `item.raiser` (the unified `Item` wire shape camelizes `raiser` → `raiser`,
    not `raisedBy`). Pre-0205 the head only checked `raisedBy`, which is why
    every card on the P4 surface fell through to the `<SystemChip />`
    fallback."""
    jsx = _read(RUN_DETAIL_JSX)
    assert re.search(
        r"_resolveAgent\(item\.raisedBy\s*\|\|\s*item\.raiser\)",
        jsx,
    ), (
        "ItemCard must resolve the head's provider chip from "
        "_resolveAgent(item.raisedBy || item.raiser) — reading only raisedBy "
        "is the Bug 5 regression (Spec 0205)"
    )


def test_itemcard_does_not_fall_back_to_systemchip_for_critique_items() -> None:
    """The head's provider chip fallback must NOT be `<SystemChip />` — that
    chip is reserved for the Phase 0 brief card per DS §4.4. A critique item
    with no resolvable raiser is a data-layer regression; we surface it with
    an err-toned `Unknown raiser` chip + a console.warn, never `System`."""
    jsx = _read(RUN_DETAIL_JSX)
    # Capture from the `let providerChip;` declaration up to the next
    # top-level `const` / `let` statement — enough to cover the full
    # if/else, including the nested `} else {` brace.
    m = re.search(
        r"let providerChip;[\s\S]*?(?=\n  (?:const|let)\s+\w+\s*=)",
        jsx,
    )
    assert m, "could not locate providerChip block in ItemCard"
    block = m.group(0)
    assert "<SystemChip" not in block, (
        "ItemCard providerChip falls back to <SystemChip /> for critique items "
        "— reserved for the Phase 0 brief card per DS §4.4 (Spec 0205 Bug 5)"
    )
    assert "Unknown raiser" in block, (
        "ItemCard providerChip fallback missing the canonical err-toned "
        "'Unknown raiser' chip (Spec 0205 Bug 5)"
    )
    assert "console.warn" in block, (
        "ItemCard providerChip fallback missing console.warn — future "
        "regressions of the data-layer raiser projection should be loud "
        "(Spec 0205 Bug 5)"
    )
