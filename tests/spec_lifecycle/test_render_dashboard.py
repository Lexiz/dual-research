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
    # New design-system anchors per spec 0153.
    assert "hero--inflight" in html  # there's one in-progress spec in the bootstrap
    assert 'class="pipe"' in html
    assert 'class="metrics"' in html
    assert 'class="qtable"' in html
    assert 'class="feed"' in html
    assert 'class="drafts"' in html
    assert 'class="foot"' in html
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
