"""Tests for spec 0203.2 §3.1 — `current_queue` overlays queue-state.json.

Frontmatter `status` is frozen at queue time per spec 0202 §2.1; live
cycle-mutable status lives in `dashboard/queue-state.json`. The picker
must consult queue-state and drop specs whose live status is anything
other than `queued` (deployed, merged, in_progress, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.spec_lifecycle.pick_next_number import current_queue


def _write_spec(specs_dir: Path, number: str, *, slug: str = "fixture") -> Path:
    """Write a minimal queued-dev spec — frontmatter status frozen at `queued`.

    Carries `disposition: ship` so the spec 0251 §2.1 gate treats it as
    runnable; these tests exercise the queue-state *overlay* behaviour, which
    is orthogonal to the disposition gate (covered in
    ``tests/test_spec_0251_disposition_gate.py``).
    """
    body = f"""---
kind: dev
spec: "{number}"
slug: {slug}
status: queued
disposition: ship
---

# Spec {number} fixture
"""
    path = specs_dir / f"{number}-{slug}.md"
    path.write_text(body)
    return path


def _write_queue_state(repo_root: Path, specs: dict[str, dict]) -> Path:
    """Write a minimal queue-state.json under repo_root."""
    dashboard = repo_root / "dashboard"
    dashboard.mkdir(parents=True, exist_ok=True)
    path = dashboard / "queue-state.json"
    path.write_text(json.dumps({
        "version": 1,
        "updated_at": "2026-05-24T00:00:00Z",
        "specs": specs,
    }))
    return path


def test_current_queue_drops_specs_deployed_in_queue_state(tmp_path: Path) -> None:
    """A spec frozen at `queued` in frontmatter but `deployed` in queue-state
    must drop out of the queue — pre-0203.2 it would be returned as head."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001", slug="real-queued")
    _write_spec(specs_dir, "0002", slug="stale-frontmatter")
    _write_queue_state(tmp_path, {
        "0002": {"status": "deployed", "events": []},
    })

    result = current_queue(specs_dir)
    spec_ids = [sid for sid, _ in result]
    assert spec_ids == ["0001"], (
        f"expected only 0001 (live queued), got {spec_ids}. "
        "Pre-fix this returned both 0001 and 0002 because the filter "
        "trusted frozen frontmatter status."
    )


def test_current_queue_drops_specs_in_progress_in_queue_state(tmp_path: Path) -> None:
    """Specs whose live status is `in_progress` or `merged` should also drop."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001", slug="real-queued")
    _write_spec(specs_dir, "0002", slug="in-progress-frozen")
    _write_spec(specs_dir, "0003", slug="merged-frozen")
    _write_queue_state(tmp_path, {
        "0002": {"status": "in_progress", "events": []},
        "0003": {"status": "merged", "events": []},
    })

    result = current_queue(specs_dir)
    spec_ids = [sid for sid, _ in result]
    assert spec_ids == ["0001"]


def test_current_queue_falls_back_when_queue_state_missing(tmp_path: Path) -> None:
    """Missing `dashboard/queue-state.json` must not crash — fall back to
    the legacy frontmatter-only filter. Defensive parity with renderer."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_spec(specs_dir, "0002")

    result = current_queue(specs_dir)
    spec_ids = [sid for sid, _ in result]
    assert spec_ids == ["0001", "0002"]


def test_current_queue_returns_specs_queued_in_both(tmp_path: Path) -> None:
    """The happy path: a spec just written by `/spec-queue` has matching
    frontmatter and queue-state status. Overlay returns `queued`, filter
    accepts. Behaviour preservation for never-cycled specs."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_spec(specs_dir, "0002")
    _write_queue_state(tmp_path, {
        "0001": {"status": "queued", "events": []},
        "0002": {"status": "queued", "events": []},
    })

    result = current_queue(specs_dir)
    spec_ids = [sid for sid, _ in result]
    assert spec_ids == ["0001", "0002"]


def test_current_queue_handles_decimal_child_ids(tmp_path: Path) -> None:
    """Spec IDs like `0203.2` must look up cleanly in queue-state.json."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0203", slug="parent")
    _write_spec(specs_dir, "0203.1", slug="child-deployed")
    _write_spec(specs_dir, "0203.2", slug="child-queued")
    _write_queue_state(tmp_path, {
        "0203": {"status": "deployed", "events": []},
        "0203.1": {"status": "deployed", "events": []},
        "0203.2": {"status": "queued", "events": []},
    })

    result = current_queue(specs_dir)
    spec_ids = [sid for sid, _ in result]
    assert spec_ids == ["0203.2"]
