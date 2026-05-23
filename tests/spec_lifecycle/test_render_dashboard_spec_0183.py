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
    # 2 current drafts + 2 recent promotions = 4 total drafts in window.
    # Spec 0183 fixed the denominator (was just `promoted_recent`, now
    # `current_drafts + promoted_recent`). Spec 0196 then fixed the
    # numerator (was `queued_recent`, now `promoted_recent`). With this
    # fixture the corrected math is 2 promoted / 4 total = 50%. The
    # pre-spec-0196 math happened to also produce 50% here because all
    # queued specs in this fixture are promoted ones (2/4 = 2/4) — the
    # sharper guard for the numerator bug lives in
    # test_authoring_funnel_promo_pct_excludes_direct_queue_specs below.
    drafts = [_draft("020"), _draft("021")]
    recent_iso = (NOW - dt.timedelta(days=5)).isoformat()
    specs = [
        _promoted_spec("0300", "030", recent_iso),
        _promoted_spec("0301", "031", recent_iso),
    ]
    html = _render_authoring_funnel(specs, drafts, NOW)
    # Sub-line should mention "50% reached queue"
    assert "50% reached queue" in html, (
        f"promo_pct must use promoted_recent / (current_drafts + "
        f"promoted_recent) (50% in this fixture). Sub-line was:\n"
        f"{html[-600:]}"
    )


def _direct_queue_spec(num: str, queued_at_iso: str) -> SpecRow:
    """Spec 0196 — a spec authored directly via /spec-queue, with no
    draft step. `promoted_from_draft` is empty; the spec lands at
    status=queued without ever passing through the draft funnel."""
    return SpecRow(
        fm={
            "kind": "dev",
            "spec": num,
            "status": "queued",
            "queued_at": queued_at_iso,
            "promoted_from_draft": "",  # the load-bearing field
        },
        path=Path(f"/tmp/specs/{num}-direct.md"),
    )


def test_authoring_funnel_promo_pct_excludes_direct_queue_specs():
    """Spec 0196 — direct-queue specs (those authored via /spec-queue
    without a draft) must NOT pull the promo_pct numerator up. Before
    the fix, the numerator was `queued_recent` which counts ALL queued
    specs in the window, including direct-queue ones — producing
    nonsense like '538% reached queue' on the live repo.

    Fixture: 1 current draft + 1 promoted spec + 5 direct-queue specs
    in the window. Total in draft funnel: 1 backlog + 1 promoted = 2.
    Promoted in window: 1. Expected promo_pct: 1/2 = 50%.

    Pre-fix this would render `300% reached queue` (6 queued / 2 in
    draft funnel = 300%). Post-fix: 50%.
    """
    drafts = [_draft("100")]
    recent_iso = (NOW - dt.timedelta(days=7)).isoformat()
    specs = [
        _promoted_spec("0500", "100-promoted", recent_iso),
        _direct_queue_spec("0501", recent_iso),
        _direct_queue_spec("0502", recent_iso),
        _direct_queue_spec("0503", recent_iso),
        _direct_queue_spec("0504", recent_iso),
        _direct_queue_spec("0505", recent_iso),
    ]
    html = _render_authoring_funnel(specs, drafts, NOW)
    assert "50% reached queue" in html, (
        f"promo_pct numerator must be `promoted_recent` (1), not "
        f"`queued_recent` (6). Pre-fix this fixture rendered "
        f"`300% reached queue`. Sub-line was:\n{html[-600:]}"
    )
    # Belt-and-suspenders: assert the broken pre-fix value is NOT present.
    assert "300% reached queue" not in html
    # And no other nonsense values.
    assert "% reached queue" in html
    import re
    pct_match = re.search(r"(\d+)% reached queue", html)
    assert pct_match is not None
    assert 0 <= int(pct_match.group(1)) <= 100, (
        f"promo_pct must be bounded in [0, 100]; got "
        f"{pct_match.group(1)}% in sub-line."
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
