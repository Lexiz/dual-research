"""Tests for the one-time backfill (spec 0202 §2.6, §6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.spec_lifecycle.build_queue_state import (
    COPIED_FRONTMATTER_FIELDS,
    build_state_from_repo,
    run_backfill,
)
from scripts.spec_lifecycle.queue_state import QUEUE_STATE_REL_PATH


def _write_spec(path: Path, *, frontmatter: dict, body: str = "# body\n") -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n\n{body}")


def _write_handoff(path: Path, frontmatter_lines: list[str], body: str = "body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(frontmatter_lines)
    path.write_text(f"---\n{fm}\n---\n\n{body}")


def _fixture_repo(tmp_path: Path) -> Path:
    (tmp_path / "specs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)
    (tmp_path / "handoffs").mkdir()
    return tmp_path


# --- build_state_from_repo (pure) ----------------------------------------

def test_build_state_copies_frontmatter_status(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={
            "kind": "dev",
            "spec": "0152",
            "title": "Foo",
            "type": "new-feature",
            "status": "deployed",
            "started_at": "2026-05-22T12:00:00Z",
            "deployed_at": "2026-05-22T13:15:00Z",
            "pr": "https://example/123",
            "target_version": "1.36.0",
            "handover": "handoffs/2026-05-22-spec-0152-foo.md",
        },
    )
    state = build_state_from_repo(repo)
    entry = state.specs["0152"]
    for field in COPIED_FRONTMATTER_FIELDS:
        if field in {"merged_at", "failure_step", "queued_at"}:
            continue  # not set on this fixture
        assert field in entry, f"missing {field}"
    assert entry["status"] == "deployed"
    assert entry["pr"] == "https://example/123"


def test_build_state_skips_empty_frontmatter_values(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={
            "kind": "dev",
            "spec": "0152",
            "title": "Foo",
            "type": "bug",
            "status": "queued",
            "deployed_at": "",  # empty string — should not be copied
            "pr": "",
        },
    )
    state = build_state_from_repo(repo)
    entry = state.specs["0152"]
    assert entry["status"] == "queued"
    assert "deployed_at" not in entry
    assert "pr" not in entry


def test_build_state_handles_decimal_ids(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0170-parent.md",
        frontmatter={"kind": "dev", "title": "Parent", "type": "bug", "status": "deployed"},
    )
    _write_spec(
        repo / "specs" / "0170.1-child.md",
        frontmatter={"kind": "dev", "title": "Child", "type": "bug", "status": "queued"},
    )
    state = build_state_from_repo(repo)
    assert "0170" in state.specs
    assert "0170.1" in state.specs


def test_build_state_loads_sidecar_events(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    (repo / "dashboard" / "events" / "0152.jsonl").write_text(
        json.dumps({"ts": "t1", "step": "queued", "data": {}}) + "\n"
        + json.dumps({"ts": "t2", "step": "deployed", "data": {}}) + "\n"
    )
    state = build_state_from_repo(repo)
    assert [e["step"] for e in state.specs["0152"]["events"]] == ["queued", "deployed"]


def test_build_state_includes_spec_with_no_sidecar(tmp_path: Path) -> None:
    """A spec that never produced events still gets an entry with events: []."""
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0001-old.md",
        frontmatter={"kind": "dev", "title": "Old", "type": "bug", "status": "deployed"},
    )
    state = build_state_from_repo(repo)
    assert state.specs["0001"]["events"] == []


def test_build_state_skips_non_spec_files(tmp_path: Path) -> None:
    """README, drafts, other junk in specs/ — backfill ignores them."""
    repo = _fixture_repo(tmp_path)
    (repo / "specs" / "README.md").write_text("nothing\n")
    (repo / "specs" / "weird.txt").write_text("nothing\n")
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "queued"},
    )
    state = build_state_from_repo(repo)
    assert set(state.specs.keys()) == {"0152"}


# --- run_backfill (end-to-end) ------------------------------------------

def test_run_backfill_writes_state_file(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    result = run_backfill(repo)
    assert result["skipped"] is False
    assert result["specs"] == 1
    assert (repo / QUEUE_STATE_REL_PATH).exists()


def test_run_backfill_archives_sidecars(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    (repo / "dashboard" / "events" / "0152.jsonl").write_text(
        json.dumps({"ts": "t1", "step": "queued", "data": {}}) + "\n"
    )
    result = run_backfill(repo)
    assert result["sidecars_archived"] == 1
    assert not (repo / "dashboard" / "events" / "0152.jsonl").exists()
    assert (repo / "dashboard" / "events" / "archive" / "0152.jsonl").exists()


def test_run_backfill_archives_handoffs(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    for n in range(25):
        (repo / "handoffs" / f"2026-04-{(n % 28) + 1:02d}-spec-{n:04d}-foo.md").write_text("body\n")
    result = run_backfill(repo, cap=20)
    assert result["handoffs_archived"] == 5


def test_run_backfill_protects_active_checkpoints(tmp_path: Path) -> None:
    """An in-flight L-spec's checkpoint handoff must not move into archive."""
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0202-inflight.md",
        frontmatter={"kind": "dev", "title": "Inflight", "type": "bug", "status": "in_progress"},
    )
    cp = repo / "handoffs" / "2026-01-01-spec-0202-cp.md"
    _write_handoff(cp, ['spec: "0202"', "kind: in-spec-checkpoint"])
    # Pad with enough other handoffs to push past the cap.
    for n in range(25):
        (repo / "handoffs" / f"2026-04-{(n % 28) + 1:02d}-spec-{n + 100:04d}-foo.md").write_text("body\n")

    result = run_backfill(repo, cap=20)
    assert cp.exists()  # protected, even though its date prefix is oldest
    assert any("spec-0202-cp" in p for p in result["protected_checkpoints"])


def test_run_backfill_is_idempotent(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    run_backfill(repo)
    state_path = repo / QUEUE_STATE_REL_PATH
    first_mtime = state_path.stat().st_mtime

    result = run_backfill(repo)
    assert result["skipped"] is True
    assert "nothing to do" in result["reason"]
    # File untouched.
    assert state_path.stat().st_mtime == first_mtime


def test_run_backfill_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.spec_lifecycle.build_queue_state import main as cli_main

    repo = _fixture_repo(tmp_path)
    _write_spec(
        repo / "specs" / "0152-foo.md",
        frontmatter={"kind": "dev", "title": "Foo", "type": "bug", "status": "deployed"},
    )
    rc = cli_main(["--repo-root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backfilled 1 specs" in out

    # Re-run: idempotent message.
    rc = cli_main(["--repo-root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nothing to do" in out
