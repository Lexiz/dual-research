"""Spec 0185 — cycle-time line chart Y-axis cap (percentile-based / auto-ranged).

Covers § 4 (test plan) of `specs/0185-cycle-time-chart-percentile-y-axis-cap.md`:
helper behaviour (`_pick_cap`, `_nice_round_cap`, `_format_y_tick`) and end-to-end
rendering of `_render_cycle_time_chart` for the three repo shapes called out in
the spec — bootstrap (sub-10m), outlier-laden, and the 60m baseline.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    SpecRow,
    _format_y_tick,
    _nice_round_cap,
    _pick_cap,
    _render_cycle_time_chart,
)


def _row(number: str, cycle_secs: int) -> SpecRow:
    """SpecRow whose `cycle_seconds` property yields ``cycle_secs`` exactly.

    Uses a fixed `started_at` and a `deployed_at` offset by `cycle_secs` so the
    `_parse_ts` round-trip lands on the same int.
    """
    started_min = cycle_secs // 60
    started_sec = cycle_secs % 60
    deployed_str = f"2026-05-01T10:{started_min:02d}:{started_sec:02d}Z"
    fm = {
        "started_at": "2026-05-01T10:00:00Z",
        "deployed_at": deployed_str,
    }
    return SpecRow(fm=fm, path=Path(f"specs/{number}-fixture.md"))


# ── helper unit tests (Step 1 of the spec's stepwise migration) ───────────────


def test_pick_cap_floors_at_10m_for_short_cycles() -> None:
    """Bootstrap-repo guard: when every cycle is well under 10m, the cap stays
    at 10m so the chart isn't 80% empty whitespace."""
    cycle_secs = [120, 180, 240, 300, 360]  # 2m, 3m, 4m, 5m, 6m
    assert _pick_cap(cycle_secs) == 600


def test_pick_cap_returns_p95_above_floor() -> None:
    """When p95 is well above 10m, the cap follows p95 (not the floor)."""
    # Eighteen 30m cycles + two 50m outliers. p95 interpolates near 50m, well
    # above the 10m floor.
    cycle_secs = [30 * 60] * 18 + [50 * 60] * 2
    cap = _pick_cap(cycle_secs)
    assert cap > 600
    assert cap <= 50 * 60


def test_pick_cap_returns_floor_for_empty_input() -> None:
    """Defensive: zero-cycle repos shouldn't crash the helper; renderer
    short-circuits before this branch but the helper is still robust."""
    assert _pick_cap([]) == 600


def test_pick_cap_handles_single_value() -> None:
    """Single-cycle repos: cap is max(value, floor)."""
    assert _pick_cap([90]) == 600  # 1.5m below floor → floor wins
    assert _pick_cap([45 * 60]) == 45 * 60  # 45m above floor → value wins


def test_nice_round_cap_rounds_up_to_next_nice_minute() -> None:
    """Cap snaps to the nearest nice value in {10, 15, 20, 30, 45, 60, 90, 120}."""
    assert _nice_round_cap(0) == 10 * 60
    assert _nice_round_cap(600) == 10 * 60  # exactly 10m → 10m
    assert _nice_round_cap(601) == 15 * 60  # 10m + 1s → 15m
    assert _nice_round_cap(11 * 60) == 15 * 60
    assert _nice_round_cap(20 * 60) == 20 * 60
    assert _nice_round_cap(25 * 60) == 30 * 60
    assert _nice_round_cap(50 * 60) == 60 * 60
    assert _nice_round_cap(110 * 60) == 120 * 60


def test_nice_round_cap_clamps_above_120m() -> None:
    """Values larger than 120m clamp to 120m — outliers above clip at the top."""
    assert _nice_round_cap(180 * 60) == 120 * 60
    assert _nice_round_cap(10000 * 60) == 120 * 60


def test_format_y_tick_zero_returns_0() -> None:
    """The bottom tick is rendered as bare '0' (no 'm' suffix) to match the
    spec-0177 baseline."""
    assert _format_y_tick(60 * 60, 0.0) == "0"
    assert _format_y_tick(20 * 60, 0.0) == "0"


def test_format_y_tick_integer_minute() -> None:
    """For caps where fraction × cap lands on a whole minute, the label is
    '{N}m' with no seconds remainder."""
    assert _format_y_tick(60 * 60, 1.0) == "60m"
    assert _format_y_tick(60 * 60, 0.75) == "45m"
    assert _format_y_tick(60 * 60, 0.5) == "30m"
    assert _format_y_tick(60 * 60, 0.25) == "15m"
    assert _format_y_tick(20 * 60, 0.25) == "5m"
    assert _format_y_tick(120 * 60, 0.5) == "60m"


def test_format_y_tick_non_round_minute_includes_seconds() -> None:
    """Caps like 10m / 15m / 30m / 45m at the 25%/50%/75% ticks produce
    sub-minute remainders; the format preserves them as '{N}m {S}s'."""
    assert _format_y_tick(10 * 60, 0.25) == "2m 30s"
    assert _format_y_tick(15 * 60, 0.25) == "3m 45s"
    assert _format_y_tick(30 * 60, 0.25) == "7m 30s"


# ── _render_cycle_time_chart integration tests (Step 2) ────────────────────────


def test_cycle_time_chart_cap_picks_p95_with_floor() -> None:
    """Spec §4: fixture with sub-10m cycles asserts the rendered top label
    is '10m' (the floor wins over a sub-10m p95). Before this refactor the
    top label was always '60m'."""
    deployed = [_row(f"010{i}", secs) for i, secs in enumerate([120, 180, 240, 300, 360])]
    html = _render_cycle_time_chart(deployed)
    assert ">10m</text>" in html
    assert ">60m</text>" not in html


def test_cycle_time_chart_cap_clips_outliers_above_p95() -> None:
    """Spec §4: 19 cycles at 5m + 1 outlier at 55m. The cap nice-rounds to a
    small value (≤ 60m) and the caption notes 1 clipped outlier."""
    deployed = [_row(f"02{i:02d}", 5 * 60) for i in range(19)]
    deployed.append(_row("0299", 55 * 60))
    html = _render_cycle_time_chart(deployed)
    # The cap should be nice-rounded and well below the outlier — the spec
    # author noted "15m or 20m" as the likely nice-rounded p95.
    assert ">10m</text>" in html or ">15m</text>" in html or ">20m</text>" in html
    # Outlier note carries the (1) count + the dynamic cap minute value.
    assert "Outliers &gt;" in html or "Outliers >" in html
    assert "(1)" in html
    assert "clipped to the top" in html


def test_cycle_time_chart_cap_for_60m_repos_unchanged() -> None:
    """Spec §4: the spec-0177 baseline case — cycles spread across 10–60m —
    still nice-rounds to 60m so the chart looks identical to pre-refactor."""
    deployed = [
        _row(f"03{i:02d}", n * 60)
        for i, n in enumerate([10, 20, 30, 40, 50, 60])
    ]
    html = _render_cycle_time_chart(deployed)
    assert ">60m</text>" in html
    assert ">45m</text>" in html
    assert ">30m</text>" in html
    assert ">15m</text>" in html
    assert ">0</text>" in html


def test_cycle_time_chart_outlier_note_uses_dynamic_cap_minutes() -> None:
    """The outlier-note prose interpolates the dynamic cap minute count rather
    than the old constant string 'Outliers > 1h'."""
    # 19 sub-10m cycles + 1 outlier → cap is 10m, outlier note says '> 10m'.
    deployed = [_row(f"04{i:02d}", 4 * 60) for i in range(19)]
    deployed.append(_row("0499", 30 * 60))
    html = _render_cycle_time_chart(deployed)
    assert "&gt; 10m" in html or "> 10m" in html
    assert "1h" not in html.split("clipped to the top")[0]  # old prose gone


def test_cycle_time_chart_preserves_label_anchor_and_offset() -> None:
    """Regression guard: the Y-axis labels keep `text-anchor="end"` (via the
    enclosing <g>) and the same x-offset `pad_l - 6 = 34` for visual parity
    with the pre-refactor layout."""
    deployed = [_row(f"05{i:02d}", n * 60) for i, n in enumerate([10, 20, 30, 40, 50, 60])]
    html = _render_cycle_time_chart(deployed)
    # text-anchor lives on the enclosing <g> (one place, not five) and the
    # five <text> elements all sit at x=34 (pad_l 40 minus 6).
    assert 'text-anchor="end"' in html
    assert html.count('<text x="34"') == 5
