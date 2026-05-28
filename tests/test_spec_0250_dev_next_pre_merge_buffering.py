"""Source-pattern test: /dev-next buffers pre-merge telemetry into two flushes (spec 0250).

Per spec 0250, the pre-merge window of the `/dev-next` cycle mirrors the proven
post-merge buffering (specs 0212/0247): every happy-path lifecycle event is
emitted **local-only** (no `--push-to-main`) and the buffer is flushed in exactly
**two** batched `push-files-to-main` commits —

  * **Flush 1** at step 12 (cycle start / `in_progress`), carrying the buffered
    `cycle_started` / `preflight_ok` / `handoff_read` / `spec_read` /
    `planning_started` / `reconcile_complete` events plus the `status=in_progress`
    + `started_at` write and the `in_progress` event; and
  * **Flush 2** at step 17 (PR opened), carrying `branched`,
    `implementing_started`, `implement_complete`, `tests_started`, `tests_green`,
    `pr_opened`.

Net: the ~8 individual `spec(NNNN): queue-state update` commits the pre-merge
window used to push to `origin/main` collapse to two. **No contract change** —
same events, same lifecycle states, same vocabulary; only the push cadence moves.

Behavior-preservation invariants this test locks (spec 0250 §4):
  * Failure writes never buffer — every pre-merge halt (semantic drift at step 11,
    tests red at step 16) keeps `--push-to-main` on both its `status=failed` set
    and its `*_failed`/`failed` event, so a halt stays immediately visible on the
    dashboard.
  * The post-merge window (steps 18–23) is untouched — its events stay local-only
    and its single step-23 flush is intact.

Skill files live outside the repo, so this is a pure-stdlib source-pattern read of
`~/.claude/skills/dev-next/SKILL.md` with a skip-when-absent guard — the spec 0247
precedent. Same `_step_block` helper as `test_spec_0247_pre_merge_no_push.py`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

SKILL_PATH = Path(os.path.expanduser("~/.claude/skills/dev-next/SKILL.md"))

# A queue_state CLI invocation line that carries the immediate-push flag.
_PUSH_CMD = re.compile(r"spec_lifecycle\.queue_state\b.*--push-to-main")
# A Flush invocation line: the `queue_state push-files-to-main` CLI call. Matched
# at the invocation form (not bare `push-files-to-main`) so prose mentions of the
# "push-files-to-main plumbing" do not count as flushes.
_FLUSH_CMD = re.compile(r"spec_lifecycle\.queue_state push-files-to-main")


def _skill_body() -> str:
    if not SKILL_PATH.exists():
        pytest.skip(f"dev-next skill not present at {SKILL_PATH}")
    return SKILL_PATH.read_text(encoding="utf-8")


def _step_block(body: str, step_num: int) -> str:
    """Return the body of a top-level step `^N. ` block, stopping at the next
    top-level `^[0-9]+. ` heading. Sub-blocks indented by 4 spaces stay attached
    to their parent step."""
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


def _flush_count(block: str) -> int:
    """Number of `queue_state push-files-to-main` CLI invocations in a block.
    Counting the invocation line (not bare `push-files-to-main`) excludes prose
    mentions of the plumbing; the multi-line command's `--file
    dashboard/queue-state.json` is asserted separately where it matters."""
    return len(_FLUSH_CMD.findall(block))


# --------------------------------------------------------------------------- #
# Happy-path emissions are local-only (no --push-to-main).
# --------------------------------------------------------------------------- #

def test_step_12_happy_path_local_only() -> None:
    """Step 12's `status=in_progress` set and `in_progress` event must carry no
    `--push-to-main` — they are buffered and flushed by Flush 1."""
    block = _step_block(_skill_body(), 12)
    offending = [
        line for line in block.splitlines()
        if _PUSH_CMD.search(line)
    ]
    assert not offending, (
        "step 12 of dev-next SKILL.md still has a `queue_state … --push-to-main` "
        "command — spec 0250 makes the in_progress write local-only and flushes "
        f"it via Flush 1. Offending: {offending}"
    )


def test_step_14_happy_path_local_only() -> None:
    """Step 14's `branched` + `implementing_started` events are buffered to
    Flush 2 — no `--push-to-main`. Step 14 has no failure path."""
    block = _step_block(_skill_body(), 14)
    offending = [line for line in block.splitlines() if _PUSH_CMD.search(line)]
    assert not offending, (
        "step 14 of dev-next SKILL.md still has a `queue_state … --push-to-main` "
        f"command — spec 0250 buffers branch-phase events to Flush 2. Offending: {offending}"
    )


def test_step_15_implement_complete_local_only() -> None:
    """`implement_complete` is a happy-path event — buffered to Flush 2. (Step 15
    legitimately keeps `--push-to-main` on the L-spec `checkpoint_written` path,
    so we assert at the event level, not the whole block.)"""
    body = _skill_body()
    lines = [l for l in body.splitlines() if "implement_complete" in l and "queue_state" in l]
    assert lines, "implement_complete emission not found in SKILL.md"
    offending = [l for l in lines if "--push-to-main" in l]
    assert not offending, (
        "`implement_complete` in dev-next SKILL.md still carries `--push-to-main` "
        f"— spec 0250 buffers it to Flush 2. Offending: {offending}"
    )


def test_step_16_tests_green_path_local_only() -> None:
    """`tests_started` and `tests_green` (the green path) are buffered to Flush 2."""
    body = _skill_body()
    for event in ("tests_started", "tests_green"):
        lines = [l for l in body.splitlines() if event in l and "queue_state" in l]
        assert lines, f"{event} emission not found in SKILL.md"
        offending = [l for l in lines if "--push-to-main" in l]
        assert not offending, (
            f"`{event}` in dev-next SKILL.md still carries `--push-to-main` — "
            f"spec 0250 buffers the green path to Flush 2. Offending: {offending}"
        )


def test_step_17_pr_opened_local_only() -> None:
    """`pr_opened` is the final pre-merge happy event — buffered, then Flush 2
    fires immediately after."""
    body = _skill_body()
    lines = [l for l in body.splitlines() if "pr_opened" in l and "queue_state" in l]
    assert lines, "pr_opened emission not found in SKILL.md"
    offending = [l for l in lines if "--push-to-main" in l]
    assert not offending, (
        "`pr_opened` in dev-next SKILL.md still carries `--push-to-main` — "
        f"spec 0250 buffers it to Flush 2. Offending: {offending}"
    )


# --------------------------------------------------------------------------- #
# Exactly two batched flushes in the pre-merge window.
# --------------------------------------------------------------------------- #

def test_flush_1_present_at_step_12() -> None:
    block = _step_block(_skill_body(), 12)
    assert _flush_count(block) == 1, (
        "step 12 of dev-next SKILL.md must contain exactly one "
        "`queue_state push-files-to-main` invocation (Flush 1), "
        f"found {_flush_count(block)}"
    )
    assert "dashboard/queue-state.json" in block, (
        "step 12's Flush 1 must flush `dashboard/queue-state.json`"
    )


def test_flush_2_present_at_step_17() -> None:
    block = _step_block(_skill_body(), 17)
    assert _flush_count(block) == 1, (
        "step 17 of dev-next SKILL.md must contain exactly one "
        "`queue_state push-files-to-main` invocation (Flush 2), "
        f"found {_flush_count(block)}"
    )
    assert "dashboard/queue-state.json" in block, (
        "step 17's Flush 2 must flush `dashboard/queue-state.json`"
    )


def test_no_flush_in_intermediate_steps() -> None:
    """Steps 13–16 carry no flush — the two pre-merge flushes live only at
    steps 12 and 17, so the pre-merge window flushes exactly twice."""
    body = _skill_body()
    for step in (13, 14, 15, 16):
        block = _step_block(body, step)
        assert _flush_count(block) == 0, (
            f"step {step} of dev-next SKILL.md unexpectedly contains a "
            "`push-files-to-main … queue-state` flush — the pre-merge window "
            "must flush exactly twice (steps 12 and 17)"
        )


# --------------------------------------------------------------------------- #
# Failure writes never buffer — they stay immediately visible.
# --------------------------------------------------------------------------- #

def test_semantic_drift_failure_keeps_push() -> None:
    """Step 11's semantic-drift halt keeps `--push-to-main` on both its
    `status=failed` set and its `reconcile_failed` event (spec 0250 §4)."""
    block = _step_block(_skill_body(), 11)
    assert re.search(r"status=failed.*--push-to-main|--push-to-main.*status=failed", block), (
        "step 11 of dev-next SKILL.md must keep `--push-to-main` on the "
        "semantic-drift `status=failed` set — buffering must not swallow failure "
        "visibility (spec 0250 §4)"
    )
    assert "reconcile_failed" in block and "--push-to-main" in block, (
        "step 11 of dev-next SKILL.md must keep `--push-to-main` on the "
        "`reconcile_failed` event (spec 0250 §4)"
    )


def test_tests_red_failure_keeps_push() -> None:
    """Step 16's tests-red halt keeps `--push-to-main` on both its
    `status=failed failure_step=tests` set and its `tests_failed` event."""
    block = _step_block(_skill_body(), 16)
    failed_set = [
        l for l in block.splitlines()
        if "status=failed" in l and "failure_step=tests" in l
    ]
    assert failed_set, "step 16 must document the tests-red `status=failed failure_step=tests` write"
    assert all("--push-to-main" in l for l in failed_set), (
        "step 16's tests-red `status=failed` set must keep `--push-to-main` "
        "(spec 0250 §4) — a halt must be visible on the dashboard immediately"
    )
    failed_evt = [l for l in block.splitlines() if "tests_failed" in l and "queue_state" in l]
    assert failed_evt, "step 16 must document the `tests_failed` event"
    assert all("--push-to-main" in l for l in failed_evt), (
        "step 16's `tests_failed` event must keep `--push-to-main` (spec 0250 §4)"
    )


# --------------------------------------------------------------------------- #
# Post-merge window untouched (behavior preservation).
# --------------------------------------------------------------------------- #

def test_post_merge_handoff_written_still_local_only() -> None:
    """The post-merge `handoff_written` event stays local-only (specs 0212/0247
    doctrine) — spec 0250 does not touch the post-merge window."""
    body = _skill_body()
    lines = [l for l in body.splitlines() if "handoff_written" in l and "queue_state" in l]
    assert lines, "handoff_written emission not found in SKILL.md"
    offending = [l for l in lines if "--push-to-main" in l]
    assert not offending, (
        "post-merge `handoff_written` must stay local-only — spec 0250 leaves "
        f"the post-merge window (steps 18–23) unchanged. Offending: {offending}"
    )


def test_post_merge_step_23_flush_intact() -> None:
    """Step 23's single atomic `push-files-to-main` flush is intact."""
    block = _step_block(_skill_body(), 23)
    assert "push-files-to-main" in block, (
        "step 23 of dev-next SKILL.md must retain its atomic `push-files-to-main` "
        "flush — spec 0250 leaves the post-merge window unchanged"
    )
