"""Renderer reads cycle state from queue-state.json (spec 0202 §2.5, §6).

Covers two cases:

1. When queue-state.json has an entry for a spec, the renderer uses it
   even if the spec frontmatter still carries stale values.
2. When no entry exists (legacy / un-backfilled), the renderer falls
   back to the spec frontmatter.

Also exercises ``read_events``'s queue-state-first behaviour (spec §2.4).
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.spec_lifecycle.append_event import read_events
from scripts.spec_lifecycle.queue_state import (
    QUEUE_STATE_REL_PATH,
    append_event_to_state,
    update_state,
)
from scripts.spec_lifecycle.render_dashboard import collect


def _write_spec(path: Path, *, frontmatter: dict, body: str = "# body\n") -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n\n{body}")


def _fixture_repo(tmp_path: Path) -> Path:
    """Skeleton repo: specs/ + dashboard/events/ folders."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)
    return tmp_path


def test_renderer_reads_status_from_queue_state(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={
            "kind": "dev",
            "spec": "0152",
            "title": "Foo",
            "type": "new-feature",
            "status": "queued",  # stale — pre-state-file value
            "started_at": "",
            "deployed_at": "",
        },
    )
    update_state(
        repo,
        "0152",
        status="deployed",
        started_at="2026-05-22T12:00:00Z",
        deployed_at="2026-05-22T13:15:00Z",
        target_version="1.36.0",
    )

    specs, _drafts = collect(repo)
    assert len(specs) == 1
    row = specs[0]
    assert row.status == "deployed"  # state value, not the stale frontmatter
    assert row.fm["started_at"] == "2026-05-22T12:00:00Z"
    assert row.fm["deployed_at"] == "2026-05-22T13:15:00Z"
    assert row.target_version == "1.36.0"
    assert row.cycle_seconds == 4500  # 1h15m


def test_renderer_falls_back_to_frontmatter_when_no_state_entry(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0150-bar.md",
        frontmatter={
            "kind": "dev",
            "spec": "0150",
            "title": "Bar",
            "type": "bug",
            "status": "deployed",
            "started_at": "2026-05-01T10:00:00Z",
            "deployed_at": "2026-05-01T11:00:00Z",
        },
    )
    # No queue-state.json at all — renderer must not crash and must read fm.

    specs, _drafts = collect(repo)
    row = specs[0]
    assert row.status == "deployed"
    assert row.cycle_seconds == 3600


def test_renderer_layers_only_mutable_fields(tmp_path: Path) -> None:
    """Title and type come from frontmatter; state never overrides them."""
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={
            "kind": "dev",
            "spec": "0152",
            "title": "Frontmatter Title",
            "type": "new-feature",
            "status": "queued",
        },
    )
    update_state(repo, "0152", status="deployed")
    specs, _ = collect(repo)
    row = specs[0]
    assert row.title == "Frontmatter Title"  # immutable
    assert row.type == "new-feature"  # immutable
    assert row.status == "deployed"  # layered


def test_renderer_reads_events_from_queue_state(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={
            "kind": "dev",
            "spec": "0152",
            "title": "Foo",
            "type": "new-feature",
            "status": "in_progress",
        },
    )
    append_event_to_state(repo, "0152", "cycle_started", ts="2026-05-22T12:00:00Z")
    append_event_to_state(repo, "0152", "in_progress", ts="2026-05-22T12:00:30Z")

    specs, _ = collect(repo)
    row = specs[0]
    assert [e["step"] for e in row.events] == ["cycle_started", "in_progress"]


def test_renderer_reads_events_from_sidecar_when_state_has_none(tmp_path: Path) -> None:
    """A spec without a queue-state entry still gets events from its sidecar."""
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0150-bar.md",
        frontmatter={
            "kind": "dev",
            "spec": "0150",
            "title": "Bar",
            "type": "bug",
            "status": "deployed",
        },
    )
    sidecar = repo / "dashboard" / "events" / "0150.jsonl"
    sidecar.write_text(
        json.dumps({"ts": "2026-05-01T10:00:00Z", "step": "queued", "data": {}}) + "\n"
        + json.dumps({"ts": "2026-05-01T10:30:00Z", "step": "deployed", "data": {}}) + "\n"
    )
    specs, _ = collect(repo)
    row = specs[0]
    assert [e["step"] for e in row.events] == ["queued", "deployed"]


def test_read_events_shim_prefers_queue_state(tmp_path: Path) -> None:
    """read_events itself prefers queue-state over the sidecar (§2.4 shim)."""
    repo = _fixture_repo(tmp_path)
    events_dir = repo / "dashboard" / "events"
    # Both sources exist; state should win.
    append_event_to_state(repo, "0152", "from_state")
    (events_dir / "0152.jsonl").write_text(
        json.dumps({"ts": "old", "step": "from_sidecar", "data": {}}) + "\n"
    )
    events = read_events(events_dir, "0152")
    assert [e["step"] for e in events] == ["from_state"]


def test_read_events_shim_falls_back_to_sidecar(tmp_path: Path) -> None:
    """When the spec has no state entry, the sidecar is the source."""
    repo = _fixture_repo(tmp_path)
    events_dir = repo / "dashboard" / "events"
    # state file exists but doesn't mention this spec
    update_state(repo, "0152", status="deployed")
    (events_dir / "0150.jsonl").write_text(
        json.dumps({"ts": "t1", "step": "queued", "data": {}}) + "\n"
    )
    events = read_events(events_dir, "0150")
    assert [e["step"] for e in events] == ["queued"]


def test_read_events_legacy_callers_still_work(tmp_path: Path) -> None:
    """Test fixtures that pass a bare tmp_path keep working (no queue-state)."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "0001.jsonl").write_text(
        json.dumps({"ts": "t1", "step": "queued", "data": {}}) + "\n"
    )
    events = read_events(events_dir, "0001")
    assert [e["step"] for e in events] == ["queued"]


def test_renderer_handles_decimal_spec_ids(tmp_path: Path) -> None:
    """Decimal IDs (spec 0199) round-trip cleanly between renderer and state."""
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0170.1-sub.md",
        frontmatter={
            "kind": "dev",
            "spec": "0170.1",
            "title": "Sub",
            "type": "bug",
            "status": "queued",
        },
    )
    update_state(repo, "0170.1", status="deployed")
    specs, _ = collect(repo)
    row = specs[0]
    assert row.number == "0170.1"
    assert row.status == "deployed"


def test_state_file_path_constant_matches_spec(tmp_path: Path) -> None:
    """Spec §2.1 names ``dashboard/queue-state.json``; constant matches."""
    update_state(tmp_path, "0202", status="queued")
    assert (tmp_path / QUEUE_STATE_REL_PATH).exists()
    assert QUEUE_STATE_REL_PATH == "dashboard/queue-state.json"
