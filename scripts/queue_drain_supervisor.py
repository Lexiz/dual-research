"""Queue-drain supervisor (spec 0191).

Drains the dual-research dev-spec queue end-to-end by spawning one headless
``claude -p "/dev-next"`` subprocess per iteration. Until spec 0191 the loop
lived as prose in ``~/.claude/skills/dev-queue-run/SKILL.md`` — agent-followed
instructions, not unit-testable code. This module owns the loop in Python so
the per-iteration mechanics are regression-locked.

Public API
----------

- ``drain_queue(...) -> DrainResult`` — the loop. Tests inject a fake
  ``spawn_command`` to avoid spawning ``claude`` for real.
- ``DrainResult`` — the structured outcome of one drain.

The skill body remains the source of truth for human invariants (single
greenlight at start, halt-on-failure semantics, between-iteration session
isolation). Mechanical detail — argv shape, log path format, queue re-read,
resume-mode dispatch, log-tail-on-failure — lives here.

CLI
---

The module also exposes a ``__main__`` entry so the skill body can call
``uv run python -m scripts.queue_drain_supervisor --project-dir ...``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from scripts.spec_lifecycle.checkpoint import (
    build_headless_command,
    find_active_checkpoint,
)
from scripts.spec_lifecycle.pick_next_number import current_queue


# Type alias for the spawn injection point. Tests pass fakes that record argv
# per call and return rigged exit codes; the default implementation pipes
# subprocess stdout+stderr into ``log_path``.
SpawnCommand = Callable[[list[str], Path], int]

# Default tail length for the failure summary. The skill body says "last 50
# lines"; codifying as a constant so a future spec can tune it without
# touching the loop.
DEFAULT_FAILURE_TAIL_LINES = 50


@dataclass(frozen=True)
class DrainResult:
    """Structured outcome of one drain.

    Attributes
    ----------
    completed:
        Spec numbers that shipped during this drain, in pick order. A resume
        sub-iteration that completes the same spec adds the number once, on
        the iteration that flipped it to ``deployed``.
    failed:
        Spec number that halted the supervisor, or ``None`` if the drain
        finished cleanly (queue empty or every spec shipped).
    failure_log_tail:
        Last ``DEFAULT_FAILURE_TAIL_LINES`` lines of the failed iteration's
        log file, or ``None`` when ``failed is None``. Surfaced as the
        supervisor's last-words summary; the full log lives at the
        ``runs/queue-drain/<timestamp>-spec-<NNNN>.log`` path the iteration
        wrote.
    iterations:
        Total ``spawn_command`` invocations. Counts resume re-spawns: an
        L-spec that checkpoints once and resumes counts as 2.
    log_paths:
        Per-iteration log file paths, in pick order. Useful for the CLI's
        final summary and for tests asserting log isolation.
    """

    completed: list[str]
    failed: str | None
    failure_log_tail: str | None
    iterations: int
    log_paths: list[Path] = field(default_factory=list)


def _default_spawn_command(argv: list[str], log_path: Path) -> int:
    """Run ``argv`` with stdout+stderr captured to ``log_path``.

    Used when no ``spawn_command`` is injected. Each iteration runs in its
    own subprocess (per spec 0186 §2 — session isolation), so we use
    ``subprocess.run`` rather than streaming. The caller already pinned cwd
    via the calling shell; ``build_headless_command`` does not pass ``--cwd``
    (the installed CLI does not accept it — see spec 0194).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(  # noqa: S603
            argv,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return proc.returncode


def _default_now() -> str:
    """ISO-like timestamp for log filenames. Format matches what the
    pre-0191 skill prose used: ``YYYY-MM-DDTHH-MM-SSZ`` (colons swapped for
    dashes so it lands cleanly in a filename).
    """
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _tail(text: str, n: int = DEFAULT_FAILURE_TAIL_LINES) -> str:
    """Return the last ``n`` lines of ``text``."""
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def _read_log_tail(log_path: Path, n: int = DEFAULT_FAILURE_TAIL_LINES) -> str:
    """Best-effort log-tail read.

    The log file may not exist if ``spawn_command`` failed before writing
    anything (e.g. a process spawn error before the file was opened). In
    that case return an explanatory string instead of crashing the
    supervisor.
    """
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"(log file not found at {log_path})"
    except OSError as exc:
        return f"(could not read log at {log_path}: {exc})"
    return _tail(text, n)


def _read_spec_status(specs_dir: Path, spec_number: str) -> str | None:
    """Return the on-disk ``status`` for ``spec_number``, or ``None`` if the
    spec file isn't present.

    Used between iterations to detect resume mode: if the supervisor just
    spawned ``/dev-next`` on spec NNNN and the spec is still
    ``in_progress`` afterwards, the iteration must have written a
    checkpoint handoff — so the next iteration should re-pick the same spec
    via ``find_active_checkpoint`` rather than advance to the next queue
    position.
    """
    from scripts.spec_lifecycle.frontmatter import parse

    for entry in specs_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if not entry.name.startswith(f"{spec_number}-"):
            continue
        return parse(entry).frontmatter.get("status")
    return None


def drain_queue(
    specs_dir: str | Path,
    handoffs_dir: str | Path,
    runs_dir: str | Path,
    project_dir: str | Path,
    *,
    spawn_command: SpawnCommand | None = None,
    now: Callable[[], str] | None = None,
    quiet: bool = False,
) -> DrainResult:
    """Drain the queue end-to-end.

    Parameters
    ----------
    specs_dir:
        ``specs/`` directory of the repo. The queue is read from this
        directory's frontmatter via ``current_queue``.
    handoffs_dir:
        ``handoffs/`` directory. Checked between iterations for L-spec
        resume-mode checkpoints via ``find_active_checkpoint``.
    runs_dir:
        Directory under which per-iteration log files are written
        (``<runs_dir>/<now()>-spec-<NNNN>.log``). Created on demand.
    project_dir:
        Repo root. Threaded through to ``build_headless_command`` for
        callers that need it (the current installed CLI ignores it; future
        CLI versions may not).
    spawn_command:
        Injection point for subprocess spawning. Defaults to
        ``_default_spawn_command`` (real ``subprocess.run`` with
        stdout+stderr captured to ``log_path``). Tests pass a fake that
        records argv per call and returns rigged exit codes.
    now:
        Injection point for the log-filename timestamp.
    quiet:
        Suppress per-iteration stdout prints. Tests usually pass
        ``quiet=True``.

    Returns
    -------
    DrainResult
        Structured outcome.
    """
    spawn = spawn_command or _default_spawn_command
    timestamp = now or _default_now

    specs_path = Path(specs_dir)
    handoffs_path = Path(handoffs_dir)
    runs_path = Path(runs_dir)

    completed: list[str] = []
    log_paths: list[Path] = []
    iterations = 0
    # Spec numbers we've already started fresh on this drain — used to detect
    # resume mode (same spec re-picked because it stayed ``in_progress``).
    previously_spawned: set[str] = set()

    while True:
        queue = current_queue(specs_path)
        if not queue:
            # Queue empty — but if the previous iteration left a spec at
            # ``in_progress`` with an active checkpoint, fall through to the
            # resume branch instead of returning.
            resume_target = _find_resume_target(handoffs_path, specs_path)
            if resume_target is None:
                break
            spec_number = resume_target
        else:
            head_pos, head_fm = queue[0]
            spec_number = str(head_fm.get("spec") or "").strip()
            if not spec_number:
                # Malformed frontmatter — surface as failure rather than
                # spinning forever.
                return DrainResult(
                    completed=completed,
                    failed=None,
                    failure_log_tail=(
                        f"(queue head at position {head_pos} has no `spec` "
                        f"field in frontmatter)"
                    ),
                    iterations=iterations,
                    log_paths=log_paths,
                )

        log_path = runs_path / f"{timestamp()}-spec-{spec_number}.log"
        argv = build_headless_command(spec_number, log_path, project_dir)

        if not quiet:
            kind = (
                "resume"
                if spec_number in previously_spawned
                else "fresh"
            )
            print(
                f"[supervisor] iter {iterations + 1}: spec {spec_number} "
                f"({kind}) → {log_path}",
                flush=True,
            )

        exit_code = spawn(argv, log_path)
        iterations += 1
        log_paths.append(log_path)
        previously_spawned.add(spec_number)

        if exit_code != 0:
            tail = _read_log_tail(log_path)
            if not quiet:
                print(
                    f"[supervisor] HALT: spec {spec_number} returned "
                    f"exit code {exit_code}",
                    flush=True,
                )
            return DrainResult(
                completed=completed,
                failed=spec_number,
                failure_log_tail=tail,
                iterations=iterations,
                log_paths=log_paths,
            )

        # Exit code 0. The iteration may have:
        #   (a) flipped the spec to ``deployed`` — advance.
        #   (b) written a checkpoint and left it ``in_progress`` — resume
        #       next loop (the queue re-read will skip it since it's no
        #       longer ``queued``; the resume-target probe picks it up).
        # We don't need to distinguish here — the next loop's queue re-read
        # + resume probe handles both. We just record the completion of
        # *this iteration*.
        post_status = _read_spec_status(specs_path, spec_number)
        if post_status == "in_progress":
            # Checkpoint case. Don't add to ``completed`` — the spec hasn't
            # shipped yet. The next iteration will re-pick it via the
            # resume probe.
            continue

        # Spec is no longer ``in_progress`` (typically ``deployed``; could
        # also be ``failed`` if /dev-next set that and returned 0 anyway,
        # which would be a contract violation — but we don't second-guess).
        completed.append(spec_number)

    return DrainResult(
        completed=completed,
        failed=None,
        failure_log_tail=None,
        iterations=iterations,
        log_paths=log_paths,
    )


def _find_resume_target(handoffs_path: Path, specs_path: Path) -> str | None:
    """Return the spec number that should resume, if any.

    Walks all specs whose status is ``in_progress`` and checks each for an
    active checkpoint handoff. Returns the first match (in practice there is
    at most one; the ``/dev-next`` pre-flight halts on multiples).
    """
    from scripts.spec_lifecycle.frontmatter import parse

    for entry in sorted(specs_path.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        fm = parse(entry).frontmatter
        if fm.get("kind") != "dev":
            continue
        if fm.get("status") != "in_progress":
            continue
        spec_number = str(fm.get("spec") or "").strip()
        if not spec_number:
            continue
        if find_active_checkpoint(handoffs_path, spec_number, "in_progress"):
            return spec_number
    return None


# ── CLI ──────────────────────────────────────────────────────────────────


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="queue_drain_supervisor",
        description=(
            "Drain the dual-research dev-spec queue end-to-end. Spawns one "
            "headless `claude -p /dev-next` per iteration; halts on the first "
            "failure."
        ),
    )
    p.add_argument(
        "--project-dir",
        required=True,
        help="Repo root (e.g. /Users/alexlisitzky/dual-research)",
    )
    p.add_argument(
        "--specs-dir",
        default="specs",
        help="Specs directory relative to --project-dir (default: specs)",
    )
    p.add_argument(
        "--handoffs-dir",
        default="handoffs",
        help="Handoffs directory relative to --project-dir (default: handoffs)",
    )
    p.add_argument(
        "--runs-dir",
        default="runs/queue-drain",
        help="Log directory relative to --project-dir (default: runs/queue-drain)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print what would be spawned (one line per planned iteration) "
            "without actually spawning any subprocesses."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    specs_dir = project_dir / args.specs_dir
    handoffs_dir = project_dir / args.handoffs_dir
    runs_dir = project_dir / args.runs_dir

    if args.dry_run:
        # In dry-run we still re-read the queue, build the argv shape, but
        # never spawn. Useful for verifying the supervisor sees the same
        # queue the agent would have spawned.
        queue = current_queue(specs_dir)
        if not queue:
            print("[supervisor] queue empty — nothing to drain.")
            return 0
        print(f"[supervisor] dry-run plan ({len(queue)} specs):")
        for i, (pos, fm) in enumerate(queue, start=1):
            spec_number = str(fm.get("spec") or "?")
            slug = str(fm.get("slug") or "?")
            argv_iter = build_headless_command(
                spec_number,
                runs_dir / f"<timestamp>-spec-{spec_number}.log",
                project_dir,
            )
            print(
                f"  {i}. spec {spec_number} (pos {pos}) — {slug}\n"
                f"     argv: {argv_iter}"
            )
        return 0

    result = drain_queue(
        specs_dir=specs_dir,
        handoffs_dir=handoffs_dir,
        runs_dir=runs_dir,
        project_dir=project_dir,
    )

    print()
    print("=" * 60)
    print(f"[supervisor] drain finished: {result.iterations} iteration(s)")
    if result.completed:
        print(
            f"[supervisor] shipped: {', '.join(result.completed)} "
            f"({len(result.completed)} spec(s))"
        )
    if result.failed:
        print(f"[supervisor] HALTED on spec {result.failed}")
        print(f"[supervisor] last log tail ({DEFAULT_FAILURE_TAIL_LINES} lines):")
        print(result.failure_log_tail or "(no tail captured)")
        return 1
    if not result.completed:
        print("[supervisor] queue was empty — nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
