"""In-spec checkpoint handoff helpers (spec 0186).

Spec 0186 introduces two related capabilities:

1. **Supervisor model for `/dev-queue-run`.** The queue runner spawns a fresh
   ``claude -p "/dev-next"`` subprocess per queued spec instead of running
   ``/dev-next``'s body inline. Each iteration gets its own clean session so
   later specs in the loop do not run under a context-burned window.

2. **L-spec in-spec checkpoint handoffs.** For specs with ``complexity: L``,
   ``/dev-next`` may write a checkpoint handoff after each completed
   top-level ``## 2.N`` subsection and halt cleanly. The next ``/dev-next``
   invocation reads the checkpoint, enters resume mode, skips re-branching,
   and picks up at the next subsection.

This module gives the supervisor + dev-next skill bodies a small typed
interface for the two new artefacts:

- :func:`classify_handoff_kind` — distinguishes the new ``in-spec-checkpoint``
  handoff from today's implicit ``post-deploy`` shape.
- :class:`CheckpointHandoff` + :func:`read_checkpoint` — typed parse of a
  checkpoint handoff's frontmatter, ``None`` when the file isn't one.
- :func:`find_active_checkpoint` — locate the checkpoint handoff that should
  resume a still-``in_progress`` spec, ``None`` when no resume is in flight.
- :func:`build_headless_command` — the supervisor's ``claude -p`` argv,
  isolated in one place so the contract can be patched if the CLI shifts
  (spec 0186 §7, "Headless ``claude -p`` runtime drift").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.spec_lifecycle.frontmatter import parse as parse_frontmatter

CHECKPOINT_KIND = "in-spec-checkpoint"
DEFAULT_KIND = "post-deploy"


def classify_handoff_kind(frontmatter: dict[str, Any]) -> str:
    """Return the handoff kind.

    Pre-spec-0186 handoffs have no ``kind`` field. Treat them as
    ``post-deploy`` — that is the only shape the codebase wrote before
    in-spec checkpoints existed. Anything else passes through as-is so
    future kinds added by downstream specs do not need to touch this
    function.
    """
    kind = frontmatter.get("kind")
    if not kind:
        return DEFAULT_KIND
    return str(kind)


@dataclass(frozen=True)
class CheckpointHandoff:
    """Typed view of an ``in-spec-checkpoint`` handoff's frontmatter.

    Field names mirror spec 0186 §2.2. The ``path`` field is informational
    so the resume path in ``/dev-next`` step 9 can quote which file it
    consulted.
    """

    spec: str
    branch: str
    branch_sha: str
    completed_subsections: list[str]
    next_subsection: str
    tests_status: str
    version_bumped: bool
    changelog_written: bool
    path: Path


def read_checkpoint(path: str | Path) -> CheckpointHandoff | None:
    """Parse a handoff file as a checkpoint, or return ``None`` if it isn't one.

    A file is a checkpoint when ``kind: in-spec-checkpoint`` appears in its
    frontmatter. Files with no ``kind:`` field (legacy post-deploy handoffs)
    return ``None`` — they are never treated as checkpoints.
    """
    parsed = parse_frontmatter(path)
    fm = parsed.frontmatter
    if classify_handoff_kind(fm) != CHECKPOINT_KIND:
        return None
    return CheckpointHandoff(
        spec=str(fm.get("spec", "")),
        branch=str(fm.get("branch", "")),
        branch_sha=str(fm.get("branch_sha", "")),
        completed_subsections=list(fm.get("completed_subsections") or []),
        next_subsection=str(fm.get("next_subsection", "")),
        tests_status=str(fm.get("tests_status", "not-yet-run")),
        version_bumped=bool(fm.get("version_bumped", False)),
        changelog_written=bool(fm.get("changelog_written", False)),
        path=Path(path),
    )


def find_active_checkpoint(
    handoffs_dir: str | Path,
    spec_number: str,
    spec_status: str,
) -> CheckpointHandoff | None:
    """Return the checkpoint that should resume ``spec_number``, if any.

    Resume mode activates only when:

    - The most recent handoff for this spec is a checkpoint.
    - The spec's on-disk ``status`` is ``in_progress``.

    Anything else returns ``None`` and the caller falls through to the
    today-shape pre-flight / pick-from-queue path. Spec 0186 §7 calls out
    that misreading a checkpoint when one shouldn't fire is the key risk
    — these two predicates are the disambiguators.
    """
    if spec_status != "in_progress":
        return None
    directory = Path(handoffs_dir)
    if not directory.exists():
        return None
    candidates = sorted(directory.glob(f"*-spec-{spec_number}-*.md"))
    if not candidates:
        return None
    latest = candidates[-1]
    return read_checkpoint(latest)


def build_headless_command(
    spec_number: str,
    log_path: str | Path,
    project_dir: str | Path,
) -> list[str]:
    """Build the supervisor's ``claude -p`` argv for one queue iteration.

    Spec 0186 §2.1 pins the contract: one queued spec → one headless
    ``claude -p "/dev-next"`` invocation, stdout+stderr captured to
    ``log_path``. Keeping this in one helper is the §7 mitigation
    against headless CLI drift — when the ``claude`` arg shape
    changes, only this function moves.

    The installed ``claude`` CLI (v2.1.79) does not accept a ``--cwd``
    flag, so the caller is responsible for setting the subprocess
    working directory via ``subprocess.Popen(..., cwd=...)`` or
    ``cd <dir> && claude -p ...`` in a shell wrapper. ``project_dir``
    stays in the signature for callers to thread through to whichever
    cwd-pinning mechanism they use.

    The returned argv excludes shell-level redirection; the caller is
    responsible for routing output to ``log_path`` (e.g. via ``stdout=``
    on a ``subprocess.Popen`` call, or ``> "$LOG" 2>&1`` in a shell
    wrapper).
    """
    return [
        "claude",
        "-p",
        "/dev-next",
    ]


# Spec 0192 §2 — first calibrated threshold for the L-spec checkpoint
# trigger. Re-evaluate after the first real L-spec drain produces evidence
# of where the agent actually starts degrading. Tune up if drains routinely
# fit in one session; tune down if the agent reports compaction warnings
# before this fires.
DEFAULT_SESSION_AGE_THRESHOLD = timedelta(minutes=30)


def should_checkpoint_now(
    session_started_at: datetime,
    *,
    now: datetime | None = None,
    threshold: timedelta = DEFAULT_SESSION_AGE_THRESHOLD,
) -> bool:
    """Return ``True`` when the L-spec session has been running long enough
    that the per-``## 2.N`` checkpoint cadence should halt cleanly.

    The signal is wall-clock session age. No token-counter dependency,
    no Claude-internal probe — spec 0186 §5 explicitly banned both. Spec
    0192 picks wall-clock age as the deterministic starting heuristic.

    ``session_started_at`` is the timestamp the session began. The skill
    body reads it from the spec frontmatter's ``started_at`` field (set
    at ``/dev-next`` step 12 when the spec flips to ``in_progress``).
    Under resume mode the caller substitutes the timestamp of the most
    recent ``resume_started`` event in the spec's sidecar log, so the
    helper measures the *current* session's age rather than the
    cumulative cycle.

    The ``>=`` comparison means the predicate is True at the exact
    threshold boundary, not strictly after. That matters for tests that
    construct a session aged exactly the threshold value.

    Spec 0186 §7 calls out that this heuristic may be wrong in either
    direction. Tuning happens in a follow-up if real drains show the
    threshold mis-firing — the predicate signature is stable; only the
    default changes.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return (now - session_started_at) >= threshold
