# Handover — Spec 0140 — Phase 4 deadlock: draft extractor + escape-valve breadth (v1.9.1)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#162](https://github.com/Lexiz/dual-research/pull/162) (merged, squash, branch deleted)
- **Spec:** [specs/0140-phase4-deadlock-extractor-and-escape-valve.md](../specs/0140-phase4-deadlock-extractor-and-escape-valve.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog rows fixed:** B12 (extractor truncation) → B13 (escape valve too narrow) → B07 (Phase 4 hard-cap deadlock)
- **Version:** `1.9.0 → 1.9.1` (PATCH — bug fix only)

## What landed

One causal chain fixed in three surgical edits, no new event types, no protocol surface changes.

### Edit 1 — Inclusive draft extractor at the Phase 4 drafter-revision call site

[`src/dual_research/orchestrator/dr_run.py`](../src/dual_research/orchestrator/dr_run.py) — imports + the call site inside `_drive_interaction_phase` swap from `extract_revised_draft` (strict; truncates at the first `^##\s+\S` heading) to `extract_revised_draft_inclusive` (sibling-tolerant; absorbs `##` headings that are NOT in the protocol allowlist). Anchor-run shape: `## Revised draft` was followed by `## 1. Executive Summary`, `## 2. Version Baseline`, `## 3. Tier 1 Pass/Fail`, `## 4. Ranked Candidates` — pre-fix the extractor returned a 7-line preamble (76 bytes on disk); post-fix it returns the full body (29 502 bytes for round 7).

### Edit 2 — Extend `_PROTOCOL_TOP_HEADINGS` with Spec 0114 v2 sentinels

[`src/dual_research/protocol/parse.py`](../src/dual_research/protocol/parse.py) — added `stance`, `addressing items raised against me`, `ratifying my own items`, `new items i'm raising`, `phase artifact`, `status`, `closeout constraints` to the allowlist, with a comment cross-referencing `contract/markers.py` so future Spec 0114 sentinel additions stay in sync. `## Revised draft` itself is deliberately absent — the extractor's start anchor matches it via `_REVISED_DRAFT_HEADING_RE`, and including it here would cause a same-section re-match.

### Edit 3 — Widen the Spec 0137 escape valve for terminal-ledger one-agent-AGREED deadlocks

[`src/dual_research/orchestrator/dr_run.py::_drive_interaction_phase`](../src/dual_research/orchestrator/dr_run.py) (production async path) + [`src/dual_research/orchestrator/deep_research.py::DeepResearchPhase.run`](../src/dual_research/orchestrator/deep_research.py) (sync mirror used by the test harness). The escape valve now fires when:

- **`both_agreed`** + terminal ledger (original 0137 form — hash drift), **or**
- **`one_agreed`** (XOR) + terminal ledger + `round_no >= caps.soft` (new — covers the anchor-run shape where the reviewer was looking at a stub draft and couldn't honestly ratify).

The transcript line gains a `trigger` field (`both_agreed` / `one_agreed_terminal`) so replay can tell the two paths apart without adding a new event type. The published `ArtifactCanonicallyPromoted` event schema is unchanged; the UI's "converged via artifact promotion" badge applies as-is.

## Files touched

- `src/dual_research/orchestrator/dr_run.py` — extractor swap + escape-valve widening
- `src/dual_research/orchestrator/deep_research.py` — mirror widening in the sync path
- `src/dual_research/protocol/parse.py` — extend `_PROTOCOL_TOP_HEADINGS`
- `tests/protocol/test_parse.py` — anchor-run shape, each Spec 0114 sentinel as a terminator, grep regression, anchor-run replay
- `tests/orchestrator/test_deep_research.py` — widened escape valve at and below the soft cap; existing both-AGREED hash-drift test unchanged
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.9.0 → 1.9.1`
- `CHANGELOG.md` — `[1.9.1]` entry

## Tests

```
1228 passed in 10.07s
```

New cases added by this PR:

- `test_extract_revised_draft_inclusive_retains_numbered_sub_sections` — anchor-run shape; asserts `## 1. Executive Summary` through `## 4. Ranked Candidates` are in the body, terminator (`## Phase artifact`) and trailing artifact are not.
- `test_extract_revised_draft_inclusive_terminates_at_spec_0114_sentinel` — asserts `## Status` terminates the body.
- `test_extract_revised_draft_inclusive_terminates_at_each_0114_sentinel` — loops every newly-added sentinel; each must terminate.
- `test_dr_run_does_not_import_strict_extractor` — grep regression on `dr_run.py`.
- `test_extract_revised_draft_inclusive_replays_anchor_run_round07` — on-disk replay against `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md`; asserts body ≥ 25 000 chars and contains literal `## 4. Ranked Candidates`. Skips when the run directory is absent so CI on fresh clones stays green.
- `test_artifact_promotion_does_not_fire_when_only_one_agreed_below_soft_cap` — replaces the old 0137 negative test; uses `soft=5, hard=4` so every round is strictly below the soft-cap gate; asserts the widening does NOT fire and the loop exits via hard cap.
- `test_artifact_promotion_fires_when_one_agreed_terminal_past_soft_cap` — new; `soft=2, hard=8`; one-agent AGREED at round 2 fires the widening; `final_round=2`, `via_artifact_promotion=True`, one `ArtifactCanonicallyPromoted` event with `phase="phase2"` and `round=2`.

## Deploy

```
fly deploy
…
✔ [1/2] Machine 2870612f037368 is now in a good state
✔ [2/2] Machine 148ee320f427e8 is now in a good state
```

Live: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.9.1","backend":"supabase"}`.

## Known follow-ups

- **B12 path-3 (retroactive salvage).** Out of scope per spec §4. The anchor run's `round-07-claude.md` still holds 312 lines of usable draft body; lines 47–312 could be lifted into a clean `final.md` by a one-shot script. Not a structural concern; documented for completeness.
- **Closeout-urge predicate** still requires both-AGREED. The widening sits before the `if rr.closeout_event is not None:` branch, so a one-agent-AGREED + terminal-ledger run no longer reaches closeout in any case — the precedence is correct as-is, but if a future spec widens closeout the order will need a second look.
- **Telemetry semantics.** `via_artifact_promotion=True` now covers both the original hash-drift case and the new one-agent-AGREED late-round case. The transcript-side `trigger` discriminator lives only on the transcript line, not on the event; if the UI needs a finer split later, it can read the transcript.
- **Spec 0114 sentinel drift.** Comment in `parse.py` cross-references `contract/markers.py`; both files live under the protocol/contract boundary. If a future Spec 0114 amendment adds a new section sentinel, the allowlist must be extended in lockstep — no automated guard.
- **End-to-end smoke run.** The on-server health check is green; firing a fresh `/dual-research-run` on a brief known to drift in Phase 4 (to confirm the run converges at natural agreement rather than hard-cap) is left as a user-side smoke since it costs ~$10 of LLM spend and ~15 minutes. Spec §5 lists it as a manual test.
