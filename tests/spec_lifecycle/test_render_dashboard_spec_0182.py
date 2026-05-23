"""Spec 0182 — bootstrap timeline must compute per-stage durations.

Before the fix, the inline `computeStages` JS function in
`DASHBOARD_BOOTSTRAP_JS` returned only `{ name, status, ev }`, and
`renderTimeline` hard-coded `—` for every `.tl__dur` cell. Every 5s
`/api/data` repaint therefore wiped the server-rendered per-stage
durations from completed stages.

These source-substring tests lock the lexical evidence of the fix.
A future refactor that drops `duration_seconds` or `_fmtDurSecs`
would flag here without needing a JS runtime in the test rig.
"""
from scripts.spec_lifecycle.render_dashboard import DASHBOARD_BOOTSTRAP_JS


def test_bootstrap_compute_stages_returns_duration_seconds():
    # The duration_seconds key must appear in the object returned by
    # computeStages. Before spec 0182 the literal substring is absent.
    assert "duration_seconds" in DASHBOARD_BOOTSTRAP_JS, (
        "computeStages must return duration_seconds per stage. Without it, "
        "the 5s repaint flips every completed .tl__dur cell back to em-dash "
        "(spec 0182 §3.1)."
    )


def test_bootstrap_render_timeline_uses_fmt_dur_secs():
    # The renderTimeline output must consult _fmtDurSecs to render the
    # duration text (not hard-coded em-dash). Locks the §3.2 wiring.
    assert "_fmtDurSecs" in DASHBOARD_BOOTSTRAP_JS, (
        "renderTimeline must call _fmtDurSecs(s.duration_seconds) for the "
        ".tl__dur cell. Hard-coded em-dash defeats the spec 0182 fix."
    )


def test_bootstrap_compute_stages_anchor_priority_matches_server():
    # Anchor priority must match stages.compute_stages exactly so first
    # paint and repaint don't diverge for historical specs that lack
    # cycle_started. Lock the exact `||` chain.
    assert (
        "byStep['cycle_started'] || byStep['queued'] || byStep['in_progress']"
        in DASHBOARD_BOOTSTRAP_JS
    ), (
        "Anchor preference must be cycle_started → queued → in_progress, "
        "in that exact order via the byStep[...]||... chain. Mirrors "
        "stages.py:225-229."
    )


def test_bootstrap_fmt_dur_secs_handles_em_dash_for_null():
    # The helper must render '—' for null / negative (matches the
    # server's _humanize_seconds None branch).
    src = DASHBOARD_BOOTSTRAP_JS
    # We're just checking the source literal — the helper carries the
    # em-dash fallback for queued / fail stages where duration_seconds
    # is null.
    assert "secs == null" in src or "secs === null" in src, (
        "_fmtDurSecs must guard against null/undefined to render em-dash "
        "for queued/fail stages."
    )
