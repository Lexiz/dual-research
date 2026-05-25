"""Source-pattern test: /dev-next step 20 pivots on deploy-main cancellation (spec 0211.3).

Per spec 0211.3, step 20 of the dev-next skill wraps `gh run watch` in a
`set +e` / `WATCH_RC=$?` / `set -e` capture so the cycle can branch on
`cancelled` (caused by the `deploy-main` concurrency group at
`.github/workflows/deploy.yml:27-29` collapsing the pending-run queue) and
pivot to the surviving deploy.yml run on the latest `origin/main` SHA,
instead of halting on `cancelled` exit status.

The three assertions below lock the resulting step structure into the skill
body. Same doctrine + helpers as `test_spec_0211_2_merge_sha_captured_at_merge_time.py`.
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


def test_step_20_captures_watch_exit_status() -> None:
    """Step 20 must capture `gh run watch`'s exit status into a shell variable
    (rather than branching directly on it via `if gh run watch ...; then`) so
    the cycle can inspect a `cancelled` conclusion without halting bash on
    `-e`. Spec 0211.3 picks `WATCH_RC` as the variable name."""
    body = _skill_body()
    block = _step_block(body, 20)
    assert "WATCH_RC" in block, (
        "step 20 of dev-next SKILL.md must capture `gh run watch --exit-status` "
        "into a `WATCH_RC` shell variable so the cancellation pivot can branch "
        "on the conclusion (spec 0211.3)"
    )


def test_step_20_pivots_on_cancellation_to_origin_main() -> None:
    """Step 20 must (a) detect a `cancelled` conclusion and (b) re-query
    `origin/main` via `git ls-remote` to find the surviving deploy.yml run.
    Both tokens must appear in the same step-20 block."""
    body = _skill_body()
    block = _step_block(body, 20)
    assert "git ls-remote origin main" in block, (
        "step 20 of dev-next SKILL.md must use `git ls-remote origin main` "
        "to read the remote's authoritative tip for the concurrency-cancellation "
        "pivot (spec 0211.3) — not `git rev-parse origin/main`, which is the "
        "race spec 0211.2 closed"
    )
    assert "cancelled" in block, (
        "step 20 of dev-next SKILL.md must branch on a `cancelled` conclusion "
        "from `gh run view --json conclusion` to trigger the pivot (spec 0211.3)"
    )


def test_spec_0211_3_breadcrumb_present_near_pivot() -> None:
    """The string `spec 0211.3` must appear in step 20's block, near the
    pivot site — locks the design citation so a future re-shuffle leaves a
    breadcrumb back to the spec."""
    body = _skill_body()
    block = _step_block(body, 20)
    assert "spec 0211.3" in block, (
        "step 20 of dev-next SKILL.md must cite `spec 0211.3` in a comment or "
        "prose near the concurrency-cancellation pivot block "
        "(design-breadcrumb invariant)"
    )
