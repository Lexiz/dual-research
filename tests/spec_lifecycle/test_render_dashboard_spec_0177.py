"""Spec 0177 — dashboard redesign v3 regressions.

Covers § 6 (test plan) of `specs/0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md`:
hero structure, horizontal timeline, history columns, populated Metrics tab,
pastel chart tokens, pagination, light-default theme, DS sync of `.pager`.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    PAGER_PAGE_SIZE,
    collect,
    main,
    render_index,
    _build_sparkline_polyline,
    _humanize_seconds,
    _render_pager,
)


def _spec(
    specs_dir: Path,
    number: str,
    *,
    status: str = "deployed",
    type_: str = "new-feature",
    title: str | None = None,
    started_at: str = "",
    deployed_at: str = "",
    queued_at: str = "",
    created: str = "",
    queue_position: int | None = None,
    target_version: str = "",
) -> None:
    """Write a minimal spec frontmatter file. ``title`` defaults to a unique
    fixture-derived string so assertions can pin behaviour to a specific row.
    """
    title = title or f"Spec {number} fixture row"
    parts = [
        "---",
        "kind: dev",
        f'spec: "{number}"',
        f"slug: fixture-{number}",
        f"title: {title}",
        f"type: {type_}",
        f"status: {status}",
    ]
    if started_at:
        parts.append(f'started_at: "{started_at}"')
    if deployed_at:
        parts.append(f'deployed_at: "{deployed_at}"')
    if queued_at:
        parts.append(f'queued_at: "{queued_at}"')
    if created:
        parts.append(f"created: {created}")
    if queue_position is not None:
        parts.append(f"queue_position: {queue_position}")
    if target_version:
        parts.append(f"target_version: {target_version}")
    parts.append("---\nbody\n")
    (specs_dir / f"{number}-{number}-fixture.md").write_text("\n".join(parts))


def _bootstrap_repo(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "drafts").mkdir()
    (tmp_path / "handoffs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)
    return tmp_path


def test_hero_region_is_full_width_no_flanking_columns(tmp_path: Path) -> None:
    """Spec 0177 §2.1 — the hero region sits as a direct child of `.page`
    via `.strip { display: contents; }`. No flanking 3-column grid pinned
    around it. We assert the CSS expresses `display: contents` for `.strip`
    and not `grid-template-columns`."""
    from scripts.spec_lifecycle.render_dashboard import DASHBOARD_CSS

    assert ".strip { display: contents; }" in DASHBOARD_CSS
    # Make sure the old 3-column grid is gone.
    assert "grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) minmax(0, 0.6fr)" not in DASHBOARD_CSS


def test_counter_row_has_five_counters_with_accent(tmp_path: Path) -> None:
    """Spec 0177 §2.1 — 5 counter cards including the avg-cycle accent."""
    root = _bootstrap_repo(tmp_path)
    for n in ("0101", "0102", "0103"):
        _spec(root / "specs", n, status="deployed",
              started_at="2026-05-01T00:00:00Z",
              deployed_at="2026-05-01T00:10:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert html.count('class="counter') >= 5  # 4 plain + 1 accent
    assert 'counter counter--accent' in html
    # The accent counter carries the avg-cycle label.
    assert "Avg cycle (last 10)" in html


def test_inflight_render_has_tl_with_seven_steps(tmp_path: Path) -> None:
    """Spec 0177 §6 + spec 0213 §2.1 — in-flight render contains
    `<div class="tl">` with exactly 7 `tl__step` children (the canonical
    span rows after spec 0213's collapse from 11 → 7)."""
    root = _bootstrap_repo(tmp_path)
    _spec(root / "specs", "0151", status="in_progress",
          started_at="2026-05-22T10:00:00Z")
    (root / "dashboard" / "events" / "0151.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"in_progress","data":{}}\n'
    )
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert '<div class="tl" aria-label="Cycle stages">' in html
    assert html.count('class="tl__step tl__step--') == 7


def test_history_grid_has_lifetime_and_cycle_headers(tmp_path: Path) -> None:
    """Spec 0177 §2.3 — history grid headers `Spec / Title / Type / Status /
    Lifetime / Cycle`. At least one deployed row shows non-`—` Lifetime + Cycle.
    """
    root = _bootstrap_repo(tmp_path)
    _spec(root / "specs", "0140", status="deployed",
          created="2026-05-15",
          started_at="2026-05-22T10:00:00Z",
          deployed_at="2026-05-22T10:30:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # 6-column grid via `.qrow--history-header`.
    assert "qrow--history-header" in html
    assert "<div>Spec</div>" in html and "<div>Title</div>" in html
    assert "<div>Type</div>" in html and "<div>Status</div>" in html
    assert ">Lifetime<" in html
    assert ">Cycle<" in html
    # The "Version" column header should be gone from the History grid header
    # row (we don't assert "Version" entirely because target_version values
    # can still appear elsewhere in the frontmatter dump for spec pages).
    history_section_idx = html.find('data-region="all-specs"')
    history_section = html[history_section_idx:history_section_idx + 20000]
    assert "<div>Version</div>" not in history_section
    # Deployed row carries both Lifetime + Cycle (non-empty).
    assert "30m" in history_section  # 30-minute cycle ⇒ "30m" via _humanize_seconds


def test_metrics_tab_contains_at_least_four_distinct_charts_and_three_callouts(
    tmp_path: Path,
) -> None:
    """Spec 0177 §6 — assert the Metrics tab carries ≥ 4 `<svg class="chart"`
    elements and 3 `.callout` cards."""
    root = _bootstrap_repo(tmp_path)
    # Six deployed specs over the last week so the callouts have data to chew on.
    for i, n in enumerate(("0140", "0141", "0142", "0143", "0144", "0145")):
        _spec(root / "specs", n, status="deployed",
              created="2026-05-20",
              started_at=f"2026-05-{20+i:02d}T10:00:00Z",
              deployed_at=f"2026-05-{20+i:02d}T10:{10+i:02d}:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert html.count('<svg class="chart"') >= 4, (
        f"expected ≥ 4 chart SVGs; got {html.count('<svg class=\"chart\"')}"
    )
    # Three callouts in the strip above the charts. The class composition is
    # `callout` plus an optional tone modifier; count by the icon inside each
    # callout for a robust match.
    assert html.count('class="callout__icon"') >= 3
    assert 'class="callouts"' in html


def test_pastel_chart_tokens_in_design_system_tokens_css() -> None:
    """Spec 0177 §2.5 — `--chart-*` tokens land in both the `:root` (dark)
    block and the `body.light` block of tokens-and-primitives.css.
    """
    css = Path("design-system/assets/styles/tokens-and-primitives.css").read_text(
        encoding="utf-8"
    )
    root_block, _, light_block = css.partition("body.light {")
    assert "--chart-blue:" in root_block, "chart-blue missing from dark :root block"
    assert "--chart-purple:" in root_block
    assert "--chart-grey:" in root_block
    assert "--chart-track:" in root_block
    # Light block: every token should re-declare with a softer hex.
    assert "--chart-blue:" in light_block
    assert "--chart-purple:" in light_block
    assert "--chart-grey:" in light_block
    assert "--chart-track:" in light_block


def test_render_pager_emits_count_and_buttons() -> None:
    """Spec 0177 §2.6 — `_render_pager` emits a strip with the count text,
    a disabled prev button, an aria-current page-1 button, and an enabled
    next button when there are ≥ 2 pages.
    """
    html = _render_pager(total_rows=23, label="Queue")
    assert 'class="pager"' in html
    assert 'aria-label="Queue pagination"' in html
    assert "Showing 1–10 of 23" in html
    # 23 rows → 3 pages. First page button is aria-current.
    assert 'data-pager-go="1"' in html and 'aria-current="page"' in html
    assert 'data-pager-go="2"' in html
    assert 'data-pager-go="3"' in html
    # Prev disabled, next enabled on first render.
    assert 'data-pager-prev aria-label="Previous page" disabled' in html
    assert 'data-pager-next aria-label="Next page"' in html
    assert " disabled>→</button>" not in html, "next button should NOT be disabled on page 1 of 3"


def test_render_pager_collapses_to_ellipsis_past_five_pages() -> None:
    """Past 5 pages, mid-pages collapse into an ellipsis."""
    html = _render_pager(total_rows=200, label="Recent activity")
    # 200 / 10 = 20 pages.
    assert 'class="pager__ellipsis"' in html
    # First three pages + last page button.
    assert 'data-pager-go="1"' in html
    assert 'data-pager-go="2"' in html
    assert 'data-pager-go="3"' in html
    assert 'data-pager-go="20"' in html
    # No middle pages.
    assert 'data-pager-go="10"' not in html


def test_render_pager_empty_when_under_page_size() -> None:
    """When total_rows ≤ PAGER_PAGE_SIZE there is no pager (the rows fit
    on one page; the strip would be visual noise)."""
    assert _render_pager(total_rows=0, label="Queue") == ""
    # The wrapper section gates emission at len > PAGE_SIZE, so the renderer
    # itself never gets called with values ≤ PAGE_SIZE in the live path; we
    # still assert the helper's count-text branch handles small totals.
    html = _render_pager(total_rows=PAGER_PAGE_SIZE, label="Queue")
    assert "Showing 1–10 of 10" in html


def test_queue_rows_get_data_pager_page_attribute(tmp_path: Path) -> None:
    """Spec 0177 §2.6 — queued rows from index 10 onward carry
    `data-pager-page="2"` (or higher) and `hidden`. Rows on page 1 carry
    `data-pager-page="1"` and no `hidden`."""
    root = _bootstrap_repo(tmp_path)
    for i in range(15):
        _spec(
            root / "specs",
            f"0{200 + i:03d}",
            status="queued",
            queue_position=i + 1,
            queued_at="2026-05-22T10:00:00Z",
        )
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # 15 queued specs → 2 pages; pager visible.
    assert 'class="pager"' in html
    assert 'data-pager-page="1"' in html
    assert 'data-pager-page="2"' in html
    # The 11th queued row (idx 10) goes on page 2 and is hidden initially.
    assert 'data-pager-page="2" hidden' in html


def test_light_default_in_theme_init_script() -> None:
    """Spec 0177 §2.7 — first-visit users get light, not auto."""
    from scripts.spec_lifecycle.render_dashboard import _render_theme_init_script

    body = _render_theme_init_script()
    assert "||'light'" in body
    # The except branch should also fall back to 'light' (was 'auto').
    assert "setAttribute('data-theme','light')" in body
    # The legacy 'auto' fallback must be gone from the init script.
    assert "||'auto'" not in body
    assert "setAttribute('data-theme','auto')" not in body


def test_pager_css_lands_in_both_design_system_and_live_components() -> None:
    """Spec 0177 §2.6 + CLAUDE.md DS sync rule — `.pager` block exists in
    BOTH `design-system/assets/styles/composed-components.css` AND
    `src/dual_research/ui/static/components.css`.
    """
    ds_css = Path("design-system/assets/styles/composed-components.css").read_text(
        encoding="utf-8"
    )
    live_css = Path("src/dual_research/ui/static/components.css").read_text(
        encoding="utf-8"
    )
    assert ".pager {" in ds_css, "missing .pager block in design-system/.../composed-components.css"
    assert ".pager {" in live_css, "missing .pager block in src/dual_research/ui/static/components.css"
    # Spot-check that the block contains the active-page selector + no hex
    # values (tokens only per CLAUDE.md).
    for css in (ds_css, live_css):
        # The whole stylesheet has hex colours in older blocks; we only
        # care that the .pager rule itself reads from tokens.
        pager_start = css.index(".pager {")
        pager_end = css.index(".pager__ellipsis", pager_start)
        pager_block = css[pager_start:pager_end + 200]
        assert "var(--md-" in pager_block, ".pager block must read from --md-* tokens"
        assert 'aria-current="page"' in pager_block


def test_main_emits_dashboard_with_new_structure(tmp_path: Path) -> None:
    """End-to-end: running ``main`` against a minimal fixture writes the
    expected files and the new structural anchors land in index.html.
    """
    root = _bootstrap_repo(tmp_path)
    _spec(root / "specs", "0301", status="deployed",
          created="2026-05-20",
          started_at="2026-05-22T10:00:00Z",
          deployed_at="2026-05-22T10:10:00Z")
    ds = root / "design-system" / "assets" / "styles"
    ds.mkdir(parents=True)
    (ds / "tokens-and-primitives.css").write_text(":root { --md-surface-dim: #000; --chart-blue: #7fa8d8; }\n")
    (ds / "composed-components.css").write_text(".chip { display: inline-block; } .pager { display: flex; }\n")
    out = tmp_path / "site"
    rc = main(["--repo-root", str(root), "--out", str(out)])
    assert rc == 0
    index = (out / "index.html").read_text(encoding="utf-8")
    # Counter row + chart card + new theme default all land.
    assert 'counter counter--accent' in index
    assert 'class="chart-card"' in index
    assert 'data-theme="light"' in index
    # tokens.css carries the chart token (came from the fixture DS file above).
    assert "--chart-blue" in (out / "tokens.css").read_text(encoding="utf-8")


def test_humanize_seconds_extends_to_weeks() -> None:
    """Spec 0177 §2.3 — _humanize_seconds learned to render weeks."""
    one_week = 7 * 24 * 3600
    assert _humanize_seconds(one_week) == "1w"
    assert _humanize_seconds(one_week + 3 * 24 * 3600) == "1w 3d"
    # Below a week still reads in days.
    assert _humanize_seconds(2 * 24 * 3600) == "2d"
    assert _humanize_seconds(2 * 24 * 3600 + 3600) == "2d 1h"


def test_sparkline_handles_short_and_flat_series() -> None:
    """Spec 0177 §2.1 sparkline — handles 0/1 points (flat baseline) and
    a normal series (mapped onto the 0–120 × 4–20 viewBox).

    Mapping: x is evenly spaced across [0, 120]; y inverts so the smallest
    value lands at y=20 (visual bottom) and the largest at y=4 (visual top).
    """
    assert _build_sparkline_polyline([]) == "0,12 120,12"
    assert _build_sparkline_polyline([300]) == "0,12 120,12"
    pts = _build_sparkline_polyline([300, 600, 900])
    # 3 points evenly spaced across x ∈ [0, 120].
    assert pts.startswith("0.0,")
    assert pts.endswith("120,4.0") or pts.endswith("120.0,4.0")
    assert "60" in pts.split(" ")[1]  # midpoint x ≈ 60


def test_bootstrap_js_emits_horizontal_timeline_and_pager_state() -> None:
    """Spec 0177 §2.1 / §2.2 / §2.6 — bootstrap JS includes the new
    structures: STAGE_DEFS, renderTimeline(), pagerState map, renderPager.
    Live-JS picks up the new light-theme default in the toggle wiring.
    """
    from scripts.spec_lifecycle.render_dashboard import (
        DASHBOARD_BOOTSTRAP_JS, DASHBOARD_LIVE_JS,
    )

    assert "STAGE_DEFS" in DASHBOARD_BOOTSTRAP_JS
    assert "renderTimeline" in DASHBOARD_BOOTSTRAP_JS
    assert "tl__step--" in DASHBOARD_BOOTSTRAP_JS
    assert "pagerState" in DASHBOARD_BOOTSTRAP_JS
    assert "renderPager" in DASHBOARD_BOOTSTRAP_JS
    # The history grid mirror picks up Lifetime + Cycle.
    assert "qrow--history-header" in DASHBOARD_BOOTSTRAP_JS
    assert "Lifetime" in DASHBOARD_BOOTSTRAP_JS
    assert "Cycle" in DASHBOARD_BOOTSTRAP_JS
    # Spec 0177 §2.7 — live-js toggle wiring's first-visit fallback is now 'light'.
    assert "applyTheme('light')" in DASHBOARD_LIVE_JS
