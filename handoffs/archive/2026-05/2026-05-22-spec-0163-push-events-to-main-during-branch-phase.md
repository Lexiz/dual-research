---
spec: "0163"
date: 2026-05-22
version: 1.24.0
pr: https://github.com/Lexiz/dual-research/pull/186
---

# Spec 0163 — Push /dev-next events to main during feature-branch phase

v1.24.0 ships in-band live event streaming from the feature branch back to `origin/main` via git plumbing, plus five new event types and an in-flight hero that reflects them in real time. **End-to-end was validated mid-cycle** — `implement_complete`, `tests_green`, `pr_opened`, and `merged` all landed on `origin/main` as their own commits within ~1–2s of emission, before the squash-merge. The dashboard's live API saw them on the next 15s tick.

## What landed

- `scripts/spec_lifecycle/append_event.py`
  - New `push_event_to_main(events_dir, spec_id, new_line, *, retries=1, repo_dir=None)` helper. Uses `git fetch origin main` + `git cat-file -p origin/main:<rel_path>` + `git hash-object -w --stdin` + `read-tree`/`update-index`/`write-tree` in a temp `GIT_INDEX_FILE` + `git commit-tree -p origin/main` + atomic `git push origin <sha>:refs/heads/main`. No working tree mutation, no checkout, no touching the main index. On non-fast-forward: re-fetch + rebuild + retry once. After retries exhausted: warning to stderr and return False; the line is already in the local file and will reach main via the eventual squash-merge.
  - Spec body suggested `git ls-tree + git mktree` for the tree-walk; the implementation uses `update-index --cacheinfo` against a temp index instead. Same observable result (a new root tree atop `origin/main` with one file replaced), substantially less code, no manual path climb. Documented in code.
  - New CLI flag `--push-to-main` on the module; `append_event(push_to_main=True)` for library callers.
  - Bug fix during implementation: when callers pass an absolute `events_dir` (common in tests and from the SKILL.md when run from the repo root), `update-index` rejected the absolute path. Helper now makes it repo-relative when `repo_dir` is set.
- `scripts/spec_lifecycle/stages.py`
  - Five new step names in `TOLERATED_NON_STAGE_STEPS`: `planning_started`, `implementing_started`, `tests_started`, `deploy_started`, `deploy_health_check_ok`.
  - New `STEP_LABELS` dict — single Python source of truth for human-readable step names, mirrored verbatim into `DASHBOARD_BOOTSTRAP_JS`.
- `scripts/spec_lifecycle/render_dashboard.py`
  - In-flight hero `<section>` now carries `data-current-step="<latest_step>"` for headless inspection.
  - New `currently · <label>` chip in the hero's chip row.
  - New staleness chip with `data-last-event-at="<iso>"`. Server-rendered tone matches what the JS will compute at first paint (no flash). Tones: `< 30s` → `tone-ok`, `30s–2min` → `tone-warn`, `> 2min` → `tone-err`. Reused the existing `chip` composed component — zero new DS primitives.
  - **Note on tone naming:** the spec body cited `tone-warning` / `tone-danger` for the staleness chip, but the DS only has `tone-warn` / `tone-err` (per `design-system/assets/styles/composed-components.css`). Used the actual DS tones — flagged inline in code.
  - `DASHBOARD_LIVE_JS` extended: existing `setInterval(tick, 1000)` now also handles `[data-last-event-at]` elements (text + tone swap).
  - `DASHBOARD_BOOTSTRAP_JS` now carries `STEP_LABELS` + `staleTone(seconds)` + `stepLabel(step)` helpers and emits both chips in `renderHeroInflight`.
- Host-side `~/.claude/skills/dev-next/SKILL.md`
  - Step 9 emits `planning_started` (no `--push-to-main` — committed inline in step 12's batch).
  - Step 14 emits `branched` + `implementing_started` with `--push-to-main`.
  - Step 15b emits `implement_complete` with `--push-to-main`.
  - Step 16 wraps the pytest run with `tests_started` + `tests_green`, both `--push-to-main`.
  - Step 17 emits `pr_opened` with `--push-to-main`.
  - Step 18 emits `merged` with `--push-to-main`.
  - Step 21 emits `deploy_started` (on main, no flag).
  - Step 22 emits `deploy_health_check_ok` (on main, no flag).

## Tests

- 6 unit tests for `push_event_to_main` against a real temp git repo: happy path with two events, race retry on non-fast-forward, idempotent on `main`, graceful failure when push fails, `append_event(push_to_main=True)` integration, appending atop an existing on-main events file.
- 3 unit tests for the new `TOLERATED_NON_STAGE_STEPS` + `STEP_LABELS` coverage.
- 4 unit tests for the renderer hero's `data-current-step` / chip labels / staleness chip / unknown-step fallback.
- 4 happy-dom vitest cases for the JS staleness chip (5s / 90s / 300s tone class) + `data-current-step` paint.
- Full pytest suite: **1532 passed in 19.66s**.
- Full vitest suite: **9 passed (9)**.

## Deploy notes

- `fly deploy` succeeded in landing v1.24.0 across both machines (image `01KS88S0ZCTW0WY3XD37HCV1SB`, version 293, 2/2 healthy on iad) but the rollout surfaced a transient `failed to get lease on VM 7815697b157728: machine not found` warning. The named VM ID doesn't appear in `flyctl machines list` — likely an orphaned reference Fly's orchestrator carried from a previous deploy. Non-fatal: bluegreen continued, new green machines came up healthy, the cluster converged. `/api/health` returned `{"ok":true,"version":"1.24.0","backend":"supabase"}`.
- Post-deploy sweep: `sweep: no stale blues on dual-research-alex` (cluster size 2/2, expected — Fly self-destroyed any blues this round).

## Verification mid-cycle

The clearest validation that the mechanism actually works: I watched `dashboard/events/0163.jsonl` on `origin/main` advance live during this very cycle. Branch-only event (`branched`, emitted before the spec landed) stayed on the branch; `implement_complete`, `tests_green`, `pr_opened`, and `merged` all reached `origin/main` as standalone commits while the branch was still open. The dashboard's `/api/data` endpoint reflected each new event on the next 15s poll.

## Operational note — merge conflict mid-cycle

The first squash-merge attempt failed because `dashboard/events/0163.jsonl` diverged: the branch had `branched` (emitted *without* `--push-to-main`, since that flag was being implemented in this cycle) plus everything else; main had everything else from the live pushes but no `branched`. Resolved by merging `origin/main` into the branch, restoring the `branched` line, and re-squashing. **Going forward, this is a non-issue** — the new SKILL.md step 14 emits `branched` with `--push-to-main`, so the file stays in lockstep from the start of the very next cycle.

## What's still rough

- The bluegreen lease warning is a Fly orchestrator quirk that has now bitten three deploys in a row (handoffs 0160, 0161, 0163). Spec 0162's sweep handles `safe_to_destroy` cleanup but doesn't help when Fly's lease table itself references a non-existent VM. Worth thinking about a pre-deploy probe.
- `deploy_started`, `deployed`, `deploy_health_check_ok` are all on main locally, so they reach the dashboard at step 24's commit-and-push rather than truly live. Acceptable — the deploy itself is the user-visible signal, and the staleness chip handles the "is anything still happening" question. Documented in §2.2's prose.
