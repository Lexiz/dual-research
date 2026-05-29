---
kind: dev
spec: "0256"
slug: drafter-delta-apply-guard-resync-and-strict-anchor-contract
title: "Guard the drafter-delta apply path against anchor failure, resync the drafter on no-op, and tighten the anchor contract (strict, not fuzzy)"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
disposition: ship
disposition_reason: "Promotion trigger fired — live run 20260529-164844 died at EXIT_RUNTIME with no final.md when an apply-time edit_section_anchor_not_found propagated past the parse-only fallback; this is the binding constraint on phase-4 completion, not latent."
depends_on: []
complexity: L
created: 2026-05-30
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: a-spec-promote-session
promoted_from_draft: "005"
---

<!-- DEV SPEC RULE: this body contains NO open questions, TBD markers, or
"figure it out later" prose. The draft's one open decision (tolerance vs.
fuzzy matching) is resolved in §2.3: strict deterministic normalization,
NOT similarity matching. -->

# Spec 0256 — Guard the drafter-delta apply path, resync the drafter on no-op, and tighten the anchor contract (strict, not fuzzy)

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — adds new resilience behaviour (apply-time fallback, post-no-op resync signal) and a tightened anchor contract; changes phase-4 round mechanics and the closeout/escape-valve partition (an apply-time anchor failure no longer terminates the run). Not behaviour-preserving → not `refactoring`; touches phase mechanics + a parser invariant → not `bug` (per CLAUDE.md "Contract-changing specs are not bugs").
> **Evidence:** live run `runs/20260529-164844-backend-language-choice/` (no `final.md`; `run_failed`×1, `edit_section_anchor_not_found`×4, `phase4_drafter_repair_failed`×2, `repair_drafter_fallback_engaged`×1, `raiser_self_address`×7). Promoted from `draft-005`. Sister surface to spec 0231 (heading-anchor intolerance) and spec 0238 (deterministic tolerant terminator). Cause-of-death is a captured live run on a **real** prior_draft → spec 0238 live-failure-fix discipline applies.

---

## 1. Context

Phase 4's revision loop applies a drafter's `## Revised draft` turn as a set of section-delta ops. The orchestrator helper [`_apply_drafter_revised_draft`](src/dual_research/orchestrator/dr_run.py:1401) wraps **only the parse step** in a `ProtocolParseError` fallback: the `try/except` at [dr_run.py:1439-1446](src/dual_research/orchestrator/dr_run.py:1439) catches a failure of `extract_revised_draft_deltas` and substitutes a `RevisedDraftFull(content=prior_draft)` no-op payload (spec 0231 §2.3). But the **apply step** — `apply_revised_draft_deltas` at [dr_run.py:1454](src/dual_research/orchestrator/dr_run.py:1454) — runs *outside* that `try`. When the parse succeeds but an anchor fails to match at apply time, [`apply_revised_draft_deltas`](src/dual_research/protocol/parse.py:696) raises `ProtocolParseError("drafter", [edit_section_anchor_not_found: …])` ([parse.py:809-839](src/dual_research/protocol/parse.py:809)). That exception propagates uncaught to the run-level `except BaseException` tombstone at [run.py:565](src/dual_research/orchestrator/run.py:565) → `run_failed` → `EXIT_RUNTIME` ([run.py:607](src/dual_research/orchestrator/run.py:607)). The run dies at exit 2 with no `final.md`. This is exactly what happened in `20260529-164844`.

The root cause of the *anchor mismatch* is **state divergence, not whitespace drift.** In that run the round-2 revision no-op'd (the parse-step fallback fired: `phase4_drafter_repair_failed`), so on disk `phase4/draft-v2.md` is the **un-revised** prior. But the drafter was never told its revision was dropped, so its round-3 EDIT_SECTION ops anchor on content it *believed* it wrote in round 2 — e.g. `ANCHOR: ### Section 3 — Tier 2 Scoring Summary` and `ANCHOR: DVS dependencies: Postgres client, Azure SDK (Blob/Queue/Event Grid), OIDC, PDF parsing, crypto.` Neither literal exists on disk; the real heading is `### Section 3 — Tier 2 Scoring: AI-Coding-Automation Fitness (Criterion 2.1, Highest Weight)`. Because the drafter is anchoring on long multi-line body literals against a draft that diverged from its mental model, byte-exact matching cannot recover — and **fuzzy matching would make it worse**: draft-v2.md carries four "Tier 2 Scoring" sections (Sections 3–6), so a similarity match on "Section 3 — Tier 2 Scoring Summary" could silently bind to Section 4/5/6 and corrupt `final.md` into the wrong section.

## 2. Proposed change

Three load-bearing changes plus one secondary prompt fix, in priority order. The first is the run-saving guard; the second removes the divergence that produces the mismatch; the third reduces the surface area that drift can attack — strictly, without fuzziness.

### 2.1 — APPLY-GUARD: an apply-time anchor failure triggers the same no-op fallback as a parse failure

In [`_apply_drafter_revised_draft`](src/dual_research/orchestrator/dr_run.py:1401), extend the `ProtocolParseError` recovery to cover the **apply** call, not just the parse call. Concretely, the `apply_revised_draft_deltas(...)` call at [dr_run.py:1454](src/dual_research/orchestrator/dr_run.py:1454) must be wrapped so that a raised `ProtocolParseError` (i.e. `edit_section_anchor_not_found`, `edit_section_anchor_ambiguous`, `edit_section_unknown_heading`, `replace_section_unknown_heading`, `replace_section_missing_reason` — every hard error `apply_revised_draft_deltas` can raise at [parse.py:838-839](src/dual_research/protocol/parse.py:838)) is caught and converted into the **same no-op fallback** the parse step already uses:

- set `fallback_fired = True`, record `e.errors` into `fallback_errors`;
- re-apply with `payload = RevisedDraftFull(content=prior_draft)` so `draft-v(N+1).md` is a byte-equal copy of `draft-vN.md`;
- emit the existing `ProtocolViolation(violation_code="phase4_drafter_repair_failed", op_kind="revised_draft", …)` so the no-op is observable on the dashboard exactly as the parse-step fallback is today.

The result: an apply-time anchor failure can no longer reach the [run.py:565](src/dual_research/orchestrator/run.py:565) tombstone. The round loop continues; if the drafter never produces an applicable revision across rounds, the existing hard-cap terminates with a legible deadlock and a final draft, not an opaque `run_failed`. (Mechanically the cleanest shape is one fallback-construction site shared by both the parse-`except` and a new apply-`except` — implementer's discretion, but both paths MUST set `fallback_fired`/`fallback_errors` identically so the dashboard signal is uniform.)

### 2.2 — DRAFTER RESYNC: when a revision no-ops, feed the drafter the real on-disk draft with an explicit "your revision did NOT apply" signal

The `_build` closure in [`run_dr_phase4`](src/dual_research/orchestrator/dr_run.py:1528) already re-reads the current draft from disk each round via `current_draft_path(ctx.session, ctx.state.draft_round)` ([dr_run.py:1529-1530](src/dual_research/orchestrator/dr_run.py:1529)) — so the drafter is structurally always handed the on-disk draft. The missing piece is the **signal**: when the prior round no-op'd (fallback fired), the drafter is never told, so it keeps issuing edits against the draft it *intended* to have produced.

Add state tracking for "the previous drafter revision no-op'd" (e.g. a `last_revision_noop: bool` plus the `fallback_errors` from that round, threaded through `SessionContext` / phase-4 state) and, when set, prepend an explicit banner to the drafter's next-round prompt:

> ⚠ Your previous revision did NOT apply (it failed to parse / its anchors did not match the current draft). The draft below is the **current on-disk draft** — it does NOT contain your last round's intended edits. Re-issue your edits against THIS text; do not assume any prior revision landed.

Flag must be set on any fallback (`phase4_drafter_repair_failed`, whether parse-step or the new apply-step path) and cleared the moment a revision applies cleanly. This is what stops anchors from diverging round-over-round.

### 2.3 — ANCHOR ROBUSTNESS: strict deterministic normalization + a tighter anchor contract — NOT fuzzy matching

This resolves the draft's one open decision (tolerance vs. fuzzy matching) **in favour of strict tolerance only.** Two sub-parts:

**(a) Deterministic normalization at match time.** In the EDIT_SECTION branch of [`apply_revised_draft_deltas`](src/dual_research/protocol/parse.py:807), normalize **both** sides (section body and `anchor`) through a single deterministic function before the `count`/`replace`, mirroring the spirit of spec 0238's deterministic tolerant terminator (NOT its absence of fuzziness — explicitly its determinism). The normalization set is closed and fixed:

- collapse runs of inner whitespace to a single space and strip leading/trailing whitespace per line;
- unify smart/curly quotes to straight quotes (`’→'`, `“”→"`) and en/em dashes are left as-is unless trivially equivalent;
- tolerate a trailing-punctuation difference on the anchor (`.`, `,`, `:`, `;`).

Match counting and the single-occurrence replacement operate on the normalized projection but **write back the original draft bytes** for the non-matched span (i.e. normalization governs *where* the match is, not *what* survives). `0` normalized matches still raises `edit_section_anchor_not_found`; `>1` still raises `edit_section_anchor_ambiguous`. **No similarity threshold, no LCS, no fuzzy/approximate matching of any kind** — under state divergence a fuzzy match can bind a similar-but-wrong section (the four "Tier 2 Scoring" sections in the evidence run) and silently corrupt `final.md`. Normalization is exact-after-canonicalization; it is not approximate.

**(b) Tighten the drafter anchor contract in the prompt.** The drafter is currently free to emit multi-line body+table literals as `ANCHOR:` values (the evidence run anchored on full prose blocks and table rows). Update the EDIT_SECTION instruction in the phase-4 drafter prompt ([prompts.py](src/dual_research/protocol/prompts.py), the EDIT_SECTION block around [prompts.py:1362](src/dual_research/protocol/prompts.py:1362)) to require **short, single-line, structurally-unique anchors** — a subsection heading line (`### Section N — …`) or a distinctive single sentence/identifier — rather than multi-line body or table literals. Shrinking the anchor to a structural handle shrinks the surface drift can attack and makes the `>1`-match ambiguity error fire loudly instead of a long literal silently failing.

### 2.4 — SECONDARY: stop the drafter prompt leaking reviewer-style ADDRESS affordances (raiser_self_address ×7)

Phase-4 round 2 of the evidence run emitted `raiser_self_address`×7 — the drafter issued `### ADDRESS` blocks against its **own** raised items, which [deep_research.py:457](src/dual_research/orchestrator/deep_research.py:457) drops as a protocol violation. The phase-4 prompts already carry a "Do NOT use ADDRESS here; ADDRESS is reserved for the other agent's items" guard in places ([prompts.py:1813-1814](src/dual_research/protocol/prompts.py:1813), [prompts.py:2319-2325](src/dual_research/protocol/prompts.py:2319)), yet the drafter still self-addressed 7×, so the affordance is leaking through the drafter-facing path. Audit the drafter-role branch of the phase-4 prompt builders and make the "RESOLVE/WITHDRAW your own items; ADDRESS is for the other agent's items only" rule unambiguous on the drafter path. This is scoped **into this spec** (not a carve-out): it is a one-surface prompt-wording fix, it co-occurred in the exact failing round, and the malformed self-ADDRESS blocks plausibly contributed to the round-2 parse failure that triggered the no-op cascade — so it shares the regression fixture in §6.

## 3. User stories & acceptance criteria

Non-UI spec — touches the orchestrator, protocol parser, and prompt builders only; no frontend or design-system surface. §3.1 / §3.2 are not applicable. Operator-visible behaviour change: a phase-4 run that previously died at `EXIT_RUNTIME` with no output now completes to `final.md`, surfacing the drafter's failure as observable `phase4_drafter_repair_failed` violations on the dashboard rather than a fatal tombstone.

## 4. Data / Schema deltas

No persistent-schema impact. In-memory phase-4 state gains a transient "previous revision no-op'd" flag (§2.2); it is not serialized beyond what `save_state` already persists for the round loop. The `draft-v(N+1).md` artifact contract is unchanged (a file is always written; under fallback it is byte-equal to `draft-vN.md`).

## 5. Out of scope

- **Fuzzy / similarity / LCS anchor matching.** Explicitly rejected in §2.3 — it risks silent wrong-section corruption under state divergence.
- **Changing the `ANCHOR:` field *format*** to line-range or content-hash anchors. §2.3(b) tightens the *guidance* (short structural anchors) but keeps the literal-substring mechanism; a format redesign is a larger drafter-contract conversation, deferred (no spec number reserved — re-raise from a real failure if §2.3 proves insufficient).
- **Item-ID aliasing and early-deadlock abort.** Spec 0255 is validated (phase 2 converged genuinely, `via_hard_cap=False`, `via_ghost_cap=False`); neither is the binding constraint on this failure and neither is touched here.
- **Phase 0–3 parser surfaces.** This spec is confined to the phase-4 drafter-delta apply path and its prompt.

## 6. Test plan

Per CLAUDE.md spec-0238 live-failure-fix discipline, the regression test exercises the **real entry point** against the **captured artifact** — a helper-only unit test on `apply_revised_draft_deltas` is insufficient on its own.

- [ ] **Real-entry-point regression (load-bearing).** Vendor `round-02-claude.md`, `round-02-claude.malformed-1.md`, `round-03-claude.md`, and `draft-v2.md` from `runs/20260529-164844-backend-language-choice/phase4/` into `tests/fixtures/` (or the established anchor-runs fixture dir). Drive the real `run_dr_phase4` / `_on_revised_draft` → `_apply_drafter_revised_draft` path through the no-op-at-r2 → anchor-mismatch-at-r3 sequence. Assert: (1) the run does **NOT** `run_failed` and does **NOT** exit `EXIT_RUNTIME`; (2) a `final.md` is produced; (3) the r2 fallback emits `phase4_drafter_repair_failed`.
- [ ] **No wrong-section corruption.** After driving the captured r3 turn, assert no edit was applied to a non-target section — specifically that none of Sections 4/5/6 ("Tier 2 Scoring: …") were mutated by the `Section 3 — Tier 2 Scoring Summary` anchor (the fuzzy-match trap). Under strict normalization this anchor must `edit_section_anchor_not_found` → no-op, leaving all four sections byte-unchanged.
- [ ] **Apply-guard unit coverage.** A direct test that `_apply_drafter_revised_draft` catches an apply-time `ProtocolParseError` and produces a byte-equal `draft-v(N+1).md` + a `phase4_drafter_repair_failed` violation (the §2.1 contract), distinct from the parse-step path.
- [ ] **Resync signal.** Assert the next-round drafter prompt carries the "your previous revision did NOT apply" banner when and only when the prior round no-op'd; assert it is absent after a clean apply.
- [ ] **Strict normalization, both directions.** Anchors differing from the body only by inner-whitespace runs, smart-vs-straight quotes, or a trailing `.`/`,`/`:` match and replace correctly; an anchor whose target is genuinely absent (the r3 divergence case) still raises `edit_section_anchor_not_found`. Include a negative test that a *similar-but-different* anchor does **not** match (no fuzzy fallthrough).
- [ ] **raiser_self_address regression.** Replaying the captured round-02 drafter turn under the revised prompt-contract assertions, confirm the drafter-path prompt no longer presents an ADDRESS affordance for the drafter's own items (assert against the built prompt text); pin the existing drop semantics at [deep_research.py:457](src/dual_research/orchestrator/deep_research.py:457) are unchanged.

## 7. Risks

- **Normalization changes match identity and could mask a real semantic drift.** Mitigated by keeping the normalization set closed/deterministic (§2.3a — no similarity threshold) and by the "no wrong-section corruption" test; if normalization ever matches a wrong span the ambiguity error (`>1` match) fires rather than a silent replace.
- **Apply-guard could convert a *should-fail* run into a silently degraded one.** Mitigated because the no-op is loud: `phase4_drafter_repair_failed` is published per fallback and surfaces on the dashboard; repeated no-ops still hit the hard cap with a legible deadlock. The alternative (status quo) is a fatal `run_failed` with no output, which is strictly worse.
- **Tightening the anchor-contract prompt could reduce the drafter's edit expressiveness.** Mitigated by allowing any short structurally-unique anchor (heading or distinctive sentence), and by REPLACE_SECTION remaining available for whole-section rewrites. Revert path: the prompt change is isolated and can be relaxed without touching the apply-guard or resync logic.
