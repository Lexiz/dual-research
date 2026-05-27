---
spec: 0142
title: Prompt capture for full-view modals — Initial Brief persistence and modal hydration
label: bug
version-bump: PATCH
status: ready
target-version: 1.9.3
created: 2026-05-21
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0142 — Prompt capture for full-view modals

> Ship bucket: **UI full-view modal hydration / prompt persistence.**
> Depends on: **0019** (Supabase `session_files` schema), **0033** (per-turn
> `TurnInputs` event + `inputs/<key>.json`), **0085** (synth fallback for
> missing bundles). Downstream: **0145** (canonical prompt-piece registry)
> builds on the same persistence path producing non-empty prompts, so this
> spec must land first.
> Complexity: **S** — one new persisted file (`inputs/input.json`), one new
> Phase-0 round-keyed bundle path, and a modal turn-key routing fix.
> Targeted version bump: **PATCH (1.9.2 → 1.9.3)** — bug fix. No schema
> changes; new files slot into the existing `inputs/<key>.json` shape.

---

## Context

On run `20260521-010637-dvs-backend-language-choice`, opening the Initial
Brief full-view card (the `kind: 'input'` card on the Phase 0 row of the
timeline) renders the System Prompt and User Prompt with synthesised /
placeholder content carrying the **"agent default — the per-run system
prompt for this older turn was not recorded"** caveat — even though the
run is current and the prompts demonstrably exist in
the `events` table. To the user this reads as "empty / wrong prompts on
a fresh run", which is the failure B05 captures.

Three independent gaps combine:

1. **The modal's turn-key is a literal sentinel.** `InputBriefModal`
   ([run-detail.jsx:5657](src/dual_research/ui/static/run-detail.jsx)) opens
   with `turnKey={item.turnKey || 'input'}`, and the timeline builder
   stamps exactly `turnKey: 'input'` on the brief card
   ([live-data.jsx:493](src/dual_research/ui/static/live-data.jsx)). No
   `inputs/input.json` is ever written, so the server falls into the
   synthesis branch in `_read_input_bundle_supabase`
   ([server.py:1517](src/dual_research/ui/server.py)) which composes a
   placeholder system prompt from `preflight_input_bundle(..., agent_name="<agent>")`
   — i.e. the brief is folded in but the system text is the agent-default
   variant with `<placeholder>` substitutions, stamped
   `system_source: "agent-default"`.

2. **No `inputs/input.json` is ever persisted.** The orchestrator emits
   `TurnInputs` only inside `run_one_call`
   ([_call.py:91](src/dual_research/orchestrator/_call.py)), keyed by the
   per-turn `turn_key` (`phase0_claude`, `phase0_gpt`, …). The shared
   Phase-0 "brief" — the input slot the InputBriefModal claims to show —
   has no producer in the persistence path.

3. **Per-round Phase-0 inputs are clobbered.** `_derive_turn_key`
   ([_call.py:42](src/dual_research/orchestrator/_call.py)) only includes
   the round index for `phase ∈ {2, 4}`, so every Phase-0 negotiation
   round writes to the same `inputs/phase0_<agent>.json` path. The
   last-write-wins semantics mean only the final round's bundle survives
   on disk; for the anchor run, `inputs/phase0_claude.json` carries
   `label: "phase0-r4-claude"` even though four `phase0_round{1..4}_claude`
   cards in the timeline link to that single file.

The Supabase events for this run *do* carry the prompt text per turn —
`events?kind=eq.turn_inputs` returns 39 rows with full `pieces.system`
(~4.9k chars) and `pieces.brief` (~18.4k chars). The data exists; the
UI's lookup path doesn't find it.

Actual payload of the first Phase-0 `turn_inputs` row
(`seq=3`, `payload.label="phase0-r1-claude"`):

```json
{
  "agent": "claude",
  "phase": "phase0",
  "label": "phase0-r1-claude",
  "pieces": {
    "system": "You are participating in a dual-agent research protocol with another large langu… (4914 chars)",
    "brief":  "# Document Verification Service — Backend Language Choice\n\n> This file is the fu… (18377 chars)",
    "d1": "", "d2": "", "plan": "", "hist": "", "draft": "", "histp": ""
  }
}
```

`session_files?run_id=eq.<run>&path=like.inputs*` returns **zero rows**
for this run despite 33 `inputs/*.json` files existing on the local
session-dir — the push CLI's `rglob("*.json")` claims to cover them
([remote.py:303](src/dual_research/persistence/remote.py)) but the rows
are not present in Supabase for this run. This is the failure surface
behind the empty modal: even when the on-disk file exists, the hosted
backend can't see it.

## Current-state audit

### Modal JSX
| file:line | role |
|---|---|
| [run-detail.jsx:5636](src/dual_research/ui/static/run-detail.jsx) | `InputBriefModal` — the full-view container for the Initial Brief card. |
| [run-detail.jsx:5657](src/dual_research/ui/static/run-detail.jsx) | `<InputTabContent turnKey={item.turnKey \|\| 'input'} />` — hydration call. |
| [run-detail.jsx:5103](src/dual_research/ui/static/run-detail.jsx) | `InputTabContent` — fetches via `useInputBundle(turnKey)`. |
| [live-data.jsx:493](src/dual_research/ui/static/live-data.jsx) | Timeline builder stamps `turnKey: 'input'` on the brief card. |
| [run-detail.jsx:5085](src/dual_research/ui/static/run-detail.jsx) | `INPUT_PIECE_ORDER = ['system', 'brief', 'd1', …]` — render order. |

### Server-side prompt-capture path
| file:line | role |
|---|---|
| [_call.py:91](src/dual_research/orchestrator/_call.py) | `run_one_call` emits `TurnInputs(pieces=prompt_bundle)` when caller supplies a bundle. |
| [_call.py:36](src/dual_research/orchestrator/_call.py) | `_derive_turn_key` — Phase 0 collapses to `phase0_<agent>` (no round). |
| [aggregator.py:734](src/dual_research/ui/aggregator.py) | `_on_turn_inputs` writes `session_dir/inputs/<key>.json`. |
| [aggregator.py:529](src/dual_research/ui/aggregator.py) | `build_phase0_input_bundle` — synthesises the `input` bundle from `brief.md` + placeholder system text. |
| [protocol/prompts.py:937](src/dual_research/protocol/prompts.py) | `preflight_input_bundle` — returns the 8-key dict with `brief` populated and `d1..histp` empty. |

### Supabase storage layer
| file:line | role |
|---|---|
| [supabase/migrations/0001_initial.sql:44](supabase/migrations/0001_initial.sql) | `session_files (run_id, path, content, size_bytes)` PK `(run_id, path)`. |
| [supabase/migrations/0001_initial.sql:33](supabase/migrations/0001_initial.sql) | `events (run_id, seq, ts, kind, payload jsonb)` — already holds the real prompt text. |
| [remote.py:303](src/dual_research/persistence/remote.py) | `_iter_file_rows` rglobs `*.md, *.json, *.jsonl` from the session-dir. |
| [server.py:1448](src/dual_research/ui/server.py) | `_read_input_bundle_supabase` — Supabase lookup + synth fallback. |
| [server.py:1517](src/dual_research/ui/server.py) | Special `key == "input"` branch — synthesises with `system_source: "agent-default"`. |

## Proposed change

Three concrete edits, smallest to largest:

**1. Persist a real `inputs/input.json` at session setup.**
When the orchestrator boots a session and writes `brief.md`, also write
the shared Phase-0 input bundle to `session_dir/inputs/input.json` using
the same `build_phase0_input_bundle` builder the synth path already
calls — but with `system_source: "recorded"` and the real per-run agent
names rather than the `"<agent>"` placeholder. This file is then picked
up by the existing `rglob("*.json")` in `_iter_file_rows` and pushed to
Supabase like every other input bundle.

```python
# src/dual_research/orchestrator/run.py — at session setup, alongside
# the existing brief.md write:
from dual_research.protocol.prompts import preflight_input_bundle
from dual_research.persistence.input_bundle import write_input_bundle_file

write_input_bundle_file(
    session_dir,
    key="input",
    payload={
        "agent": "shared",
        "phase": "phase0",
        "label": "phase0-input",
        "pieces": preflight_input_bundle(brief=brief_text, agent_name="<both>"),
        "emitted_at": iso_now(),
        "system_source": "recorded",
    },
)
```

**2. Round-key Phase-0 inputs.** Extend `_derive_turn_key`
([_call.py:42](src/dual_research/orchestrator/_call.py)) to include the
round index for `phase == 0` when `idx > 0`, matching the existing
`phase ∈ {2, 4}` branch. Same change in `_on_turn_inputs`
([aggregator.py:752](src/dual_research/ui/aggregator.py)). After this,
`inputs/phase0_round1_claude.json … phase0_round4_claude.json` all
persist independently, and the round-keyed timeline cards (`turnKey:
"phase0_round1_claude"`, etc.) get real per-round bundles instead of
falling back to whatever survived last-write-wins.

**3. Audit the other full-view modals for the same class of bug.**
Per B05's "audit every other full-view card", confirm each modal's
`turnKey` resolves to a persisted bundle or — for Phase 0 / Phase 1
single-call phases — to one of the synthesis-friendly keys. The cards
listed in `live-data.jsx` already use canonical `phase{N}_round{R}_{agent}`
keys for phases 2 and 4; phase 1 uses `phase1_{agent}` which is the
correct single-call shape; the `input` sentinel is the only outlier.
After change (1), it becomes a real persisted key like the rest.

## Out of scope

- **No canonical prompt-piece registry.** Spec 0145 introduces a
  registry that names every piece (system, brief, d1, d2, plan, …) with
  a stable id and surfaces per-piece token tracking. This spec only
  ensures the existing 8-key `pieces` dict has non-empty content where
  it should — registry refactor lands separately on top.
- **No per-attachment token tracking.** Also 0145's territory.
- **No Consumption-tab UI changes.** The Consumption tab already
  consumes `prompt_pieces` from `TurnEnded`; that path is independent of
  this fix and unaffected.
- **No backfill of past runs' `inputs/input.json`.** Section "Risks"
  discusses why; new runs persist, old runs continue to synthesise.
- **No fix to the push CLI's apparent skip of `inputs/*.json`.** The
  anchor run has zero `inputs/*` rows in Supabase despite 33 on disk;
  the root cause (push-while-running timing, row-size limit, or a
  filter we missed) is tracked separately. After this spec's
  `inputs/input.json` write at session-setup time, the Initial Brief
  modal hydrates correctly via the existing synthesis path even if the
  push-CLI gap persists, because the synth uses `brief.md` (which DOES
  push) and the proposed change additionally stamps `system_source:
  "recorded"` once a future push fixes the gap.

## Test plan

- [ ] Unit test in `tests/orchestrator/test_session_setup.py`: spin up
  a fresh session-dir, verify `inputs/input.json` exists with
  `system_source: "recorded"`, `pieces.brief` matches the run's brief,
  and `pieces.system` is non-empty.
- [ ] Unit test in `tests/orchestrator/test_call.py`: assert
  `_derive_turn_key(agent_label="claude", phase="phase0", label="phase0-r2-claude")`
  returns `"phase0_round2_claude"` (today returns `"phase0_claude"`).
- [ ] Unit test in `tests/ui/test_aggregator.py`: feed two
  `turn_inputs` events for the same agent at phase 0 rounds 1 and 2;
  assert both `inputs/phase0_round1_<agent>.json` and
  `inputs/phase0_round2_<agent>.json` exist on disk independently.
- [ ] Integration test in `tests/ui/test_server.py`: against a
  fixture session-dir with a persisted `inputs/input.json`, hit
  `GET /api/runs/<id>/inputs/input` and assert response carries
  `system_source: "recorded"` and non-empty `pieces.brief`.
- [ ] Smoke test: fire a fresh `/dual-research-run`, open the Initial
  Brief modal in the live UI, confirm the System Prompt and User Prompt
  sections render without the "agent default" caveat.
- [ ] Manual replay: re-push the anchor run
  `20260521-010637-dvs-backend-language-choice` after the change,
  confirm `inputs/input.json` lands in `session_files`, and the modal
  hydrates from the recorded bundle.

## Risks

- **No backfill for past runs.** Runs that pre-date this fix have no
  `inputs/input.json` row; their Initial Brief modal will continue
  hydrating via the synth path with `system_source: "agent-default"`.
  This is the documented "older run" caveat the UI already renders
  (per spec 0085), so it's not a regression — only the new behaviour
  is "older runs explicitly flagged; new runs accurate". Backfilling
  is feasible (re-derive from each run's `brief.md` + push) but
  intentionally deferred.
- **Last-write-wins on disk for unmigrated runs.** Until change (2)
  ships in concert with (1), per-round Phase-0 bundles continue to
  overwrite. The modal fix in (1) is independent of (2) — both can
  land in the same patch, but (1) alone restores the Initial Brief
  case, which is B05's reported failure.
- **Rollback strategy.** Change (1) is purely additive — removing the
  session-setup write yields the previous synth-fallback behaviour.
  Change (2) modifies a key derivation; revert restores the
  last-write-wins shape. No data loss in either direction because
  bundles are append-only-immutable (spec 0033).
- **Compatibility with 0145.** The canonical prompt-piece registry
  will rename / restructure `pieces` keys (system → `system_prompt`,
  brief → `user_prompt`, etc.). This spec preserves the existing
  8-key shape so 0145 lands cleanly on top: rename pass + per-piece
  metadata, with non-empty content guaranteed at the entry point.

## Open questions

- Should `inputs/input.json`'s `pieces.system` use the placeholder
  variant (current `preflight_input_bundle` behaviour with
  `_placeholder("brief")` substituted in the system body) or inline
  the real brief text into the system slot? The placeholder variant
  matches what the agent actually saw at call time (system was cached
  with the brief inlined via prompt caching); the literal variant
  matches what the user expects to read. Default to the placeholder
  variant for consistency with the per-turn bundles, but flag for
  decision in review.
