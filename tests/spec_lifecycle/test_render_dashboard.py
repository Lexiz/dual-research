"""Tests for scripts.spec_lifecycle.render_dashboard."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    collect,
    copy_design_system_assets,
    main,
    render_index,
)


def _bootstrap_repo(tmp_path: Path) -> Path:
    """Create a minimal repo-like layout to render against."""
    specs = tmp_path / "specs"
    specs.mkdir()
    drafts = specs / "drafts"
    drafts.mkdir()
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    events_dir = tmp_path / "dashboard" / "events"
    events_dir.mkdir(parents=True)

    (specs / "0101-deployed-spec.md").write_text(
        '---\nkind: dev\nspec: "0101"\nslug: deployed-spec\ntitle: Deployed thing\n'
        'type: new-feature\nstatus: deployed\nstarted_at: "2026-05-01T00:00:00Z"\n'
        'deployed_at: "2026-05-01T01:00:00Z"\npr: "https://x/pr/1"\n---\nbody\n'
    )
    (specs / "0102-queued-spec.md").write_text(
        '---\nkind: dev\nspec: "0102"\nslug: queued-spec\ntitle: Queued thing\n'
        'type: bug\nstatus: queued\nqueue_position: 1\nqueued_at: "2026-05-22T10:00:00Z"\n---\nbody\n'
    )
    (specs / "0103-in-flight.md").write_text(
        '---\nkind: dev\nspec: "0103"\nslug: in-flight\ntitle: In flight thing\n'
        'type: refactoring\nstatus: in_progress\nstarted_at: "2026-05-22T10:00:00Z"\n---\nbody\n'
    )
    (drafts / "draft-001-x.md").write_text(
        '---\nkind: draft\ndraft_id: "001"\nslug: x\ntitle: Draft thing\n'
        'type: unclassified\nstatus: draft\ncreated: "2026-05-22"\n---\nbody\n'
    )
    (events_dir / "0103.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"in_progress","data":{}}\n'
    )
    return tmp_path


def _bootstrap_design_system(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "assets" / "styles"
    ds.mkdir(parents=True)
    (ds / "tokens-and-primitives.css").write_text(":root { --md-surface-dim: #000; }\n")
    (ds / "composed-components.css").write_text(".chip { display: inline-block; }\n")


def test_collect_finds_specs_and_drafts(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    assert len(specs) == 3
    assert len(drafts) == 1
    assert {s.status for s in specs} == {"deployed", "queued", "in_progress"}


def test_index_contains_all_sections(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, live_version="1.18.0")
    # Spec 0153 anchors that survived the spec-0169 redesign.
    assert "hero--inflight" in html  # there's one in-progress spec in the bootstrap
    assert 'class="qtable"' in html
    assert 'class="feed"' in html
    assert 'class="drafts"' in html
    assert 'class="foot"' in html
    # Spec 0169 §2.1 / §2.2 — callout strip + tab bar replace the pipe + metrics row.
    assert 'class="strip"' in html
    assert 'class="counters"' in html
    assert 'class="avg-cycle"' in html
    assert 'class="tabs"' in html
    assert 'data-panel="now"' in html
    assert 'data-panel="spec"' in html
    assert 'data-panel="history"' in html
    assert 'data-panel="metrics"' in html
    # The legacy .metrics section moved INTO the Metrics tab — still present.
    assert 'class="metrics"' in html
    # Spec 0169 §2.5 — total-elapsed banner ships inside the History tab.
    assert 'class="te-banner"' in html
    # Spec links remain filename-derived.
    assert 'href="spec-0101.html"' in html
    assert 'href="spec-0102.html"' in html
    assert 'href="spec-0103.html"' in html
    assert 'href="draft-001.html"' in html
    # Section labels still present in the page (under .sh headings now).
    assert "Queue" in html
    assert "Drafts" in html
    assert "All specs" in html
    assert "Recent activity" in html


def test_spec_0169_theme_toggle_and_shim(tmp_path: Path) -> None:
    """Spec 0169 §2.7 — theme toggle in header + inline init script + shim CSS."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, live_version="1.30.0")
    # Toggle button in the header.
    assert 'id="theme-toggle"' in html
    assert 'data-theme-icon' in html
    assert 'data-theme-label' in html
    # <html data-theme="auto"> default.
    assert 'data-theme="auto"' in html
    # Inline init script reads localStorage before paint.
    assert "localStorage.getItem('dr-dashboard-theme')" in html
    # Shim CSS lives in DASHBOARD_CSS; live JS wires persistence.
    from scripts.spec_lifecycle.render_dashboard import DASHBOARD_CSS, DASHBOARD_LIVE_JS
    assert 'html[data-theme="dark"]' in DASHBOARD_CSS
    assert 'html[data-theme="light"]' in DASHBOARD_CSS
    assert 'html[data-theme="auto"]' in DASHBOARD_CSS
    assert "dr-dashboard-theme" in DASHBOARD_LIVE_JS
    assert "applyTheme" in DASHBOARD_LIVE_JS


def test_spec_0169_total_elapsed_banner_math(tmp_path: Path) -> None:
    """Spec 0169 §2.5 — banner math: sum, mean (excl > 1h), median, fastest/slowest."""
    import datetime as dt
    from scripts.spec_lifecycle.render_dashboard import _render_total_elapsed_banner, SpecRow

    base = dt.datetime(2026, 5, 22, 10, 0, 0, tzinfo=dt.timezone.utc)
    def row(number: str, cycle_seconds: int) -> SpecRow:
        started = base.strftime("%Y-%m-%dT%H:%M:%SZ")
        deployed = (base + dt.timedelta(seconds=cycle_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return SpecRow(
            fm={
                "spec": number, "slug": f"spec-{number}", "title": f"Spec {number}",
                "type": "new-feature", "status": "deployed",
                "started_at": started, "deployed_at": deployed,
            },
            path=tmp_path / f"specs/{number}-spec.md",
        )

    specs = [
        row("0001", 300),    # 5m
        row("0002", 600),    # 10m
        row("0003", 1200),   # 20m
        row("0004", 1800),   # 30m
        row("0005", 40000),  # outlier > 1h, excluded from mean
    ]
    html = _render_total_elapsed_banner(specs)
    # Total: 43900s → "12h 11m"
    assert "12h 11m" in html
    # Mean excl outliers: (300+600+1200+1800)/4 = 975s → "16m 15s"
    assert "16m 15s" in html
    # Median (incl outliers): 1200s = "20m"
    assert "20m" in html
    # Fastest 0001 / Slowest 0005
    assert "0001" in html
    assert "0005" in html
    # Excluded-outlier note
    assert "excluding 1 outlier" in html


def test_cycle_time_formatting(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, _ = collect(root)
    deployed = next(s for s in specs if s.status == "deployed")
    assert deployed.cycle_seconds == 3600


def test_idle_vs_inflight_hero(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)

    inflight_specs = [s for s in specs if s.status == "in_progress"]
    idle_specs = [s for s in specs if s.status != "in_progress"]

    inflight_html = render_index(specs, drafts)
    assert "hero--inflight" in inflight_html
    # Eleven stages rendered.
    assert inflight_html.count('class="stage stage--') == 11

    idle_html = render_index(idle_specs, drafts)
    assert "hero--idle" in idle_html
    assert "hero--inflight" not in idle_html
    assert "Nothing in flight" in idle_html

    # Both heroes never appear in the same render.
    assert not ("hero--idle" in inflight_html and "hero--inflight" in inflight_html and "Nothing in flight" in inflight_html)


def test_assets_copied(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    _bootstrap_design_system(root)
    out = tmp_path / "site"

    rc = main(["--repo-root", str(root), "--out", str(out)])
    assert rc == 0
    assert (out / "index.html").exists()
    assert (out / "tokens.css").exists()
    assert (out / "components.css").exists()
    assert (out / "dashboard.css").exists()
    # Verify the copied tokens.css came from the design-system source.
    assert "--md-surface-dim" in (out / "tokens.css").read_text(encoding="utf-8")


def test_meta_refresh_retired_per_spec_0160(tmp_path: Path) -> None:
    """Spec 0160 retired the 60s meta-refresh (introduced in spec 0156 §2.2).
    The bootstrap script's 15s /api/data poll now handles freshness without
    page reloads, so mid-scroll users don't get bounced."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert 'http-equiv="refresh"' not in html


def test_dashboard_live_js_script_referenced(tmp_path: Path) -> None:
    """The hero references the live-ticker script (spec 0156 §2.3)."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert 'src="dashboard-live.js"' in html


def test_inflight_hero_emits_live_data_attributes(tmp_path: Path) -> None:
    """In-flight hero carries data-cycle-started-at and data-stage-started-at
    with ISO 8601 timestamps so dashboard-live.js can rewrite the text
    every second (spec 0156 §2.3)."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # The bootstrap repo has one in-progress spec (0103) so the in-flight hero renders.
    assert "hero--inflight" in html
    # Cycle-started attribute appears on the hero's big number.
    assert "data-cycle-started-at=" in html
    # And the current stage row has the stage-started-at attribute.
    assert "data-stage-started-at=" in html
    # Values look like ISO 8601 timestamps (year prefix shows up).
    import re

    cycle_match = re.search(r'data-cycle-started-at="(\d{4}-\d{2}-\d{2}T[^"]+)"', html)
    assert cycle_match is not None, "data-cycle-started-at must be an ISO 8601 timestamp"


def test_main_writes_dashboard_live_js(tmp_path: Path) -> None:
    """`main` writes dashboard-live.js alongside the other assets (spec 0156 §2.3)."""
    root = _bootstrap_repo(tmp_path)
    _bootstrap_design_system(root)
    out = tmp_path / "site"

    rc = main(["--repo-root", str(root), "--out", str(out)])
    assert rc == 0
    js = out / "dashboard-live.js"
    assert js.exists()
    content = js.read_text(encoding="utf-8")
    assert "data-cycle-started-at" in content
    assert "data-stage-started-at" in content
    assert "prefers-reduced-motion" in content  # Honors the user pref.


def test_assets_copy_missing_raises(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    out = tmp_path / "site"
    out.mkdir()
    try:
        copy_design_system_assets(root, out)
    except FileNotFoundError as exc:
        assert "Design-system stylesheets missing" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
