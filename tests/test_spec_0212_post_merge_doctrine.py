"""Source-pattern test: /dev-next post-merge doctrine (spec 0212).

Spec 0212 closes two frictions in the post-merge window of `/dev-next`:

1. `gh pr merge --delete-branch` is split into a plain `gh pr merge --admin
   --squash` plus an explicit `git push origin --delete $BRANCH` + `git branch
   -D $BRANCH` block. The composite call used to run `git checkout main`
   internally, colliding with the author worktree at
   `/Users/alexlisitzky/dual-research-author/` that holds `main`.

2. Every post-merge happy-path `--push-to-main` event emission is buffered
   locally and flushed atomically in step 23. The `deploy-main` concurrency
   group at `.github/workflows/deploy.yml` can no longer cancel the
   merge-commit's deploy run, because no newer runs queue behind it in the
   window between merge and `gh run watch` returning.

The assertions below lock the resulting step structure into the skill body.
Failure-path emissions (`set status=failed`, `append-event failed`) keep
`--push-to-main` because the cycle halts after them — there is no step 23 to
flush the buffer.

Same `_step_block` helper as `test_spec_0211_2_merge_sha_captured_at_merge_time.py`.
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


def test_step_19_drops_delete_branch_flag() -> None:
    """Step 19 must NOT pass `--delete-branch` to `gh pr merge`. The composite
    call ran `git checkout main` internally, colliding with the author
    worktree's hold on `main`. Spec 0212 splits the call."""
    body = _skill_body()
    block = _step_block(body, 19)
    pattern = re.compile(r"gh\s+pr\s+merge[^\n]*--delete-branch")
    assert not pattern.search(block), (
        "step 19 of dev-next SKILL.md still invokes `gh pr merge "
        "--delete-branch` — spec 0212 split branch cleanup from the merge "
        "call to avoid the author-worktree `git checkout main` collision."
    )


def test_step_19_has_squash_merge_and_explicit_delete() -> None:
    """Step 19 must contain both `gh pr merge --admin --squash` (the new
    flagless merge) AND `git push origin --delete` (the explicit cleanup)."""
    body = _skill_body()
    block = _step_block(body, 19)
    merge_pattern = re.compile(r"gh\s+pr\s+merge\s+--admin\s+--squash")
    delete_pattern = re.compile(r"git\s+push\s+origin\s+--delete")
    assert merge_pattern.search(block), (
        "step 19 of dev-next SKILL.md must invoke `gh pr merge --admin "
        "--squash` (spec 0212 — without --delete-branch)"
    )
    assert delete_pattern.search(block), (
        "step 19 of dev-next SKILL.md must contain `git push origin "
        "--delete \"$BRANCH\"` as the explicit remote-branch cleanup (spec "
        "0212 — replaces the cleanup half of `gh pr merge --delete-branch`)"
    )


def test_spec_0212_breadcrumb_present_in_step_19() -> None:
    """The string `spec 0212` must appear in step 19's block — locks the
    design citation so a future re-shuffle leaves a breadcrumb back to the
    spec."""
    body = _skill_body()
    block = _step_block(body, 19)
    assert "spec 0212" in block, (
        "step 19 of dev-next SKILL.md must cite `spec 0212` near the "
        "explicit-cleanup block (design-breadcrumb invariant)"
    )


def test_step_20_deploy_started_is_local_only() -> None:
    """Step 20's `deploy_started` emission must NOT pass `--push-to-main`.
    Spec 0212's buffer-events doctrine forbids any happy-path `--push-to-main`
    between merge and step 23's atomic flush, because each post-merge push to
    `origin/main` queues a new deploy.yml run in the `deploy-main` concurrency
    group and risks cancelling the merge-commit's own run."""
    body = _skill_body()
    block = _step_block(body, 20)
    # Match the deploy_started append-event line; tolerate whitespace + line
    # continuations.
    pattern = re.compile(
        r"append-event[^\n]*--push-to-main[^\n]*deploy_started"
        r"|append-event[^\n]*deploy_started[^\n]*--push-to-main"
    )
    assert not pattern.search(block), (
        "step 20 of dev-next SKILL.md emits `deploy_started` with "
        "`--push-to-main` — spec 0212 requires this event to be local-only "
        "(flushed by step 23) so the merge-commit's deploy run is not "
        "cancelled by the deploy-main concurrency group."
    )


def test_step_20_happy_path_deployed_is_local_only() -> None:
    """Step 20's happy-path `deployed` emission must NOT pass `--push-to-main`.
    Same doctrine as `deploy_started` above."""
    body = _skill_body()
    block = _step_block(body, 20)
    pattern = re.compile(
        r"append-event[^\n]*--push-to-main[^\n]*deployed"
        r"|append-event[^\n]*deployed[^\n]*--push-to-main"
    )
    assert not pattern.search(block), (
        "step 20 of dev-next SKILL.md emits `deployed` with `--push-to-main` "
        "— spec 0212 requires this event to be local-only (flushed by "
        "step 23). Both the happy-path branch (`WATCH_RC == 0`) and the "
        "pivot-path tail must drop the flag."
    )


def test_step_19_re_detach_precedes_branch_delete() -> None:
    """Step 19's explicit-cleanup block must run `git checkout --detach -f
    origin/main` BEFORE `git branch -D "$BRANCH"`. `git branch -D` on a
    branch that is still checked out in the current worktree is refused by
    git ("cannot delete branch ... used by worktree at ..."); the spec 0212
    cycle live-discovered this with the detach AFTER the by-name delete and
    folded the re-detach into the cleanup block in the correct order.

    A future re-shuffle of step 19 that moves the detach back below the
    delete — or drops the detach line altogether — re-introduces the
    collision AND breaks the spec-0210 baseline-pose contract (the queue
    worktree must be detached at `origin/main` between cycles)."""
    body = _skill_body()
    block = _step_block(body, 19)
    lines = block.split("\n")
    # Anchor at start-of-line (allow leading whitespace) so that prose mentions
    # like `\`git branch -D "$BRANCH"\` fails when ...` inside the surrounding
    # explanatory text do not match — only executable shell lines do.
    detach_pattern = re.compile(r"^\s*git\s+checkout\s+--detach")
    delete_pattern = re.compile(r'^\s*git\s+branch\s+-D\s+"\$BRANCH"')
    detach_idx: int | None = next(
        (i for i, ln in enumerate(lines) if detach_pattern.search(ln)),
        None,
    )
    delete_idx: int | None = next(
        (i for i, ln in enumerate(lines) if delete_pattern.search(ln)),
        None,
    )
    assert detach_idx is not None, (
        "step 19 of dev-next SKILL.md must contain `git checkout --detach` "
        "in the explicit-cleanup block — spec 0212 folded the spec-0210 "
        "re-detach into step 19. Dropping it breaks the baseline-pose "
        "contract AND re-introduces the `git branch -D` worktree collision."
    )
    assert delete_idx is not None, (
        'step 19 of dev-next SKILL.md must contain `git branch -D "$BRANCH"` '
        "as the local-branch cleanup half of the spec-0212 explicit block."
    )
    assert detach_idx < delete_idx, (
        f"step 19 ordering violation: `git checkout --detach` (line "
        f"{detach_idx} of block) must precede `git branch -D \"$BRANCH\"` "
        f"(line {delete_idx} of block). With the delete first, git refuses "
        "the by-name delete because the queue worktree at "
        "`/Users/alexlisitzky/dual-research/` is still checked out on the "
        "spec branch (live-discovered during the spec 0212 cycle)."
    )


def test_step_20_failure_paths_keep_push_to_main() -> None:
    """Step 20's failure-path emissions MUST keep `--push-to-main` — the
    cycle exits after them, so there is no step 23 to flush the buffer.
    Failures need to surface on the dashboard immediately.

    Two failure paths: the `deploy_run_not_found` halt (run row never appears)
    and the real-failure halt (deploy.yml run concludes with `failure` /
    `timed_out` / `startup_failure`)."""
    body = _skill_body()
    block = _step_block(body, 20)
    # Collapse bash line continuations (` \\\n    ` → ` `) so `set --push-to-main`
    # and its `status=failed` argument land on the same logical line.
    collapsed = re.sub(r"\\\s*\n\s+", " ", block)
    # `set --push-to-main NNNN status=failed` — both flags on the same logical line.
    set_failed = re.compile(
        r"queue_state\s+set\s+--push-to-main[^\n]*status=failed",
    )
    event_failed = re.compile(r"append-event\s+--push-to-main[^\n]*failed")
    assert set_failed.search(collapsed), (
        "step 20 of dev-next SKILL.md must keep `--push-to-main` on the "
        "`set status=failed` calls in the failure paths — the cycle exits "
        "after them so the buffer would never flush. Failures must reach "
        "the dashboard immediately."
    )
    assert event_failed.search(collapsed), (
        "step 20 of dev-next SKILL.md must keep `--push-to-main` on the "
        "`append-event failed` calls in the failure paths."
    )
