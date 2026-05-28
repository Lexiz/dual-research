"""Spec 0233 §3 step 6 — invariant: every spec template under
``specs/_templates/`` declares the ``disposition`` and ``disposition_reason``
frontmatter keys so verbatim-template authors satisfy the spec 0229.1
validator gate without having to read the error message.

The bar-string placeholder (``ship | defer | archive``) is intentional per
spec 0233 §2 — it fails the validator's vocabulary check, so an author who
forgets to pick a value still hits a clear error rather than silently
shipping with the placeholder.
"""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.frontmatter import parse

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "specs" / "_templates"


def _template_files() -> list[Path]:
    return sorted(p for p in TEMPLATES_DIR.glob("*.md") if p.name != "README.md")


def test_templates_directory_has_files() -> None:
    files = _template_files()
    assert files, f"expected at least one template under {TEMPLATES_DIR}"


def test_every_template_declares_disposition_keys() -> None:
    missing: list[str] = []
    for tpl in _template_files():
        fm = parse(tpl).frontmatter
        if "disposition" not in fm or "disposition_reason" not in fm:
            missing.append(tpl.name)
    assert not missing, (
        "spec 0233 invariant: every template under specs/_templates/ must "
        "declare `disposition` and `disposition_reason` placeholders. "
        f"Missing: {missing}"
    )
