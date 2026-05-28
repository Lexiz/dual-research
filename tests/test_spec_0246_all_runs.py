"""Spec 0246 — All Runs card-layout rewrite.

Source-pattern tests (spec 0206 doctrine) lock the page anatomy via
positive-presence + antipodal-absence regexes against the JSX/CSS source,
plus data-layer tests for the additive ``RunListRow`` fields and their
derivation. Runtime rendering is proven via Claude Preview MCP screenshots
in the PR description.
"""

from __future__ import annotations

import dataclasses
import re

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

RUN_LIST = ("src", "dual_research", "ui", "static", "run-list.jsx")
APP = ("src", "dual_research", "ui", "static", "app.jsx")
CSS_LIVE = ("src", "dual_research", "ui", "static", "components.css")
CSS_DS = ("design-system", "assets", "styles", "composed-components.css")

# Every new class the rewrite introduces; the sync test asserts both CSS
# files define each one (project DS-sync rule).
NEW_CLASSES = [
    ".run-card", ".run-card--errored", ".run-card--abandoned",
    ".run-card--completed", ".run-card--running", ".run-card--archived",
    ".rc-status", ".rc-status--errored", ".rc-topic", ".rc-idbdg",
    ".rc-chev", ".rc-live", ".rc-archive-btn", ".rc-phases", ".rc-phase",
    ".rc-phase--done", ".rc-phase--active", ".rc-phase--failed",
    ".rc-phase--abandon", ".rc-phase--pending", ".rc-agent", ".rc-agent--a",
    ".rc-agent--b", ".rc-agent__cost", ".rc-agent__name", ".rc-bdg",
    ".rc-bdg--warn", ".rc-bdg--err", ".rc-bdg--ok", ".rc-bdg--info",
    ".rc-note", ".rc-note--err", ".rc-note--warn", ".rc-note--ok",
    ".ar-chrome", ".ar-tab", ".ar-pill", ".ar-project", ".ar-stats",
    ".ar-stat", ".ar-stat--phase", ".phase-dist", ".ar-filters", ".fchip",
    ".ar-sort", ".ar-group", ".ar-group--warn", ".ar-grid",
]


# ─── Run card anatomy ────────────────────────────────────────────────────


def test_run_card_renders_status_topic_metrics_id():
    jsx = read_repo_text(*RUN_LIST)
    assert_jsx_contains(jsx, r"run-card--errored", msg="errored card modifier missing")
    assert_jsx_contains(jsx, r"rc-status--errored", msg="errored status pill modifier missing")
    assert_jsx_contains(jsx, r'className="rc-topic"', msg="rc-topic missing")
    assert_jsx_contains(jsx, r'rc-meta__l">Started', msg="Started metric cell missing")
    assert_jsx_contains(jsx, r'className="rc-idbdg"', msg="rc-idbdg missing")
    # Antipode — the pre-fix RunRow render component is gone (replaced by RunCard).
    assert_jsx_lacks(jsx, r"function RunRow\(", msg="old RunRow must be replaced by RunCard")


# ─── 5-segment phase strip ───────────────────────────────────────────────


def test_phase_strip_renders_five_cells_with_state_modifiers():
    jsx = read_repo_text(*RUN_LIST)
    for label in ("P1 plan", "P2 nego", "P3 res", "P4 rev", "P5 sum"):
        assert_jsx_contains(jsx, re.escape(label), msg=f"phase label {label!r} missing")
    # The dynamic modifier is built from run.phases — assert the class stem.
    assert_jsx_contains(jsx, r"rc-phase rc-phase--", msg="phase cell class stem missing")
    # All five state modifiers are defined in the authoritative CSS.
    css = read_repo_text(*CSS_DS)
    for mod in ("--done", "--active", "--failed", "--abandon", "--pending"):
        assert_jsx_contains(css, re.escape(f".rc-phase{mod}"), msg=f"CSS .rc-phase{mod} missing")
    # Antipode — the card does NOT consume the shared PhaseMini primitive...
    assert_jsx_lacks(jsx, r"<PhaseMini", msg="RunCard must not consume <PhaseMini>")
    # ...but PhaseMini itself survives for the /#/language showcase.
    assert_jsx_contains(jsx, r"function PhaseMini\(", msg="PhaseMini definition must survive")


# ─── Per-agent rows: Claude on sable, GPT on sage (CSS, both files) ───────


def test_agent_rows_claude_sable_gpt_sage():
    for parts in (CSS_DS, CSS_LIVE):
        css = read_repo_text(*parts)
        assert_jsx_contains(
            css, r"\.rc-agent--a::before\s*\{[^}]*background:\s*var\(--p-sable\)",
            msg=f"Claude sable accent missing in {parts[-1]}",
        )
        assert_jsx_contains(
            css, r"\.rc-agent--b::before\s*\{[^}]*background:\s*var\(--p-sage\)",
            msg=f"GPT sage accent missing in {parts[-1]}",
        )
        # Antipode — agent rules must not inline a 6-digit hex colour.
        assert_jsx_lacks(
            css, r"\.rc-agent[^{]*\{[^}]*#[0-9a-fA-F]{6}",
            msg=f"agent rules must use tokens, not hex, in {parts[-1]}",
        )


# ─── Stats panel aggregates the unfiltered run set ───────────────────────


def test_stats_panel_aggregates_unfiltered():
    jsx = read_repo_text(*RUN_LIST)
    assert_jsx_contains(jsx, r"computeStats\(runs\)", msg="stats must aggregate the unfiltered runs")
    assert_jsx_contains(jsx, r"<StatsPanel stats=\{stats\}", msg="StatsPanel must receive stats")
    # Antipode — stats must NOT be computed from the filtered subset, and the
    # page must NOT take an external `runs` prop (it owns its fetch).
    assert_jsx_lacks(jsx, r"computeStats\(visibleRuns\)", msg="stats must not use the filtered set")
    assert_jsx_lacks(jsx, r"function AllRunsPage\(\{[^}]*\bruns\b", msg="AllRunsPage must own its fetch, not take a runs prop")


# ─── Filter chip row: seven canonical statuses in order ──────────────────


def test_filter_chip_row_seven_statuses_in_order():
    jsx = read_repo_text(*RUN_LIST)
    order = r"'all'.*'running'.*'converged'.*'deadlocked'.*'errored'.*'abandoned'.*'completed'"
    assert_jsx_contains(jsx, order, msg="filter chips out of order or incomplete", flags=re.DOTALL)
    # Antipode — the inline search input and its `/`-focus shortcut are gone.
    assert_jsx_lacks(jsx, r"ref=\{searchRef\}", msg="inline search input must be removed")
    assert_jsx_lacks(jsx, r"e\.key !== '/'", msg="`/`-focus keyboard handler must be removed")


# ─── No inline styles on the new card tree ───────────────────────────────


def test_no_inline_style_on_run_card():
    jsx = read_repo_text(*RUN_LIST)
    start = jsx.index("function RunCard(")
    end = jsx.index("function ConfirmArchiveDialog(")
    card_src = jsx[start:end]
    assert "style={{" not in card_src, "RunCard must be class-driven — no inline style={{ ... }}"
    assert_jsx_contains(jsx, r"'run-card ' \+", msg="card uses the run-card class via the class map")


# ─── Spec-0245 archive machinery survives the rewrite ────────────────────


def test_archive_machinery_survives():
    jsx = read_repo_text(*RUN_LIST)
    assert_jsx_contains(jsx, r"useRunList\(\{ archived", msg="useRunList archived fetch must survive")
    assert_jsx_contains(jsx, r"useMe\(", msg="useMe must survive")
    assert_jsx_contains(jsx, r"isAdmin && \(", msg="admin gate must survive")
    assert_jsx_contains(jsx, r'data-testid="archived-view-toggle"', msg="Active/Archived toggle must survive")
    assert_jsx_contains(jsx, r"onArchivedView\(false\)", msg="Active toggle wiring must survive")
    assert_jsx_contains(jsx, r"onArchivedView\(true\)", msg="Archived toggle wiring must survive")
    assert_jsx_contains(jsx, r"setArchivedView", msg="archivedView state setter must survive")
    assert_jsx_contains(jsx, r"<ConfirmArchiveDialog", msg="ConfirmArchiveDialog must be rendered")
    assert_jsx_contains(jsx, r"<ConfirmUnarchiveDialog", msg="ConfirmUnarchiveDialog must be rendered")
    assert_jsx_contains(jsx, r"function ConfirmArchiveDialog\(", msg="ConfirmArchiveDialog must be defined")
    assert_jsx_contains(jsx, r"function ConfirmUnarchiveDialog\(", msg="ConfirmUnarchiveDialog must be defined")
    assert_jsx_contains(jsx, r"Icon\.Archive", msg="archive button must use Icon.Archive")
    assert_jsx_contains(jsx, r"Icon\.ArchiveUp", msg="restore button must use Icon.ArchiveUp")
    assert_jsx_contains(jsx, r"onArchive", msg="onArchive handler must survive")
    assert_jsx_contains(jsx, r"onUnarchive", msg="onUnarchive handler must survive")
    assert_jsx_contains(jsx, r"function _secondsSinceIso\(", msg="_secondsSinceIso helper must survive")


# ─── Both CSS files define every new class (DS-sync rule) ─────────────────


def test_both_css_files_in_sync():
    ds = read_repo_text(*CSS_DS)
    live = read_repo_text(*CSS_LIVE)
    for cls in NEW_CLASSES:
        assert cls in ds, f"{cls} missing from composed-components.css"
        assert cls in live, f"{cls} missing from live components.css"


# ─── app.jsx swaps the global chrome off the list route ──────────────────


def test_list_route_uses_all_runs_page():
    app = read_repo_text(*APP)
    assert_jsx_contains(app, r"<AllRunsPage", msg="list route must render AllRunsPage")
    assert_jsx_lacks(app, r"<RunListView", msg="old RunListView consumer must be gone")
    assert_jsx_contains(app, r"route\.view !== 'list'", msg="global ChromeBar must be suppressed on the list route")


# ─── Data layer: RunListRow additive fields + derivation ─────────────────


def test_runlistrow_is_dataclass_with_new_and_0245_fields():
    from dual_research.ui.models import RunListRow

    assert dataclasses.is_dataclass(RunListRow)
    names = {f.name for f in dataclasses.fields(RunListRow)}
    # Spec 0246 additive fields...
    assert {"phases", "rounds_completed", "rounds_max", "agents", "note"} <= names
    # ...without dropping the spec 0245 soft-delete fields.
    assert {"deleted_at", "deleted_by"} <= names


def test_phase_outcomes_algorithm():
    from dual_research.ui.aggregator import derive_phase_outcomes

    assert derive_phase_outcomes(4, "errored") == ("done", "done", "done", "failed", "pending")
    assert derive_phase_outcomes(5, "completed") == ("done",) * 5
    assert derive_phase_outcomes(5, "converged") == ("done",) * 5
    assert derive_phase_outcomes(2, "running") == ("done", "active", "pending", "pending", "pending")
    assert derive_phase_outcomes(2, "abandoned") == ("done", "abandon", "pending", "pending", "pending")
    assert derive_phase_outcomes(3, "deadlocked") == ("done", "done", "abandon", "pending", "pending")


def test_run_note_generic_copy():
    from dual_research.ui.aggregator import derive_run_note

    err = derive_run_note("errored", 4, error_type="ProtocolParseError")
    assert err.variant == "err" and err.icon == "error" and "ProtocolParseError" in err.html
    ok = derive_run_note("completed", 5, rounds_completed=3)
    assert ok.variant == "ok" and ok.icon == "check_circle" and "P5" in ok.html
    warn = derive_run_note("abandoned", 2)
    assert warn.variant == "warn" and warn.icon == "pause_circle"
    assert derive_run_note("running", 2) is None  # running rows collapse the note


def test_agent_breakdowns_cost_and_search_chip():
    from dual_research.ui.aggregator import derive_agent_breakdowns

    metrics = {
        "totals_by_agent": {
            "claude": {"cost_usd": 4.20, "search_cost": 0.01, "searches": 3},
            "openai": {"cost_usd": 5.70, "search_cost": 0.0, "searches": 0},
        }
    }
    agents = derive_agent_breakdowns(metrics)
    assert agents["a"].name == "Claude" and agents["a"].cost == 4.21
    assert agents["b"].name == "GPT" and agents["b"].cost == 5.70
    # Search chip ships for the agent with searches; absent otherwise.
    assert any(c.text == "3 searches" and c.kind == "info" for c in agents["a"].chips)
    assert agents["b"].chips == []
    assert derive_agent_breakdowns(None) == {}


def test_api_runs_camel_shape_includes_new_and_0245_fields():
    import dataclasses as _dc

    from dual_research.ui.models import AgentBreakdown, AgentChip, RunListRow, RunNote
    from dual_research.ui.server import _to_camel

    row = RunListRow(
        id="r-13ed3f4a-91c2",
        display_id="r-13ed3f4a-91c2",
        status="errored",
        phase=4,
        topic="Postgres multi-tenant RLS & connection-pool reset",
        started_at_ago=10,
        started_at="2026-05-28T14:00:00Z",
        duration=600,
        cost=9.91,
        phases=("done", "done", "done", "failed", "pending"),
        rounds_completed=2,
        rounds_max=6,
        agents={
            "a": AgentBreakdown(name="Claude", cost=4.21, chips=[AgentChip(text="3 searches", kind="info")]),
            "b": AgentBreakdown(name="GPT", cost=5.70),
        },
        note=RunNote(variant="err", icon="error", html="Run failed in P4: <b>X</b>."),
        deleted_at="2026-05-28T15:00:00Z",
        deleted_by="admin@example.com",
    )
    camel = _to_camel(_dc.asdict(row))
    # Spec 0246 additive fields (camelCased)...
    for key in ("phases", "roundsCompleted", "roundsMax", "agents", "note"):
        assert key in camel, f"{key} missing from /api/runs row shape"
    assert camel["agents"]["a"]["cost"] == 4.21
    assert camel["note"]["variant"] == "err"
    # ...and the spec 0245 fields are preserved.
    assert camel["deletedAt"] == "2026-05-28T15:00:00Z"
    assert camel["deletedBy"] == "admin@example.com"
