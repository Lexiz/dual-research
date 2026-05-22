"""Regression test for spec 0160 — `--shell-only` shell mode.

In shell mode the renderer emits data-empty containers with `data-region`
attributes; the bootstrap script populates them at runtime from /api/data.
This locks in:

- The hero / queue / feed / drafts / all-specs sections have
  ``data-region`` attributes wrapping a ``region-skeleton``.
- Section bodies do NOT contain any spec number, title, or status text
  (so the bootstrap script can swap them cleanly).
- ``<script src="dashboard-bootstrap.js" defer>`` is in the ``<head>``.
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
    (specs / "0101-deployed.md").write_text(
        '---\nkind: dev\nspec: "0101"\nslug: deployed\ntitle: A unique spec title\n'
        'type: new-feature\nstatus: deployed\nstarted_at: "2026-05-01T00:00:00Z"\n'
        'deployed_at: "2026-05-01T01:00:00Z"\npr: "https://x/pr/1"\n---\nbody\n'
    )
    return tmp_path


def test_shell_mode_emits_data_region_skeletons(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, shell_only=True)
    # Spec 0169 introduced `counters` / `avg` / `total-elapsed`; spec 0177
    # folded `avg` into the counter row so it's no longer a separate region.
    # Metrics still has a region (inside the Metrics tab).
    for region in ("hero", "counters", "metrics", "queue", "feed", "drafts", "all-specs", "total-elapsed"):
        assert f'data-region="{region}"' in html, f"missing data-region={region!r}"
    # `avg` region is gone — assert that explicitly so we don't accidentally
    # re-introduce a separate avg-cycle swap path.
    assert 'data-region="avg"' not in html
    # Skeleton class present (visual placeholders).
    assert "region-skeleton" in html


def test_shell_mode_does_not_leak_spec_content(tmp_path: Path) -> None:
    """Shell mode is data-empty — section bodies should not contain spec
    numbers, titles, or status strings from the fixture."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, shell_only=True)
    # The fixture spec's title and status should not appear anywhere in the
    # body (only in skeletons; no real data baked in).
    assert "A unique spec title" not in html
    assert ">deployed<" not in html  # status chip text
    # Spec link href would only appear in populated sections; shell omits it.
    assert 'href="spec-0101.html"' not in html


def test_shell_mode_references_bootstrap_script(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, shell_only=True)
    assert '<script src="dashboard-bootstrap.js" defer></script>' in html


def test_shell_mode_header_has_data_last_updated(tmp_path: Path) -> None:
    """Bootstrap script writes "updated X ago" into [data-last-updated]."""
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, shell_only=True)
    assert "data-last-updated" in html
