---
kind: dev
spec: "0152"
slug: spec-lifecycle-system-v1
title: Spec lifecycle system v1 — typed drafts, dev queue, dashboard, session naming
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.17.0
status: deployed
queue_position: 0
depends_on: []
complexity: L
created: 2026-05-22
queued_at: 2026-05-22T00:00:00Z
started_at: 2026-05-22T00:00:00Z
merged_at: "2026-05-22T10:50:17Z"
deployed_at: "2026-05-22T10:50:17Z"
pr: "https://github.com/Lexiz/dual-research/pull/175"
handover: "handoffs/2026-05-22-spec-0152-spec-lifecycle-system-v1.md"
failure_step: ""
source_session: bootstrap-2026-05-22
promoted_from_draft: ""
---

# Spec 0152 — Spec lifecycle system v1: typed drafts, dev queue, dashboard, session naming

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — adds a new operational surface (drafts directory, dev queue, dashboard route on GH Pages, host-side skills + hooks). No breaking changes to the existing DR app or CLI. No schema changes to Supabase. Pre-1.0 model code paths untouched.
> **Evidence:** This spec self-bootstraps a system; no prior spec to cite. The design discussion that produced it is the conversation that authored this file. Replaces the ad-hoc spec workflow currently documented in `CONTRIBUTING.md` and the legacy `scripts/queue-autonomous/` + `src/dual_research/queue_v2/` infra (also deleted in this spec).

---

## 1. Context

The DR repo has had a spec-driven workflow since spec 0001 — `CONTRIBUTING.md` codifies the loop `spec → branch → implement → PR → admin squash-merge → next spec`. In practice, several patchwork systems accreted around that loop:

- A `scripts/queue-autonomous/` autonomous-mode runner with its own `policy.md`, `prompt.sh`, `capture-shots.py`.
- A `src/dual_research/queue_v2/` Python package (`cli.py`, `parse_spec.py`, `reason.py`, `implement.py`, `verify.py`, `pr.py`, `deploy.py`, `handover.py`, `timings.py`) with its own state machine.
- A `queue/state.json` + `queue/runs/<NNNN>/` directory tree carrying per-spec event logs, decisions, and screenshots.
- A `specs/_kickoff-prompts/` directory of hand-pasted kickoff prompts (0140 through 0147) for starting new sessions on each spec.
- A host-side `~/.claude/skills/prep-kickoff/` skill that generated kickoff prompts into `_kickoff-prompts/` files.

Each piece solved a real problem at the time it was built, but together they:

1. **Conflate spec authoring with spec execution.** Authoring sessions touch `git checkout`, branches accumulate before any code lands, and parallel ideation sessions risk colliding.
2. **Carry duplicate state.** The repo, `queue/state.json`, the run directory, and the spec frontmatter can all disagree about a spec's status.
3. **Treat every spec the same.** A bug, a refactor, and a new feature all flow through identical templates, even though the implementer needs different information for each.
4. **Have no monitoring surface.** Progress, throughput, and historical cycle time are invisible unless you read the repo file-by-file.
5. **Don't capture session identity.** Sessions in this repo all surface as `[DR-O]` or `[DR-X]` regardless of which spec they're driving.

This spec consolidates the workflow into a single coherent system and deletes the legacy infrastructure in the same PR. After it ships, the DR spec workflow has exactly one source of truth (spec frontmatter), four user-facing skills, one dashboard, and one session-naming format.

## 2. Proposed change

### 2.1 Workflow model

Three kinds of session interact with the system:

- **Authoring session.** Open-ended chat that ideates and ends in either a draft or a queued dev spec. Never touches branches. Lives in a dedicated worktree.
- **Queue-control session.** Long-lived. The user types "next" / "go" and the session drives one dev cycle end-to-end. Lives in the primary checkout. Switches branches during a cycle.
- **(Implicit) Dev execution.** Happens inside the queue-control session's turn. Not a separate process.

Authoring never creates branches. The queue session is the only place branches exist. This is the invariant that makes parallel ideation safe.

### 2.2 Four user-facing skills

Installed at `~/.claude/skills/<name>/SKILL.md`. Each is invokable via slash command and via natural-language triggers documented in a memory file.

| Skill | Slash | NL triggers (non-exhaustive) | Purpose |
|---|---|---|---|
| `spec-draft` | `/spec-draft` | "save this as a draft", "park this idea", "draft spec from this" | Summarises current thread into `specs/drafts/draft-NNN-<slug>.md` with `kind: draft`. No dev-number reservation. No branch. Saves immediately (drafts are scratch). |
| `spec-queue` | `/spec-queue` | "queue this for dev", "make the dev spec", "this is ready to ship" | Classifies the spec type (new-feature/bug/refactoring/test/breaking), populates the matching template, previews in chat, user confirms, commits to main as `specs/NNNN-<slug>.md` with `status: queued`. No branch. |
| `spec-promote` | `/spec-promote <draft-id>` | "promote draft 008 to dev", "move this draft into the queue" | Reads `specs/drafts/draft-NNN-…md`, walks the user through any gaps (unresolved questions especially), runs the dev-spec validator, writes `specs/NNNN-<slug>.md`, deletes the draft. |
| `dev-next` | `/dev-next` | "next", "go", "kick off the next one", "run the queue" | Pre-flight → reconcile → execute the full cycle → stop. Only valid in the queue-control session (refuses if invoked from the author worktree). |

### 2.3 Filesystem layout

All paths relative to `/Users/alexlisitzky/dual-research/` unless noted.

```
specs/
  _templates/
    new-feature.md
    bug.md
    refactoring.md
    test.md
    breaking.md
  drafts/
    README.md
    draft-001-summary-tab-v2.md       (parked from untracked specs/0152-…)
    draft-002-login-screen-v2.md       (parked from untracked specs/0153-…)
    draft-003-timeline-refresh.md      (placeholder over prototypes/timeline-iteration/)
  0152-spec-lifecycle-system-v1.md    (this spec)
  0149-…, 0150-…, 0151-…             (frontmatter backfilled to new format)
  0001-…0148-…                        (untouched; renderer tolerates old format)
handoffs/
  2026-05-22-spec-0151-….md          (frontmatter added)
  2026-05-22-spec-0152-….md          (written at deploy time)
dashboard/
  events/
    0152.jsonl                        (event sidecar for this spec)
  site/
    index.html                        (regenerated by GH Action; published to gh-pages)
    style.css
    spec-NNNN.html (per spec)         (regenerated)
scripts/
  spec_lifecycle/
    __init__.py
    frontmatter.py                    (shared YAML I/O)
    validator.py                      (type-aware validation)
    pick_next_number.py               (atomic next dev spec number)
    pick_next_draft.py                (next draft id)
    reconcile.py                      (handoff drift detection)
    render_dashboard.py               (static HTML generator)
    append_event.py                   (skill writes call this)
.github/workflows/
  dashboard.yml                       (push-to-main → render → publish gh-pages)
prototypes/
  timeline-iteration/                 (committed alongside draft-003)
```

Deleted in this PR: `scripts/queue-autonomous/`, `queue/`, `src/dual_research/queue_v2/`, `specs/_kickoff-prompts/`.

### 2.4 Frontmatter contract

**Dev spec (`specs/NNNN-<slug>.md`):**

```yaml
kind: dev
spec: 0156                             # zero-padded 4 digits
slug: <kebab>
title: <imperative phrase>
type: new-feature | bug | refactoring | test | breaking
label: new-feature | bug | refactoring | test | breaking   # kept for CONTRIBUTING.md compatibility; mirrors type
version_bump: MAJOR | MINOR | PATCH
target_version: X.Y.Z | TBD
status: queued | in_progress | merged | deployed | failed | cancelled
queue_position: <int, meaningful only while queued; 0 once started>
depends_on: [0152, 0154]               # other specs that must merge first
complexity: S | M | L
created: YYYY-MM-DD
queued_at: <ISO8601 or "">
started_at: <ISO8601 or "">
merged_at: <ISO8601 or "">
deployed_at: <ISO8601 or "">
pr: <URL or "">
handover: <path or "">
failure_step: <name or "">
source_session: <session id or label>
promoted_from_draft: <draft id or "">
```

**Draft (`specs/drafts/draft-NNN-<slug>.md`):**

```yaml
kind: draft
draft_id: NNN                          # zero-padded 3 digits
slug: <kebab>
title: <imperative phrase>
type: <guess or "unclassified">        # informational; finalized at promotion
status: draft
created: YYYY-MM-DD
source_session: <session id or label>
```

**Handoff (`handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md`):**

```yaml
spec: NNNN
date: YYYY-MM-DD
version: X.Y.Z
pr: <URL>
```

### 2.5 Type-specific templates

Each template lives at `specs/_templates/<type>.md`. All templates share the header preamble + frontmatter shape above. Bodies differ.

**`new-feature.md`** required sections: Context · Proposed change · Out of scope · Test plan · Risks. Optional: UX/Behavior, Data/Schema.

**`bug.md`** required sections: Reproduction (Environment, Steps, Expected, Actual, Evidence) · Root cause hypothesis (with file:line citations) · Fix · Regression-prevention test (must describe a test that fails before the fix, passes after) · Blast radius · Out of scope · Risks.

**`refactoring.md`** required sections: Current state (cited) · Target state · Stepwise migration (each step independently revertable) · Behavior preservation (which existing tests cover what, or parity tests added) · Out of scope (must explicitly disclaim new features) · Risks.

**`test.md`** required sections: Coverage gap · Test approach · What it would catch · Risks.

**`breaking.md`** inherits new-feature, adds: Compatibility break · Migration plan · Rollback plan.

**No "Open questions" section in any dev-spec template.** Questions are queue blockers — resolve them before the spec enters the queue. Drafts may carry "Unresolved questions"; promotion walks through them.

### 2.6 Validator contract

`scripts/spec_lifecycle/validator.py` exposes:

```python
def validate_dev_spec(path: Path) -> ValidationResult: ...
def validate_draft(path: Path) -> ValidationResult: ...
```

Checks for dev specs:

- Frontmatter has all required keys for `kind: dev`.
- `status` is one of the enum values.
- `type` matches the template body sections present.
- ≥ 2 file:line citations anywhere in the body (matched by regex `[\w\-/.]+\.(py|jsx|tsx|css|md):\d+`).
- A "Test plan" section (for types where it's required) with ≥ 2 lines matching `^- \[[ x]\]`.
- No `[TBD]` markers in the body.
- No "Open questions" section.
- Bodies of "?" sentences (heuristic: lines ending with `?`) flagged for human review (does not fail validation; surfaces as warnings).
- Type-specific checks: bug specs must have `Expected:` and `Actual:` lines and a Regression-prevention test description; refactoring specs must have an explicit "this spec does not add new features" line in Out of scope.

`ValidationResult` carries `ok: bool`, `errors: list[str]`, `warnings: list[str]`.

### 2.7 Dev cycle (`/dev-next`)

Pre-flight (on `main`, primary checkout — refuses to run from author worktree):

1. `git fetch`, confirm clean working tree, on `main`, up to date with origin.
2. No open `spec/*` PRs (`gh pr list --head 'spec/*' --state open` empty).
3. No spec on disk with `status: in_progress`.
4. Pick spec with lowest `queue_position` where `status: queued`. Surface one-line summary. **One confirmation point.** User says go.

Reconcile (on `main`):

5. Read most recent file in `handoffs/`. Walk the queued spec for any file:line citations whose path no longer exists or whose line number is past the file's current length. If drift is found:
   - **Mechanical drift** (file moved, line number shifted): propose patches, show diff, user accepts → patched in single commit on main. Proceed.
   - **Semantic drift** (file deleted, function removed, contract changed): halt. Set `status: failed, failure_step: reconcile`. Print the conflict to chat. Exit.

Execute:

6. Update spec frontmatter `status: in_progress, started_at: <now>`. Append event. Commit + push.
7. `git checkout -b spec/NNNN-<slug>`.
8. Implement per spec body. Tests written/updated.
9. Full pytest suite. Red → halt with `failure_step: tests`. Green → continue.
10. Push branch. `gh pr create` with body containing summary + test plan + link to spec.
11. Update frontmatter on branch: `status: merged, pr: <url>, merged_at: <now>`. Commit + push.
12. `gh pr merge --admin --squash --delete-branch`.
13. `git checkout main && git pull`.
14. `fly deploy`. Failure → `failure_step: deploy`. Smoke any anchor referenced in spec.
15. Write `handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md` with frontmatter.
16. Update spec frontmatter: `status: deployed, deployed_at: <now>, handover: <path>`. Re-rank remaining `status: queued` specs (decrement `queue_position` by 1). Flush buffered events to the sidecar. Single commit + push.
17. **Stop.** Print one-line status to chat. Do not auto-start the next spec. Pause-between-specs rule applies.

If any step fails: frontmatter goes to `status: failed, failure_step: <name>`, the next `/dev-next` invocation refuses to start until the user manually resolves (edits the failed spec's frontmatter back to `queued` or `cancelled`).

### 2.8 Event sidecar

Each spec has `dashboard/events/<spec-or-draft-id>.jsonl`, append-only:

```json
{"ts": "2026-05-22T15:42:00Z", "step": "queued", "data": {}}
{"ts": "2026-05-22T16:10:00Z", "step": "reconcile_start", "data": {}}
{"ts": "2026-05-22T16:11:00Z", "step": "in_progress", "data": {}}
{"ts": "2026-05-22T17:23:00Z", "step": "tests_green", "data": {"count": 1463}}
{"ts": "2026-05-22T17:27:00Z", "step": "merged", "data": {"pr": "..."}}
{"ts": "2026-05-22T17:31:00Z", "step": "deployed", "data": {"version": "1.17.0"}}
```

Events generated on `main` get committed immediately. Events generated on the feature branch buffer locally and are committed as a single line-batch at step 16 when the cycle is back on main. The dashboard regenerates on push to main, so it always sees consistent batched updates.

`append_event.py` exposes `append_event(spec_id: str, step: str, data: dict | None = None)`.

### 2.9 Dashboard

`scripts/spec_lifecycle/render_dashboard.py` reads every `specs/NNNN-*.md`, every `specs/drafts/draft-NNN-*.md`, every `handoffs/*.md`, and every `dashboard/events/*.jsonl`. Renders static HTML to `dashboard/site/`.

Sections rendered:

- **In flight** card: spec with `status: in_progress`, with elapsed time from `started_at` and current event step.
- **Queue**: specs with `status: queued`, ordered by `queue_position`, with ETA from rolling-average cycle time.
- **Recently shipped**: last 10 with `status: deployed`, with cycle time (`deployed_at - started_at`).
- **All specs**: sortable table with every spec.
- **Drafts**: separate tab listing every file in `specs/drafts/`.
- **Metrics**: average cycle time (rolling 10), throughput per week (last 4 weeks), % needing reconcile patches, failure count.

Per-spec page (`spec-NNNN.html`): frontmatter dump, event timeline (read from sidecar), links to spec source on GitHub, PR, handoff.

Workflow (`.github/workflows/dashboard.yml`):

- Triggers on push to `main` when paths under `specs/`, `handoffs/`, or `dashboard/` change.
- Sets up Python, runs `python scripts/spec_lifecycle/render_dashboard.py --out dashboard/site/`.
- Publishes `dashboard/site/` to the `gh-pages` branch.
- GitHub Pages serves from `gh-pages` root.

Resulting URL: `https://lexiz.github.io/dual-research/`.

### 2.10 Session naming integration

Title format (DR sessions only): `[DR · <context> · <O|X>] <body>`.

Contexts:

- `scratch` — DR session, no spec touched.
- `draft-NNN` — created or working draft NNN.
- `NNNN` — created or working dev spec NNNN.
- `queue` — queue-control session, idle.
- `queue · NNNN in flight` — queue-control session mid-cycle on spec NNNN.

Skills set the title decisively when they run:

- `/spec-draft` → `[DR · draft-NNN · O] <slug>`.
- `/spec-queue` → `[DR · NNNN · O] <slug>`.
- `/spec-promote` → rewrites current session to `[DR · NNNN · O] <slug>` (the dev number after promotion).
- `/dev-next` → on cycle start: `[DR · queue · NNNN in flight · O]`. On cycle end: `[DR · queue · idle · O]`. On failure: `[DR · queue · NNNN failed · O]`.

`~/.claude/hooks/auto-prefix-session.py` is extended to:

- Recognize the new format via regex `^\[DR · ([a-z]+(?:-\d+)?|\d{4}|queue(?: · [\w\s]+)?) · (O|X)\]`.
- Leave spec-tagged titles alone (don't reclassify back to generic `[DR-O]`).
- Continue to handle other categories (`[PV]`, `[WoW]`, `[CK]`, `[SYS]`) unchanged.
- For `[DR · scratch · O]` sessions, every 5th UserPromptSubmit re-evaluates: if a spec ID is being referenced or a spec was just created, upgrade the title.

`~/.claude/hooks/cleanup-session-prefixes.py` is extended:

- The `list` command parses the new format into `{context, spec_id, kind}` fields.
- The `apply` command, for spec-tagged sessions, reads the spec's frontmatter at `/Users/alexlisitzky/dual-research/specs/NNNN-*.md` (or `drafts/draft-NNN-*.md`) and derives status: `deployed` or `cancelled` → `X`; otherwise → `O`. No LLM call needed for these.
- Non-spec sessions (`scratch`, plus other categories) continue to use the LLM classifier as today.

### 2.11 Author worktree

`/Users/alexlisitzky/dual-research-author/` — created via `git worktree add ~/dual-research-author main`. Pinned to `main`. All `/spec-*` skills run from there. `/dev-next` refuses to run from there.

The skills detect their worktree via `git rev-parse --show-toplevel` and check against a small policy: `/spec-*` requires the toplevel to be either `~/dual-research-author` or any worktree NOT named `~/dual-research`; `/dev-next` requires the toplevel to be exactly `~/dual-research`.

### 2.12 Memory updates (host side)

- Delete `~/.claude/skills/prep-kickoff/`.
- Delete `~/.claude/projects/-Users-alexlisitzky/memory/feedback_prep_kickoff_trigger.md`.
- Add four new memory entries for natural-language triggers (one per skill).
- Update the MEMORY.md index accordingly.

The retained memory entries (`feedback_pause_between_specs`, `feedback_handle_full_delivery`, `project_dual_research_repo`, `feedback_low_reversal_just_decide`, `feedback_no_handoff_unless_asked`, `feedback_secrets_pragmatic`) remain valid and are referenced from the skill SKILL.md descriptions where applicable.

## 3. UX / Behavior

### 3.1 Skill invocation flow

A typical authoring session ends with a single sentence from the user. The skill model recognises the intent from memory triggers and invokes the right skill, which then proceeds.

**`/spec-draft` flow:**
1. Reads the conversation.
2. Picks next `draft_id` by scanning `specs/drafts/` (atomic via filesystem create).
3. Writes the draft with `kind: draft` frontmatter and body distilled from the thread.
4. Commits + pushes to `main` (from the author worktree).
5. Stamps session title to `[DR · draft-NNN · O] <slug>`.
6. Reports: file path, draft id, and "ready to promote when you're sure" hint.

**`/spec-queue` flow:**
1. Reads the conversation.
2. Classifies the spec type with explicit reasoning shown to the user.
3. Allows user to override the type.
4. Picks next dev spec number (atomic via git push retry).
5. Populates the type-specific template from thread content.
6. Runs the validator. If any check fails, prints the gaps and asks the user to clarify before retrying.
7. Once the draft passes validation, previews the full spec in chat.
8. User confirms → commits + pushes.
9. Stamps session title to `[DR · NNNN · O] <slug>`.

**`/spec-promote <draft-id>` flow:**
1. Loads `specs/drafts/draft-<id>-*.md`.
2. If the draft has "Unresolved questions" section, walks through each, asks the user to resolve, folds resolutions into the spec body.
3. Asks the user to confirm the type (defaults to whatever the draft has, or unclassified).
4. Populates the type-specific template.
5. Validates. Same gate as `/spec-queue` — refuses to promote until clean.
6. Previews. User confirms.
7. Writes the new dev spec. Deletes the draft. Commits + pushes (one commit).
8. Stamps session title.

**`/dev-next` flow:** described in §2.7.

### 3.2 Dashboard interaction

- User opens `https://lexiz.github.io/dual-research/` in a browser tab. Bookmark it.
- After any `main` push, the GH Action runs (~30s); refresh the page to see updates.
- Per-spec pages reachable by clicking the spec row in any table.
- No authentication needed (public repo); fine because nothing sensitive is on the dashboard.

## 4. Out of scope

This spec deliberately does NOT:

- **Implement parallel dev cycles.** The data model is parallel-ready (multiple `status: in_progress` is structurally fine; branch names are unique), but the pre-flight check enforces serial execution. Lifting it to N concurrent specs is a future spec.
- **Add a `/spec-reorder` or `/spec-cancel` skill.** For v1, queue reordering and cancellation are done by hand-editing frontmatter. If these become frequent, future specs add skills.
- **Migrate the entire spec history to new frontmatter.** Only the most recent three specs (0149, 0150, 0151) are backfilled; older specs render with whatever fields they have and the dashboard tolerates missing fields. A future spec can do the full backfill if desired.
- **Authenticate the dashboard.** Public repo, public dashboard. Not for sensitive data.
- **Replace `CONTRIBUTING.md` wholesale.** It's updated to reference the new workflow but the existing labelling + version-bump + admin-merge sections stay as-is.
- **Touch the DR app (`src/dual_research/`) for any reason other than removing `queue_v2/`.** The Python package, FastAPI server, UI, orchestrator, and CLI are not modified.
- **Wire branch protection.** CONTRIBUTING.md already states it's discipline, not enforcement. Unchanged here.
- **Build a desktop notification on cycle completion.** Possible future addition; not in this spec.

## 5. Test plan

- [ ] `tests/test_spec_lifecycle/test_frontmatter.py` — round-trip parse + write for dev spec, draft, handoff frontmatter shapes; preserves field order; handles missing fields gracefully.
- [ ] `tests/test_spec_lifecycle/test_validator.py` — for each type (new-feature, bug, refactoring, test, breaking): valid spec passes; missing required section fails; insufficient citations fails; missing test-plan checkboxes fails; `[TBD]` markers fail; "Open questions" section fails; bug spec missing Expected/Actual fails; refactoring spec missing "no new features" disclaimer in Out of scope fails.
- [ ] `tests/test_spec_lifecycle/test_pick_next_number.py` — given a fixture specs/ directory, returns next zero-padded 4-digit number; skips drafts/; raises on disk if the next slot already exists (race).
- [ ] `tests/test_spec_lifecycle/test_render_dashboard.py` — given a fixture repo state, renders index.html containing all expected sections (in-flight, queue, deployed, drafts, metrics); per-spec page lists frontmatter and events.
- [ ] `tests/test_spec_lifecycle/test_reconcile.py` — given a spec citing a file path, returns no-drift when path exists; mechanical-drift when path moved; semantic-drift when file deleted.
- [ ] Manual: render dashboard locally with `python scripts/spec_lifecycle/render_dashboard.py --out /tmp/dr-dash`. Confirm 0152 appears as in_progress (during this spec's own ship). Confirm draft-001/002/003 appear in drafts.
- [ ] Manual: after deploy, open `https://lexiz.github.io/dual-research/` and confirm dashboard is live, shows 0152 deployed.
- [ ] Manual: in a fresh author session, invoke `/spec-promote 001`. Confirm draft-001 becomes `specs/0153-summary-tab-v2.md` with `status: queued, queue_position: 1`. Confirm `specs/drafts/draft-001-…md` is gone.
- [ ] Manual: confirm session title in author session is now `[DR · 0153 · O] summary-tab-v2`.
- [ ] Manual: invoke `/spec-promote 003`. Confirm validator refuses (draft is too thin) and surfaces actionable gaps.
- [ ] `uv run pytest tests/ -q` full suite passes.

## 6. Risks

- **Bootstrap meta-risk: shipping the system means manually following a workflow the system is supposed to enforce.** Mitigation: This spec is the only one that ships outside the system; spec 0153 onwards uses `/dev-next`. The validator is run by hand on this spec before PR.
- **GitHub Pages publishing latency.** First push to `gh-pages` may take 5–10 minutes for Pages to come online; subsequent updates are ~30s. Mitigation: enable Pages as part of this PR's ship sequence so the first publish happens with the merge, before the user starts testing.
- **Hook race conditions.** The existing auto-prefix hook has sophisticated race-defeat for CCD's metadata rewrites. Extending it with new format recognition risks introducing regressions in the existing categories. Mitigation: regex is additive (new format takes precedence; old format unchanged); existing categories run through unchanged code paths.
- **`queue_v2/` deletion may break an import elsewhere.** Mitigation: grep for `queue_v2` imports before deletion; remove any references; run full test suite after deletion.
- **Frontmatter format collision with the legacy `label` field.** The new format includes both `type` and `label` (mirror of each other) for compatibility with CONTRIBUTING.md's existing version-bump table. If they ever diverge in a spec file, the validator flags it.
- **Author worktree drifts from main.** Mitigation: the `/spec-*` skills run `git pull --ff-only` from the author worktree before writing the spec file.
- **Atomic next-number race under parallel `/spec-queue`.** Two authoring sessions could try to claim the same NNNN within milliseconds. Mitigation: skill writes with `git push`; on push failure (someone else claimed it), pulls, recomputes next number, retries up to 3 times before surfacing to the user.

---

This spec ships as PR opened from `spec/0152-spec-lifecycle-system-v1` against `main`, admin-squash-merged, and followed by `fly deploy` + handoff write per §2.7 even though the cycle itself is run manually (bootstrap).
