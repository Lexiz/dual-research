---
kind: dev
spec: "0205"
slug: dashboard-queue-state-parity-and-l-spec-event-vocab
title: "Fix: dashboard live API + L-spec event vocab parity with queue-state.json"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-24
queued_at: "2026-05-24T01:30:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0205 — Fix: dashboard live API + L-spec event vocab parity with queue-state.json

> **Type:** bug  |  **Severity:** P1  |  **Affects:** all dashboard surfaces post-spec-0202 deploy
> **Bump:** PATCH — bug fix
> **Evidence:** spec 0203 currently in-flight; `dashboard/queue-state.json` shows `specs.0203.status = "in_progress"` with 5+ events (incl. `checkpoint_written`); live dashboard shows 0203 as `queued` with zero events. Confirmed by direct file inspection during authoring.

---

## 1. Reproduction

**Environment:** live dashboard at https://dr-dashboard.pages.dev (Cloudflare Pages), Function `/api/data` powered by [functions/api/data.js](functions/api/data.js). Repo state at authoring time: spec 0202 deployed (v1.42.0), spec 0203 mid-cycle (`status: in_progress` in `dashboard/queue-state.json`, no sidecar at `dashboard/events/0203.jsonl`).

**Steps:**
1. Open `https://dr-dashboard.pages.dev` in any browser. Bootstrap fetches `/api/data`.
2. Inspect the in-flight hero in the "Now" tab.
3. Open the activity feed in the "Now" tab.
4. Check the browser devtools Network tab for `/api/data` response → `specs[0203]` and `events[0203]`.

**Expected:**
- In-flight hero shows 0203 as "In flight · step N of 11 — implement" (or whichever stage is current).
- Elapsed timer ticks from `cycle_started` event ts (`2026-05-24T00:49:56Z`).
- Activity feed shows recent events for 0203 including `branched`, `implementing_started`, `checkpoint_written`.
- `/api/data` response has `specs[0203].status = "in_progress"` and `events["0203"]` is a non-empty array including `checkpoint_written`.

**Actual:**
- In-flight hero either doesn't surface 0203 at all OR shows it as `queued` (frozen frontmatter snapshot).
- Activity feed has no entries for 0203 after its `queued` event.
- `/api/data` response has `specs[0203].status = "queued"` and `events["0203"]` is missing or empty.
- Build-time renderer warnings on every Cloudflare build: `warning: spec 0203 has unknown event steps: ['checkpoint_written']`.

**Source of the regression:**

| source change | what it did | dashboard impact | spec section |
|---|---|---|---|
| **0202 §2.1** | Made `dashboard/queue-state.json` the authoritative store for cycle-mutable per-spec state (status, events, timestamps). Spec frontmatter `status` is now frozen at queue time. Per-spec sidecar `dashboard/events/NNNN.jsonl` is no longer written. | The build-time renderer was updated ([render_dashboard.py:171-198](scripts/spec_lifecycle/render_dashboard.py)). The live Pages Function was NOT — it still reads sidecars + frontmatter. | §3.1 |
| **0186 §2.2 + 0192** | Added `checkpoint_written` and `resume_started` events for L-spec checkpointing, plus `kind: in-spec-checkpoint` handoff variant. Carries `next_subsection` + `completed_subsections` payload. | Neither event name is in the dashboard's tolerated/labelled vocabulary. The payload that signals L-spec progress is dropped on the floor. | §3.2, §3.3, §3.4 |

## 2. Root cause hypothesis

Two independent regressions, both from `0202` and `0186/0192` landing without dashboard follow-up. Detail:

### 2.1 — `functions/api/data.js` never learned about queue-state.json

[functions/api/data.js:113-117](functions/api/data.js) only matches four blob shapes from the tree walk:

```
specs/\d{4}(?:\.\d+)?-…              → frontmatter (frozen at queue time after 0202)
specs/drafts/draft-\d{3}-…
handoffs/\d{4}-\d{2}-\d{2}-spec-…
dashboard/events/\d{4}(?:\.\d+)?\.jsonl  → per-spec sidecar (not written after 0202)
```

There is no fetch of `dashboard/queue-state.json`. The response shape ([data.js:174-180](functions/api/data.js)) spreads `row.fm` straight into the spec rows and builds `events` exclusively from sidecar buckets ([data.js:171-173](functions/api/data.js)).

After 0202 ships, no spec emits sidecars and no spec rewrites cycle-mutable frontmatter. So every active spec returns from `/api/data` with frozen queue-time status and an empty events bucket.

Cloudflare's 30s rebuild paints the shell correctly (the renderer reads queue-state.json — [render_dashboard.py:171-198](scripts/spec_lifecycle/render_dashboard.py)), then `dashboard-bootstrap.js` overwrites it with the stale live payload. Net: viewer sees regression.

### 2.2 — New event names rejected as "unknown"

[scripts/spec_lifecycle/stages.py:39-54](scripts/spec_lifecycle/stages.py) defines `TOLERATED_NON_STAGE_STEPS`. Neither `checkpoint_written` nor `resume_started` is in the set. `compute_stages` at [stages.py:207-210](scripts/spec_lifecycle/stages.py) classifies them as unknown, so [render_dashboard.py:3996](scripts/spec_lifecycle/render_dashboard.py) prints `warning: spec NNNN has unknown event steps: ['checkpoint_written']` on every build.

### 2.3 — Feed icons + kickers missing

[render_dashboard.py:348-365](scripts/spec_lifecycle/render_dashboard.py) (`_FEED_STEP_ICON`) and [render_dashboard.py:367-384](scripts/spec_lifecycle/render_dashboard.py) (`_FEED_KICKER`) have no entries for the new events. The lookup at [render_dashboard.py:1590-1591](scripts/spec_lifecycle/render_dashboard.py) falls back to `("circle", "neutral")` + `step.replace("_", " ")`. Functional but unbranded.

### 2.4 — L-spec sub-progress is invisible

The in-flight hero ([render_dashboard.py:541-650](scripts/spec_lifecycle/render_dashboard.py)) anchors the "currently · …" chip to `latest_step` via `STEP_LABELS` ([stages.py:58-79](scripts/spec_lifecycle/stages.py)). The `checkpoint_written` event payload (`next_subsection`, `completed_subsections`) — the only signal that an L-spec is making sub-section progress — surfaces nowhere. A multi-hour L-spec like 0203 appears frozen on "Implement" with no indication of `§2.5 of …` progress.

## 3. Fix

Four additive sub-changes. None alter the canonical 11-stage timeline.

### 3.1 — Teach `functions/api/data.js` about queue-state.json (load-bearing)

In [functions/api/data.js](functions/api/data.js):

1. Append `dashboard/queue-state.json` to `allBlobs` AFTER `eventBlobs` so existing alias indices stay stable. It's a single extra blob — one extra GraphQL aliased field, well under the 50-subrequest free-tier limit and inside the existing 400-alias batch.
2. Parse it as JSON (not YAML) in the post-fetch loop, into `let queueState = null;`.
3. Define at the top of the file:
   ```js
   const QUEUE_STATE_LAYERED_FIELDS = [
     'status', 'started_at', 'merged_at', 'deployed_at',
     'pr', 'handover', 'failure_step', 'target_version', 'queued_at',
   ];
   ```
   Mirror of `_QUEUE_STATE_LAYERED_FIELDS` at [render_dashboard.py:40-52](scripts/spec_lifecycle/render_dashboard.py). Keep in lock-step.
4. After `specRows` is built ([data.js:148-156](functions/api/data.js)), layer `queueState.specs[full_id]` over each spec row: for each key in `QUEUE_STATE_LAYERED_FIELDS`, if the queue-state entry has a non-null value, overwrite the spec row's value.
5. Build `events` map ([data.js:172-175](functions/api/data.js)) with preference order: queue-state entry's `events` array if present, else legacy sidecar bucket. Mirrors the renderer's preference at [render_dashboard.py:193-198](scripts/spec_lifecycle/render_dashboard.py).
6. Add `queue_state_updated_at: queueState?.updated_at ?? null` to the response envelope at [data.js:176-181](functions/api/data.js). Bootstrap can use this as the freshness anchor in a follow-up; for this spec it's just plumbed through.

Defensive: if the queue-state blob fails to fetch or parse, log and proceed with the legacy path (don't 502 the whole API). Mirror the existing "skip on parse failure" pattern.

### 3.2 — Add new event names to the orchestrator vocabulary

In [scripts/spec_lifecycle/stages.py](scripts/spec_lifecycle/stages.py):

- `TOLERATED_NON_STAGE_STEPS` (line 39): add `"checkpoint_written"` and `"resume_started"`.
- `STEP_LABELS` (line 58): add `"resume_started": "resuming"` and `"checkpoint_written": "checkpoint"`.

### 3.3 — Add feed icons + kickers + details for new events

In [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py):

- `_FEED_STEP_ICON` (line 348): `"resume_started": ("replay", "info")`, `"checkpoint_written": ("bookmark_added", "info")`. Both are Material Symbols already used elsewhere in the codebase tree (Google Symbols catalogue; no DS extension needed — DS check below).
- `_FEED_KICKER` (line 367): `"resume_started": "resumed"`, `"checkpoint_written": "checkpoint"`.
- `_feed_detail` (line 390): add a branch for `checkpoint_written` → `f"{spec_label} · §{_escape(data.get('next_subsection') or '?')} · {len(data.get('completed_subsections') or [])} done"`. Add a branch for `resume_started` → `f"{spec_label} · resumed at §{_escape(_latest_checkpoint_subsection(spec) or '?')}"` where `_latest_checkpoint_subsection` is a new private helper that scans `spec.events` in reverse for the most recent `checkpoint_written` event and returns its `next_subsection`. (The `resume_started` event's own `data` is empty per [checkpoint.py:188](scripts/spec_lifecycle/checkpoint.py).)

### 3.4 — Surface L-spec sub-progress on the in-flight hero

In `_render_hero_inflight` ([render_dashboard.py:541-650](scripts/spec_lifecycle/render_dashboard.py)):

After the existing "currently · …" chip ([render_dashboard.py:603-606](scripts/spec_lifecycle/render_dashboard.py)) and BEFORE the staleness chip ([render_dashboard.py:608-615](scripts/spec_lifecycle/render_dashboard.py)):

- Locate the most recent `checkpoint_written` event in `spec.events`.
- If found AND `spec.status == "in_progress"`:
  ```py
  next_sub = (cp_ev.get("data") or {}).get("next_subsection") or "?"
  done_n  = len((cp_ev.get("data") or {}).get("completed_subsections") or [])
  chips.append(
      f'<span class="chip tone-info" data-checkpoint-next="{_escape(next_sub)}" '
      f'data-checkpoint-done="{done_n}">'
      f'§{_escape(next_sub)} · {done_n} subsections done</span>'
  )
  ```
- `data-checkpoint-next` / `data-checkpoint-done` attributes let the bootstrap update the chip in place without a re-render (§3.5 below). Keep the same DOM shape on first paint and on bootstrap update.

### 3.5 — Bootstrap parity for the live chip

`DASHBOARD_BOOTSTRAP_JS` inside [render_dashboard.py:3277-3580](scripts/spec_lifecycle/render_dashboard.py) reimplements `compute_stages`, the staleness chip, and the "currently" chip. Add:

- `STEP_LABELS_JS` mirror entries for the two new step names (same strings as §3.2).
- A client-side branch in the hero update path: when the latest event for the in-flight spec is `checkpoint_written`, find the chip with `data-checkpoint-next` and update its inner text + `data-*` attributes. If the chip is absent (first checkpoint after a fresh paint that pre-dates the event), inject it after the "currently" chip using the same HTML template as §3.4.
- Mirror `_feed_detail`'s new branches in the feed renderer (~[render_dashboard.py:3577](scripts/spec_lifecycle/render_dashboard.py)) so the live feed shows the same icon + kicker + detail as the server-rendered feed.

Lock-step with server-rendered first paint is required (spec 0163 §2.4 pattern) to avoid a visible flash.

### 3.6 — Design-system check

All new UI is composed of existing DS primitives:

- Chip variant: `chip tone-info` — established primitive (see [render_dashboard.py:603-605](scripts/spec_lifecycle/render_dashboard.py)).
- Material Symbols `replay` and `bookmark_added` — Google catalogue, identical loader/font path to existing icons like `bookmark`, `merge`, `check_circle` ([render_dashboard.py:348-365](scripts/spec_lifecycle/render_dashboard.py)).

No DS extension required. Spec body does not modify `design-system/SPEC.md`.

## 4. User stories & acceptance criteria

### 4.1 User stories

- As a **viewer**, I want the live dashboard to reflect the in-flight spec's real status and event stream within ~30s of an event, so I can see what `/dev-next` is doing without re-running it.
- As a **viewer**, I want to see L-spec subsection progress (e.g. `§2.5 · 5 subsections done`) so a multi-hour L-spec doesn't appear frozen on the timeline.
- As a **viewer**, I want the activity feed to render meaningful kickers and icons for checkpoint and resume events, not generic circle placeholders.

### 4.2 Acceptance scenarios (BDD)

> **Scenario 1:** in-flight hero reflects queue-state status
> GIVEN `dashboard/queue-state.json` has `specs.0203.status = "in_progress"` and at least one event with step `implementing_started`
> WHEN the dashboard loads and bootstrap.js fetches `/api/data`
> THEN the hero kicker text contains `In flight · step` AND the hero title link points to `spec-0203.html` AND the elapsed timer's `data-cycle-started-at` attribute is set to the `cycle_started` event timestamp.

> **Scenario 2:** L-spec sub-progress chip
> GIVEN the latest event for the in-flight spec is `checkpoint_written` with `data.next_subsection = "2.5"` and `data.completed_subsections.length = 5`
> WHEN the dashboard renders (either server-side first paint or bootstrap update)
> THEN a chip in the hero contains text matching `/§2\.5/` AND `/5 subsections done/` AND carries `data-checkpoint-next="2.5"`.

> **Scenario 3:** feed entry for checkpoint_written
> GIVEN a `checkpoint_written` event exists in the last 24h for any spec
> WHEN the activity feed renders
> THEN the corresponding feed row uses the `bookmark_added` Material Symbol AND the kicker text "checkpoint" AND the detail text contains `§` followed by the event's `next_subsection`.

## 5. Regression-prevention tests

- [ ] **[functions/api/data.test.js](functions/api/data.test.js)** — extend the test suite: build a fixture queue-state.json with one in-flight spec (events array populated, status `in_progress`) and zero sidecars; mock the GraphQL response to include the queue-state blob; assert the response merges `status`/`started_at`/`events` from queue-state into the matching spec row and exposes `queue_state_updated_at` at the top level. Fails before the §3.1 fix; passes after.
- [ ] **`tests/test_stages.py`** (or wherever `compute_stages` tests live) — extend the "tolerated steps" coverage: pass an event list including `checkpoint_written` and `resume_started`; assert the returned `unknown_events` list is empty. Fails before §3.2; passes after.
- [ ] **`tests/test_render_dashboard.py`** — new test: build a `SpecRow` with synthetic events `[cycle_started, in_progress, implementing_started, checkpoint_written{data:{next_subsection:"2.5", completed_subsections:["2.1","2.2","2.3","2.4","2.8"]}}]` and status `in_progress`; call `_render_hero_inflight`; assert the returned HTML contains `§2.5` AND `5 subsections done` AND `data-checkpoint-next="2.5"`. Fails before §3.4; passes after.
- [ ] **Manual:** after deploy, wait < 60s, refresh dashboard, confirm the in-flight spec (will be 0203 if still mid-cycle, otherwise the next L-spec) reflects real queue-state status, shows live events, and shows the L-spec sub-progress chip if a `checkpoint_written` event exists.

## 6. Blast radius

- **`functions/api/data.js`** is the only Cloudflare Pages Function in the repo. The queue-state.json fetch is +1 GraphQL aliased field (well inside `GRAPHQL_BATCH_SIZE = 400` and the 50-subrequest free-tier ceiling). Edge cache (15s `max-age` + 60s SWR) absorbs hot traffic. Existing alias indices preserved by appending the new blob last.
- **`scripts/spec_lifecycle/stages.py`** changes are additive (more tolerated steps, more labels). No existing test asserts the new events are unknown. `current_stage_label` is unaffected — neither new event maps to a canonical stage.
- **`scripts/spec_lifecycle/render_dashboard.py`** changes are additive (dict entries + one extra chip in the in-flight hero + small `_feed_detail` branches + bootstrap mirror). Does not modify the 11-stage canonical timeline, the breakdown chart, the cycle-time metrics, or any deployed-spec rendering. The new chip slots into the existing `chips` list at the same position as other in-flight chips.
- **Backwards compatibility:** legacy sidecar fallback retained in both `data.js` and `render_dashboard.py` so historical specs (pre-0202) that still have sidecars continue to render.

## 7. Out of scope

- **Sidecar archive surfacing** (`dashboard/events/archive/`) — read-only history, no live UI need; deferred to a follow-up if/when an archive viewer is desired.
- **Differentiating `kind: in-spec-checkpoint` from `kind: post-deploy` in the handoff list** — aesthetic only, no functional regression; deferred to a separate dev spec post-merge if the user wants the distinction surfaced.
- **Backfilling sidecars for specs ≥ 0202** — `queue-state.json` is the new contract; do not regenerate sidecars.
- **Adding a separate "L-spec progress" tab or timeline visualisation** — out of scope for the bug fix; the in-flight hero chip is sufficient signal. Deferred to a follow-up dev spec if richer L-spec UX is wanted.

## 8. Risks

- **GraphQL batch shape change in `data.js`** — must keep existing alias indices stable so the post-fetch dispatch stays deterministic. Mitigation: queue-state.json appended LAST to `allBlobs`; existing four-shape regex dispatch loop is unchanged for indices `0..N-1`; new blob handled by an explicit index check at `i === allBlobs.length - 1` OR by a fifth path regex (`^dashboard/queue-state\.json$`).
- **"currently · resumed" label timing** — if a `resume_started` fires but the next stage-event lands within the same poll window, the chip would briefly flicker through "resumed". Mitigation: only flip the chip label when `resume_started` is literally the latest event; once any subsequent event arrives, the chip reverts to that event's label.
- **Bootstrap-before-Function deploy window** — if the bootstrap update ships before `data.js` redeploys (Cloudflare rebuild + Function deploy race), the live chip injection runs against the old API payload that lacks `queue_state_updated_at`. Mitigation: bootstrap reads with `??` fallbacks (no hard dependency on the new envelope field); worst case the chip simply doesn't appear, which is the current state.
- **L-spec checkpoint payload schema drift** — if a future spec changes `completed_subsections` from a list to a count or renames `next_subsection`, the chip would render `§? · 0 done`. Mitigation: the helper reads both fields defensively (`.get(...) or default`) and degrades gracefully rather than crashing.
