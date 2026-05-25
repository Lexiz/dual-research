"""Spec 0213 §2.2 + §4 — source-pattern test on the JS bootstrap's
``STAGE_DEFS`` array.

UI doctrine (spec 0206): assert the *post-fix* anatomy via a positive regex
AND the *pre-fix* anatomy is absent via an antipodal regex. Catches a
silent regression where someone restores the 11-row single-event-per-stage
layout without also updating the corresponding ``STAGES`` table on the
Python side.
"""

from __future__ import annotations

from tests._ui_pattern_helpers import assert_jsx_contains, assert_jsx_lacks


def _bootstrap_src() -> str:
    from scripts.spec_lifecycle.render_dashboard import DASHBOARD_BOOTSTRAP_JS
    return DASHBOARD_BOOTSTRAP_JS


# Post-fix shape — three-element tuples `[name, start_event, end_event]`.
# Pin the exact row strings so a future rename of any single event surfaces
# here as a test diff, not as a silent dashboard regression.
POSITIVE_ROW_PATTERNS = (
    r"\[\s*'Pre-flight',\s*'cycle_started',\s*'preflight_ok'\s*\]",
    r"\[\s*'Read & plan',\s*'handoff_read',\s*'reconcile_complete'\s*\]",
    r"\[\s*'Implement',\s*'branched',\s*'implement_complete'\s*\]",
    r"\[\s*'Test',\s*'tests_started',\s*'tests_green'\s*\]",
    r"\[\s*'Ship',\s*'pr_opened',\s*'merged'\s*\]",
    r"\[\s*'Deploy',\s*'merged',\s*'deployed'\s*\]",
    r"\[\s*'Handoff',\s*'deployed',\s*'handoff_written'\s*\]",
)


def test_bootstrap_stage_defs_has_seven_span_rows() -> None:
    """Each of the seven post-spec-0213 rows appears as a 3-element tuple."""
    src = _bootstrap_src()
    for pat in POSITIVE_ROW_PATTERNS:
        assert_jsx_contains(
            src, pat,
            msg=f"missing post-0213 STAGE_DEFS row: {pat!r}",
        )


# Antipodal absence — the pre-0213 row labels and the two-element-tuple
# shape must not survive. If any of these strings appears as a STAGE_DEFS
# row, the 11-row single-event-per-stage layout has snuck back in.
ANTIPODAL_PATTERNS = (
    # Old standalone row names.
    r"\[\s*'Read handoff',",
    r"\[\s*'Read spec',",
    r"\[\s*'Branch',",
    r"\[\s*'PR',\s*'pr_opened'\s*\]",
    r"\[\s*'Merge',\s*'merged'\s*\]",
    # Two-element-tuple shape: ['Name', 'event_name'] with no third element.
    # Match a row that ends with a single quoted event then `]` — the
    # post-0213 rows always have a comma + second quoted event before `]`.
    r"\[\s*'Pre-flight',\s*'preflight_ok'\s*\]",
)


def test_bootstrap_stage_defs_lacks_pre_0213_row_shapes() -> None:
    """Old 11-row labels and the two-tuple shape must not appear."""
    src = _bootstrap_src()
    for pat in ANTIPODAL_PATTERNS:
        assert_jsx_lacks(
            src, pat,
            msg=f"pre-0213 STAGE_DEFS pattern leaked back in: {pat!r}",
        )


def test_bootstrap_compute_stages_uses_span_indices() -> None:
    """`computeStages` must index `def[2]` (end_event) for the done check.
    Pre-0213 the bootstrap indexed `def[1]` — that path is gone."""
    src = _bootstrap_src()
    # Positive: the done-check accesses index 2 (end_event).
    assert_jsx_contains(
        src, r"STAGE_DEFS\[i\]\[2\]\s+in\s+byStep",
        msg="computeStages must check end_event via STAGE_DEFS[i][2] post-0213",
    )
    # Positive: the start-event read happens.
    assert_jsx_contains(
        src, r"var\s+startKey\s*=\s*def\[1\]\s*,\s*endKey\s*=\s*def\[2\]",
        msg="computeStages must destructure (startKey, endKey) from STAGE_DEFS rows",
    )
