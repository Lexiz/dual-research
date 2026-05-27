---
kind: dev
spec: "0228"
slug: emit-protocol-violation-on-invalid-op
title: "Emit ProtocolViolation when an op is silently dropped for a state-machine reason; promote verifier invariant I4.4 from reporting to gating"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0225", "0227"]
complexity: M
created: 2026-05-27
queued_at: "2026-05-26T22:18:11Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0228 — Emit `ProtocolViolation` on state-machine-invalid ops; flip verifier I4.4 to gating

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0225 (verifier), 0227 (reclassification rule)
> **Bump:** MINOR — extends the conditions under which a first-class event fires AND promotes a verifier invariant from `reporting` to `gating`. Per CLAUDE.md "Contract-changing specs are not `bug`s" (the rule introduced by spec 0227), this is a contract amendment and MUST be a `new-feature`, not a `bug`.
> **Evidence:** cowork synthesis at `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md` §2.1, §3 Area 4 [NEW], §6 action 3 · failing run `runs/20260526-102321-backend-language-choice/phase2/round-02-claude.md` lines 230/236/242/248 · silent-drop site `src/dual_research/orchestrator/deep_research.py:482-483`.

---

## 1. Context

Run `20260526-102321-backend-language-choice` died during phase-2 round 2. claude (turning first that round) emitted `### RESOLVE` blocks for `D-plan-c-02`, `D-plan-c-04`, `D-plan-c-05`, and `Q-plan-c-01` — four items still in state `open` because openai had not yet ADDRESSed them that round. The four RESOLVE blocks are visible in the transcript at `runs/20260526-102321-backend-language-choice/phase2/round-02-claude.md:230`, `:236`, `:242`, and `:248`. None of them produced any orchestrator-side signal. The lifecycle handler at [src/dual_research/orchestrator/deep_research.py:482](src/dual_research/orchestrator/deep_research.py:482)–`:483` checks `if ent.current_state != State.ADDRESSED: continue` — a silent `continue` that drops the op without emitting any event, log line, or transition record. The reconstructed ledger then carried those four items as `open` indefinitely, phase 2 burned three more closeout rounds against unresolvable items, and the run died at `phase2-r5-claude turn_inputs`.

The cowork synthesis pinned this as the Bug-A root cause and explicitly rejected the originally-proposed "add `open → resolved` edge" remedy (§2.1 adjudication) on the grounds that it would reintroduce the self-report trust trap the 0114 state machine exists to prevent. The synthesis's recommended cure (§3 Area 4 [NEW]; §6 action 3) is to make the rejection observable: emit a `ProtocolViolation` event from every silent-drop site so the verifier — whose I4.4 invariant from [spec 0225](specs/0225-verifier-invariants.md) already turn-file ⇄ transcript diffs to catch exactly this case — can fire on it. With emission in place, I4.4 also flips from `reporting` to `gating`.

## 2. Proposed change

Two coupled changes in a single spec; the verifier flip is unsafe without the emission, and the emission is incomplete without the verifier flip.

### 2.1 — Emit `ProtocolViolation` from every silent-drop site in `apply_turn`

In [src/dual_research/orchestrator/deep_research.py:482](src/dual_research/orchestrator/deep_research.py:482)–`:483`, the documented RESOLVE-on-non-ADDRESSED rejection silently `continue`s. Siblings exist in the same `apply_turn` function and its helpers for: ADDRESS on non-`open`; ACKNOWLEDGE without a prior RESOLVE / wrong handshake half; WITHDRAW on a terminal state; and possibly other state-machine guards. Enumerate every `continue` inside `apply_turn` (and the helpers it calls) where the rejection reason is state-machine-derived, and replace each one with code that ALSO emits a `ProtocolViolation`. The ledger's existing behaviour — do not transition the item, do not record a transition — is preserved exactly; the only behaviour change is that the rejection is now logged as an event.

Identification rule: grep `src/dual_research/orchestrator/deep_research.py` and its `_apply_*` helpers for `continue` inside the per-block `elif isinstance(blk, …):` branches. For each `continue` whose preceding guard checks one of (`ent.current_state`, `ent.raiser`, `is_terminal(…)`, `ent.ack_proposed_by`), prepend a `ProtocolViolation` emission with the payload below. Pure parser-failure `continue`s (malformed block, missing required field) are NOT in scope here — those already emit `ParseError`-class events; only state-machine guards are touched.

The `ProtocolViolation` payload must express: op kind (`resolve`/`address`/`acknowledge`/`withdraw`/etc.); op target ID; actor; phase; round; current item state (or `null` if the item didn't exist when the op was applied); expected state(s) the guard required; one-line reason string. Check the live shape of `ProtocolViolation` in [src/dual_research/events/types.py](src/dual_research/events/types.py) first; if the existing dataclass cannot express that payload, extend it minimally (new fields with defaults so existing emit sites keep compiling). Do NOT speculatively extend — confirm a field is missing before adding it.

### 2.2 — Flip verifier I4.4 from `reporting` to `gating`

In [src/dual_research/contract/verifier.py](src/dual_research/contract/verifier.py), I4.4's severity declaration changes from `reporting` to `gating`. The check's logic — turn-file ⇄ transcript diff for ops present in the transcript but not in the ledger — is unchanged. Update the inline docstring / invariants table to reflect the new severity and to cite this spec as the activation point. The verifier's CLI exit code path (`exit 1` on any gating failure) automatically picks up the new gating call site without further changes.

The anchor-fixture baselines under [tests/fixtures/anchor-runs/](tests/fixtures/anchor-runs/) regenerate as part of this change. The dead reference fixture `20260526-102321-backend-language-choice` now shows I4.4 as a `gating` failure listing the four dropped RESOLVEs from claude round 2; the clean reference fixture `20260521-010637-dvs-backend-language-choice` is unaffected because no invalid ops exist on that run. The PR diff must include the regenerated `expected.json` files with a one-line PR comment that names this spec as the cause of the diff.

### 2.3 — Files touched (summary)

  - [src/dual_research/orchestrator/deep_research.py](src/dual_research/orchestrator/deep_research.py) — replace silent `continue`s in `apply_turn` (and its helpers) with `ProtocolViolation`-emitting blocks. Expected ~5–15 sites; the grep determines.
  - [src/dual_research/events/types.py](src/dual_research/events/types.py) — extend `ProtocolViolation` payload IFF the current shape cannot express the diagnostic in §2.1. Otherwise no change.
  - [src/dual_research/contract/verifier.py](src/dual_research/contract/verifier.py) — flip I4.4 severity from `reporting` to `gating`; update inline docstring.
  - [tests/orchestrator/test_deep_research.py](tests/orchestrator/test_deep_research.py) (or appropriate sibling) — new per-site unit tests + new replay test against the dead-reference round-02-claude transcript.
  - [tests/test_verifier.py](tests/test_verifier.py) — anchor-fixture `expected.json` regenerates for both reference runs; the dead-fixture baseline now lists I4.4 as a gating failure.
  - `CHANGELOG.md`, `pyproject.toml`, `src/dual_research/__init__.py` — MINOR bump per CLAUDE.md "Versioning and CHANGELOG".

## 3. User stories & acceptance criteria

Non-UI spec — user-story / BDD section is optional per the template. Acceptance is encoded by the gating checks in §6 Test plan; the user-visible "outcome" of this spec is that protocol violations now appear in the dashboard event stream and the verifier CLI exit-codes on them.

## 4. Data / Schema deltas

No schema impact unless §2.1's payload extension lands. If it does: the `ProtocolViolation` dataclass in [src/dual_research/events/types.py](src/dual_research/events/types.py) gains 1–4 new fields with defaults; existing serialised events remain readable because new fields default. No migration of historical event sidecars (`dashboard/events/NNNN.jsonl`) is required — historical events keep their old shape; the new fields appear only on events emitted after this spec lands.

## 5. Out of scope

  - **Addressee-obligation invariant (I2.4 / cowork synthesis action 6).** That spec stops an agent from emitting AGREED while open items are addressed at it. It is the natural next spec in the sequence and will be drafted post-merge of 0228 (deferred to a follow-up dev spec — provisionally `0229-addressee-obligation-invariant`).
  - **Rewriting the lifecycle state machine.** No new states, no new edges. Per cowork synthesis §2.1: do NOT add `open → resolved` — that would reintroduce the self-report trust trap the existing machine exists to prevent. The state machine is the 0114 contract; this spec just makes its violations observable.
  - **Auto-coercing RESOLVE-from-open into WITHDRAW.** The synthesis flagged this as a future option; not part of this spec. For now the op is rejected with a `ProtocolViolation`; any coercion behaviour is a separate decision (deferred — to be raised in a follow-up spec only if downstream data shows the rejection alone is insufficient).
  - **Parser-error / malformed-block rejection.** Those already emit `ParseError`-class events; this spec only touches state-machine guards.
  - **UI surfacing of `ProtocolViolation` in the dashboard.** Out of scope; the event lands in `dashboard/events/NNNN.jsonl` and the verifier CLI; dedicated dashboard rendering is a separate UI spec to be drafted if/when needed.

## 6. Test plan

  - [ ] `uv run pytest tests/ -q` passes.
  - [ ] Per-site unit test for each silent-drop site identified in §2.1: construct a minimal phase state, apply a turn containing one state-machine-invalid op of the relevant kind, assert exactly one `ProtocolViolation` event is emitted with the expected payload (op kind, target ID, actor, current state, expected state, reason), AND the item state in the ledger is unchanged.
  - [ ] New replay-style test loads `tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/phase2/round-02-claude.md`, feeds it through `apply_turn` against a fresh phase state seeded with the round-01 ledger, and asserts exactly four `ProtocolViolation` events for `D-plan-c-02` / `D-plan-c-04` / `D-plan-c-05` / `Q-plan-c-01`, each carrying `current_state="open"` and `expected_state="addressed"`.
  - [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` exits 0 (clean reference fixture unaffected — no invalid ops exist on this run).
  - [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/` exits non-zero, and the gating failure list now includes I4.4 naming the four dropped RESOLVEs explicitly.
  - [ ] Regenerated `expected.json` baselines under `tests/fixtures/anchor-runs/*/expected.json` are checked into the PR with a one-line comment naming this spec as the source of the diff.

## 7. Risks

  - **Missing a silent-drop site.** The grep in §2.1 enumerates by structural pattern (state-machine guard immediately followed by `continue` in a per-block branch). Mitigation: after fixing each identified site, re-grep with the same pattern and confirm zero remaining hits. A site missed here is a latent bug, not an immediate regression — the verifier's turn-file ⇄ transcript diff will still catch it once I4.4 is gating, and a follow-up spec can close the gap.
  - **`ProtocolViolation` payload extension breaks downstream consumers.** Mitigation: extend with `field(default=…)` so the dataclass remains constructable from existing call sites; check the dashboard event renderer (if it reads `ProtocolViolation`) to confirm it gracefully ignores unknown fields. If the renderer crashes on unknown fields, that's a separate bug to fix here or split out.
  - **Verifier flip surfaces dormant violations in other historical runs.** With I4.4 now gating, any historical run that contained invalid ops will start failing the verifier. The two checked-in anchor fixtures are the only ones that matter for CI (the clean one stays clean; the dead one was already failing on other invariants). Other historical runs are diagnostic-only and not part of the CI gate — surfacing the violations there is the intended outcome.
  - **Replay test flakiness from transcript-parse evolution.** The replay test depends on the parser reading the exact dead-reference transcript shape. Mitigation: pin the transcript as a checked-in fixture under `tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/` and treat any future parser change as a test-update obligation, not a flake.
