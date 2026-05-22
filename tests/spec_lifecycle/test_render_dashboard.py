"""Tests for scripts.spec_lifecycle.render_dashboard."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import collect, render_index


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
        'type: bug\nstatus: queued\nqueue_position: 1\n---\nbody\n'
    )
    (specs / "0103-in-flight.md").write_text(
        '---\nkind: dev\nspec: "0103"\nslug: in-flight\ntitle: In flight thing\n'
        'type: refactoring\nstatus: in_progress\nstarted_at: "2026-05-22T10:00:00Z"\n---\nbody\n'
    )
    (drafts / "draft-001-x.md").write_text(
        '---\nkind: draft\ndraft_id: "001"\nslug: x\ntitle: Draft thing\n'
        'type: unclassified\nstatus: draft\n---\nbody\n'
    )
    (events_dir / "0103.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"in_progress","data":{}}\n'
    )
    return tmp_path


def test_collect_finds_specs_and_drafts(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    assert len(specs) == 3
    assert len(drafts) == 1
    assert {s.status for s in specs} == {"deployed", "queued", "in_progress"}


def test_index_contains_all_sections(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert "In flight" in html
    assert "Queue" in html
    assert "Recently shipped" in html
    assert "Drafts" in html
    assert "All specs" in html
    assert "Metrics" in html
    # Spec links use filename-derived 4-digit ID
    assert 'href="spec-0101.html"' in html
    assert 'href="spec-0102.html"' in html
    assert 'href="spec-0103.html"' in html
    assert 'href="draft-001.html"' in html


def test_cycle_time_formatting(tmp_path: Path) -> None:
    root = _bootstrap_repo(tmp_path)
    specs, _ = collect(root)
    deployed = next(s for s in specs if s.status == "deployed")
    # 0101 deployed 1 hour after started
    assert deployed.cycle_seconds == 3600
