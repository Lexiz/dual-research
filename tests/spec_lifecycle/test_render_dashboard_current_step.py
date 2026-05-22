"""Spec 0163 — hero surfaces the latest event as `data-current-step` plus chips."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import collect, render_index


def _bootstrap(tmp_path: Path, latest_step: str, latest_ts: str) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "drafts").mkdir()
    (tmp_path / "handoffs").mkdir()
    events_dir = tmp_path / "dashboard" / "events"
    events_dir.mkdir(parents=True)
    (specs / "0200-flight.md").write_text(
        '---\nkind: dev\nspec: "0200"\nslug: flight\ntitle: Flight\n'
        'type: new-feature\nstatus: in_progress\nstarted_at: "2026-05-22T10:00:00Z"\n---\nbody\n'
    )
    (events_dir / "0200.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"cycle_started","data":{}}\n'
        '{"ts":"2026-05-22T10:00:30Z","step":"preflight_ok","data":{}}\n'
        '{"ts":"2026-05-22T10:01:00Z","step":"in_progress","data":{}}\n'
        '{"ts":"2026-05-22T10:01:30Z","step":"branched","data":{"branch":"spec/0200-flight"}}\n'
        f'{{"ts":"{latest_ts}","step":"{latest_step}","data":{{}}}}\n'
    )
    return tmp_path


def test_hero_has_data_current_step_attribute(tmp_path: Path) -> None:
    root = _bootstrap(tmp_path, "implementing_started", "2026-05-22T10:02:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert 'data-current-step="implementing_started"' in html


def test_hero_carries_human_label_for_current_step(tmp_path: Path) -> None:
    root = _bootstrap(tmp_path, "implementing_started", "2026-05-22T10:02:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # Friendly label appears in the chip.
    assert "currently · implementing" in html


def test_staleness_chip_data_last_event_at(tmp_path: Path) -> None:
    root = _bootstrap(tmp_path, "tests_started", "2026-05-22T10:02:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    assert 'data-last-event-at="2026-05-22T10:02:00Z"' in html
    assert "chip-stale" in html
    # Some tone class must be set.
    assert any(tone in html for tone in ("tone-ok", "tone-warn", "tone-err"))


def test_unknown_step_uses_fallback_label(tmp_path: Path) -> None:
    root = _bootstrap(tmp_path, "future_step_name", "2026-05-22T10:02:00Z")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # Fallback: underscores → spaces.
    assert 'data-current-step="future_step_name"' in html
    assert "currently · future step name" in html
