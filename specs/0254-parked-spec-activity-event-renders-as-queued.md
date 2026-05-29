---
kind: dev
spec: "0254"
slug: parked-spec-activity-event-renders-as-queued
title: "Fix: parked spec's activity event renders as QUEUED instead of Parked"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-29
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship
disposition_reason: "Active dashboard display defect mislabelling parked specs as queued; user requested it be runnable."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0254 — Fix: parked spec's activity event renders as QUEUED instead of Parked

> **Type:** bug  |  **Severity:** P2  |  **Affects:** dashboard RECENT ACTIVITY feed (server renderer + Cloudflare data API), all parked specs
> **Bump:** PATCH — bug fix
> **Evidence:** spec 0253.1 (`status: parked`, `disposition: archive`) renders the activity row `08:35:22 UTC · QUEUED · 0253.1`. Its already-recorded event in `dashboard/queue-state.json` is `{"ts":"2026-05-29T08:35:22Z","step":"queued","data":{"disposition":"archive","status":"parked"}}`.

---

## 1. Reproduction

**Environment:** Dashboard at `https://lexiz.github.io/dual-research/` (server-rendered by `scripts/spec_lifecycle/render_dashboard.py`) and the Cloudflare Pages function `functions/api/data.js`.

**Steps:**
1. Author a spec with `disposition: defer` or `disposition: archive` → it is committed with `status: parked` and an initial lifecycle event of `step: queued`.
2. Regenerate the dashboard (push to `main` triggers `.github/workflows/dashboard.yml`).
3. Look at the RECENT ACTIVITY feed for that spec.

**Expected:** The activity row reads **Parked** (the spec is correctly excluded from the runnable queue and shown in the Parked lane everywhere else).

**Actual:** The activity row reads **QUEUED** — e.g. `08:35:22 UTC · QUEUED · 0253.1`. Only the activity feed is wrong; the Parked lane and queue-picker exclusion are correct.

## 2. Root cause hypothesis

The initial lifecycle event is hardcoded as `step: queued` for **every** spec regardless of disposition, and the feed renderers display the `queued` step verbatim as "queued"/"Queued".

- **Emit side:** [`~/.claude/skills/spec-queue/SKILL.md:142`](~/.claude/skills/spec-queue/SKILL.md) emits `append-event NNNN queued '{}'` with an empty payload. The state-file `status` and commit message correctly derive `parked` (SKILL.md lines 135–141), but the event itself carries no disposition/status signal. The `/dev-next` deferral carve-out subagent (dev-next `SKILL.md` step 24.5, which reuses this flow) hits the same path — for 0253.1 it happened to emit `{"disposition":"archive","status":"parked"}`, so that payload is already self-describing, but the manual `/spec-queue` path is not.
- **Render side (parity twins):**
  - [`scripts/spec_lifecycle/render_dashboard.py:405`](scripts/spec_lifecycle/render_dashboard.py) (`_FEED_STEP_ICON`), [`:429`](scripts/spec_lifecycle/render_dashboard.py) (`_FEED_KICKER`), and [`:473`](scripts/spec_lifecycle/render_dashboard.py) (`_feed_detail`) all key purely off `step == "queued"` and emit the kicker `"queued"` — never inspecting `data.status`.
  - [`functions/api/data.js:209`](functions/api/data.js) already has the `_is_parked` parity twin (`spec.parked = spec.status === 'parked' || ...`) for the lane classification but does not apply the same parked-aware mapping to the activity event derivation.

This is a **labelling** defect, not a new contract: the `queued` event type is unchanged; we are reading existing payload/frontmatter to choose a display label.

## 3. Fix

No new lifecycle event type is introduced (that would force a `new-feature`/`breaking` label per CLAUDE.md). The `queued` step stays the single creation event; it becomes self-describing and the renderers become parked-aware.

**3.1 — Emit-time (self-describing event).** Change the canonical emit instruction in [`~/.claude/skills/spec-queue/SKILL.md:142`](~/.claude/skills/spec-queue/SKILL.md) so that when a spec is authored parked (`disposition != ship`), the initial `queued` event's data payload carries the status — `'{"status": "parked"}'` (or the chosen `<status>`) — instead of `'{}'`. Make this mechanical from the `<status>` already chosen in Step 4 / used in the state-file `set` (SKILL.md lines 135–141), so it is automatic for both manual `/spec-queue` and the `/dev-next` deferral carve-out subagent rather than hand-added. A runnable (`disposition: ship`) spec keeps the empty `'{}'` payload.

**3.2 — Render-time (`render_dashboard.py`).** A `queued` event whose `data.status == "parked"` (or whose owning spec's frozen frontmatter / overlaid status is parked) must render with the **Parked** kicker and a parked-appropriate icon/tone rather than "queued". Apply this in the feed kicker/icon lookup and `_feed_detail` so the same `queued` step yields two labels keyed on parked-ness. Use the existing parked derivation (`status == "parked"` / `disposition != "ship"` — the `_is_parked` logic) as the source of truth so the feed agrees with the Parked lane.

**3.3 — Render-time parity twin (`data.js`).** Apply the identical mapping in [`functions/api/data.js`](functions/api/data.js)'s activity derivation, reusing the existing `spec.parked` / `_is_parked` computation (lines 209–217). The two renderers MUST stay in lock-step per CLAUDE.md — same input → same "Parked" vs "Queued" label.

**3.4 — Backfill (render-only).** The mapping in 3.2/3.3 keys off the already-recorded event payload (`data.status == "parked"`) and/or the spec's parked frontmatter, so the existing 0253.1 event renders as **Parked** with no manual data edit. No migration of `dashboard/queue-state.json` is performed.

## 4. User stories & acceptance criteria

This spec touches the dashboard renderers `scripts/spec_lifecycle/render_dashboard.py` and `functions/api/data.js`; §5 below is the load-bearing regression gate.

### 4.1 — User stories

> As a `viewer`, I want a parked spec's RECENT ACTIVITY row to read "Parked", so that the feed agrees with the Parked lane and I am not misled into thinking the spec is runnable.

> As a `dev`, I want a normal queued spec's activity row to keep reading "Queued", so that the fix does not erase the distinction between runnable and parked specs.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** `parked spec reads Parked`
> GIVEN a `queued`-step activity event whose `data.status` is `"parked"` (e.g. spec 0253.1's recorded event)
> WHEN the dashboard activity feed renders that row
> THEN the row's kicker text is "Parked" and is not "Queued".

> **Scenario 2:** `runnable spec still reads Queued`
> GIVEN a `queued`-step activity event with empty `data` on a `disposition: ship` spec
> WHEN the dashboard activity feed renders that row
> THEN the row's kicker text is "Queued".

## 5. Regression-prevention test

Pure-stdlib pattern/unit tests per the UI test doctrine (no Playwright). Each fails before the fix, passes after.

- [ ] Test: a synthetic `queued` event with `data.status == "parked"` → `render_dashboard.py` feed renderer emits the Parked kicker (positive) and does NOT emit the "queued" kicker for that row (antipodal-absence).
- [ ] Test: a synthetic `queued` event with empty `data` on a `disposition: ship` spec → renders "Queued" (guards the normal path against over-matching).
- [ ] Test: regression fixture built from 0253.1's actual event (`step: queued`, `data: {"disposition":"archive","status":"parked"}`) → renders "Parked".
- [ ] Test: source-pattern assertion that `functions/api/data.js`'s activity derivation contains the parked-aware mapping (positive regex on the post-fix shape; antipodal-absence regex on the pre-fix verbatim-`queued` shape), keeping the two renderers' parity provable in stdlib per spec 0206.

## 6. Blast radius

- `_FEED_STEP_ICON` / `_FEED_KICKER` / `_feed_detail` in `render_dashboard.py` are read only by the activity feed; other `step` values (`in_progress`, `merged`, `deployed`, …) are untouched because the mapping branches only when `step == "queued"` **and** the spec is parked.
- `data.js` already computes `spec.parked`; reusing it adds no new data dependency.
- The emit-side change adds a key to the event `data` payload only for parked specs; runnable specs keep `'{}'`, so existing queued-spec feeds are unchanged.

## 7. Out of scope

- **Spec 0253.1 itself** (the supabase zero-event detail-path floor) — leave parked; this spec only fixes how its creation event is *labelled*.
- **Introducing a dedicated `parked` lifecycle event type** — explicitly avoided to keep this a `bug` (a new first-class event type would be a contract change requiring a `new-feature`/`breaking` label per CLAUDE.md).

## 8. Risks

- **Over-matching:** a guard test (normal `disposition: ship` queued spec still reads "Queued") prevents the parked branch from swallowing the normal path.
- **Parity drift:** the two renderers could diverge; the source-pattern test on `data.js` plus the shared `_is_parked` derivation keep them locked per CLAUDE.md's two-file rule.
- **Stale payloads:** specs queued before the 3.1 emit change carry `'{}'`; the render-time mapping therefore also falls back to the spec's parked frontmatter, so historical parked specs are caught even without the self-describing payload.
