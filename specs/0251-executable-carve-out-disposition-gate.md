---
kind: dev
spec: "0251"
slug: executable-carve-out-disposition-gate
title: Make the carve-out disposition gate executable in the queue picker
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship
disposition_reason: "Closes a doctrine-only gate that lets archive/defer carve-outs run; a first-class lifecycle/contract change worth shipping now."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. -->

# Spec 0251 — Make the carve-out disposition gate executable in the queue picker

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds the `parked` lifecycle state and a new queue-selection predicate (a contract change; per CLAUDE.md's contract-change rule this is `new-feature`, not `bug`).
> **Evidence:** CLAUDE.md §"Carve-out follow-ups must triage at carve-out time" (line 60); spec 0229 §7 R4 (doctrinal-drift risk); Cowork verification of the live queue state (one spec, 0248, `disposition: ship`).

---

## 1. Context

CLAUDE.md:60 states the doctrine: *"A carve-out reaches `/dev-next` only when its disposition is `ship`,"* with default `archive`. The gate is **doctrine-only — nothing enforces it.** Three surfaces ignore `disposition`:

- The queue picker `current_queue` at [`pick_next_number.py:155`](scripts/spec_lifecycle/pick_next_number.py:155) filters on `fm.get("kind") == "dev" and live_status == "queued"` only — it never reads `disposition`. (`live_status` is the queue-state overlay; frozen frontmatter status is correctly ignored for finished specs.)
- The validator enforces the *presence and shape* of `disposition` / `disposition_reason` (`VALID_DISPOSITIONS = {"ship","defer","archive"}` at [`validator.py:24`](scripts/spec_lifecycle/validator.py:24), `_check_disposition_shape`) but not the gate.
- The `/dev-next` step 24.5 deferral subagent (`~/.claude/skills/dev-next/SKILL.md`, step 24.5 at line 509) always commits auto-authored carve-outs as `status: queued`, regardless of disposition.

Net: a carve-out with `disposition: archive` still runs as long as `status: queued`. Deferrals accrete into the run queue by default — the exact doctrinal-drift risk spec 0229 §7 R4 named. The corpus is already 256 specs.

## 2. Proposed change

Four coordinated edits.

### 2.1 — Gate the queue picker (the single read-time choke point)

In `current_queue` at [`pick_next_number.py:155`](scripts/spec_lifecycle/pick_next_number.py:155), additionally require frozen-frontmatter disposition `== "ship"`. `disposition` lives in frozen frontmatter (`fm`); `status` in the overlay (`live_status`) — read each from its own source:

```python
if fm.get("kind") == "dev" and live_status == "queued" and fm.get("disposition") == "ship":
```

**Safe to enable now, no false drops** (Cowork-verified; stated so reviewers trust the flip): the live queue (queue-state overlay) is exactly one spec — 0248, `disposition: ship`. The older 0203–0228 block shows `status: queued` only in *frozen* frontmatter; the overlay resolves them to `merged`, so they will not be wrongly skipped.

### 2.2 — Never drop silently: log + surface skipped specs

A silent skip is the worst failure mode. Two parts.

**a. Log skips at pick time.** `current_queue` must also collect the queued specs it SKIPPED for `disposition != "ship"` (i.e. `live_status == "queued"` but `disposition != "ship"`) and expose them — via a second return value or a companion function. The `/dev-next` picker step (step 6) must log `skipped N queued specs (disposition≠ship): [ids]` to chat/stderr. Never drop silently.

**b. Surface on the dashboard.** Parked-but-queued specs get a distinct lane (e.g. "Parked") so a non-`ship` spec isn't invisible. This touches [`render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) (`_render_pipeline` column set, ~line 826) AND its parity twin [`functions/api/data.js`](functions/api/data.js) (queue-state overlay block, ~line 198). Keep the two in sync — same discipline as the existing overlay logic both already mirror. **This dashboard lane is the bulk of the implementation effort.**

### 2.3 — Honest status at authoring time: add a `parked` status

Auto-authored carve-outs (and human-authored specs) whose disposition is not `ship` should carry a non-runnable status so frozen frontmatter matches reality rather than lying with `queued`.

- Add `parked` to `VALID_STATUSES` (enforced at [`validator.py:182`](scripts/spec_lifecycle/validator.py:182); set defined at `validator.py:21`).
- Add `parked` to any status vocabulary in [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) / `build_queue_state.py` if a status enum is referenced there. Status is a free-form scalar today, but confirm and add wherever a vocab is asserted.
- Edit the `/dev-next` step 24.5 subagent template (`~/.claude/skills/dev-next/SKILL.md`, line 509) so it sets `status` from the disposition it assigns: `ship` → `queued`; `defer` / `archive` → `parked`. Default disposition stays `archive` (matches CLAUDE.md) → default status `parked` (not runnable).
- For consistency, the `/spec-queue` and `/spec-promote` skills should likewise write `status: parked` when the author leaves disposition at a non-`ship` value, so a human must consciously set `disposition: ship` to enqueue. The §2.1 gate makes this enforceable regardless, but honest status keeps the corpus readable.

### 2.4 — Doctrine + cleanup

- Update CLAUDE.md:60: the gate now applies to **all** queued dev specs, not just carve-outs (a scope expansion beyond today's carve-out-only wording). Any dev spec authored without an explicit `disposition: ship` is un-runnable until promoted. State that this is the intended fail-safe, and that the picker logs every skip (§2.2) so it is never silent.
- Fix step-number drift: [`scripts/spec_lifecycle/deferrals.py:7`](scripts/spec_lifecycle/deferrals.py:7) docstring says "step 25.5"; the skill says "step 24.5". Reconcile to the skill's actual numbering (24.5).

## 4. Data / Schema deltas

No DB schema impact. Lifecycle-vocabulary delta only: `VALID_STATUSES` gains `parked`. `dashboard/queue-state.json` may now carry `status: parked` entries; the overlay readers in `render_dashboard.py` and `functions/api/data.js` must treat `parked` as a known, surfaceable state.

## 5. Out of scope

- `deploy.yml` and the `/dev-next` pre-merge telemetry buffering — those are separate queued specs (0249, 0250); do not touch.
- No design-system (component) work beyond the dashboard "Parked" lane, which is data-derivation plus an existing render surface. Cite the relevant `render_dashboard.py` / `data.js` sections rather than design-system primitives unless a new visual token is introduced.
- No retroactive re-statusing of the existing 0203–0228 frozen frontmatter — the overlay already resolves them to `merged`; the gate reads `fm.disposition` only on live-queued specs.

## 6. Test plan

- [ ] `pick_next_number`: a queued spec with `disposition: archive` is EXCLUDED from `current_queue`; a queued spec with `disposition: ship` is INCLUDED; the skipped-spec collector returns the archive/defer ids. Cover decimal IDs (e.g. `0170.1`).
- [ ] `validator`: `parked` is accepted in `VALID_STATUSES`; a non-vocab status (e.g. `bogus`) is still rejected.
- [ ] Dashboard: parked / non-`ship` queued specs derive into the Parked lane in BOTH `render_dashboard.py` and `functions/api/data.js` (assert parity across the two surfaces).
- [ ] Skill (skip-when-absent, per spec 0247 precedent): the `/dev-next` step 24.5 subagent template sets `status` from disposition (`ship` → `queued`, else `parked`).
- [ ] Picker logging: the skip-log line `skipped N queued specs (disposition≠ship): [ids]` is emitted when ≥ 1 queued spec has `disposition != "ship"`.

## 7. Risks

- **Wrongly skipping a live spec.** Mitigated by the Cowork-verified one-spec live queue (0248 = `ship`) and the mandatory skip-log in §2.2a — no silent drop, so any false skip is immediately visible in chat/stderr and on the dashboard Parked lane.
- **Dashboard parity drift** between `render_dashboard.py` and `functions/api/data.js`. Mitigated by a single test that asserts the Parked-lane derivation on both surfaces.
- **Default flips to non-runnable.** Authors who omit `disposition: ship` now produce a `parked` spec. This is the intended fail-safe (documented in §2.4), and the skip-log makes the parked state discoverable rather than silent.
