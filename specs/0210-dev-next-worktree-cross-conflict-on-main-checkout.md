---
kind: dev
spec: "0210"
slug: dev-next-worktree-cross-conflict-on-main-checkout
title: "Refactor: /dev-next step 19/20/24 — eliminate worktree cross-conflict on main checkout (push-via-plumbing for handoff + archive, queue worktree never holds main)"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-24
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0210 — Refactor: `/dev-next` worktree cross-conflict on main checkout

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** PATCH — internal restructure of the `/dev-next` skill + a CLAUDE.md prose update, no runtime code change
> **Evidence:** spec 0205.2's handoff at `handoffs/2026-05-24-spec-0205.2-remove-dead-kind-tab-kind-tabs-css-and-jsx-variant-branches.md:66` ("Worktree cross-conflict during merge cleanup") is the explicit deferral. The cycle's `gh pr merge --admin --squash --delete-branch` exited 1 locally because `main` was held by the sibling author worktree, cascading into the orchestrator manually freeing main (queue worktree stash → checkout main → stash drop → branch delete) and accidentally detaching the author worktree from main mid-flow. The remote merge succeeded; only local cleanup blew up. Same failure mode is structural — recurs every cycle.

---

## 1. Current state

The dual-research repo uses a two-worktree split documented at `CLAUDE.md:43`–`:48`:

- **Authoring worktree** at `/Users/alexlisitzky/dual-research-author/` — "Stays on `main`."
- **Queue worktree** at `/Users/alexlisitzky/dual-research/` — "Cuts feature branches."

The `/dev-next` skill at `~/.claude/skills/dev-next/SKILL.md` drives the queue worktree end-to-end. Two of its steps require the queue worktree to be on `main`:

- **Step 20** at `~/.claude/skills/dev-next/SKILL.md:308` — `git checkout main && git pull`. This runs immediately after step 19's `gh pr merge --admin --squash --delete-branch` so the working tree is positioned for `fly deploy` (step 21) and the post-deploy handoff + archive commit (step 24).
- **Step 24** at `~/.claude/skills/dev-next/SKILL.md:370`–`:382` — writes the handoff file, runs the archive job, then `git add … && git commit … && git push origin main`. This requires being on `main` because the commit is created on the working-tree HEAD.

Both steps collide with the CLAUDE.md "author worktree stays on main" convention. Git's worktree model forbids two worktrees from holding the same branch (`git checkout` on one fails when another worktree already has it checked out). So the queue worktree's step-20 `git checkout main` cannot succeed while the author worktree is on main.

The other main-side writes inside `/dev-next` — step 12 (cycle-start state update), step 18 (merge-time state update), and the inline `--push-to-main` event appends — already work around this via `scripts/spec_lifecycle/queue_state.py`'s push-via-plumbing path (`queue_state.py:266`–`:382`, `update_state(push_to_main=True)`). That path builds a tree from the queue worktree's index without ever checking out main: `git read-tree`, `git update-index`, `git write-tree`, `git commit-tree -p origin/main`, `git push origin <sha>:main`. It works from any HEAD, including a detached one. Step 19's verified-delete block (`SKILL.md:284`–`:303`) and step 20–24 do NOT use this plumbing.

The 0205.2 cycle's symptom: `gh pr merge` itself succeeded on the remote (PR landed as `c0967b6`), but the local cleanup the same command attempts (delete the merged branch locally + reposition local HEAD) failed because main was held elsewhere. The orchestrator then had to dance the author worktree off main (stash queue-state edits, checkout the queue to main, drop stash, delete spec branch) to free the ref. The dance left the author worktree detached at `c0967b6` after the cycle — observed in the cycle's post-mortem and reproducible by inspecting `git worktree list` mid-flow.

**Pain points:**

- **Structural recurrence.** The failure mode is not transient — it fires every cycle the author worktree is on `main` (which is its documented steady state). Each cycle pays the manual dance tax.
- **Silent author-worktree drift.** If the dance fails midway (e.g. stash apply conflicts, operator interruption), the author worktree is left detached at the previous HEAD without a flag to the user. The 0205.2 cycle hit exactly this — author had to be manually reattached at end-of-cycle.
- **Convention contradicts mechanism.** `CLAUDE.md:47` promises the author worktree stays on main; `~/.claude/skills/dev-next/SKILL.md:308` requires the queue worktree to take main. Both can't hold true simultaneously. The skill's behaviour today is "win by forcing the author worktree off main during the cycle" — undocumented and unsafe.
- **The plumbing pattern already exists and works.** `queue_state.py:266`–`:382` proves the queue can write to `origin/main` without ever checking out main. Step 24's handoff + archive commit is the last main-side write that doesn't yet use it.

## 2. Target state

Direction (a) from the deferral, refined: **the queue worktree never holds `main`.** All main-side writes go through the existing push-via-plumbing pattern in `scripts/spec_lifecycle/queue_state.py` (or an extension of it for handoff/archive files). The author worktree's documented "stays on main" convention is preserved unchanged.

Two artifacts change:

- **`~/.claude/skills/dev-next/SKILL.md`** — step 20 is deleted (no `git checkout main && git pull`); step 21's `fly deploy` runs from the detached-at-`origin/main` HEAD the cycle ends step 19 on (`fly deploy` doesn't care about the local branch ref — it just needs the working tree at the deployed commit); step 24's `git add … && git commit … && git push origin main` is replaced with a plumbing-based equivalent that builds a tree from the queue's working tree, commits it parented on `origin/main`, and pushes the commit SHA directly via `git push origin <sha>:main`. Step 19's verified-delete block is unchanged on the remote side (`git push origin --delete`); the local-side `git branch -D` runs against the spec branch (still permitted from a detached HEAD).
- **`scripts/spec_lifecycle/queue_state.py`** gains a sibling helper that does the same plumbing for arbitrary added files (handoff + archive moves + `dashboard/events/*.jsonl` appends). Or the existing `_push_state_to_main` is generalised to accept a list of `(rel_path, content_bytes)` entries instead of just the state file. Either way, the new helper is reused from `/dev-next` step 24 and from any future caller that needs to commit non-state files to main from the queue worktree.

The queue worktree's resting state across the cycle is **detached at `origin/main`** — the same pose `/spec-queue` already uses at `~/.claude/skills/spec-queue/SKILL.md:100` (`git fetch origin && git checkout --detach origin/main`). When step 11 cuts the feature branch (`git checkout -b spec/NNNN-<slug>`), it does so from the detached HEAD. When step 19 finishes the merge, the cycle re-detaches at `origin/main` via `git fetch origin && git checkout --detach origin/main`. No local `main` ref is ever held by the queue worktree.

Behavior preservation: `fly deploy` reads the working tree, not the local branch label — it succeeds from a detached HEAD pointing at the same commit. The post-deploy commit's parent is `origin/main` (refreshed via `git fetch origin` immediately before the plumbing commit), preserving the linear history step 24 produces today. All `dashboard/queue-state.json` and `dashboard/events/*.jsonl` writes already go through plumbing — no change there. Handoff files (`handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md`) and the archive-job file moves (`handoffs/archive/YYYY-MM/*.md`) become the additional payload the new helper handles.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1: Generalise `_push_state_to_main` in `scripts/spec_lifecycle/queue_state.py`** (`queue_state.py:266`–`:382`). Extract the tree-building logic into a new helper `push_files_to_main(repo_dir, payload, commit_message)` where `payload` is a list of `(rel_path, content_bytes | None)` tuples (`None` content = file deletion, for the archive case where a file moves from `handoffs/foo.md` to `handoffs/archive/.../foo.md`). The existing `_push_state_to_main` becomes a single-entry caller of the new helper. CLI parity preserved: `queue_state set --push-to-main` continues to work identically.
  - Verified by: existing unit tests in `tests/test_queue_state_*.py` (if any) still pass; new unit test asserts the helper accepts multi-file payloads and produces one commit with all files.
- **Step 2: Add CLI subcommand `push-files-to-main`** to `scripts/spec_lifecycle/queue_state.py` so `/dev-next` step 24 can invoke it from a bash block. Signature: `uv run python -m scripts.spec_lifecycle.queue_state push-files-to-main --message "<msg>" --file <path> [--file <path> …] [--delete <path> …]`. The command reads each `--file` from disk relative to repo root and builds the multi-file commit.
  - Verified by: round-trip test that creates two files via the new CLI, fetches origin/main, asserts both appear in the resulting commit.
- **Step 3: Rewrite `/dev-next` step 24's commit block** in `~/.claude/skills/dev-next/SKILL.md:370`–`:382` to use the new helper. The bash block becomes:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state push-files-to-main \
    --message "spec(NNNN): deployed v<X.Y.Z> + handoff + archive (k moved, j checkpoints cleaned)" \
    --file dashboard/queue-state.json \
    --file handoffs/<file> \
    --file dashboard/events/NNNN.jsonl \
    --file handoffs/archive/YYYY-MM/<moved-files>...
  ```
  No `git add`, no `git commit`, no `git push origin main`, no working-tree checkout requirement.
  - Verified by: one end-to-end `/dev-next` cycle on a throwaway spec lands the post-deploy commit on `origin/main` without the queue worktree ever holding `main`.
- **Step 4: Delete step 20** at `~/.claude/skills/dev-next/SKILL.md:308` (`git checkout main && git pull`). Renumber steps 21–27 → 20–26 throughout the skill, updating cross-references in step bodies and the surrounding prose (e.g. spec 0202 §2.2 references, the "step 20's checkout" mention in step 19 at `:316`). Add a one-sentence note at the top of "Execute" explaining the queue worktree stays detached at `origin/main` for the entire cycle and re-detaches after step 19.
  - Verified by: grep the updated skill for `git checkout main`; only the spec/feature-branch checkouts (`git checkout -b spec/...`) remain. No bare `git checkout main` references.
- **Step 5: Add re-detach at end of step 19**. After the verified-delete block completes successfully (`~/.claude/skills/dev-next/SKILL.md:303`), append:
  ```bash
  git fetch origin && git checkout --detach origin/main
  ```
  This positions the queue worktree at the post-merge `origin/main` SHA without holding the `main` ref. `fly deploy` (renumbered step 20) runs from this detached HEAD against the just-merged code.
  - Verified by: `git worktree list` after step 19 shows the queue worktree at `(detached HEAD)`, not `[main]`.
- **Step 6: Update `CLAUDE.md` to reflect the new mechanism**. The two-worktree split prose at `CLAUDE.md:43`–`:48` keeps the author worktree's "stays on `main`" guarantee unchanged. Replace the queue worktree description "Cuts feature branches" with: "Operates from a detached HEAD at `origin/main`; cuts feature branches off that HEAD during `/dev-next`. Never holds the `main` ref locally — all main-side writes (queue state, handoffs, archive) go through the push-via-plumbing helper in `scripts/spec_lifecycle/queue_state.py`." One sentence added; nothing else changes.
  - Verified by: a reader of CLAUDE.md alone can reproduce the cycle's worktree state without reading the SKILL.md.
- **Step 7: Test + version bump + CHANGELOG**. Add a test in `tests/test_dev_next_no_main_checkout.py` (new file) that greps the SKILL.md body for forbidden patterns: `git checkout main` (bare, not `-b spec/`) and `git pull origin main` outside the pre-flight step 1 fast-forward. Bump `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` per PATCH (spec frontmatter). Add `## [X.Y.Z] — YYYY-MM-DD` to `CHANGELOG.md` under `### Changed`.
  - Verified by: `uv run pytest tests/test_dev_next_no_main_checkout.py -v` green; CHANGELOG renders correctly on the dashboard.

## 4. Behavior preservation

- [ ] Existing `tests/` suite (1870 tests as of v1.44.4) passes unchanged — no production code path touched.
- [ ] Existing queue-state `--push-to-main` callers (step 12, step 18, inline event appends throughout `/dev-next`) continue to work via the unchanged `update_state(push_to_main=True)` entrypoint that now delegates to the generalised helper.
- [ ] Post-deploy commit on `origin/main` from step 24 has identical shape to today's: same parent (`origin/main` at deploy time), same file set, same commit message format (`spec(NNNN): deployed v<X.Y.Z> + handoff + archive (k moved, j checkpoints cleaned)`).
- [ ] `fly deploy` succeeds from a detached HEAD (confirmed by Fly's docs and by `/spec-queue`'s existing detached-HEAD pattern at `~/.claude/skills/spec-queue/SKILL.md:100`).
- [ ] Author worktree's `git status` is unchanged across the cycle — no detach, no stash dance, no branch delete touches it. Verified post-cycle by `git worktree list` showing author at `[main]`, queue at `(detached HEAD)`.
- [ ] Dashboard timeline events (`preflight_ok` through `deployed`, `deploy_health_check_ok`, `handoff_written`) all land on `origin/main` in the same sequence and shape as today.

## 5. Out of scope

**Explicit: this spec does NOT add any new feature.** It restructures the existing main-side write mechanism so the queue worktree never holds the `main` ref. No new feature surfaces — no new dashboard signals, no new spec-lifecycle stages, no changes to spec frontmatter or queue-state schema.

- **Direction (b) — revise the CLAUDE.md two-worktree contract so the author worktree is normally detached.** Deliberately rejected. The author worktree's "stays on main" property is a UX guarantee (when an operator opens a Claude Code session there, `git status` shows `On branch main` without explanation); breaking it would surprise every author-side session. Direction (a) leaves the user-facing contract intact and absorbs the change entirely into the skill mechanics. (Deferred to: no follow-up planned. If direction (a) proves harder than estimated, a future spec can revisit.)
- **Generalising the helper to other branches.** `push_files_to_main` is named for the dual-research workflow's only main-side target. A future spec that needs to push commits to a release branch from a detached HEAD can generalise then. (Deferred to: no follow-up planned.)
- **Removing `/dev-next` step 1's `git pull --ff-only origin main`.** That step runs at cycle start to advance the local `main` ref so disk-read prompts between cycles see the current queue. Under the new mechanism the queue worktree no longer holds a local `main` — but step 1's `git pull` is benign (no-op when the local ref doesn't exist; the underlying `git fetch` is still useful). Replacing step 1 with a bare `git fetch origin` is a follow-up; this spec keeps step 1 unchanged for review minimality. (Deferred to: future cleanup spec.)
- **Touching `/dev-queue-run`.** That skill drives `/dev-next` end-to-end across multiple specs; its own logic doesn't take main-side checkouts. The fix here cascades automatically when `/dev-next` is fixed. No edits to `~/.claude/skills/dev-queue-run/SKILL.md`.
- **Backfilling the fix to historical handoffs.** The 0205.2 handoff stays as-is — it documents the failure mode this spec closes.
- **Removing the local `fly deploy` invocation in `/dev-next` step 21.** This spec's worktree restructure is a prerequisite for that change (the deploy-race fix is simpler once the queue worktree never holds `main`), but the deploy-race itself is closed in follow-up spec 0211. Doing both in one spec would conflate two reviewable concerns and inflate the diff. (Deferred to: spec 0211 — `delegate-fly-deploy-to-github-actions`.)

## 6. Risks

- **Risk: `fly deploy` rejects a detached HEAD.** *Mitigation:* `fly deploy` reads `fly.toml` + the working tree, not the git ref. Verified by `/spec-queue` running similar git operations from a detached HEAD without issue. If Fly does choke (e.g. on a `git rev-parse HEAD` lookup that prefers branch names), the cycle still succeeds — Fly's CLI accepts a detached HEAD and falls back to the commit SHA for image labelling. Reversible by re-adding step 20's `git checkout main` as a pre-deploy step if needed.
- **Risk: the multi-file plumbing helper produces a non-fast-forward push when origin/main has advanced.** *Mitigation:* the existing `_push_state_to_main` at `queue_state.py:266`–`:382` already handles this case via re-fetch + retry. The generalised helper inherits the same retry path. New unit test asserts the retry covers multi-file payloads.
- **Risk: archive file deletions are not captured by the `--file` payload form.** *Mitigation:* the helper accepts `--delete <path>` for file removals; the archive job lists moved-out paths via its existing manifest. Verified by step 2's round-trip test which includes a deletion case.
- **Risk: cross-reference drift after renumbering step 20 deletion.** *Mitigation:* step 4's verification step greps for both old and new step numbers across the SKILL.md body to catch any stale `step 20` reference. CLAUDE.md and other skills (`spec-queue`, `spec-promote`, `dev-queue-run`) do not cite specific `/dev-next` step numbers, so the renumbering is contained.
- **Risk: a future operator manually runs `git checkout main` in the queue worktree (out of habit) and re-introduces the conflict.** *Mitigation:* the CLAUDE.md prose update at step 6 explicitly documents the queue worktree as "never holds the `main` ref locally"; the `/dev-next` skill's existing "Where this runs" preamble (`SKILL.md:11`) gets a one-sentence note about the detached-HEAD invariant. Hard-enforcement via a hook is possible but out of scope here — the convention + documentation is sufficient for the single-operator workflow.
