"""Source-pattern test: /dev-next SKILL.md never invokes `fly deploy` or the
post-deploy sweep locally (spec 0211).

Per spec 0211, deploys are owned by `.github/workflows/deploy.yml` on push to
main, and the post-deploy sweep moved into CI alongside `flyctl deploy
--remote-only`. The skill body must:

  1. Contain no executable bash line invoking `fly deploy` or
     `scripts/sweep_stale_blues.sh` — prose mentions inside markdown text are
     fine (they explain what was removed).
  2. Contain none of the historic "case-1–5" matrix prose that existed only to
     recover from the local-vs-CI deploy race this spec eliminates.
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


def _bash_code_lines(body: str) -> list[tuple[int, str]]:
    """Return (line_number, line) tuples for every line inside a ```bash …
    ``` fenced code block. Line numbers are 1-indexed."""
    out: list[tuple[int, str]] = []
    in_bash = False
    for idx, raw in enumerate(body.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            lang = stripped.removeprefix("```").strip().lower()
            if not in_bash and lang == "bash":
                in_bash = True
            elif in_bash:
                in_bash = False
            continue
        if in_bash:
            out.append((idx, raw))
    return out


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def test_skill_has_no_local_fly_deploy_invocation() -> None:
    body = _skill_body()
    # `fly deploy` as a command — token-bounded so `fly deployed` etc. don't
    # match. Commented-out lines are tolerated (none should exist, but we don't
    # want a future review-only comment to trip the test).
    pattern = re.compile(r"\bfly\s+deploy\b")
    offenders = [
        f"line {lineno}: {line.strip()}"
        for lineno, line in _bash_code_lines(body)
        if not _is_comment(line) and pattern.search(line)
    ]
    assert offenders == [], (
        "dev-next SKILL.md contains a bash line invoking `fly deploy` — "
        f"spec 0211 moved the deploy into GH Actions. Offenders: {offenders}"
    )


def test_skill_has_no_local_sweep_invocation() -> None:
    body = _skill_body()
    pattern = re.compile(r"scripts/sweep_stale_blues\.sh\b")
    offenders = [
        f"line {lineno}: {line.strip()}"
        for lineno, line in _bash_code_lines(body)
        if not _is_comment(line) and pattern.search(line)
    ]
    assert offenders == [], (
        "dev-next SKILL.md contains a bash line invoking "
        "`scripts/sweep_stale_blues.sh` — spec 0211 moved the sweep into "
        f"`.github/workflows/deploy.yml`. Offenders: {offenders}"
    )


def test_skill_no_longer_carries_case_matrix_prose() -> None:
    """The historic five-case `fly status` matrix existed only to recover from
    the local-vs-CI deploy race. With the race gone (spec 0211), the matrix
    prose must be gone too."""
    body = _skill_body()
    forbidden_phrases = [
        "matrix below is its actionable distillation",
        "Route by case (first match wins)",
        "fly machine list -a dual-research-alex --json",
        "fly releases -a dual-research-alex --json",
    ]
    found = [phrase for phrase in forbidden_phrases if phrase in body]
    assert found == [], (
        "dev-next SKILL.md still carries case-1–5 matrix prose from before "
        f"spec 0211. Forbidden phrases found: {found}"
    )


def test_skill_watches_gh_actions_deploy() -> None:
    """Positive assertion: the skill explicitly delegates the deploy to GH
    Actions via `gh run watch`. Catches accidental regression to a local
    `fly deploy` call."""
    body = _skill_body()
    assert "gh run watch" in body, (
        "dev-next SKILL.md must invoke `gh run watch` to observe the GH "
        "Actions deploy.yml run (spec 0211)"
    )
    assert "deploy.yml" in body, (
        "dev-next SKILL.md must reference `.github/workflows/deploy.yml` "
        "as the deploy owner (spec 0211)"
    )
