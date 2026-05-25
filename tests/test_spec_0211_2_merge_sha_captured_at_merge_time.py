"""Source-pattern test: /dev-next captures MERGE_SHA at merge time (spec 0211.2).

Per spec 0211.2, step 19 captures the merge commit SHA from GitHub's
authoritative PR API (`gh pr view --json mergeCommit`) immediately after
`gh pr merge` returns, before any subsequent `--push-to-main` call (or step
19's re-detach) can advance `origin/main` past the merge commit. Step 20 then
consumes that captured value instead of re-deriving `MERGE_SHA` from
`origin/main` (which is the race spec 0211.2 closes).

The three assertions below lock the resulting step structure into the skill
body. Same doctrine + helpers as `test_spec_0211_no_local_fly_deploy.py`.
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


def _step_block(body: str, step_num: int) -> str:
    """Return the body of a top-level step `^N. ` block, stopping at the
    next top-level `^[0-9]+. ` heading. Sub-blocks indented by 4 spaces
    stay attached to their parent step."""
    lines = body.splitlines()
    start: int | None = None
    end: int | None = None
    heading = re.compile(r"^(\d+)\.\s")
    for idx, line in enumerate(lines):
        m = heading.match(line)
        if m is None:
            continue
        if int(m.group(1)) == step_num and start is None:
            start = idx
            continue
        if start is not None and int(m.group(1)) != step_num:
            end = idx
            break
    if start is None:
        raise AssertionError(f"step {step_num} heading not found in SKILL.md")
    if end is None:
        end = len(lines)
    return "\n".join(lines[start:end])


def test_step_20_no_longer_reads_merge_sha_from_origin_main() -> None:
    """Step 20's body must not re-derive MERGE_SHA from `origin/main` — that
    is the race spec 0211.2 closes."""
    body = _skill_body()
    block = _step_block(body, 20)
    pattern = re.compile(r"git\s+rev-parse\s+origin/main")
    assert not pattern.search(block), (
        "step 20 of dev-next SKILL.md still derives MERGE_SHA from "
        "`git rev-parse origin/main` — spec 0211.2 moved the capture into "
        "step 19. Found in step-20 block."
    )


def test_step_19_captures_merge_sha_via_gh_pr_view() -> None:
    """Step 19 must contain the `gh pr view ... --json mergeCommit` capture
    that spec 0211.2 introduces."""
    body = _skill_body()
    block = _step_block(body, 19)
    # Tolerate either inline JSON-jq form or split across lines via continuations.
    pattern = re.compile(r"gh\s+pr\s+view[^\n]*mergeCommit", re.DOTALL)
    assert pattern.search(block), (
        "step 19 of dev-next SKILL.md must invoke `gh pr view ... "
        "mergeCommit` to capture MERGE_SHA at merge time (spec 0211.2)"
    )


def test_spec_0211_2_breadcrumb_present_near_capture() -> None:
    """The string `spec 0211.2` must appear in step 19's block, near the
    capture site — locks the design citation so a future re-shuffle leaves
    a breadcrumb back to the spec."""
    body = _skill_body()
    block = _step_block(body, 19)
    assert "spec 0211.2" in block, (
        "step 19 of dev-next SKILL.md must cite `spec 0211.2` in a comment "
        "or prose near the MERGE_SHA capture (design-breadcrumb invariant)"
    )
