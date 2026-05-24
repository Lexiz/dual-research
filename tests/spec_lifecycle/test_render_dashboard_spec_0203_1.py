"""Spec 0203.1 — dashboard parity tests.

Covers the §3.4 L-spec sub-progress chip on the in-flight hero, the §3.3
feed-detail branches for the three new events, and the §3.5 bootstrap
mirror tables (existence + new-event entries).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    DASHBOARD_BOOTSTRAP_JS,
    SpecRow,
    _feed_detail,
    _FEED_KICKER,
    _FEED_STEP_ICON,
    _latest_checkpoint_subsection,
    _render_hero_inflight,
)


def _inflight_l_spec(events: list[dict]) -> SpecRow:
    fm = {
        "kind": "dev",
        "spec": "0203",
        "slug": "critique-v2-live-promotion",
        "title": "Critique V2 — live promotion",
        "type": "new-feature",
        "status": "in_progress",
        "complexity": "L",
        "started_at": "2026-05-24T10:00:00Z",
    }
    return SpecRow(fm=fm, path=Path("specs/0203-critique-v2-live-promotion.md"), events=events)


# ── §3.4 — L-spec sub-progress chip on the in-flight hero ─────────────────


def test_hero_inflight_surfaces_lspec_subsection_chip() -> None:
    """When the latest checkpoint says §2.5 with 5 completed subsections,
    the in-flight hero must render a chip stating both numbers AND carry
    the `data-checkpoint-next` attribute the bootstrap reads on repaint."""
    events = [
        {"ts": "2026-05-24T10:00:00Z", "step": "cycle_started", "data": {}},
        {"ts": "2026-05-24T10:00:05Z", "step": "in_progress", "data": {}},
        {"ts": "2026-05-24T10:01:00Z", "step": "branched",
         "data": {"branch": "spec/0203-critique-v2-live-promotion", "from": "main@abc"}},
        {"ts": "2026-05-24T10:01:05Z", "step": "implementing_started", "data": {}},
        {"ts": "2026-05-24T11:00:00Z", "step": "checkpoint_written",
         "data": {
             "path": "handoffs/2026-05-24-spec-0203-critique-v2-live-promotion.md",
             "next_subsection": "2.5",
             "completed_subsections": ["2.1", "2.2", "2.3", "2.4", "2.8"],
         }},
    ]
    spec = _inflight_l_spec(events)
    now = dt.datetime(2026, 5, 24, 12, 0, 0, tzinfo=dt.timezone.utc)
    html = _render_hero_inflight(spec, [spec], now)

    assert "§2.5" in html
    assert "5 subsections done" in html
    assert 'data-checkpoint-next="2.5"' in html
    assert 'data-checkpoint-done="5"' in html


def test_hero_inflight_omits_chip_when_no_checkpoint_event() -> None:
    """A spec mid-implement with no checkpoint must not show the chip."""
    events = [
        {"ts": "2026-05-24T10:00:00Z", "step": "cycle_started", "data": {}},
        {"ts": "2026-05-24T10:00:05Z", "step": "in_progress", "data": {}},
        {"ts": "2026-05-24T10:01:00Z", "step": "branched",
         "data": {"branch": "spec/0203-x"}},
    ]
    spec = _inflight_l_spec(events)
    now = dt.datetime(2026, 5, 24, 12, 0, 0, tzinfo=dt.timezone.utc)
    html = _render_hero_inflight(spec, [spec], now)
    assert "subsections done" not in html
    assert "data-checkpoint-next" not in html


# ── §3.3 — feed-detail branches for the new events ────────────────────────


def test_feed_detail_checkpoint_written() -> None:
    spec = _inflight_l_spec([])
    detail = _feed_detail(
        spec,
        "checkpoint_written",
        {"next_subsection": "2.5", "completed_subsections": ["2.1", "2.2", "2.3", "2.4", "2.8"]},
    )
    assert "§2.5" in detail
    assert "5 done" in detail


def test_feed_detail_resume_started_reads_latest_checkpoint() -> None:
    events = [
        {"ts": "2026-05-24T11:00:00Z", "step": "checkpoint_written",
         "data": {"next_subsection": "2.5", "completed_subsections": ["2.1"]}},
        {"ts": "2026-05-24T11:30:00Z", "step": "resume_started",
         "data": {"from_checkpoint": "handoffs/x.md", "next_subsection": "2.5"}},
    ]
    spec = _inflight_l_spec(events)
    detail = _feed_detail(spec, "resume_started", events[1]["data"])
    assert "resumed at §2.5" in detail


def test_feed_detail_promoted_as_next() -> None:
    spec = _inflight_l_spec([])
    detail = _feed_detail(spec, "promoted_as_next", {"was": "0205", "cascade": 0})
    assert "was 0205" in detail


def test_latest_checkpoint_helper_handles_missing_and_empty() -> None:
    assert _latest_checkpoint_subsection(None) is None
    spec_empty = _inflight_l_spec([])
    assert _latest_checkpoint_subsection(spec_empty) is None


# ── §3.3 — feed icon + kicker tables carry entries for new events ────────


def test_feed_step_icon_table_covers_new_events() -> None:
    assert _FEED_STEP_ICON["checkpoint_written"] == ("bookmark_added", "info")
    assert _FEED_STEP_ICON["resume_started"] == ("replay", "info")
    assert _FEED_STEP_ICON["promoted_as_next"] == ("arrow_upward", "info")


def test_feed_kicker_table_covers_new_events() -> None:
    assert _FEED_KICKER["checkpoint_written"] == "checkpoint"
    assert _FEED_KICKER["resume_started"] == "resumed"
    assert _FEED_KICKER["promoted_as_next"] == "promoted as next"


# ── §3.5 — bootstrap JS mirror tables carry parity for new events ────────


def test_bootstrap_step_labels_mirror_new_events() -> None:
    js = DASHBOARD_BOOTSTRAP_JS
    assert "'checkpoint_written': 'checkpoint'" in js
    assert "'resume_started': 'resuming'" in js
    assert "'promoted_as_next': 'promoted as next'" in js


def test_bootstrap_feed_icon_table_mirrors_new_events() -> None:
    js = DASHBOARD_BOOTSTRAP_JS
    assert "var FEED_STEP_ICON" in js
    assert "'checkpoint_written': ['bookmark_added','info']" in js
    assert "'resume_started':     ['replay',        'info']" in js
    assert "'promoted_as_next':   ['arrow_upward',  'info']" in js


def test_bootstrap_renderHeroInflight_injects_checkpoint_chip() -> None:
    """The bootstrap mirror of the §3.4 chip must carry the same
    data-checkpoint-next attribute the server emits."""
    js = DASHBOARD_BOOTSTRAP_JS
    assert "data-checkpoint-next=" in js
    assert "data-checkpoint-done=" in js
    assert "subsections done" in js
