---
kind: dev
spec: "0149"
slug: post-batch-cleanup-and-anthropic-cache-engagement
title: Post-batch cleanup + Anthropic cache engagement + protocol follow-ups
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.14.0
status: deployed
queue_position: 0
depends_on: []
complexity: M
created: 2026-05-22
queued_at: ""
started_at: ""
merged_at: "2026-05-22T01:00:00Z"
deployed_at: "2026-05-22T01:00:00Z"
pr: "https://github.com/Lexiz/dual-research/pull/171"
handover: "handoffs/2026-05-22-spec-0149-post-batch-cleanup-and-anthropic-cache-engagement.md"
failure_step: ""
source_session: pre-lifecycle-bootstrap
promoted_from_draft: ""
---
# Spec 0149 — Post-batch cleanup, Anthropic cache engagement, and protocol follow-ups

> Ship bucket: **The long-tail spec. Closes all post-batch-cleanup-audit rows except D15 (legacy-shim sunset, owned by 0150) and D05 (input.json backfill, consolidated into 0150 alongside D15's backfill). Marquee item is D02 — the Anthropic `cache_control` engagement fix — which is the only real cost-impact change in the batch. Everything else is small individually but accumulates: one new protocol op (D08), one prompt tightening (D04), one search-citation tightening (D17), one validator measurement (D18), one rich-preview UI surface (D19), a pricing-rate audit (D06), an anchor-run salvage script (D07), three cleanup deletions (D20, D22, D23), a diagram regeneration (D21), and two operational hand-offs (D09 fresh-run smoke, D24 fly support ticket).**
> Depends on:
> - **0148** (just landed at v1.13.0). D02's validation criterion is *Anthropic turns render non-zero `cache savings · ×N reuse` in the CcxCard totals block* — the rendering machinery shipped in 0148. D04 reads from `run.violations` (the transcript-derived list 0148 populated). D21's diagram label set must include `system.web_sources` + `system.tool_definitions` (registered in 0148).
> - **0146** / **0145** — D19 sits inside the per-attachment surface 0145 plumbed and 0146 made visible by default. D20 deletes the dead `Preflight*Tab` components 0145 left in place for blast-radius reasons.
> - **0144** — D17 is the search-citation resolution work 0144's investigation surfaced; D18 measures the validator 0144 wired in.
> - **0143** — D02 consumes the `DUAL_RESEARCH_DEBUG_USAGE=1` instrumentation 0143 shipped. D06 audits the `gpt-5-mini` pricing row 0143 deliberately did not bump.
> - **0141** — D04 consumes the `EmptyTurnDetected` event 0141 emits and 0148 surfaces as a chip.
> Complexity: **L** — twelve sub-sections, two non-trivial (D02 protocol diagnosis + fix; D08 new contract op). The other ten are small but heterogeneous; the spec's complexity is mostly fan-out, not depth.
> Targeted version bump: **MINOR (1.13.0 → 1.14.0)** — D02 changes effective Anthropic cost on every call (~3× swing if the audit is right); D08 adds a new wire-shape (`RequestEvidence` block); D04 changes prompt language; D17 changes citation behaviour. Multiple semi-public-facing surfaces. Clearly MINOR, not PATCH.

---

## 1. Context

The 0140–0147 batch shipped end-to-end and 0148 closed the consumption-card boundary (B16 §10.1–§10.6 + protocol-violation chips). The post-batch cleanup audit at `specs/_post-batch-cleanup-audit.md` tracks 24 deferred items across the eight specs of the batch. After 0148, **sixteen items remain**. This spec closes **twelve** of them:

- **D02 (Anthropic cache engagement)** is the only real cost-impact change. The audit's verbatim quote: "*The smoking-gun shape stays the same either way: `cache_read_tokens == 0 AND cache_write_tokens == 0 AND cost matches plain input × output arithmetic`.*" If the audit is right, every Claude turn on production today pays the full-input rate when it should be paying the cache-read rate — roughly a 3× over-charge against expected per-turn cost. 0143 shipped the instrumentation (`DUAL_RESEARCH_DEBUG_USAGE=1` → `<session>/usage-debug.jsonl`); 0149 fires a fresh run with the flag set, reads the raw SDK payload to determine whether the cache miss is env-side (`cache_control` header silently dropped by the SDK) or request-side (the breakpoints we're emitting don't match Anthropic's stable-prefix policy), and ships the fix. The validation criterion comes from 0148: an Anthropic turn must now render non-zero `cache savings · ×N reuse` in the CcxCard totals block. Before 0148, that line didn't exist; now it does, which means D02's success is observable end-to-end without a code-level metrics dump.

- **D04 (empty-turn prompt tightening)** was deferred from 0148 because designing the prompt tightening requires real-world `EmptyTurnDetected` signal data, and the anchor run pre-dates spec 0141's deploy. 0148 made the signal visible via chips, but only on go-forward runs. 0149 fires the long-pending D09 fresh-run smoke first, harvests any `EmptyTurnDetected` events it produces, then tightens the prompt language to prevent empty turns from being structurally possible.

- **D08 (`RequestEvidence` op channel)** is a new contract block: a way for a model mid-run to request sources / evidence for an existing item, distinct from raise-time `evidence_required: bool`. New op, new parser path, new prompt language. Orthogonal to the rest of the batch.

- **D17 (search_N resolution tightening)** is also fresh-run-data-dependent. The anchor run resolves 9/30 (30%) of `search_N` records — either we're emitting `search_N` references too liberally on the address side, or the audit-capture path is dropping `consulted_sources` too often. Once D09 has fired, we have a baseline; we tighten the worse-performing side.

- **D18 (validator over-flagging measurement)** is observational. 0144 wired the validator in but the anchor run pre-dates the deploy so it can't reveal false-flag rates. D09 produces the first measurement; if >50% of items are unverified-flagged when the underlying evidence is actually present, an urgent prompt-side fix follows.

- **D19 (per-attachment rich previews)** was kept out of 0145 §5.4 because the anchor run has zero attachments. After D09 (which the spec instructs to use an attachment-bearing brief), the rich-preview branch can be designed against real data.

- **D06 (`gpt-5-mini` pricing audit)**, **D07 (anchor-run draft body salvage)**, **D20 (dead Preflight*Tab components)**, **D21 (diagram regeneration + How-It-Works rewire)**, **D22 (orphaned CSS rules)**, **D23 (variable rename + dead `PhaseContent` function)** are all janitor work. Each is small individually; bundling them avoids twelve micro-PRs.

- **D09 (fresh-run smoke)** and **D24 (fly support ticket)** are operational actions, not code changes. D09 is a one-time `/dual-research-run` against a drift-prone + attachment-bearing brief; the spec instructs the implementer to fire it as the FIRST step (because D04, D17, D18, D19, D02's validation, and 0148's untested-on-real-output surfaces all depend on its output). D24 is a communication action; the seventh-consecutive `machines.dev` mid-rolling-deploy timeout demands a support ticket before the eighth deploy (which is this spec's).

Six items stay outstanding after 0149: D15 (legacy-shim sunset, 0150's marquee), D05 (input.json backfill, absorbed by 0150 alongside D15's JSONB backfill), D09 (manual smoke, ongoing forward), D24 (manual ticket, fires once), plus D11-Anthropic-extended-thinking and D02 validation (carried as 0149's own internal checkpoints; not deferred). The audit count goes from 16 → 4 after this spec lands.

---

## 2. Goals

1. **D02 — Anthropic cache engagement.** A fresh Claude turn must emit `cache_read_tokens > 0` and `cache_write_tokens > 0` in the SDK usage payload, and the CcxCard's totals block must render a non-zero `cache savings · ×N reuse on Xkt` line for that turn.

2. **D04 — Empty-turn prevention via prompt tightening.** Add language to the protocol's per-phase prompts that makes "a turn with zero output blocks AND no STATUS: AGREED marker" structurally invalid (the model is required to either emit one of `{raise, address, comment, agreed, propose, …}` or set STATUS: AGREED). Verified by: D09's fresh run produces zero net-new `EmptyTurnDetected` events after the prompt tightening, on a brief known to historically drift.

3. **D06 — `gpt-5-mini` pricing audit.** Confirm the `PRICING["gpt-5-mini"]` row matches current OpenAI developer pricing. Update if stale; add a new `PRICING_VERSION` entry only if the test tier (Haiku + gpt-5-mini) actually changes.

4. **D07 — Anchor-run draft salvage.** Produce `runs/20260521-010637-dvs-backend-language-choice/final.md` from lines 47–312 of `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md`. One-shot script committed under `scripts/`; not part of the production pipeline.

5. **D08 — `RequestEvidence` op.** New contract block: a model can emit `OP: REQUEST_EVIDENCE` mid-run against an existing item ID to request that the other agent produce evidence for a previously stated claim. Distinct wire shape from raise-time `evidence_required: bool`. Parser path, validator path, and prompt fragment all added.

6. **D17 — `search_N` resolution tightening.** Raise the anchor run's 30% resolution rate to >60% on D09's fresh run. Achieved by tightening whichever side D09's diagnostic dump fingers — address-side (model emits fewer un-resolvable `search_N` references) or audit-capture-side (the capture path drops fewer `consulted_sources`).

7. **D18 — Validator over-flagging measurement.** Read every `unverified=True` flag on D09's fresh run; manually classify each as true-positive (evidence genuinely absent) or false-positive (validator missed evidence that was actually there). Compute the false-flag rate. If >50%, file a follow-up spec for the prompt-side fix.

8. **D19 — Per-attachment rich previews.** Render markdown / thumbnail / download surface for attached files in the per-attachment sub-rows of the consumption card and the brief modal. The per-attachment sub-row currently shows attachment ID + title + token count; this adds preview content.

9. **D20 — Dead `Preflight*Tab` cleanup.** Delete `PreflightContentTab`, `PreflightSourcesTab`, `PreflightFilesTab`, `SourceRowAttachment`, `FileCard`, `AttachmentsEmpty` from `run-detail.jsx`. Zero external call-sites today.

10. **D21 — Diagram regeneration + How-It-Works rewire.** Regenerate `deep-research-pipeline.{light,dark}.svg` with canonical-ID labels sourced from `REGISTRY` at generation time (so the new `system.web_sources` + `system.tool_definitions` IDs from 0148 are included). Rewire `how-it-works.jsx` to render `deep-research-pipeline` instead of the now-stale `02-phase-inputs`.

11. **D22 — Orphaned CSS cleanup.** Remove `.ccx-header .stats .sep` and `.ccx-header .stats .pct` rules from `components.css:2540-2541` (zero JSX matches).

12. **D23 — Variable rename + `PhaseContent` deletion.** Rename `p0StatsRoundCount` → `p0StatsCount` in `live-data.jsx` for parallel naming with `p2StatsCount` / `p4StatsCount`. Delete the orphaned `PhaseContent` function at `run-detail.jsx:7672`.

Operational, not goals but ship gates:
- **D09**: fire a fresh `/dual-research-run` on a brief that is BOTH (a) historically drift-prone (Phase 4 deadlock risk) AND (b) attachment-bearing. Push live. Capture `usage-debug.jsonl` if D02 work is in progress.
- **D24**: file a fly.io support ticket before the post-0149 deploy.

---

## 3. Non-goals

- **No D15 work (legacy-shim sunset).** 0150 owns. The legacy `user_prompt` `ArtifactDef`, the JS shim (`LEGACY_KEY_TO_CANONICAL` + the pre-0118 7-key vocabulary branch at `run-detail.jsx:2342-2345`), the `LEGACY_INPUT_BUNDLE_KEYS`, and the JSONB → `turn_prompt_pieces` backfill all stay until 0150.
- **No D05 work (historic `inputs/input.json` backfill).** Consolidated into 0150 alongside D15's backfill, per the post-0148 review note. The synth fallback continues to serve pre-0142 runs until 0150 lands.
- **No new persistence schema.** D08's `RequestEvidence` op rides the existing transcript-event channel; D17/D18 are observational on existing data; D19 is render-only. Zero migrations.
- **No retroactive backfill of D02's cache-savings into historical runs.** Historical Claude turns (which paid full-input pricing) keep their original `cost_usd`. Going forward, D02's fix reduces cost AND surfaces `cache_savings_usd > 0`. The historical/forward boundary is the deploy timestamp.
- **No `PRICING_VERSION` bump unless D06 reveals stale rates.** The version is automatic-via-failure-message per spec 0143's pattern.
- **No Compare-tab visual changes.** Same `CcxCard` flows through via CSS inheritance.
- **No Jest harness / visual regression suite.** Same carve-out as 0144 / 0148.
- **No prompt-tightening for D17 if D09's diagnostic dump points at audit-capture-side.** The audit-side fix and the prompt-side fix are exclusive at v1.14.0 — whichever side D09 fingers is the side we touch.
- **No D11-Anthropic extended-thinking enablement** unless D02's diagnosis surfaces it as a coincident fix. Extended-thinking is an Anthropic config flag; flipping it on is independent of cache engagement, but if D02's investigation reveals it should be on, it's cheap to enable inline. Validation: `output_breakdown.reasoning > 0` populates on Anthropic turns. Otherwise stays off and remains a future deferred item.

---

## 4. Current-state audit

### 4.1 — Anthropic agent + cache_control (D02)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/agents/anthropic_agent.py` | 306 | `cache_control` dict in `_split_and_apply_ephemeral_cache()` — the function that decides where to place cache breakpoints in the prompt. |
| `src/dual_research/agents/anthropic_agent.py` | 175–176 | `DUAL_RESEARCH_DEBUG_USAGE=1` gate → `usage-debug.jsonl` write. The diagnostic surface we read from in §5.3. |
| `src/dual_research/agents/base.py` | 214–217 | `TokenUsage.cache_read_tokens`, `cache_write_tokens`, `cache_write_5m_tokens`, `cache_write_1h_tokens` — the fields that must become non-zero post-fix. |

### 4.2 — Empty-turn prompt + retry hook (D04)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/protocol/prompts.py` | 304, 489 | Per-phase prompt assembly; line 489 is the core toggle for STATUS: AGREED constraint language. No "must surface at least one block" phrasing exists today — this is the addition. |
| `src/dual_research/orchestrator/deep_research.py` | 566 | `EmptyTurnDetected` emit site in turn loop. Retry hook would slot here. The default behaviour after the prompt tightening is "no retry" — the prompt should make empty turns structurally impossible. The retry path stays out of scope unless D09 shows the prompt fix alone is insufficient. |

### 4.3 — `gpt-5-mini` pricing (D06)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/agents/pricing.py` | 86–92 | `PRICING["gpt-5-mini"]` row: input $0.25/M, output $2.00/M, cache_read $0.025/M. Audit candidate. |
| `tests/agents/test_pricing_version.py` | (whole file) | Regression test; pins the per-tier pricing version. Bumps only if D06 finds stale rates that affect the test tier (Haiku + gpt-5-mini). |

### 4.4 — Anchor-run draft salvage (D07)

| File | Lines | Role |
|---|---|---|
| `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md` | 47–312 | Source for the salvaged `final.md` (file exists, 312 lines total). |
| `scripts/` | new | Destination for the one-shot salvage script. Out-of-tree from production pipeline. |

### 4.5 — `RequestEvidence` op (D08)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/contract/operations.py` | 38 | `evidence_required: bool` field on `RaiseBlock` (raise-time, exists today). The mid-run channel D08 adds is distinct. |
| `src/dual_research/contract/markers.py` | 173 | Parser regex for `evidence_required: (true\|false)`. New regex line(s) for `OP: REQUEST_EVIDENCE` go alongside. |
| `src/dual_research/contract/validator.py` | 222, 286 | `validate_parsed()` / `validate_turn()` entry points. New op needs its own validation branch (target item must exist; requester ≠ original author; etc.). |
| `src/dual_research/contract/evidence.py` | 1–14 | Core evidence spec; mid-run request slot is currently undefined — this spec adds the design here. |

### 4.6 — `search_N` resolution (D17)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/contract/evidence.py` | 154, 164 | `consulted_sources` resolution; `search_N` linkage expected but currently fires at 30% on the anchor run. |

D09's diagnostic dump determines whether the fix is address-side (model emits fewer `search_N` references → tighten the prompt fragment that explains the citation contract) or capture-side (the capture path drops `consulted_sources` → fix the capture).

### 4.7 — Validator over-flagging (D18)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/contract/validator.py` | 222 | `validate_parsed()`. The validator runs `validate_all_evidence` against each search-bearing turn; `unverified=True` is the over-flag we're measuring. |

D18 is observational at v1.14.0 — we read flags on the fresh run, classify, and either close D18 (if false-flag rate < 50%) or open a follow-up spec.

### 4.8 — Per-attachment rich previews (D19)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 2336 | `SubInputRow()` — the per-attachment sub-row component spec 0145 added. Today renders attachment ID + title + token count. |
| Spec 0145 | §5.4 | Original design intent: markdown / thumbnail / download surface per attachment. Gated on a fresh attachment-bearing run; D09 supplies. |

### 4.9 — Dead `Preflight*Tab` components (D20)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 6268, 6272, 6288, 6308, 6331, 6369 | `PreflightContentTab`, `PreflightSourcesTab`, `PreflightFilesTab`, `AttachmentsEmpty`, `SourceRowAttachment`, `FileCard`. All have ZERO external callers as of post-0148. Only internal cross-references between the six. |

### 4.10 — Diagrams (D21)

| File | Lines | Role |
|---|---|---|
| `diagrams/deep-research-pipeline.{light,dark}.svg` | (whole files) | Source diagrams. Regenerate with canonical-ID labels including `system.web_sources` + `system.tool_definitions`. |
| `src/dual_research/ui/static/diagrams/deep-research-pipeline.{light,dark}.svg` | (whole files) | Bundled copies in the UI static tree. Mirror after regeneration. |
| `src/dual_research/ui/static/how-it-works.jsx` | 748, 770, 799 | `diagramName: '02-phase-inputs'` — three call-sites that need rewiring to `'deep-research-pipeline'`. |

### 4.11 — Orphaned CSS (D22)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/components.css` | 2540–2541 | `.ccx-header .stats .sep` and `.ccx-header .stats .pct` rules. Zero JSX matches confirmed. |

### 4.12 — `p0StatsRoundCount` + `PhaseContent` (D23)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/live-data.jsx` | 548, 696, 822 | `p0StatsRoundCount` (line 548; legacy infix) vs `p2StatsCount` (line 696) / `p4StatsCount` (line 822). The Phase 0 variant carries the legacy `Round` infix from the pre-0114 fallback path. |
| `src/dual_research/ui/static/run-detail.jsx` | 7672 | `function PhaseContent() { … }` — defined, zero callers as of post-0148. |

---

## 5. Proposed change

### 5.1 — D09: fire the fresh-run smoke FIRST

Before any code change in §5.3–§5.8, fire `/dual-research-run` (via the `dual-research-run` skill if available, else by hand) against a brief that is:
1. **Drift-prone** (Phase 4 deadlock risk — a topic with multi-axis legitimate disagreement, e.g. "backend language for X" / "monolith vs microservices for Y").
2. **Attachment-bearing** (at least one PDF / markdown / image attached to the user prompt — required for D19).

Push live (`--push-while-running`). Capture `<session>/usage-debug.jsonl` for D02 (set `DUAL_RESEARCH_DEBUG_USAGE=1` at run time). Cost: ~$10 LLM spend, ~15 min.

After the run completes, the implementation session has:
- A fresh `transcript.jsonl` to read `EmptyTurnDetected` events from (D04 input)
- A fresh `usage-debug.jsonl` to inspect for cache-control behaviour (D02 input)
- A fresh set of `search_N` records + `consulted_sources` (D17 baseline)
- A fresh set of validator `unverified` flags (D18 input)
- A fresh attachment-bearing run to design D19 against
- A live exercise of 0148's untested-on-real-output surfaces (D11-Anthropic, D13/D14 agent-layer emit, D03 active chips)

### 5.2 — D24: file the fly.io support ticket

Before the post-0149 deploy, file a ticket via the fly.io support portal describing the seven consecutive deploys (0140, 0141, 0142, 0144, 0146, 0147, 0148) that hit the same `machines.dev` mid-rolling-deploy timeout — machine 1 healthy first pass, machine 2 reaches `stopped` when `machines.dev` API times out waiting on health checks, recovered by `fly machine start <id>`. Include the seven app names + deploy timestamps from the handover files. No code change.

### 5.3 — D02: Anthropic cache engagement

**Diagnostic step** (read-only, from §5.1's output):
1. Open `<session>/usage-debug.jsonl`. For one Claude turn (any phase), inspect the raw SDK request payload. Check whether `cache_control: {"type": "ephemeral"}` markers are present in the system / user content blocks, and whether the response's `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` are non-zero.
2. Three possible diagnoses:
   - **Env-side**: SDK strips `cache_control` headers silently (e.g. `anthropic` SDK version too old, or `extra_headers` not threading through). Fix: bump SDK, or re-route the header through the supported field.
   - **Request-side**: `cache_control` markers ARE present but on content that doesn't qualify (e.g. the breakpoint sits inside content that changes per-turn → no cache hit). Fix: re-position the breakpoints to land on stable prefixes only (system preamble + task instructions, not turn-specific content).
   - **Eligibility-side**: per-call content under cache breakpoint is below Anthropic's 1024-token minimum. Fix: extend cache breakpoint to include enough prior turns to clear the threshold.

**Fix step** (depends on diagnosis):
- The fix touches `_split_and_apply_ephemeral_cache()` at [anthropic_agent.py:306](src/dual_research/agents/anthropic_agent.py) and the caller that decides which content blocks get `cache_control` markers.
- Re-fire one Claude turn locally with `DUAL_RESEARCH_DEBUG_USAGE=1` after each candidate fix; iterate until `cache_read_input_tokens > 0` on turn 2 of the same session.

**Validation** (after deploy):
- Open the CcxCard for any Claude turn on the post-fix run; the totals block must render `cache savings · ×N reuse on Xkt · $0.X` with `$0.X > 0`. (This row was added in 0148 — its absence today is a true zero, not a render bug.)
- Reconcile: total Claude cost on the post-fix run should drop relative to a same-shaped pre-fix run by roughly `cache_read_tokens × (input_per_mtok - cache_read_per_mtok) / 1e6` per turn. Order-of-magnitude check; tight reconcile is out of scope.

### 5.4 — D04: empty-turn prompt tightening

Read every `EmptyTurnDetected` event from §5.1's `transcript.jsonl`. For each, note (a) which phase, (b) which agent, (c) what the model output WAS (likely a status line with no operation block).

In [protocol/prompts.py:489](src/dual_research/protocol/prompts.py) (the STATUS: AGREED constraint toggle), add a constraint line like:

```
Every turn MUST contain at least one operation block (OP: RAISE, OP: ADDRESS,
OP: COMMENT, OP: AGREED, OP: PROPOSE, OP: REQUEST_EVIDENCE, ...) OR a
top-level STATUS: AGREED line. A turn with only status text and no
operation/agreement is invalid; emit an explicit STATUS: AGREED if you
have nothing to add.
```

Wording calibrated to whatever the §5.1 `EmptyTurnDetected` events reveal as the real failure mode. If the events fire on "model says 'continuing review' with no block", the language above is correct. If they fire on a different shape (e.g. model emits a block but the parser rejects it), the fix is parser-side, not prompt-side — escalate as a follow-up rather than ship the wrong tightening.

No retry path in v1.14.0. The prompt makes empty turns structurally impossible; we re-measure after deploy. If `EmptyTurnDetected` keeps firing post-deploy, a retry hook in the orchestrator turn loop is the v1.14.1 fix.

### 5.5 — D17: search_N resolution

Read every `search_N` reference in §5.1's transcript and cross-reference against the run's `consulted_sources`. Two ratios:
- `search_N` references *with* a resolved source: should be > 60% post-fix
- `search_N` references *without* a resolved source: the false-positive set

If the false-positive set is dominantly *model-emitted-references-with-no-actual-source* → tighten the prompt fragment in [protocol/prompts.py](src/dual_research/protocol/prompts.py) that explains the citation contract. Add: "Only emit `search_N` when you actually consulted source N. Do not emit `search_N` to reference your own prior reasoning."

If the false-positive set is dominantly *real-sources-that-the-capture-path-missed* → fix [contract/evidence.py:154](src/dual_research/contract/evidence.py) (the resolution function). Likely an off-by-one in how `consulted_sources` indices align with the `search_N` numbering convention.

Pick whichever side D09 surfaces as dominant; touch only that side.

### 5.6 — D18: validator over-flagging measurement

For every item on the §5.1 run with `unverified=True`:
1. Open the source item, read the underlying claim.
2. Open the run's `consulted_sources` (or relevant attached file).
3. Classify: true-positive (claim genuinely has no source backing) vs false-positive (claim is supported, validator missed it).

Compute false-positive rate. Write a one-paragraph summary into the 0149 handover.

- If FP rate < 50%: D18 closes. Validator is calibrated reasonably; over-flagging is within tolerance.
- If FP rate ≥ 50%: D18 opens a follow-up spec for the prompt-side fix to the validator. No code change in 0149 — measurement only.

### 5.7 — D19: per-attachment rich previews

Inside `SubInputRow` at [run-detail.jsx:2336](src/dual_research/ui/static/run-detail.jsx):

```jsx
function SubInputRow({ piece, ...existingProps }) {
  // ... existing token count + title rendering ...

  if (piece.attachmentId) {
    return (
      <div className="sub-input-row sub-input-row--attachment">
        {existing left col (icon + canonical ID label)}
        {existing right col (token count + chevron)}
        {expanded && <AttachmentPreview attachmentId={piece.attachmentId} title={piece.displayTitle} />}
      </div>
    );
  }
  // ... existing non-attachment branch ...
}

function AttachmentPreview({ attachmentId, title }) {
  // Routes by file type:
  // - .md / .txt → render as <pre> with monospace; truncate at 80 lines + "view more" link
  // - .pdf → render <iframe src={`/api/attachments/${attachmentId}`} className="attachment-preview attachment-preview--pdf"> 
  // - .png/.jpg/.gif → render <img src={`/api/attachments/${attachmentId}`} className="attachment-preview attachment-preview--image">
  // - else → render <a href={`/api/attachments/${attachmentId}`} download>{title}</a>
}
```

`/api/attachments/<id>` endpoint: confirm at impl time whether one exists or whether D19 also ships the endpoint. Likely already exists from spec 0145's session-files plumbing — verify before designing the FE.

CSS for `.attachment-preview` variants in `components.css` (one new rule block; reuse existing tokens — no new design-system additions).

### 5.8 — D06: gpt-5-mini pricing audit

Open https://platform.openai.com/docs/pricing and read the current `gpt-5-mini` row. Compare against [pricing.py:86–92](src/dual_research/agents/pricing.py):
- `input_per_mtok`: $0.25 (currently)
- `output_per_mtok`: $2.00 (currently)
- `cache_read_per_mtok`: $0.025 (currently)

If any rate differs:
1. Update [pricing.py:86–92](src/dual_research/agents/pricing.py).
2. Bump `PRICING_VERSION` per the existing pattern (spec 0143).
3. Update `tests/agents/test_pricing_version.py` to expect the new version.

If all three match: no code change; note "audited, current" in the handover.

### 5.9 — D07: anchor-run draft salvage

One-shot script at `scripts/salvage_anchor_run_draft.py`:

```python
#!/usr/bin/env python3
"""Salvage the anchor run's draft body (lines 47–312 of round-07-claude.md)
into a clean final.md. One-shot — not part of the production pipeline.

Spec 0149 D07.
"""
from pathlib import Path

ANCHOR_DIR = Path("runs/20260521-010637-dvs-backend-language-choice")
SOURCE = ANCHOR_DIR / "phase4" / "round-07-claude.md"
DEST = ANCHOR_DIR / "final.md"

lines = SOURCE.read_text().splitlines()
draft_body = "\n".join(lines[46:312])  # 0-indexed: lines 47-312 (inclusive)
DEST.write_text(draft_body + "\n")
print(f"Wrote {DEST} ({len(draft_body.splitlines())} lines)")
```

Run once; commit the resulting `final.md` alongside the script.

### 5.10 — D20: dead Preflight*Tab cleanup

Delete in `run-detail.jsx`:
- `PreflightContentTab` at line 6268
- `PreflightSourcesTab` at line 6272
- `PreflightFilesTab` at line 6288
- `AttachmentsEmpty` at line 6308
- `SourceRowAttachment` at line 6331
- `FileCard` at line 6369

Plus any internal cross-references between them. Pre-check (mandatory): grep each name across `src/dual_research/ui/static/` — any external caller is a precondition fail, halt and surface for review.

Per the 0148 retrospective: confirm none of these components reference `run.violations`, `usage.outputBreakdown`, `usage.cacheSavingsUsd`, `ViolationChip`, or `DYNAMIC_SEPARATE_KEYS`. (Almost certainly clean; they're old preflight code.)

### 5.11 — D22: orphaned CSS cleanup

Delete [components.css:2540–2541](src/dual_research/ui/static/components.css):

```css
.ccx-header .stats .sep { … }
.ccx-header .stats .pct { … }
```

Both have zero JSX matches as of 0148's `.ccx-header` rework. Deletion is purely a noise reduction.

### 5.12 — D23: variable rename + `PhaseContent` deletion

In [live-data.jsx](src/dual_research/ui/static/live-data.jsx) line 548 region:
- Rename `p0StatsRoundCount` → `p0StatsCount` (all references in this file, expected ~3–4 sites). Parallel naming with `p2StatsCount` / `p4StatsCount`.

In [run-detail.jsx:7672](src/dual_research/ui/static/run-detail.jsx):
- Delete the entire `function PhaseContent() { … }` block. Zero callers (verified post-0148).

### 5.13 — D21: diagram regeneration + How-It-Works rewire

Regenerate `deep-research-pipeline.light.svg` and `deep-research-pipeline.dark.svg` from the diagram-source pipeline (location TBD at impl time — look in `diagrams/Makefile` or `diagrams/regen.py` if one exists; if not, the SVGs are hand-edited and the spec scope expands to include a source-of-truth strategy).

Label set must include every canonical artifact ID from `contract/artifacts.py:REGISTRY` that's user-facing in the pipeline visual — including the two new IDs `system.web_sources` and `system.tool_definitions` registered in 0148. Source the label set programmatically (`from dual_research.contract.artifacts import REGISTRY`).

Update [src/dual_research/ui/static/diagrams/](src/dual_research/ui/static/diagrams/) with the regenerated files.

In [how-it-works.jsx:748, 770, 799](src/dual_research/ui/static/how-it-works.jsx), rewire `diagramName: '02-phase-inputs'` → `diagramName: 'deep-research-pipeline'`. Three sites.

If `02-phase-inputs.{light,dark}.svg` is no longer referenced anywhere after the rewire, delete it (grep first; do not delete on assumption).

---

## 6. Test plan

- [ ] **D09 smoke**: fresh `/dual-research-run` on a drift-prone + attachment-bearing brief succeeds end-to-end; all 0148-introduced surfaces (violation chips, output breakdown if reasoning > 0, cache savings line, web_sources / tool_definitions rows) render correctly on real data.
- [ ] **D02 unit**: `_split_and_apply_ephemeral_cache` on a fixture conversation produces request payload with `cache_control` markers on stable-prefix content only. The unit test pins the breakpoint placement so a future refactor can't silently drop it.
- [ ] **D02 anchor (post-deploy)**: a fresh Claude turn on the post-fix deploy emits `usage.cache_read_input_tokens > 0` (visible in `usage-debug.jsonl` or via the `CcxCard` totals block).
- [ ] **D04 unit**: regenerate the protocol prompts; assert the new "every turn MUST contain at least one operation block OR STATUS: AGREED" language is present in all five phase prompts (preflight, plan-negotiation, drafting, review, closeout).
- [ ] **D04 post-deploy**: a fresh run on the same kind of brief that produced `EmptyTurnDetected` in §5.1 now produces zero net-new events (sample size 1; if it fails to converge, escalate to v1.14.1 retry-loop work).
- [ ] **D06 unit**: pricing table assertion (whichever rates apply post-audit).
- [ ] **D07 manual**: run the salvage script; assert `runs/20260521-010637-dvs-backend-language-choice/final.md` exists with `wc -l` between 250–280.
- [ ] **D08 unit (`tests/contract/test_request_evidence_spec_0149.py`)**: parse a synthetic transcript with one `OP: REQUEST_EVIDENCE` block; assert the parser surfaces it as a `RequestEvidenceBlock`; assert the validator rejects malformed cases (target item doesn't exist; requester is the original author; etc.).
- [ ] **D17 manual**: read §5.1 transcript, compute resolution rate; if < 60% post-fix, escalate.
- [ ] **D18 manual**: classify every `unverified=True` flag from §5.1; compute FP rate; write one paragraph in the handover.
- [ ] **D19 visual**: open the §5.1 run's brief modal + consumption card; assert each attachment shows its rich preview branch (`<pre>` / `<iframe>` / `<img>` / fallback `<a>`).
- [ ] **D20 grep**: `grep -rn "PreflightContentTab\|PreflightSourcesTab\|PreflightFilesTab\|SourceRowAttachment\|FileCard\|AttachmentsEmpty" src/dual_research/ui/static/` returns zero hits after deletion.
- [ ] **D21 visual**: open `/how-it-works` page; assert the new `deep-research-pipeline` diagram renders (light + dark variants).
- [ ] **D22 grep**: `grep -n "\.ccx-header .stats .sep\|\.ccx-header .stats .pct" src/dual_research/ui/static/` returns zero hits after deletion.
- [ ] **D23 grep**: `grep -n p0StatsRoundCount src/dual_research/ui/static/` returns zero hits after rename. `grep -n "function PhaseContent" src/dual_research/ui/static/` returns zero hits after deletion.
- [ ] **Full suite**: `pytest -q` passes; existing 1389 + ~6 new (D02 unit, D04 unit, D06 unit, D08 unit + edge cases). Net: ~1395.
- [ ] **D24 confirmation**: fly support thread exists, recorded in handover.

---

## 7. Risks

- **D02 diagnosis-mismatch.** If §5.3's diagnostic flow doesn't fit any of the three diagnosis branches (env / request / eligibility), we have a fourth failure mode and the fix budget for 0149 doesn't cover it. Mitigation: time-box D02 diagnosis to 1 hour of investigation; if no clean diagnosis, ship the rest of 0149 without D02 and split D02 to a v1.14.1 spec.
- **D04 misdiagnosis.** If `EmptyTurnDetected` is firing on a parser-rejection rather than a model-side empty turn, the prompt tightening is the wrong fix. The risk is shipping a prompt change that doesn't help and might marginally degrade other model behaviour. Mitigation: §5.4 explicitly says "calibrate wording to whatever the events reveal as the real failure mode"; if D09 surfaces parser-rejection cases, escalate as a follow-up rather than ship.
- **D09's brief choice is load-bearing.** If the brief drifts but produces no attachments, D19 stays untested. If it has attachments but doesn't drift, D04 stays untested. Mitigation: pick a brief that is BOTH (multi-axis legitimate disagreement on a technical topic, with a PDF/markdown attached for context). Sample brief topics: "Storage layer for a CRDT-based collaborative editor" + attached architecture doc; "ML pipeline orchestration choice for a 50TB dataset" + attached requirements PDF.
- **D17 / D18 v1.14.0 sample size.** Both decisions ride on a single fresh run (n=1). If the run is unrepresentative, the resolution-rate or false-flag-rate numbers don't generalise. Mitigation: spec is honest about n=1 — D18 explicitly escalates to a follow-up spec rather than declaring closure if FP rate ≥ 50%.
- **D08 protocol surface.** Adding a new op affects every transcript-bearing path. Risk of dead key on the wire if the parser ships but no prompt language references the op. Mitigation: §5 includes a prompt-fragment addition alongside the parser; CI ensures both land together (`test_request_evidence_spec_0149.py` parses fixture transcripts that include the new op).
- **D21 source-of-truth gap.** If diagrams have no regeneration pipeline (i.e. they're hand-edited SVGs), then "regenerate from REGISTRY" is structurally impossible at v1.14.0 and 0149's D21 narrows to "hand-edit the SVG to include the two new IDs". This is the most likely outcome — spec narrows the scope at impl time if so.
- **D20 component-reference miss.** If the cleanup misses an internal cross-reference (e.g. `PreflightSourcesTab` calls `SourceRowAttachment` and we delete one but not the other), the build breaks. Mitigation: §5.10 explicitly says "plus any internal cross-references" and the grep test catches the leftover.
- **D02 reconcile drift.** Post-fix, the run-detail's `total_cost_usd` for Claude turns drops materially. The anchor-run reconcile-rebuild script will register a delta and `test_anchor_run_metrics_pinned_to_old_pricing_version` will fail. Mitigation: same pattern as spec 0143's reconcile-rebuild; update the pin in the same PR if the test goes red.
- **D04 prompt change vs anchor-run replay.** Prompt change means the anchor run is no longer reproducible byte-identically under the new prompts. Mitigation: don't claim byte-reproducibility for the anchor across 0149; record the divergence in the handover.

---

## 8. Open questions

- **D19 `/api/attachments/<id>` endpoint existence.** Confirm at impl time whether spec 0145 / 0146 / 0148 plumbed a public attachments endpoint. If not, D19 spec scope expands to include the endpoint; if yes, D19 is purely FE.
- **D08 prompt fragment placement.** The `RequestEvidence` op's prompt explanation can live in either the per-phase prompt (each phase that supports the op explains it) or a shared "operations vocabulary" preamble. Lean toward the latter for consistency with existing op explanations, but confirm at impl time which pattern is dominant.
- **D21 diagram regeneration pipeline.** Whether `diagrams/` has a Makefile / regen script. If yes, use it. If no, decide between (a) writing one as part of 0149, or (b) narrowing D21 to a hand-edit. Lean toward (b) unless a regeneration pipeline already exists.
- **D24 fly support thread channel.** Whether to file via the fly.io community forum (https://community.fly.io/) or the paid support portal. Sub-question for the operator; spec doesn't prescribe.
- **D02 SDK version pin.** If the diagnosis fingers env-side (SDK strips `cache_control`), the fix may include a `pyproject.toml` version bump of the `anthropic` SDK. Confirm current pinned version at impl time; check release notes for cache-control-related fixes.

---
