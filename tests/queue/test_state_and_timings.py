"""Tests for queue_v2.state + queue_v2.timings."""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.queue_v2 import state, timings


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    # Simulate a repo root by dropping a pyproject.toml.
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    return tmp_path


def test_init_queue_then_begin_spec_round_trip(repo: Path) -> None:
    state.init_queue(["0092", "0093", "0094"], repo_root=repo)
    s = state.load(repo)
    assert s.queue == ["0092", "0093", "0094"]
    assert s.active is None

    state.begin_spec("0092", "m3", "spec/0092-m3", repo_root=repo)
    s = state.load(repo)
    assert s.queue == ["0093", "0094"]
    assert s.active and s.active["spec"] == "0092"
    assert all(meta["status"] == "pending" for meta in s.active["steps"].values())


def test_begin_and_end_step_records_duration(repo: Path) -> None:
    state.init_queue(["0092"], repo_root=repo)
    state.begin_spec("0092", "m3", "spec/0092-m3", repo_root=repo)
    state.begin_step("1_read", repo_root=repo)
    state.end_step("1_read", "done", {"files_touched_count": 5}, repo_root=repo)

    s = state.load(repo)
    step = s.active["steps"]["1_read"]
    assert step["status"] == "done"
    assert step["duration_s"] >= 0
    assert s.active["detail"]["1_read"]["files_touched_count"] == 5


def test_skipped_step_does_not_record_timing(repo: Path) -> None:
    state.init_queue(["0092"], repo_root=repo)
    state.begin_spec("0092", "m3", "spec/0092-m3", repo_root=repo)
    state.begin_step("3_rewrite", repo_root=repo)
    state.end_step(
        "3_rewrite", "skipped", {"reason": "none"}, repo_root=repo
    )

    payload = timings.load(repo)
    assert payload["step_durations"]["3_rewrite"] == []


def test_timings_median_across_runs(repo: Path) -> None:
    state.init_queue(["0092"], repo_root=repo)
    timings.record("4_implement", 1800, repo_root=repo)
    timings.record("4_implement", 2200, repo_root=repo)
    timings.record("4_implement", 1900, repo_root=repo)
    assert timings.median("4_implement", repo_root=repo) == 1900


def test_failure_state_persists_on_step_failed(repo: Path) -> None:
    state.init_queue(["0092"], repo_root=repo)
    state.begin_spec("0092", "m3", "spec/0092-m3", repo_root=repo)
    state.begin_step("1_read", repo_root=repo)
    state.end_step("1_read", "failed", {"error": "boom"}, repo_root=repo)

    s = state.load(repo)
    assert s.failure is not None
    assert s.failure["step"] == "1_read"
    assert s.failure["spec"] == "0092"


def test_finish_spec_promotes_to_completed(repo: Path) -> None:
    state.init_queue(["0092"], repo_root=repo)
    state.begin_spec("0092", "m3", "spec/0092-m3", repo_root=repo)
    state.finish_spec(repo_root=repo)

    s = state.load(repo)
    assert s.completed == ["0092"]
    assert s.active is None
