"""Regression test for spec 0160 — `<meta http-equiv="refresh">` is gone.

The 60s meta-refresh (spec 0156 §2.2) was retired when the bootstrap script
took over freshness via 15s polling of /api/data. Neither shell-only nor
default mode should emit the tag anymore — pages without page reloads is
the point.
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
    (specs / "0303-no-refresh.md").write_text(
        '---\nkind: dev\nspec: "0303"\nslug: no-refresh\ntitle: No-meta-refresh check\n'
        'type: new-feature\nstatus: deployed\nstarted_at: "2026-05-01T00:00:00Z"\n'
        'deployed_at: "2026-05-01T01:00:00Z"\npr: "https://x/pr/3"\n---\nbody\n'
    )
    return tmp_path


def test_no_meta_refresh_in_shell_mode(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, shell_only=True)
    assert 'http-equiv="refresh"' not in html, (
        "spec 0160 retired the 60s meta-refresh; bootstrap script handles freshness now"
    )


def test_no_meta_refresh_in_default_mode(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert 'http-equiv="refresh"' not in html
