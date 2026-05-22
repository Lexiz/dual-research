"""Tests for scripts.spec_lifecycle.append_event.push_event_to_main (spec 0163)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.spec_lifecycle.append_event import (
    append_event,
    push_event_to_main,
    read_events,
)


def _git(repo: Path, *args: str, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        **kwargs,
    )


@pytest.fixture
def repo_pair(tmp_path: Path) -> tuple[Path, Path]:
    """A bare 'remote' + a working clone, both with a main branch and an empty
    dashboard/events/ directory.
    """
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    # Ensure main is the default branch name in the bare repo.
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", "refs/heads/main"],
        cwd=str(remote),
        check=True,
    )

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(remote), str(clone))
    _git(clone, "config", "user.email", "test@example.com")
    _git(clone, "config", "user.name", "Test")
    _git(clone, "checkout", "-b", "main")
    (clone / "dashboard" / "events").mkdir(parents=True)
    (clone / "README.md").write_text("seed\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-m", "seed")
    _git(clone, "push", "-u", "origin", "main")
    return remote, clone


def _events_on_main(clone: Path, spec_id: str) -> list[dict]:
    """Read events as they currently appear on origin/main (not the working tree)."""
    _git(clone, "fetch", "--quiet", "origin", "main")
    cat = subprocess.run(
        ["git", "cat-file", "-p", f"origin/main:dashboard/events/{spec_id}.jsonl"],
        cwd=str(clone),
        capture_output=True,
        text=True,
    )
    if cat.returncode != 0:
        return []
    return [json.loads(line) for line in cat.stdout.strip().split("\n") if line.strip()]


def test_push_two_events_lands_two_commits_on_main(repo_pair: tuple[Path, Path]) -> None:
    """Happy path: two pushes land two commits with the correct appended lines."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0001-feature")

    line1 = json.dumps({"ts": "2026-05-22T10:00:00Z", "step": "implementing_started", "data": {}}) + "\n"
    line2 = json.dumps({"ts": "2026-05-22T10:01:00Z", "step": "tests_started", "data": {}}) + "\n"

    # Write both lines to the local file first (mimicking what append_event does).
    log = clone / "dashboard" / "events" / "0001.jsonl"
    log.write_text(line1)
    assert push_event_to_main("dashboard/events", "0001", line1, repo_dir=clone) is True

    log.write_text(line1 + line2)
    assert push_event_to_main("dashboard/events", "0001", line2, repo_dir=clone) is True

    events = _events_on_main(clone, "0001")
    assert [e["step"] for e in events] == ["implementing_started", "tests_started"]


def test_race_retry_rebuilds_atop_new_tip(repo_pair: tuple[Path, Path]) -> None:
    """When origin/main advances between fetch and push, the retry rebuilds on the new tip."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0002-feature")

    # Set up a second clone that will race a commit in.
    second = clone.parent / "second"
    _git(clone.parent, "clone", str(repo_pair[0]), str(second))
    _git(second, "config", "user.email", "racer@example.com")
    _git(second, "config", "user.name", "Racer")
    (second / "racer.txt").write_text("racer\n")
    _git(second, "add", "-A")
    _git(second, "commit", "-m", "racer commit")
    _git(second, "push", "origin", "main")

    # Now push our event — first attempt will lose the race (fetch grabs racer's
    # commit, but our locally-cached origin/main from clone time is stale).
    # The helper's retry should fetch and succeed.
    line = json.dumps({"ts": "2026-05-22T10:00:00Z", "step": "branched", "data": {}}) + "\n"
    log = clone / "dashboard" / "events" / "0002.jsonl"
    log.write_text(line)
    assert push_event_to_main("dashboard/events", "0002", line, repo_dir=clone) is True

    events = _events_on_main(clone, "0002")
    assert [e["step"] for e in events] == ["branched"]
    # And the racer's commit is still present on main.
    _git(clone, "fetch", "--quiet", "origin", "main")
    files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "origin/main"],
        cwd=str(clone), capture_output=True, text=True, check=True,
    ).stdout
    assert "racer.txt" in files


def test_no_op_when_on_main(repo_pair: tuple[Path, Path]) -> None:
    """When the local branch is already 'main', the helper short-circuits."""
    _remote, clone = repo_pair
    # We're on main from the fixture's setup.
    line = json.dumps({"ts": "2026-05-22T10:00:00Z", "step": "queued", "data": {}}) + "\n"
    assert push_event_to_main("dashboard/events", "0003", line, repo_dir=clone) is False

    # No new events file should be on origin/main.
    assert _events_on_main(clone, "0003") == []


def test_graceful_failure_when_push_fails(
    repo_pair: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """If the push can never succeed, the helper logs and returns False without raising."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0004-feature")

    # Break the remote so the push fails.
    bad_remote = clone.parent / "does-not-exist.git"
    _git(clone, "remote", "set-url", "origin", str(bad_remote))

    line = json.dumps({"ts": "2026-05-22T10:00:00Z", "step": "branched", "data": {}}) + "\n"
    log = clone / "dashboard" / "events" / "0004.jsonl"
    log.write_text(line)

    result = push_event_to_main("dashboard/events", "0004", line, repo_dir=clone)
    assert result is False
    # The local file is intact — the line is still there and will reach main
    # via the eventual squash-merge.
    assert read_events(clone / "dashboard" / "events", "0004") == [
        {"ts": "2026-05-22T10:00:00Z", "step": "branched", "data": {}}
    ]
    captured = capsys.readouterr()
    assert "push_event_to_main failed" in captured.err


def test_append_event_with_push_to_main_flag(repo_pair: tuple[Path, Path]) -> None:
    """append_event(push_to_main=True) writes locally AND pushes."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0005-feature")

    log = append_event(
        clone / "dashboard" / "events",
        "0005",
        "implementing_started",
        {},
        ts="2026-05-22T10:00:00Z",
        push_to_main=True,
        repo_dir=clone,
    )
    assert log.exists()
    events = _events_on_main(clone, "0005")
    assert len(events) == 1
    assert events[0]["step"] == "implementing_started"


def test_appending_to_existing_file_on_main(repo_pair: tuple[Path, Path]) -> None:
    """When the events file already has lines on main, push concatenates correctly."""
    _remote, clone = repo_pair
    # Seed an initial event on main first.
    line1 = json.dumps({"ts": "2026-05-22T09:00:00Z", "step": "queued", "data": {}}) + "\n"
    (clone / "dashboard" / "events" / "0006.jsonl").write_text(line1)
    _git(clone, "add", "dashboard/events/0006.jsonl")
    _git(clone, "commit", "-m", "seed events")
    _git(clone, "push", "origin", "main")

    # Now branch and push two more events.
    _git(clone, "checkout", "-b", "spec/0006-feature")
    line2 = json.dumps({"ts": "2026-05-22T10:00:00Z", "step": "branched", "data": {}}) + "\n"
    (clone / "dashboard" / "events" / "0006.jsonl").write_text(line1 + line2)
    assert push_event_to_main("dashboard/events", "0006", line2, repo_dir=clone)

    events = _events_on_main(clone, "0006")
    assert [e["step"] for e in events] == ["queued", "branched"]
