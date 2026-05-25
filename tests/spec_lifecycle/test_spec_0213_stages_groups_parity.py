"""Spec 0213 §2.3 + §4 — `STAGES` (Python) and `_STAGE_GROUPS` (Python)
must produce the same 7 rows with the same `(start_event, end_event)`
pairs in the same order. Drift between them = the metrics chart and the
timeline disagree about what /dev-next did, which is the exact bug
spec 0213 closed. This assertion is the gate that keeps them aligned.
"""

from __future__ import annotations

from scripts.spec_lifecycle.render_dashboard import _STAGE_GROUPS
from scripts.spec_lifecycle.stages import STAGES


def test_stages_and_stage_groups_have_same_seven_labels() -> None:
    """Same row count and labels in the same order."""
    stage_names = [s.name for s in STAGES]
    group_names = [label for label, _token, _pairs in _STAGE_GROUPS]
    assert stage_names == group_names, (
        f"STAGES vs _STAGE_GROUPS label drift:\n"
        f"  STAGES:        {stage_names}\n"
        f"  _STAGE_GROUPS: {group_names}"
    )
    assert len(stage_names) == 7


def test_stages_and_stage_groups_have_same_start_end_pairs() -> None:
    """Each row encodes the same `(start_event, end_event)` pair on both
    sides. The chart and the timeline must measure the exact same span
    when they label a bucket the same name."""
    stage_pairs = [(s.start_event, s.end_event) for s in STAGES]
    group_pairs = []
    for _label, _token, pairs in _STAGE_GROUPS:
        assert len(pairs) == 1, (
            f"post-0213 _STAGE_GROUPS uses a single `start_event→end_event` pair "
            f"per bucket; got {pairs!r}"
        )
        frm, to = pairs[0].split("→")
        group_pairs.append((frm, to))
    assert stage_pairs == group_pairs, (
        f"STAGES vs _STAGE_GROUPS (start, end) drift:\n"
        f"  STAGES:        {stage_pairs}\n"
        f"  _STAGE_GROUPS: {group_pairs}"
    )


def test_chart_tokens_are_distinct() -> None:
    """Each bucket gets its own chart-* token so the stacked bar's palette
    doesn't collapse two adjacent rows into one visual band."""
    tokens = [token for _label, token, _pairs in _STAGE_GROUPS]
    assert len(set(tokens)) == len(tokens), (
        f"_STAGE_GROUPS chart tokens are not distinct: {tokens}"
    )
