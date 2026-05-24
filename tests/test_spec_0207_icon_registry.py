"""Spec 0207 — link-variant icon registry regression tests.

Locks in two invariants on ``src/dual_research/ui/static/icons.jsx``:

1. The ``'link-variant'`` key exists in the ICONS dict with a non-empty SVG
   path (so the five existing ``<Mdi name="link-variant" />`` call sites
   resolve instead of rendering the placeholder rect at icons.jsx:103-108).
2. Every ``<Mdi name="X" />`` invocation across the static JSX tree
   references a key that exists in the ICONS dict — generalising the
   regression so any future caller using an un-registered name fails CI
   instead of reaching production as a blank rounded square.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests._ui_pattern_helpers import REPO_ROOT, assert_jsx_contains, read_repo_text

_STATIC_DIR = REPO_ROOT / "src" / "dual_research" / "ui" / "static"

# Captures the dict-literal keys: matches `  'key': '...'` rows in the ICONS
# object. Keys are lowercase MDI slugs (letters, digits, hyphens).
_ICONS_KEY_RE = re.compile(r"^\s*'([a-z0-9-]+)':\s*'", re.MULTILINE)

# Captures every <Mdi name="..."/> reference. Permits arbitrary attribute
# order/whitespace; the `name` attribute is required.
_MDI_REF_RE = re.compile(r"<Mdi\b[^>]*\bname=\"([a-z0-9-]+)\"")


def test_link_variant_resolves() -> None:
    text = read_repo_text("src", "dual_research", "ui", "static", "icons.jsx")
    assert_jsx_contains(
        text,
        r"'link-variant':\s*'[^']+'",
        msg=(
            "ICONS dict must contain a non-empty 'link-variant' key so the "
            "evidence/sources chips and lifecycle-footer call sites resolve "
            "to the canonical chain-link glyph (spec 0207 §3)."
        ),
    )


def test_no_call_site_uses_missing_icon() -> None:
    icons_text = (_STATIC_DIR / "icons.jsx").read_text(encoding="utf-8")
    keys = set(_ICONS_KEY_RE.findall(icons_text))
    assert keys, (
        "ICONS dict appears empty — the key-extraction regex failed against "
        f"{_STATIC_DIR / 'icons.jsx'}."
    )

    missing: list[tuple[str, str]] = []
    for jsx_path in sorted(_STATIC_DIR.glob("*.jsx")):
        if jsx_path.name == "icons.jsx":
            continue
        text = jsx_path.read_text(encoding="utf-8")
        for name in _MDI_REF_RE.findall(text):
            if name not in keys:
                missing.append((jsx_path.name, name))

    assert not missing, (
        "Every <Mdi name='...'> call site must reference a key in the ICONS "
        "dictionary at src/dual_research/ui/static/icons.jsx (spec 0207 §5). "
        f"Unregistered references: {missing}"
    )
