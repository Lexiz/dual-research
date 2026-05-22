---
kind: dev
spec: "0186"
slug: queue-drain-session-isolation-and-l-spec-checkpointing
title: Queue-drain session isolation and L-spec checkpointing
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.32.0
status: deployed
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: "2026-05-22T22:56:31Z"
merged_at: "2026-05-22T23:06:43Z"
deployed_at: "2026-05-22T23:15:02Z"
pr: "https://github.com/Lexiz/dual-research/pull/196"
handover: "handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md"
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0186 — Queue-drain session isolation and L-spec checkpointing

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds new infra to `/dev-queue-run` (supervisor model) + `/dev-next` (in-spec checkpointing). Backwards-compatible with single-spec invocation.
> **Evidence:** Live failure on 2026-05-23 drain attempt — agent halted before §2.1 of spec 0173 with 13 queued specs ahead because it could see context burning. Branch `spec/0173-...` was cut, frontmatter flipped to `in_progress`, `implementing_started` event emitted, then halt.

---

## 1. Context

`/dev-queue-run` drains the entire dual-research queue in **one** Claude Code session. The skill body explicitly calls this out: "run `/dev-next`'s full body **inline** — do NOT recurse into `/dev-next`; the body is duplicated by reference" (`~/.claude/skills/dev-queue-run/SKILL.md:43`). That inline shape was fine when the queue held a couple of S specs. With 14 specs queued — including L-complexity entries like 0173 ("largest restructure" called out, 11 §2.N subsections) — a single session accumulates context across pre-flight reads, DS SPEC reads, code reads, test output, deploy logs, and handoff writes. Later specs in the loop run under a compacted/degraded window even when the early specs landed cleanly.

The 2026-05-23 drain attempt is the proof: the agent halted on `/dev-queue-run` after pre-flight, branching, and partial reading for §2.1 of 0173 alone, citing visible context burn with 13 specs still ahead. Nothing destructive happened — branch is recoverable from the live state — but the failure mode (forced bundling of work-output into a single context) is structural, not a one-off.

A secondary, related failure mode: even one L-complexity spec may not fit in a single session. The drain failure exposes this — 0173 alone, in a fresh session, may still need to span sessions to ship faithfully.

## 2. Proposed change

Two layers. They share infrastructure (the headless invocation contract and an extended handoff schema) but solve distinct problems.

### 2.1 Layer 1 — Supervisor model for `/dev-queue-run`

Refactor `~/.claude/skills/dev-queue-run/SKILL.md` so the loop **does not** inline `/dev-next`'s body. Instead, for each queued spec the skill spawns a fresh Claude Code session via headless `claude` invocation, waits for it to complete, then proceeds.

Per-iteration contract (one queued spec → one headless invocation):

```bash
mkdir -p runs/queue-drain
LOG="runs/queue-drain/$(date -u +%Y-%m-%dT%H-%M-%SZ)-spec-NNNN.log"
claude -p "/dev-next" \
  --cwd /Users/alexlisitzky/dual-research \
  > "$LOG" 2>&1
RC=$?
```

- **Exit code semantics.** `RC == 0` → success, advance loop. `RC != 0` → halt the supervisor; the failed spec's frontmatter is already at `status: failed` (set inside the headless `/dev-next` run via existing step-failure logic) so the next `/dev-queue-run` refuses to start until the user resolves it. Matches existing halt-on-failure shape at `~/.claude/skills/dev-queue-run/SKILL.md:58`.
- **Output capture.** Per-iteration log file under `runs/queue-drain/<timestamp>-spec-NNNN.log`. The supervisor tails the last 50 lines on failure and surfaces them inline so the user sees what broke without opening the file. On success, the supervisor surfaces only the PR URL + cycle time (one line per spec).
- **Cross-session bridge.** The existing handoff file (written at `~/.claude/skills/dev-next/SKILL.md:184`) is the bridge — `/dev-next` already reads the latest handoff at step 9. No new bridging file needed for the inter-spec case.
- **Between-iteration re-read.** The supervisor re-reads `current_queue('specs')` from disk between iterations (`scripts/spec_lifecycle/pick_next_number.py:46`). This already happens inline today — moving it to between subprocess calls is a one-line port.
- **Single greenlight preserved.** The pre-flight confirmation at `~/.claude/skills/dev-queue-run/SKILL.md:28` runs once in the supervisor; the per-spec confirmation in `/dev-next` is bypassed when invoked headless via the same mechanism used today (the existing "Suppress the per-spec greenlight" rule at `~/.claude/skills/dev-queue-run/SKILL.md:54` extends — pass an env var or `-p` arg that `/dev-next` already recognizes).

### 2.2 Layer 2 — L-spec checkpoint handoffs in `/dev-next`

Extend `~/.claude/skills/dev-next/SKILL.md` so that for specs with `complexity: L`, the implementation phase (step 15) writes an **in-spec checkpoint handoff** after each completed top-level `## 2.N` subsection, then has a budget check. If the session's accumulated context is past a threshold, `/dev-next` halts cleanly with `status: in_progress` preserved and a checkpoint handoff written. The next `/dev-next` invocation (spawned by the supervisor) picks up from that checkpoint.

Checkpoint handoff format — extension of today's handoff schema at `~/.claude/skills/dev-next/SKILL.md:184`:

```yaml
---
spec: "NNNN"
date: 2026-MM-DD
kind: in-spec-checkpoint           # new value, distinct from today's implicit "post-deploy"
branch: spec/NNNN-<slug>
branch_sha: <sha>
completed_subsections: ["2.1", "2.2", "2.3"]
next_subsection: "2.4"
tests_status: green | red | not-yet-run
version_bumped: true | false
changelog_written: true | false
---
```

Body section additions:
- `## State at checkpoint` — what was implemented, what was deferred *within this checkpoint cycle* (distinct from spec-level deferrals at `~/.claude/skills/dev-next/SKILL.md:114`).
- `## Resume instructions` — explicit pointer to `next_subsection` and any in-flight test or DS reads the resuming session should redo.

Resume path in `/dev-next` step 9 (handoff read):
- Today: reads latest handoff for inter-spec context.
- New: if latest handoff has `kind: in-spec-checkpoint` AND `spec` matches the spec currently being picked up (i.e. that spec's frontmatter still says `in_progress`), enter **resume mode** — skip steps 12–14 (already done last cycle), jump to step 15 starting at `next_subsection`, and proceed.

L-spec checkpoint cadence: after each top-level `## 2.N` is fully implemented + tests for that subsection are green (where applicable). Not after every file edit, not after every test run — too noisy. Per-`## 2.N` is the natural seam: each subsection in an L spec already represents a coherent chunk.

L-spec trigger: any spec with `complexity: L` in frontmatter. M and S specs continue to run end-to-end in one session (matches the working state today).

### 2.3 What does NOT change

- `/dev-next` invoked directly (single-spec, interactive) still works exactly as today. The checkpoint logic is dormant unless the spec is `complexity: L`.
- The handoff file location, naming convention (`YYYY-MM-DD-spec-NNNN-<slug>.md`), and reader code stay backwards-compatible. The new `kind:` field is additive.
- The dashboard renderer (`scripts/spec_lifecycle/render_dashboard.py`, called out in `CLAUDE.md`) does not need updates for this spec — events emitted are the same set; the new handoff kind is invisible to the renderer.

## 3. UX / Behavior

The user's experience changes as follows:

**Today (drain):**
1. User runs `/dev-queue-run` in the queue session.
2. One greenlight at start.
3. Single session does all N specs inline. Long-tail specs degrade under context pressure.

**After this spec (drain):**
1. User runs `/dev-queue-run` in the queue session (same invocation).
2. One greenlight at start (same).
3. Supervisor spawns spec 1 in a fresh `claude -p` session. Output tailed to `runs/queue-drain/`. Supervisor waits.
4. On success, supervisor surfaces PR URL + cycle time; moves to spec 2 in another fresh session.
5. On failure, supervisor surfaces the failure and halts.

**Today (single L spec):** the implementer ships or halts. No mid-spec resume.

**After this spec (single L spec):** the implementer ships in one session if possible. If context pressure crosses the threshold mid-implementation, a checkpoint handoff is written and the session halts cleanly. The next `/dev-next` (or supervisor iteration) resumes from `next_subsection`.

User-visible artifacts:
- New: per-iteration log files under `runs/queue-drain/`.
- New: checkpoint handoffs in `handoffs/` with `kind: in-spec-checkpoint`.
- Unchanged: PR URLs, dashboard events, deploy URLs.

## 4. Data / Schema deltas

No DB schema changes. Two file-format additions, both additive:

- Handoff frontmatter gains optional fields: `kind`, `branch`, `branch_sha`, `completed_subsections`, `next_subsection`, `tests_status`, `version_bumped`, `changelog_written`. Pre-existing handoffs (no `kind:` field) are treated as `kind: post-deploy` by readers.
- New directory `runs/queue-drain/` for per-iteration logs (gitignored — these are local-session artifacts).

## 5. Out of scope

- **PR-review skill / fix-loop.** Discussed in the same conversation that motivated this spec but is a separate concern. Its own spec will follow.
- **Resume after supervisor failure.** If the supervisor crashes mid-queue, the user re-runs `/dev-queue-run` and the loop picks up from whichever spec is next at `status: queued`. No automatic crash recovery or state restoration.
- **Context-pressure measurement.** The L-spec checkpoint trigger uses a simple heuristic: "after each completed `## 2.N`, decide whether to halt based on session age or a coarse signal." No new token-counter infra. If the heuristic turns out to be wrong, refine in a follow-up spec.
- **Parallel-spec execution.** The supervisor remains strictly sequential. Parallel drain is a separate (much larger) concern.
- **Inter-spec drift reconciliation in supervisor.** Each fresh `/dev-next` invocation already runs reconcile at step 9–11 — the supervisor inherits that for free, no extra work.
- **`/dev-next` invoked manually mid-checkpoint.** If a user manually invokes `/dev-next` while a checkpoint handoff exists, the resume logic activates. There is no separate "force start fresh" path in this spec.

## 6. Test plan

- [ ] **Supervisor end-to-end:** create a synthetic 2-spec test queue (both S complexity, trivial bodies). Run `/dev-queue-run`. Both specs ship in separate sessions. Assert: two distinct log files under `runs/queue-drain/`, two distinct PR URLs, two distinct handoff files, both specs reach `status: deployed`.
- [ ] **Supervisor halts on failure:** synthetic queue where spec 2 has an intentional test failure. Run `/dev-queue-run`. Assert: spec 1 ships green; spec 2 lands at `status: failed`; supervisor halts; spec 3 (if added) is not touched.
- [ ] **L-spec checkpoint round-trip:** synthetic L spec with 3 `## 2.N` subsections. Force checkpoint after `## 2.1`. Spawn a second `/dev-next` invocation. Assert: it reads the checkpoint handoff, enters resume mode, skips re-branching, starts at `## 2.2`, finishes through `## 2.3`, ships normally.
- [ ] **Checkpoint handoff schema:** `parse_handoff_file` (existing parser cited at `~/.claude/skills/dev-next/SKILL.md:215`) reads the new fields without crashing on pre-existing handoffs missing them.
- [ ] **Single-spec interactive `/dev-next` unchanged:** run `/dev-next` directly on a fresh S spec, end-to-end. Assert: no checkpoint handoff written, no new behavior triggered, output identical to pre-spec-0186 shape.
- [ ] **Validator runs clean:** `uv run pytest tests/ -q` for any new helpers added (e.g. handoff-kind classifier, supervisor argument builder).

## 7. Risks

- **Headless `claude -p` runtime drift.** If the CLI's headless mode changes semantics (arg shape, exit-code conventions, output capture), the supervisor breaks. *Mitigation:* keep the invocation contract isolated in one helper in the supervisor; pin to the documented `-p` shape; the spec writes a minimal helper that can be patched in one place.
- **L-spec checkpoint heuristic too aggressive or too lax.** Cadence per `## 2.N` may be too coarse for the largest specs (one subsection might itself exhaust a session) or too fine for medium-L specs. *Mitigation:* ship with the per-subsection trigger; if real drains show the heuristic mis-firing, refine in a follow-up. The handoff format is general enough to support finer cadences later without re-spec.
- **Resume-mode misreads checkpoint vs post-deploy handoff.** If `/dev-next` step 9 picks up a checkpoint handoff when it should pick up a post-deploy one, the implementer skips work. *Mitigation:* the `spec` field in the checkpoint handoff frontmatter is the disambiguator — resume mode only activates when checkpoint `spec` matches the spec currently being picked up AND that spec's status is `in_progress`. Anything else falls through to today's behavior.
- **Per-iteration log files accumulate.** `runs/queue-drain/` grows unbounded over time. *Mitigation:* gitignored from the start; user can `rm -rf runs/queue-drain/` whenever. If this becomes annoying, a follow-up spec can add a retention policy.
- **Session-title stamping inside headless mode.** The existing stamp-session-title hook fires per session. Each headless iteration becomes its own session with its own title. *Acceptance:* this is correct — each session gets a distinct title showing which spec it's working on, which is more informative than the single drain-session title is today.
