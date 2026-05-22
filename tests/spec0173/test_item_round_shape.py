"""Spec 0173 §2.2 — upstream `[object Object]` root-cause regression.

Spec 0166 §2.4 shipped a defensive guard in `TlTurnRow` that catches
`typeof item.round !== 'number'` and substitutes a SystemChip + ErrorChip
pair. The upstream code path that handed an object into `item.round`
was deferred at the time. The anchor was the deadlock fall-through in
`live-data.jsx`'s `buildLiveTimeline`, which pushed
`{ kind: 'deadlock', round: run.round, ... }` — but `run.round` is the
structured `{ current, total }` object (read everywhere else via
`run.round?.current`), not a scalar round index.

This test is structural — a regex pass over `live-data.jsx` that
asserts:

1. Every literal `round:` assignment is either a numeric for-loop
   counter (`r`, `cur`), a `?.current`-unwrapped value, or wrapped in
   the `(run.round && typeof run.round === 'object') ? … : …` guard
   the §2.2 fix introduced. No bare `round: run.round`.

2. The narrow `(run.round && typeof run.round === 'object')` guard is
   present at the deadlock branch — the spec's specific fix point.

A behavioural test would need a JS runtime; the structural guard is
the cheap version that survives in pytest. The defensive
`activityLabelError` branch at run-detail.jsx:~1167 stays as the
runtime safety net.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


LIVE_DATA = (
    Path(__file__).parent.parent.parent
    / "src"
    / "dual_research"
    / "ui"
    / "static"
    / "live-data.jsx"
)


@pytest.fixture(scope="module")
def js() -> str:
    return LIVE_DATA.read_text()


def test_no_bare_round_run_round_assignment(js: str) -> None:
    """No literal `round: run.round,` assignment remains — that pattern
    handed an object into `item.round` and broke the cross-review turn
    cards on the anchor run.
    """
    # Match `round: run.round` followed by anything that isn't `.` or
    # `?` (which would denote `run.round.current` / `run.round?.current`).
    bare = re.findall(r"round:\s*run\.round(?![.?\w])", js)
    assert bare == [], (
        "spec 0173 §2.2 regression: at least one `round: run.round` "
        "assignment in live-data.jsx hands the structured object into a "
        f"scalar field. Matches: {bare}"
    )


def test_deadlock_branch_unwraps_run_round_to_scalar(js: str) -> None:
    """The deadlock card's `round:` value must be an unwrapped scalar.
    Either the `(typeof run.round === 'object') ? run.round.current : …`
    guard, or `run.round?.current`, is acceptable. A bare `run.round`
    is not.
    """
    # Find the `kind: 'deadlock'` block and inspect its `round:` value.
    m = re.search(
        r"kind:\s*['\"]deadlock['\"][^}]*?round:\s*([^,}]+)",
        js,
        re.DOTALL,
    )
    assert m is not None, "deadlock card not found in live-data.jsx"
    round_expr = m.group(1).strip()
    assert (
        "run.round?.current" in round_expr
        or ("typeof" in round_expr and "object" in round_expr and "current" in round_expr)
    ), (
        "spec 0173 §2.2 regression: the deadlock card's `round:` field "
        f"must unwrap `run.round` to a scalar. Found: {round_expr!r}"
    )


def test_defensive_guard_in_tl_turn_row_still_present() -> None:
    """The spec 0166 §2.4 safety net at `TlTurnRow` stays — spec 0173
    §2.2 fixed the upstream symptom but the guard is the canonical
    last line of defence for any future regression. Spec body: "After
    the upstream bug is fixed, the defensive guard at §2.4 still ships
    — it's a safety net for future regressions. The guard does not
    get removed."
    """
    run_detail = (
        Path(__file__).parent.parent.parent
        / "src"
        / "dual_research"
        / "ui"
        / "static"
        / "run-detail.jsx"
    )
    source = run_detail.read_text()
    # Two anchors that together prove the guard branch is intact:
    # 1) the `typeof item.round === 'number'` discriminator
    # 2) the `activityLabelError` assignment for the non-number fall-through
    assert "typeof item.round === 'number'" in source, (
        "spec 0166 §2.4 defensive guard missing from TlTurnRow"
    )
    assert "activityLabelError" in source, (
        "spec 0166 §2.4 ErrorChip fall-through missing from TlTurnRow"
    )
