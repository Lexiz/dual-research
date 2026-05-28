"""Source-pattern test: /dev-next step 18 buffers the merged state (spec 0247).

Per spec 0247, step 18 ("Merge-time state update") no longer pushes the
`merged` lifecycle state to `origin/main` before the squash-merge. Both the
`set status=merged …` and the `append-event … merged` writes are now
**local-only** buffered writes to the worktree's `dashboard/queue-state.json`;
step 23's atomic `push-files-to-main` flushes them alongside `status=deployed`.
This removes the pre-merge `--push-to-main` commits that raced the merge-commit
deploy under `deploy.yml`'s `deploy-main` concurrency group (the cancellation
spec 0211.3 detects and pivots around — 0247 removes the cause).

The three assertions below lock the resulting step structure into the skill
body. Same doctrine + `_step_block` helper as
`test_spec_0211_2_merge_sha_captured_at_merge_time.py`.
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


def test_step_18_has_no_push_to_main() -> None:
    """Antipodal absence: step 18's block must contain no `--push-to-main`
    token — the pre-merge pushes are the deploy-race cause spec 0247 removes."""
    body = _skill_body()
    block = _step_block(body, 18)
    assert "--push-to-main" not in block, (
        "step 18 of dev-next SKILL.md still carries a `--push-to-main` flag — "
        "spec 0247 buffers the merged state locally and flushes it in step 23. "
        "A pre-merge push re-introduces the deploy-race."
    )


def test_step_18_still_computes_merged_state() -> None:
    """Positive: step 18 still writes `status=merged` + `merged_at` — only the
    push is deferred, the state is still captured at merge time."""
    body = _skill_body()
    block = _step_block(body, 18)
    assert "status=merged" in block, (
        "step 18 of dev-next SKILL.md must still set `status=merged` (the "
        "merged state is buffered, not dropped)"
    )
    assert "merged_at" in block, (
        "step 18 of dev-next SKILL.md must still capture `merged_at` at merge "
        "time (only its push is deferred to step 23)"
    )


def test_spec_0247_breadcrumb_present_in_step_18() -> None:
    """Breadcrumb: the string `spec 0247` must appear in step 18's block —
    locks the design citation so a future re-shuffle leaves a trail back."""
    body = _skill_body()
    block = _step_block(body, 18)
    assert "spec 0247" in block, (
        "step 18 of dev-next SKILL.md must cite `spec 0247` in a comment or "
        "prose at the buffered-write site (design-breadcrumb invariant)"
    )
