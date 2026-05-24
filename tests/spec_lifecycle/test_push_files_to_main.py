"""Round-trip tests for push_files_to_main + detached-HEAD resync (spec 0210).

Uses the same bare-remote + working-clone fixture pattern as
``test_queue_state_conflict.py`` so the multi-file plumbing exercises a real
``git push origin`` round-trip rather than a mock.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.spec_lifecycle.queue_state import (
    _resync_detached_head_to_origin_main,
    push_files_to_main,
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
    (clone / "handoffs").mkdir()
    (clone / "handoffs" / "seed.md").write_text("seed handoff\n")
    (clone / "README.md").write_text("seed\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-m", "seed")
    _git(clone, "push", "-u", "origin", "main")
    return remote, clone


def _read_blob_from_main(clone: Path, rel_path: str) -> str | None:
    _git(clone, "fetch", "--quiet", "origin", "main")
    res = subprocess.run(
        ["git", "cat-file", "-p", f"origin/main:{rel_path}"],
        cwd=str(clone),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return None
    return res.stdout


def test_push_files_to_main_writes_multiple_files_in_one_commit(
    repo_pair: tuple[Path, Path],
) -> None:
    _remote, clone = repo_pair
    # Land an arbitrary feature branch first to ensure we test from a non-main ref.
    _git(clone, "checkout", "-b", "spec/0210-foo")

    payload = [
        ("dashboard/queue-state.json", '{"specs": {"0210": {"status": "deployed"}}}\n'),
        ("handoffs/2026-05-24-spec-0210-foo.md", "---\nspec: \"0210\"\n---\n\nlanded.\n"),
    ]
    ok = push_files_to_main(payload, "spec(0210): test commit", clone)
    assert ok

    qs = _read_blob_from_main(clone, "dashboard/queue-state.json")
    assert qs is not None and '"0210"' in qs
    hf = _read_blob_from_main(clone, "handoffs/2026-05-24-spec-0210-foo.md")
    assert hf is not None and "landed." in hf

    # Single commit (one commit-tree call), parent is the prior main tip.
    log = _git(clone, "log", "origin/main", "--oneline", "-n", "2").stdout
    assert "spec(0210): test commit" in log


def test_push_files_to_main_supports_deletions(
    repo_pair: tuple[Path, Path],
) -> None:
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0210-bar")

    # Seed a file to delete via a separate add-push first.
    push_files_to_main(
        [("handoffs/will-go.md", "to be deleted\n")],
        "seed file to delete",
        clone,
    )
    assert _read_blob_from_main(clone, "handoffs/will-go.md") is not None

    # Now push a payload that deletes it AND adds a new file.
    ok = push_files_to_main(
        [
            ("handoffs/will-go.md", None),
            ("handoffs/archive/2026-05/will-go.md", "moved to archive\n"),
        ],
        "spec(0210): archive move",
        clone,
    )
    assert ok
    assert _read_blob_from_main(clone, "handoffs/will-go.md") is None
    archived = _read_blob_from_main(clone, "handoffs/archive/2026-05/will-go.md")
    assert archived == "moved to archive\n"


def test_push_files_to_main_retries_on_non_fast_forward(
    repo_pair: tuple[Path, Path], tmp_path: Path,
) -> None:
    """A second clone advances origin/main; the first clone's push retries,
    rebuilds the tree on top of the new origin/main, and succeeds."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0210-baz")

    # Second clone lands its own commit on main, advancing origin/main.
    second = tmp_path / "second"
    _git(tmp_path, "clone", str(_remote), str(second))
    _git(second, "config", "user.email", "racer@example.com")
    _git(second, "config", "user.name", "Racer")
    _git(second, "checkout", "-b", "spec/0210-racer")
    push_files_to_main(
        [("handoffs/racer.md", "racer landed\n")],
        "racer commit",
        second,
    )

    # First clone's locally-cached origin/main is stale; push must retry.
    ok = push_files_to_main(
        [("handoffs/first.md", "first landed\n")],
        "first commit",
        clone,
    )
    assert ok
    # Both files present on origin/main after the retry.
    assert _read_blob_from_main(clone, "handoffs/racer.md") == "racer landed\n"
    assert _read_blob_from_main(clone, "handoffs/first.md") == "first landed\n"


def test_resync_detached_head_advances_to_origin_main(
    repo_pair: tuple[Path, Path],
) -> None:
    _remote, clone = repo_pair
    # Re-detach the queue clone at origin/main (the new resting state per spec 0210).
    _git(clone, "fetch", "--quiet", "origin", "main")
    _git(clone, "checkout", "--detach", "origin/main")
    detached_sha_before = _git(clone, "rev-parse", "HEAD").stdout.strip()

    # Push a new file via plumbing — advances origin/main but NOT the detached HEAD.
    push_files_to_main(
        [("handoffs/new.md", "new file\n")],
        "spec(0210): new file",
        clone,
    )
    new_origin_sha = _git(clone, "rev-parse", "origin/main").stdout.strip()
    assert new_origin_sha != detached_sha_before

    # Local HEAD is still at the pre-push commit until we resync.
    assert _git(clone, "rev-parse", "HEAD").stdout.strip() == detached_sha_before

    resynced = _resync_detached_head_to_origin_main(clone)
    assert resynced is True
    assert _git(clone, "rev-parse", "HEAD").stdout.strip() == new_origin_sha


def test_resync_is_noop_when_head_is_on_a_branch(
    repo_pair: tuple[Path, Path],
) -> None:
    """Branch refs are NOT advanced — would be destructive."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0210-on-branch")
    branch_sha_before = _git(clone, "rev-parse", "HEAD").stdout.strip()

    push_files_to_main(
        [("handoffs/x.md", "x\n")],
        "spec(0210): x",
        clone,
    )

    resynced = _resync_detached_head_to_origin_main(clone)
    assert resynced is False
    # Branch ref unchanged.
    assert _git(clone, "rev-parse", "HEAD").stdout.strip() == branch_sha_before


def test_push_files_to_main_failure_does_not_raise(
    repo_pair: tuple[Path, Path], tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Permanent push failure returns False; warning written to stderr."""
    _remote, clone = repo_pair
    _git(clone, "checkout", "-b", "spec/0210-broken")
    bad_remote = tmp_path / "does-not-exist.git"
    _git(clone, "remote", "set-url", "origin", str(bad_remote))

    ok = push_files_to_main(
        [("handoffs/x.md", "x\n")],
        "will fail",
        clone,
    )
    assert ok is False
    assert "push_files_to_main failed" in capsys.readouterr().err
