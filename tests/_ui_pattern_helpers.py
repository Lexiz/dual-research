"""UI source-pattern test helpers (spec 0206).

Canonical idiom for source-pattern UI tests: read a JSX / CSS file as text
and assert a positive regex is present (post-fix shape) AND an antipodal
regex is absent (pre-fix shape). See ``design-system/SPEC.md`` §13 for the
doctrine; this module collapses the boilerplate into three functions used
by every UI regression test.

Typical use::

    from tests._ui_pattern_helpers import (
        assert_jsx_contains, assert_jsx_lacks, read_repo_text,
    )

    jsx = read_repo_text("src", "dual_research", "ui", "static", "run-detail.jsx")
    assert_jsx_contains(jsx, r'Mdi name="link-variant"', msg="…")
    assert_jsx_lacks(jsx, r'<Tab variant="kind">', msg="…")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

REPO_ROOT = Path(__file__).resolve().parent.parent

Pattern = Union[str, re.Pattern[str]]


def read_repo_text(*parts: str) -> str:
    """Return ``<REPO_ROOT>/<*parts>`` as UTF-8 text.

    Anchors at the repo root so callers don't have to derive paths from
    ``__file__`` per-test.
    """
    return REPO_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _compile(pattern: Pattern, flags: int = 0) -> re.Pattern[str]:
    if isinstance(pattern, re.Pattern):
        return pattern
    return re.compile(pattern, flags)


def assert_jsx_contains(
    text: str,
    pattern: Pattern,
    *,
    msg: str,
    flags: int = 0,
) -> re.Match[str]:
    """Assert ``pattern`` matches somewhere in ``text`` (post-fix anatomy).

    Returns the match so callers can chain further checks against the
    captured groups. On failure, raises ``AssertionError`` with ``msg``
    plus a short tail of ``text`` for context.
    """
    rx = _compile(pattern, flags)
    m = rx.search(text)
    if m is None:
        tail = text[-400:] if len(text) > 400 else text
        raise AssertionError(
            f"{msg}\n"
            f"  expected pattern: {rx.pattern!r}\n"
            f"  not found in {len(text)}-char text\n"
            f"  …tail: {tail!r}"
        )
    return m


def assert_jsx_lacks(
    text: str,
    pattern: Pattern,
    *,
    msg: str,
    flags: int = 0,
) -> None:
    """Assert ``pattern`` does NOT match anywhere in ``text`` (pre-fix shape is gone).

    On failure, raises ``AssertionError`` with ``msg`` plus the captured
    snippet so the regression is visible in test output.
    """
    rx = _compile(pattern, flags)
    m = rx.search(text)
    if m is not None:
        snippet = m.group(0)
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        raise AssertionError(
            f"{msg}\n"
            f"  forbidden pattern still present: {rx.pattern!r}\n"
            f"  matched snippet: {snippet!r}"
        )
