"""Spec 0190 — `<Tab variant="solid">` emits `data-active`, not `.is-active`.

Spec 0173 §2.3 migrated the bar-2 segments from `.is-active` className to
`data-active="true"` attribute selector but left a dual CSS selector in place
because `TimelineTabs` (the other in-tree consumer of `<Tab variant="solid">`
via shared.jsx) still emitted the legacy `.is-active` className. Spec 0190
completes the migration: the `variant === 'solid'` branch in shared.jsx now
emits `data-active` only, and both `components.css` and
`composed-components.css` drop the dual selector for the canonical attribute
selector.

Structural tests over `shared.jsx` and both CSS files pin the new shape:

1. The `variant === 'solid'` branch in shared.jsx contains `data-active=` and
   does NOT contain `'is-active'`.
2. Both CSS files declare `.tab-solid[data-active="true"]` (the canonical
   selector) and do NOT declare `.tab-solid.is-active` (the legacy dual
   selector).

Pattern mirror of `tests/spec0173/test_item_round_shape.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent.parent
SHARED_JSX = ROOT / "src" / "dual_research" / "ui" / "static" / "shared.jsx"
COMPONENTS_CSS = ROOT / "src" / "dual_research" / "ui" / "static" / "components.css"
COMPOSED_CSS = ROOT / "design-system" / "assets" / "styles" / "composed-components.css"


@pytest.fixture(scope="module")
def shared_src() -> str:
    return SHARED_JSX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def components_src() -> str:
    return COMPONENTS_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def composed_src() -> str:
    return COMPOSED_CSS.read_text(encoding="utf-8")


def _variant_solid_branch(src: str) -> str:
    """Extract the body of the `if (variant === 'solid') { return ( … ); }`
    branch in shared.jsx so the assertions only look at that branch (not the
    other variants which still use `is-active`).

    Spec 0205.2 removed the `variant === 'kind'` branch that previously
    delimited the end of the solid branch; the next branch is now
    `variant === 'phase'`."""
    match = re.search(
        r"if\s*\(\s*variant\s*===\s*'solid'\s*\)\s*\{(.*?)\}\s*if\s*\(\s*variant\s*===\s*'phase'",
        src,
        flags=re.DOTALL,
    )
    assert match is not None, (
        "Could not locate the `variant === 'solid'` branch in shared.jsx. "
        "Has the Tab component been restructured?"
    )
    return match.group(1)


def test_solid_branch_emits_data_active(shared_src: str) -> None:
    """`<Tab variant="solid">` must emit `data-active={active ? 'true' : undefined}`
    so the canonical CSS attribute selector matches the active state."""
    branch = _variant_solid_branch(shared_src)
    assert "data-active=" in branch, (
        f"`variant === 'solid'` branch does not emit `data-active`. "
        f"Branch body: {branch!r}"
    )


def test_solid_branch_does_not_emit_is_active(shared_src: str) -> None:
    """`<Tab variant="solid">` must NOT emit the legacy `'is-active'`
    className — the spec 0173 §2.3 migration is now complete."""
    branch = _variant_solid_branch(shared_src)
    assert "'is-active'" not in branch and '"is-active"' not in branch, (
        f"`variant === 'solid'` branch still emits `is-active` className. "
        f"Spec 0190 completed the data-active migration; this should be gone. "
        f"Branch body: {branch!r}"
    )


def test_other_variants_still_use_is_active(shared_src: str) -> None:
    """Spec 0190 §5: other Tab variants (`phase`, `chrome`, the default
    `.tab`) keep their `is-active` className — they target separate CSS
    selectors and are out of scope. This guard catches an accidental
    sweep that drops `is-active` from those branches too.

    Spec 0205.2 removed the `'kind'` variant from the list above; the
    surviving branches are `phase`, `chrome`, and the default."""
    # The remaining `is-active` uses live in branches AFTER the solid branch.
    # We look at the entire file minus the solid branch and confirm at least
    # one `'is-active'` survives.
    branch = _variant_solid_branch(shared_src)
    rest = shared_src.replace(branch, "")
    assert "'is-active'" in rest, (
        "No `is-active` className references remain in shared.jsx. Spec 0190 "
        "§5 expected the phase / chrome / default Tab variants to keep their "
        "`is-active` modifier — did this spec accidentally sweep them too?"
    )


def test_components_css_drops_is_active_dual_selector(components_src: str) -> None:
    """`src/dual_research/ui/static/components.css` must not carry the
    legacy `.tab-solid.is-active` selector after spec 0190."""
    assert not re.search(r"\.tab-solid\s*\.is-active\b", components_src), (
        "components.css still carries `.tab-solid.is-active` selector. "
        "Spec 0190 dropped the dual selector — the canonical "
        "`.tab-solid[data-active=\"true\"]` is the sole active-state target."
    )


def test_components_css_keeps_data_active_selector(components_src: str) -> None:
    """`components.css` must still carry `.tab-solid[data-active="true"]` —
    the canonical active-state selector is the sole survivor of the dual
    selector spec 0190 collapsed."""
    assert '.tab-solid[data-active="true"]' in components_src, (
        "components.css is missing `.tab-solid[data-active=\"true\"]`. "
        "Active-state styling would be lost."
    )


def test_composed_components_css_drops_is_active_dual_selector(
    composed_src: str,
) -> None:
    """`design-system/assets/styles/composed-components.css` must mirror
    components.css per the CLAUDE.md two-files-in-sync rule."""
    assert not re.search(r"\.tab-solid\s*\.is-active\b", composed_src), (
        "composed-components.css still carries `.tab-solid.is-active`. "
        "Spec 0190 must drop it from BOTH CSS files."
    )


def test_composed_components_css_keeps_data_active_selector(
    composed_src: str,
) -> None:
    assert '.tab-solid[data-active="true"]' in composed_src, (
        "composed-components.css is missing `.tab-solid[data-active=\"true\"]`. "
        "The DS canonical CSS must keep the active-state selector."
    )
