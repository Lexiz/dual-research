---
kind: dev
spec: "0231"
slug: parser-heading-tolerance-and-repair-fallback
title: Parser heading tolerance and graceful repair fallback
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-27
queued_at: ""
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

# Spec 0231 — Parser heading tolerance and graceful repair fallback

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — introduces a new `ProtocolViolation` code (`phase4_drafter_repair_failed`) and widens parser-extraction contracts; first-class event-type addition per CLAUDE.md's contract-change rule.
> **Evidence:** anchor-run fixture [`tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/) committed at `c2b1662`; Cowork reconciliation [`cowork/briefs/2026-05-27-live-run-findings-reconciliation.md`](../cowork/briefs/2026-05-27-live-run-findings-reconciliation.md); design sign-off [`cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md); failure report [`cowork/feedback/2026-05-27-live-run-20260527-054652-failure-report.md`](../cowork/feedback/2026-05-27-live-run-20260527-054652-failure-report.md).

---

## 1. Context

Live run `20260527-054652-backend-language-choice` exposed two parser-strictness failures of the same class — the parser rejects heading formats that models emit naturally — and a third anti-fix in the repair flow that makes the first failure strictly worse than the underlying malformation.

**Failure 1 — drafter inline `### EDIT_SECTION` anchor.** In [`phase4/round-02-claude.malformed-1.md:218`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase4/round-02-claude.malformed-1.md) the drafter emits `### EDIT_SECTION ## 1. Summary` (anchor inline on the H3 line, no newline). [`src/dual_research/protocol/parse.py:596`](src/dual_research/protocol/parse.py:596) raises `ProtocolParseError("revised_draft_body_missing_delta_op")`; the heading-normaliser at [`src/dual_research/protocol/parse.py:650`](src/dual_research/protocol/parse.py:650) (`_normalise_section_heading`) strips a leading numeric prefix but not a leading `## ` token, so the heading argument never binds. Repair fires, the model "fixes" the turn by stripping the `### EDIT_SECTION` blocks entirely (strictly worse — the substantive edits are gone), validation fails a second consecutive time, and the run exits 52.

**Failure 2 — glued `##` section heading in phase 2.** In [`phase2/round-01-claude.md:23`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase2/round-01-claude.md:23) claude emits `## New items I'm raisingNow I have evidence for the key factual claims...` (heading glued to reasoning prose, no newline). [`extract_fenced_section`](src/dual_research/protocol/parse.py:179) at [`src/dual_research/protocol/parse.py:192`](src/dual_research/protocol/parse.py:192) anchors the section start on `^##\s+<heading-name>\s*$` — a glued line fails the trailing `\s*$` and the section is silently missed. Six `### RAISE` blocks in claude's body never register; phase 2's ledger holds only OpenAI's six items; phase 2 "converges organically" with claude's entire raised side — including the central `Go #1 vs C# #1` ranking disagreement — never tracked. The verifier later flags 18 phase-2 ADDRESS/RESOLVE ops as I4.4 fails because they target ledger entries that don't exist; per Cowork's reconciliation [`§ Finding 2`](../cowork/briefs/2026-05-27-live-run-findings-reconciliation.md), all 18 are downstream of this single registration failure, not 0228 implementation gaps.

Both are the same class: parser strictness vs. model heading variance (cf. spec 0122 "glued bodies"). Both must be fixed together. The third layer — repair-flow non-ablation + graceful fallback — protects against any future case where the parser's tolerance is still too narrow, by replacing the "exit 52" outcome with a parseable no-op + loud `ProtocolViolation`.

## 2. Proposed change

Three layers in a single bundled commit. Each layer is independently testable; layer 3's fallback is last-resort and should rarely fire once layers 1+2 land.

### 2.1 — Parser tolerance for inline `### EDIT_SECTION ## <heading>` (Cowork 2.a)

Widen [`_normalise_section_heading`](src/dual_research/protocol/parse.py:650) so it strips a leading `## ` (markdown H2 token) in addition to the existing numeric-prefix strip. Cowork sign-off [`§ 2.a`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md): "correct splice point; that's exactly why `### EDIT_SECTION ## 1. Summary` didn't bind." Exact regex is the implementer's call — proposed shape: extend the existing `re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", h)` line with an additional pre-pass that strips a leading `^##\s+` token. Backwards-compatible: standalone anchors (`### EDIT_SECTION 1. Summary`) continue to parse identically.

### 2.2 — Parser tolerance for glued `## <heading><prose>` (Cowork 2.b — all 6 sections)

Loosen the heading anchor inside [`extract_fenced_section`](src/dual_research/protocol/parse.py:179) — currently `r"^##\s+" + _escape_regex(heading_name) + r"\s*$"` at [`src/dual_research/protocol/parse.py:192`](src/dual_research/protocol/parse.py:192). Replace the trailing `\s*$` end-anchor with a boundary that accepts EITHER a newline OR the next non-whitespace character after the heading name (so `## New items I'm raisingNow I have evidence...` matches the heading and the section body starts at `Now I have evidence...`). The "glued prose" between the heading and the first op block becomes harmless noise that the existing `### RAISE` finder skips over — Cowork [`§ 2.b`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md) confirms this composition is safe.

Apply uniformly to all six known phase-2 and phase-4 section anchors used by [`extract_fenced_section`](src/dual_research/protocol/parse.py:179) call sites (see [`src/dual_research/protocol/parse.py:1112`](src/dual_research/protocol/parse.py:1112)-[`1128`](src/dual_research/protocol/parse.py:1128) and [`src/dual_research/protocol/parse.py:305`](src/dual_research/protocol/parse.py:305)):

- `## Stance`
- `## Status`
- `## Addressing items raised against me`
- `## Ratifying my own items`
- `## New items I'm raising`
- `## Phase artifact` / `## Revised draft`

Implementer's call on whether to widen all six call sites (the heading-name argument is plain string) or to keep the boundary check in `extract_fenced_section` itself — the latter is simpler. Either way: standalone clean headings (newline after the heading name) must continue to parse identically.

### 2.3 — Repair-flow non-ablation + graceful fallback (Cowork 2.c — three mandatory conditions)

Three sub-clauses, all required:

**(a) Do NOT preemptively strip `### EDIT_SECTION` headers before sending the malformed content into the repair retry.** The current observation is that, given the inline-anchor malformation, the drafter responds to the [`repair_prompt`](src/dual_research/protocol/prompts.py:794) by removing the EDIT_SECTION blocks entirely. With 2.1 in place this should stop occurring (the parser never rejects the inline form), but the repair retry must not introduce a normalisation step that strips these headers — that's the "strictly worse" anti-fix the user flagged.

**(b) Last-resort fallback when a repaired turn ALSO fails the parse.** Today, [`src/dual_research/orchestrator/repair.py:392`](src/dual_research/orchestrator/repair.py:392) catches the second `ProtocolParseError` with `except ProtocolParseError: pass` — leaving the next round's validator to trip `consecutive_failures >= 2` and abort with exit 52. Replace that silent pass with a fallback **applied at the drafter-revised-draft seam** (e.g. inside [`_on_revised_draft`](src/dual_research/orchestrator/dr_run.py:1408) when `extract_revised_draft_deltas` raises, or in the upstream `repair.py` block when `is_drafter=True` and the second parse fails):

- Synthesize a `REPLACE_DRAFT_FULL` revised-draft payload whose body is **the prior draft body, verbatim** (no-op the revision).
- Do NOT use the unparseable original's body — per Cowork [`§ 2.c`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md), that ships an `ANCHOR:` / `REPLACE_WITH:`-shaped garbage doc downstream.
- The run continues to the next round. The no-op leaves the reviewer's items open; if the drafter never produces parseable output across rounds, the existing hard-cap catches a legible deadlock instead of an opaque exit-52.

**(c) Mandatory `ProtocolViolation` emission (NEVER silent).** When the fallback fires, emit `ProtocolViolation(violation_code="phase4_drafter_repair_failed", agent=<drafter>, phase=4, round=<round>)`. Add the code to the `ProtocolViolation.violation_code` docstring enumeration at [`src/dual_research/events/types.py:497`](src/dual_research/events/types.py:497) and [`src/dual_research/events/types.py:503`](src/dual_research/events/types.py:503).

**Implementer caution (Cowork [`§ 2.c`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md) note 3):** if this fallback fires often in practice, that signals 2.1 / 2.2 are too narrow and need re-scoping. Don't let the fallback become the de-facto fix — the parser-tolerance widenings are the primary intervention.

### 2.4 — Files touched

| File | Layer | Change |
| --- | --- | --- |
| [`src/dual_research/protocol/parse.py`](src/dual_research/protocol/parse.py) | 2.1 | `_normalise_section_heading` strips leading `## ` |
| [`src/dual_research/protocol/parse.py`](src/dual_research/protocol/parse.py) | 2.2 | `extract_fenced_section` heading-end boundary accepts glued prose |
| [`src/dual_research/orchestrator/repair.py`](src/dual_research/orchestrator/repair.py) or [`src/dual_research/orchestrator/dr_run.py`](src/dual_research/orchestrator/dr_run.py) | 2.3b | drafter-second-failure fallback (no-op revise + emit PV) — implementer chooses the seam |
| [`src/dual_research/events/types.py`](src/dual_research/events/types.py) | 2.3c | add `phase4_drafter_repair_failed` to the `violation_code` enumeration |
| [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py) | mech | MINOR bump |

## 3. User stories & acceptance criteria

Not a UI spec — user-stories / BDD scenarios are optional. The observable acceptance criteria live in §6 (Test plan) and the verifier numbers below.

**Operator-visible acceptance:**

- A re-run against the anchor-fixture input shape parses both the drafter inline-anchor turn and claude's glued-heading phase-2 turn without invoking the repair flow.
- `uv run dual-research verify tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/` shows I4.4 fails-count dropping from ~30 to ≤ ~14 (the slug-ID-derived entries from Finding 3 remain — they're a separate spec). I3.3 still fails (slug IDs, out of scope). I2.5 continues to report. I5.* continues to pass.
- The Cowork "false convergence" diagnosis is testable: feeding [`phase2/round-01-claude.md`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase2/round-01-claude.md) through [`extract_fenced_section`](src/dual_research/protocol/parse.py:179) with heading `"New items I'm raising"` now returns the body containing claude's six `### RAISE` blocks (previously: `None`).
- A synthetic round where the drafter emits unparseable output and the repair retry ALSO fails: the run emits `ProtocolViolation(violation_code="phase4_drafter_repair_failed")`, writes a no-op draft (byte-equal to the prior draft), and proceeds to the next round — does NOT exit 52.

## 4. Data / Schema deltas

No schema deltas. One new `ProtocolViolation.violation_code` value (`phase4_drafter_repair_failed`); the on-disk and on-event shape is unchanged.

## 5. Out of scope

Deliberately excluded — each has a named follow-up target:

- **Slug-ID normalisation (Finding 3).** OpenAI emits slug-shaped STATUS IDs (e.g. `D-go-csharp-21-edge`) and I3.3 correctly flags them. Per Cowork [`§ Finding 3`](../cowork/briefs/2026-05-27-live-run-findings-reconciliation.md), these are downstream observability noise — not the cause of claude's dropped raises. Deferred to a separate follow-up dev spec on orchestrator-side slug→canonical normalisation.
- **0228 extension with new violation codes** (`address_self_raised`, `resolve_no_prior_address`, etc.). Per Cowork [`§ Finding 2`](../cowork/briefs/2026-05-27-live-run-findings-reconciliation.md), 0228 is NOT implementation-incomplete on this evidence — the 18 phase-2 flagged ops are downstream of layer 2.2's registration failure, not missed state-machine paths. Extending 0228 here would be exactly the accretion pattern the engagement warned against. No follow-up planned.
- **I2.6 verifier invariant** (per-agent-per-round RAISED-count ⇄ `item_raised` event-count parity). Per Cowork [`§ §3`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md), this is a separate observability spec queued concurrently — it's the standing oracle that flips green when 2.2 lands. Deferred to a separate follow-up dev spec to be queued in parallel with this one.
- **Repair-prompt copy edits.** A prompt nudge ("heading on its own line") is optional belt per Cowork [`§ 2.b`](../cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md); the parser-side fix is primary. Out of scope here.
- **Snapshot updates beyond the anchor fixture.** Other test snapshots are untouched by this spec; only [`tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/) regenerates against the new parser tolerance.

## 6. Test plan

- [ ] **Parser unit — inline `### EDIT_SECTION ## <heading>` parses (2.1).** Add to [`tests/protocol/test_parse.py`](tests/protocol/test_parse.py): synthetic turn with `### EDIT_SECTION ## 1. Summary` and a single `ANCHOR:` / `REPLACE_WITH:` pair; assert `extract_revised_draft_deltas` returns one `EditSectionOp` whose `heading` normalises to match `## 1. Summary` from a synthetic prior draft.
- [ ] **Parser unit — glued `## <heading><prose>` parses (2.2).** Add to [`tests/protocol/test_parse.py`](tests/protocol/test_parse.py): synthetic phase-2 turn with `## New items I'm raisingNow I have evidence...\n\n### RAISE\n...`; assert `extract_fenced_section(text, "New items I'm raising")` returns a non-`None` body containing the `### RAISE` block.
- [ ] **Parser unit — backwards compatibility (standalone anchor).** Existing-shape turn `### EDIT_SECTION 1. Summary` continues to parse identically (no double-strip regression).
- [ ] **Parser unit — backwards compatibility (clean heading).** Existing-shape turn with `## New items I'm raising\n\n### RAISE\n...` continues to parse identically.
- [ ] **Integration — replay [`phase4/round-02-claude.malformed-1.md`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase4/round-02-claude.malformed-1.md) through `extract_revised_draft_deltas`.** Assert 10 `EditSectionOp` instances parse (the count grep'd from the fixture); no `ProtocolParseError` raised.
- [ ] **Integration — replay [`phase2/round-01-claude.md`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase2/round-01-claude.md) through `extract_fenced_section`.** Assert the `## New items I'm raising` body is recovered AND a downstream `### RAISE` finder returns six blocks.
- [ ] **Integration — fallback fires + run continues (2.3b/2.3c).** Synthetic phase-4 round where the drafter emits unparseable output both initially AND after repair; assert a `ProtocolViolation(violation_code="phase4_drafter_repair_failed")` event is emitted, the persisted `draft-v(N+1).md` is byte-equal to `draft-vN.md`, AND the orchestrator returns control to the round loop (does not raise / exit 52).
- [ ] **Verifier snapshot regenerate.** Update the [`tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/`](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/) verifier-output snapshot through [`tests/test_verifier.py`](tests/test_verifier.py); assert I4.4 fails-count drops to ≤ ~14, I3.3 fails-count unchanged (slug IDs, out of scope), I2.5 still reporting, I5.* still pass.
- [ ] **CHANGELOG entry + MINOR version bump.** New `## [X.Y.Z] — 2026-05-27` (or merge-date) section under the file header citing this spec; matching bumps in [`pyproject.toml`](pyproject.toml) and [`src/dual_research/__init__.py`](src/dual_research/__init__.py).
- [ ] **`uv run pytest tests/ -q` passes.**

## 7. Risks

- **2.2's boundary widening could over-match.** If a real `## Heading` line legitimately runs into adjacent content elsewhere in the protocol, the new tolerance could capture more than intended. Mitigation: the regex stays anchored on the heading-name match — only the trailing terminator widens — and the parsed body is still bounded by the next `^## ` heading outside fenced ranges (per [`_next_h2_outside_fences`](src/dual_research/protocol/parse.py:166)). The standalone-clean backwards-compat test asserts no behaviour change on the well-formed shape. If a real false-positive surfaces, narrow the boundary in a follow-up — don't ship a third repair-flow layer on top.
- **Fallback masks a real drafter regression.** If layer 2.3b fires *often* once shipped, that means layers 2.1 / 2.2 are too narrow OR the drafter prompt itself is producing unparseable bodies the parser can't reasonably tolerate. Mitigation: the mandatory `ProtocolViolation` makes occurrences observable in the dashboard and the verifier output; the implementer should add a follow-up if frequency-in-practice exceeds a rare-edge-case rate (call it: >1 firing per 10 runs).
- **Snapshot regeneration drift.** Regenerating the verifier snapshot for the anchor fixture risks masking a real regression elsewhere. Mitigation: review the diff explicitly against the acceptance criteria in §3 (I4.4 drops, I3.3 unchanged, I2.5 reports, I5.* pass) — any other invariant moving is a regression, not a regeneration artifact.
- **`phase4_drafter_repair_failed` becomes a load-bearing terminal state.** This is a NEW `violation_code` and the verifier doesn't yet have an invariant about it. That's intentional for v1 — observability before policy. If a downstream verifier invariant treats it as fatal in a later spec, that's a separate contract change to spec.
