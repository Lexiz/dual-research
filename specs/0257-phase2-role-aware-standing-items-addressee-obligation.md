---
kind: dev
spec: "0257"
slug: phase2-role-aware-standing-items-addressee-obligation
title: Make the phase-2/4 standing-items surface role-aware so the addressee ADDRESSes and the raiser stops self-addressing and self-resolving
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0229", "0216"]
complexity: L
created: 2026-05-30
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: 20260530-175809-backend-language-choice-diagnostic
promoted_from_draft: "006"
disposition: ship
disposition_reason: "Binding constraint on convergence quality — the captured run completed but all three phases exited via escape valves (ghost_cap / artifact_promotion), never genuine resolution, with 50 phase-2 protocol violations tracing to one role-blind prompt surface."
---

<!-- DEV SPEC RULE: this body contains NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. -->

# Spec 0257 — Role-aware standing-items surface: addressee must ADDRESS, raiser must not self-address or resolve-from-open

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** 0229 (addressee-obligation invariant), 0216 (raiser-self-address observability)
> **Bump:** MINOR — adds an always-on, role-split standing-items surface for normal negotiation/review rounds; the addressee-obligation that previously existed only in the closeout-round prompt becomes a standing per-round contract. New steering behaviour for phase 2 and phase 4, not a behaviour-preserving refactor.
> **Evidence:** [`runs/20260530-175809-backend-language-choice/`](runs/20260530-175809-backend-language-choice/) (completed, exit 0, 56KB `final.md`); absorbs and supersedes [`specs/drafts/draft-006-phase2-resolve-on-open-protocol-violations-prompt-vs-state-machine.md`](specs/drafts/draft-006-phase2-resolve-on-open-protocol-violations-prompt-vs-state-machine.md) (promote-trigger #1 now met). Contract this is the prompt-side complement to: [spec 0229](specs/0229-addressee-obligation-invariant.md), [spec 0216](specs/0216-raiser-self-address-observability.md).

---

## 0. Post-merge correction (shipped v1.66.0, PR #297) — dead→live retarget

> **This correction header was added after merge.** It does NOT change what
> shipped; it records that the implementation landed on different code than
> the §2 body below cites, and why. Read this before treating §2's file:line
> citations as a map of the live code.

Every code citation in §2 of this spec points at a **dead** surface —
unreachable from the live `run_dr_phase2` / `run_dr_phase4` entry points
since the spec-0118 v2 rewrite. The `reconcile` step passed only because the
cited `file:line` locations still *exist*; it does not check call-path
liveness. The fix was retargeted onto the live surfaces at `/dev-next` time
(operator decision: retarget in-flight rather than halt/re-queue). What
actually shipped:

| §2 cited (DEAD — do not edit to fix behaviour) | Live surface that shipped |
|---|---|
| `ledger/prompt.py:build_standing_items_section` + role-blind `_INSTRUCTION` (§2.1) | `deep_research.format_role_aware_standing_items`, rendered via `dr_run._format_standing_items` (and `DeepResearchPhase._build_standing_items_text`) |
| new `LedgerState.ratifiable_entries` over `current_status == "addressed"` (§2.1) | inline filter on the contract `LedgerEntryV2` state machine (`State.ADDRESSED`); the legacy `LedgerState` has **no** `addressed` status |
| `negotiation_round1_prompt` / `negotiation_turn_prompt` callout (§2.2) | `plan_negotiation_round1_prompt_v2` / `plan_negotiation_round_n_prompt_v2` |
| `review_turn_prompt` phase-4 callout (§2.2) | `review_round1_prompt_v2` / `review_round_n_prompt_v2` |

`build_standing_items_section` and the legacy `phase2.py`/`phase4.py` runners
were left untouched and flagged for deletion — spec **0257.1** removes them
(deleting the dead surface eliminates the miscitation trap that caused this
retarget). The behavioural claim (LLMs stop self-addressing / start
ADDRESSing) is **not** proven by the §6.2 deterministic replay; it requires
the §6.3 live re-run (captured as **draft 008**). Per CLAUDE.md "Cite the live
surface, not the dead one" — the durable guard added off the back of this
spec. See PR [#297](https://github.com/Lexiz/dual-research/pull/297) and
[the handoff](../handoffs/2026-05-30-spec-0257-phase2-role-aware-standing-items-addressee-obligation.md).

---

## 1. Context

The captured run `20260530-175809-backend-language-choice` completed (the phase-4 anchor-crash fix from spec 0256 held), but its convergence quality is poor: **all three converging phases exited via escape valves, none by genuine resolution** — phase 0 `via_artifact_promotion`, phase 2 `via_ghost_cap` (round 6), phase 4 `via_artifact_promotion`. Phase 2 emitted **50 protocol violations across three codes that reduce to one root cause: the agents disagree about who owns/addresses/closes ledger items.** Counts from the run transcript (`event` key, not `kind`): `resolve_from_non_addressed` ×24 (claude, every round 2–6 + phase 4), `agreed_with_open_addressed_items` ×20 (openai, every round 2–6), `raiser_self_address` ×5 (claude, round 2), `resolve_wrong_raiser` ×1. Spec 0255 stopped this deadlocking (closeout urged, ghost-cap armed) but the role-confusion still fires every round and prevents genuine resolution. This confirms item ownership — not early-deadlock-abort — is the binding constraint on convergence quality.

The single root cause is the **role-blind standing-items instruction** at [`src/dual_research/ledger/prompt.py:26`](src/dual_research/ledger/prompt.py:26). For *both* item groups (raised-by-them and raised-by-you) it offers the *same* two options: "(a) **answer or address** the item directly … OR (b) **explicitly close it out**." That instruction directly invites all three violation classes. For an item **raised by you** (you are the raiser), option (a) "address" produces `raiser_self_address` and option (b) "close it out" produces `resolve_from_non_addressed` — observed verbatim in round-02-claude, which issued `### ADDRESS D-plan-c-01` ("I am conceding D-plan-c-01") on its own open item. For an item **raised by them** (you are the addressee), option (b) "close it out" lets the addressee skip ADDRESS and jump to AGREED — observed verbatim in round-02-openai, which wrote "No open Claude-raised items remain for me to address" while `D-plan-c-01..03` were still `open`, set `STATUS: AGREED`, and only resolved its *own* `-g-` items → `agreed_with_open_addressed_items`. The legal-op set is strictly determined by role, but the prompt never says so. Compounding this: the addressee-obligation block exists **only** in `closeout_request_section` ([`src/dual_research/protocol/prompts.py:1675`](src/dual_research/protocol/prompts.py:1675)) — normal rounds never show it; `build_standing_items_section` only surfaces `open` entries via `open_entries()` ([`src/dual_research/ledger/models.py:103`](src/dual_research/ledger/models.py:103)), so the raiser never even *sees* its item flip to `addressed` and therefore never learns when it is finally allowed to RESOLVE.

## 2. Proposed change

Two prompt-side prongs. The verifier invariants and the orchestrator's drop semantics ([`src/dual_research/orchestrator/deep_research.py:457`](src/dual_research/orchestrator/deep_research.py:457), `:579`, `:598`) are **unchanged** — they are the executable contract; this spec makes the prompt teach that contract reliably.

### 2.1 — Role-aware standing-items surface (`src/dual_research/ledger/prompt.py`)

Replace the single role-blind `_INSTRUCTION` with **three role-scoped groups**, each carrying only the legal ops for that role. The grouping split already exists at [`src/dual_research/ledger/prompt.py:107`](src/dual_research/ledger/prompt.py:107) (`add_group(by_them)` / `add_group(by_you)`); this spec gives each group its own instruction string and adds a third group:

1. **`### Raised by the other agent — you are the ADDRESSEE`** (open items where `raised_by == them`). Instruction: you MUST emit `### ADDRESS <id>` for each (or `### REQUEST_EVIDENCE <id>`, or a counter-argument that holds the item open). You may NOT RESOLVE, WITHDRAW, or "close out" these — only the raiser ratifies. **Declaring `STATUS: AGREED` while any item here is still open/unaddressed is the `agreed_with_open_addressed_items` violation (spec 0229, gating invariant I2.4).**
2. **`### Raised by you — still open (NOT yet addressed)`** (open items where `raised_by == perspective`). Instruction: the other agent has not addressed these yet. Do NOT emit `### ADDRESS <id>` on your own item (`raiser_self_address`, spec 0216) and do NOT emit `### RESOLVE <id>` while the item is `open` (`resolve_from_non_addressed`). Your only legal move now is `### WITHDRAW <id>` (or wait for the addressee).
3. **`### Raised by you — ADDRESSED, ready for you to ratify`** (NEW group; items where `raised_by == perspective` and `current_status == "addressed"`). Instruction: the other agent has ADDRESSed these — you may now `### RESOLVE <id>` (you accept), `### ACKNOWLEDGE <id>` (irreconcilable), or counter (flip back to open with rationale).

Group 3 requires surfacing `addressed`-state items, which `open_entries()` excludes. Add a sibling helper `ratifiable_entries(perspective)` on `LedgerState` (next to `open_entries` at [`src/dual_research/ledger/models.py:103`](src/dual_research/ledger/models.py:103)) returning entries with `current_status == "addressed"` and `raised_by == perspective`; `build_standing_items_section` calls it for group 3. `_format_entry_line` ([`src/dual_research/ledger/prompt.py:144`](src/dual_research/ledger/prompt.py:144)) already prints `current_status`; extend it to also print `addressed_by` when present so the raiser sees who addressed the item.

### 2.2 — Standing role-contract callout in the round-N prompt body (`src/dual_research/protocol/prompts.py`)

The round-N `negotiation_turn_prompt` ([`src/dual_research/protocol/prompts.py:300`](src/dual_research/protocol/prompts.py:300)) describes a narrative protocol ("Substantive disagreements I'm holding", "Resolved or non-blocking differences" — lines 409–454) that never names the ADDRESS/RESOLVE role split; only the round-1 prompt and the phase-4 review prompt carry the role-correct "Addressing items raised against me" / "Ratifying my own items" structure. Introduce a constant `_ADDRESS_RESOLVE_ROLE_CALLOUT` (a sibling to `_OPERATION_BLOCK_REFERENCE` at [`src/dual_research/protocol/prompts.py:1347`](src/dual_research/protocol/prompts.py:1347)) stating the contract for the **symmetric phase-2** axis in one paragraph:

> The agent that RAISED an item never ADDRESSes it and never RESOLVEs it while it is `open`. The OTHER agent (the addressee) ADDRESSes it (`open → addressed`). Only then may the raiser RESOLVE / ACKNOWLEDGE / WITHDRAW it. You may not declare `STATUS: AGREED` while any item raised against you is still `open` and unaddressed.

Render `_ADDRESS_RESOLVE_ROLE_CALLOUT` inline in `negotiation_round1_prompt` and `negotiation_turn_prompt`, immediately above the `## Status` section.

**Phase 4 is NOT the same axis — do not reuse the phase-2 wording (cowork correction 3).** Verified against run `20260529-164844`: phase 4 has a fixed **drafter = addressee** (claude), **reviewer = raiser** (openai) — an asymmetric, role-fixed split, unlike phase-2 where both agents raise and address symmetrically. The 7× `raiser_self_address` there is the *drafter* addressing *reviewer*-raised items, which is plausibly an item-ownership / ID artifact rather than pure role-blindness. Therefore:

- `review_turn_prompt` gets its **own** constant `_ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4`, framed in drafter/reviewer terms ("the REVIEWER raises issues/comments; the DRAFTER ADDRESSes each via the revision; the REVIEWER alone ratifies — the drafter never ADDRESSes its own surfaced items"), **not** the phase-2 raiser/addressee paragraph verbatim. Shipping the correct wording is unconditional.
- The phase-4 *behavioural* outcome is **verified, not assumed**: 0257 does not claim the callout alone resolves the phase-4 violations. The replay harness (§6) vendors the phase-4 turns and the live re-run (§6) reports phase-4 violations separately. If the phase-4 `raiser_self_address` count does not go to zero with the corrected callout, the residual is an item-ownership/ID-mapping defect in the phase-4 drafter path and is carved to a follow-up (`0257.2`), **not** treated as a 0257 regression. The phase-2 fix is the committed behavioural deliverable; the phase-4 fix is committed wording + measurement.

## 3. User stories & acceptance criteria

Non-UI spec (touches `src/dual_research/ledger/` and `src/dual_research/protocol/` only). User-story / BDD section omitted per template §3.

Before/after, observable in the run transcript:

- **Before** (run `20260530-175809`): phase 2 converges `via_ghost_cap` with 46 phase-2 violations (+4 in phase 4); the addressee (openai) emits zero `### ADDRESS` blocks against claude's `D-plan-c-*` items; the raiser (claude) emits `### ADDRESS`/`### RESOLVE` on its own open items every round.
- **After**: the addressee emits one `### ADDRESS` per open item-raised-against-it before any `STATUS: AGREED`; the raiser emits `### RESOLVE` only after its item shows `current_status: addressed`; phase 2 converges `via_genuine_resolution` with zero `raiser_self_address` / `resolve_from_non_addressed` / `agreed_with_open_addressed_items`.

## 4. Data / Schema deltas

None. No ledger schema change — `ratifiable_entries` is a read-side query over existing `current_status` / `raised_by` fields. No new event types, no verifier-invariant additions or severity changes.

## 5. Out of scope

- **Changing the 0228 state machine or allowing RESOLVE-from-open as a legal transition** (draft-006 remediation path #2). Rejected: the state machine is correct; the prompt failed to teach it. The fix is the prompt, not the contract.
- **Bidirectional resolution / letting either agent resolve regardless of raiser** (draft-006 path #3). Rejected: would weaken the raiser-owns-ratification contract that the verifier enforces.
- **Auto-ADDRESS / auto-acknowledge on the agent's behalf after K stuck rounds — rejected permanently, removed from the roadmap (cowork correction 1).** This is the un-demotion / addressee-obligation-satisfied-without-cooperation mechanism already evaluated and **archived in [spec 0255 §5](specs/0255-decouple-closeout-urge-from-effective-status.md)**. It fabricates protocol ops the agent never emitted — an item would show `addressed` when no agent addressed it — corrupting the ledger's meaning and creating a *second* silent-failure surface rather than a safety net. The liveness floor already exists (spec 0255 ghost-cap); the cost cap is the deferred early-deadlock-abort below. **If 0257 underperforms on the live re-run, the next lever is early-deadlock-abort + further tightening of the prompt / ID surface — NOT auto-ADDRESS.**
- **Early-deadlock-abort.** Explicitly deferred — this run proves item ownership, not abort-latency, is the binding constraint; promote abort only after a run converges via genuine resolution and still wastes rounds. This (with prompt/ID tightening) is the designated next lever if 0257's prompt fix underperforms.
- **Item-ID slug-vs-positional canonicalization beyond surfacing.** The ledger already reconciles openai's self-authored slugs to positional `-g-` IDs and round-2+ STATUS arrays used the canonical IDs correctly; this spec only guarantees the canonical IDs + state are surfaced per role. A dedicated round-1 ID-emission tightening, if still needed after this lands, is a sibling follow-up (`0257.1`), not this spec.

The CI floor is a **behavioural replay harness** (§6.2), not the prompt-content string checks alone. The string checks (§6.1) prove the prompt *says* the right words; they do **not** prove agents *behave* — relying on them as the gate is the 0231→0238 trap (a fix passes CI by testing the wrong layer while behaviour regresses silently, cowork correction 2). The string checks are necessary-but-insufficient; the replay harness is the durable spec-0238 regression.

### 6.1 — Prompt-content + unit checks (necessary, not sufficient)

- [ ] `build_standing_items_section` over a ledger with one open-against-me item, one open-by-me item, and one addressed-by-me item renders **three** distinct groups whose instruction text contains, respectively: "ADDRESS" + "may NOT RESOLVE" (addressee group); "do NOT" + "WITHDRAW" (raiser-open group); "RESOLVE" + "ratify" (raiser-addressed group). (positive)
- [ ] The same output contains **none** of the pre-fix role-blind phrase fragments ("answer or address" co-occurring with "explicitly close it out" in a single shared instruction). (antipodal-absence)
- [ ] `ratifiable_entries("claude")` returns exactly the `current_status == "addressed"` entries with `raised_by == "claude"` and excludes `open` / terminal entries. (falsifiable)
- [ ] `_ADDRESS_RESOLVE_ROLE_CALLOUT` is present in `negotiation_round1_prompt` + `negotiation_turn_prompt`, and the **distinct** `_ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4` (drafter/reviewer wording) is present in `review_turn_prompt` and absent from the phase-2 prompts. (falsifiable — guards the correction-3 asymmetry)

### 6.2 — Behavioural replay harness (the CI floor — committed 0257 deliverable, cowork correction 2)

- [ ] **Vendor** run `20260530-175809`'s phase-2 turns AND phase-4 turns as a recorded fixture under `tests/fixtures/spec_0257/` (per the spec-0206/0238 captured-artifact convention).
- [ ] **Replay phase 2** through the real `run_dr_phase2` entry point (agent turns served from the fixture, prompts rendered by the role-aware build) and assert: the addressee emits a `### ADDRESS` for each open item-raised-against-it **before** any `STATUS: AGREED`, and the raiser emits **zero** `raiser_self_address` and **zero** `resolve_from_non_addressed`. (falsifiable, deterministic)
- [ ] **Replay phase 4** through the real `run_dr_phase4` entry point against the vendored phase-4 turns and **report** the `raiser_self_address` count under the corrected `_..._PHASE4` callout. Target zero; a non-zero residual confirms the item-ownership/ID hypothesis and triggers the `0257.2` carve-out (per §2.2) rather than failing this gate. (measurement, not pass/fail on phase 4)

### 6.3 — Live acceptance evidence (in the PR, not a CI gate)

- [ ] A real re-run on the `backend-language-choice` brief, scored via `/dr-run-assess`, reports phase 2 `phase_converged via_genuine_resolution` (not `via_ghost_cap` / `via_artifact_promotion`) with **zero** `raiser_self_address`, `resolve_from_non_addressed`, and `agreed_with_open_addressed_items`. The PR description carries the run ID, the phase-2 tally, and the **separate** phase-4 tally (so the phase-4 half is observed, not assumed). (acceptance evidence)

## 7. Risks

- **The callout adds tokens to every interaction round.** Mitigation: one paragraph (~80 words) shared via a single constant; negligible against the existing multi-KB prompts.
- **A live re-run is non-deterministic and cannot gate CI; prompt-content string checks alone test the wrong layer (the 0231→0238 trap).** Mitigation: the CI gate is the §6.2 behavioural replay harness — it replays this run's vendored turns through the real `run_dr_phase2` / `run_dr_phase4` entry points and asserts the addressee ADDRESSes-before-AGREED and the raiser emits no self-address/resolve-from-open. The §6.1 string checks are necessary-but-insufficient guards; the live run (§6.3) is PR acceptance evidence. This is the spec-0238 real-entry-point discipline made deterministic.
- **Surfacing a third group could overflow the `max_chars`/`max_items` truncation budget.** Mitigation: the existing truncation logic at [`src/dual_research/ledger/prompt.py:95`](src/dual_research/ledger/prompt.py:95) already caps and emits a "…omitted" line; the new group participates in the same budget with no new cap path.
- **Revert plan:** the change is additive prompt text + one read-side query; if a re-run regresses convergence, revert the commit — no migration, no state to unwind.
