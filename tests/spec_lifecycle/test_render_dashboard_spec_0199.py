"""Spec 0199 — render_dashboard handles decimal spec IDs.

Covers the §6 test plan items:
- `render_dashboard.py` does not crash on a decimal spec ID
  (regression of `int("0170.1")` at line 1629).
- The renderer sorts a mix of decimal + integer IDs as
  `[0170, 0170.1, 0171]` rather than alphabetically or by stripping `.M`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    SpecRow,
    collect,
    render_index,
)


def _bootstrap_design_system(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "assets" / "styles"
    ds.mkdir(parents=True)
    (ds / "tokens-and-primitives.css").write_text(":root { --md-surface-dim: #000; }\n")
    (ds / "composed-components.css").write_text(".chip { display: inline-block; }\n")


def _bootstrap_repo_with_decimals(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    drafts = tmp_path / "specs" / "drafts"
    drafts.mkdir()
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    events_dir = tmp_path / "dashboard" / "events"
    events_dir.mkdir(parents=True)
    _bootstrap_design_system(tmp_path)

    (specs / "0170-parent.md").write_text(
        '---\nkind: dev\nspec: "0170"\nslug: parent\ntitle: Parent thing\n'
        'type: new-feature\nstatus: queued\nqueued_at: "2026-05-22T10:00:00Z"\n---\nbody\n'
    )
    (specs / "0170.1-child.md").write_text(
        '---\nkind: dev\nspec: "0170.1"\nslug: child\ntitle: Decimal child\n'
        'type: new-feature\nstatus: queued\nqueued_at: "2026-05-22T10:01:00Z"\n---\nbody\n'
    )
    (specs / "0171-next.md").write_text(
        '---\nkind: dev\nspec: "0171"\nslug: next\ntitle: Next integer\n'
        'type: new-feature\nstatus: queued\nqueued_at: "2026-05-22T10:02:00Z"\n---\nbody\n'
    )
    return tmp_path


def test_spec_row_number_includes_decimal(tmp_path: Path) -> None:
    p = tmp_path / "0170.1-foo.md"
    p.write_text(
        '---\nkind: dev\nspec: "0170.1"\nslug: foo\ntitle: t\n'
        "type: bug\nstatus: queued\n---\nbody\n"
    )
    row = SpecRow(fm={"spec": "0170.1", "status": "queued"}, path=p)
    assert row.number == "0170.1"
    assert row.sort_key == (170, 1)


def test_spec_row_integer_number(tmp_path: Path) -> None:
    p = tmp_path / "0170-foo.md"
    p.write_text(
        '---\nkind: dev\nspec: "0170"\nslug: foo\ntitle: t\n'
        "type: bug\nstatus: queued\n---\nbody\n"
    )
    row = SpecRow(fm={"spec": "0170", "status": "queued"}, path=p)
    assert row.number == "0170"
    assert row.sort_key == (170, 0)


def test_render_does_not_crash_on_decimal_spec(tmp_path: Path) -> None:
    """Regression of `int(s.number or '0')` at render_dashboard.py:1629 —
    the All-specs sort would have raised `ValueError` on `"0170.1"`."""
    root = _bootstrap_repo_with_decimals(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, live_version="1.40.0")
    # Smoke: every decimal spec appears in the queue/all-specs panels.
    assert "0170.1" in html
    assert "0170" in html
    assert "0171" in html


def test_queue_order_interleaves_decimals(tmp_path: Path) -> None:
    """Spec 0199 §3.2 Scenario 5 — `[0170, 0170.1, 0171]` ordering in the
    rendered queue, sourced from the spec-ID sort key (not queue_position)."""
    root = _bootstrap_repo_with_decimals(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts, live_version="1.40.0")
    # Find the queue table and confirm the three spec IDs appear in the
    # interleaved order. The queue panel is wrapped in `data-pager-target`.
    queue_start = html.find('aria-label="Queue"')
    assert queue_start != -1
    queue_end = html.find("</section>", queue_start)
    queue_html = html[queue_start:queue_end]
    idx_170 = queue_html.find(">0170<")
    idx_170_1 = queue_html.find(">0170.1<")
    idx_171 = queue_html.find(">0171<")
    assert 0 < idx_170 < idx_170_1 < idx_171, (
        f"expected queue order 0170 < 0170.1 < 0171, got "
        f"positions {idx_170}, {idx_170_1}, {idx_171}"
    )
