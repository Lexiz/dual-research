"""Source-pattern test: /dev-next defers the merged write past step 19 (spec 0247.1).

Per spec 0247, step 18 ("Merge-time state update") no longer pushes the
`merged` lifecycle state to `origin/main` before the squash-merge — both the
`set status=merged …` and the `append-event … merged` writes became
**local-only** buffered writes, flushed by step 23's atomic `push-files-to-main`.
That removed the pre-merge `--push-to-main` commits that raced the merge-commit
deploy under `deploy.yml`'s `deploy-main` concurrency group.

Spec 0247.1 fixes a correctness gap in that change: step 19's
`git checkout --detach -f origin/main` force-discards uncommitted working-tree
changes to the tracked `dashboard/queue-state.json`, so a `merged` write placed
in step 18 (before the detach) is wiped before step 23 ever runs. The durable
fix **relocates the merged write to after the step-19 re-detach**, joining the
post-merge buffer cohort (`deploy_started`, `deploy_health_check_ok`,
`handoff_written`) that survives the force-detach. Step 18 now only *captures*
`merged_at` at merge time (the `MERGED_AT=` shell variable, co-located with the
spec 0211.2 `MERGE_SHA` capture, both read before the detach).

The no-pre-merge-`--push-to-main` property spec 0247 introduced is unchanged —
this file's antipodal-absence assertions therefore extend across BOTH step 18
and step 19's relocated write block, so the new write site cannot reintroduce a
pre-merge push either. Same doctrine + `_step_block` helper as
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


def test_step_19_relocated_write_has_no_push_to_main() -> None:
    """Antipodal absence, extended (spec 0247.1): the relocated `merged` write
    lives in step 19's block and must also be local-only. The no-pre-merge-push
    property must hold across the whole pre-step-23 merge window, not just
    step 18 — the new write site cannot reintroduce a pre-merge push.

    Matched at the command level, not raw substring: step 19's *prose* mentions
    `--push-to-main` legitimately (the spec 0211.2 capture-before-push
    reasoning). The invariant is that no `queue_state` *invocation* carries the
    flag."""
    body = _skill_body()
    block = _step_block(body, 19)
    offending = [
        line
        for line in block.splitlines()
        if "spec_lifecycle.queue_state" in line and "--push-to-main" in line
    ]
    assert not offending, (
        "step 19 of dev-next SKILL.md has a `queue_state … --push-to-main` "
        "command — the relocated merged write (spec 0247.1) must stay local-only "
        "and ride step 23's atomic push-files-to-main; a pre-merge push here "
        f"re-introduces the deploy-race spec 0247 removed. Offending: {offending}"
    )


def test_step_19_writes_merged_state() -> None:
    """Positive (spec 0247.1): the `status=merged` + `merged_at` *write* now
    lands in step 19's block — the surviving, post-detach site that step 23
    flushes."""
    body = _skill_body()
    block = _step_block(body, 19)
    assert "status=merged" in block, (
        "step 19 of dev-next SKILL.md must set `status=merged` at the relocated "
        "(post-detach) write site — spec 0247.1 moves the buffered merged write "
        "past step 19's force re-detach so it survives to step 23"
    )
    assert "merged_at" in block, (
        "step 19 of dev-next SKILL.md must write `merged_at` at the relocated "
        "(post-detach) write site (spec 0247.1)"
    )


def test_step_18_captures_merged_at_but_not_the_write() -> None:
    """Positive + antipodal companion (spec 0247.1): step 18 still *captures*
    `merged_at` at merge time (the `MERGED_AT=` shell variable, before the
    detach), but the `status=merged` *write* has left step 18 — it now lives in
    step 19's post-detach block."""
    body = _skill_body()
    block = _step_block(body, 18)
    assert "MERGED_AT=" in block, (
        "step 18 of dev-next SKILL.md must capture `merged_at` at merge time as "
        "the `MERGED_AT=` shell variable (capture-before-detach, spec 0247.1) — "
        "the value must be timestamped before step 19's force re-detach"
    )
    assert "status=merged" not in block, (
        "step 18 of dev-next SKILL.md must NOT carry the `status=merged` write — "
        "spec 0247.1 relocated that write to step 19's post-detach block so the "
        "force re-detach does not discard it"
    )


def test_spec_0247_1_breadcrumb_present_in_step_19() -> None:
    """Breadcrumb (spec 0247.1): the string `spec 0247.1` must appear in
    step 19's block — locks the design citation to the relocated write site so
    a future re-shuffle leaves a trail back."""
    body = _skill_body()
    block = _step_block(body, 19)
    assert "spec 0247.1" in block, (
        "step 19 of dev-next SKILL.md must cite `spec 0247.1` in a comment or "
        "prose at the relocated merged-write site (design-breadcrumb invariant)"
    )
