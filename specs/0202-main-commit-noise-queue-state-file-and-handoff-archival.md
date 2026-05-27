---
kind: dev
spec: "0202"
slug: main-commit-noise-queue-state-file-and-handoff-archival
title: Main-commit noise reduction — queue-state file + handoff archival + event consolidation
type: new-feature
label: new-feature
version_bump: MINOR
target_version: ""
status: in_progress
depends_on: ["0199"]
complexity: L
created: 2026-05-24
queued_at: ""
started_at: "2026-05-23T23:33:14Z"
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: orchestrator-hardening-series-2026-05-24
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0202 — Main-commit noise reduction: queue-state file + handoff archival + event consolidation

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** 0199 (decimal IDs / queue-position drop — this spec presumes spec IDs are the queue order)
> **Bump:** MINOR — introduces a new architectural piece (`dashboard/queue-state.json`) and changes where cycle state lives; no spec is renumbered, no behaviour reverts, the dashboard URL is unchanged.
> **Evidence:** Spec 5 of a 7-spec orchestrator-hardening series. Author: the user, 2026-05-24 orchestrator-audit conversation. Current `git log --oneline -200 main` shows 175 admin / 25 code commits (88% admin); `handoffs/` carries 120 files; `dashboard/events/` carries 50 per-spec sidecars. Pain point: code commits drown in admin churn, and per-spec doc folders grow unbounded.

---

## 1. Context

Three coupled accumulation problems on `main` motivate this spec.

**1. Spec frontmatter is rewritten on every cycle status change.** [~/.claude/skills/dev-next/SKILL.md](docs/dev-next-skill-ref.md) step 12 rewrites the spec's frontmatter to flip `status: queued → in_progress` (plus `started_at`); step 18 rewrites it again for `status: merged, pr, merged_at`; step 24 rewrites it a third time for `status: deployed, deployed_at, handover`. Each rewrite is one commit to `main` against the spec file. Combined with `--push-to-main` event-sidecar commits ([scripts/spec_lifecycle/append_event.py:61](scripts/spec_lifecycle/append_event.py:61), spec 0163), a typical cycle lands 8–10 admin commits per spec. After ~70 specs, that's ~600 admin commits in `git log` competing with ~70 code commits. The spec audit also flagged that the post-deploy commit at step 24 is overloaded — it does the status flip, the handoff write, *and* (pre-0199) the full-queue re-rank, all in one commit message.

**2. The `handoffs/` folder grows unbounded.** `handoffs/` currently holds 120 files committed directly to git. There's no rotation, no archive, no cap. L-spec checkpoint handoffs are doubly leaky: when an L-spec writes a `kind: in-spec-checkpoint` handoff at cycle 1 ([scripts/spec_lifecycle/checkpoint.py](scripts/spec_lifecycle/checkpoint.py), spec 0186), and then ships at cycle 2 with a final `post-deploy` handoff, the cycle-1 checkpoint stays in `handoffs/` forever — superseded but never deleted. Every multi-cycle L-spec leaves one or more orphaned checkpoint files behind.

**3. Per-spec event sidecars accumulate without bound.** `dashboard/events/NNNN.jsonl` exists for every spec ever queued, all 50 of them committed to git. The renderer reads them ([scripts/spec_lifecycle/render_dashboard.py:141](scripts/spec_lifecycle/render_dashboard.py:141) — `events = read_events(events_dir, spec_id)`), but a deployed spec from weeks ago doesn't need its sidecar on the hot path. There's no archival.

Spec 0199 already dropped the `queue_position` frontmatter field, so re-ranking is no longer a source of churn. This spec addresses the remaining frontmatter-write side and the doc-accumulation side together because the two halves share one architectural move: a single mutable state file (`dashboard/queue-state.json`) becomes the authoritative source for cycle state, and the post-deploy step in `/dev-next` becomes the natural archival hook for handoffs and (now-consolidated) events.

### Traceability table — source items → spec sections

Source: this spec's atomic items come from the user's brief in the 2026-05-24 orchestrator-audit conversation (no NOTES.md or ideation file). Per the gate added by spec 0198 §2.2, every named atomic item must land in this spec body or defer to §5 with a follow-up target.

| Source item | Source ref | Spec section |
|---|---|---|
| Single queue-state file replaces per-spec frontmatter status writes | user brief, "the fix — three parts", part 1 | §2.1 |
| `dashboard/queue-state.json` as the file name | user brief, "files likely to change" (suggested name) | §2.1 (adopted verbatim) |
| Spec frontmatter `status` becomes a queue-time snapshot, not authoritative | user brief, "four baked-in design decisions" item 1 | §2.1 + §2.5 |
| Handoff archive on age + count, cap at N = 20 | user brief, "the fix — three parts", part 2.a | §2.3 |
| L-spec checkpoint cleanup on final post-deploy handoff | user brief, "the fix — three parts", part 2.b + "risks" item 3 | §2.3 |
| One-time backfill of 120 existing handoffs | user brief, "the fix — three parts", part 2.c + §6 test plan | §2.6 + §6 |
| Event-sidecar lifecycle — fold into queue-state.json | user brief, "the fix — three parts", part 3 + 2026-05-24 `AskUserQuestion` (option B selected) | §2.4 |
| Handoff archive folder is git-tracked (not .gitignored) | user brief, "four baked-in design decisions" item 2 | §2.3 (cited as constraint) |
| Archive at deploy time, not as a cron | user brief, "four baked-in design decisions" item 3 | §2.3 + §2.4 |
| One-time backfill is part of this spec's pre-merge actions | user brief, "four baked-in design decisions" item 4 | §2.6 |
| Concurrent writes risk (two skill sessions) | user brief, "risks" item 4 | §2.1 (write helper) + §7 |

No items deferred. All eleven ship in this spec.

### Verified against current code

- Spec frontmatter status flips happen at `/dev-next` steps 12, 18, 24, and at failure-recovery points in steps 11, 16, 21 (per [~/.claude/skills/dev-next/SKILL.md](docs/dev-next-skill-ref.md)). Confirmed against the skill body read at author time.
- `--push-to-main` lives at [scripts/spec_lifecycle/append_event.py:61](scripts/spec_lifecycle/append_event.py:61) (`push_event_to_main`) and writes one commit per event to `dashboard/events/NNNN.jsonl`. Confirmed — the function uses `GIT_INDEX_FILE` plumbing to push without disturbing the working tree.
- The renderer reads per-spec sidecars at [scripts/spec_lifecycle/render_dashboard.py:141](scripts/spec_lifecycle/render_dashboard.py:141) and frontmatter timestamps (`started_at`, `deployed_at`) at [scripts/spec_lifecycle/render_dashboard.py:80](scripts/spec_lifecycle/render_dashboard.py:80). Confirmed.
- L-spec checkpoint handoffs have `kind: in-spec-checkpoint` and `spec: "NNNN"` in frontmatter, per [scripts/spec_lifecycle/checkpoint.py](scripts/spec_lifecycle/checkpoint.py). Confirmed.
- `git log --oneline -200 main | grep -E 'spec\(.*\):' | wc -l` = 175 / 200 (87.5%). `ls handoffs/ | wc -l` = 120. `ls dashboard/events/ | wc -l` = 50. Confirmed at author time.
- `dashboard/queue-state.json` does not exist on `main` today. Confirmed via `ls dashboard/`.

---

## 2. Proposed change

### 2.1 — `dashboard/queue-state.json` as the cycle-state file

**New file: `dashboard/queue-state.json`.** Single JSON document, committed to `main`, holding all mutable cycle state for every spec. Schema:

```json
{
  "version": 1,
  "updated_at": "2026-05-24T12:34:56Z",
  "specs": {
    "0152": {
      "status": "deployed",
      "started_at": "2026-05-22T12:00:00Z",
      "merged_at": "2026-05-22T13:10:00Z",
      "deployed_at": "2026-05-22T13:15:00Z",
      "pr": "https://github.com/Lexiz/dual-research/pull/123",
      "target_version": "1.36.0",
      "handover": "handoffs/2026-05-22-spec-0152-foo.md",
      "failure_step": null,
      "events": [
        {"ts": "2026-05-22T11:50:00Z", "step": "queued", "data": {}},
        {"ts": "2026-05-22T12:00:00Z", "step": "cycle_started", "data": {}},
        {"ts": "2026-05-22T12:00:30Z", "step": "in_progress", "data": {}}
      ]
    },
    "0153": { "status": "queued", "events": [{"ts": "...", "step": "queued", "data": {}}] }
  }
}
```

Top-level keys: `version` (schema version, starts at `1`), `updated_at` (timestamp of the last write — used by the dashboard for a "last refreshed" hint), `specs` (map keyed by spec ID — strings, supporting decimal IDs per spec 0199).

Per-spec keys are *all optional* except `status`. Missing keys (e.g., `deployed_at` for an `in_progress` spec) are `null` or absent — the renderer reads defensively. `events` is an append-only list of `{ts, step, data}` triples; the shape matches today's `dashboard/events/NNNN.jsonl` line shape so the renderer's existing stage-derivation code ([scripts/spec_lifecycle/stages.py](scripts/spec_lifecycle/stages.py), referenced by `compute_stages` in [scripts/spec_lifecycle/render_dashboard.py:486](scripts/spec_lifecycle/render_dashboard.py:486)) keeps working with minimal change.

**New module: `scripts/spec_lifecycle/queue_state.py`.** Typed read/write interface:

- `read_state(repo_root: Path) -> QueueState` — load `dashboard/queue-state.json`, returns an empty state if the file doesn't exist. Pure function.
- `update_state(repo_root: Path, spec_id: str, *, push_to_main: bool = False, **fields) -> Path` — read-modify-write. Atomic at the JSON-document level (rewrite the whole file each time — the file is small, ~200 specs × ~500 bytes = ~100 KB, well under git's blob comfort zone). When `push_to_main=True`, the write is committed to `main` directly via the same git-plumbing path that `push_event_to_main` already uses at [scripts/spec_lifecycle/append_event.py:170](scripts/spec_lifecycle/append_event.py:170) (`_build_tree_with_temp_index`). Conflict handling: on `non-fast-forward` push rejection, refetch `origin/main`, replay the local diff onto the new tip, retry up to 3 times. After 3 conflicts, surface a clear error to the caller — the on-disk file is still safe and the caller can choose to halt or retry manually.
- `append_event_to_state(repo_root: Path, spec_id: str, step: str, data: dict, *, push_to_main: bool = False) -> None` — convenience wrapper that calls `update_state` to append one entry to the spec's `events` list. Replaces today's `append_event(events_dir, spec_id, step, data)`.

The `events` field on each spec is append-only — `update_state` validates that no caller passes a shorter `events` array than what's already on disk (defends against accidentally clobbering live data during a concurrent-write race).

**Spec frontmatter `status` becomes a queue-time snapshot.** Once a spec is committed via `/spec-queue` or `/spec-promote`, its frontmatter is immutable. The validator at [scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py) is unchanged — frontmatter shape requirements still hold — but no skill, script, or `/dev-next` step rewrites the frontmatter after the initial queue commit. Existing legacy specs (with status drifted from queue-time) are reconciled by the one-time backfill in §2.6.

### 2.2 — Skill updates: status writes redirect to queue-state.json

**File: `~/.claude/skills/spec-queue/SKILL.md`.** Step 6 currently commits the spec file alone:

```bash
git add specs/NNNN-<slug>.md
git commit -m "Spec NNNN — <title> (queued)"
git push origin HEAD:main
```

Replace with a combined commit that includes the initial queue-state entry:

```bash
uv run python -m scripts.spec_lifecycle.queue_state \
  set NNNN status=queued queued_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
git add specs/NNNN-<slug>.md dashboard/queue-state.json
git commit -m "Spec NNNN — <title> (queued)"
git push origin HEAD:main
```

Step 7 (the separate `event queued` commit) is deleted — the `queued` event is appended to `dashboard/queue-state.json` inside the same commit. Drops one commit per spec at queue time.

**File: `~/.claude/skills/spec-promote/SKILL.md`.** Same shape — promotion writes the initial `queued` entry into queue-state.json in the same commit that lands the promoted spec.

**File: `~/.claude/skills/dev-next/SKILL.md`.** Every `status: …` frontmatter write is replaced by a `queue_state.update_state(...)` call. Specifically:

- **Step 12** (cycle start): was "Update frontmatter `status: in_progress, started_at: <now>`. Append event `in_progress`. Commit + push (spec frontmatter, the buffered preflight/handoff/spec/reconcile events, and this `in_progress` event all in one commit)." Becomes: "Call `update_state(spec_id, status='in_progress', started_at=now, events=[...buffered + in_progress])` with `push_to_main=True`. No spec frontmatter write." Single commit, against queue-state.json only.
- **Steps 14, 15, 16, 17** (branched / implementing_started / implement_complete / tests_started / tests_green / pr_opened): the `append_event(--push-to-main)` calls become `append_event_to_state(--push-to-main)`. Same commit cadence (one per event) but every commit lands on `dashboard/queue-state.json`, not on per-spec sidecars. `git log -- specs/NNNN-*.md` shows the queue commit only.
- **Step 18** (merge-time flip): was "On the branch, update frontmatter: `status: merged, pr: <url>, merged_at: <now>`. Commit + push. Emit `merged` event." Becomes: "Call `update_state(spec_id, status='merged', pr=url, merged_at=now)` with `push_to_main=True`, appending the `merged` event in the same call." No branch-side frontmatter commit.
- **Step 24** (post-deploy): was "Update spec frontmatter: `status: deployed, deployed_at: <now>, handover: handoffs/<file>`. One commit with all of the above plus the buffered branch-side event lines. Push." Becomes: "Call `update_state(spec_id, status='deployed', deployed_at=now, handover=path, events=[...remaining])` plus the new archive operations from §2.3 and §2.4 in **one commit** to `main`."
- **Failure paths** (steps 11, 16, 21): the `status: failed, failure_step: <name>` writes become `update_state(spec_id, status='failed', failure_step=name)` calls. No frontmatter write.
- **Step 25.5** (deferred-spec subagent): the subagent's `/spec-queue` flow follows the new shape — initial state-file entry + spec file in one commit.

**File: `~/.claude/skills/dev-queue-run/SKILL.md`.** Audit for any status-writes; if present, redirect them to `update_state`. The supervisor primarily orchestrates `claude -p` calls, so it likely has no direct writes — the audit confirms or documents.

### 2.3 — Handoff lifecycle: archive + cap + checkpoint cleanup

**Live-folder cap.** `handoffs/` is capped at the most recent **N = 20** files (configurable as a module-level constant in the new archive script; default and only-tuned value is 20). Older files move to `handoffs/archive/YYYY-MM/` keyed by the month derived from the filename date prefix (`YYYY-MM-DD-spec-NNNN-<slug>.md`). The archive folder is committed to git — the brief's "four baked-in decisions" item 2 makes this a hard requirement, not a `.gitignore` entry, so history stays browsable.

**New script: `scripts/spec_lifecycle/archive_handoffs.py`.**

- `archive_old_handoffs(handoffs_dir: Path, cap: int = 20, *, dry_run: bool = False) -> list[tuple[Path, Path]]` — returns the list of `(src, dst)` pairs moved (or that would be moved when `dry_run=True`). Sorts entries by filename (date-prefixed → lexicographic = chronological), keeps the newest `cap`, moves the rest under `handoffs/archive/YYYY-MM/`. The `YYYY-MM` is parsed from the filename's date prefix; files whose names don't match the date prefix pattern are left untouched and warning-logged.
- `cleanup_superseded_checkpoints(handoffs_dir: Path, spec_id: str) -> list[Path]` — scans `handoffs/` for files where the frontmatter has both `kind: in-spec-checkpoint` AND `spec: "NNNN"`. Deletes each match. Returns the list of deleted paths. Both predicates required — defends against deleting the wrong file if a future handoff kind ever uses `spec: "NNNN"` alone.
- CLI entry-point: `uv run python -m scripts.spec_lifecycle.archive_handoffs --cap 20` runs `archive_old_handoffs` against the repo's `handoffs/` and prints the moved list. `--dry-run` previews without moving.

**Wiring into `/dev-next`.** After step 24's post-deploy commit (the new "single deploy commit"), add step 24a:

```bash
uv run python -m scripts.spec_lifecycle.archive_handoffs --cap 20
uv run python -c "
from pathlib import Path
from scripts.spec_lifecycle.archive_handoffs import cleanup_superseded_checkpoints
deleted = cleanup_superseded_checkpoints(Path('handoffs'), 'NNNN')
for p in deleted: print(f'cleaned checkpoint {p}')
"
```

Both operations stage their changes and are committed alongside the deployed-status update in the same commit, so the post-deploy commit message becomes: `spec(NNNN): deployed v<X.Y.Z> + handoff + archive (k moved, j checkpoints cleaned)`. One commit, three jobs disambiguated in the message instead of overloaded silently.

**Checkpoint cleanup is conditional on a deployed handoff being the trigger.** Per the brief: "When an L-spec writes its **final post-deploy** handoff, the L-spec's prior `kind: in-spec-checkpoint` handoff files are deleted in the same commit." This is fired only at step 24 (deploy success). A failed cycle that halts before step 24 leaves checkpoints intact — they're the resume target for the next `/dev-next` invocation. The cleanup is also a no-op for M and S specs (no checkpoints ever written), so the call is cheap and unconditional from the `/dev-next` body's perspective.

### 2.4 — Event consolidation: events live in queue-state.json

**Per-spec sidecars deprecated.** `dashboard/events/NNNN.jsonl` is no longer written for new specs. Events live inside the spec's entry under `dashboard/queue-state.json` (`specs[NNNN].events` — see §2.1 schema). The rename of `append_event` → `append_event_to_state` (§2.1) carries this through.

**Backwards-compatibility shim in `read_events`.** [scripts/spec_lifecycle/append_event.py:221](scripts/spec_lifecycle/append_event.py:221) — `read_events(events_dir, spec_id)` — is kept but rewired: it now reads from `queue-state.json` if the spec has an entry there, falling back to the legacy `dashboard/events/NNNN.jsonl` sidecar otherwise. This keeps test fixtures and any external callers happy during the migration window.

**Per-spec sidecar archival.** The one-time backfill (§2.6) reads each existing `dashboard/events/*.jsonl`, folds its lines into the corresponding spec's `events` array in queue-state.json, then moves the consumed sidecar to `dashboard/events/archive/NNNN.jsonl`. New specs from §2.2 onwards never create a top-level sidecar — they write directly to queue-state.json. The `dashboard/events/archive/` folder is git-tracked (same rule as `handoffs/archive/`).

### 2.5 — Renderer reads from queue-state.json

**File: `scripts/spec_lifecycle/render_dashboard.py`.**

- [Line 128](scripts/spec_lifecycle/render_dashboard.py:128) — `collect(repo_root)` is rewired. It now (a) loads `queue-state.json` once via `read_state`, then (b) iterates spec files and builds `SpecRow` instances where the cycle-mutable fields (`status`, `started_at`, `merged_at`, `deployed_at`, `pr`, `handover`, `failure_step`, `target_version`, `events`) come from queue-state.json, and the shape-immutable fields (`title`, `type`, `complexity`, `depends_on`, `version_bump`, `slug`, `label`) come from the spec frontmatter.
- [Line 141](scripts/spec_lifecycle/render_dashboard.py:141) — `events = read_events(events_dir, spec_id)` is replaced by reading `events` off the state entry. The legacy sidecar read path stays in `read_events` for the backwards-compatibility shim from §2.4.
- `SpecRow.cycle_seconds` ([line 79](scripts/spec_lifecycle/render_dashboard.py:79)) reads `started_at` and `deployed_at` from the state entry, not from `fm`. Logic unchanged otherwise.
- `SpecRow.status` ([line 63](scripts/spec_lifecycle/render_dashboard.py:63)) reads from the state entry. Spec frontmatter's `status` is the immutable snapshot — useful for audit but not what the dashboard renders.
- A spec without a state-file entry (legacy, not yet backfilled, or freshly created via a future workflow we haven't built) falls back to frontmatter so the renderer never blows up.

**No HTML/UI changes.** The hero, pipeline strip, history table, and metrics tab keep their existing markup. This spec changes the data source, not the presentation. Out-of-scope per the brief.

### 2.6 — One-time backfill

**New script: `scripts/spec_lifecycle/build_queue_state.py`.** Runs once during the implementation of this spec. Steps:

1. Read every `specs/NNNN-*.md` (and `specs/NNNN.M-*.md` per spec 0199). For each, copy frontmatter `status`, `started_at`, `merged_at`, `deployed_at`, `pr`, `handover`, `failure_step`, `target_version` into the new state entry. (Specs whose frontmatter doesn't carry one of these fields get `null`/absent.)
2. Read every `dashboard/events/*.jsonl`. For each, parse the JSONL lines and inject the resulting list as `state.specs[NNNN].events`.
3. Write `dashboard/queue-state.json` with `version: 1`, `updated_at: <now>`, and the populated `specs` map.
4. Move `dashboard/events/NNNN.jsonl` → `dashboard/events/archive/NNNN.jsonl` for every consumed sidecar.
5. Archive handoffs: call `archive_old_handoffs(Path('handoffs'), cap=20)` — moves the 100 oldest handoffs (of the current 120) into `handoffs/archive/YYYY-MM/` subfolders.

The script is idempotent — re-running on an already-backfilled repo is a no-op (it detects the state file's existence and exits cleanly with a "nothing to do" message). It runs from the implementing branch as a single commit message `spec(0202): one-time backfill — queue-state.json, archived 50 event sidecars, archived 100 handoffs` so the diff is self-contained and reviewable.

**In-flight spec handling.** If at backfill time exactly one spec has `status: in_progress` (the one this very spec is being shipped under, or a separate one resuming via checkpoint), its checkpoint handoff is preserved in the live `handoffs/` folder *regardless of cap* — the archive logic skips files referenced by any active `kind: in-spec-checkpoint` whose `spec` matches an `in_progress` entry in the state file. This protects the resume target.

---

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a `dev` reading `git log main`, I want to see code commits surface above admin churn so that the most recent meaningful change to the repo is visible without scrolling.

> As a `dev` opening the `handoffs/` folder, I want to see only the most recent ~20 files so that finding the latest cycle's notes doesn't require sorting through months of history.

> As a `dev` whose L-spec finally shipped after multiple checkpoint cycles, I want the prior checkpoint handoffs cleaned up automatically when the final post-deploy handoff lands so that the folder doesn't accumulate stale resume targets.

> As a `dev` checking the live dashboard, I want it to render accurate cycle status without requiring spec frontmatter to be rewritten on every transition, so that the spec file's git history stays clean.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** A queued spec lands with no frontmatter churn during its cycle.
> GIVEN a fresh spec authored via `/spec-queue` (status flips through `queued → in_progress → merged → deployed`)
> WHEN the cycle completes via `/dev-next` and the spec is deployed
> THEN `git log --oneline -- specs/NNNN-<slug>.md` shows exactly one commit (the original queue commit), and the spec's status as rendered by the dashboard comes from `dashboard/queue-state.json`.

> **Scenario 2:** Handoff folder caps at 20 after a deploy.
> GIVEN `handoffs/` contains 25 files before `/dev-next` begins its post-deploy step
> WHEN the post-deploy step at `/dev-next` step 24a runs `archive_old_handoffs`
> THEN `handoffs/` contains exactly 20 files (the most recent by filename) and the other 5 live under `handoffs/archive/YYYY-MM/` keyed by their date prefix.

> **Scenario 3:** L-spec checkpoint cleanup fires on final post-deploy handoff.
> GIVEN an L-spec NNNN wrote a `kind: in-spec-checkpoint` handoff at cycle 1, was resumed, and is about to write its `kind: post-deploy` handoff at cycle 2
> WHEN `/dev-next` step 24a calls `cleanup_superseded_checkpoints('handoffs', 'NNNN')`
> THEN the cycle-1 checkpoint file is deleted and the deletion lands in the same git commit as the new post-deploy handoff.

> **Scenario 4:** Dashboard renders cycle state from queue-state.json after migration.
> GIVEN the one-time backfill from §2.6 has run and `dashboard/queue-state.json` exists with entries for all 200 specs
> WHEN `scripts/spec_lifecycle/render_dashboard.py` builds the dashboard
> THEN every spec's `status`, `started_at`, and `deployed_at` is read from the state file (verified by checking the rendered HTML against the state file's contents), and per-spec sidecars under `dashboard/events/` are no longer accessed for any spec that has a state-file entry.

---

## 4. Data deltas

**New file: `dashboard/queue-state.json`** — schema in §2.1. Single document, committed to `main`, mutated by `queue_state.update_state`. No migration of existing JSON consumers (the file is new — no readers other than the renderer + queue-state module that this spec introduces).

**New folder: `dashboard/events/archive/`** — git-tracked. Receives per-spec sidecars during the one-time backfill (§2.6). No further writes after the backfill commit.

**New folder: `handoffs/archive/YYYY-MM/`** — git-tracked. Receives files older than the most-recent 20 from `handoffs/`. Subfolders keyed by `YYYY-MM` derived from filename date prefix.

**Spec frontmatter semantics shift, not schema shift.** No field is renamed or removed; existing fields (`status`, `started_at`, etc.) remain in the frontmatter as queue-time snapshots, but skills/scripts stop writing them after the initial queue commit. No migration breaks any existing spec on disk.

---

## 5. Out of scope

- **Renumbering or rewriting existing specs.** The 200 specs on disk keep their filenames and frontmatter unchanged.
- **Dashboard HTML/UI changes.** Hero, pipeline strip, history, metrics tab, primer page — all unchanged. Data source shifts; presentation does not.
- **Further reducing in-cycle event-push count.** This spec keeps the existing `--push-to-main` cadence (~7 events per cycle from branch phase), with the change that those pushes now hit `dashboard/queue-state.json` instead of per-spec sidecars. If a future tightening wants to batch event pushes (e.g., one push per stage rather than one per event), deferred to a follow-up dev spec.
- **Migrating off git as the storage layer** (e.g., SQLite, hosted store). The brief calls this out explicitly. Git remains the storage backend.
- **The V2 promotion specs** (#6 critique V2 → live, #7 timeline V2). Those are separate downstream specs.
- **GitHub Pages CI changes.** `.github/workflows/dashboard.yml` continues to invoke the renderer; the renderer's data source change is internal.

---

## 6. Test plan

- [ ] **Backfill produces a complete state file.** After `build_queue_state.py` runs against the current repo, `dashboard/queue-state.json` contains an entry for every `specs/*.md` file (verify by diffing the keyset). Every entry has `status`, and every entry with frontmatter `deployed_at` has it copied verbatim. Test: `tests/spec_lifecycle/test_build_queue_state.py` with a fixture repo of 5–10 specs covering each status.
- [ ] **`queue_state.update_state` is conflict-safe.** Simulate a parallel write by writing one update locally, advancing `origin/main` with a different update, then calling `update_state` — it must detect the non-fast-forward and retry, merging both updates. Test: `tests/spec_lifecycle/test_queue_state_conflict.py`.
- [ ] **`append_event_to_state` is monotonic.** Calling `append_event_to_state` with an `events` array shorter than the on-disk one raises rather than clobbers. Test: same file as above.
- [ ] **`archive_old_handoffs` keeps the most-recent N.** Given a fixture of 25 dated handoff filenames, `cap=20` leaves exactly 20 in `handoffs/` and moves 5 to `handoffs/archive/YYYY-MM/`. Test: `tests/spec_lifecycle/test_archive_handoffs.py`.
- [ ] **`cleanup_superseded_checkpoints` matches both predicates.** Given a fixture with three handoffs — one `kind: in-spec-checkpoint, spec: "0202"`, one `kind: in-spec-checkpoint, spec: "0201"`, one `kind: post-deploy, spec: "0202"` — calling `cleanup_superseded_checkpoints(dir, '0202')` deletes exactly the first file. Test: same file.
- [ ] **Renderer reads from queue-state.json when present.** A fixture renderer run with a populated state file produces a dashboard whose `Spec 0152` row shows the state-file's `status`/`deployed_at`, even if the spec frontmatter has stale values. Test: `tests/spec_lifecycle/test_render_dashboard_reads_state.py`.
- [ ] **Renderer falls back to frontmatter for specs without state entries.** A fixture with one spec missing from queue-state.json still renders that spec's status from its frontmatter. Test: same file.
- [ ] **One-time backfill is idempotent.** Run `build_queue_state.py` twice in succession; the second run is a no-op (no file changes, exits 0 with a "nothing to do" message). Test: `tests/spec_lifecycle/test_build_queue_state.py`.
- [ ] **Post-deploy commit message captures all three jobs.** After `/dev-next` step 24a runs, the commit message matches `r"spec\(\d+\): deployed v[\d.]+ \+ handoff \+ archive \(\d+ moved, \d+ checkpoints cleaned\)"`. Verified manually as part of the implementation cycle's own deploy; documented in the handoff.
- [ ] **Handoff backfill lands ~100 archived files.** After the one-time backfill commits, `ls handoffs/ | wc -l` returns exactly 20, and `find handoffs/archive -name '*.md' | wc -l` returns 100 (current 120 — kept 20). Verified manually as part of the implementation cycle's pre-merge diff; documented in the handoff.

---

## 7. Risks

- **Renderer must work during the transition window.** Between the moment the backfill script writes queue-state.json and the moment `/dev-next` skill bodies start writing to it, there's a small interval where both sources exist. *Mitigation:* the renderer's per-row fallback (§2.5) reads from queue-state.json when an entry exists and falls back to frontmatter when it doesn't. The backfill creates entries for *every* spec, so the fallback is exercised only for hypothetical future specs that bypass the new flow — a defensive safety net, not the hot path.
- **`update_state` race between concurrent skill sessions.** Two `claude -p "/dev-next"` instances (or the queue-control session + an author worktree's `/spec-queue`) writing simultaneously could land conflicting updates. *Mitigation:* `update_state` uses the same `GIT_INDEX_FILE` + non-fast-forward retry pattern as `push_event_to_main` ([scripts/spec_lifecycle/append_event.py:124](scripts/spec_lifecycle/append_event.py:124)). The file is small (~100 KB), so re-reading + re-applying the local diff is cheap. Cap of 3 retries surfaces hard conflicts to the caller.
- **Wrong handoff deleted by checkpoint cleanup.** A bad predicate could remove a post-deploy handoff instead of a checkpoint. *Mitigation:* the matcher requires *both* `kind: in-spec-checkpoint` AND `spec: "NNNN"` to fire. Test fixture in §6 explicitly covers the three-way discrimination (matching-checkpoint, mismatched-spec checkpoint, post-deploy). Deletion logs the path to stderr for audit.
- **Archive script runs against an actively-edited handoff.** If a user has `handoffs/2026-05-20-foo.md` open in an editor while archive runs, the file moves out from under them. *Mitigation:* archive happens only at `/dev-next` step 24a (post-deploy) — a controlled point with no concurrent human editing expected. The cycle is also serial (one `/dev-next` at a time per `feedback_pause_between_specs`), so there's no second writer.
- **Backfill misses fields the brief didn't anticipate.** If an older spec carries a frontmatter field that's needed at render time but isn't in §2.6's copy list (e.g., a deprecated `source_session` or `promoted_from_draft`), the renderer's fallback covers it — these fields stay in frontmatter and aren't touched by this spec.
- **L-complexity overshoot.** The spec touches ~10 files and introduces 3 new scripts; the cycle may need the L-spec checkpoint cadence (spec 0186) to stay green inside the 30-minute checkpoint window. *Mitigation:* the implementation order is natural — backfill last (§2.6 depends on §2.1 + §2.3 + §2.4 being in place), with §2.1 (queue-state module), §2.3 (archive script), §2.4 (events consolidation), §2.5 (renderer) as independent subsections that each end at a green test boundary, making checkpoint halts clean.
