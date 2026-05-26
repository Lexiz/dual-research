"""Spec 0221 — DocumentModal labels the doc/doc-live body tab "Output".

Source-pattern tests (spec 0206 doctrine) that lock the anatomical
contract: in ``DocumentModal`` the body tab's ``label`` is a ternary
keyed on a ``isDocItem`` predicate that matches both ``'doc'`` and
``'doc-live'`` item kinds, replacing the previous unconditional
``label: 'Content'``.

The positive assertions pin the post-fix shape (gating predicate
present + ternary in the descriptor); the antipodal-absence assertion
proves the pre-fix unconditional ``label: 'Content'`` block on the
body-tab descriptor is gone.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

_RUN_DETAIL = ("src", "dual_research", "ui", "static", "run-detail.jsx")


def test_document_modal_gates_label_on_isdocitem() -> None:
    jsx = read_repo_text(*_RUN_DETAIL)
    assert_jsx_contains(
        jsx,
        r"label:\s*isDocItem\s*\?\s*'Output'\s*:\s*'Content'",
        msg=(
            "DocumentModal's body tab descriptor must use a ternary on "
            "`isDocItem` so doc / doc-live modals show 'Output' while turn "
            "/ plan modals (which route through other modal components) "
            "are unaffected (spec 0221 §3)."
        ),
    )


def test_document_modal_defines_isdocitem_predicate() -> None:
    jsx = read_repo_text(*_RUN_DETAIL)
    assert_jsx_contains(
        jsx,
        r"const\s+isDocItem\s*=\s*item\.kind\s*===\s*'doc'\s*\|\|\s*item\.kind\s*===\s*'doc-live'",
        msg=(
            "DocumentModal must define `isDocItem` as `item.kind === 'doc' "
            "|| item.kind === 'doc-live'` so both completed Phase 3/5 "
            "drafts AND in-flight live drafts get the 'Output' label "
            "(spec 0221 §3 + §8)."
        ),
    )


def test_document_modal_body_tab_no_unconditional_content_label() -> None:
    jsx = read_repo_text(*_RUN_DETAIL)
    # Scoped to the DocumentModal context: the only place where the body
    # tab descriptor is immediately followed by an `item.turnKey &&`
    # conditional Agent Input tab. The unrelated turn/plan modal at
    # ~line 7000 uses an unconditional `{ id: 'input', label: 'User
    # prompt' }` shape, which is out of scope for this spec (§7) and so
    # must NOT match this antipodal.
    assert_jsx_lacks(
        jsx,
        r"id:\s*'content',\s*\n\s*label:\s*'Content',\s*\n"
        r"\s*content:\s*<LazyMarkdownBody[^>]+/>,\s*\n"
        r"\s*\},\s*\n\s*item\.turnKey\s*&&",
        msg=(
            "Pre-fix shape — unconditional `label: 'Content'` on the "
            "DocumentModal body tab descriptor (followed by the "
            "`item.turnKey &&` conditional Agent Input tab) — must be "
            "gone. The body tab label is now gated on `isDocItem` "
            "(spec 0221 §3)."
        ),
    )
