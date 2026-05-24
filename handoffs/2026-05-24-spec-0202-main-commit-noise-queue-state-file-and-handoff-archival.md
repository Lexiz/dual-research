---
spec: "0202"
date: 2026-05-24
version: "1.42.0"
pr: "https://github.com/Lexiz/dual-research/pull/230"
---

# Spec 0202 — Main-commit noise reduction: queue-state file + handoff archival + event consolidation (v1.42.0)

New-feature spec. Single mutable state file (`dashboard/queue-state.json`) becomes the authoritative source for cycle status, timestamps, PR URL, handoff pointer, and event timeline. Spec frontmatter is now a queue-time immutable snapshot. Handoff folder caps at 20; checkpoint handoffs auto-clean when their parent spec deploys. Per-spec event sidecars deprecated, folded into `queue-state.json`.

## What shipped

### In-repo (the PR diff)

- **`scripts/spec_lifecycle/queue_state.py`** (new, +395 lines). `QueueState` dataclass + JSON round-trip; `read_state(repo_root)`, `update_state(repo_root, spec_id, *, push_to_main, events_append, events_replace, **fields)` with 3-retry non-fast-forward conflict resolution preserving concurrent writers' events; `append_event_to_state` convenience wrapper; CLI subcommands `set`, `append-event`, `show`. Push-to-main path mirrors `scripts.spec_lifecycle.append_event.push_event_to_main`'s `GIT_INDEX_FILE` plumbing ([scripts/spec_lifecycle/append_event.py:124](scripts/spec_lifecycle/append_event.py:124)).
- **`scripts/spec_lifecycle/archive_handoffs.py`** (new, +180 lines). `archive_old_handoffs(handoffs_dir, cap=20, *, dry_run, protect)` moves the older files to `handoffs/archive/YYYY-MM/` keyed by filename date prefix; `cleanup_superseded_checkpoints(handoffs_dir, spec_id)` deletes `kind: in-spec-checkpoint` handoffs matching BOTH predicates. `protect={path}` shields in-flight L-spec checkpoints. CLI flags `--cap`, `--dry-run`, `--cleanup-spec`.
- **`scripts/spec_lifecycle/build_queue_state.py`** (new, +180 lines). One-time backfill: copies frontmatter + sidecar events into a fresh `dashboard/queue-state.json`, moves sidecars to `dashboard/events/archive/`, archives handoffs past the cap. Idempotent. Includes `_stringify` to coerce YAML-parsed `datetime.date` / `datetime.datetime` to ISO strings before JSON serialisation.
- **`scripts/spec_lifecycle/append_event.py`** ([read_events at lines 221-289](scripts/spec_lifecycle/append_event.py:221)) — `read_events` now first tries `dashboard/queue-state.json` (inferred from `events_dir.parent.parent` unless `repo_root=` is passed explicitly), falls back to the legacy `<events_dir>/NNNN.jsonl` sidecar. Test fixtures that pass a bare `tmp_path` keep working through the fallback.
- **`scripts/spec_lifecycle/render_dashboard.py`** ([collect at lines 162-205](scripts/spec_lifecycle/render_dashboard.py:162)) — reads `queue-state.json` once via `read_state`, layers per-spec entries over the spec frontmatter dict for cycle-mutable fields (`status`, `started_at`, `merged_at`, `deployed_at`, `pr`, `handover`, `failure_step`, `target_version`). Events come from `state.specs[NNNN].events` when present, else fall back to the legacy sidecar. Shape-immutable fields stay sourced from frontmatter. Decimal IDs (spec 0199) are handled via the existing `SPEC_ID_RE` match.
- **`pyproject.toml` + `src/dual_research/__init__.py`** — MINOR bump `1.41.2` → `1.42.0` (new-feature per spec).
- **`uv.lock`** — auto-updated for the version bump.
- **`CHANGELOG.md`** — `## [1.42.0] — 2026-05-24` section.
- **`dashboard/queue-state.json`** (new, ~210 KB). Backfill output: 194 spec entries with all events.
- **`dashboard/events/archive/`** (new). 51 per-spec sidecars moved here.
- **`handoffs/archive/2026-05/`** (new). 94 older handoffs moved here.

### Tests (1835 passed, 61 new)

- `tests/spec_lifecycle/test_queue_state.py` — 18 tests: read/write, CLI (`set`/`append-event`/`show`/`null` handling), unknown-field rejection, decimal-ID round-trip, trailing newline.
- `tests/spec_lifecycle/test_queue_state_conflict.py` — 7 tests: push-to-main happy path, race retry preserves concurrent writer's events, RuntimeError on permanent push failure with local file untouched, `events_replace` length validation, `events_append` unconditionally additive.
- `tests/spec_lifecycle/test_archive_handoffs.py` — 14 tests: cap keeps most-recent N, dry-run no-op, files-without-date-prefix skipped + warned, year-month bucketing, `protect=` set respected, `cleanup_superseded_checkpoints` matches both predicates only, handles multiple checkpoints, no-op when handoffs/ missing, CLI dry-run + cleanup-spec.
- `tests/spec_lifecycle/test_build_queue_state.py` — 12 tests: frontmatter status copy, empty-string skip, decimal IDs round-trip, sidecar load, no-sidecar spec gets `events: []`, non-spec files ignored, end-to-end runs (state file written, sidecars archived, handoffs archived, in-flight checkpoint protected), idempotency, CLI.
- `tests/spec_lifecycle/test_render_dashboard_reads_state.py` — 10 tests: status read from state-over-frontmatter, fallback to frontmatter when no state entry, immutable fields not layered, events from state, events from sidecar fallback, `read_events` shim prefers state, falls back to sidecar, legacy callers work, decimal-ID round-trip.

### Out-of-band (skill prose, not repo-tracked)

`~/.claude/skills/{spec-queue,spec-promote,dev-next,dev-queue-run}/SKILL.md` are edited in place — they live in the user's Claude config dir, not in this repo. Per spec 0202 §2.2:

- **`spec-queue/SKILL.md` step 6 + 7** — initial `queue-state.json` entry now lands in the SAME commit as the spec file (`queue_state set status=queued queued_at=... NNNN` + `queue_state append-event NNNN queued '{}'` + `git add specs/NNNN-…md dashboard/queue-state.json && git commit -m "..."`). The separate `event queued` commit at step 7 is gone — step 7 retained as a stub that points back to step 6 so step numbering stays stable.
- **`spec-promote/SKILL.md` step 8** — same shape; promotion writes initial state-file entry alongside the promoted spec file in one commit.
- **`dev-next/SKILL.md`**:
  - Global: every `uv run python -m scripts.spec_lifecycle.append_event [--push-to-main] dashboard/events` reference becomes `uv run python -m scripts.spec_lifecycle.queue_state append-event [--push-to-main]` (drops the `dashboard/events` arg).
  - Step 5 pre-flight in-progress check now reads from `dashboard/queue-state.json` instead of disk frontmatter.
  - Step 12 (cycle start) calls `queue_state set --push-to-main NNNN status=in_progress started_at=$NOW` instead of writing spec frontmatter.
  - Step 18 (merge-time flip) calls `queue_state set --push-to-main NNNN status=merged pr=URL merged_at=$NOW` with no branch-side frontmatter commit (queue-state push lands directly on main; the step-17 branch-identity assertion still guards the actual feature-branch push earlier in the flow).
  - Step 24 (post-deploy) calls `queue_state set NNNN status=deployed deployed_at=$NOW handover=PATH` plus the new step 24a's `archive_handoffs --cap 20 --cleanup-spec NNNN`, ALL committed in ONE commit with message `spec(NNNN): deployed vX.Y.Z + handoff + archive (k moved, j checkpoints cleaned)`.
  - Failure paths (steps 11, 16, 21) call `queue_state set --push-to-main NNNN status=failed failure_step=<name>` with no spec frontmatter write.
  - Deferred-spec subagent prompt (step 25.5) updated to point at `/spec-queue` step 6's new combined commit shape.
  - Failure-recovery footer note documents that queue state — not frontmatter — is the on-disk record of `status: failed`.
- **`dev-queue-run/SKILL.md`** step 2 — in-progress check reads from `queue-state.json`. Failure-recovery footer note adds the manual flip command: `uv run python -m scripts.spec_lifecycle.queue_state set --push-to-main NNNN status=queued failure_step=null`.

## Why this exists

Three coupled accumulation problems on `main` motivated the spec — spec frontmatter rewritten 3× per cycle, `handoffs/` growing unbounded (123 files at author time), per-spec event sidecars accumulating (51 at author time). All three share one architectural move: a single mutable state file becomes the authoritative cycle-state source, and the post-deploy step becomes the natural archival hook.

Net effect on `git log main`:
- Cycle commit count drops from ~8–10 per cycle to ~3 (queue-side: 1 for spec+state; branch-side: ~1 in normal flow when not migrating; post-deploy: 1 consolidated).
- `handoffs/` size on disk stays bounded; older files remain browsable in `handoffs/archive/YYYY-MM/`.
- Per-spec `dashboard/events/*.jsonl` directory disappears (existing files archived; new specs never create one).

## Acceptance evidence

Per spec §6 test plan + this cycle's own deploy:

- ✅ **Backfill produces a complete state file.** Live run: `build_queue_state: backfilled 194 specs, archived 51 event sidecars, archived 94 handoffs (protected 0 in-flight checkpoints)`. `dashboard/queue-state.json` is ~210 KB with one entry per spec on disk. Test fixture coverage in `test_build_queue_state.py`.
- ✅ **`queue_state.update_state` is conflict-safe.** Live race test in `test_queue_state_conflict.py::test_update_state_race_preserves_concurrent_events`: second clone pushes an event; first clone's push retries, re-reads origin, and preserves both writers' events.
- ✅ **`append_event_to_state` is monotonic.** `events_replace` shorter than on-disk raises ValueError; `events_append` is unconditionally additive (covered in same test file).
- ✅ **`archive_old_handoffs` keeps the most-recent N.** Live backfill: 30 entries remain in `handoffs/` (20 dated + 10 non-date-prefixed like `latest-arc.md`, `integration-state.md` — these don't match the date-prefix regex and are intentionally left in place). Test fixture coverage in `test_archive_handoffs.py`.
- ✅ **`cleanup_superseded_checkpoints` matches both predicates.** Test fixture covers the three-way discrimination (matching-checkpoint, mismatched-spec checkpoint, post-deploy same-spec) explicitly.
- ✅ **Renderer reads from queue-state.json when present + falls back to frontmatter when not.** Both paths covered in `test_render_dashboard_reads_state.py`. Live verification: post-deploy dashboard at `https://lexiz.github.io/dual-research/` (next renderer run, on push to main of this cycle's final commit).
- ✅ **One-time backfill is idempotent.** Test fixture verifies re-run is a no-op (file mtime unchanged); CLI prints "nothing to do" message.
- ✅ **`uv run pytest tests/ -q` green.** 1835 passed in 22.76s. 61 new tests, 1774 prior tests all still pass.
- ⏳ **Post-deploy commit message captures all three jobs.** Validated at this cycle's own step 24 (the commit that closes this handoff out). Pattern: `spec(0202): deployed v1.42.0 + handoff + archive (k moved, j checkpoints cleaned)`.

## Deploy notes

- Strategy: rolling (per spec 0200). Both machines (`879634f0700698`, `2872d65a660408`) cycled through `Updating → started → smoke checks → good state` in sequence. Machine `879634f0700698` was replaced by new machine `683e130b1049d8`; machine `2872d65a660408` updated in place. Lease-clear on `879634f0700698` reported "lease not found" — expected because that machine was replaced (the new replacement machine ID is `683e130b1049d8`), so the lease was naturally cleared with the old machine's destroy. Not a failure.
- Post-deploy sweep: `sweep: no stale blues on dual-research-alex`. Image-based fallback found no off-image machines.
- Smoke: `curl https://dual-research-alex.fly.dev/` → HTTP 200 in 0.34s. Cluster is converged and serving v1.42.0.

## Mechanical layout of the PR

Branch had several commits pre-squash:

- `a191061` — implementation (queue_state.py, archive_handoffs.py, build_queue_state.py, append_event.py shim, render_dashboard.py rewire, all 5 test files, version bump + CHANGELOG).
- `bb95069` — buffered event line for `implementing_started`.
- `9361468` — one-time backfill (queue-state.json + 51 sidecar moves + 94 handoff moves).
- `e245c1c` — `tests_green` event.
- `5edc919` — `_stringify` fixup for YAML-parsed dates in backfill (caught at live run; YAML returns `datetime.date` objects for ISO date literals).
- `4ab256d` — `merged` event + state-file `status: merged, pr, merged_at` (no spec frontmatter write per §2.2).
- `71b03c7` — merge of `origin/main` to resolve a dashboard/events/0202.jsonl conflict caused by the pre-migration `push_to_main` events landing on main while this branch moved the same file to archive.

All squash-merged into one commit on main as PR #230.

## Deviations from spec

- **§2.2 `events=` API**: the spec wording suggested `events_replace=` was the primary mechanism with `events_append=` as a convenience. Implementation prefers `events_append=` as the typical pathway and accepts both — `events_replace=` remains in the signature with the length-validation defense, but the caller-facing API is `events_append=` for adding new events.
- **Step-numbering in `spec-queue/SKILL.md`**: step 7 was deleted in the spec body; I kept it as a "(deprecated, see step 6)" stub so the downstream step numbers (8, 9, 10) stay stable.
- **Spec 0202's own merge cycle**: per §2.2, step 18 should call `queue_state set --push-to-main`. For this one migration cycle, `queue-state.json` did not yet exist on `origin/main` (it lands in THIS PR), so a `--push-to-main` call would have created a fresh state file from scratch, overwriting other specs' entries on main. Resolution: step 18 ran without `--push-to-main` and committed the merged-status flip on the branch instead. Subsequent cycles will use `--push-to-main` per the canonical flow because by then queue-state.json exists on main.
- **`dashboard/events/0202.jsonl` merge conflict**: pre-spec-0202 push-to-main calls for `branched` (`6d8b89d`) and `implementing_started` (`67b8dfe`) landed on main while this branch moved the same file into `dashboard/events/archive/`. Resolved by `git merge origin/main` — the conflict was content-identical (the local archived sidecar already had those event lines, having been written by `append_event` locally even though only the per-event commits were on main). One merge commit, no manual edits needed.

## Migration window note

For all cycles AFTER this one ships: `queue-state.json` exists on `origin/main` and branch-phase `queue_state append-event --push-to-main` calls behave identically to spec 0163's previous per-sidecar push — the dashboard sees branch-phase events live, just on a different file. The skill prose changes are the source of truth for the new flow; this handoff is the migration-window record.
