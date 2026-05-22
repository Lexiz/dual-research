"""Regression test for spec 0160 — default mode preserves baked-in dashboard.

The default mode (no `--shell-only` flag) is the local-preview / fallback
path; the renderer must still emit the full populated dashboard with spec
numbers and titles baked into the HTML. The bootstrap script is also
referenced but harmless if /api/data isn't reachable locally.
"""
from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import collect, render_index


def _bootstrap_repo(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "drafts").mkdir()
    (tmp_path / "handoffs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)
    (specs / "0202-default-mode.md").write_text(
        '---\nkind: dev\nspec: "0202"\nslug: default-mode\ntitle: Default-mode regression check\n'
        'type: new-feature\nstatus: deployed\nstarted_at: "2026-05-01T00:00:00Z"\n'
        'deployed_at: "2026-05-01T01:00:00Z"\npr: "https://x/pr/2"\n---\nbody\n'
    )
    return tmp_path


def test_default_mode_bakes_spec_content_into_html(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)  # no shell_only
    assert "Default-mode regression check" in html, "spec title should be baked into the HTML"
    assert 'href="spec-0202.html"' in html, "spec link should appear in the populated sections"


def test_default_mode_has_data_region_wrappers_for_bootstrap_swaps(tmp_path: Path) -> None:
    """Even default mode wraps sections in data-region containers so the
    bootstrap script can swap them when /api/data is reachable."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    for region in ("hero", "pipeline", "metrics", "queue", "feed", "drafts", "all-specs"):
        assert f'data-region="{region}"' in html


def test_default_mode_references_bootstrap_and_live_scripts(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert '<script src="dashboard-bootstrap.js" defer></script>' in html
    assert '<script src="dashboard-live.js" defer></script>' in html


def test_default_mode_no_skeletons_in_populated_sections(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert "region-skeleton" not in html
