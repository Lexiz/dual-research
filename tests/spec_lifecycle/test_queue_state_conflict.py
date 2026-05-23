"""Concurrent-write + monotonicity tests for queue_state (spec 0202 §6).

Mirrors the bare-remote + working-clone pattern used by
``test_push_event_to_main.py`` so the concurrency assertions exercise the
real ``git push origin`` round-trip rather than a mock.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.spec_lifecycle.queue_state import (
    QUEUE_STATE_REL_PATH,
    QueueState,
    _apply_updates,
    append_event_to_state,
    read_state,
    update_state,
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
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
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
    (clone / "dashboard").mkdir(parents=True)
    (clone / "README.md").write_text("seed\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-m", "seed")
    _git(clone, "push", "-u", "origin", "main")
    return remote, clone


def _state_on_main(clone: Path) -> dict:
    _git(clone, "fetch", "--quiet", "origin", "main")
    cat = subprocess.run(
        ["git", "cat-file", "-p", f"origin/main:{QUEUE_STATE_REL_PATH}"],
        cwd=str(clone),
        capture_output=True,
        text=True,
    )
    if cat.returncode != 0:
        return {}
    return json.loads(cat.stdout)


# --- Conflict-safety: race retry preserves the concurrent writer ------------

def test_update_state_push_to_main_happy_path(repo_pair: tuple[Path, Path]) -> None:
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0202-foo")

    update_state(
        clone,
        "0202",
        status="in_progress",
        started_at="2026-05-24T12:00:00Z",
        push_to_main=True,
        repo_dir=clone,
    )

    on_main = _state_on_main(clone)
    assert on_main["specs"]["0202"]["status"] == "in_progress"
    assert on_main["specs"]["0202"]["started_at"] == "2026-05-24T12:00:00Z"
    assert (clone / QUEUE_STATE_REL_PATH).exists()


def test_update_state_race_preserves_concurrent_events(
    repo_pair: tuple[Path, Path]
) -> None:
    """A second clone advances main with its own event; the first clone's
    retry re-reads origin and preserves it instead of clobbering."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0202-bar")

    # Seed an initial state on main from the first clone.
    update_state(
        clone, "0202", status="in_progress", push_to_main=True, repo_dir=clone
    )

    # Second clone races a different event in.
    second = clone.parent / "second"
    _git(clone.parent, "clone", str(_remote), str(second))
    _git(second, "config", "user.email", "racer@example.com")
    _git(second, "config", "user.name", "Racer")
    _git(second, "checkout", "-b", "spec/0202-racer")
    append_event_to_state(
        second,
        "0202",
        "racer_event",
        {"who": "second"},
        ts="2026-05-24T12:30:00Z",
        push_to_main=True,
        repo_dir=second,
    )

    # Now the first clone pushes its own event. Its locally-cached
    # origin/main is stale; the push must retry, re-read, and preserve the
    # racer's event.
    append_event_to_state(
        clone,
        "0202",
        "first_event",
        {"who": "first"},
        ts="2026-05-24T12:35:00Z",
        push_to_main=True,
        repo_dir=clone,
    )

    on_main = _state_on_main(clone)
    steps = [e["step"] for e in on_main["specs"]["0202"]["events"]]
    assert "racer_event" in steps
    assert "first_event" in steps


def test_update_state_failure_leaves_local_untouched(
    repo_pair: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """When push permanently fails, the local working-tree file is not
    written. The caller can halt cleanly per spec §2.1."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0202-baz")

    # Break the remote so push always fails.
    bad_remote = clone.parent / "does-not-exist.git"
    _git(clone, "remote", "set-url", "origin", str(bad_remote))

    with pytest.raises(RuntimeError, match="push to origin/main failed"):
        update_state(
            clone, "0202", status="in_progress", push_to_main=True, repo_dir=clone
        )

    # Local file was not written (no successful push).
    assert not (clone / QUEUE_STATE_REL_PATH).exists()
    assert "queue_state push failed" in capsys.readouterr().err


# --- Monotonicity (events array cannot shrink) -----------------------------

def test_apply_updates_rejects_shorter_events_replace(tmp_path: Path) -> None:
    """events_replace must be at least as long as the on-disk events array
    — defends against clobbering a concurrent writer's events."""
    update_state(
        tmp_path,
        "0202",
        events_append=[
            {"ts": "t1", "step": "a", "data": {}},
            {"ts": "t2", "step": "b", "data": {}},
            {"ts": "t3", "step": "c", "data": {}},
        ],
    )
    state = read_state(tmp_path)
    with pytest.raises(ValueError, match="refusing to shrink events"):
        _apply_updates(
            state,
            "0202",
            fields={},
            events_append=None,
            events_replace=[{"ts": "x", "step": "x", "data": {}}],
            now_iso="now",
        )


def test_apply_updates_allows_equal_length_events_replace(tmp_path: Path) -> None:
    """Equal length is fine — caller may be rewriting the same events with
    corrected metadata."""
    update_state(
        tmp_path,
        "0202",
        events_append=[
            {"ts": "t1", "step": "a", "data": {}},
            {"ts": "t2", "step": "b", "data": {}},
        ],
    )
    state = read_state(tmp_path)
    _apply_updates(
        state,
        "0202",
        fields={},
        events_append=None,
        events_replace=[
            {"ts": "t1", "step": "a", "data": {"fixed": True}},
            {"ts": "t2", "step": "b", "data": {}},
        ],
        now_iso="now",
    )
    assert state.specs["0202"]["events"][0]["data"] == {"fixed": True}


def test_events_append_is_unconditionally_additive(tmp_path: Path) -> None:
    append_event_to_state(tmp_path, "0202", "a")
    append_event_to_state(tmp_path, "0202", "b")
    append_event_to_state(tmp_path, "0202", "c")
    events = read_state(tmp_path).specs["0202"]["events"]
    assert [e["step"] for e in events] == ["a", "b", "c"]
