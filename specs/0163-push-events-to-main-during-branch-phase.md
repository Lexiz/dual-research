---
kind: dev
spec: "0163"
slug: push-events-to-main-during-branch-phase
title: Push /dev-next events to main during feature-branch phase
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.24.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T15:51:01Z"
started_at: "2026-05-22T16:05:00Z"
merged_at: "2026-05-22T16:35:00Z"
deployed_at: "2026-05-22T16:38:30Z"
pr: "https://github.com/Lexiz/dual-research/pull/186"
handover: "handoffs/2026-05-22-spec-0163-push-events-to-main-during-branch-phase.md"
failure_step: ""
source_session: dashboard-live-events-investigation-2026-05-22
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0163 — Push /dev-next events to main during feature-branch phase

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds a new mechanism (in-band events-to-main pushing), five new event types, and a UI staleness chip. No breaking changes — existing events file format, frontmatter schema, and stage model are preserved.
> **Evidence:** during spec 0162's implementation at 2026-05-22T15:32–15:38, `origin/main`'s `dashboard/events/0162.jsonl` had its last event at `in_progress` (15:32:45Z) while the local branch had appended `branched` (15:32:47Z) and continued into the implementation phase. Net: the Pages Function from spec 0160 correctly served what was on main, but main itself was 5+ minutes stale because all branch-side events (`branched`, `implement_complete`, `tests_green`, `pr_opened`, `merged`) buffer locally until the squash-merge at /dev-next step 19.

---

## 1. Context

Spec 0160 introduced a Cloudflare Pages Function that pulls live data from GitHub at request time, decoupling dashboard freshness from Cloudflare's build pipeline. It works as designed. The remaining lag — 5+ minutes of "stuck on in_progress" during every cycle — turns out to be upstream of the Function entirely: it's a git-topology problem.

`/dev-next` emits events in two regimes ([`~/.claude/skills/dev-next/SKILL.md`](~/.claude/skills/dev-next/SKILL.md), steps 1–12 vs. 14–23). Steps 1–12 run on `main` and their event lines are committed to `main` in one batched commit at step 12 (the "start in_progress" commit). Steps 14 onward run on the feature branch `spec/NNNN-<slug>`; their event lines (`branched`, `implement_complete`, `tests_green`, `pr_opened`, `merged`, `deployed`, `handoff_written`) accumulate in `dashboard/events/NNNN.jsonl` on the branch. They reach `main` only when `gh pr merge --admin --squash` lands at step 19 — typically 5–20 minutes after the cycle started. The dashboard, which reads `main`, sees that entire window as a dead zone.

Spec 0156 §5 deferred "server-side push" and "per-event commit + push" as too invasive at the time. The cheaper option — surgical pushes of just the events file from the branch back to main via git plumbing, with no working-tree disturbance — was not evaluated. That's what this spec does.

## 2. Proposed change

Four coupled surfaces, one coherent feature: events stream to main as they happen, with enough new event types to make the implementation phase visible.

### 2.1 — Push-to-main mechanism in `scripts/spec_lifecycle/append_event.py`

- New module-level helper `push_event_to_main(events_dir, spec_id, new_line, *, retries=1)` added alongside the existing [`append_event`](scripts/spec_lifecycle/append_event.py) at line 23.
- Uses git plumbing — no checkout, no working-tree mutation:
  1. `git fetch origin main` (quiet).
  2. Read `dashboard/events/NNNN.jsonl` blob from `origin/main` via `git cat-file -p` (empty string if the file doesn't exist on main yet).
  3. Concatenate the existing content + the new line(s); pipe into `git hash-object -w --stdin` to get a new blob SHA.
  4. Build a new tree from `origin/main`'s tree with the events-file entry replaced/inserted using `git ls-tree` + `git mktree`.
  5. `git commit-tree <new-tree> -p origin/main -m "spec(NNNN): event <step>"` → commit SHA.
  6. `git push origin <commit-sha>:refs/heads/main` (atomic ref update; fails non-fast-forward if main moved between fetch and push).
  7. On non-fast-forward: re-fetch, rebuild from new `origin/main`, retry once. After `retries` exhausted: log a warning and continue (the event line is still safely in the local file; will reach main via the eventual squash-merge anyway).
- New CLI flag `--push-to-main` on the `append_event` module CLI. Default off (preserves existing buffered-then-squashed behavior for steps that don't need live visibility — e.g. the early steps 1/8/9/11 already commit to main inline).
- Idempotent when the working tree's current branch is already `main`: the flag becomes a no-op (the caller is already committing to main directly).
- Atomic against the local file write: `push_event_to_main` is called immediately after `append_event` writes to the local file, so a crash between the two leaves the local file ahead of main (recoverable on next push or eventual squash-merge), not the other way around.

### 2.2 — Five new event types emitted from `/dev-next` SKILL.md (host-side)

Host-side change at `~/.claude/skills/dev-next/SKILL.md`. Five new emit points, all using `--push-to-main`:

| Event                       | Inserted at                                          | What it marks                              |
|-----------------------------|------------------------------------------------------|--------------------------------------------|
| `planning_started`          | End of step 9 (after `spec_read`)                    | Orchestrator begins reasoning about scope  |
| `implementing_started`      | End of step 14 (right after `branched`)              | First file edit about to happen            |
| `tests_started`             | Start of step 16 (right before `uv run pytest`)      | Test run begins                            |
| `deploy_started`            | Start of step 21 (right before `fly deploy`)         | Fly deploy begins                          |
| `deploy_health_check_ok`    | End of step 22 (after anchor-run smoke succeeds)     | Deployed version is observably healthy     |

Each is one extra line in the SKILL.md, mirroring the existing `append_event` calls. Steps 1, 8, 9, 11, 12 keep their current buffered behavior (those commit to main inline already; --push-to-main would be redundant). Steps 14, 15, 16, 17, 18 (already on the branch) get the flag.

### 2.3 — Stages + renderer updates

- [`scripts/spec_lifecycle/stages.py`](scripts/spec_lifecycle/stages.py) at line 39 — extend `TOLERATED_NON_STAGE_STEPS` to include the five new step names. They don't anchor new stages; they're informational markers within existing stages.
- [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) — extend the in-flight hero to surface the most recent event as a "currently: `<step name>`" tag. Server-side render emits the value as a `data-current-step` attribute on the hero; the live JS keeps it in sync on each `/api/data` refresh.
- The DASHBOARD_BOOTSTRAP_JS constant at line 1458 — on each refresh, read the latest event from the `events[spec.number]` array and update the `data-current-step` attribute. Map the five new step names to human-readable labels (e.g. `implementing_started` → "implementing"). Mapping dict lives at the top of the JS so it's easy to extend.
- Per-spec `spec-NNNN.html` pages already render the full event timeline — they pick up the new step names automatically since the events file is the source. No template change needed beyond a friendly display-name lookup matching the JS dict.

### 2.4 — Staleness chip in the hero

- New chip in the in-flight hero showing "last event Ns ago", updated every second by the existing `dashboard-live.js` ticker at [scripts/spec_lifecycle/render_dashboard.py:1401](scripts/spec_lifecycle/render_dashboard.py) (extend the existing setInterval loop — no new timer).
- Color via existing chip-tone classes:
  - `< 30s` → `chip tone-ok`
  - `30s – 2min` → `chip tone-warning`
  - `> 2min` → `chip tone-danger`
- Server emits the latest event's ISO timestamp as `data-last-event-at` on the chip. The JS computes `Date.now() - dataset.lastEventAt` and rewrites the text + swaps the tone class.
- DS citation: existing `chip` composed component (canonical at `design-system/assets/styles/composed-components.css`, live copy at `src/dual_research/ui/static/components.css`; same component spec 0156 used for its `chip tone-warning` stale badge). No new DS primitives. `tone-ok` / `tone-warning` / `tone-danger` are existing token-driven variants.

## 3. UX / Behavior

- **Before:** during the implementation/test/deploy phase of any /dev-next cycle, the dashboard's last event is `in_progress` (committed early at step 12). The hero says "in flight" but nothing about the spec updates until the entire cycle completes 5–20 minutes later, at which point everything jumps to `deployed`.
- **After:** events tick onto main in real time (within ~1–2s of emission, then ~15s edge cache propagation). The visible event sequence becomes: `queued` → `cycle_started` → `preflight_ok` → `handoff_read` → `spec_read` → `planning_started` → `reconcile_complete` → `in_progress` → `branched` → `implementing_started` → `implement_complete` → `tests_started` → `tests_green` → `pr_opened` → `merged` → `deploy_started` → `deployed` → `deploy_health_check_ok` → `handoff_written`. The hero's "currently: …" tag reflects the latest step.
- **Staleness chip:** turns yellow at 30s without a new event, red at 2 minutes. During healthy implementation work that's still "no event in N seconds" — red is not a failure indicator, it's a "this stage is long" indicator. The user can glance at it and confirm whether the orchestrator is still doing something or has stalled.
- **Reduced motion:** the chip updates text + tone class on a 1s tick; no animation. Same accessibility profile as the existing live ticker.

## 4. Data / Schema deltas

- No database / Supabase changes.
- Event JSONL format unchanged: `{ts, step, data}` per line.
- Five new `step` values join the existing vocabulary. Backward compatible — older specs lacking these events render exactly as today.
- No frontmatter schema changes.
- No new env vars (the push uses the same git credentials /dev-next already has).

## 5. Out of scope

- **Side-channel event store (Supabase / Cloudflare KV).** Discussed and explicitly deferred — git stays canonical. The plumbing-based push achieves real-time freshness without splitting source of truth.
- **Dropping feature branches and working directly on `main`.** Discussed and explicitly deferred — loses PR ceremony, version-tagged PRs, and the squash-merge boundary. Too invasive for this spec.
- **Per-file `file_edited` events during implementation.** Would produce ~5–15 extra commits per cycle for marginal information gain. Out of scope; can be reconsidered as a follow-up if the user finds the implement phase still feels too quiet despite `implementing_started`.
- **Heartbeat / "still_implementing" events emitted every N minutes during long phases.** Requires the orchestrator to ping mid-tool-use, which is awkward from Claude Code's loop. Out of scope; the staleness chip in §2.4 covers the "is anything happening?" question well enough at this resolution.
- **Sub-second event timestamp resolution.** Current 1s resolution is fine; the bottleneck was always git topology, not timestamp precision.
- **Changes to the existing `cycle_started` / `queued` anchor model from spec 0156.** Stays as-is.
- **Tuning the staleness chip thresholds** (30s / 2min) based on real usage. Pick reasonable defaults; tune in a one-line follow-up if needed.

## 6. Test plan

- [ ] Unit test: `tests/spec_lifecycle/test_push_event_to_main.py` against a temp git repo — call `push_event_to_main` twice with two different events, verify two new commits land on `main` with the correct line appended to `dashboard/events/0001.jsonl`.
- [ ] Unit test: race retry — between fetch and push, simulate `origin/main` advancing (commit something else); assert the second-attempt commit is built on the new tip and succeeds.
- [ ] Unit test: idempotent on main — when the local branch is `main`, `push_event_to_main` is a no-op (the caller is already committing to main; double-push would be redundant). Assert no extra commit is created.
- [ ] Unit test: graceful failure — when `git push` fails after retries exhausted, the function logs but does not raise. The local events file still contains the line (caller already wrote it).
- [ ] Unit test: `tests/spec_lifecycle/test_stages_new_tolerated_steps.py` — assert each of the five new step names is in `TOLERATED_NON_STAGE_STEPS` and does not trip the `unknown_steps` return list from `compute_stages`.
- [ ] Unit test: renderer hero — fixture with `step: implementing_started` as the latest event; assert the rendered hero HTML contains `data-current-step="implementing_started"` and a human label.
- [ ] Unit test: `dashboard-bootstrap.js` (vitest) — fixture `/api/data` with a very recent event → chip class includes `tone-ok`; with a 90s-old event → `tone-warning`; with a 5min-old event → `tone-danger`.
- [ ] Manual: run `/dev-next` on the next queued spec; watch the dashboard during the cycle. Confirm `implementing_started` and `tests_started` appear within ~30s of emission. Confirm the "currently: …" tag updates.
- [ ] Manual: during a long implementation phase, confirm the staleness chip transitions ok → warning → danger as expected.
- [ ] Manual: complete a full cycle, verify the deployed spec's `dashboard/events/NNNN.jsonl` on `main` contains all five new event types interleaved in order with the existing ones.

## 7. Risks

- **Push race.** Two `push_event_to_main` calls emitted within the same second could both try to fast-forward `main` from the same parent SHA; only one wins. Mitigation: single retry on non-fast-forward, rebuilding from the new tip. Realistic collision rate is low — /dev-next emits events sequentially in a single shell, no concurrent emitter.
- **Network failure mid-push.** The local file write happened; the push didn't. Mitigation: the next event's push, or the eventual squash-merge at step 19, picks up the buffered lines. No data loss; just dashboard freshness lag for that one event window.
- **Tree-rewriting plumbing is fragile.** `git mktree` requires the exact entry format `git ls-tree` produces. Mitigation: thorough unit tests against a real temp git repo (not mocks). Use Python's `subprocess.run` with the same git binary the rest of /dev-next uses — no need for an alternative implementation.
- **Commit-count inflation on `main`.** Five new commits per /dev-next cycle (~doubles the existing per-cycle commit count). Mitigation: each commit is small (one-line append). The shell-only build from spec 0160 means Cloudflare rebuilds cost ~nothing. `git log --oneline` gets noisier — acceptable price for live dashboard.
- **Squash-merge later collides with main-side commits for the same file.** Branch's `dashboard/events/NNNN.jsonl` will contain `branched`/`implement_complete`/etc.; main already has them (pushed live during the cycle). The squash-merge at step 19 produces a no-op delta for those events (identical content), but the *branch's* version of the file may have lines main doesn't (events emitted on branch *without* `--push-to-main`, or events emitted between the last live-push and the merge). Mitigation: in /dev-next step 19's squash-merge, the events file gets a clean fast-forward — main already contains everything the live pushes pushed; the squash-merge contributes any remaining branch-only lines. Worst case: a few duplicate lines if both regimes pushed the same event. Acceptable; the dashboard's deduplication (by `ts + step`) is a simple follow-up if duplicates appear in practice.
- **Authentication.** /dev-next's environment already has `git push` access to `origin/main`. No new tokens.
- **Stale chip "false positives" during legitimate long phases.** A 20-minute implementation goes red on the staleness chip. That's correct — red means "no event in 2+ minutes," which is true. If users find it annoying, the thresholds tune in one line. If users want a "still alive" heartbeat: that's the deferred follow-up flagged in §5.
- **Renderer-Python drift from the live JS.** Per-spec pages (`spec-NNNN.html`) render via the Python renderer; the index uses live JS. Both need the new step → label mapping. Mitigation: keep the mapping in one Python dict and one JS dict, both edited in the same commit; cross-reference in code comments. A test could assert the two dicts agree (read both from the file system at test time).
