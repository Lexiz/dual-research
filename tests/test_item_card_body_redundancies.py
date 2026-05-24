"""Spec 0179 — critique-card body redundancies must stay deleted.

ItemCard's per-kind sub-renderers (DQ / Issue / Comment) historically
duplicated state/anchor/seen-row metadata that the head's chips and the
inline anchor already carry. This test locks the deletions so a future
"defensive add-back" PR cannot reintroduce the redundancies without
explicit, named approval (modify this test).

Note vs the original spec body: spec 0173 §2.9 rewrote `ItemCardDQBody`
to mount `ItemCardThreadView` instead of a stack of `ItemCardTurnRow`s;
the resolution text now rides the resolve-transition bubble. The
fourth assertion below is adapted to assert that `ItemCardThreadView`
remains the resolution-text surface inside `ItemCardDQBody`.
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def _read():
    return JSX.read_text()


def test_item_card_dq_no_terminal_verdict_row():
    text = _read()
    # The `.item-card__verdict` class in ItemCardDQBody was the third repetition
    # of the resolution text — dropped by spec 0179 §3.1.
    #
    # The retirement comment in components.css uses the literal class name in
    # prose; the JSX file's own retirement comment talks about
    # "the pre-0179 `.item-card__verdict` row" — both are intentional and stay,
    # but we lock that no LIVE className= consumer survives.
    assert 'className="item-card__verdict"' not in text, (
        "JSX className='item-card__verdict' regressed — spec 0179 §3.1 deleted "
        "this row. If reintroducing the verdict row deliberately, modify this "
        "test and name the spec that justifies it."
    )


def test_item_card_no_bottom_anchor_blockquote():
    text = _read()
    # `.item-card__anchor--bottom` was rendered as a duplicate of the inline
    # anchor on Issue + Comment bodies — dropped by §3.2 + §3.3.
    assert "item-card__anchor--bottom" not in text, (
        "item-card__anchor--bottom is gone from run-detail.jsx per spec 0179 §3.2/§3.3. "
        "The inline anchor at the top of the body is the only canonical anchor surface."
    )


def test_item_card_no_seen_row():
    text = _read()
    # `.item-card__seen-row` chip cluster duplicated the head's lifecycle chip
    # (spec 0173 §2.8) — dropped by §3.4 + §3.5.
    assert 'className="item-card__seen-row"' not in text, (
        "JSX className='item-card__seen-row' regressed — spec 0179 §3.4/§3.5 "
        "deleted this chip cluster. Raised-by + round metadata lives in the "
        "head lifecycle chip (spec 0173 §2.8)."
    )


def test_item_card_dq_lifecycle_section_preserved():
    """Adapted from spec §4's fourth test, refreshed for spec 0203 §2.6.
    The pre-0173 `<ItemCardTurnRow>` stack became `<ItemCardThreadView>`
    in spec 0173 §2.9; spec 0203 §2.6 replaced that with
    `<ItemCardLifecycleSection>` (LIFECYCLE overline + `.lc-row` stack)
    so all four kinds (Q / D / I / C) render the same expanded anatomy.
    We lock the current surface so a future PR that drops it doesn't
    take the resolution text with it."""
    text = _read()
    m = re.search(
        r"function\s+ItemCardDQBody\b.*?(?=\nfunction\s+\w+)",
        text, re.DOTALL,
    )
    assert m is not None, "ItemCardDQBody body span not found"
    body = m.group(0)
    assert re.search(r"<ItemCardLifecycleSection\s+item=\{item\}", body), (
        "ItemCardDQBody must still mount <ItemCardLifecycleSection item={item} /> "
        "after spec 0203 §2.6 replaced ItemCardThreadView — the lifecycle "
        "section is the canonical resolution-text surface. If it's gone, "
        "the resolution text disappears entirely from terminal D/Q cards."
    )


def test_design_system_spec_carries_parity_gate():
    """Spec 0179 §3.6 mandates a parity-verification gate in
    design-system/SPEC.md §4.1. Lock that it stays present so future DS
    edits don't drop it silently."""
    spec = (Path(__file__).parent.parent / "design-system" / "SPEC.md").read_text()
    assert "ItemCard parity verification" in spec, (
        "design-system/SPEC.md must carry the spec 0179 §3.6 parity-verification "
        "rule under §4.1. PRs that touch ItemCard chrome must embed an 8-capture "
        "image grid in the PR description."
    )
    # And the canonical reference path is the four screenshot anchors.
    assert "07-question-card-duplicate.png" in spec
    assert "10-comments-card.png" in spec
