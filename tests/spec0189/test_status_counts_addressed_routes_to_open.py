"""Spec 0189 — `addressed` status routes into the Open bucket of statusCounts.

Spec 0173 §2.4 introduced the bar-2 status segments (`All · Open · Resolved · Drift`)
on the critique pane. They derive Open / Resolved counts from the `_isOpenStatus`
and `_isResolvedStatus` predicates. Both were defined narrowly: `_isOpenStatus`
matched only `'open' | 'open-new'`, `_isResolvedStatus` matched only `'resolved' |
'answered' | 'resolved-*'`. The `addressed` state — emitted by the item-state
machine for items where the actor has responded but the raiser hasn't yet
conceded / pushed back — matched neither predicate. So `addressed` items showed
in the `All` count but fell out of every per-state count, breaking the
arithmetic invariant `All == Open + Resolved + Drift` that the user can verify
by glance.

The fix at [src/dual_research/ui/static/run-detail.jsx:7123](src/dual_research/ui/static/run-detail.jsx:7123)
widens `_isOpenStatus` to include `'addressed'` — `addressed` is "still open
from the raiser's POV" until the item reaches a terminal state.

This structural test pins the fix: a regex over `run-detail.jsx` asserts
`_isOpenStatus` is defined to include `'addressed'`. It fails before the fix
(predicate omits `addressed`) and passes after.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


RUN_DETAIL = (
    Path(__file__).parent.parent.parent
    / "src"
    / "dual_research"
    / "ui"
    / "static"
    / "run-detail.jsx"
)


@pytest.fixture(scope="module")
def src() -> str:
    return RUN_DETAIL.read_text(encoding="utf-8")


def test_is_open_status_includes_addressed(src: str) -> None:
    """`_isOpenStatus` must include `'addressed'` so the bar-2 Open count covers
    transitional items. Without this, All ≠ Open + Resolved + Drift on any phase
    with a mid-arc item."""
    # Find the `_isOpenStatus = (s) => …` definition line. It must mention
    # `'addressed'` (or `"addressed"`) inside the predicate body.
    match = re.search(
        r"const\s+_isOpenStatus\s*=\s*\(s\)\s*=>\s*([^;]+);",
        src,
    )
    assert match is not None, (
        "Could not locate `_isOpenStatus = (s) => …` predicate in run-detail.jsx. "
        "Has it moved or been renamed?"
    )
    body = match.group(1)
    assert "'addressed'" in body or '"addressed"' in body, (
        f"`_isOpenStatus` body does not mention 'addressed'. Found: {body!r}. "
        "Per spec 0189 the predicate must route `addressed` into the Open bucket."
    )


def test_is_open_status_still_covers_open_and_open_new(src: str) -> None:
    """Regression guard: widening `_isOpenStatus` must keep the existing open
    states. Strips the fix from silently dropping `open` or `open-new`."""
    match = re.search(
        r"const\s+_isOpenStatus\s*=\s*\(s\)\s*=>\s*([^;]+);",
        src,
    )
    assert match is not None
    body = match.group(1)
    assert "'open'" in body or '"open"' in body, (
        f"`_isOpenStatus` no longer matches 'open'. Found: {body!r}."
    )
    assert "'open-new'" in body or '"open-new"' in body, (
        f"`_isOpenStatus` no longer matches 'open-new'. Found: {body!r}."
    )


def test_is_resolved_status_unchanged_does_not_match_addressed(src: str) -> None:
    """`_isResolvedStatus` must NOT match `addressed`. Spec 0189 §6 explicitly
    leaves the Resolved predicate alone — `addressed` is "not yet closed", so
    calling it resolved would be a different bug."""
    match = re.search(
        r"const\s+_isResolvedStatus\s*=\s*\(s\)\s*=>\s*([^;]+?\)\s*\)?;)",
        src,
        flags=re.DOTALL,
    )
    assert match is not None, (
        "Could not locate `_isResolvedStatus = (s) => …` predicate."
    )
    body = match.group(1)
    assert "'addressed'" not in body and '"addressed"' not in body, (
        f"`_isResolvedStatus` unexpectedly matches 'addressed'. Found: {body!r}. "
        "Per spec 0189 §6 the Resolved predicate stays narrow."
    )
