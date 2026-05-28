---
spec: "0247.1"
date: 2026-05-28
version: "1.60.3"
pr: "https://github.com/Lexiz/dual-research/pull/285"
kind: post-deploy
---

# Spec 0247.1 — relocate `/dev-next` merged write past step-19 force re-detach

Refactoring. Closes a correctness gap in [spec 0247](specs/0247-pre-merge-push-to-main-deploy-race-hardening.md)'s
own deliverable. Spec 0247 made `/dev-next` step-18's `merged` queue-state write
local-only (to close the pre-merge deploy-race), assuming step-23's atomic
`push-files-to-main` would flush it. But step 19's `git checkout --detach -f
origin/main` runs *between* steps 18 and 23 and force-discards uncommitted
working-tree changes to the tracked `dashboard/queue-state.json` — wiping the
step-18 buffer before step 23 and dropping `pr` / `merged_at` / the `merged`
event on every cycle. This spec relocates the write to the **post-detach** side
of step 19, where it joins the buffer cohort that demonstrably survives.

## What landed

- **`~/.claude/skills/dev-next/SKILL.md`** (skill body, outside the repo):
  - **Step 18** rewritten to *capture only* — it sets the `MERGED_AT=` shell
    variable at merge time (co-located in reasoning with the spec 0211.2
    `MERGE_SHA` capture, both read before the detach) and a `# spec 0247.1:`
    breadcrumb. The `set status=merged …` / `append-event … merged` *writes*
    are removed from step 18.
  - **Step 19** gains a new post-detach sub-block — after the force re-detach +
    branch-cleanup + verified-delete — that performs the local-only `set
    status=merged pr="$PR_URL" merged_at="$MERGED_AT"` and `append-event …
    merged` writes, with a `# spec 0247.1:` breadcrumb. No `--push-to-main`:
    the no-pre-merge-push property spec 0247 introduced is preserved.
- **Regression guard relocated:** `tests/test_spec_0247_pre_merge_no_push.py`
  now carries 5 source-pattern tests (SKIP when SKILL.md absent):
  - `test_step_18_has_no_push_to_main` — unchanged (core spec-0247 invariant).
  - `test_step_19_relocated_write_has_no_push_to_main` — **new**, antipodal
    absence extended to step 19, matched at the *command* level (step 19's prose
    legitimately mentions `--push-to-main` in the spec 0211.2 capture-reasoning,
    so a raw-substring check would false-positive; the test scans for a
    `queue_state … --push-to-main` invocation instead).
  - `test_step_19_writes_merged_state` — rewritten from
    `test_step_18_still_computes_merged_state`; asserts `status=merged` +
    `merged_at` now write in step 19's block.
  - `test_step_18_captures_merged_at_but_not_the_write` — companion: step 18
    still captures `MERGED_AT=` (capture-before-detach), but the `status=merged`
    write has left step 18 (antipodal-absence on the pre-fix shape).
  - `test_spec_0247_1_breadcrumb_present_in_step_19` — relocated breadcrumb
    assertion, now on step 19.
- Version 1.60.2 → 1.60.3 (PATCH); CHANGELOG `### Changed` entry; `uv.lock`
  refreshed; version-notes sidecar regenerated (234 entries).

## Verification this cycle (the fix dogfooded itself)

- This cycle executed the *corrected* flow: `MERGED_AT` was captured at merge
  time (step 18, before the detach); the `merged` write was issued **after**
  step 19's `git checkout --detach -f origin/main` re-detach, so the buffer was
  not force-discarded.
- After the relocated write, the working-tree `dashboard/queue-state.json`
  carried `status=merged` + `pr` + `merged_at` + the `merged` event, and those
  fields survived to the step-23 atomic `push-files-to-main` flush — the
  field-completeness spec 0247 §4 asserted but the skill had regressed is
  restored on `origin/main`.
- Full suite 2364 passed. Deploy run `26600456483` (merge commit `3ecb7ed`)
  concluded `success`; deployed app `https://dual-research-alex.fly.dev/`
  returns HTTP 200 on v1.60.3.
