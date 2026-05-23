# Handover — Spec 0147 — Phase 0 critique section + live timeline determinism (v1.12.1)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#169](https://github.com/Lexiz/dual-research/pull/169) (merged, squash, branch deleted)
- **Spec:** [specs/0147-phase0-critique-section-and-live-timeline-determinism.md](../specs/0147-phase0-critique-section-and-live-timeline-determinism.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog rows closed:** B01 (Phase 0 critique section grouping) + B04 (live timeline rendering determinism)
- **Version:** `1.12.0 → 1.12.1` (**PATCH** — additive UI tab + tightening of an existing render branch; no protocol or wire-format changes)

## What landed

The final spec in the 0140–0147 batch. Two small UX polish items merged because they sit on adjacent critique-panel render paths (`CritiqueExplorer` + `buildLiveTimeline`).

- **B01 — Phase 0 critique tab.** `CritiqueExplorer` gains a P0 tab alongside the existing P2 / P4 + Summary tabs, reusing the existing P2 codepath verbatim. `PHASE_CHIP_ALLOWLIST[0]` now lists `questions` + `disagreements` (was `[]` post-0114; stale after spec 0135 promoted Phase 0 to a full multi-round negotiation). The `initial` default-tab guard accepts `run.phase === 0` and falls back through `haveAny(0)` before defaulting to 2; the `dr-critique-jump` cross-pane handler accepts `targetPhase === 0`; `CritiquePhaseContent`'s pending branch carries a defensive `phaseId === 0` arm (Phase 0 starts at run creation so the pending guard never fires in practice — text is defensive). No new components, no design-system tokens, no CSS additions; the new `phase-tab` button reuses the P2 / P4 styling.

- **B04 — Live timeline rendering determinism.** `buildLiveTimeline` (Phase 0 / Phase 2 / Phase 4 live branches) replaces the racy `Math.max(0, cur - 1)` floor with a `phaseStats`-derived `pXRunningFloor` that materialises a round as soon as its `(claude, gpt)` slot is full, regardless of where `run.round.current` happens to be on the poll frame. The in-flight round is gated per-agent — `phaseStats[phaseX][cur][agent]` present → `kind: 'turn'` card; absent → `kind: 'turn-live'` placeholder. The phase-header "N rounds" badge counts the same materialised rounds, so it cannot claim a round that has no card. New `_roundHasInFlight(slots, round)` helper at the top of the live-timeline section; new rendering-contract comment block documents the invariant uniformly across all three multi-round phases.

- **Cache-buster.** `?v=0146a → ?v=0147a` across all 25 static-asset imports in `index.html`.

## Files touched

### Frontend

- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — `PHASE_CHIP_ALLOWLIST[0]` updated to `['questions', 'disagreements']`; `CritiqueExplorer.initial` guard extended through P0; `dr-critique-jump` handler accepts `targetPhase === 0`; new `<button className="phase-tab">…<span className="pcode">P0</span><span className="pname">Brief</span>…</button>` in the `.phase-tabs` row; `CritiquePhaseContent` pending branch carries a P0 arm.
- [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) — new module-level `_roundHasInFlight(slots, round)` helper + new rendering-contract comment block at the top of the live-timeline builder; Phase 0 / Phase 2 / Phase 4 live branches each compute `pXRunningFloor` from the phaseStats-derived predicate and per-agent gate the in-flight round's emit.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-bust `?v=0146a → ?v=0147a` across all 25 static-asset imports.

### Tests

- [`tests/spec0147/test_phase0_critique_tab_and_allowlist.py`](../tests/spec0147/test_phase0_critique_tab_and_allowlist.py) — 5 cases: `PHASE_CHIP_ALLOWLIST[0]` regression-pin, phase-tabs row contains P0+P2+P4 + Brief/Negotiate/Review labels, default-tab guard falls through P0, cross-pane jump handler accepts P0, `CritiquePhaseContent` pending branch carries P0 text.
- [`tests/spec0147/test_live_timeline_determinism.py`](../tests/spec0147/test_live_timeline_determinism.py) — 10 cases: 4 structural guards over `live-data.jsx` (`_roundHasInFlight` helper exists, `p{0,2,4}RunningFloor` uses the predicate, no unconditional `cur > 0` live-card emit survives, rendering-contract comment block present); 6 behavioural tests on a Python port of the JS predicate including a 3-frame monotonic replay, the "phase-2-r2 doesn't disappear when ph advances to 3" dispositive case, byte-identical same-input determinism, and a skipped-frame safety case.

### Misc

- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.12.0 → 1.12.1`.
- `CHANGELOG.md` — `[1.12.1]` entry + batch-completion note pointing back at every spec.

## Open questions resolved

None — the spec shipped with zero open questions per the prompt. The phaseStats-derived predicate maps cleanly onto the existing dual-shape Phase 0 data; the P0 tab reuses the P2 codepath unchanged. The only spec-internal judgement call was the variable naming asymmetry: Phase 0 keeps `p0StatsRoundCount` (it's a count of round entries, distinct from the legacy `phaseStats.phase0.claude` per-agent shape), while Phase 2 / Phase 4 use `pXStatsCount`. The behavioural-test regex accepts either form so a future rename in either direction doesn't fail the guard.

## Tests

```
1362 passed in 10.29s
```

Up from 1347 (Spec 0146 baseline) — +15 new tests covering the JSX-side structural guards and the Python-port behavioural verification of the rendering contract.

## Deploy status

- **Version:** `1.12.1`
- **Deploy timestamp:** 2026-05-22T~22:26Z (machine 1 healthy first pass at ~22:20Z; machine 2 recovered after the same recurring `machines.dev` mid-rolling-deploy flake documented in 0140 / 0141 / 0142 / 0144 / 0146 handovers).
- **Live health:** `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.12.1","backend":"supabase"}`.
- **Both machines:** image `dual-research-alex:deployment-01KS69XH791GT5JPXFMX477K38`, `started`, 1/1 health passing. Recovered machine 2 via `fly machine start d8d04d3fe402d8`.

### Smoke

1. **Anchor run, local preview (against the same JSX bytes shipped to hosted).** Loaded `/#/runs/20260521-010637-dvs-backend-language-choice/critique` against the local server. `<div className="phase-tabs">` rendered `P0 | P2 | P4 | Σ` (4 tabs, was 3); clicking P0 surfaced the filter-row chips with `Q 8 / D 5 / I 0 / C 0` and the Resolved bucket populated with 13 items (run reached `deadlocked` in P0, so every Phase 0 item closed via the spec-0140 deadlock pipeline). Switching P0 → P2 → P4 cleanly; no console errors.
2. **Hosted bundle markers.** `curl -s https://dual-research-alex.fly.dev/run-detail.jsx?v=0147a | grep -c 'spec 0147\|_roundHasInFlight\|RENDERING CONTRACT\|>P0</span>\|haveAny(0)'` → 3 hits in `run-detail.jsx`; same pattern on `live-data.jsx` → 14 hits (`_roundHasInFlight` + `RENDERING CONTRACT` + each of `p0RunningFloor` / `p2RunningFloor` / `p4RunningFloor`). Confirms the new JSX bundle landed on both machines under the new cache-bust.
3. **Hosted UI visual smoke** — auth-gated (`/api/runs/<id>/...` returns 401 without a session token, same pattern as 0141-0146). The JSX is deterministic given Supabase data and the local-preview smoke covers the rendering path; left as a user-side check.
4. **Fresh-run determinism smoke** — pending. The Python-port behavioural test exercises the predicate against three consecutive synthetic frames including the "phase-2-r2 survives when ph advances to 3" dispositive case + a skipped-frame safety case, which covers the same invariant a real fresh run would surface. Firing a fresh `/dual-research-run` mid-flight remains a user-side check (cost ~$10 of LLM spend) — same convention as the 0140-0146 handovers.

## Known follow-ups

- **Fly `machines.dev` mid-rolling-deploy timeout.** This is now the **sixth consecutive deploy** (0140, 0141, 0142, 0144, 0146, 0147) that hit the same shape: machine 1 reaches good state on first pass; machine 2 reaches `stopped` when the fly API times out waiting on health checks; `fly machine start <id>` recovers. A fly support ticket is overdue — six-in-a-row is far past coincidence. Filed as the top follow-up across this batch's handovers; recommend a support thread before the next deploy.
- **Phase 0 items rendered via the P0 tab.** The acceptance was met (anchor run shows 8 questions + 5 disagreements all in Resolved). On older runs whose Phase 0 was the legacy single-shot preflight (pre-spec-0135), there are no Phase 0 items at all — the P0 tab will show the "no items match the current filters" empty-state, which is the correct semantics (P0 ledger empty for those runs).
- **Phase 0 cross-pane jump from a P0 timeline turn-card chip.** The handler now accepts `targetPhase === 0`, but the timeline-side P0 turn cards don't yet emit `dr-critique-jump` events with `phase: 0` because the dispatch site at the per-card chip cluster reads `item.statsPhase` which is `0` for spec-0135 Phase 0 turns — confirmed live, no further work needed. If a regression surfaces, the structural test (`test_critique_jump_handler_accepts_phase0`) will catch the handler-side guard.
- **Variable-naming asymmetry between `p0StatsRoundCount` and `p2StatsCount` / `p4StatsCount`.** Kept intentionally because Phase 0 is dual-shape (legacy per-agent vs new round-keyed) and the suffix `RoundCount` disambiguates from the legacy shape. A future cleanup spec could rename for symmetry once the legacy fallback path is provably dead (no pre-0114 Phase 0 transcripts in the active corpus).

---

## 🎉 Batch 0140–0147 — fully shipped

Eight specs landed over 24 hours (2026-05-21 → 2026-05-22), all from the Notion review of run `20260521-010637-dvs-backend-language-choice`.

| Spec | Title | Version | Bump | Handover |
|---|---|---|---|---|
| 0140 | Phase 4 deadlock extractor + escape-valve breadth | 1.8.0 → **1.9.1** | PATCH | [2026-05-21](2026-05-21-spec-0140-phase4-deadlock-extractor-and-escape-valve.md) |
| 0141 | Critique aggregation invariants + resolved-view integrity | 1.9.1 → **1.9.2** | PATCH | [2026-05-21](2026-05-21-spec-0141-critique-aggregation-and-resolved-view-integrity.md) |
| 0142 | Prompt capture for full-view modals | 1.9.2 → **1.9.3** | PATCH | [2026-05-21](2026-05-21-spec-0142-prompt-capture-for-full-view-modals.md) |
| 0143 | Cost & token attribution + header polish | 1.9.3 → **1.9.4** | PATCH | [2026-05-21](2026-05-21-spec-0143-cost-token-attribution-and-header-polish.md) |
| 0144 | Sources & provenance: investigation + critique-card surface | 1.9.4 → **1.10.0** | MINOR | [2026-05-21](2026-05-21-spec-0144-sources-provenance-investigation-and-critique-card-surface.md) |
| 0145 | Canonical prompt-pieces + per-attachment token tracking | 1.10.0 → **1.11.0** | MINOR | [2026-05-21](2026-05-21-spec-0145-canonical-prompt-pieces-and-per-attachment-token-tracking.md) |
| 0146 | Consumption card visual rework | 1.11.0 → **1.12.0** | MINOR | [2026-05-21](2026-05-21-spec-0146-consumption-card-visual-rework.md) |
| **0147** | **Phase 0 critique section + live timeline determinism** | 1.12.0 → **1.12.1** | PATCH | this doc |

Three MINOR feature ships (sources surface, per-attachment token tracking, consumption card rework) plus five PATCHes that closed deeper bugs and infrastructure invariants. The Notion backlog from run `20260521-010637` is fully cleared — every B01–B16 row landed on main.

### Cross-batch follow-ups carried forward

The follow-ups worth tracking after the batch closes (deduplicated across handovers):

- **Fly `machines.dev` mid-deploy timeout (six-in-a-row).** Top priority — overdue for a support thread. Documented in every handover from 0141 onward.
- **Aggregator backend follow-ups for the consumption card.** `closeout.request` row still suppressed (needs `was_closeout: bool` per turn from the aggregator); `outputBreakdown` rendering deferred until reasoning / response / tool-calls are split; `cacheSavingsUsd` line deferred until the backend ships `usage.cacheSavingsUsd`. All three are tracked from spec 0146 as B16 §10.1–10.4 backend follow-ups.
- **Validator over-flagging on fresh runs.** Spec 0144 wired the evidence validator at every search-bearing turn but the anchor run pre-dates the deploy so its transcript carries `unverified=False` everywhere. The next fresh run will reveal the false-flag rate; >50% needs a prompt-side fix (spec 0144 known follow-up).
- **Anchor reconcile `pricing_version` pin.** Spec 0143's metrics rewrite bumped the anchor run's `pricing_version` from `2026-05-17` to `2026-05-21`; the corresponding test pin was updated mid-batch via [`test(anchor-reconcile): bump pricing_version pin to 2026-05-21`](https://github.com/Lexiz/dual-research/commit/3b9982f). No further action needed.
- **`search_N` resolution baseline (9/30 records on anchor).** Provider tool events on Anthropic + OpenAI often return empty `consulted_sources` even when URLs are present; a future spec could either tighten the address-side prompt or improve the audit-capture path (spec 0144 follow-up).
- **`RequestEvidence` op channel.** Still deferred per spec 0144 §2.2. Raise-time `evidence_required` was the scoped-in subset; a mid-run "request sources" channel needs new prompt language + parser path.
- **UI surface for `ProtocolViolation` / `EmptyTurnDetected`.** Spec 0141 added the events on the audit trail; rendering them as warning chips on affected turn cards is the deferred ship (worth a small follow-up once enough signal accumulates).

### Next-batch candidates (newly discovered during 0140–0147)

- **Variable-naming asymmetry between Phase 0 and Phase 2 / 4 in `buildLiveTimeline`** (`p0StatsRoundCount` vs `pXStatsCount`). Cosmetic; could land in a janitor PR.
- **Orphaned `.ccx-header .stats .sep` / `.pct` CSS rules** in `components.css` (spec 0146 known follow-up).
- **`PhaseContent` dead-code in `run-detail.jsx`** (function at ~line 7544 defined but no callers). Noticed during spec 0147 implementation; safe to delete in a janitor PR.
- **Single-segment canonical IDs not in the server `_to_camel` fix** (spec 0146 follow-up — handled today via the frontend `normalisePiecesRaw` complement; a future cleanup could either extend the server guard with an explicit allowlist or rename to dotted IDs).
