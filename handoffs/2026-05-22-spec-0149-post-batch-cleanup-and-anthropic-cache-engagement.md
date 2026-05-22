# Handover — Spec 0149 — Post-batch cleanup + Anthropic cache engagement + protocol follow-ups (v1.14.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#171](https://github.com/Lexiz/dual-research/pull/171) (merged, squash, branch deleted)
- **Spec:** [specs/0149-post-batch-cleanup-and-anthropic-cache-engagement.md](../specs/0149-post-batch-cleanup-and-anthropic-cache-engagement.md)
- **Audit:** [specs/_post-batch-cleanup-audit.md](../specs/_post-batch-cleanup-audit.md) — closed twelve rows: D02, D04, D06, D07, D08, D17, D19, D20, D21, D22, D23, plus D11/D14 holdovers already wire-active. **Five rows still open** (vs the spec's projection of four): D09, D15, D05, D18, D24.
- **Anchor run:** `20260521-010637-dvs-backend-language-choice` (replay only; no fresh smoke this round — user-deferred to post-spec-0150).
- **Version:** `1.13.0 → 1.14.0` (**MINOR** — new public protocol op `REQUEST_EVIDENCE`, prompt-language changes, multiple FE surfaces).

## What landed

Twelve audit rows closed in one ship. Five of those (D02, D04, D17, D19, and partially D06) are **hypothesis-driven** — the spec's intended validation path was a fresh `/dual-research-run` smoke (D09) which the operator deferred to post-spec-0150. The other seven (D07, D08, D20, D21, D22, D23, plus the pricing-version mechanics from D06) close without dependency on smoke data.

- **D02 — Anthropic cache engagement (hypothesis-driven fix).** `_build_content` in [agents/anthropic_agent.py:292](../src/dual_research/agents/anthropic_agent.py) now supports any number of `CACHE_BREAKPOINT` markers in a single prompt — every chunk except the last carries `cache_control: {type: ephemeral, ttl: 1h}`. Anthropic accepts up to four breakpoints and matches the longest stable prefix, so prompts that have a stable Brief but a mutating draft section (Phase 4 review revisions; growing prior-turn history) get two cache options. Phase 2 round 1 / Phase 2 round N / Phase 3 drafting / Phase 4 review prompts in [protocol/prompts.py](../src/dual_research/protocol/prompts.py) now emit a second breakpoint after `_inline_section("Brief", brief_content)` and before the drafts. **Diagnosis was hypothesis-only**: without `<session>/usage-debug.jsonl` from a fresh run, the leading hypothesis was that the single-breakpoint placement collapsed the cache prefix every time the draft section changed (Phase 4 round-to-round draft revisions, etc.). The validation criterion — a Claude turn rendering `cache savings · ×N reuse on Xkt · $0.X` with `$0.X > 0` — moves to the deferred D09 smoke.

- **D04 — Empty-turn prompt tightening.** New `## Empty-turn invariant (spec 0149 §5.4 — D04)` section added to `negotiation_round1_prompt`, `negotiation_turn_prompt`, and `review_turn_prompt`. Language: *"Every turn in this phase MUST contain at least one ledger operation block — `### RAISE`, `### ADDRESS`, `### RESOLVE`, `### ACKNOWLEDGE`, `### WITHDRAW`, or `### REQUEST_EVIDENCE` — OR a top-level `STATUS: AGREED / APPROVED` line."* Phase 2 round 1 carries the round-1-cannot-agree variant. Phase 0 was deliberately left alone — the orchestrator's empty-turn check at [deep_research.py:557](../src/dual_research/orchestrator/deep_research.py) includes Phase 0 but the v1 Phase 0 prompts don't emit ledger blocks; without smoke data confirming whether Phase 0 actually fires `EmptyTurnDetected` in production, the safer move was to not introduce changes there. Validation deferred to D09 smoke.

- **D08 — `RequestEvidence` op.** New `### REQUEST_EVIDENCE <item-id>` block — first-class mid-run channel for requesting evidence on a previously-stated item, distinct from raise-time `evidence_required: bool` on RAISE blocks. Full wiring:
  - [`contract/operations.py`](../src/dual_research/contract/operations.py) — new `RequestEvidenceBlock` dataclass; extended `OperationBlock` alias.
  - [`contract/markers.py`](../src/dual_research/contract/markers.py) — new `OP_REQUEST_EVIDENCE_RE` mirroring the other id-bearing ops' `_ID_TAIL` tolerance.
  - [`contract/__init__.py`](../src/dual_research/contract/__init__.py) — exported from the package boundary.
  - [`contract/validator.py`](../src/dual_research/contract/validator.py) — new branch in `_operation_errors`: `request_evidence_missing_item_id` + `request_evidence_missing_reason`.
  - [`protocol/parse.py`](../src/dual_research/protocol/parse.py) — `_parse_request_evidence_block` + addressing-section dispatch arm (REQUEST_EVIDENCE lives in *"Addressing items raised against me"* because semantically the requester is responding to someone else's item).
  - [`protocol/prompts.py`](../src/dual_research/protocol/prompts.py) — block-shape reference appended to `_OPERATION_BLOCK_REFERENCE` with the cross-turn semantic note ("you cannot REQUEST_EVIDENCE on your own item").
  - [`orchestrator/deep_research.py`](../src/dual_research/orchestrator/deep_research.py) — counted as a ledger-affecting block by the empty-turn check.
  - **Open question on per-phase vs shared placement (§8 Q2 resolved):** the codebase uses per-phase op enumeration (RAISE / ADDRESS / RESOLVE listed inside each phase prompt's task description, not in a shared preamble). D08 followed the per-phase pattern by extending `_OPERATION_BLOCK_REFERENCE` — that reference block is reused across every interaction phase that supports the ledger ops.

- **D17 — `search_N` resolution (address-side, hypothesis-driven).** New `## Citation contract (spec 0149 §5.5 — D17)` section in `COMMON_PREAMBLE` (lands in every phase prompt). Language: *"Only emit an inline `[N]` citation when N references a source you actually consulted via web search (or another tool) during this turn AND N appears as a numbered row under your `## Sources` heading with a real URL. Do not emit `[N]` to reference your own prior reasoning, your training-data recall, the other agent's draft, or a source you did not actually fetch this turn."* Audit-side fix (the off-by-one hypothesis at [evidence.py:154](../src/dual_research/contract/evidence.py)) deferred pending fresh-run dominant-FP-type data — the audit-side fix could mask a real model fabrication problem if shipped before measuring the FP set.

- **D19 — Per-attachment rich previews.** New `AttachmentPreview` + `AttachmentTextPreview` components in [run-detail.jsx](../src/dual_research/ui/static/run-detail.jsx). `SubInputRow` gains optional `runId` + `attachmentId` props; when both set, a per-row chevron toggles a preview. The preview routes by `kind` / file extension / MIME against the existing [`/api/runs/<id>/attachment-blobs/<rel_path>`](../src/dual_research/ui/server.py) endpoint (D19 is FE-only; no new endpoint). Branches:
  - `link` (kind) or no `rel_path` → external anchor with the attachment title + source.
  - `.md` / `.txt` / `text/*` → lazy-fetched `<pre>` with 80-line truncation + "show more" affordance.
  - `.pdf` / `application/pdf` → `<iframe>` at 420px height.
  - `.png` / `.jpg` / `.gif` / `.webp` / `image/*` → `<img>` capped at 320px.
  - else → download link with the file's basename.
  - Attachment-ID match mirrors `buildAttachmentTitleMap` (sha256[:8] → slugified basename fallback).

- **D06 — `gpt-5-mini` pricing audit.** Audit attempted 2026-05-22; live verification at `platform.openai.com/docs/pricing` and `openai.com/api/pricing` returned 403 (the auth-gated docs pages). **Rates unchanged** ($0.25/$2.00/$0.025). The `notes` field on the row in [`agents/pricing.py`](../src/dual_research/agents/pricing.py) now records the audit attempt and the open verification path. `PRICING_VERSION` bumped to `2026-05-22` (documentation-only — the snapshot map in [`test_pricing_version.py`](../tests/agents/test_pricing_version.py) gets a new entry whose comment makes the docs-only nature explicit).

- **D07 — Anchor-run draft salvage.** New one-shot script [`scripts/salvage_anchor_run_draft.py`](../scripts/salvage_anchor_run_draft.py). Lifts lines 47-312 of `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md` into a clean `final.md` (266 lines, within the spec's 250-280 target). Script was executed locally — `final.md` exists on the operator's disk; `runs/` is gitignored so the artifact doesn't ride the repo. Re-runnable / idempotent.

- **D20 — Six dead `Preflight*Tab` components removed.** `PreflightContentTab`, `PreflightSourcesTab`, `PreflightFilesTab`, `AttachmentsEmpty`, `SourceRowAttachment`, `FileCard` deleted from [run-detail.jsx](../src/dual_research/ui/static/run-detail.jsx) along with the `formatBytes` helper that was used only by `FileCard`. All six lost their last external caller when spec 0145 collapsed the preflight modal to a single "User prompt" tab. Pre-grep verified zero external callers before deletion.

- **D21 — `deep-research-pipeline` rewire + footer annotation.** Three sites in [how-it-works.jsx](../src/dual_research/ui/static/how-it-works.jsx) rewired from `diagramName: '02-phase-inputs'` → `diagramName: 'deep-research-pipeline'`. SVGs copied from `/diagrams/` (where they sat retired) into `/src/dual_research/ui/static/diagrams/how-it-works/` so the `HiwDiagram` component's path resolves. A footer annotation was added to all four SVG copies (parent diagrams/ + ui/static/diagrams/ + ui/static/diagrams/how-it-works/, light + dark) noting the post-spec-0148 artifacts: `system.web_sources` and `system.tool_definitions` live inside the system-prompt aggregate rather than as discrete composite-input slots. `02-phase-inputs.svg` is **NOT** deleted — it remains referenced by `design-system/audits/2026-05-20-hiw-rework/mockup.html`.

- **D22** — Orphaned `.ccx-header .stats .sep` / `.ccx-header .stats .pct` CSS rules removed from [`components.css`](../src/dual_research/ui/static/components.css).

- **D23** — `p0StatsRoundCount` renamed → `p0StatsCount` across [`live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) (parallel naming with `p2StatsCount` / `p4StatsCount`). Orphaned `function PhaseContent()` deleted from [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx).

- **Cache-buster** bumped `?v=0148a → ?v=0149a` across all 25 static-asset imports in [`index.html`](../src/dual_research/ui/static/index.html).

- **Untracked stash.** A `prototypes/how-it-works-v2/` directory (24KB index.html + 87KB render.js, a Material-3 styled how-it-works preview that the operator didn't recognize) was moved to `/tmp/dr-prototype-stash/` and removed from the working tree per operator instruction.

## Files touched

### Backend (Python)
- [`src/dual_research/agents/anthropic_agent.py`](../src/dual_research/agents/anthropic_agent.py) — `_build_content` multi-breakpoint support (D02).
- [`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py) — `PRICING_VERSION = "2026-05-22"`; `gpt-5-mini` `notes` field updated (D06).
- [`src/dual_research/contract/operations.py`](../src/dual_research/contract/operations.py) — `RequestEvidenceBlock` + extended `OperationBlock` alias (D08).
- [`src/dual_research/contract/markers.py`](../src/dual_research/contract/markers.py) — `OP_REQUEST_EVIDENCE_RE` (D08).
- [`src/dual_research/contract/__init__.py`](../src/dual_research/contract/__init__.py) — exported `RequestEvidenceBlock` (D08).
- [`src/dual_research/contract/validator.py`](../src/dual_research/contract/validator.py) — `_operation_errors` branch for REQUEST_EVIDENCE (D08).
- [`src/dual_research/protocol/parse.py`](../src/dual_research/protocol/parse.py) — `_parse_request_evidence_block` + addressing-section dispatch arm (D08).
- [`src/dual_research/protocol/prompts.py`](../src/dual_research/protocol/prompts.py) — D02 second breakpoints; D04 empty-turn invariant in three phases; D08 reference shape; D17 citation contract in `COMMON_PREAMBLE`; CACHE_BREAKPOINT docstring rewrite.
- [`src/dual_research/orchestrator/deep_research.py`](../src/dual_research/orchestrator/deep_research.py) — `RequestEvidenceBlock` counted as ledger-affecting block (D08).

### Frontend
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — `AttachmentPreview` + `AttachmentTextPreview` + `_deriveAttachmentSlug` helpers (D19); `SubInputRow` extended with `runId` + `attachmentId` props + per-row chevron (D19); six dead components + `formatBytes` deleted (D20); `PhaseContent` deleted (D23).
- [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) — `p0StatsRoundCount` → `p0StatsCount` (D23).
- [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx) — three `diagramName: '02-phase-inputs'` → `'deep-research-pipeline'` (D21).
- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — `.ccx-header .stats .sep` / `.pct` removed (D22).
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-buster `0148a → 0149a` across 25 imports.

### Diagrams
- [`diagrams/deep-research-pipeline.{light,dark}.svg`](../diagrams/) — D21 footer annotation.
- [`src/dual_research/ui/static/diagrams/deep-research-pipeline.{light,dark}.svg`](../src/dual_research/ui/static/diagrams/) — D21 footer annotation (mirror).
- [`src/dual_research/ui/static/diagrams/how-it-works/deep-research-pipeline.{light,dark}.svg`](../src/dual_research/ui/static/diagrams/how-it-works/) — copied + D21 footer annotation (new files at this path).

### Scripts / other
- [`scripts/salvage_anchor_run_draft.py`](../scripts/salvage_anchor_run_draft.py) — D07 one-shot.
- [`pyproject.toml`](../pyproject.toml), [`src/dual_research/__init__.py`](../src/dual_research/__init__.py), [`uv.lock`](../uv.lock) — `1.13.0 → 1.14.0`.
- [`CHANGELOG.md`](../CHANGELOG.md) — `[1.14.0]` entry.
- [`specs/0149-post-batch-cleanup-and-anthropic-cache-engagement.md`](../specs/0149-post-batch-cleanup-and-anthropic-cache-engagement.md) — the spec itself (added to the PR; no amendments needed — citations all held at impl time).

### Tests
- [`tests/agents/test_cache_wiring.py`](../tests/agents/test_cache_wiring.py) — extended with two new multi-breakpoint cases (D02 unit).
- [`tests/agents/test_pricing_version.py`](../tests/agents/test_pricing_version.py) — new snapshot entry for `2026-05-22` (D06).
- [`tests/protocol/test_prompts_cache_marker.py`](../tests/protocol/test_prompts_cache_marker.py) — extended to assert two-breakpoint shape on Phase 2 r1 / Phase 2 rN / Phase 3 / Phase 4 (D02).
- [`tests/protocol/test_empty_turn_invariant_spec_0149.py`](../tests/protocol/test_empty_turn_invariant_spec_0149.py) — new (3 cases, D04).
- [`tests/protocol/test_citation_contract_spec_0149.py`](../tests/protocol/test_citation_contract_spec_0149.py) — new (3 cases, D17).
- [`tests/contract/test_request_evidence_spec_0149.py`](../tests/contract/test_request_evidence_spec_0149.py) — new (7 cases, D08).
- [`tests/ui/test_pricing_spec_0148.py`](../tests/ui/test_pricing_spec_0148.py) — `PRICING_VERSION` pin bumped (D06).

## Open-question resolutions (spec §8)

1. **D19 `/api/attachments/<id>` endpoint existence.** **Resolved: yes, the endpoint exists** as `/api/runs/{run_id}/attachments` (index) + `/api/runs/{run_id}/attachment-blobs/{rel_path}` (blob serving) in [`ui/server.py:248`](../src/dual_research/ui/server.py) and `:828`. D19 is FE-only against the existing endpoint. The `window.useAttachments(runId)` hook and `window.attachmentBlobUrl(runId, relPath)` helper already exist in [`live-data.jsx`](../src/dual_research/ui/static/live-data.jsx).

2. **D08 prompt fragment placement — per-phase vs shared preamble.** **Resolved: per-phase pattern dominant**, but D08 specifically rides in `_OPERATION_BLOCK_REFERENCE` (already a shared block for the ledger ops). That reference is included in every interaction-phase prompt where ledger ops are valid. Cross-phase consistency wins; per-phase reference duplication would have been the higher-overhead path.

3. **D21 diagram regeneration pipeline.** **Resolved: no pipeline exists.** `diagrams/` contains only the two SVG files plus the `how-it-works/` subdir of phase-specific SVGs — no `Makefile`, no `regen.py`, no `scripts/regenerate_diagrams.py`. D21 narrowed to hand-edit of the SVGs + add a footer annotation rather than re-generating from `REGISTRY` programmatically.

4. **D24 fly support thread channel.** **Resolved: user-deferred** ("Skip D24 this round"). The 8th-consecutive `machines.dev` mid-rolling-deploy timeout fired again on this deploy and was recovered manually; the support ticket remains un-filed.

5. **D02 anthropic SDK version pin.** **Resolved: current pin (`anthropic>=0.102.0`) was not bumped.** Without diagnostic-payload evidence pointing at env-side rejection of the `cache_control` header or the `extended-cache-ttl-2025-04-11` beta, bumping the SDK would have been blind. The beta header is being threaded correctly through `default_headers` at [anthropic_agent.py:59-66](../src/dual_research/agents/anthropic_agent.py); the most likely failure mode (per the structural read of the prompt-piece layout) is request-side breakpoint placement, which the D02 fix addresses directly.

## D02 diagnosis outcome

**Diagnosis: hypothesis-only (request-side placement was the structural read).** Without a `<session>/usage-debug.jsonl` dump from a fresh run, the diagnostic flow in spec §5.3 couldn't be exercised. The structural read of the prompt-piece layout found:

- The legacy single-breakpoint placement sat *after* the variable per-call content (Brief + drafts + plan blocks) and *before* the static task instructions. For Phase 2 round N → round N+1 transitions where the drafts stay stable, the cached prefix was the same — but Phase 4 review rounds revise the draft *between* rounds, breaking the cache prefix on every revision.
- The fix adds a *second* breakpoint after `_inline_section("Brief", brief_content)` and before the drafts. Anthropic accepts up to four `cache_control` breakpoints and matches the longest stable prefix; even when the draft mutates round-to-round, the "brief-only" prefix stays stable.

**Fix description.** [`_build_content`](../src/dual_research/agents/anthropic_agent.py) was rewritten to split a prompt on every `CACHE_BREAKPOINT` marker (not just the first) and apply `cache_control: {"type": "ephemeral", "ttl": "1h"}` to every chunk except the last. Phase 2 / 3 / 4 prompt builders in `protocol/prompts.py` now emit two breakpoints. Unit-tested in [`tests/agents/test_cache_wiring.py`](../tests/agents/test_cache_wiring.py) and [`tests/protocol/test_prompts_cache_marker.py`](../tests/protocol/test_prompts_cache_marker.py).

**Anchor-run reconcile delta:** none. The anchor run pre-dates the fix; `metrics.json` is unchanged. The validation criterion ("a Claude turn renders non-zero `cache savings · ×N reuse` on a fresh run") moves to the deferred D09 smoke.

**`PRICING_VERSION` bump:** Yes — `2026-05-21 → 2026-05-22`. The bump was forced by the D06 `notes`-field edit on `gpt-5-mini`, not by any rate change. The snapshot map in `test_pricing_version.py` carries a new entry whose comment is explicit about the docs-only motivation.

## D04 prompt-tightening calibration notes

Without `EmptyTurnDetected` events from a fresh run, the wording was set to the spec §5.4 draft: *"Every turn in this phase MUST contain at least one ledger operation block — `### RAISE`, `### ADDRESS`, `### RESOLVE`, `### ACKNOWLEDGE`, `### WITHDRAW`, or `### REQUEST_EVIDENCE` — OR a top-level `STATUS: AGREED / APPROVED` line."* Phase 2 round 1 carries an additional clause ("Round 1 cannot terminate the phase"). Phase 4 carries the drafter's round-1 carve-out. The validation — *"a fresh run on a brief that historically produced EmptyTurnDetected events now produces zero net-new events"* — moves to the deferred D09 smoke. If the smoke reveals the failure mode is parser-rejection rather than model-side empty turn, the prompt change won't help; that branch escalates to a v1.14.x parser-side fix.

## D17 dominant FP type + which side got tightened

**Dominant FP type: unknown without smoke data.** The hypothesis-driven choice was address-side, on the prior that model-side over-citation is the more common failure mode than capture-side off-by-one. The audit-side fix (at [`evidence.py:154-164`](../src/dual_research/contract/evidence.py)) remains untouched — fixing it without a real off-by-one to fix would have been worse than leaving it. D09's smoke will read every `search_N` reference and cross-reference against `consulted_sources`; if the dominant FP type is capture-side, the address-side language won't hurt and a follow-up spec ships the audit-side fix.

## D18 false-flag rate measurement + close-or-escalate decision

**Not performed. D18 stays open in the audit.** D18 is purely observational — it requires a fresh run with the validator wired live. The anchor run pre-dates the spec-0144 validator deploy; without D09, there's no dataset to measure against. **Decision deferred to post-D09**. If FP rate ≥ 50% in the smoke, a follow-up spec ships the prompt-side validator fix; otherwise the row closes.

## D19 endpoint situation

**Existed.** `/api/runs/{run_id}/attachments` (index) at [`ui/server.py:248`](../src/dual_research/ui/server.py); `/api/runs/{run_id}/attachment-blobs/{rel_path}` (blob serving) at `:304`. D19 was implementable as FE-only — no new endpoint shipped.

## D21 path (regen pipeline vs hand-edit)

**Hand-edited.** No `diagrams/Makefile` / `diagrams/regen.py` / `scripts/regenerate_diagrams.py` was present. The narrow path: copy `deep-research-pipeline.{light,dark}.svg` from `diagrams/` (where they were retired) into `src/dual_research/ui/static/diagrams/how-it-works/`, add a footer text annotation noting `system.web_sources` + `system.tool_definitions` (which the diagram does not depict as boxes since they're agent-layer artifacts inside the system-prompt aggregate, not composite-input slots), and rewire `how-it-works.jsx` 3 sites. **Not done**: full re-drawing of the diagram with boxes for the two new artifacts. The audit row closes on "the new IDs are mentioned in the diagram", not "depicted as boxes" — the explicit follow-up is to commission a proper re-draw when a regen pipeline lands or a designer pass is scheduled.

## D24 support ticket

**Not filed.** Per operator direction ("Skip D24 this round"). **The 8th consecutive `machines.dev` mid-rolling-deploy timeout fired on this deploy** and was recovered via `fly machine start d8d04d3fe402d8 -a dual-research-alex`. The audit row stays open; the cumulative-deploy-count escalation now stands at eight-in-a-row.

## Deploy status

- **Version:** `1.14.0`
- **Deploy timestamp:** 2026-05-22T~01:14Z (the second machine was restarted manually after the rolling-deploy timeout; recovery took ~15 seconds).
- **Live health:** `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.14.0","backend":"supabase"}` (consistent across 5 polls).
- **Both machines started + 1/1 health passing**: machine `148ee320f427e8` (image `…01KS6KHJRKYNN0FAW0QQ1KMXSQ`) and machine `d8d04d3fe402d8` (image `…01KS6KGX9V3JKCDKYASDA6H7J4`). The two distinct image hashes are an artifact of the recovery — `148ee320f427e8` picked up an earlier-finishing build than the one my CLI invocation produced. Both report v1.14.0 to `/api/health`, so the operator-visible behaviour is consistent.

### Smoke

1. **Local preview reload after JSX changes** — no console errors; 40-artifact anchor-run timeline renders correctly; `/how-it-works` reachable and the `01-pipeline.dark.svg` initial diagram loads. `/diagrams/how-it-works/deep-research-pipeline.{light,dark}.svg?v=0149a` both serve 200 and contain the spec-0149 footer annotation.
2. **Hosted bundle markers.** `curl -s https://dual-research-alex.fly.dev/run-detail.jsx?v=0149a | grep -c -E 'Spec 0149|AttachmentPreview|RequestEvidenceBlock|Empty-turn invariant|REQUEST_EVIDENCE|attachmentId,$|_deriveAttachmentSlug'` → **10 hits**. The bundle has the spec-0149 JSX.
3. **Hosted diagram check.** `curl -s https://dual-research-alex.fly.dev/diagrams/how-it-works/deep-research-pipeline.light.svg?v=0149a | grep -c system.web_sources` → 1. Annotation landed on the hosted SVG.
4. **Fresh-run smoke (D09):** **DEFERRED** per operator direction to after spec 0150 ships. This is the validation gate for D02, D04, D17, D18, and the file-bearing branches of D19.

## Anchor-run replay results

The anchor run was not re-pushed this spec. The D07 salvage script ran locally and produced `runs/20260521-010637-dvs-backend-language-choice/final.md` (266 lines from `phase4/round-07-claude.md` lines 47-312); `runs/` is gitignored so the artifact lives on the operator's disk. No cost-number shifts under D02 (the anchor pre-dates the fix); no `PRICING_VERSION` impact on the anchor's `metrics.json` because the only rate-table change was a documentation-only `notes` edit on `gpt-5-mini`, which the anchor doesn't use (the anchor uses Claude Sonnet 4.6 + GPT-5.5).

## Tests

```
1404 passed in 11.12s
```

Up from 1389 (Spec 0148 baseline) — +15 net (3 new in test_empty_turn_invariant_spec_0149 + 3 in test_citation_contract_spec_0149 + 7 in test_request_evidence_spec_0149 + 2 multi-breakpoint cases in test_cache_wiring; minus 2 pin edits that didn't add new test count).

## Known follow-ups / outstanding from audit

After this lands, **five rows remain open** in [`specs/_post-batch-cleanup-audit.md`](../specs/_post-batch-cleanup-audit.md):

- **D09 — fresh-run smoke.** User-deferred to post-spec-0150. The validation gate for D02 (cache_read > 0), D04 (zero net-new EmptyTurnDetected events), D17 (search_N resolution rate ≥ 60%), D18 (validator FP rate), and D19's file-bearing preview branches. Cost: ~$10 LLM + ~15-20 min.
- **D15 — legacy-shim sunset (deadline 2026-08-19).** Owned by Spec 0150. The `LEGACY_KEY_TO_CANONICAL` map + legacy `user_prompt` ArtifactDef + JSONB → `turn_prompt_pieces` backfill all live here.
- **D05 — input.json backfill.** Consolidated into 0150 alongside D15's backfill per the post-0148 review note.
- **D18 — validator over-flagging measurement.** Purely observational, blocked on D09 smoke data.
- **D24 — fly.io `machines.dev` support ticket.** Eighth-consecutive deploy timeout un-escalated. User-deferred this round.

Additional carries from D02 / D04 / D17 / D19:
- **D02 — Anthropic cache engagement validation.** The fix is in; the cache-savings line will show `$0.X > 0` on Claude turns *if* the fix engages on real provider responses. The smoke confirms; if it doesn't, a v1.14.x follow-up adjusts the breakpoint placement.
- **D04 prompt-side calibration** — if the smoke shows `EmptyTurnDetected` still firing on parser-rejection cases, the parser-side fix is the v1.14.x follow-up.
- **D17 capture-side fallback** — if the smoke shows capture-side off-by-one is dominant, a v1.14.x follow-up touches [`evidence.py:154`](../src/dual_research/contract/evidence.py).
- **D19 file-attachment branches** — `markdown` / `pdf` / `image` branches are untested against real file-kind attachments (the anchor run has only Notion `link`-kind entries).
- **D11-Anthropic extended-thinking** — still gated on the agent config flip (independent of this spec).
- **D21 diagram artwork** — the new IDs are present as a footer annotation; properly drawing them as boxes in the pipeline visual is a designer / regen-pipeline follow-up.

## Closure status (per audit row)

| Dxx | Status | Notes |
|---|---|---|
| **D02** | **CLOSED (hypothesis-driven; validation deferred to D09)** | Multi-breakpoint support + second breakpoint after Brief in Phase 2/3/4. Unit tests pinning placement. Validation: Claude turn on D09 smoke shows `cache savings · ×N reuse` line with $X > 0. |
| **D04** | **CLOSED (hypothesis-driven; validation deferred to D09)** | Empty-turn invariant in Phase 2 round 1 / Phase 2 round N / Phase 4. |
| **D06** | **CLOSED (audited under access constraint)** | Rates unchanged; 403 on docs pages prevented live verification. `notes` updated; `PRICING_VERSION` bumped to 2026-05-22. |
| **D07** | **CLOSED** | Script ran locally; `final.md` 266 lines. |
| **D08** | **CLOSED** | New op end-to-end: contract dataclass + parser regex + section dispatch + validator branch + prompt-fragment + empty-turn-check wiring + 7 unit tests. |
| **D17** | **CLOSED (hypothesis-driven; validation deferred to D09)** | Address-side citation contract in `COMMON_PREAMBLE`. Audit-side fix carried forward if D09 surfaces capture-side dominance. |
| **D18** | **OPEN** | Purely observational; blocked on D09 data. |
| **D19** | **CLOSED (link branch only; file branches untested on real data)** | FE-only against existing endpoint. Link branch testable against the anchor run; markdown / pdf / image branches need an attachment-bearing run. |
| **D20** | **CLOSED** | Six dead components + `formatBytes` deleted. |
| **D21** | **CLOSED (narrow scope — annotation, not boxes)** | Rewire done; SVGs carry footer mention of the new IDs. Full visual integration is a designer follow-up. |
| **D22** | **CLOSED** | Two orphaned CSS rules removed. |
| **D23** | **CLOSED** | Rename + dead-function deletion. |
| **D09** | **OPEN (user-deferred to post-spec-0150)** | The validation gate for the five hypothesis-driven items above. |
| **D24** | **OPEN (user-deferred to post-spec-0150)** | 8th-consecutive timeout un-escalated. |

After Spec 0150 lands, only D24 + possibly residual D04 / D17 / D18 follow-ups will remain.
