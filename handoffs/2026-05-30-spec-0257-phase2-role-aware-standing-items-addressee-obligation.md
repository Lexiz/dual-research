---
spec: "0257"
date: 2026-05-30
version: "1.66.0"
pr: "https://github.com/Lexiz/dual-research/pull/297"
kind: post-deploy
---

# Spec 0257 — role-aware standing-items surface (addressee must ADDRESS, raiser must not self-resolve)

Shipped in **v1.66.0** (PR [#297](https://github.com/Lexiz/dual-research/pull/297), deploy run
[26694165409](https://github.com/Lexiz/dual-research/actions/runs/26694165409)
green; homepage smoke 200).

## What landed

The per-round standing-items block agents see in phase 2 / phase 4 was
**role-blind** — every non-terminal item rendered identically to both
agents, inviting the raiser to ADDRESS/RESOLVE its own open items and
letting the addressee declare AGREED without ADDRESSing anything. That
single surface produced the 50 phase-2 ownership violations in run
`20260530-175809` (converged `via_ghost_cap`, never genuine resolution).

- **§2.1 — `format_role_aware_standing_items`** (`orchestrator/deep_research.py`)
  partitions the live contract ledger by `(role, lifecycle-state)`:
  (1) raised-against-you → *you are the ADDRESSEE, you MUST `### ADDRESS`*;
  (2) raised-by-you-still-open → *only `### WITHDRAW`, no self-address /
  no resolve-from-open*; (3) raised-by-you-ADDRESSED → *ready to ratify:
  RESOLVE / ACKNOWLEDGE / counter*, with `addressed_by` surfaced;
  (4) addressed-by-you-awaiting-raiser → informational. Both live render
  sites — `dr_run._format_standing_items` and
  `DeepResearchPhase._build_standing_items_text` — route through the one
  shared formatter (no diverging surface).
- **§2.2 — role callouts in the live `_v2` prompt builders.**
  `_ADDRESS_RESOLVE_ROLE_CALLOUT` (symmetric raiser/addressee) renders
  above `## Status` in `plan_negotiation_round1_prompt_v2` /
  `plan_negotiation_round_n_prompt_v2`; a **distinct**
  `_ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4` (asymmetric drafter/reviewer
  wording — cowork correction 3, not assumed-symmetric) renders in
  `review_round1_prompt_v2` / `review_round_n_prompt_v2`.

## Reconcile correction — retargeted off dead code onto the live path

The queued spec's §2 citations were **all dead** since the spec-0118 v2
rewrite (unreachable from `run_dr_phase2` / `run_dr_phase4`). The
reconciler reported "clean" because the file:line locations literally
exist; only a call-graph read caught it. Retarget map:

| Spec cited (DEAD) | Live surface (used) |
|---|---|
| `ledger/prompt.py:build_standing_items_section` | `deep_research.format_role_aware_standing_items` via `dr_run._format_standing_items` |
| new `LedgerState.ratifiable_entries` (`current_status == "addressed"`) | inline filter on contract `LedgerEntryV2` (`State.ADDRESSED`); legacy `LedgerState` has no `addressed` status |
| `negotiation_round1_prompt` / `negotiation_turn_prompt` | `plan_negotiation_round1_prompt_v2` / `plan_negotiation_round_n_prompt_v2` |
| `review_turn_prompt` | `review_round1_prompt_v2` / `review_round_n_prompt_v2` |

Decision was the user's (retarget in-flight rather than halt/re-queue).
A durable spec-authoring rule was added to `CLAUDE.md` to prevent the
class of bug: confirm a cited function is reachable from the live entry
points before citing it.

## Tests

- **§6.1 prompt-content + unit checks (live surface)** — three role
  groups with role-correct substrings; antipodal-absence of the legacy
  role-blind phrasing; ratifiable group = addressed-and-raised-by-agent
  only; phase-2 callout in both `_v2` builders + absent from phase 4;
  phase-4 callout distinct and absent from phase 2 (correction-3 guard).
- **§6.2 behavioural replay harness (CI floor)** at
  `tests/test_spec_0257_role_aware_standing_items.py` — vendored run
  `20260530-175809` phase-2/phase-4 turns (`tests/fixtures/spec_0257/`)
  replayed through the **real** `DeepResearchPhase.apply_turn` path + the
  live `dr_run._format_standing_items` entry point. Asserts each agent
  receives the role-correct grouping and that the captured artifact
  reproduces all three ownership-violation classes (spec-0238 discipline).
  Does NOT assert "zero violations" on the vendored turns — those are
  frozen pre-fix outputs that necessarily re-emit the violations; zeroing
  them is the live re-run (§6.3), not a CI gate.
- **Phase-4 measurement (non-gating):** vendored phase-4
  `raiser_self_address` count = **0** for this run. (The 7× was a
  *different* run, `20260529-164844`.) No `0257.2` carve-out triggered
  by this fixture.
- Full suite: **2465 passed**.

## Deferred during implementation

- **Delete the dead legacy standing-items surface.** `build_standing_items_section`
  ([`src/dual_research/ledger/prompt.py`](../src/dual_research/ledger/prompt.py))
  and its only callers, the legacy `orchestrator/phase2.py` /
  `orchestrator/phase4.py` runners, have been unreachable from
  `run_dr_phase2` / `run_dr_phase4` since the spec-0118 v2 rewrite. This
  spec flagged the function for deletion (a `.. deprecated:: spec 0257`
  note was added) but did NOT remove it, to keep the diff focused on the
  live fix. A follow-up should delete `build_standing_items_section`, the
  legacy phase2/phase4 runners, and their now-orphaned tests. This is a
  "should but didn't" carve-out of 0257.

- **Live acceptance re-run (§6.3) not executed here.** The spec's PR
  acceptance evidence is a real `backend-language-choice` re-run scored
  via `/dr-run-assess`, expected to show phase-2 `via_genuine_resolution`
  with zero `raiser_self_address` / `resolve_from_non_addressed` /
  `agreed_with_open_addressed_items`. E2E runs must launch from a plain
  Terminal.app session (CLAUDE.md / spec 0243) — they cannot run from a
  Claude Code surface (the CLI guard refuses). The re-run is therefore
  deferred to a manual launch; until it lands, the phase-2 behavioural
  improvement is verified deterministically by §6.2 (rendered surface +
  violation-path) but not yet confirmed on live LLM behaviour.
