# Backlog inventory — Notion review (run 20260521-010637-dvs-backend-language-choice)

> Source: Notion page "Claude report: bugs, improvements, investigation" (https://www.notion.so/36799f3e507f80008aa4d0f4dc25bce8)
> Anchor run: 20260521-010637-dvs-backend-language-choice
> Generated: 2026-05-21
> Total items: 16

## Preamble

> This page is a structured digest of the items originally captured in [Known bugs and improvements](https://www.notion.so/36799f3e507f8033847bc318c4674a55) — all of them anchored on run `20260521-010637-dvs-backend-language-choice` (plus follow-up findings on the same run). Each section below is the Claude-authored interpretation lifted verbatim from the source page, paired with the original screenshot(s) where one exists. The verbatim user-authored descriptions are not duplicated here — refer to the source page if you need the raw wording.

---

## B01 — Phase 0 section in Critique panel
- **Type:** improvement
- **Area:** ui / critique panel / run-detail
- **Severity (if a bug):** n/a
- **Repro signal:** screenshot
- **Cross-links:**
- **Verbatim quote:**
  > ## Improvement 1 — Add a Phase 0 section to the Critique panel
  > ### Interpretation
  > The Critique panel renders dedicated sections for Phase 2 and Phase 4 summaries but has no equivalent section for Phase 0. Since Phase 0 now runs a negotiation round that emits critique items (disagreements and questions), the Critique panel must (a) gain a Phase 0 section using the same toggle/button pattern as the other phase sections, and (b) surface every critique artifact captured during Phase 0 inside that section. Acceptance: opening a finished run that produced Phase 0 critique items shows a Phase 0 section in the Critique panel containing every Phase 0 disagreement and question.
  > ### Screenshot
  > ![](screenshot.png)

---

## B02 — Disagreement raise/close invariant violated
- **Type:** bug
- **Area:** orchestrator / critique aggregation / run summary
- **Severity (if a bug):** high
- **Repro signal:** run-log
- **Cross-links:**
- **Verbatim quote:**
  > ## Bug 1 — Disagreement raise/close count invariant violated (9 raised, 10 closed)
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, the run summary reports 9 disagreements raised but 10 disagreements closed — an impossible state since you cannot close more than were raised. Investigate the underlying disagreement events for this run, determine whether the raise counter is under-counting, the close counter is over-counting, or the same disagreement is being counted closed twice (e.g. once when resolved and again when superseded or auto-closed at phase end), and fix the aggregation so the invariant `raised >= closed` holds for every run.
  > ### Screenshot
  > ![](screenshot.png)

---

## B03 — Token / cost capture skewed between Claude and ChatGPT
- **Type:** bug
- **Area:** consumption tab / cost attribution / aggregator
- **Severity (if a bug):** high
- **Repro signal:** run-log
- **Cross-links:** B11
- **Verbatim quote:**
  > ## Bug 2 — Token and cost capture skewed between Claude and ChatGPT
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, the cost view shows Claude charged \$8.51 for \~200k tokens while ChatGPT charged \$1.81 for roughly 3x the token volume. These ratios are not consistent with either provider's published per-token pricing, so the cost/token attribution is being captured incorrectly somewhere — tokens may be mis-allocated across models, dollar amounts may be computed against the wrong price tier (e.g. input vs. output, or cached vs. uncached), or one side is being double-counted while the other is dropped. Trace the full path from per-call provider response → persistence → the per-run aggregated batches view → the global Consumption tab, identify where the divergence is introduced, and fix the capture so token totals and dollar totals reconcile against documented per-model prices on **both** views (not just one).
  > ### Screenshot
  > ![](screenshot.png)

---

## B04 — Live timeline rendering non-deterministic
- **Type:** improvement
- **Area:** ui / live timeline / critique panel
- **Severity (if a bug):** n/a
- **Repro signal:** behavioural
- **Cross-links:**
- **Verbatim quote:**
  > ## Improvement 2 — Live timeline rendering is non-deterministic across phases
  > ### Interpretation
  > While a run is in flight, the timeline's rendering of negotiation progress is non-deterministic: sometimes each round/turn appears as a new card in real time, and other times nothing surfaces until the phase ends — at which point the Critique panel suddenly fills with disagreements and category cards in bulk. There is no documented contract for when individual turns become visible vs. when only the phase badge in the header advances. Decide and enforce a single rendering contract — either always stream per-turn, or always batch-on-phase-completion with an explicit "processing" state on the in-progress phase — and apply it uniformly across Phase 0, Phase 2, and Phase 4. Additionally, on every phase transition verify that the full-view flyovers and the Critique section are fully populated with the just-finished phase's state *before* advancing to the next phase. Acceptance: across multiple runs, the timeline produces the same kind of progressive signal at the same points, and the Critique panel never "jumps" mid-phase with state that should already have been visible.

---

## B05 — Initial Brief full-view shows empty prompts
- **Type:** bug
- **Area:** ui / full-view modals / prompt capture / persistence
- **Severity (if a bug):** high
- **Repro signal:** run-log
- **Cross-links:** B15
- **Verbatim quote:**
  > ## Bug 3 — Initial Brief full-view shows empty system and user prompts
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, opening the Initial Brief full-view card renders both the system prompt and the user prompt as empty. The brief was clearly used (the run proceeded), so the prompts exist somewhere — the failure is either at persistence (prompts not written to the run record), fetch (full-view query not retrieving them), or render (card not displaying what it received). Trace prompt capture from build → persistence → fetch → render to find the missing link, and audit **every other** full-view card (per-phase briefs, cross-review prompts, summary prompts, etc.) for the same class of bug so the fix isn't a single-card patch and future runs are protected.
  > ### Screenshot
  > ![](screenshot.png)

---

## B06 — Empty turns with zero critique movement
- **Type:** bug
- **Area:** orchestrator / patch extractor / phase 0,2,4 prompts
- **Severity (if a bug):** high
- **Repro signal:** run-log
- **Cross-links:** B09
- **Verbatim quote:**
  > ## Bug 4 — Empty turns recording zero critique movement across Phase 0 / 2 / 4
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, many turns across Phase 0, Phase 2, and Phase 4 are recorded with zero adds and zero removes for every critique category (questions, disagreements, issues, comments). Concrete examples: Phase 0 GPT runs 3 and 4 are empty; Phase 2 turns 4 and 5 are empty for both Claude and GPT, with only one Claude disagreement resolved in round 5 and the remaining turns essentially empty; in Phase 4 almost every turn shows no critique movement while the editor still records removals — i.e. the models ping-pong without producing anything new. Two hypotheses to investigate per empty turn: (1) the model genuinely produced nothing actionable, meaning the prompt is not nudging strongly enough toward resolving open critique items — fix by tightening the resolve-driven instructions; or (2) the model **did** produce critique movement but the capture/patch-extractor pipeline dropped it before it landed on the turn — fix by repairing the capture path. For each empty turn, determine which hypothesis applies using raw model logs vs. the parsed turn output, then fix accordingly.
  > ### Screenshots
  > ![](screenshot.png)
  > ![](screenshot.png)
  > ![](screenshot.png)

---

## B07 — Phase 4 deadlock after turn 8
- **Type:** bug
- **Area:** orchestrator / phase 4 / turn parsing / context payload
- **Severity (if a bug):** blocker
- **Repro signal:** run-log
- **Cross-links:** B09, B12, B13
- **Verbatim quote:**
  > ## Bug 5 — Phase 4 deadlock after turn 8 with model output still flowing
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, Phase 4 stops advancing after turn 8 and the entire run deadlocks. While this is happening, the live terminal is still printing large volumes of model output as if the LLMs are continuing to reply — so generation is happening, but nothing is being parsed into a recordable turn, nothing is being attributed to critique movement, and the phase never advances. Investigate (a) what Phase 4 is repeatedly sending into the model context across turns — strongly suspected: a large accumulating blob that is re-sent verbatim each turn — and (b) why the output coming back stops being ingested into a turn record. Adjacent improvement to consider (do not bundle into the fix without confirmation): trim the context echoed back to the model on each Phase 4 turn so it focuses on what is still **open** (unresolved questions, disagreements, issues, comments) rather than re-processing the same growing payload — this may both speed Phase 4 up and prevent the deadlock, but must not strip context the model genuinely needs to reason about the work.

---

## B08 — Phase 4 cards missing Issue and Comment patches
- **Type:** bug
- **Area:** ui / phase 4 cross-review cards / critique rendering
- **Severity (if a bug):** med
- **Repro signal:** run-log
- **Cross-links:** B14
- **Verbatim quote:**
  > ## Bug 6 — Phase 4 cross-review cards don't render Issue and Comment patches
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, the Phase 4 header filters expose all four critique categories (Question, Disagreement, Issue, Comment), but the per-round cross-review cards only render add/remove patches for Questions and Disagreements — Issues and Comments are not patched onto the cards. The cross-review rounds in Phase 4 do produce Issues and Comments, so the per-round cards must render add/remove patches for those two categories using the same patch-rendering logic already used for Questions and Disagreements. Acceptance: in any Phase 4 cross-review round where an Issue or Comment is added or removed, a matching tag/patch appears on that round's card, identical in shape to the existing Question/Disagreement patches.
  > ### Screenshot
  > ![](screenshot.png)

---

## B09 — Source / provenance logic absent on this run
- **Type:** investigation
- **Area:** sources / provenance / orchestrator triggers
- **Severity (if a bug):** n/a
- **Repro signal:** run-log
- **Cross-links:** B14
- **Verbatim quote:**
  > ## Investigate 1 — Source / provenance logic not surfacing on this run
  > ### Interpretation
  > We recently added logic that explicitly governs how sources are requested, stored, and linked to critique items (questions, disagreements, issues, comments) — establishing provenance between a request-for-more-research and the actual research result, including the timing of when the research landed. On run `20260521-010637-dvs-backend-language-choice` none of this surfaces — no sources are cited, recorded, or requested anywhere in the run. Two parallel investigations are needed: (1) audit the source/provenance code path end-to-end for bugs that would prevent it from emitting under the conditions it is meant to fire on, and (2) determine whether this specific run simply never hit the conditions that should request sources (in which case the logic is fine but the trigger conditions need to be reviewed), or whether it did hit them but the recording silently failed.

---

## B10 — Resolved view contradicts Phase 4 timeline
- **Type:** bug
- **Area:** ui / critique resolved view / phase 4 resolution tracking
- **Severity (if a bug):** high
- **Repro signal:** run-log
- **Cross-links:** B06, B07
- **Verbatim quote:**
  > ## Bug 7 — Critique "Resolved" view contradicts the Phase 4 timeline
  > ### Interpretation
  > On run `20260521-010637-dvs-backend-language-choice`, the Critique panel's Resolved section claims almost everything was resolved in Phase 1 (only two items resolved later, one in round 2 and one in round 3). The Phase 4 timeline tells a contradictory story: it ran up to round 8 and ended in a deadlock with very little resolution movement actually happening. Three possibilities to investigate, and probably some combination is in play: (a) the Resolved aggregation is mis-attributing resolution events to early rounds — i.e. items are counted as "resolved in Phase 1" when they were actually resolved much later or never; (b) Phase 4 turns are failing to record their resolution events at all, so the Resolved view simply doesn't see Phase 4's work; or (c) the model is being told via the prompt that "everything is already resolved" too early, leaving it with nothing meaningful to act on in Phase 4 — which is what produces the deadlock. The way critique items are surfaced to the models and the way resolution events are captured are clearly out of sync. Pin down which of (a)/(b)/(c) is happening (or which combination), and fix the resolution-tracking + nudge loop so the Resolved view and the Phase 4 timeline tell a consistent story.
  > ### Screenshots
  > ![](screenshot.png)
  > ![](screenshot.png)

---

## B11 — Top-bar copy button + Total cost/token labels
- **Type:** improvement
- **Area:** ui / run-detail header / top bar
- **Severity (if a bug):** n/a
- **Repro signal:** screenshot
- **Cross-links:** B03
- **Verbatim quote:**
  > ## Improvement 3 — Top-bar copy button and Total cost / token labels
  > ### Interpretation
  > Two related changes to the top bar of the run view. (1) Next to the badge that displays the run ID, add a small copy button; clicking it should copy the run ID (or run link) along with the run's total cost and total token usage to the clipboard in a single action. Before wiring this up, validate that the cost and token totals being shown — and therefore copied — are accurate; this overlaps with Bug 2, which must be resolved first since cost/token capture is currently unreliable. (2) Label the cost and token figures in the top bar explicitly as "Total cost" and "Total tokens" (or equivalent wording) so it is unambiguous to the user that these are run-wide totals, not per-phase or per-model values.
  > ### Screenshot
  > ![](screenshot.png)

---

## B12 — Phase 4 draft extractor drops body on `##` sub-sections
- **Type:** bug
- **Area:** orchestrator / phase 4 / draft extractor / prompts
- **Severity (if a bug):** blocker
- **Repro signal:** code-pointer
- **Cross-links:** B07, B13
- **Verbatim quote:**
  > ## Bug 8 — Phase 4 draft extractor drops body when sub-sections use `##` instead of `###`
  > ### Interpretation
  > The Phase 4 draft extractor is brittle: it stops at *any* `##` header that follows `## Revised draft`, so whenever the drafting model writes draft-body sub-sections at the `##` level (which Claude does even when prompted to use `###`), the extractor captures only the title and silently drops the entire research payload. Observed on run `20260521-010637-dvs-backend-language-choice`, where `phase4/round-07-claude.md` held 312 lines of full content but `phase4/draft-v7.md` ended up as a 76-byte stub — the substantive output of an entire \~\$10 run sits unused on disk because the parser couldn't find it. Fix path in priority order: (1) **structural** — switch the extractor from "stop at any `##`" to "stop at a known whitelist of sibling sentinels" (`## Stance`, `## Addressing items raised against me`, `## Ratifying my own items`, `## New items`, `## Phase artifact`, `## Status`), so authors can freely use `##` inside the draft body and still get captured correctly; (2) **defensive prompt sharpening** — restate the drafter instruction with an explicit `###` example so it does not drift back to `##`; (3) **salvage for this run** — pull lines 47–312 out of `round-07-claude.md` and write them as a clean `final.md` so the spent \$10.31 on this run is not wasted.

---

## B13 — Phase 4 escape valve precondition too narrow (Spec 0137)
- **Type:** bug
- **Area:** orchestrator / phase 4 escape valve / spec 0137
- **Severity (if a bug):** high
- **Repro signal:** spec-pointer
- **Cross-links:** B07, B12
- **Verbatim quote:**
  > ## Bug 9 — Phase 4 escape valve (Spec 0137) precondition is too narrow
  > ### Interpretation
  > The Phase 4 escape-valve logic (Spec 0137) has a precondition that is too narrow to cover the deadlock shapes we actually hit: it only fires when *both* agents emit `STATUS: AGREED` with terminal ledgers and the artifact hashes diverge. It does not fire in the more common shape — one or both agents stuck at `IN_PROGRESS` for the full Phase 4 round budget — which is exactly what happened on run `20260521-010637-dvs-backend-language-choice`: GPT stayed at `IN_PROGRESS` for all 8 rounds (because Bug 8 left the on-disk draft as a stub it could not honestly ratify), so the escape valve never engaged and the run rode all the way into a hard-cap deadlock with no escape attempt. Broaden the trigger (either by extending Spec 0137's precondition or by layering a sibling rule) to also catch: (a) one agent at `AGREED` while the other is stuck at `IN_PROGRESS` for K rounds, and (b) both agents at `IN_PROGRESS` with zero critique-ledger movement for K rounds. Either condition should invoke the same escape behaviour that the current narrow condition does, so future Phase 4 deadlocks of this shape get short-circuited instead of burning the full round budget.

---

## B14 — Source provenance visible on every critique card
- **Type:** feature
- **Area:** sources / provenance / critique card UI / design-system
- **Severity (if a bug):** n/a
- **Repro signal:** code-pointer
- **Cross-links:** B08, B09
- **Verbatim quote:**
  > ## Improvement 4 — Source provenance visible on every critique card (the answer to Investigate 1)
  > ### Interpretation
  > The product needs source provenance to be visible on every critique-section card across every run, matching the iteration-3 badge-governance ideation mockup that the design conversation converged on. That requires three coordinated workstreams, in this order:
  > **1) Backend — extend the provenance schema and turn the validator on.**
  > - (a) Add denormalised provenance fields to `EvidenceRecord` (both `src/dual_research/contract/evidence.py:28-44` and the UI mirror `src/dual_research/ui/models.py:402-420`): `raised_in_round: int`, `answered_in_round: int`, `requested_by: ActorId | None`, `provided_by: ActorId`, `attached_at: datetime`. Populate them in `_apply_transition` (`src/dual_research/ui/items.py:160-181`) where the round + actor are already in scope from the `ItemTransitioned` event.
  > - (b) Add an optional first-class `RequestEvidence` block (or equivalent ledger op) so mid-run requests for sources can be modelled distinctly from the raise-time `evidence_required: bool`. Persist them as their own events so the timeline can render a "Claude asked GPT for sources in r3" turn that is structurally different from a raise.
  > - (c) Wire `unverified` end-to-end: make `dr_run.py` and `ledger/replay.py` construct `DeepResearchPhase` with a real `evidence_validator` (the `validate_all_evidence` already present in `contract/evidence.py:91-194`), and change `deep_research.py:354-363` so that flagged records propagate to the UI with `unverified=True` / `unverified_reason=...` instead of dropping the whole ADDRESS block. Acceptance: at least one source in a test fixture renders the `⚠ unverified` chip on the corresponding card.
  > - (d) Resolve `EvidenceRecord.evidence_event_id` against the per-turn `TurnSearchAudit` (`src/dual_research/audit/schema.py`) inside `ui/items.py` and surface `consulted_sources` / `citations` next to each evidence record in the wire payload, so the UI has the data to render a full source excerpt + provider attribution + search query.
  > - (e) Pair with Investigate 1's second prong: confirm that on run `20260521-010637-dvs-backend-language-choice` (and a fresh test run) the new schema actually populates — no nulls, every source linked to its raising round AND its answering round.
  > **2) Frontend — wire the existing ****`ItemCard`**** to the live critique pane and style it.**
  > - (a) Switch `renderItem` (`run-detail.jsx:6169-6195`) to route new-protocol items through `<ItemCard>` (already defined at `run-detail.jsx:1325-1401`), and stop dropping `evidence` / `transitions` / `anchor_*` / `evidence_required` in `_normalizeToThread` (`run-detail.jsx:6419-6512`). All four kinds (Q / D / I / C) should use `ItemCard`; only legacy pre-0114 runs continue through `QuestionThread`.
  > - (b) Add CSS rules for `.source-row` and the surrounding Sources segment to `src/dual_research/ui/static/components.css`, matching the visual treatment in `handoffs/ds-v2-audit/badge-governance-mockup-iter3.html` lines 177–185 (compact row, host badge, expandable disclosure, bounded-scroll excerpt body). Today this class has zero matching rules outside the modal's `.rp-sources` wrapper.
  > - (c) Extend the QuestionThread status vocabulary (`shared.jsx:1167-1178`) to also surface `capped` and `acknowledged` as card-level status chips, so the header status chip matches what the lifecycle already produces.
  > - (d) Consume `item.evidence_required` in `ItemCard` and render the "Evidence needed: …" italic helper underneath the body when the flag is set.
  > - (e) Unify the lifecycle footer across all four item kinds: `✓ resolved/capped/acknowledged/withdrawn at round N · M turns to converge` for all of them (currently only Questions get the "M turns to converge" suffix; Disagreements get "conceded by X"; Issues/Comments get nothing).
  > - (f) Render the `⚠ unverified` chip on the source row when `record.unverified === true`.
  > - Acceptance: opening a finished new-protocol run, every critique-section card shows the iter-3 layout — header with Sources N chip, body + Evidence needed helper when applicable, LIFECYCLE chip-tagged timeline, footer with checkmark + round + turn count, and a SOURCES (N) section underneath listing every attached source with title + host + expandable excerpt.
  > **3) Design system — canonise the layout so backend + frontend can be governed by it.**
  > - (a) Move the recovered iteration-3 mockup from `handoffs/ds-v2-audit/badge-governance-mockup-iter3.html` to `design-system/audits/2026-05-19-badge-governance-iter3/mockup.html` and reference it from `design-system/SPEC.md` as the canonical visual source for critique-card source visualisation.
  > - (b) Add a `SourceRow` component section to `SPEC.md`: collapsed state (▶ disclosure + title + host badge), expanded state (URL link + fetched-at + search-query + content-excerpt with bounded scroll), `⚠ unverified` chip slot, host-badge styling.
  > - (c) Add a `Sources segment` spec to `SPEC.md`: label "Sources (N)", placement immediately after the lifecycle footer, separator behaviour, empty state (hide segment entirely when N === 0).
  > - (d) Add a critique-card composition spec to `SPEC.md` and a matching rendered example to `design-system/assets/Design System v2.html` showing how the full primitive stacks together: header chips → body → Evidence-needed helper (optional) → LIFECYCLE → footer → SOURCES.
  > - (e) Add a sentence-level invariant to `SPEC.md`: "All four critique-item kinds (Question, Disagreement, Issue, Comment) render with the same card layout; only the category chip changes." This is the rule that makes Bug 6 above (Issues/Comments not patched onto Phase 4 cards) and this Improvement converge on the same primitive.
  > Sequencing: (1) must land before (2) so the frontend has data to render; (3) should land in parallel with (2) so the design-system text spec, the rendered visual reference, and the live JSX all converge in the same commit (per the design-system invariant that SPEC + visual reference + live implementation must always agree). Bug 6 (Phase 4 Issues/Comments missing from cards) should be folded into this work because it is the same primitive — fixing it without (2) means doing the layout twice.
  > Cross-reference: this Improvement is the operational follow-up to Investigate 1 above. The recovered visual reference lives at `/Users/alexlisitzky/dual-research/handoffs/ds-v2-audit/badge-governance-mockup-iter3.html` and can be opened locally during this session at `http://127.0.0.1:8766/handoffs/ds-v2-audit/badge-governance-mockup-iter3.html`.

---

## B15 — Canonical prompt-pieces + per-attachment token tracking
- **Type:** feature
- **Area:** protocol prompt-pieces / artifact registry / consumption tab / full-view modals / how-it-works diagram
- **Severity (if a bug):** n/a
- **Repro signal:** code-pointer
- **Cross-links:** B05, B16
- **Verbatim quote:**
  > ## Improvement 5 — Canonical prompt-pieces, per-attachment token tracking, and full-view alignment
  > ### Interpretation
  > The Deep Research protocol already has a canonical artifact registry (Spec 0117) and a per-piece token-attribution emitter (Spec 0118) that the Consumption tab consumes. Four drifts have accumulated between the registry, the emitter, the UI, and the user-facing documentation, and they need to be closed together because they all stem from one root cause — divergence from the registry — and because the Consumption tab and the full-view modals can only stay in sync if they're driven from the same canonical piece dict.
  > **The four drifts:**
  > 1. **The ****`user_prompt`**** composite is collapsed in the emitter.** `src/dual_research/protocol/prompt_pieces.py` emits a single `user_prompt` key per phase, even though the registry already templates `user_prompt.message` and `user_prompt.attachment.<id>` (`src/dual_research/contract/artifacts.py:167-170`). Attachments therefore get no individual token share in Consumption and no individual row in any full-view modal.
  > 2. **Two registry entries are dead.** `system.preamble` (`artifacts.py:151`) and `system.task.closeout` (`artifacts.py:163`) are defined but never emitted as pieces. The diagram does not mention either; the UI cannot render either; the Consumption tab never receives either.
  > 3. **`run-detail.jsx`**** carries a legacy piece vocabulary parallel to the registry.** `INPUT_PIECE_ORDER = ['system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']` (`run-detail.jsx:5085`) drives every full-view input panel and every per-phase grouping. These short keys are not the canonical IDs the aggregator emits — they're a pre-0117 mapping that the input-bundle layer translates into. The result is that the Consumption tab (canonical IDs) and the full-view modals (legacy keys) are speaking two languages about the same pieces.
  > 4. **The user-facing documentation no longer matches the protocol.** `diagrams/deep-research-pipeline.{light,dark}.svg` — the diagram with informal but accurate labels for every per-phase input/output — is unreferenced (`how-it-works.jsx:56`). How It Works embeds `02-phase-inputs.{light,dark}.svg` in the per-phase slot instead, but its labels aren't keyed to the registry either, and it only shows inputs (not outputs or agreements).
  > The user-visible consequence is that the **briefing full view** currently shows the original chat message under "User prompt" + a system block under "System prompt", but does not surface attachments under that User-prompt section, does not surface a methodology preamble (if one exists), and does not align its labels with the Consumption tab's piece names. The **side-by-side modals** (NegotiateReviewModal / DraftReviewModal) read input bundles via the legacy vocabulary, so the left "contested input" pane and the input sub-pane are not labelled by canonical artifact ID.
  > **Scope cut, made explicit:** Outputs are explicitly out of scope for per-piece token decomposition. Output artifacts keep their canonical IDs for provenance and timeline labelling, but `output_tokens` stays atomic per turn (provider-reported, not estimated per output piece). This is a deliberate scope cut to keep the work focused on the input side, which is where the cost-visualization gap lives today.
  > ### Proposed change — eight coordinated workstreams
  > **1) Decompose ****`user_prompt`**** into composite pieces in the emitter.** In `src/dual_research/protocol/prompt_pieces.py`, every `pieces_for_*()` function changes its `user_prompt` parameter from a single string to a composite. Replace `user_prompt: str` with `user_prompt_message: str, attachments: Iterable[Attachment]` where `Attachment` is `(id: str, title: str, content: str)`. Migrate every call site in `orchestrator/dr_run.py` (`dr_run.py:573, 716, 721, 892, 1103, 1252`).
  > Emitted keys per phase after the change:
  > - **P0** → `system.task.input`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `prior_turns.phase0`, `ledger.standing_items`, `closeout.request` (round-conditional)
  > - **P1** → `system.task.research_plan`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`
  > - **P2** → `system.task.plan_negotiation`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, `prior_turns.phase2`, `ledger.standing_items`, `closeout.request`
  > - **P3** → `system.task.drafting`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, `phase2.agreement.plan`, `all_p2_turns`, `carry_forward.phase2`
  > - **P4** → `system.task.review`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `current_draft`, `prior_turns.phase4`, `ledger.standing_items`, `closeout.request`
  > The aggregate `user_prompt` key is **dropped** from the emitted dict. The Consumption tab's per-phase grouping in Spec 0118 already groups by prefix (`user_prompt.*`) so per-section totals continue to roll up correctly. A small renderer adjustment in the Consumption tab presents the composite under a single "User prompt" group label by default, expandable to the per-attachment breakdown.
  > **2) Investigate ****`system.preamble`**** and ****`system.task.closeout`****; either wire up or delete.** Both are registered with display names but never produced by any `pieces_for_*()` function. Read `src/dual_research/protocol/prompts.py` and `protocol/blocks.py`. If a methodology preamble is actually prepended to every system prompt, plumb a `system_preamble: str` argument through every `pieces_for_*()` function and emit `system.preamble`. If not, delete the `ArtifactDef` line in `contract/artifacts.py`. Same shape for `system.task.closeout`: if its content is subsumed by `closeout.request`, delete the registry entry; if not, add the emission. The investigation is small and bounded — read those two files, decide, and land 1-2 emitter lines or remove 1-2 registry lines. Do not defer.
  > **3) Replace the legacy UI piece vocabulary with canonical artifact IDs.** In `src/dual_research/ui/static/run-detail.jsx`, the legacy keys `'system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'` are removed from `INPUT_PIECE_LABEL` (`5071-5080`), `INPUT_PIECE_ORDER` (`5085`), and `INPUT_PIECE_DEFAULT_COLLAPSED` (`5089`). They are replaced by:
  > - A `displayNameOf(canonicalId, attachmentTitles)` helper that ports the Python `artifacts.display_name()` logic to JS.
  > - A canonical-ID order list defined per phase, matching the diagram's arrival-order numbering.
  > Every reader (`InputTabContent`, `AgentInputDualPane`, the Consumption tab's piece-bar renderer) reads pieces by canonical ID. The aggregator stops translating canonical → legacy at the input-bundle boundary; canonical IDs flow end-to-end. A small new module `src/dual_research/ui/static/artifact-display.js` holds the registry template list (mirrored from `contract/artifacts.py`), `displayNameOf()`, and `phaseOrderFor(phaseNum)`. The Python side and the JS side stay in sync via a CI test (see Test plan).
  > **4) Full-view single-view modals: drive sections from canonical pieces.** `InputBriefModal` and `PreflightResponseModal` (`run-detail.jsx:5636, 5682`) restructure to three sections:
  > - **System prompt** — one row per `system.*` piece in the emitted dict (typically `system.task.<phase>`, plus `system.preamble` if wired in §2).
  > - **User prompt** — one row for `user_prompt.message`, then one row per `user_prompt.attachment.<id>` in attachment order. Each attachment row shows the title (from `attachments.json`), the piece's estimated tokens, and the rendered content (markdown for text attachments; thumbnail for images; download link for binary).
  > - **Derived inputs** — one row per remaining piece (`prior_turns.phase{N}`, `ledger.standing_items`, `closeout.request`, prior agreements/plans/drafts when the phase has them). Collapsed by default.
  > The existing `Sources` and `Files` tabs on `InputBriefModal` (`5659-5667`) are removed — that information is now native to the User-prompt section. The `Content` tab stays (rendered standalone, still useful) but is renamed `User prompt` to match the section label.
  > **5) Full-view side-by-side modals: canonical labels on both panes.** `NegotiateReviewModal` and `DraftReviewModal` (`3982, 4414`) update so that:
  > - **Left pane** ("Original" sub-tab) — the document currently shown is labelled by its canonical artifact ID rather than by a path or a phase-specific phrase. The mapping is per phase × round, already implemented in `leftPaneTabsFor()` (`4928-4960`); this change is label-only:
  >   | Card | Left-pane document → canonical artifact ID |
  >   |---|---|
  >   | P0 round 1 | `user_prompt.message` |
  >   | P0 round N≥2 | `phase0.<other_agent>.r<N-1>` |
  >   | P1 plan | `user_prompt.message` |
  >   | P2 round 1 | `phase1.<other_agent>` |
  >   | P2 round N≥2 | `phase2.<other_agent>.r<N-1>` |
  >   | P3 draft | `phase2.agreement.plan` |
  >   | P4 round 1 | `current_draft` (= `phase3.draft.v1` at this point) |
  >   | P4 round N≥2 | `phase4.<other_agent>.r<N-1>` |
  > - **Input sub-tab** — replaces `AgentInputDualPane`'s legacy-keyed layout with the same canonical-piece layout used by the single-view modals (System / User prompt / Derived). Still dual-pane (Claude vs GPT) where both agents share the same input set.
  > - **Right pane (Q/D/I/C critique)** — layout unchanged; confirm items are read from `run.phaseReviewItems[phase{N}Round{R}{Agent}]` (`4996`) and that filter chips match the categories the phase emits (P0/P2 = Q/D; P4 = Q/D/I/C; P1/P3 = none).
  > **6) Per-attachment persistence and aggregator support.** Confirm `src/dual_research/ui/aggregator.py` forwards `promptPieces` in the `TurnEnded` event unchanged. If it currently normalises keys, remove that normalisation. `src/dual_research/ui/models.py` widens any typed piece-dict schema to `dict[str, int]` keyed by canonical IDs (the registry's `is_known()` is the validator). Per-turn `inputs/<turnKey>.json` keys change to canonical IDs in the same migration. **Backfill is out of scope** — historical runs render with whatever keys they recorded; a thin UI shim reads either vocabulary during the transition release.
  > **7) Regenerate the canonical pipeline diagram.** `diagrams/deep-research-pipeline.{light,dark}.svg` is regenerated with labels that resolve **byte-identical to what ****`display_name(id)`**** returns** for the canonical registry IDs the code actually emits. Visual + structural baseline (Pixel design language, viewBox, palette, chip legend, section ordering) preserved. Labels swap to:
  > - Persistent input strip: `user_prompt.message` → "Chat message", then one row per `user_prompt.attachment.<id>` resolved to template `Attachment · {title}`. Three illustrative rows with placeholder titles + a continuation row, matching today's visual density.
  > - All `system.task.*` rows keyed to their registry IDs.
  > - All round-conditional rows keyed to `prior_turns.phase{0,2,4}`, `ledger.standing_items`, `closeout.request`.
  > - All outputs keyed to `phase{N}.<agent>.r<N>`, `phase1.claude`, `phase1.openai`, `phase3.draft.v1`, `phase4.draft.v<N>`.
  > - All agreements keyed to `phase{N}.agreement.<kind>`.
  > - FINALIZE inputs/output keyed to `current_draft`, `all_carry_forward`, `final.document`.
  > Additions or removals driven by §1 and §2: per-attachment rows in the persistent input strip replace the informal "Attachment 1 / 2 / 3" sketch; `system.preamble` and `system.task.closeout` rows appear or are absent depending on §2's investigation outcome. Both authoring (`diagrams/`) and bundled (`src/dual_research/ui/static/diagrams/`) copies regenerated together.
  > **8) Wire the regenerated diagram into How It Works.** `src/dual_research/ui/static/how-it-works.jsx` currently embeds `02-phase-inputs.{light,dark}.svg` in three places (`748, 770, 799`). The three `HiwDiagram` references change `diagramName: '02-phase-inputs'` → `diagramName: 'deep-research-pipeline'`. Alt-text updates to "Dual Research pipeline — every named input and output per phase, keyed to the canonical artifact registry". The cache-bust suffix in `HiwDiagram`'s `src` template (`519`) bumps from `v=0133a` → next free value so existing clients refetch. The how-it-works changelog gains a new release note pointing to this work and explaining the diagram is now keyed to registry IDs. The old `02-phase-inputs.{light,dark}.svg` is left on disk for one release as a deprecation grace; a follow-up cleanup removes it. **Two diagrams claiming to be "the per-phase view" is the original sin this work is fixing** — one canonical source, fed by the registry, is the entire point.
  > ### Test plan
  > - **Unit:** `pieces_for_*()` emit `user_prompt.message` + zero-or-more `user_prompt.attachment.<id>` for every phase that takes a user prompt; no aggregate `user_prompt` key remains in any return value.
  > - **Unit:** per phase, full set of canonical keys asserted against the diagram's arrival-order list, gated by the round/blocked conditionals.
  > - **Unit:** `is_known()` returns True for every key any `pieces_for_*()` can emit; CI fails on the first orphan key.
  > - **Unit (cross-language):** `artifact-display.js`'s template list parses from a JSON dump emitted by `contract/artifacts.py` at build time; Python and JS template lists must compare equal.
  > - **Unit:** `displayNameOf('user_prompt.attachment.foo', {foo: 'My document'})` returns `Attachment · My document`; falls through to the literal ID when no template matches.
  > - **Integration:** smoke session with a brief + 2 attachments; every `pieces_for_*()` emits two `user_prompt.attachment.<id>` keys, `inputs/<turnKey>.json` persists them, aggregator forwards them in `TurnEnded` payloads.
  > - **Manual:** briefing card full view on a multi-attachment run — System prompt and User prompt sections present, User prompt section lists chat message followed by one row per attachment with its title, no Sources/Files tabs remain.
  > - **Manual:** P0/P2/P4 round modal — left pane shows the document labelled by its canonical artifact ID; Input sub-tab matches the canonical-piece layout; right pane shows expected Q/D (and Q/D/I/C for P4).
  > - **Manual:** Consumption tab — User-prompt group has an expand affordance that reveals per-attachment rows; collapsed view sums to the same total as today's `user_prompt` segment.
  > - **Visual regression:** snapshot `InputBriefModal` and one card per phase × round combination before/after; only intended deltas are (a) attachments now in-section, (b) labels via `displayNameOf()`.
  > - **Diagram parity (programmatic, CI):** extract every text label from `diagrams/deep-research-pipeline.{light,dark}.svg`; assert every label representing a piece resolves through `display_name(<registry-id>)` to that exact string. Structural labels (`PHASE 0`, `INPUTS · in order`, the chip legend, numeric markers) whitelisted. **CI fails closed when a diagram label has no canonical-ID origin OR when a new registry piece is missing from the diagram.** This is the mechanism that prevents the drift from coming back.
  > - **Diagram parity (light vs dark):** identical text labels in both variants; only palette tokens differ.
  > - **Manual:** How It Works page — three `HiwDiagram` slots that used `02-phase-inputs` now render `deep-research-pipeline`; theme switching still swaps light ↔ dark; cache-bust query string forces a refetch; labels match the same display strings the run-detail modals show.
  > ### Risks
  > - **Cross-language template drift.** Python `REGISTRY` and JS `REGISTRY` can fall out of sync. Mitigation: CI test dumps `REGISTRY` to JSON at build time and asserts the JS file matches; failing CI is the only path to green merge.
  > - **Persistence format change.** `inputs/<turnKey>.json` keys change. Mitigation: read-path shim that accepts both legacy short keys and canonical IDs during the transition release; shim removal tracked in a follow-up.
  > - **Aggregator key normalisation regressions.** Removing prior normalisation can corrupt per-phase totals. Mitigation: regression test loading a recorded fixture run; assert piece totals per phase pre/post-refactor.
  > - **`system.preamble`**** investigation finds an actual preamble.** Wiring it through every emitter touches every phase's call site. Mitigation: §2 lands first so the rest of the work absorbs the signature change in one pass.
  > - **Visual regressions in side-by-side left-pane labels.** "Other's prior turn" → `phase0.<agent>.r<N-1>` display name reads differently. Mitigation: confirm `displayNameOf()` resolution renders human-friendly strings before merge; snapshot tests catch structural breakage.
  > - **Diagram-vs-registry drift returning.** Without an enforcement mechanism the drift comes back next time someone adds a piece. Mitigation: the CI diagram-parity test runs on every PR; the list of intentionally-omitted registry IDs is an explicit allowlist, forcing each omission to be declared.
  > - **`02-phase-inputs.svg`**** orphan during deprecation.** File on disk for one release means any out-of-tree reference (a doc, a Notion embed, a screenshot caption) keeps pointing at the now-stale diagram. Mitigation: deprecation follow-up filed at merge time, deletion tied to the next minor release.
  > ### Open questions for review
  > - **Attachment row labels in Consumption tab** — render the attachment title (from `attachments.json`) or the raw `<id>`? Default: title via `displayNameOf()` with `attachmentTitles` map; raw ID as fallback.
  > - **Legacy-key shim sunset deadline** — encode as a `# REMOVE AFTER` comment in `run-detail.jsx`, or track solely as a follow-up? Default: both — comment for in-file visibility, follow-up for ownership.
  > - **P3 left-pane label** — `phase2.agreement.plan` (proposed) vs `phase0.agreement.interpretation`. Both reasonable; the agreed plan is the more proximate cause of the draft.
  > - **02-phase-inputs replacement vs coexistence** — proposed: replace, on the grounds that two diagrams claiming "the per-phase view" is the drift this work is closing. Coexistence would keep both as a lightweight summary + detail view.
  > ### Cross-references
  > - Spec 0114 — Deep Research protocol (defines the phase structure this work documents).
  > - Spec 0117 — Artifact registry + display names (the canonical IDs this work makes load-bearing).
  > - Spec 0118 — Consumption tab + per-piece token tracking (the consumer this work feeds).
  > - The pre-existing draft of this work was on `main` at commits `757c588` and `af0890f` (file `specs/0139-canonical-prompt-pieces-and-full-view-alignment.md`) and is being moved off `main` to free the `0139` slot for review prioritization.

---

## B16 — Consumption card visual rework + spec-0139 preview rendering (Spec 0140)
- **Type:** feature
- **Area:** consumption tab / CcxCard / design-system v2 / spec 0140
- **Severity (if a bug):** n/a
- **Repro signal:** spec-pointer
- **Cross-links:** B15, B03
- **Verbatim quote:**
  > # Spec 0140 — Consumption card visual rework + spec-0139 preview rendering
  > ```yaml
  > spec: 0140
  > title: Consumption card visual rework + spec-0139 preview rendering
  > label: feature
  > version-bump: MINOR
  > status: proposed
  > target-version: 1.10.0
  > created: 2026-05-21
  > depends-on: 0100, 0118, 0139
  > pr: ""
  > ```
  > > **Status note (2026-05-21):** all of the visual changes below have been prototyped end-to-end in a local working tree against run `20260521-010637-dvs-backend-language-choice`. This spec captures the prototype verbatim so it can be re-implemented from a clean branch with proper tests + design-system updates. **Nothing has been committed or pushed.**
  > ## Context
  > The Consumption tab's card component (`CcxCard` in `src/dual_research/ui/static/run-detail.jsx`, currently SPEC-0100 / spec-0118 anatomy) had drifted from the design-system §14 reference (`design-system/SPEC.md` §4.3 + `design-system/assets/Design System v2.html` lines 1086–1288) in four ways:
  > 1. **Header trio missing.** Live header showed only `(X% of 1M)` next to the chevron; the design system specifies `Xkt total · $cost · X% of cap`.
  > 2. **Single Total-tokens bar instead of total-in + total-out.** Spec 0118 collapsed both bars into one combined bar; the design system wants both as section-header bars.
  > 3. **No per-piece breakdown that matches the registry.** Live unfolded view had ad-hoc rows (`User prompt`, `System prompt`, `Output`) instead of the design-system 5-bucket vocabulary (system prompt · conversation history · round context · tool definitions · web sources) or the spec-0139 canonical per-phase list.
  > 4. **No totals block.** Live used a free-text mono line (`9.2kt seen · 246.1kt billed (× 27.0 token reuse) · 11.8kt out`) instead of the `.ccx-totals` block (input billed / input cost / web search / cache savings / total input).
  > In parallel, spec 0139 defines the canonical per-phase input piece list that the backend will emit once §1 of that spec ships (`pieces_for_*()` decomposes `user_prompt` into `user_prompt.message` + `user_prompt.attachment.<id>`). The Consumption tab needs to render those canonical pieces with their registry display names — and ideally, **render the full anatomy today** using extrapolated placeholders for keys the backend doesn't yet emit, so the team can see what the final look will be before the backend lands.
  > User-facing iterations during prototyping further refined the design beyond design-system §14:
  > - **Single combined Total-tokens bar in collapsed view** (not the two-bar design-system reference). Two bars only appear when unfolded.
  > - **`(X% of 1M)`**** right-aligned to the bar's right edge** (not next to the chevron).
  > - **Totals block: label left, value right** (mirroring the bar-row layout above it).
  > - **One-decimal precision** for all cost displays inside the Consumption card.
  > These four divergences are intentional and should be back-ported into the design-system spec (see §11).
  > ## Proposed change
  > ### 1. Collapsed view: single combined Total-tokens bar
  > Replace the two-bar `total in` / `total out` collapsed anatomy from design-system §14 with a single `Total tokens` bar covering input + output tokens.
  > **Bar row anatomy** (collapsed):
  > ```javascript
  > [Total tokens label] [bar — fill: agent color | overlay: cache reuse stripe] [Xt · $X.X]
  > ```
  > Where:
  > - Label = literal string `Total tokens` (capital T).
  > - Bar fill width = `(in + cacheRead + cacheWrite + out) / scale.denom`.
  > - Reuse stripe width = `cacheRead / scale.denom`, clamped inside the fill (only renders when `cacheRead > 0`).
  > - Right text = `${fmt.tokens(in + cacheRead + cacheWrite + out)}t · ${fmtCost1(cost)}` — combined tokens + one-decimal cost.
  > The bar uses the agent's `in` fill class (`.fl.in` for Claude, `.fl.in-b` for GPT). No separate `total out` bar in collapsed view.
  > ### 2. Header grid: percent right-aligns to the bar end
  > Convert `.ccx-header` from `display: flex` to a 3-column grid that matches the bar-row grid (`140px 1fr 100px`). The header columns become:
  > | Col | Content | Justification |
  > |---|---|---|
  > | 1 (140px) | `.hd-id` wrapper containing `.ccx-icon`  • `.nm` | inline-flex, gap 10px |
  > | 2 (1fr) | `.stats` containing only `(X.X% of 1M)` | right-aligned (`justify-self: end`) |
  > | 3 (100px) | `.chev` | right-aligned (`justify-self: end`) |
  > Result: the closing `)` of the percentage sits at exactly the same x-coordinate as the right edge of the bar fill in the row below (the boundary between col 2 and col 3). Pixel-verified during prototyping: `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right`.
  > Tokens and cost are **removed from the header stats** — they live only at the end of the Total-tokens bar (collapsed) or inside the totals block (unfolded). The percentage is the only header stat.
  > `.stats { white-space: nowrap; }` prevents the percentage from wrapping when the card is narrow (e.g. side-by-side at \<1280 px viewport).
  > ### 3. Unfolded view: section-header bars Total in / Total out
  > When the card expands, the single Total-tokens bar is replaced with the design-system §14 anatomy:
  > ```javascript
  > ccx-header
  > ccx-bar-row.is-total       Total in    [bar + reuse stripe]    {Xkt}
  > ccx-divider
  > ccx-sub-row × N            input piece breakdown (spec-0139, see §4)
  > ccx-totals                 input totals block (see §5)
  > ccx-section-spacer
  > ccx-bar-row.is-total       Total out   [bar]                   {Xkt}
  > ccx-divider
  > ccx-sub-row × M            output piece breakdown (when measured, see §9)
  > ccx-totals                 output totals block
  > ```
  > Labels are **capital T**: `Total in`, `Total out` — matching the collapsed `Total tokens`. (Design system uses lowercase `total in` / `total out`; this spec back-ports the capitalization.)
  > ### 4. Spec-0139 canonical input sub-rows
  > The `.ccx-sub-row` list under `Total in` is driven by spec 0139's per-phase canonical-ID list, in arrival order. A static table in `run-detail.jsx`:
  > ```javascript
  > const SPEC_0139_PHASE_PIECES = {
  >   0: [
  >     'system.task.input',
  >     'user_prompt.message',
  >     'user_prompt.attachment.<id>',
  >     'prior_turns.phase0',           // R2+ only
  >     'ledger.standing_items',
  >     'closeout.request',             // closeout round only — suppressed in MVP
  >   ],
  >   1: [
  >     'system.task.research_plan',
  >     'user_prompt.message',
  >     'user_prompt.attachment.<id>',
  >     'phase0.agreement.interpretation',
  >   ],
  >   2: [
  >     'system.task.plan_negotiation',
  >     'user_prompt.message',
  >     'user_prompt.attachment.<id>',
  >     'phase0.agreement.interpretation',
  >     'phase1.claude',
  >     'phase1.openai',
  >     'prior_turns.phase2',           // R2+ only
  >     'ledger.standing_items',
  >     'closeout.request',             // suppressed in MVP
  >   ],
  >   3: [
  >     'system.task.drafting',
  >     'user_prompt.message',
  >     'user_prompt.attachment.<id>',
  >     'phase0.agreement.interpretation',
  >     'phase1.claude',
  >     'phase1.openai',
  >     'phase2.agreement.plan',
  >     'all_p2_turns',
  >     'carry_forward.phase2',
  >   ],
  >   4: [
  >     'system.task.review',
  >     'user_prompt.message',
  >     'user_prompt.attachment.<id>',
  >     'current_draft',
  >     'prior_turns.phase4',           // R2+ only
  >     'ledger.standing_items',
  >     'closeout.request',             // suppressed in MVP
  >   ],
  > };
  > ```
  > Each ID resolves to its display name via `window.DrArtifacts.displayName(id, { titleForId })` — the existing JS port of the Python `display_name()` (artifacts.jsx).
  > **Round-conditional handling:**
  > - `prior_turns.*` is omitted when the turn's round is 1.
  > - `closeout.request` is **always suppressed in MVP**: the card doesn't yet know whether the round was a closeout round. Wiring this up requires the aggregator to surface `was_closeout: bool` per turn — tracked as backend follow-up (§9).
  > **Attachment expansion:** the template `user_prompt.attachment.<id>` is expanded into N rows, one per attachment in the run. When `run.attachments` is missing (every shipped run today), a 2-row preview placeholder is used:
  > ```javascript
  > const PREVIEW_ATTACHMENTS = [
  >   { id: 'briefing', title: 'Briefing document' },
  >   { id: 'context',  title: 'Supplementary context' },
  > ];
  > ```
  > **Fill-class mapping** (which color lane each piece reads in):
  > | Pieces | Fill class | Rationale |
  > |---|---|---|
  > | `system.*` | `sys` | system instructions — sable-tinted |
  > | `user_prompt.*` | `round` | per-round inputs |
  > | `prior_turns.*` | `hist` | conversation history, cache-amplified |
  > | `phase{1,2,3,4}.{claude,openai}`  • `phaseN.<agent>.r<N>`  • `all_p2_turns` | `hist` | prior agent output re-read |
  > | `phaseN.agreement.*` | `round` | round context |
  > | `current_draft`, `carry_forward.*`, `ledger.standing_items`, `closeout.request` | `round` | round context |
  > ### 5. Totals block — labels left, values right
  > `.ccx-totals .line` keeps `display: flex; justify-content: space-between;` but the DOM child order is swapped: `<span class="l">label</span><span class="v">value</span>`. Visual result:
  > ```javascript
  > input tokens · billed       160,942
  > input cost                  $0.5
  > web search · 2 queries      $0.0
  > total input                 $0.5      ← .is-grand: bold rule above, larger value
  > ```
  > Reasoning: the totals block now mirrors the bar-row pattern above it (`Total in [bar] 160.9kt` — label left, value right) instead of inverting it.
  > ### 6. One-decimal cost formatter, scoped to the Consumption card
  > Add `fmtCost1(n)` in `run-detail.jsx`:
  > ```javascript
  > function fmtCost1(n) {
  >   const v = Number(n) || 0;
  >   return `$${v.toFixed(1)}`;
  > }
  > ```
  > Apply **only inside ****`CcxCard`** to:
  > - Header stats cost
  > - Bar-row right text (cost half of `Xt · $X.X`)
  > - Every line in the input + output totals blocks
  > The global `fmt.cost` keeps its 4-decimal precision (`$0.0541`) for:
  > - Run-detail footer aggregate (`$0.5076 + $1.8051 = $10.3127`)
  > - Reconcile delta column
  > - Turn-status chips outside the Consumption tab
  > - Tooltip strings
  > This is intentional — the Consumption card is a glance-view; precision lives where the user is auditing numbers (reconcile, footer totals).
  > **Known cosmetic issue:** sub-dollar costs that round to zero display as `$0.0`, which reads as "free". For example, `searchCost: 0.02` → `$0.0`. Two ways to handle (open question §13):
  > - (a) Render `<$0.1` for any non-zero amount under 5¢
  > - (b) Keep `$0.0` — the user understands one-decimal precision and the totals block carries the truth
  > Default for this spec: (b). Switch to (a) if it tests poorly.
  > ### 7. Synthetic-row preview indicator
  > Rows backed by extrapolated values (not present in the turn's real `promptPieces`) render with three subtle markers:
  > 1. **Opacity 0.62** on the entire `.ccx-sub-row`.
  > 2. **Diagonal-stripe pattern** layered over the bar fill: `repeating-linear-gradient(45deg, transparent 0 4px, rgba(255,255,255,0.18) 4px 6px)`.
  > 3. **`preview`**** chip** in the `.num` slot before the token count: dashed `1px` outline, transparent fill, faint text color.
  > Tooltip on each synthetic row: `Preview · the backend doesn't yet emit ${id}; this row is extrapolated (spec 0139).`
  > When the backend ships spec 0139 §1 (per-attachment emission), `promptPieces` will contain `user_prompt.attachment.<id>` keys and the rows flip from `synthetic: true` to `synthetic: false` automatically — no card-side changes needed.
  > ### 8. CamelCase converter mirroring `_snake_to_camel`
  > Server-side `_to_camel` (`src/dual_research/ui/server.py:1879`) runs `_snake_to_camel` on every dict key as a single string, treating `.` as an ordinary character. So `prior_turns.phase2` → `priorTurns.phase2` and `system.task.research_plan` → `system.task.researchPlan`.
  > The JS-side resolver must mirror this exactly:
  > ```javascript
  > function _canonicalToCamelKey(id) {
  >   return id.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
  > }
  > ```
  > This is a **regression-prone** change — an earlier prototype split on `.` first and only camelized within each segment, which incorrectly produced `prior_turns.phase2` and silently missed every `priorTurns.*` key in the live data. A unit test pinning the camelCase output for a handful of canonical IDs is in the test plan.
  > ### 9. Pre-spec-0139 backward-compat fallback
  > Until spec 0139 §1 ships, every emitter writes a single `user_prompt` key holding the aggregate. To avoid the "Chat message" row reading as `preview · 420` on every existing run, fall back:
  > ```javascript
  > if (realTokens === 0 && id === 'user_prompt.message') {
  >   realTokens = Number(piecesRaw?.userPrompt) || 0;
  > }
  > ```
  > Once spec 0139 §1 lands, both keys may coexist briefly; prefer `user_prompt.message` when present. Remove the fallback in the next minor release.
  > ### 10. Output sub-rows + cache savings — placeholders for backend follow-up
  > Two pieces of the design-system §14 anatomy require backend work and **render as empty / missing** today:
  > | Row(s) | Backend gap | Today's behaviour |
  > |---|---|---|
  > | `reasoning` / `response` / `tool calls` under Total out | Backend reports only total `out`; no breakdown shipped | Output sub-row list is empty; totals block carries the single number |
  > | `cache savings · ×N reuse on Xk` line in input totals block | Per-model input-rate not shipped to frontend; can't compute `(input_rate − cache_rate) × cacheRead` client-side | Line is omitted entirely |
  > When the backend lands these, the card renders them automatically:
  > - Output breakdown: `usage.outputBreakdown.{reasoning, response, toolCalls}` is the contract.
  > - Cache savings: either ship `usage.cacheSavingsUsd` directly, or ship the per-model rates in the run snapshot so the frontend can compute it.
  > ### 11. Design-system spec updates (back-port the divergences)
  > Four updates to `design-system/SPEC.md` §4.3 + the example HTML (`design-system/assets/Design System v2.html` §14):
  > 1. **Collapsed view becomes single Total-tokens bar** (replace the two-bar reference).
  > 2. **Header trio drops to single percentage**, right-aligned to bar end (not flex-end next to chevron).
  > 3. **Totals block flipped**: labels left, values right.
  > 4. **One-decimal precision** on all cost displays inside the card; document the `<$0.1` decision per §6.
  > `design-system/CHANGELOG.md` gets a new entry pointing at this spec.
  > ### 12. Live CSS updates (components.css mirror)
  > `src/dual_research/ui/static/components.css` is the live mirror of `design-system/assets/styles/composed-components.css` for the production app. Both files need the same `.ccx-header` grid changes. Patch:
  > ```css
  > .ccx-header {
  >   display: grid;
  >   grid-template-columns: 140px 1fr 100px;
  >   align-items: center;
  >   gap: 12px;
  >   padding-bottom: 4px;
  > }
  > .ccx-header .hd-id {
  >   display: inline-flex; align-items: center; gap: 10px;
  >   min-width: 0; overflow: hidden;
  > }
  > .ccx-header .stats {
  >   justify-self: end;
  >   white-space: nowrap;
  >   /* (rest unchanged) */
  > }
  > .ccx-header .chev {
  >   justify-self: end;
  >   /* (rest unchanged — width/height/flex untouched) */
  > }
  > ```
  > `.stats { margin-left: auto; }` is **removed** — flex semantics don't apply under grid.
  > ### 13. Cache-buster version bump
  > `src/dual_research/ui/static/index.html` bumps `?v=0138a` → `?v=0140a` so existing clients refetch all CSS + JSX after deploy. (During the prototype iteration the buster cycled through `0139a` → `0139h`; the merged commit should land at `0140a`.)
  > ## Out of scope
  > - **Output-piece decomposition.** §10 documents the contract for when it lands; this spec doesn't ship it.
  > - **Cache-savings computation.** §10 documents the contract; this spec doesn't ship the per-model rate table to the frontend.
  > - **Closeout-round detection.** `closeout.request` row stays suppressed until the aggregator emits `was_closeout` per turn.
  > - **Spec-0139 §1 (emitter decomposition).** This spec consumes whatever `promptPieces` ships; the emitter side is owned by spec 0139.
  > - **Compare-tab / cross-run views.** Same `CcxCard` is used there, so the visual changes flow through, but no compare-specific tweaks.
  > - **Mobile / \<900px breakpoint.** Current grid `140px 1fr 100px` works down to \~720px card width. Narrower viewports get tested separately.
  > - **Light-mode parity.** Existing token-driven CSS handles it; the prototype was verified in dark only. Visual regression catches any drift.
  > ## Backend follow-up (separate spec, not this PR)
  > Tracked here so they're not forgotten when this lands:
  > 1. **Spec 0139 §1** — `pieces_for_*()` emit `user_prompt.message` + `user_prompt.attachment.<id>`. Without this, the Chat-message row uses the fallback in §9 and attachment rows stay marked `preview`.
  > 2. **Output breakdown** — record reasoning vs. response vs. tool-call tokens per turn. Anthropic's extended-thinking API exposes a reasoning-tokens field; OpenAI's `usage.completion_tokens_details.reasoning_tokens` likewise. Tool-call token cost is recoverable from the assistant message's `tool_calls` field length.
  > 3. **Cache savings** — either ship `usage.cacheSavingsUsd` (server computes; clean) or ship per-model `input_per_mtok` + `cache_read_per_mtok` in the run snapshot (frontend computes; more flexible).
  > 4. **Closeout detection** — surface `was_closeout: bool` on every `TurnTokenUsage` so the `closeout.request` row renders when relevant.
  > 5. **Web-source tokens** — split the input-token cost of fetched search-result snippets out from the prompt-piece dict so a real `web sources` row + token count is renderable.
  > 6. **Tool-definitions tokens** — split the input-token cost of tool definitions out from the system prompt aggregate.
  > 7. **Attachments in the run snapshot** — `run.attachments` is currently undefined in the API payload; pipe through from `attachments.json` so the per-attachment row labels resolve from real titles instead of the `PREVIEW_ATTACHMENTS` placeholder.
  > ## Test plan
  > ### Unit (Python — unchanged)
  > - [ ] `_to_camel` round-trips `prior_turns.phase2` ↔ `priorTurns.phase2`. (Already covered by existing tests; this spec is a consumer, not a modifier.)
  > ### Unit (JS)
  > - [ ] `_canonicalToCamelKey('prior_turns.phase2') === 'priorTurns.phase2'`
  > - [ ] `_canonicalToCamelKey('system.task.research_plan') === 'system.task.researchPlan'`
  > - [ ] `_canonicalToCamelKey('ledger.standing_items') === 'ledger.standingItems'`
  > - [ ] `_canonicalToCamelKey('phase1.claude') === 'phase1.claude'` (no-op for already-camel keys)
  > - [ ] `fmtCost1(0.5028) === '$0.5'`; `fmtCost1(0.02) === '$0.0'`; `fmtCost1(undefined) === '$0.0'`
  > - [ ] `buildSpec0139InputBuckets({}, {}, 2, 1, {})` returns the P2 piece order minus `prior_turns.phase2` (R1)
  > - [ ] `buildSpec0139InputBuckets({ userPrompt: 5251 }, {}, 2, 3, {})` returns a row where `id === 'user_prompt.message'`, `tokens === 5251`, `synthetic === false` (backward-compat fallback)
  > - [ ] `buildSpec0139InputBuckets({ 'user_prompt.message': 400 }, {}, 2, 3, {})` prefers the canonical key over the legacy aggregate
  > ### Visual / integration (manual)
  > - [ ] Open `/#/runs/<recent-run>` → Consumption tab. Verify:
  >   - [ ] Header shows `<name>` left, `(X% of 1M)` right-aligned to bar end, chevron flush right.
  >   - [ ] `(X% of 1M)` doesn't wrap when cards render side-by-side at 1280 px viewport.
  >   - [ ] Collapsed shows single `Total tokens` bar with `Xkt · $X.X` at the right.
  >   - [ ] Reuse stripe is visible on the collapsed bar when `cacheRead > 0`.
  > - [ ] Expand a P3 card on a complete run. Verify:
  >   - [ ] `Total in` and `Total out` are section-header bars with capital T.
  >   - [ ] Input sub-rows are in spec-0139 arrival order: `Drafting instructions` → `Chat message` → 2× `Attachment · …` (preview) → `Agreed interpretation` → `Claude's research plan` → `GPT's research plan` → `Agreed plan` → `All negotiation turns` → `Carry-forward items (phase 2)` (preview).
  >   - [ ] Preview rows have dim opacity + dashed-outline `preview` chip + diagonal-stripe bar overlay.
  >   - [ ] Totals block has labels left, values right, one-decimal costs.
  > - [ ] Expand a P2 R1 card. Verify `Prior negotiation turns` is **omitted** (R1).
  > - [ ] Expand a P2 R2+ card. Verify `Prior negotiation turns` **appears** with real data (no preview chip).
  > - [ ] Expand a P0 R1 card on a run that hit cache. Verify the reuse-stripe overlay shows on the `Total in` bar with width proportional to `cacheRead / scale.denom`.
  > - [ ] Compare tab + cross-run search: confirm the same card renders without regression.
  > ### Visual regression
  > - [ ] Snapshot the Consumption tab at:
  >   - `/#/runs/20260521-010637-dvs-backend-language-choice` (P0 → P4 deadlocked)
  >   - `/#/runs/20260518-065852-backend-language-choice-briefing-for-dual-research` (4 attachments)
  > - [ ] Light + dark variants of both.
  > - [ ] Compare before/after the PR; the only intended deltas are the §1–§7 anatomy changes.
  > ### Pixel alignment
  > - [ ] `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right` for every card on the page (programmatic check).
  > ## Risks
  > - **Header overflow at narrow widths.** Cards rendered side-by-side at \<900 px viewport could push the percentage into the chevron column. Mitigation: `white-space: nowrap` on `.stats` + verified down to 720 px during prototyping. If a narrower viewport shows wrapping, drop the col-2 `1fr` to `minmax(80px, 1fr)` to force the chevron to overflow first.
  > - **`fmtCost1`**** regression for sub-cent costs.** `$0.02` rendering as `$0.0` reads as "free" on cards that ran one search. Mitigation: open question §13 decides whether to switch to `<$0.1` representation.
  > - **CamelCase converter bug returning.** §8 describes the precise bug from prototyping (segment-by-segment splitting). Mitigation: explicit unit tests in the test plan + the converter sits next to a comment that documents the bug-prone pattern.
  > - **Preview placeholders mistaken for real data.** Even with three visual markers (opacity, stripe, chip), a user skimming the card could mistake a preview row for measured data. Mitigation: the tooltip text says explicitly "extrapolated (spec 0139)"; the chip text is `preview` not `est` or `~`.
  > - **Design-system spec drifting from live again.** §11 + §12 are deliberately in this spec to land both surfaces together. The composed-components.css and components.css will be kept manually in sync; longer-term, the design system's `audits/` workflow should diff them in CI.
  > - **Spec-0139 §1 lands first.** If the emitter ships before this card, the design-system §14 reference + the live card render real attachments and real `user_prompt.message`. The `synthetic` flag still routes correctly because it's keyed on `realTokens === 0`. No code change needed; just delete the `PREVIEW_ATTACHMENTS` fallback and the unit test for the backward-compat fallback in §9.
  > ## Open questions
  > 1. **Sub-cent cost display** (§6). Switch to `<$0.1` for non-zero amounts under 5¢, or keep `$0.0`? Default: keep `$0.0` for consistency; revisit if user-testing flags it.
  > 2. **`fmtCost1`**** scope.** Apply to the run-detail footer aggregate (`$10.3127` → `$10.3`) for consistency, or keep 4-decimal precision there because it's the "audit number"? Default: keep 4-decimal in the footer.
  > 3. **Capital-T labels.** This spec ships `Total tokens` / `Total in` / `Total out`. Design-system §14 uses lowercase. Spec back-ports the capitalisation. Confirm this is the desired direction (alternative: lowercase everywhere for design-system parity).
  > 4. **`closeout.request`**** suppression.** The MVP suppresses this row entirely. Should we render it as a preview row on every P0/P2/P4 round so users know it exists, with a tooltip explaining "only fires on closeout"? Trade-off: more visible vs. less honest about what the data actually says.
  > 5. **Preview-row totals reconciliation.** The synthetic rows' tokens are NOT summed into the `input tokens · billed` total — the total comes from real `in`. This means rows can total more than the "billed" number when synthetic + real overlap. Worth surfacing in the tooltip or via a "real subtotal · NN%" annotation? Default: ignore; it's a known artifact of preview mode.
  > 6. **Compare-tab impact.** The same `CcxCard` is used in the Compare view. Worth a separate manual test pass even though no compare-specific code changed? Default: yes — already in the test plan.
  > ## Files touched (concrete list for the implementer)
  > ```javascript
  > src/dual_research/ui/static/run-detail.jsx
  >   - rewrite CcxCard (≈220 LOC, replaces SPEC-0100 anatomy)
  >   - add CcxTotalsBlock helper (≈14 LOC)
  >   - add fmtCost1 helper (≈4 LOC)
  >   - add buildSpec0139InputBuckets + supporting constants (≈140 LOC)
  >   - add _canonicalToCamelKey helper (≈3 LOC)
  >   - add buildOutputBuckets (≈10 LOC) — empty until backend ships outputBreakdown
  >   - update ConsumptionView to pass `round` to CcxCard (1 LOC)
  >
  > src/dual_research/ui/static/components.css
  >   - .ccx-header → grid (≈10 LOC)
  >   - .ccx-header .hd-id new rule (≈4 LOC)
  >   - .ccx-header .stats { justify-self: end; white-space: nowrap; } (2 LOC)
  >   - .ccx-header .chev { justify-self: end; } (1 LOC)
  >
  > src/dual_research/ui/static/index.html
  >   - bump ?v=0138a → ?v=0140a (40 LOC, mechanical)
  >
  > design-system/assets/styles/composed-components.css
  >   - mirror the .ccx-header changes from components.css (matches §12)
  >
  > design-system/SPEC.md
  >   - rewrite §4.3 "Consumption row" per §11
  >
  > design-system/assets/Design System v2.html
  >   - rewrite §14 anatomy + examples per §11
  >   - rebuild the consumption HTML mocks to match the new collapsed + unfolded look
  >
  > design-system/CHANGELOG.md
  >   - new entry for spec 0140
  > ```
  > No backend changes in this spec — the contract for `usage.outputBreakdown` and `usage.cacheSavingsUsd` is documented in §10 for the follow-up spec.
  > ## Acceptance criteria
  > This spec is "done" when:
  > - [ ] All §1–§9 anatomy changes are live behind cache buster `?v=0140a`.
  > - [ ] §11 design-system updates merged in the same PR (or a tightly-coupled follow-up — author's call).
  > - [ ] All unit + visual tests in the Test plan pass.
  > - [ ] One real Notion screenshot of the dark-mode unfolded P3 card is attached to the PR description so reviewers see the target.
  > - [ ] The 7 backend follow-ups in §10 are filed as separate specs (or one umbrella spec) so they don't get lost.
