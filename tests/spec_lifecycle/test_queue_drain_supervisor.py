"""Tests for scripts.queue_drain_supervisor — spec 0191.

Covers ``drain_queue`` with an injected fake ``spawn_command`` so the
loop's mechanics are unit-tested without spawning a real ``claude``
subprocess. Four canonical scenarios per spec §4:

1. Empty queue → early return, zero iterations.
2. Two-spec happy path → both ship, ``failed is None``, two iterations.
3. Halt-on-failure → first spec ships, second's exit code != 0 halts the
   supervisor, log tail captured.
4. Resume-mode re-pick → fake spawn writes a checkpoint handoff and
   leaves the spec ``in_progress`` on the first call; second call
   completes it. ``iterations == 2``, ``completed == [spec]`` once.

Plus a few smaller assertions on the argv shape, log-tail content, and
``_default_now`` / ``_default_spawn_command`` defaults.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.queue_drain_supervisor import (
    DEFAULT_FAILURE_TAIL_LINES,
    DrainResult,
    _default_now,
    _read_log_tail,
    _tail,
    drain_queue,
)


def _write_spec(
    specs_dir: Path,
    number: str,
    *,
    status: str = "queued",
    queue_position: int = 1,  # kept for back-compat; ignored post spec 0199
    slug: str = "fixture",
    started_at: str = "",
) -> Path:
    """Write a minimal queued-dev spec file with the right frontmatter shape.

    Spec 0199 §2.4 — `queue_position` is no longer written. `current_queue`
    sorts by spec ID (`(parent, child)` tuple). The `queue_position` keyword
    is kept on this helper so existing call sites continue to read clearly
    ("position 1 first") even though the field itself is gone.
    """
    del queue_position  # explicitly unused — keeps the kwarg for call sites.
    # Spec 0251 §2.1 — `disposition: ship` so the picker gate treats queued
    # fixtures as runnable. Harmless on non-queued fixtures (they drop on
    # status). The gate itself is covered in test_spec_0251_disposition_gate.py.
    body = f"""---
kind: dev
spec: "{number}"
slug: {slug}
status: {status}
disposition: ship
"""
    if started_at:
        body += f'started_at: "{started_at}"\n'
    body += "---\n\n# Spec {number} fixture\n"
    path = specs_dir / f"{number}-{slug}.md"
    path.write_text(body)
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
date: 2026-05-23
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

## State at checkpoint

§2.1 done.

## Resume instructions

Resume at §{next_subsection}.
"""
    path = handoffs_dir / f"2026-05-23-spec-{spec_number}-fixture.md"
    path.write_text(body)
    return path


@pytest.fixture
def repo(tmp_path: Path) -> dict[str, Path]:
    """Per-test temp repo skeleton."""
    specs = tmp_path / "specs"
    specs.mkdir()
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    runs = tmp_path / "runs" / "queue-drain"
    runs.mkdir(parents=True)
    return {
        "root": tmp_path,
        "specs": specs,
        "handoffs": handoffs,
        "runs": runs,
    }


def _frozen_now() -> str:
    """Deterministic timestamp so test log paths are predictable."""
    return "2026-05-23T00-00-00Z"


# ── Test 1: empty queue ──────────────────────────────────────────────────


def test_empty_queue_returns_zero_iterations(repo: dict[str, Path]) -> None:
    """No queued specs → no iterations, no completed, no failure."""
    calls: list[list[str]] = []

    def fake_spawn(argv: list[str], log_path: Path) -> int:
        calls.append(argv)
        return 0

    result = drain_queue(
        specs_dir=repo["specs"],
        handoffs_dir=repo["handoffs"],
        runs_dir=repo["runs"],
        project_dir=repo["root"],
        spawn_command=fake_spawn,
        now=_frozen_now,
        quiet=True,
    )

    assert isinstance(result, DrainResult)
    assert result.iterations == 0
    assert result.completed == []
    assert result.failed is None
    assert result.failure_log_tail is None
    assert result.log_paths == []
    assert calls == []  # spawn was never invoked


# ── Test 2: two-spec happy path ──────────────────────────────────────────


def test_two_spec_happy_path_ships_both(repo: dict[str, Path]) -> None:
    """Two queued specs, both subprocess invocations return 0. Each
    iteration's fake also flips the spec to ``deployed`` so the loop
    advances to the next queue head."""
    _write_spec(repo["specs"], "0500", queue_position=1, slug="alpha")
    _write_spec(repo["specs"], "0501", queue_position=2, slug="beta")

    calls: list[tuple[list[str], Path]] = []

    def fake_spawn(argv: list[str], log_path: Path) -> int:
        calls.append((argv, log_path))
        # Simulate /dev-next flipping the spec to deployed.
        spec_number = argv[-1] if False else None  # argv doesn't carry it
        # The argv from build_headless_command is ['claude', '-p', '/dev-next'].
        # The spawn fake has to infer which spec by reading the queue itself.
        from scripts.spec_lifecycle.pick_next_number import current_queue

        queue = current_queue(repo["specs"])
        if queue:
            head_fm = queue[0][1]
            head_number = str(head_fm.get("spec"))
            head_path = next(repo["specs"].glob(f"{head_number}-*.md"))
            text = head_path.read_text()
            text = text.replace(
                f"status: queued",
                f"status: deployed",
            )
            head_path.write_text(text)
        return 0

    result = drain_queue(
        specs_dir=repo["specs"],
        handoffs_dir=repo["handoffs"],
        runs_dir=repo["runs"],
        project_dir=repo["root"],
        spawn_command=fake_spawn,
        now=_frozen_now,
        quiet=True,
    )

    assert result.iterations == 2
    assert result.completed == ["0500", "0501"]
    assert result.failed is None
    assert result.failure_log_tail is None
    assert len(result.log_paths) == 2
    # Each spawn call carries the canonical argv shape from
    # build_headless_command. The argv is intentionally identical between
    # iterations — the spec to run is encoded in the queue file, not in argv.
    assert calls[0][0] == ["claude", "-p", "/dev-next"]
    assert calls[1][0] == ["claude", "-p", "/dev-next"]


# ── Test 3: halt-on-failure ──────────────────────────────────────────────


def test_halt_on_failure_first_spec_ships_second_halts(
    repo: dict[str, Path],
) -> None:
    """Spec A returns 0 (and flips to deployed). Spec B returns 1. The
    supervisor halts: completed = [A], failed = B, failure_log_tail
    populated."""
    _write_spec(repo["specs"], "0510", queue_position=1, slug="ok")
    _write_spec(repo["specs"], "0511", queue_position=2, slug="bad")

    call_idx = [0]

    def fake_spawn(argv: list[str], log_path: Path) -> int:
        idx = call_idx[0]
        call_idx[0] += 1

        # Write something to the log so the tail-read has content.
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"fake stdout line 1 for call {idx}\n"
            f"fake stdout line 2 for call {idx}\n"
            f"ERROR: simulated failure on call {idx}\n"
        )

        from scripts.spec_lifecycle.pick_next_number import current_queue

        queue = current_queue(repo["specs"])
        if not queue:
            return 0
        head_fm = queue[0][1]
        head_number = str(head_fm.get("spec"))
        head_path = next(repo["specs"].glob(f"{head_number}-*.md"))

        if idx == 0:
            # Spec A: flip to deployed and return 0.
            text = head_path.read_text().replace(
                "status: queued", "status: deployed"
            )
            head_path.write_text(text)
            return 0
        # Spec B: leave it in_progress and return 1 (mimic /dev-next halt).
        text = head_path.read_text().replace(
            "status: queued", "status: failed"
        )
        head_path.write_text(text)
        return 1

    result = drain_queue(
        specs_dir=repo["specs"],
        handoffs_dir=repo["handoffs"],
        runs_dir=repo["runs"],
        project_dir=repo["root"],
        spawn_command=fake_spawn,
        now=_frozen_now,
        quiet=True,
    )

    assert result.iterations == 2
    assert result.completed == ["0510"]
    assert result.failed == "0511"
    assert result.failure_log_tail is not None
    # The tail must include the line we wrote to the failure log.
    assert "ERROR: simulated failure on call 1" in result.failure_log_tail


# ── Test 4: resume-mode re-pick ──────────────────────────────────────────


def test_resume_mode_repicks_same_spec_after_checkpoint(
    repo: dict[str, Path],
) -> None:
    """First spawn writes a checkpoint handoff + leaves the spec
    ``in_progress``. The next iteration re-picks the same spec via the
    resume probe (queue is empty in the meantime), completes it, and the
    drain finishes. ``iterations == 2``, ``completed == [spec]``."""
    _write_spec(repo["specs"], "0520", queue_position=1, slug="lspec")

    call_idx = [0]

    def fake_spawn(argv: list[str], log_path: Path) -> int:
        idx = call_idx[0]
        call_idx[0] += 1
        head_path = next(repo["specs"].glob("0520-*.md"))

        if idx == 0:
            # Checkpoint path: flip to in_progress (mimicking /dev-next
            # mid-cycle state) and write a checkpoint handoff.
            text = head_path.read_text().replace(
                "status: queued", "status: in_progress"
            )
            head_path.write_text(text)
            _write_checkpoint_handoff(
                repo["handoffs"], "0520", next_subsection="2.2"
            )
            return 0
        # Resume sub-iteration: flip to deployed and return 0.
        text = head_path.read_text().replace(
            "status: in_progress", "status: deployed"
        )
        head_path.write_text(text)
        return 0

    result = drain_queue(
        specs_dir=repo["specs"],
        handoffs_dir=repo["handoffs"],
        runs_dir=repo["runs"],
        project_dir=repo["root"],
        spawn_command=fake_spawn,
        now=_frozen_now,
        quiet=True,
    )

    assert result.iterations == 2
    # The spec only counts as completed when it ships (i.e. is no longer
    # in_progress). The checkpoint iteration must NOT pre-count it.
    assert result.completed == ["0520"]
    assert result.failed is None
    assert call_idx[0] == 2


# ── Smaller mechanical assertions ─────────────────────────────────────────


def test_log_paths_are_per_iteration_unique(repo: dict[str, Path]) -> None:
    """Each iteration must get a unique log file path under runs_dir,
    keyed by the spec number it ran. Used as the §3 session-isolation
    invariant from spec 0186."""
    _write_spec(repo["specs"], "0530", queue_position=1)
    _write_spec(repo["specs"], "0531", queue_position=2)

    tick = [0]

    def monotonic_now() -> str:
        tick[0] += 1
        return f"2026-05-23T00-00-{tick[0]:02d}Z"

    def fake_spawn(argv: list[str], log_path: Path) -> int:
        from scripts.spec_lifecycle.pick_next_number import current_queue

        head = current_queue(repo["specs"])[0][1]
        head_path = next(
            repo["specs"].glob(f"{head.get('spec')}-*.md")
        )
        head_path.write_text(
            head_path.read_text().replace(
                "status: queued", "status: deployed"
            )
        )
        return 0

    result = drain_queue(
        specs_dir=repo["specs"],
        handoffs_dir=repo["handoffs"],
        runs_dir=repo["runs"],
        project_dir=repo["root"],
        spawn_command=fake_spawn,
        now=monotonic_now,
        quiet=True,
    )

    assert len(result.log_paths) == 2
    assert result.log_paths[0] != result.log_paths[1]
    assert "spec-0530" in result.log_paths[0].name
    assert "spec-0531" in result.log_paths[1].name


def test_tail_returns_last_n_lines() -> None:
    text = "\n".join(f"line {i}" for i in range(100))
    assert _tail(text, n=3) == "line 97\nline 98\nline 99"


def test_read_log_tail_handles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.log"
    tail = _read_log_tail(missing)
    assert "not found" in tail
    assert str(missing) in tail


def test_default_now_format_is_filename_safe() -> None:
    ts = _default_now()
    # 2026-05-23T13-45-22Z shape: digits, dashes, T, Z.
    # No colons (which would break Windows filenames) and no spaces.
    assert ":" not in ts
    assert " " not in ts
    assert ts.endswith("Z")
    assert "T" in ts


def test_drain_result_is_frozen_dataclass() -> None:
    """The result is intentionally immutable so callers can't tamper with
    the audit trail after the supervisor returns."""
    r = DrainResult(
        completed=["0001"], failed=None, failure_log_tail=None,
        iterations=1, log_paths=[Path("/tmp/x.log")],
    )
    with pytest.raises((AttributeError, Exception)):
        r.iterations = 99  # type: ignore[misc]


def test_default_failure_tail_lines_constant_is_reasonable() -> None:
    """Smoke guard on the failure-tail length constant — 50 lines is the
    spec body's stated value. If a future spec wants 100, it should bump
    this constant deliberately, not by accident."""
    assert DEFAULT_FAILURE_TAIL_LINES == 50
