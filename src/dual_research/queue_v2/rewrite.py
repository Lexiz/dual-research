"""Step 3 · Rewrite — apply alignment notes to the spec file itself.

If Step 2 produced no notes, Step 3 marks itself ``skipped`` and the
queue proceeds. Otherwise the model that's driving the queue (the
calling Claude session) makes targeted in-place edits to the spec
file authorised by the spec's § 9 "Spec rewrite mandate", logging
each edit verbatim to ``queue/runs/<NNNN>/rewrite-log.md``.

This module never edits the spec file directly. It owns:

- The decision to skip vs. flag-for-rewrite (based on note count).
- The append-only log of every edit the caller reports back.
- Step transition + persistence of the log path.

The actual textual edits to ``specs/NNNN-*.md`` are performed by the
calling session via the standard Edit tool — that is what "authorised
by § 9" means in practice. The queue records the diff after the fact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from dual_research.queue_v2 import state


def has_rewrite_work(spec_number: str, repo_root: Path | None = None) -> bool:
    """True iff Step 2 produced ≥1 alignment note."""
    repo = repo_root or _repo_root()
    notes_path = state.run_dir(spec_number, repo) / "reason-notes.md"
    if not notes_path.exists():
        return False
    body = notes_path.read_text()
    return "_No alignment notes" not in body


def log_edit(
    spec_number: str,
    edit_summary: str,
    before: str | None = None,
    after: str | None = None,
    repo_root: Path | None = None,
) -> None:
    """Append a single edit record to the spec's rewrite log."""
    repo = repo_root or _repo_root()
    log_path = state.run_dir(spec_number, repo) / "rewrite-log.md"
    is_new = not log_path.exists()
    with log_path.open("a") as f:
        if is_new:
            f.write(f"# Spec {spec_number} — rewrite log\n\n")
            f.write("Recorded by Step 3 Rewrite. Forwarded into Step 8 Handover.\n\n")
        f.write(f"## {edit_summary.strip()}\n\n")
        if before is not None or after is not None:
            f.write("```diff\n")
            for line in (before or "").splitlines():
                f.write(f"- {line}\n")
            for line in (after or "").splitlines():
                f.write(f"+ {line}\n")
            f.write("```\n\n")


def run_skip(spec_number: str, repo_root: Path | None = None) -> None:
    repo = repo_root or _repo_root()
    state.begin_step("3_rewrite", repo_root=repo)
    state.end_step(
        "3_rewrite",
        "skipped",
        {"reason": "no alignment notes"},
        repo_root=repo,
    )


def run_complete(
    spec_number: str,
    edits: Iterable[dict[str, str]],
    repo_root: Path | None = None,
) -> None:
    """Mark Step 3 complete after the calling session has applied edits.

    ``edits`` is an iterable of ``{"summary": ..., "before": ..., "after": ...}``
    dicts — each one is appended to rewrite-log.md.
    """
    repo = repo_root or _repo_root()
    state.begin_step("3_rewrite", repo_root=repo)
    n = 0
    for e in edits:
        log_edit(
            spec_number,
            e.get("summary", ""),
            e.get("before"),
            e.get("after"),
            repo_root=repo,
        )
        n += 1
    log_path = state.run_dir(spec_number, repo) / "rewrite-log.md"
    state.end_step(
        "3_rewrite",
        "done",
        {"edit_count": n, "log_file": str(log_path)},
        repo_root=repo,
    )


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = ["has_rewrite_work", "log_edit", "run_complete", "run_skip"]
