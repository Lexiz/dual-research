"""Spec 0172 — critique-card regression guard.

Two paired symptoms regressed by spec 0151 §3.4.3 and partially fixed
by spec 0173 §2.5 / §2.9: the head ID chip (`<code>{item.id}</code>`)
and the Disagreement / Question body `__sid` were retired then. This
spec finishes the job for the Issue body: it deletes the
`<strong className="item-card__sid">{shortCode}</strong>` chip plus
the surrounding `.item-card__title-row` block that did manual
`item.body.split('\\n')` and rendered the first line through a plain
`<span>` — which surfaced literal `**` delimiters when the upstream
body began with `**Title**`. The fix routes the whole body through
`<Markdown>`, matching `ItemCardCommentBody`'s existing pattern, so
bold renders as real `<strong>` and the cryptic short-code disappears.

A vitest DOM test would be the cleanest regression check, but the
project has no vitest harness for `run-detail.jsx` (loaded via
in-browser babel, not bundled). This static-analysis pass guards the
structural contract that survives in pytest:
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent
RUN_DETAIL = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"
COMPONENTS_CSS = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "components.css"
COMPOSED_CSS = REPO_ROOT / "design-system" / "assets" / "styles" / "composed-components.css"


@pytest.fixture(scope="module")
def jsx() -> str:
    return RUN_DETAIL.read_text()


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text()


@pytest.fixture(scope="module")
def composed_css() -> str:
    return COMPOSED_CSS.read_text()


def test_no_item_card_sid_consumer(jsx: str) -> None:
    """The cryptic short-code surface `.item-card__sid` must have no JSX
    consumer — neither the Issue body `<strong>` nor any DQ body `<code>`
    callsite the original spec 0172 catalog called out."""
    assert "item-card__sid" not in jsx, (
        "Found a JSX className='item-card__sid' consumer — spec 0172 deletes "
        "the cryptic short-code surface across all critique card kinds"
    )


def test_no_item_card_title_row_consumer(jsx: str) -> None:
    """The `.item-card__title-row` block (which manually split body on '\\n'
    and rendered the title line through a plain <span>, surfacing literal
    `**` delimiters) must be deleted."""
    assert "item-card__title-row" not in jsx, (
        "Found a JSX className='item-card__title-row' consumer — the title-row "
        "block is what produced the literal `**` markdown regression"
    )
    # And neither of its leaf children — title-sep / title — should remain.
    assert "item-card__title-sep" not in jsx
    assert 'className="item-card__title"' not in jsx


def test_no_head_id_chip(jsx: str) -> None:
    """The head ID chip `<code>{item.id}</code>` from spec 0151 §3.4.3 (already
    retired by spec 0173 §2.5) must stay retired."""
    # Tolerate whitespace inside the curly braces.
    pattern = re.compile(r"<code>\s*\{\s*item\.id\s*\}\s*</code>")
    assert not pattern.search(jsx), (
        "Found a `<code>{item.id}</code>` head chip — spec 0173 §2.5 / 0172 §3 "
        "drops this cryptic ID surface"
    )


def test_issue_body_does_not_split_on_newline(jsx: str) -> None:
    """`ItemCardIssueBody` must not carry the spec-0151 manual
    `split('\\n')` / `titleLine` / `restBody` / `shortCode` heuristic
    that produced literal `**` for bold-prefixed bodies. The body is
    rendered via `<ItemCardLifecycleSection />` (spec 0205 Bug 2 — the
    lifecycle's raise row carries `item.body` as its quote, so the
    standalone Markdown block above it was a duplicate)."""
    match = re.search(
        r"function ItemCardIssueBody\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx,
        flags=re.DOTALL,
    )
    assert match is not None, "ItemCardIssueBody function body not located"
    fn_body = match.group("body")

    # The split-on-newline / titleLine / restBody heuristic stays out.
    assert "split('\\n')" not in fn_body, (
        "ItemCardIssueBody still splits item.body on '\\n' — spec 0172 dropped "
        "the manual title-line heuristic; spec 0205 keeps it out"
    )
    assert "titleLine" not in fn_body
    assert "restBody" not in fn_body
    # Lifecycle section is the body renderer post-spec-0205.
    assert "ItemCardLifecycleSection" in fn_body, (
        "ItemCardIssueBody must render <ItemCardLifecycleSection /> as the "
        "body (spec 0205 Bug 2 — lifecycle leads)"
    )

    # The shortCode derivation that produced the `__sid` chip is gone.
    assert "parseCodeId(item.id)" not in fn_body
    assert "shortCode" not in fn_body


def test_dead_css_classes_removed(components_css: str) -> None:
    """The four `.item-card__sid` / `.item-card__title-row` /
    `.item-card__title-sep` / `.item-card__title` rule bodies must be
    deleted (we accept the retirement comments that mention the class
    names in prose — but not active CSS rule bodies)."""
    for selector_rule in (
        r"^\.item-card__sid\s*\{",
        r"^\.item-card__title-row\s*\{",
        r"^\.item-card__title-sep\s*\{",
        r"^\.item-card__title\s*\{",
    ):
        assert not re.search(selector_rule, components_css, flags=re.MULTILINE), (
            f"components.css still has an active rule body for {selector_rule!r} "
            "— spec 0172 deletes the dead Issue-title-row CSS along with the JSX"
        )


def test_composed_css_clean(composed_css: str) -> None:
    """The DS-canonical stylesheet never carried these classes; assert that
    stays true (a future spec could only add them to the DS copy if they
    came back as a real primitive)."""
    for selector in (
        ".item-card__sid",
        ".item-card__title-row",
        ".item-card__title-sep",
    ):
        assert selector not in composed_css, (
            f"DS composed-components.css unexpectedly contains `{selector}`"
        )


def test_comment_body_lifecycle_leads(jsx: str) -> None:
    """`ItemCardCommentBody` matches `ItemCardIssueBody`'s shape post-spec-0205
    (Bug 2): body renders via `<ItemCardLifecycleSection />`; the standalone
    `<Markdown text={String(item.body)}/>` block is gone (lifecycle's raise
    row already carries `item.body` as its quote, so the standalone block
    was a duplicate)."""
    match = re.search(
        r"function ItemCardCommentBody\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx,
        flags=re.DOTALL,
    )
    assert match is not None, "ItemCardCommentBody function body not located"
    fn_body = match.group("body")
    assert "ItemCardLifecycleSection" in fn_body, (
        "ItemCardCommentBody must render <ItemCardLifecycleSection /> as the "
        "body (spec 0205 Bug 2 — lifecycle leads)"
    )
    assert "<Markdown text={String(item.body)}" not in fn_body, (
        "ItemCardCommentBody still has a standalone <Markdown text={String(item.body)}/> "
        "block above lifecycle (spec 0205 Bug 2 — lifecycle's raise row "
        "already carries item.body; standalone block is a duplicate)"
    )
