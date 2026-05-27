---
kind: dev
spec: "0229"
slug: addressee-obligation-invariant
title: "Enforce addressee-obligation: emit ProtocolViolation on AGREED with open addressed-at-me items; surface those items in closeout requests; promote verifier I2.4 from reporting to gating; codify the carve-out-disposition convention"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: "1.48.0"
status: queued
depends_on: ["0225", "0227", "0228"]
complexity: M
created: 2026-05-27
queued_at: "2026-05-26T23:20:50Z"
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

# Spec 0229 — Enforce addressee-obligation invariant + codify carve-out-disposition convention

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0225 (verifier), 0227 (reclassification rule), 0228 (ProtocolViolation infra + I4.4 gating)
> **Bump:** MINOR — per [CLAUDE.md](CLAUDE.md) "Contract-changing specs are not `bug`s" rule (modifies the negotiation contract, extends a first-class event with a new code, promotes a gating invariant, adds a CLAUDE.md process rule).
> **Evidence:** Cowork synthesis `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md` §6 action 6; failing run `runs/20260526-102321-backend-language-choice/phase2/round-02-openai.md`.

---

## 1. Context

This is the final stabilisation spec from the Cowork logic-cutoff synthesis. Spec 0228 (just shipped, v1.47.0) surfaced *one* side of the 20260526-102321-backend-language-choice failure — claude's RESOLVE-from-open ops on `D-plan-c-02 / D-plan-c-04 / D-plan-c-05 / Q-plan-c-01` now emit a `ProtocolViolation(resolve_from_non_addressed)` instead of being silently dropped at [src/dual_research/orchestrator/deep_research.py:482](src/dual_research/orchestrator/deep_research.py:482). But the deeper bug remains: **nothing in the protocol compels openai to ADDRESS items addressed at it before it can emit AGREED.** Openai's only recourse today is ghost-cap, which buries the raiser's items as `capped` — a workaround, not a fix.

The cure is the **addressee-obligation** invariant — synthesis §3 Area 2 [NEW]: "an agent may not emit `AGREED` while `open` items addressed *at it* remain un-ADDRESSED." Two layers ship together: the closeout-request prompt builder at [src/dual_research/orchestrator/deep_research.py:286](src/dual_research/orchestrator/deep_research.py:286) currently filters items to `ent.raiser == agent` (only items THIS agent raised), excluding exactly the items the addressee needs to be reminded about; and the orchestrator never demotes a non-compliant AGREED at runtime. Verifier I2.4 at [src/dual_research/contract/verifier.py:533-593](src/dual_research/contract/verifier.py:533) already checks the invariant — it just reports rather than gates. With this spec, the unified 0114 contract is fully enforced in code + CI.

### Source-artifact traceability

| source item | source quote/ref | spec section |
|---|---|---|
| Synthesis §6 action 6 ("addressee-obligation + RESOLVE-from-open coercion as one honest feature spec") | `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:281-283` | §2.1 + §2.2 (RESOLVE-from-open coercion → §5 deferred) |
| Synthesis §3 Area 2 [NEW] addressee-obligation | `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:194-195` | §2.1 + §2.2 |
| Synthesis §2.1 "Synthesis remedy (b)" | `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:106-107` | §2.1 + §2.2 |
| Verifier I2.4 currently reporting | `src/dual_research/contract/verifier.py:589-593` | §2.4 (severity flip) |
| Closeout-request filter excludes addressed-at-me items | `src/dual_research/orchestrator/deep_research.py:281-297` | §2.1 |
| ProtocolViolation event docstring (currently 8 codes) | `src/dual_research/events/types.py:503-549` | §2.3 (one new code) |
| Failing run round-02 openai never ADDRESSed claude's four items | `runs/20260526-102321-backend-language-choice/phase2/round-02-openai.md` | §6 test plan (replay test) |
| Carve-out-disposition convention from 0226 debrief | `cowork/feedback/2026-05-26-spec-0226-recommendation.md` | §2.5 (CLAUDE.md addition) |

## 2. Proposed change

### 2.1 — Closeout-request builder: surface addressed-at-me items

Update the builder at [src/dual_research/orchestrator/deep_research.py:281-297](src/dual_research/orchestrator/deep_research.py:281). Today the loop appends only entries whose `ent.raiser == agent`. Change the predicate to compute two lists:

- `owned_items` — items where `ent.raiser == agent` (unchanged from today).
- `addressed_at_me_items` — items where `ent.raiser != agent` AND `ent.current_state == open` (the items the OTHER agent raised and that this agent has not yet ADDRESSed).

Extend [`closeout_request_section`](src/dual_research/protocol/prompts.py:1593) to take both lists and render them as two distinct blocks in the prompt: one for items the agent owns (existing closeout language), and one new block stating the addressee-obligation — e.g., "You have N open items addressed at you that you have not yet ADDRESSed; you must emit ADDRESS blocks for each before declaring AGREED." Empty lists render nothing. Pre-spec callsites continue to render the owned-items block as today (zero-length `addressed_at_me_items`).

### 2.2 — Runtime enforcement in `apply_turn`

In [src/dual_research/orchestrator/deep_research.py](src/dual_research/orchestrator/deep_research.py) `apply_turn` (starting at line 299), after parsing the turn but before returning, when `parsed.status == "AGREED"` run the addressee-obligation predicate against the post-turn ledger: are there entries where `ent.raiser != agent` AND `ent.current_state == open`?

- If yes: append a `ProtocolViolation(violation_code="agreed_with_open_addressed_items", agent=agent, phase=<phase>, round=round, item_id=<each blocking item id, comma-joined or one event per blocking item>, from_state="open", op_kind="agreed", expected_state="addressed", reason="AGREED with N open items addressed at this agent: <ids>")` to `violations`.
- The orchestrator's downstream convergence check at lines 1017 and 1020 currently reads `rr.claude_status == "AGREED"` / `rr.openai_status == "AGREED"` from the round result. To demote the offending agent's effective status, the round-result builder must consult the post-`apply_turn` ledger and override `claude_status` / `openai_status` to `"IN_PROGRESS"` whenever an `agreed_with_open_addressed_items` violation was emitted for that agent in that round. The transcript-on-disk and the agent's self-reported `STATUS` line are unchanged; only the orchestrator's reconstructed ledger refuses to converge on the non-compliant AGREED.

Implementation note: the simplest wiring is to track per-(phase, round, agent) "AGREED-was-demoted" in the round-result assembly. The round-result type is built in the negotiation loop around [src/dual_research/orchestrator/deep_research.py:715-870](src/dual_research/orchestrator/deep_research.py:715); pass the violations list down and check for the new code there. If a clean attribute on the round-result dataclass already exists for "effective status", use it; otherwise add `effective_claude_status` / `effective_openai_status` adjacent to the existing `claude_status` / `openai_status` and have the convergence gate consult the effective version. Self-reported `claude_status` stays on the dataclass for the diagnostic trail.

- **Gate-only demotion + transcript truth.** The demotion is applied at the convergence-gate only — the orchestrator's reconstructed status used for `check_convergence` is `IN_PROGRESS`, but the agent's persisted/emitted status in the turn file stays `STATUS: AGREED` (what the agent actually emitted). The ProtocolViolation event is the audit signal explaining why the AGREED didn't count toward convergence. **Do not rewrite the turn file's STATUS line, and do not introduce a new `via_*` flag on `PhaseConverged`** — `via_*` flags are the convergence-PATH partition (verifier I2.3 asserts exactly-one-or-none on a PhaseConverged event). Demotion BLOCKS convergence, so no PhaseConverged is emitted and the `via_*` partition does not apply. ProtocolViolation is the correct, complete observability surface.

### 2.3 — Extend ProtocolViolation code-list

Add the new code `agreed_with_open_addressed_items` to the docstring at [src/dual_research/events/types.py:503-549](src/dual_research/events/types.py:503). After this spec ships the docstring lists 9 codes total (8 from spec 0141/0216/0228 + this one). Update the `Codes in use today:` bullet list accordingly and add a one-paragraph note explaining that this code is the runtime counterpart of verifier invariant I2.4 (the addressee-obligation).

### 2.4 — Flip verifier I2.4 to gating

- **2.4 Verifier I2.4: refactor the detector to handled-vs-unhandled, then promote severity to gating.** Pure severity-flip is NOT safe — the existing `_check_i2_4` implementation at `src/dual_research/contract/verifier.py:533-593` (fail condition at lines 583-588) is a pure-emission check: it flags any AGREED-while-owing turn regardless of whether the orchestrator demoted it. Post-0229, healthy runs will legitimately contain premature-AGREED turns that get demoted-and-recovered (that's the whole point of the demotion mechanism); a pure-emission gating check fails those runs. The fix MUST refactor `_check_i2_4` to mirror exactly what spec 0228 did for I4.4 (the `op-with-matching-ProtocolViolation = pass` pattern): for each AGREED-while-owing turn the function currently flags, look up the corresponding `agreed_with_open_addressed_items` ProtocolViolation events for the same `agent + phase + round` scope. If a matching ProtocolViolation exists, the AGREED was demoted and the case is HANDLED → that instance passes. If no matching ProtocolViolation exists (i.e., the AGREED actually counted toward convergence — produced a `phase_converged` event with open addressed-at-me items still in the ledger), the case is UNHANDLED → that instance fails. Severity flips to `gating` only after this refactor lands.

### 2.5 — CLAUDE.md carve-out-disposition convention

Append a new subsection to the existing "Contract-changing specs are not `bug`s" subsection in [CLAUDE.md](CLAUDE.md):

> ### Carve-out follow-ups must triage at carve-out time
>
> When implementing a spec produces a follow-up spec (a "noticed during implementation" carve-out), the carve-out's frontmatter must include a `disposition:` field set to one of `ship` / `defer` / `archive`, with a one-sentence `disposition_reason:`. Default disposition is `archive`. A carve-out reaches `/dev-next` only when its disposition is `ship`. This forces triage at the moment of carving rather than letting the carve-out accrete into the queue and consume a `/dev-next` cycle by default.
>
> The 200+ spec corpus this project carries is partly the result of follow-ups shipping without triage. The discipline this section names is what stops the pattern.

Validator enforcement of the new `disposition:` frontmatter field is out of scope here (see §5); this spec lands the doctrinal rule. The next follow-up spec to be carved is the place the convention takes effect in practice.

### 2.6 — Version bump + CHANGELOG

- Bump [src/dual_research/__init__.py](src/dual_research/__init__.py) `__version__` from `1.47.0` to `1.48.0`.
- Bump [pyproject.toml](pyproject.toml) `version` from `1.47.0` to `1.48.0`.
- Add a `## [1.48.0] — 2026-05-27` section to [CHANGELOG.md](CHANGELOG.md) with `### Added` bullets covering: addressee-obligation runtime enforcement (ProtocolViolation `agreed_with_open_addressed_items`); closeout-request prompt surfaces addressed-at-me items; verifier I2.4 promoted to gating; CLAUDE.md carve-out-disposition convention.

## 3. User stories & acceptance criteria

Not a UI-touching spec — User stories / BDD scenarios omitted per template (§3 is REQUIRED only for frontend specs).

Implementer-facing acceptance criteria (mirrors §6 test plan and §7 explicit gates):

- `uv run pytest tests/ -q` passes.
- `uv run dual-research verify tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` exits 0 with I2.4 reporting `pass` (now gating).
- `uv run dual-research verify tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/` exits non-zero with I2.4 listed as a gating failure alongside the existing I5.1 / I5.2 / I4.4 failures.
- [CLAUDE.md](CLAUDE.md) contains the new "Carve-out follow-ups must triage at carve-out time" subsection nested under "Contract-changing specs are not `bug`s".

## 4. Data / Schema deltas

No on-disk schema changes. The serialised `ProtocolViolation` event gets one additional value in the `violation_code` string-enum domain (`agreed_with_open_addressed_items`); existing replay/parse paths already tolerate unknown codes (the field is `str`, not a typed enum).

The optional `effective_claude_status` / `effective_openai_status` round-result attributes added in §2.2 are in-memory only — round results are not persisted as their own event type. The transcript files (`runs/<run-id>/phase<N>/round-<RR>-<agent>.md`) are unchanged; only the orchestrator's reconstructed-ledger convergence gate consults the effective status.

## 5. Out of scope

- **Coercing RESOLVE-from-open into WITHDRAW.** Synthesis §2.1 flagged this as a future option. Current behaviour (reject with `ProtocolViolation(resolve_from_non_addressed)`, leave item open) is what spec 0228 shipped and what this spec builds on. Deferred to a follow-up dev spec to be drafted post-merge if/when an anchor run demonstrates the coercion is needed.
- **Removing ghost-cap or hard-cap as escape valves.** The four `via_*` flags remain a first-class partition per synthesis §2.2. This spec adds an invariant that REDUCES how often closeout/ghost-cap fires for the wrong reason; it does not retire those paths.
- **Touching `_build_standing_items_text` at [src/dual_research/orchestrator/deep_research.py:260-273](src/dual_research/orchestrator/deep_research.py:260) beyond the closeout-request builder.** Cowork owns the §7.1 blind-spot read of state-presentation (early finding per synthesis §7: state reporting appears accurate; focus on ratify-instruction). If Cowork's read surfaces a needed change, that's a separate spec — deferred pending Cowork's read.
- **Validator enforcement of the new `disposition:` frontmatter field** introduced doctrinally in §2.5. The CLAUDE.md rule lands here; the validator wiring is deferred to a follow-up dev spec carved against [scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py) the next time a carve-out is created. This is itself an instance of the convention being introduced.
- **Backfill / re-classification of pre-1.48.0 runs.** Existing replayed anchor runs will pick up the new gating I2.4 verdict on replay; we do not rewrite historical run-summary JSON.

## 6. Test plan

- [ ] **Unit — runtime enforcement.** New test in `tests/test_spec_0229_addressee_obligation.py`: construct a phase state with one open item raised by agent `claude` and addressed-at-`openai`. Apply a turn from `openai` with `parsed.status == "AGREED"`. Assert: (a) the returned `violations` list contains exactly one `ProtocolViolation` with `violation_code == "agreed_with_open_addressed_items"`, `agent == "openai"`, and the blocking item id in the `item_id` / `reason` field; (b) the orchestrator's round-result for that round exposes an effective status of `IN_PROGRESS` for `openai` despite `openai_status == "AGREED"` on the dataclass.
- [ ] **Unit — clean case is silent.** Same fixture but with the open item ADDRESSed by `openai` first. Apply `openai`'s AGREED. Assert: zero `agreed_with_open_addressed_items` violations; effective status equals self-reported status.
- [ ] **Closeout-prompt rendering.** New test calling `closeout_request_section` with both `owned_items` and `addressed_at_me_items` populated. Assert: rendered text contains the new addressee-obligation block, names each addressed-at-me item id, and contains the literal "before declaring AGREED" instruction. Empty `addressed_at_me_items` renders no addressee-obligation block (back-compat).
- [ ] **Replay test against the failing run.** Feed `runs/20260526-102321-backend-language-choice/phase2/round-02-openai.md` and the eventual openai AGREED turn (round 3+ if present, or fabricate one) through `apply_turn` against a fresh phase state seeded with the round-01 ledger. Assert: without the §2.2 fix the AGREED is accepted; with the fix, `ProtocolViolation(agreed_with_open_addressed_items)` fires and the four addressed-at-openai item ids are named in the violation.
- [ ] **Verifier snapshot — failing run.** Regenerate `expected.json` for `tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/`. Assert I2.4 now shows `severity: gating, verdict: fail` with the four items (`D-plan-c-02`, `D-plan-c-04`, `D-plan-c-05`, `Q-plan-c-01`) named in the evidence list. Under the handled-vs-unhandled detector this run fails because its frozen AGREEDs are pre-0229 — no matching `agreed_with_open_addressed_items` ProtocolViolation events exist for those rounds, so every offending AGREED is UNHANDLED.
- [ ] **Verifier snapshot — clean run.** Regenerate `expected.json` for `tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/`. Assert I2.4 shows `severity: gating, verdict: pass` (no AGREEDs in this run ever carried open-addressed-at-me debt, so the handled-vs-unhandled detector returns a vacuous pass — no offending instances to classify).
- [ ] **CHANGELOG + version smoke check.** Assert `__version__ == "1.48.0"` and that [CHANGELOG.md](CHANGELOG.md) contains a `## [1.48.0] — 2026-05-27` section.
- [ ] **`test_i2_4_premature_agreed_with_demotion_passes`** — construct a transcript with a turn emitting `STATUS: AGREED` while the ledger has an open item addressed at the same agent, AND a same-round `ProtocolViolation` event with `violation_code="agreed_with_open_addressed_items"` naming that turn's agent. Assert `_check_i2_4` returns `pass` (gating).
- [ ] **`test_i2_4_agreed_that_converged_with_owing_fails`** — construct a transcript with a turn emitting `STATUS: AGREED` while the ledger has an open item addressed at the same agent, NO matching `ProtocolViolation`, AND a same-round `phase_converged` event. Assert `_check_i2_4` returns `fail` (gating) and the failure cites the addressed-at-me item ID.

## 7. Risks

- **R1 — Effective-status demotion accidentally suppresses legitimate convergence.** If the AGREED-demotion logic triggers when the agent has in fact ADDRESSed all addressed-at-me items in the same turn (i.e., the parser saw both ADDRESS and STATUS: AGREED), runs that should converge will block. *Mitigation:* run the predicate against the *post*-`apply_turn` ledger so ADDRESS blocks emitted in the same turn flip the items to `addressed` BEFORE the addressee-obligation check fires. The unit test in §6 covers the "ADDRESS-then-AGREED in one turn" case explicitly.
- **R2 — Closeout-prompt token bloat.** Adding a second item-list block to the closeout request grows the prompt; in a run with many open items addressed at the agent this could push closeout requests past prompt budgets. *Mitigation:* the addressed-at-me list reuses the same `body[:200]` truncation as the owned-items list at [src/dual_research/orchestrator/deep_research.py:271](src/dual_research/orchestrator/deep_research.py:271); a list of N items adds ~250N bytes which is well within the closeout prompt budget for plausible N.
- **R3 — Anchor-run snapshot churn.** Promoting I2.4 to gating will fail every historical anchor run that has any addressee-obligation violation, not just `20260526-102321`. *Mitigation:* the verifier regen step in §6 audits both anchor runs; if other fixtures break, decide per-fixture whether the run was always invalid (in which case `expected.json` flips to gating-fail and the fixture documents the historical breach) or whether the verifier check needs a narrower scope (in which case file a follow-up). The clean anchor `20260521-010637` is the regression canary.
- **R4 — The doctrine in §2.5 lands without enforcement, drifts.** A documented convention with no validator gate is a recommendation, not a rule. *Mitigation:* explicitly named in §5 — the validator wiring is the first follow-up spec carved under the new convention, which makes it the test case for itself. If the wiring spec is not carved within two `/dev-next` cycles after this ships, the convention is failing and should be either escalated to a hard rule or removed.
