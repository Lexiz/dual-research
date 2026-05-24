---
spec: "0210"
date: 2026-05-24
version: "1.44.9"
pr: "https://github.com/Lexiz/dual-research/pull/242"
---

# Spec 0210 — eliminate /dev-next worktree cross-conflict on main checkout

PR: [#242](https://github.com/Lexiz/dual-research/pull/242) · admin-squash-merged · live on `dual-research-alex` as `v1.44.9` (image deployed via rolling, both machines healthy).

## What landed

- **`push_files_to_main` public helper** at [`scripts/spec_lifecycle/queue_state.py`](src/../scripts/spec_lifecycle/queue_state.py). Accepts `[(rel_path, content|None)]` payload — `None` content deletes the path from the resulting tree; `str` content writes UTF-8 text. Multi-file atomic commit on `origin/main` via the same `GIT_INDEX_FILE` plumbing as `_push_state_to_main` — `git read-tree origin/main` into a temp index, `git update-index --add --cacheinfo`/`--force-remove` for each entry, `git write-tree`, `git commit-tree -p origin/main`, `git push origin <sha>:refs/heads/main`. Up to 3 retries on non-fast-forward; each retry rebuilds the tree on top of the new `origin/main` and republishes (static payload — only the parent SHA changes).
- **`_resync_detached_head_to_origin_main` companion helper.** After a successful `push_files_to_main`, advances a detached HEAD to the new `origin/main` SHA via `git update-ref --no-deref HEAD <sha>` + `git read-tree HEAD`. No working tree files touched (assumed to already match the pushed content). Returns `False` and is a no-op when HEAD is on a branch — refuses to clobber branch refs.
- **Internals refactor.** `_push_state_to_main` is now a thin caller of the same plumbing: it uses a single-entry payload via the new `_hash_payload` + `_build_tree_multi` helpers. Existing `update_state(push_to_main=True)` callers (`/dev-next` step 12, step 18, inline event appends throughout) work via the unchanged public API — behavior preserved exactly.
- **New CLI subcommand** `uv run python -m scripts.spec_lifecycle.queue_state push-files-to-main --message MSG --file PATH [--file PATH...] [--delete PATH...] [--no-resync]`. Reads files from disk relative to `--repo-root`, builds the multi-file commit, resyncs the detached HEAD automatically (`--no-resync` to opt out).
- **`~/.claude/skills/dev-next/SKILL.md`** (host-side, outside repo — installed on the operator's machine). Step 19 appends `git fetch --quiet origin && git checkout --detach origin/main` after the verified-delete block (re-detach at the just-merged `origin/main`); step 20 (`git checkout main && git pull`) deleted; step 21 (`fly deploy`) renumbered to 20 and now runs from the detached HEAD; step 24 (rewritten and renumbered to 23) uses the `push-files-to-main` CLI instead of `git add … && git commit && git push origin main`. Steps 21–27 renumbered to 20–26 throughout, with all cross-references updated (handoff-template test, deferral-tracking prose, step-25.5 → step-24.5 subagent prose). The pre-flight section header changed from "on `main`, no branch yet" to "detached at `origin/main`, no branch yet"; the reconcile header from "still on `main`" to "still detached at `origin/main`". A new "Detached-HEAD invariant" sentence at the top documents the new pose.
- **CLAUDE.md update at line 39.** The queue worktree entry now reads: *"Operates from a detached HEAD at `origin/main`; cuts feature branches off that HEAD during `/dev-next`. Never holds the `main` ref locally — all main-side writes (queue state, handoffs, archive) go through the push-via-plumbing helper in `scripts/spec_lifecycle/queue_state.py` (spec 0210)."* The author worktree's documented "stays on `main`" pose at line 38 is unchanged.
- **Regression tests.** [`tests/spec_lifecycle/test_push_files_to_main.py`](tests/spec_lifecycle/test_push_files_to_main.py) — 6 round-trip tests via a bare-remote + working-clone fixture (same pattern as `test_queue_state_conflict.py`): (a) multi-file push in one commit, (b) deletion case (push then delete + add new path), (c) non-fast-forward retry preserves the racing writer, (d) detached-HEAD resync advances HEAD to the new `origin/main`, (e) resync is a no-op when HEAD is on a branch (refuses to clobber branch refs), (f) permanent failure returns `False` without raising. [`tests/test_dev_next_no_main_checkout.py`](tests/test_dev_next_no_main_checkout.py) — 3 source-pattern assertions on the installed SKILL.md: no bare `git checkout main`, no `git pull` outside pre-flight, detached-HEAD invariant prose is present.

## Verification

| Scenario | Where checked | Result |
| --- | --- | --- |
| Full local pytest | `uv run pytest tests/ -q` | 1896 passed (was 1887 at v1.44.8 + 9 new assertions) |
| `push_files_to_main` round-trip happy path | bare-remote fixture | multi-file commit lands, both files readable via `cat-file -p origin/main:<path>` |
| Deletion case | bare-remote fixture | old path returns 128 from cat-file (gone); new path readable |
| Non-fast-forward retry | two clones racing | both writers' files present on origin/main after retry |
| Detached-HEAD resync | bare-remote + detach | local HEAD advances from old SHA to new `origin/main` SHA |
| Branch-ref non-clobber | bare-remote + branch checkout | resync returns `False`, branch SHA unchanged |
| Live deploy smoke | `https://dual-research-alex.fly.dev/api/health` | `{"ok":true,"version":"1.44.9","backend":"supabase"}` |

## Test plan

- `uv run pytest tests/ -q` — 1896 passed.

## Deploy notes

- This cycle ran under the **OLD** model (the SKILL.md changes don't take effect until the NEXT `/dev-next` invocation). Hit the exact failure mode spec 0210 closes: `gh pr merge --admin --squash --delete-branch` automatically switched the queue worktree to local `main` and then failed to ff-pull because of a local `dashboard/queue-state.json` modification (the mirrored queue-state events from the cycle). Recovered manually by `git checkout origin/main -- dashboard/queue-state.json` → `git reset HEAD dashboard/queue-state.json` → `git checkout dashboard/queue-state.json` → `git pull --ff-only origin main`. The post-merge ff then succeeded cleanly. From the next cycle onward this recovery is unnecessary: the queue worktree stays detached at `origin/main`, the post-deploy commit goes via `push-files-to-main`, and `gh pr merge`'s local-side cleanup no longer needs to touch a held `main` ref.
- `fly deploy`: rolling deploy, both machines updated cleanly, image lease cleared, smoke checks green. Health endpoint returns `version: 1.44.9` immediately.
- Sweep: `sweep: no stale blues on dual-research-alex` — clean cluster, no fallback needed.

## Followups worth noting

- **Spec 0211 depends on this and is up next** ([specs/0211-delegate-fly-deploy-to-github-actions.md](specs/0211-delegate-fly-deploy-to-github-actions.md)). 0210 explicitly listed step-21's local `fly deploy` invocation as out of scope — the worktree restructure is a prerequisite for moving the deploy into GH Actions.
- **Spec 0202 §2.4 / step 1's `git pull --ff-only origin main`.** Spec 0210 §5 declared this out of scope for review minimality. From the next cycle onward the queue worktree's resting state is a detached HEAD; `git pull --ff-only origin main` from detached HEAD will fast-forward the detached pointer to the new `origin/main` (verified empirically — git accepts this). A future cleanup spec can replace it with a bare `git fetch origin && git checkout --detach origin/main` for clarity, but it's not breaking.

## Deferred during implementation

_None._ Everything called out in spec 0210 §3 stepwise migration landed in this PR. The two out-of-scope items in §5 (direction (b), helper generalisation to other branches) were pre-declared deferrals, not implementer-side deferrals.
