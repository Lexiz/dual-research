"""Spec 0183 — authoring funnel DRAFTS bucket counts current backlog.

Before the fix, `_render_authoring_funnel` only received `specs` and
computed `drafts_count = promoted_recent`. A repo with N unpromoted
drafts and zero recent promotions read as `0` — falsely implying no
authoring activity. The fix threads `drafts` through the function chain
(render_index → _render_metrics → _render_authoring_funnel) and uses
`current_drafts + promoted_recent` as the bucket count.
"""
import datetime as dt
from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    DraftRow,
    SpecRow,
    _render_authoring_funnel,
)


NOW = dt.datetime(2026, 5, 22, 12, 0, 0, tzinfo=dt.timezone.utc)


def _draft(num: str) -> DraftRow:
    return DraftRow(
        fm={"kind": "draft", "title": f"Draft {num}"},
        path=Path(f"/tmp/specs/drafts/draft-{num}-test.md"),
    )


def _promoted_spec(num: str, draft_id: str, queued_at_iso: str) -> SpecRow:
    return SpecRow(
        fm={
            "kind": "dev",
            "spec": num,
            "status": "queued",
            "queued_at": queued_at_iso,
            "promoted_from_draft": draft_id,
        },
        path=Path(f"/tmp/specs/{num}-test.md"),
    )


def _extract_drafts_bucket_count(svg_html: str) -> int:
    """Parse the rendered SVG and pull the DRAFTS count.

    The bucket is rendered as a <text> sibling of '>DRAFTS<' carrying
    the count as inner text. Source: render_dashboard.py:1290-1292.
    """
    import re

    # Find DRAFTS label then the count <text> that follows.
    m = re.search(r'>DRAFTS</text>\s*<text[^>]*>(\d+)</text>', svg_html)
    assert m, f"DRAFTS count text not found in:\n{svg_html[:600]}"
    return int(m.group(1))


def test_authoring_funnel_drafts_bucket_counts_current_backlog():
    # Three unpromoted drafts on disk, zero recent promotions.
    drafts = [_draft("001"), _draft("002"), _draft("003")]
    specs: list[SpecRow] = []
    html = _render_authoring_funnel(specs, drafts, NOW)
    assert _extract_drafts_bucket_count(html) == 3, (
        "DRAFTS bucket must include unpromoted backlog under specs/drafts/. "
        "Spec 0183 §3.2."
    )


def test_authoring_funnel_drafts_bucket_sums_backlog_and_promotions():
    # Three current drafts + two recent promotions = 5.
    drafts = [_draft("004"), _draft("005"), _draft("006")]
    recent_iso = (NOW - dt.timedelta(days=5)).isoformat()
    specs = [
        _promoted_spec("0200", "010", recent_iso),
        _promoted_spec("0201", "011", recent_iso),
    ]
    html = _render_authoring_funnel(specs, drafts, NOW)
    assert _extract_drafts_bucket_count(html) == 5, (
        "DRAFTS bucket must be current backlog (3) + promoted in last 30d (2) = 5. "
        "Spec 0183 §3.2."
    )


def test_authoring_funnel_promo_pct_uses_new_denominator():
    # 2 current drafts + 2 recent promotions = 4 total drafts in window;
    # 2 queued (the 2 promoted specs are status=queued in our fixture)
    # → 50% reached queue (pre-fix this would be 100% because the old
    # denominator was just promoted_recent=2).
    drafts = [_draft("020"), _draft("021")]
    recent_iso = (NOW - dt.timedelta(days=5)).isoformat()
    specs = [
        _promoted_spec("0300", "030", recent_iso),
        _promoted_spec("0301", "031", recent_iso),
    ]
    html = _render_authoring_funnel(specs, drafts, NOW)
    # Sub-line should mention "50% reached queue"
    assert "50% reached queue" in html, (
        f"promo_pct must use (current_drafts + promoted_recent) as the "
        f"denominator (50% in this fixture, not 100%). Sub-line was:\n"
        f"{html[-600:]}"
    )


def test_authoring_funnel_no_double_counting():
    # By construction (CLAUDE.md spec workflow: /spec-promote deletes the
    # draft file), a promoted draft has no file under specs/drafts/, so
    # the two halves of drafts_count are disjoint. We assert the SUM is
    # exact — not the union with dedup.
    drafts = [_draft("100")]
    recent_iso = (NOW - dt.timedelta(days=10)).isoformat()
    # The "100" draft was hypothetically promoted to spec 0400, but in
    # the real workflow the draft file would be deleted. We pass both
    # to confirm the function sums without dedup (the data invariant
    # is enforced upstream by /spec-promote).
    specs = [_promoted_spec("0400", "100", recent_iso)]
    html = _render_authoring_funnel(specs, drafts, NOW)
    assert _extract_drafts_bucket_count(html) == 2, (
        "Sum semantics: 1 current draft + 1 promoted = 2. Dedup is "
        "the data layer's job (per /spec-promote), not the funnel's."
    )


def test_authoring_funnel_empty_state_when_no_activity():
    # Zero drafts, zero promotions, zero in-flight, zero deployed →
    # the empty-state branch fires.
    html = _render_authoring_funnel([], [], NOW)
    assert "No spec authoring activity" in html, (
        "Empty-state branch must fire when every bucket is zero. "
        "Spec 0183 §3.4."
    )
