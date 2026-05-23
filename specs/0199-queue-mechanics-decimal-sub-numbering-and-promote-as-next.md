---
kind: dev
spec: "0199"
slug: queue-mechanics-decimal-sub-numbering-and-promote-as-next
title: Queue mechanics — decimal sub-numbering, promote-as-next, drop queue_position
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.41.0
status: merged
depends_on: ["0198"]
complexity: M
created: 2026-05-23
queued_at: "2026-05-23T21:52:44Z"
started_at: "2026-05-23T22:24:42Z"
merged_at: "2026-05-23T22:43:20Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/227"
handover: ""
failure_step: ""
source_session: orchestrator-hardening-series-2026-05-23
promoted_from_draft: ""
---

# Spec 0199 — Queue mechanics: decimal sub-numbering, promote-as-next, drop queue_position

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0198 (validator/skill gates)
> **Bump:** MINOR — adds capability (decimal IDs, `/spec-next` skill, smarter deferral routing) and refactors queue internals to remove a state-sync axis; no existing spec is renumbered or broken.
> **Evidence:** Spec 2 of a 7-spec orchestrator-hardening series. Author: the user, 2026-05-23 orchestrator-audit conversation. Concrete pain: tightly-coupled follow-up specs land at the back of a 50-deep queue; manual queue-jumping breaks handoff continuity ("last shipped 0180 / next 0170" disagreement); ~8–9 status-bookkeeping commits per spec to `main` driven by `queue_position` re-ranking in [scripts/spec_lifecycle/pick_next_number.py:64](scripts/spec_lifecycle/pick_next_number.py:64) and [~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md) step 24.

---

## 1. Context

The dual-research orchestrator runs one queued dev spec at a time via `/dev-next`. The current queue model uses two coordinates per spec: a 4-digit integer ID baked into the filename (`specs/NNNN-<slug>.md`), and a `queue_position` integer in frontmatter. The ID is assigned by [scripts/spec_lifecycle/pick_next_number.py:16](scripts/spec_lifecycle/pick_next_number.py:16) (`next_dev_number`) as `max + 1`; the position is assigned by [scripts/spec_lifecycle/pick_next_number.py:64](scripts/spec_lifecycle/pick_next_number.py:64) (`next_queue_position`) the same way. Selection of "what runs next" reads `queue_position` ascending — see [scripts/spec_lifecycle/pick_next_number.py:46](scripts/spec_lifecycle/pick_next_number.py:46) (`current_queue`) and [scripts/spec_lifecycle/render_dashboard.py:2009](scripts/spec_lifecycle/render_dashboard.py:2009).

Three concrete failures follow:

1. **Tightly-coupled follow-up lands at the back of the queue.** When the `/dev-next` step 25.5 deferral subagent (see [~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md) step 25.5) creates a follow-up spec from a deferred item, that follow-up gets the next-available integer ID and the next-available `queue_position` — both append-only. A continuation of in-flight spec 0170 becomes `0245` at position 47. The continuation never runs in the same drain even though it's literally a `## 2.N` subsection that got dropped.

2. **Manual queue-jumping breaks handoff continuity.** The current escape hatch is to hand-edit `queue_position` on the desired spec to 1 and re-rank the rest. The session-title hook ([~/.claude/hooks/cleanup-session-prefixes.py:91](~/.claude/hooks/cleanup-session-prefixes.py:91)) tags a session as `[DR · NNNN · O]` from the assigned spec number; when the orchestrator runs `0245` after just shipping `0180`, the next session reads "last shipped: 0180" but the queue head is `0245` — humans (and the deferral subagent's "what's adjacent" heuristics) lose the thread.

3. **`queue_position` is a second source of truth.** Re-ranking on each `/dev-next` cycle ([~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md) step 24: "decrement `queue_position` by 1") rewrites every queued spec's frontmatter on `main`. This is one of the larger contributors to the ~8–9 status-bookkeeping commits per spec the user has called out. The position field encodes information already present in the spec ID once IDs themselves carry queue intent.

### Traceability table — source items → spec sections

Source: this spec's atomic items come from the user's brief in the 2026-05-23 orchestrator-audit conversation (no NOTES.md or ideation file). Per the gate added by spec 0198 §2.2, every named atomic item in the source must land in this spec body or be explicitly deferred to §5 with a follow-up target. The conversation called out four atomic items and three baked-in design decisions; this table enumerates all seven.

| Source item | Source ref | Spec section |
|---|---|---|
| Decimal sub-numbering | user's brief, "the fix — three parts", part 1 | §2.1 |
| Promote-as-next capability | user's brief, "the fix — three parts", part 2 | §2.2 |
| Smarter deferral decision in `/dev-next` | user's brief, "the fix — three parts", part 3 | §2.3 |
| Drop the separate `queue_position` frontmatter field | user's brief, "the fix — three parts" (closing) + "three baked-in design decisions" item 3 | §2.4 |
| One decimal level only — no `0170.1.1` | user's brief, "three baked-in design decisions" item 1 | §2.1 (cited as design constraint) |
| Default deferral decision = "can wait / next-integer" | user's brief, "three baked-in design decisions" item 2 | §2.3 (cited as default branch) |
| Cascade-rename children when promoting a parent with decimal siblings | user's reply to author's `AskUserQuestion`, 2026-05-23 ("not overengineered, simple and clean") | §2.2 (cascade behaviour) |

No items deferred. All seven ship in this spec.

### Verified against current code

- `next_dev_number` returns `f"{nxt:04d}"` ([scripts/spec_lifecycle/pick_next_number.py:27](scripts/spec_lifecycle/pick_next_number.py:27)). Confirmed.
- `SPEC_FILE_RE = re.compile(r"^(\d{4})-")` ([scripts/spec_lifecycle/pick_next_number.py:13](scripts/spec_lifecycle/pick_next_number.py:13)). Confirmed — strict 4-digit.
- `SpecRow.number` returns `self.path.stem[:4]` ([scripts/spec_lifecycle/render_dashboard.py:60](scripts/spec_lifecycle/render_dashboard.py:60)). Confirmed — would truncate `0170.1-slug` to `0170.`.
- Queue sort: `key=lambda s: int(s.fm.get("queue_position") or 999)` ([scripts/spec_lifecycle/render_dashboard.py:2009](scripts/spec_lifecycle/render_dashboard.py:2009)). Confirmed.
- Numeric sort blowup risk: `key=lambda s: int(s.number or "0")` ([scripts/spec_lifecycle/render_dashboard.py:1629](scripts/spec_lifecycle/render_dashboard.py:1629)) — `int("0170.1")` raises `ValueError`. Confirmed.
- Hook: `re.match(r"^(\d{4})$", ctx)` ([~/.claude/hooks/cleanup-session-prefixes.py:112](~/.claude/hooks/cleanup-session-prefixes.py:112)). Confirmed strict 4-digit; decimal IDs would silently fail context derivation.
- Queue currently empty (no `status: queued` specs) at author time — verified via `current_queue('specs')`. Dropping `queue_position` poses zero reorder risk to existing queued work.

---

## 2. Proposed change

### 2.1 — Decimal sub-numbering

**New canonical spec-ID grammar:** `NNNN` (four-digit zero-padded integer, the "parent") or `NNNN.M` (parent + single decimal, `M` is a positive integer). Filenames: `specs/NNNN-<slug>.md` or `specs/NNNN.M-<slug>.md`. Exactly one decimal level is permitted — a deferral from `0170.1` becomes `0170.2` (sibling), never `0170.1.1`. This is a hard constraint of the grammar, not a convention.

**Sort key:** parse a spec ID into `(parent: int, child: int)` where the child defaults to `0` for plain integers. Ordering: lexicographic on the tuple. So `0170 → (170, 0)`, `0170.1 → (170, 1)`, `0170.2 → (170, 2)`, `0171 → (171, 0)`. Sort everywhere uses this key, never `int(s.number)` or string sort.

**File: [scripts/spec_lifecycle/pick_next_number.py](scripts/spec_lifecycle/pick_next_number.py)**

- Replace `SPEC_FILE_RE = re.compile(r"^(\d{4})-")` ([line 13](scripts/spec_lifecycle/pick_next_number.py:13)) with `SPEC_ID_RE = re.compile(r"^(\d{4})(?:\.(\d+))?-")` capturing parent and optional child.
- Add `def parse_spec_id(name_or_id: str) -> tuple[int, int]` — accepts either a filename stem (`0170.1-slug`) or a bare ID (`0170.1`); returns `(170, 1)`. Returns `(N, 0)` for plain integers. Raises `ValueError` on malformed input.
- Add `def format_spec_id(parent: int, child: int = 0) -> str` — inverse: `(170, 0) → "0170"`, `(170, 1) → "0170.1"`. Used by the new allocators.
- Modify `next_dev_number(specs_dir)` to keep returning the next-integer ID (no behaviour change — this is the default deferral / spec-queue path).
- Add `def next_decimal_child(specs_dir, parent: str) -> str`. Scans for `{parent}.*-*.md`, returns `f"{parent}.{max_child+1}"`, or `f"{parent}.1"` if none exist. Raises `ValueError` if `parent` itself contains a decimal (one-level rule).
- Modify `current_queue(specs_dir)` ([line 46](scripts/spec_lifecycle/pick_next_number.py:46)) — sort by `parse_spec_id(filename)` instead of by `queue_position`. Drop the `queue_position` read entirely.
- Delete `next_queue_position(specs_dir)` ([line 64](scripts/spec_lifecycle/pick_next_number.py:64)). Callers go away in §2.4.

**File: [scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py)**

- Add a spec-ID format check on the filename: must match `^\d{4}(?:\.\d+)?-[a-z0-9-]+\.md$`. Reject deeper decimals (`0170.1.1-x.md`) with a clear error.
- Existing checks (citations, TBD markers, type-specific rules) are unchanged.

**File: [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py)**

- Replace `SpecRow.number` ([line 60](scripts/spec_lifecycle/render_dashboard.py:60)) with `parse_spec_id(self.path.stem)[*]`-aware accessors. Add `sort_key` property returning the `(parent, child)` tuple.
- Replace `key=lambda s: int(s.number or "0")` ([line 1629](scripts/spec_lifecycle/render_dashboard.py:1629)) with `key=lambda s: s.sort_key`.
- Per-spec page filenames stay as `spec-{number}.html` where `number` is the full ID with optional decimal (e.g. `spec-0170.1.html`). The dot is filesystem-safe and URL-safe.
- Mirror the change in the JS half of the file: `parseInt(b.number, 10)` ([line 3676](scripts/spec_lifecycle/render_dashboard.py:3676)) becomes a tuple-aware comparator. Provide a `parseSpecId(idStr)` helper near the top of the inlined script block and use it for all spec-ID comparisons.

**File: [~/.claude/hooks/cleanup-session-prefixes.py](~/.claude/hooks/cleanup-session-prefixes.py)**

- Widen the regex at [line 112](~/.claude/hooks/cleanup-session-prefixes.py:112): `re.match(r"^(\d{4}(?:\.\d+)?)$", ctx)` so `[DR · 0170.1 · O]` prefixes parse correctly. The capture group's value flows into `spec_id` and downstream `_derive_status_from_spec` already uses `glob(f"{spec_id}-*.md")` which handles decimals natively.
- Also widen the `re.search(r"(\d{4})", ctx)` at [line 117](~/.claude/hooks/cleanup-session-prefixes.py:117) used for `[DR · queue · NNNN in flight · O]` prefixes — same regex update.

This is the only edit outside the dual-research repo. It is an in-scope explicit step of the spec; the implementer documents the change in the handoff so future audits can reconstruct it.

### 2.2 — Promote-as-next via new `/spec-next <id>` skill

**Decision: new skill `~/.claude/skills/spec-next/SKILL.md`, not a flag on `/spec-promote`.** Justification:

- `/spec-promote` is semantically "draft → dev-queue" — walks unresolved-questions, restructures from the draft template into the dev-template, deletes the draft file. None of those steps apply when re-ID'ing an already-queued dev spec.
- Overloading would create two unrelated code paths sharing only the dev-number-picking step (`pick_next_number`). That's coincidence, not cohesion.
- `/spec-next <id>` is self-documenting at the call site and discoverable via skill listing.
- Both skills are tiny shells over the shared `pick_next_number` helpers; no duplication penalty.

**File: `~/.claude/skills/spec-next/SKILL.md`** (new)

Behaviour:

1. **Pre-flight:** must run from the author worktree (refuses from the queue worktree, mirroring `/spec-queue`). Validates the target ID argument matches a queued spec on `main` (`status: queued`, exists at `specs/<id>-*.md`).
2. **Resolve "what comes next":** read the in-flight spec (the single spec with `status: in_progress`, picked via the same predicate `/dev-next` step 5 uses). If no spec is in flight, **refuse** with a clear message — "promote as next" requires a parent to be next-of.
3. **Compute the new ID:** call `next_decimal_child('specs', in_flight_parent_id)`. The in-flight spec is necessarily a plain integer (per the one-level rule; a deferral subagent that produced a decimal in-flight is impossible — see §2.3 for why), so its ID *is* the parent.
4. **Cascade-rename children of the target.** Find every file matching `specs/{target_id}.*-*.md` (the target's decimal siblings) and rename each in tandem: target's `(parent_old).M` becomes new parent's `(parent_new).(K+M)` where `K` is the max existing child of the new parent before this operation. The whole batch lands in one atomic git commit. Rename mirrors apply to `dashboard/events/{old_id}.jsonl → dashboard/events/{new_id}.jsonl` and to any handoff sidecars for those IDs (there are typically none for queued specs, but the skill checks).
5. **Update `depends_on`** on the renamed spec(s) and on any other queued spec with `depends_on: ["<old_id>"]`. Search-and-replace, validator-checked.
6. **No frontmatter `queue_position`** to update — §2.4 drops the field.
7. **Commit + push** as one commit: `git commit -m "spec: promote-as-next <new_id> (was <old_id>)<+ N children>"`. Push to `main`. The commit is the user-facing artifact.
8. **Session-title stamp** is not done by `/spec-next` (it doesn't own a session in the sense `/spec-queue` does; the user is in their authoring session).
9. **Report:** the new ID(s), the in-flight parent, the depends_on edges that were rewritten.

**Refusal cases:** no spec in flight; target ID not queued; target ID itself is a decimal (cannot promote-as-next a child — promote its parent instead); validator fails on the renamed file.

**Empty-of-children case:** the cascade is trivially a one-file rename. Same commit message format with no `+ N children` suffix.

### 2.3 — Smarter deferral decision in `/dev-next` step 25.5

The step 25.5 subagent (defined in [~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md) step 25.5) currently calls `next_dev_number('specs')` and gets the next integer. After this spec, the subagent decides per-deferral: **decimal sub-spec** (jumps the queue, runs right after the parent) or **next-integer** (back of the queue).

**Default = next-integer.** Conservative — only promote to decimal when the item is genuinely a continuation. The user can override after the fact via `/spec-next` (§2.2).

**Decision rule the subagent applies, in order (first match wins):**

1. If the deferred item's title or context **explicitly references the parent spec's slug, ID, or a `## 2.N` subsection of the parent** ("§2.3 deferred", "the OAuth bit from 0170") → decimal sub-spec.
2. If the deferred item is described as a "**should but didn't**" of the parent (literal phrase, or "drop on the floor", "left out", "punted from this cycle") → decimal sub-spec.
3. Otherwise → next-integer (default).

The subagent does NOT consult the user — it cannot, by its `general-purpose` background-agent contract. The user reviews and can re-route via `/spec-next` after the fact. This is the explicit user-override path mentioned in the brief.

**File: [~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md)**

- Update the step 25.5 subagent prompt template (around line 305-322 of the skill) to include the three-bullet decision rule above. The subagent then calls either `next_dev_number('specs')` (integer path) or `next_decimal_child('specs', parent_id)` (decimal path) based on the rule.
- The subagent's report (final message) now states the routing decision per item: "spec NNNN as next-integer" or "spec NNNN.M as decimal sub-spec of NNNN — rule N matched".

**File: [scripts/spec_lifecycle/deferrals.py](scripts/spec_lifecycle/deferrals.py)**

No code change. The `DeferredItem` dataclass at [scripts/spec_lifecycle/deferrals.py:48](scripts/spec_lifecycle/deferrals.py:48) already carries title + context strings; the routing rule consumes those.

### 2.4 — Drop `queue_position` frontmatter field

`queue_position` is removed from the contract entirely. Spec ID *is* the queue order (per the §2.1 sort key).

**File: [scripts/spec_lifecycle/pick_next_number.py](scripts/spec_lifecycle/pick_next_number.py)** — delete `next_queue_position` ([line 64](scripts/spec_lifecycle/pick_next_number.py:64)) and update `current_queue` ([line 46](scripts/spec_lifecycle/pick_next_number.py:46)) per §2.1.

**File: [scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py)** — `DEV_REQUIRED_FRONTMATTER` at [line 23](scripts/spec_lifecycle/validator.py:23) does NOT currently include `queue_position`, so no removal needed; but: add a soft validator warning if `queue_position` appears in frontmatter on a newly-queued spec ("`queue_position` is deprecated; remove from frontmatter — order is determined by spec ID").

**File: [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py)** — drop all reads of `queue_position`:
- [line 335](scripts/spec_lifecycle/render_dashboard.py:335) (event-payload fallback)
- [line 486](scripts/spec_lifecycle/render_dashboard.py:486) (per-spec render)
- [line 1486-1487](scripts/spec_lifecycle/render_dashboard.py:1486) (queue-row template)
- [line 1764](scripts/spec_lifecycle/render_dashboard.py:1764) (next-up label)
- [line 2009](scripts/spec_lifecycle/render_dashboard.py:2009) (queue sort)
- JS half: [line 3539](scripts/spec_lifecycle/render_dashboard.py:3539), [line 3562](scripts/spec_lifecycle/render_dashboard.py:3562) — sort + render
Replace each with the §2.1 spec-ID sort. The queue-row template renders the spec ID itself in the "position" column (since position is now intrinsic to the ID).

**File: [~/.claude/skills/spec-queue/SKILL.md](scripts/_/spec-queue-skill-ref.md)** — step 3 stops calling `next_queue_position`; step 4 stops writing `queue_position` to frontmatter.

**File: [~/.claude/skills/spec-promote/SKILL.md](scripts/_/spec-promote-skill-ref.md)** — step 5 stops calling `next_queue_position`; step 6 stops writing `queue_position` to frontmatter.

**File: [~/.claude/skills/dev-next/SKILL.md](scripts/_/dev-next-skill-ref.md)** — step 24's "Re-rank remaining `status: queued` specs (decrement `queue_position` by 1)" sub-clause is deleted in its entirety. This is the source of ~half the per-spec status-bookkeeping commits.

**File: [specs/_templates/new-feature.md](specs/_templates/new-feature.md), [specs/_templates/bug.md](specs/_templates/bug.md), [specs/_templates/refactoring.md](specs/_templates/refactoring.md), [specs/_templates/test.md](specs/_templates/test.md), [specs/_templates/breaking.md](specs/_templates/breaking.md)** — strip the `queue_position: 0` line from each template's frontmatter block.

**File: [CONTRIBUTING.md](CONTRIBUTING.md)** — remove the `queue_position: <int, meaningful only while queued>` line at line 62; add a one-line note that order is intrinsic to spec ID.

**Bulk-strip existing 198 spec files.** Sweep `specs/*.md` and remove the `queue_position:` line from each frontmatter block. Single commit, message: `chore: strip deprecated queue_position from existing spec frontmatter (spec 0199 §2.4)`. Lazy-only migration was considered and rejected — the field's continued presence on 198 files is precisely the kind of stale state the spec is trying to eliminate. One noisy commit beats a forever-deferred cleanup. (Risk: the diff is large but mechanical; reviewed via `git diff --stat` shows only frontmatter lines.)

**Tests** — update [tests/spec_lifecycle/test_pick_next_number.py](tests/spec_lifecycle/test_pick_next_number.py), [tests/spec_lifecycle/test_render_dashboard.py](tests/spec_lifecycle/test_render_dashboard.py), [tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py), [tests/spec_lifecycle/test_queue_drain_supervisor.py](tests/spec_lifecycle/test_queue_drain_supervisor.py), [tests/spec_lifecycle/test_depends_on_frontmatter.py](tests/spec_lifecycle/test_depends_on_frontmatter.py), [tests/js/staleness-chip.test.js](tests/js/staleness-chip.test.js), [tests/js/dashboard-bootstrap.test.js](tests/js/dashboard-bootstrap.test.js) to stop emitting and asserting on `queue_position`. Add new tests for the spec-ID sort and decimal cases (§6 Test plan).

---

## 3. User stories & acceptance criteria

(This spec does not touch `src/dual_research/ui/` or `design-system/`, so per spec 0198 §2.3 the user-story + BDD gates are optional. Included anyway — the user explicitly requested them for this spec, and the gates exist because they catch drift even on non-UI code paths.)

### 3.1 — User stories

> As a **dev** running `/dev-next` after a spec deferred a `## 2.N` continuation, I want the deferral subagent to file the follow-up as a decimal sub-spec (`0170.1`) when it's clearly a continuation, so that the next `/dev-next` cycle picks up the continuation before unrelated queued work — without me having to hand-edit queue positions.

> As a **dev** with a queued spec that I now realise should jump the line (the upstream change just shipped, or it blocks the work I'm starting), I want a `/spec-next <id>` skill that re-IDs the spec as a decimal child of the in-flight one, so I can promote it to "runs next" without breaking handoff continuity or rewriting any other spec's frontmatter.

> As a **dev** reviewing the dashboard, I want the queue to display in true execution order without me having to mentally remap "queue position 3 = spec 0245", so that the next-up label and the `/dev-next` head pick agree by construction.

> As a **maintainer** of the orchestrator scripts, I want `queue_position` removed from the frontmatter contract entirely, so that no `/dev-next` cycle writes ~8 position-bookkeeping commits to `main` per spec.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** decimal-sub deferral routing
> GIVEN `/dev-next` just shipped spec `0170` and the handoff's `## Deferred during implementation` section lists an item titled "§2.3 OAuth refresh — drop on the floor for this cycle"
> WHEN the step 25.5 deferral subagent runs and applies the §2.3 decision rules
> THEN the new spec is written at `specs/0170.1-oauth-refresh.md` AND its `depends_on` includes `"0170"` AND the subagent's report states "spec 0170.1 as decimal sub-spec of 0170 — rule 1 matched (referenced parent §2.3)".

> **Scenario 2:** next-integer default for unrelated deferral
> GIVEN `/dev-next` just shipped spec `0170` and the handoff's deferral section lists an item titled "switch CHANGELOG date format to UTC" with no reference to spec `0170` or any `## 2.N`
> WHEN the step 25.5 deferral subagent runs
> THEN the new spec is written at `specs/0171-changelog-utc-dates.md` (or whatever the next-available integer is) AND the subagent's report states "spec 0171 as next-integer (default — no continuation signal)".

> **Scenario 3:** `/spec-next` promotes a queued spec, cascading children
> GIVEN spec `0250` is queued and has one decimal sibling `0250.1` queued, and spec `0198` is in flight (no existing decimal children)
> WHEN the user invokes `/spec-next 0250` from the author worktree
> THEN `specs/0250-*.md` is renamed to `specs/0198.1-*.md` AND `specs/0250.1-*.md` is renamed to `specs/0198.2-*.md` AND both files' `depends_on` fields are updated AND the changes land in a single commit on `main`.

> **Scenario 4:** `/spec-next` refuses when no spec is in flight
> GIVEN no spec has `status: in_progress` AND a queued spec `0250` exists
> WHEN the user invokes `/spec-next 0250`
> THEN the skill refuses with the message `"no spec in flight — '/spec-next' requires a parent to be next-of. Use /dev-next first, then /spec-next during the cycle."` AND no files are renamed.

> **Scenario 5:** queue sort is purely by spec ID after queue_position drop
> GIVEN three queued specs exist on disk with filenames `0170.1-a.md`, `0170-b.md`, `0171-c.md` and NONE carry a `queue_position` field in frontmatter
> WHEN `current_queue('specs')` is called
> THEN it returns the three specs in the order `[0170, 0170.1, 0171]` (by `parse_spec_id` ascending) AND the dashboard renders them in the same order.

> **Scenario 6:** validator rejects two-level decimal
> GIVEN a file at `specs/0170.1.1-foo.md` (two decimal levels)
> WHEN `uv run python -m scripts.spec_lifecycle.validator specs/0170.1.1-foo.md` runs
> THEN the exit code is non-zero AND the stderr contains a message naming the spec-ID format violation.

---

## 4. Data / Schema deltas

**Frontmatter contract change** — `queue_position` is removed from the dev-spec contract. The field is not added to `DEV_REQUIRED_FRONTMATTER` (it wasn't required before either), but all writers stop emitting it and all readers stop consuming it. A one-shot sweep strips it from the existing 198 spec files on disk (§2.4).

**Filename format change** — `specs/NNNN-<slug>.md` becomes `specs/NNNN(.M)?-<slug>.md`. Existing files keep integer IDs (out of scope to renumber per §5). The new format is additive — the old form is a strict subset.

**Event sidecar files** — `dashboard/events/<spec_id>.jsonl` filenames inherit the decimal. A spec `0170.1` writes to `dashboard/events/0170.1.jsonl`. The dot is filesystem-safe. No schema change to the JSONL records themselves.

**No DB / no API contract change** — these are repo-on-disk conventions only.

---

## 5. Out of scope

- **Renumbering existing specs 0001–0198.** They keep their integer IDs forever. The §2.4 bulk-strip touches only the `queue_position` line in each frontmatter block; the spec IDs themselves are untouched.
- **Multi-level decimal nesting.** `0170.1.1` is forbidden by the grammar (§2.1) and rejected by the validator (§2.1, §3.2 Scenario 6). A deferral from `0170.1` becomes the sibling `0170.2`, not the child `0170.1.1`. (Deferred to: nothing — the user explicitly chose one decimal level only as a baked-in design decision.)
- **Auto-detection of "tightly coupled" beyond the §2.3 three-rule heuristic.** The user can re-route after the fact via `/spec-next`. (Deferred to: no follow-up planned. If the heuristic proves too coarse, a future spec can tune it.)
- **A dashboard UI affordance for "promote this queued spec".** The `/spec-next` skill is CLI-only for now. (Deferred to: a future dashboard-interactivity spec, not in this 7-spec hardening series.)
- **Migrating handoff filenames to decimal-aware naming.** The handoff convention `handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md` already supports `NNNN.M` syntactically (the dash separators tolerate the dot inside the ID segment). No code change required. Verified via the `checkpoint.find_active_checkpoint` glob at [scripts/spec_lifecycle/checkpoint.py:123](scripts/spec_lifecycle/checkpoint.py:123) which uses `*-spec-{spec_number}-*.md` — handles decimals natively.

---

## 6. Test plan

- [ ] `parse_spec_id("0170")` returns `(170, 0)`; `parse_spec_id("0170.1")` returns `(170, 1)`; `parse_spec_id("0170.1.1")` raises `ValueError`.
- [ ] `format_spec_id(170, 0)` returns `"0170"`; `format_spec_id(170, 1)` returns `"0170.1"`.
- [ ] `next_dev_number('specs')` continues to return the next-integer ID when only integer specs exist, and ignores decimal-child files when computing the next parent (e.g. specs `0170`, `0170.1`, `0171` → next is `0172`, not `0171.1`).
- [ ] `next_decimal_child('specs', '0170')` returns `"0170.1"` when no decimal children exist, `"0170.2"` when `0170.1-*.md` exists, etc.; raises `ValueError` if called with a decimal parent like `'0170.1'`.
- [ ] `current_queue('specs')` returns queued specs sorted by `parse_spec_id` ascending; works correctly with a mix of decimal and integer IDs; does NOT read `queue_position`.
- [ ] Validator rejects a file at `specs/0170.1.1-foo.md` (two decimal levels) with a clear error naming the spec-ID format violation.
- [ ] Validator passes a file at `specs/0170.1-foo.md` (one decimal level) on the spec-ID check.
- [ ] Validator emits a soft warning (not error) if `queue_position:` appears in newly-authored frontmatter.
- [ ] `render_dashboard.py` integration test: render a fixture with three specs (`0170-a.md`, `0170.1-b.md`, `0171-c.md`) and assert the rendered HTML lists them in that order in both the Python-rendered initial view AND after the JS bootstrap re-sort.
- [ ] `render_dashboard.py` does not crash on a decimal spec ID (`int("0170.1")` regression at [render_dashboard.py:1629](scripts/spec_lifecycle/render_dashboard.py:1629)).
- [ ] `/spec-next 0250` end-to-end (mock the in-flight spec at `0198`): renames `specs/0250-*.md` → `specs/0198.1-*.md`, renames the corresponding `dashboard/events/0250.jsonl` → `dashboard/events/0198.1.jsonl`, updates `depends_on` in the renamed file's frontmatter, lands in one commit.
- [ ] `/spec-next 0250` cascade test: when `specs/0250.1-*.md` also exists, both files are renamed in one commit (`0250` → `0198.1`, `0250.1` → `0198.2`).
- [ ] `/spec-next` refuses with the documented message when no spec is in flight.
- [ ] `/spec-next` refuses with a documented message when the target ID itself is a decimal.
- [ ] Step 25.5 subagent prompt-template smoke test: feed three fake deferral items (one with §2.N reference, one with "drop on the floor" phrasing, one neutral) and assert the documented routing decisions.
- [ ] Existing 198 spec frontmatter files no longer contain `queue_position:` after the bulk-strip; spot-check 5 files.
- [ ] Hook regression: `cleanup-session-prefixes.py` parses `[DR · 0170.1 · O]` to `{"kind": "dev", "spec_id": "0170.1"}` and looks up the spec file via the existing glob successfully.
- [ ] Full `uv run pytest tests/ -q` is green.

---

## 7. Risks

- **Risk: filesystem or tooling barfs on `.` in filenames.** *Mitigation:* the dot is POSIX-portable, Git-portable, GitHub-Pages-portable, and accepted by every tool in the dual-research stack — verified via existing handoff filenames like `2026-05-22-spec-NNNN-foo.md` which already embed dots. The new spec filenames are tested in the §6 integration tests.

- **Risk: the bulk-strip of `queue_position` from 198 existing specs creates a noisy diff that masks a real change.** *Mitigation:* the strip is a single mechanical commit with a dedicated message; `git diff --stat` will show only frontmatter line removals; review can focus on the diff stat rather than line-by-line. The alternative (lazy migration) leaves stale state forever, which is precisely what this spec is trying to fix.

- **Risk: a deferral-subagent decimal routing decision is wrong — work that should have gone to next-integer ends up as a queue-jumping decimal sub-spec.** *Mitigation:* the three-rule heuristic is conservative (default = next-integer); the user can re-route via `/spec-next` or just hand-edit the filename + frontmatter before the next `/dev-next` cycle. Worst case is one cycle of wrong ordering, fully reversible.

- **Risk: cascade-rename in `/spec-next` produces an inconsistent state if the commit pushes but the rename of one event sidecar fails mid-script.** *Mitigation:* the skill stages all renames in the working tree first, then commits + pushes atomically; if any rename fails before the commit, no file is touched on disk after the script aborts. The git commit itself is atomic by definition.

- **Risk: the hook update at `~/.claude/hooks/cleanup-session-prefixes.py` is forgotten by an implementer (since it lives outside the repo).** *Mitigation:* the file is named as an explicit step in §2.1 and included in the §6 test plan as a hook-regression check. The implementer's handoff records that the hook was edited (and the diff applied), so future audits can reconstruct the state.

- **Risk: decimal sub-specs accumulate during one `/dev-next` cycle and create unbounded queue-jump chains (`0170 → 0170.1 → 0170.2 → 0170.3 → … → 0171`).** *Mitigation:* the one-level rule (§2.1) caps depth; the conservative default (§2.3) keeps the heuristic from spawning chains unless the items genuinely belong together. If chains get long in practice, that's diagnostic signal that the parent spec was under-scoped — surface for the user to triage. No automated mitigation needed at this spec's level.
