"""Step 4 · Implement — create the spec branch, run scope checks.

This step manages the branch lifecycle and the scope-guard around
"Files touched". The actual code edits are performed by the calling
session via Edit / Write tools (same as Step 3 Rewrite — the queue
orchestrates, the model implements).

Step 4 entrypoints:

- ``begin(spec)``  — checkout main, pull, branch ``spec/<NNNN>-<slug>``.
- ``check_scope(spec, changed_paths)`` — assert every changed path is
  in § 2 Files touched. Returns the list of out-of-scope paths.
- ``complete(spec, diff_stats)`` — record diff stats, end the step.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

from dual_research.queue_v2 import state


class ScopeViolation(RuntimeError):
    """A changed path is not listed in § 2 Files touched."""


def begin(spec_number: str, repo_root: Path | None = None) -> str:
    """Create the spec branch off main. Returns branch name."""
    repo = repo_root or _repo_root()
    state.begin_step("4_implement", repo_root=repo)
    parsed = _load_parsed(spec_number, repo)
    branch = f"spec/{parsed['spec']}-{parsed['slug']}"
    try:
        _git(["fetch", "origin", "main"], repo)
        _git(["checkout", "main"], repo)
        _git(["pull", "--ff-only"], repo)
        _git(["checkout", "-b", branch], repo)
    except subprocess.CalledProcessError as e:
        state.end_step(
            "4_implement",
            "failed",
            {"error": str(e), "branch": branch},
            repo_root=repo,
        )
        raise
    return branch


def check_scope(spec_number: str, changed_paths: Iterable[str], repo_root: Path | None = None) -> list[str]:
    repo = repo_root or _repo_root()
    parsed = _load_parsed(spec_number, repo)
    allowed = set(parsed.get("files_touched", []))
    # The queue's own permitted-anywhere files: version + changelog + cache-bust.
    allowed |= {
        "pyproject.toml",
        "uv.lock",
        "src/dual_research/__init__.py",
        "CHANGELOG.md",
    }
    bad = [c for c in changed_paths if c not in allowed]
    return bad


def complete(
    spec_number: str,
    diff_summary: str,
    repo_root: Path | None = None,
) -> None:
    """Mark Step 4 complete with a diff summary like '+342 -89 (4 files)'."""
    repo = repo_root or _repo_root()
    state.end_step(
        "4_implement",
        "done",
        {"diff": diff_summary},
        repo_root=repo,
    )


def collect_diff_stats(repo_root: Path | None = None) -> str:
    """Compute a one-line summary from `git diff --shortstat HEAD~..HEAD`."""
    repo = repo_root or _repo_root()
    out = _git(
        ["diff", "--shortstat", "main..HEAD"],
        repo,
        capture=True,
    )
    line = (out or "").strip()
    return line or "(no diff)"


def changed_paths(repo_root: Path | None = None) -> list[str]:
    repo = repo_root or _repo_root()
    out = _git(
        ["diff", "--name-only", "main..HEAD"],
        repo,
        capture=True,
    )
    return [p for p in (out or "").splitlines() if p.strip()]


# -- helpers ---------------------------------------------------------------


def _git(args: list[str], cwd: Path, *, capture: bool = False) -> str | None:
    cmd = ["git", *args]
    if capture:
        proc = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return proc.stdout
    subprocess.run(cmd, cwd=cwd, check=True)
    return None


def _load_parsed(spec_number: str, repo: Path) -> dict:
    p = state.run_dir(spec_number, repo) / "spec-parsed.json"
    return json.loads(p.read_text())


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = [
    "ScopeViolation",
    "begin",
    "changed_paths",
    "check_scope",
    "collect_diff_stats",
    "complete",
]
