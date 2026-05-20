"""Spec 0120 §5.3.1 — behavioural sync test for the JS title/rationale splitter.

The JS helper at ``src/dual_research/ui/static/item-body.js`` exposes
``splitTitleAndRationale(body)``. There is no Python source-of-truth to
mirror it against (it's a pure UI-side parser of a soft prompt
convention), so this test:

  1. Grep-asserts the canonical regex literal is present in the JS file
     (a drift signal — if someone changes the regex, this test
     forces them to update the spec text below too).
  2. Re-implements the same logic in Python using the same regex and
     exercises the 5 cases enumerated in spec 0120 §8.

Both checks together guard the function against regression without
needing a JS test runner.
"""

from __future__ import annotations

import re
from pathlib import Path


_JS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "dual_research"
    / "ui"
    / "static"
    / "item-body.js"
)


# The regex inside the JS helper, ported verbatim. JS and Python share
# this regex syntax exactly (anchors, groups, escapes, `\s`).
_TITLE_RE = re.compile(r"^\s*\*\*(.+)\*\*\s*$")
_ANCHOR_LINE_RE = re.compile(r"^\s*>\s*(?:quote|after)\s*:", re.IGNORECASE)


def _strip_anchor_lines(body: str) -> str:
    """Python port of ``window.DrItemBody.stripAnchorLines``."""
    if not isinstance(body, str) or len(body) == 0:
        return ""
    return "\n".join(
        line for line in body.split("\n") if not _ANCHOR_LINE_RE.match(line)
    )


def _split_title_and_rationale(body: str) -> tuple[str, str]:
    """Python port of ``window.DrItemBody.splitTitleAndRationale``."""
    if not isinstance(body, str) or len(body) == 0:
        return "", ""
    lines = body.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines):
        m = _TITLE_RE.match(lines[i])
        if m:
            title = m.group(1).strip()
            rationale = "\n".join(lines[i + 1 :]).strip()
            return title, rationale
    return "", body.strip()


def test_js_helper_exports_splitter() -> None:
    text = _JS_PATH.read_text(encoding="utf-8")
    assert "function splitTitleAndRationale" in text, (
        "item-body.js must declare splitTitleAndRationale"
    )
    assert "function stripAnchorLines" in text, (
        "item-body.js must declare stripAnchorLines"
    )
    assert "window.DrItemBody" in text, (
        "item-body.js must attach to window.DrItemBody"
    )


def test_strip_anchor_lines_removes_quote_and_after() -> None:
    body = (
        "Body opening line.\n"
        "> quote: \"verbatim span\"\n"
        "> after: ## Heading text\n"
        "More body text.\n"
    )
    stripped = _strip_anchor_lines(body)
    assert "> quote:" not in stripped
    assert "> after:" not in stripped
    assert "Body opening line." in stripped
    assert "More body text." in stripped


def test_strip_anchor_lines_keeps_unrelated_blockquotes() -> None:
    # Only ``> quote:`` and ``> after:`` are stripped — generic
    # blockquotes survive.
    body = "> regular blockquote\n> quote: anchor target\n> another quote"
    stripped = _strip_anchor_lines(body)
    assert "> regular blockquote" in stripped
    assert "> another quote" in stripped
    assert "> quote: anchor target" not in stripped


def test_strip_anchor_lines_empty() -> None:
    assert _strip_anchor_lines("") == ""


def test_js_uses_canonical_regex() -> None:
    """If this assertion fails, the JS regex has drifted from the spec.

    Update both the JS file AND the Python port in this test file in
    lockstep — and bump the spec text to match.
    """
    text = _JS_PATH.read_text(encoding="utf-8")
    assert r"^\s*\*\*(.+)\*\*\s*$" in text, (
        "item-body.js must use the canonical /^\\s*\\*\\*(.+)\\*\\*\\s*$/ "
        "regex to identify the title line"
    )


def test_well_formed_title_and_body() -> None:
    title, rationale = _split_title_and_rationale(
        "**Title here**\n\nBody text."
    )
    assert title == "Title here"
    assert rationale == "Body text."


def test_missing_title_returns_full_body_as_rationale() -> None:
    body = "Plain question text without a bold title.\nSecond line."
    title, rationale = _split_title_and_rationale(body)
    assert title == ""
    assert rationale == body


def test_empty_body() -> None:
    assert _split_title_and_rationale("") == ("", "")


def test_title_with_inner_markdown_preserved() -> None:
    # Inner backticks / italics inside the title should survive — the
    # outer ** wrappers are the only thing stripped.
    title, rationale = _split_title_and_rationale(
        "**Investigate the `claim_id` field**\n\nDetails follow."
    )
    assert title == "Investigate the `claim_id` field"
    assert rationale == "Details follow."


def test_multiple_bold_lines_only_first_is_title() -> None:
    body = "**First title**\n\n**Second bold line**\n\nRationale."
    title, rationale = _split_title_and_rationale(body)
    assert title == "First title"
    assert "Second bold line" in rationale
    assert rationale.endswith("Rationale.")


def test_leading_blank_lines_are_skipped() -> None:
    title, rationale = _split_title_and_rationale(
        "\n\n**Title**\n\nBody."
    )
    assert title == "Title"
    assert rationale == "Body."


def test_non_string_body_is_safe() -> None:
    title, rationale = _split_title_and_rationale(None)  # type: ignore[arg-type]
    assert (title, rationale) == ("", "")
