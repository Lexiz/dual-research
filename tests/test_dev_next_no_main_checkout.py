"""Source-pattern test: /dev-next SKILL.md never tells the orchestrator to
hold the local ``main`` ref in the queue worktree (spec 0210).

Per spec 0210 §2 the queue worktree operates from a detached HEAD at
``origin/main``; all main-side writes go through the push-via-plumbing
helpers in ``scripts/spec_lifecycle/queue_state.py``. The skill body must
not regress to ``git checkout main`` (which would conflict with the author
worktree's documented "stays on main" pose) or ``git pull origin main``
outside the pre-flight step 1 fast-forward.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

SKILL_PATH = Path(os.path.expanduser("~/.claude/skills/dev-next/SKILL.md"))


def _skill_body() -> str:
    if not SKILL_PATH.exists():
        pytest.skip(f"dev-next skill not present at {SKILL_PATH}")
    return SKILL_PATH.read_text(encoding="utf-8")


def _strip_explanatory_lines(body: str) -> str:
    """Remove lines that mention forbidden patterns inside negation prose.

    The skill body explicitly says "no local ``git checkout main`` / ``git
    commit`` / ``git push origin main``" to document what the new mechanism
    avoids. Those mentions are inside backticks and adjacent to "no local"
    / "never" prose, so we drop any line that frames them as forbidden
    before searching for genuine occurrences.
    """
    keep: list[str] = []
    for line in body.splitlines():
        low = line.lower()
        if ("no local" in low or "never holds" in low or "no bare" in low) and "git checkout main" in low:
            continue
        keep.append(line)
    return "\n".join(keep)


def test_skill_does_not_check_out_main_branch() -> None:
    body = _strip_explanatory_lines(_skill_body())
    # Bare `git checkout main` (not the spec/<...> feature branch checkout).
    # The negative lookahead excludes `git checkout -b spec/`, `git checkout --detach`,
    # and any path argument after "main".
    pattern = re.compile(r"\bgit\s+checkout\s+main\b")
    hits = pattern.findall(body)
    assert hits == [], (
        f"dev-next SKILL.md contains bare 'git checkout main' — spec 0210 "
        f"forbids holding the main ref in the queue worktree. Hits: {hits}"
    )


def test_skill_only_pulls_main_in_preflight() -> None:
    """`git pull --ff-only origin main` is allowed in pre-flight step 1.
    No other line in the skill body may invoke `git pull` against main."""
    body = _strip_explanatory_lines(_skill_body())
    lines = body.splitlines()

    # Find the start of the post-preflight section ("## Reconcile" header).
    reconcile_start = next(
        (i for i, line in enumerate(lines) if line.startswith("## Reconcile")),
        None,
    )
    assert reconcile_start is not None, "expected '## Reconcile' section header"

    # Any `git pull` past pre-flight is forbidden, regardless of args.
    offenders = [
        f"line {i + 1}: {line.strip()}"
        for i, line in enumerate(lines[reconcile_start:], start=reconcile_start)
        if re.search(r"\bgit\s+pull\b", line)
    ]
    assert offenders == [], (
        "dev-next SKILL.md invokes `git pull` outside the pre-flight section — "
        f"spec 0210 forbids holding the main ref past step 1. Offenders: {offenders}"
    )


def test_skill_documents_detached_head_invariant() -> None:
    """Positive assertion: the skill explicitly documents that the queue
    worktree never holds main locally. Catches accidental regression of the
    invariant prose."""
    body = _skill_body()
    assert "detached" in body.lower(), (
        "dev-next SKILL.md must document the detached-HEAD invariant (spec 0210)"
    )
    assert "push-files-to-main" in body or "push_files_to_main" in body, (
        "dev-next SKILL.md must reference the push-files-to-main plumbing "
        "helper (spec 0210)"
    )
