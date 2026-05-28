"""Tests for spec 0203.2 §3.3, §3.4 — supervisor helpers overlay queue-state.

`_read_spec_status` (called between iterations) and `_find_resume_target`
(called at pre-flight) must read live cycle-mutable status from
`dashboard/queue-state.json`, not frozen frontmatter. Pre-0203.2 both
functions read frontmatter and were silently non-functional post-0202
because frontmatter status is always `queued` on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.queue_drain_supervisor import _find_resume_target, _read_spec_status


def _write_spec(specs_dir: Path, number: str, *, slug: str = "fixture") -> Path:
    """Write a minimal queued-dev spec — frontmatter status frozen at `queued`."""
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


def _write_checkpoint_handoff(
    handoffs_dir: Path,
    spec_number: str,
    *,
    next_subsection: str = "2.2",
) -> Path:
    """Write a checkpoint handoff in the post-0186 shape."""
    body = f"""---
spec: "{spec_number}"
date: 2026-05-24
kind: in-spec-checkpoint
branch: spec/{spec_number}-fixture
branch_sha: abc1234
completed_subsections: ["2.1"]
next_subsection: "{next_subsection}"
tests_status: green
version_bumped: false
changelog_written: false
---

# Spec {spec_number} — checkpoint
"""
    path = handoffs_dir / f"2026-05-24-spec-{spec_number}-fixture.md"
    path.write_text(body)
    return path


# ── _read_spec_status ─────────────────────────────────────────────────


def test_read_spec_status_prefers_queue_state(tmp_path: Path) -> None:
    """When queue-state says `in_progress` and frontmatter says `queued`,
    the function must return `in_progress`. This is the signal the
    supervisor uses to re-pick the same spec via resume mode — pre-0203.2
    it always returned `queued` (frontmatter), so resume mode never fired.
    """
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_queue_state(tmp_path, {
        "0001": {"status": "in_progress", "events": []},
    })

    assert _read_spec_status(specs_dir, "0001") == "in_progress"


def test_read_spec_status_falls_back_when_queue_state_missing(tmp_path: Path) -> None:
    """Missing queue-state.json must not crash — fall back to frontmatter."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0001")

    assert _read_spec_status(specs_dir, "0001") == "queued"


def test_read_spec_status_returns_none_when_spec_missing(tmp_path: Path) -> None:
    """A spec number not on disk returns None — unchanged behaviour."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()

    assert _read_spec_status(specs_dir, "9999") is None


def test_read_spec_status_handles_decimal_child_ids(tmp_path: Path) -> None:
    """Decimal child IDs (e.g. `0203.2`) must look up cleanly."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _write_spec(specs_dir, "0203.2", slug="child")
    _write_queue_state(tmp_path, {
        "0203.2": {"status": "deployed", "events": []},
    })

    assert _read_spec_status(specs_dir, "0203.2") == "deployed"


# ── _find_resume_target ───────────────────────────────────────────────


def test_find_resume_target_uses_queue_state_status(tmp_path: Path) -> None:
    """A spec whose live status is `in_progress` AND has an active
    checkpoint handoff must be returned. Pre-0203.2 the function filtered
    by frontmatter and unconditionally returned None.
    """
    specs_dir = tmp_path / "specs"
    handoffs_dir = tmp_path / "handoffs"
    specs_dir.mkdir()
    handoffs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_queue_state(tmp_path, {
        "0001": {"status": "in_progress", "events": []},
    })
    _write_checkpoint_handoff(handoffs_dir, "0001")

    assert _find_resume_target(handoffs_dir, specs_dir) == "0001"


def test_find_resume_target_returns_none_for_queued_specs(tmp_path: Path) -> None:
    """Specs that are actually queued (in both frontmatter and queue-state)
    must NOT be flagged as resume targets. Locks in no-false-positive."""
    specs_dir = tmp_path / "specs"
    handoffs_dir = tmp_path / "handoffs"
    specs_dir.mkdir()
    handoffs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_queue_state(tmp_path, {
        "0001": {"status": "queued", "events": []},
    })

    assert _find_resume_target(handoffs_dir, specs_dir) is None


def test_find_resume_target_returns_none_when_no_checkpoint(tmp_path: Path) -> None:
    """A spec in_progress but with no active checkpoint handoff must NOT
    be returned — the checkpoint presence is the second predicate."""
    specs_dir = tmp_path / "specs"
    handoffs_dir = tmp_path / "handoffs"
    specs_dir.mkdir()
    handoffs_dir.mkdir()
    _write_spec(specs_dir, "0001")
    _write_queue_state(tmp_path, {
        "0001": {"status": "in_progress", "events": []},
    })

    assert _find_resume_target(handoffs_dir, specs_dir) is None


def test_find_resume_target_falls_back_when_queue_state_missing(tmp_path: Path) -> None:
    """Missing queue-state.json must not crash — falls back to frontmatter.
    Since frontmatter status is always `queued` post-0202, this returns None
    for the realistic case, which is the safe default.
    """
    specs_dir = tmp_path / "specs"
    handoffs_dir = tmp_path / "handoffs"
    specs_dir.mkdir()
    handoffs_dir.mkdir()
    _write_spec(specs_dir, "0001")

    assert _find_resume_target(handoffs_dir, specs_dir) is None
