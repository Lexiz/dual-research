---
spec: "0247"
date: 2026-05-28
version: "1.60.2"
pr: "https://github.com/Lexiz/dual-research/pull/284"
kind: post-deploy
---

# Spec 0247 — stop pre-merge step-18 push-to-main deploy-race

Refactoring. `/dev-next` step 18 ("Merge-time state update") previously pushed
the `merged` lifecycle state to `origin/main` via two `--push-to-main` commits
**before** the step-19 squash-merge. Those pre-merge commits queued `deploy.yml`
runs immediately ahead of the merge commit; under the `deploy-main` concurrency
group (`cancel-in-progress: false`) GitHub's queue-collapse rule cancelled the
merge-commit's deploy job when a stale ancestor run was mid-flight — exactly
what cancelled spec 0246's `fdd2218` deploy and forced a manual
`gh workflow run deploy.yml` recovery. This spec removes the *cause* (the
pre-merge pushes); spec 0211.3's watch-side pivot remains as defence-in-depth.

## What landed

- **`~/.claude/skills/dev-next/SKILL.md` step 18** (skill body, outside the repo):
  both writes — `queue_state set … status=merged pr=… merged_at=…` and
  `append-event … merged` — dropped their `--push-to-main` flag and became
  local-only buffered writes, with a `# spec 0247:` breadcrumb comment. The
  step-18 prose + the trailing branch-identity note were updated to match.
- **Regression guard:** `tests/test_spec_0247_pre_merge_no_push.py` — 3
  source-pattern tests against the live SKILL.md (SKIP when absent): antipodal
  absence (no `--push-to-main` in step 18's block), positive (`status=merged` +
  `merged_at` retained), breadcrumb (`spec 0247` cited).
- Version 1.60.1 → 1.60.2 (PATCH); CHANGELOG `### Changed` entry; `uv.lock`
  refreshed; version-notes sidecar regenerated (233 entries).

## Verification this cycle (the fix dogfooded itself)

- Step 18 ran local-only — **no pre-merge deploy commit was created.** The merge
  commit `dd9fbf9` was the **sole** `deploy.yml` trigger (`gh run list
  --commit dd9fbf9` returned exactly one run, `26599147578`).
- That run completed **green in 1m13s with no cancellation** — the
  `deploy-main` concurrency group had nothing queued ahead of it to collapse.
  This is the prevention spec 0247 set out to deliver, observed live on the
  cycle that shipped it (closes the spec's own Risk 4).
- Full suite 2362 passed; deployed app `https://dual-research-alex.fly.dev/`
  returns HTTP 200 on v1.60.2.

## Deferred during implementation

- **Step-18 buffer does not survive step-19's force re-detach — the merged
  fields must move past it (or be re-applied at step 23).** Spec 0247 §2.1–§2.3
  modelled step 18's local-only buffer on the step-22 `handoff_written` buffer
  (`SKILL.md:442`), assuming it would survive to the step-23 atomic flush. But
  step 22 runs **after** step 19's `git checkout --detach -f origin/main`
  (`SKILL.md:308`), whereas step 18 runs **before** it. The `-f` force-detach
  discards uncommitted working-tree changes to the tracked
  `dashboard/queue-state.json`, so the step-18 buffered `merged` state
  (`status=merged`, `pr`, `merged_at`, the `merged` event) is **wiped** before
  step 23 — verified empirically this cycle: post-merge working-tree showed
  `status=merged` while `origin/main` showed `status=in_progress`, and the
  force-detach reset the working tree to the latter. As written, the skill
  therefore drops `pr` / `merged_at` / the `merged` event at step 23, violating
  the spec's own §4 behavior-preservation. **This cycle was completed correctly
  by re-supplying `pr` + `merged_at` and re-appending the `merged` event in the
  step-23 flush** (final `origin/main` carries the full state — no field
  dropped). The durable fix belongs in the skill: move the `merged` write to
  immediately after the step-19 re-detach (joining the post-merge buffer that
  already survives), or fold the `merged` fields + event into the step-23 `set`
  / push. The shipped `tests/test_spec_0247_pre_merge_no_push.py` asserts the
  `merged` writes live **in step 18**, so the corrective spec must relocate
  those assertions to wherever the surviving write lands. Disposition: **ship** —
  it is a correctness gap in this cycle's own deliverable. Artifacts:
  `~/.claude/skills/dev-next/SKILL.md:284`–`:294` (step 18) and `:308`
  (force-detach); `tests/test_spec_0247_pre_merge_no_push.py:60`–`:96`.
