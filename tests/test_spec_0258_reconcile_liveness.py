"""Spec 0258 — reconciler citation-liveness reporting check.

Exercises the `unreachable` reporting overlay added to
`scripts.spec_lifecycle.reconcile` against the REAL `src/dual_research/` tree
(not a fixture stub): the reachability index is built from live source, so a
fixture that drifts dead/live with the codebase is caught here.

stdlib + pytest only — no Playwright, no DOM rendering (this is logic, not UI).
"""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.reconcile import (
    UNREACHABLE_NOTE,
    format_report,
    main,
    reconcile_spec,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# A still-on-disk legacy runner, dead since the spec-0118 v2 rewrite and
# unreachable from the live entry points (replaced by `run_dr_phase1`).
DEAD_SURFACE = "src/dual_research/orchestrator/phase1.py:30"  # run_phase1
# A live entry point itself.
LIVE_ENTRY = "src/dual_research/orchestrator/dr_run.py:1015"  # run_dr_phase2
# Reached from a live entry point.
LIVE_REACHED = "src/dual_research/orchestrator/dr_run.py:602"  # _format_standing_items
# A non-.py citation — never analysed.
NON_PY = "src/dual_research/ui/static/components.css:5"


def _write_spec(tmp_path: Path, section_2_citations: list[str]) -> Path:
    """Write a synthetic spec whose `## 2` cites the given file:line strings."""
    cites = "\n".join(f"- `{c}`" for c in section_2_citations)
    text = (
        "---\n"
        'spec: "9999"\n'
        "kind: dev\n"
        "---\n\n"
        "# Spec 9999 — synthetic\n\n"
        "## 1. Context\n\n"
        "Background prose with no citations.\n\n"
        "## 2. Proposed change\n\n"
        f"{cites}\n\n"
        "## 3. Out of scope\n\n"
        "Nothing.\n"
    )
    spec = tmp_path / "9999-synthetic.md"
    spec.write_text(text)
    return spec


def _unreachable_paths(report) -> set[str]:
    return {f"{c.path}:{c.line}" for c in report.unreachable}


def test_dead_surface_citation_is_flagged_unreachable(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, [DEAD_SURFACE])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    flagged = _unreachable_paths(report)
    assert DEAD_SURFACE in flagged, (
        f"{DEAD_SURFACE} (run_phase1, a dead legacy runner) should be flagged; "
        f"got {flagged}"
    )
    # The dead-surface note must be attached.
    note = next(c.note for c in report.unreachable if f"{c.path}:{c.line}" == DEAD_SURFACE)
    assert note == UNREACHABLE_NOTE


def test_live_entry_point_citation_is_not_flagged(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, [LIVE_ENTRY])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    assert LIVE_ENTRY not in _unreachable_paths(report), (
        "run_dr_phase2 is a live entry point and must never be flagged"
    )


def test_reached_from_live_entry_point_is_not_flagged(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, [LIVE_REACHED])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    assert LIVE_REACHED not in _unreachable_paths(report), (
        "_format_standing_items is reached from a live entry point and must not be flagged"
    )


def test_overlay_is_reporting_not_gating(tmp_path: Path) -> None:
    """The unreachable overlay never gates: no blocking drift, CLI exit unchanged."""
    spec = _write_spec(tmp_path, [DEAD_SURFACE])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    # Overlay populated...
    assert report.unreachable, "expected the dead-surface citation in the overlay"
    # ...yet it contributes nothing to blocking drift.
    assert report.has_blocking_drift is False
    assert report.has_drift is False
    # ...and the citation stays in `clean` (orthogonal overlay, not reclassification).
    assert DEAD_SURFACE in {f"{c.path}:{c.line}" for c in report.clean}
    # ...and the CLI exit code is 0 (unchanged by the overlay).
    assert main([str(spec), str(REPO_ROOT)]) == 0


def test_non_py_citation_is_never_flagged(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, [NON_PY, DEAD_SURFACE])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    flagged = _unreachable_paths(report)
    assert NON_PY not in flagged, "a .css citation must never be flagged unreachable"
    # The .py dead surface alongside it is still flagged — guards against the
    # filter accidentally dropping the whole batch.
    assert DEAD_SURFACE in flagged


def test_citation_outside_section_2_is_not_flagged(tmp_path: Path) -> None:
    """Liveness is scoped to `## 2`; a dead-surface citation in `## 1` is ignored."""
    text = (
        "---\n"
        'spec: "9999"\n'
        "kind: dev\n"
        "---\n\n"
        "# Spec 9999 — synthetic\n\n"
        "## 1. Context\n\n"
        f"- `{DEAD_SURFACE}`\n\n"  # dead surface, but in §1
        "## 2. Proposed change\n\n"
        f"- `{LIVE_ENTRY}`\n\n"  # only a live citation in §2
        "## 3. Out of scope\n\n"
        "Nothing.\n"
    )
    spec = tmp_path / "9999-synthetic.md"
    spec.write_text(text)
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    assert DEAD_SURFACE not in _unreachable_paths(report), (
        "a dead-surface citation outside §2 must not be flagged"
    )


def test_format_report_renders_unreachable_block(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, [DEAD_SURFACE])
    report = reconcile_spec(spec, repo_root=REPO_ROOT)
    rendered = format_report(report)
    assert "unreachable (informational): 1" in rendered
    assert DEAD_SURFACE in rendered
