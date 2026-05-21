---
spec: 0145
title: Canonical prompt-pieces registry + per-attachment token tracking — protocol, persistence, and consumption surfaces
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.11.0
created: 2026-05-21
pr: ""
---

# Spec 0145 — Canonical prompt-pieces registry + per-attachment token tracking

> Ship bucket: **Protocol prompt-pieces registry + per-attachment token attribution — protocol emitter, Supabase persistence, aggregator passthrough, consumption-tab and full-view surfaces, How-It-Works diagram re-key.**
> Depends on: **0117** (canonical artifact registry — `src/dual_research/contract/artifacts.py`), **0118** (per-piece token-attribution emitter — `src/dual_research/protocol/prompt_pieces.py`), **0142** (prompt capture — fixes the upstream "what string went into the model" record this spec attributes tokens against), **0143** (cost / token attribution — final aggregator passthrough cleanup lands first so this spec only changes keys, not arithmetic), and the **reverted 0139 spec** (`757c588` + `af0890f`, removed in `3dee8b1`) which sketched the same problem and was lifted into the Notion review backlog rather than merged. This spec is the clean restart of that work, scoped tighter and rewritten from first principles in the 0140-batch voice.
> Complexity: **L** — the largest spec in the 0140–0147 batch. Multi-surface (protocol Python · Supabase migration · aggregator passthrough · run-detail JSX · How-It-Works diagram) with one schema delta and one cross-language registry sync. Approximately 8 coordinated workstreams, each scoped tight and individually testable.
> Targeted version bump: **MINOR (1.10.x → 1.11.0)** — additive on the registry / persistence side (new artifact-ID emissions, new optional `attachment_id` column on the prompt-piece persistence table); the Consumption-tab and full-view modals gain a new affordance (per-attachment rows) but the existing roll-up totals are preserved. No protocol contract or convergence-rule change. The legacy short-key vocabulary (`brief`/`d1`/`d2`/`plan`/`hist`/`draft`/`histp`) is **kept as a read-path shim** during the transition release so historical anchor runs continue to render correctly.

---

## 1. Context

### 1.1 — The gap today

The Deep Research protocol has two coexisting "piece identity" vocabularies — one canonical and one legacy — and **neither one currently captures attachments as first-class pieces**. The drift is concentrated in three places:

1. **The emitter collapses the user prompt + attachments into a single `user_prompt` key.** Every `pieces_for_*()` function in [`protocol/prompt_pieces.py`](src/dual_research/protocol/prompt_pieces.py) takes a `user_prompt: str` parameter and emits `"user_prompt": estimate_tokens(user_prompt)` ([prompt_pieces.py:56,68](src/dual_research/protocol/prompt_pieces.py); [82,88](src/dual_research/protocol/prompt_pieces.py); [96,112](src/dual_research/protocol/prompt_pieces.py); [129,140](src/dual_research/protocol/prompt_pieces.py); [156,169](src/dual_research/protocol/prompt_pieces.py)). At the call sites in `dr_run.py` ([573, 716, 723, 894, 1105, 1254](src/dual_research/orchestrator/dr_run.py)) the orchestrator passes `brief_content` — the **brief text** alone — into `user_prompt`. Attachments are materialised into `<session>/attachments/` and indexed in `attachments.json` (per spec 0025), but the protocol prompt-piece emitter never sees them. They are concatenated into the agent's actual prompt upstream of this function, but their token cost is bundled into the single `user_prompt` segment and is not separately attributable.
   - Verified against the live anchor run `20260521-010637-dvs-backend-language-choice`: a `turn_ended` event for `phase2-r1-claude` carries `prompt_pieces` with keys `{user_prompt: 5251, phase1.claude: 10971, phase1.openai: 5525, prior_turns.phase2: 5482, ledger.standing_items: 903, system.task.plan_negotiation: 1903, phase0.agreement.interpretation: 2321}` — one flat `user_prompt: 5251` segment with no attachment decomposition.
   - The same run's `attachments.json` (path `attachments.json` in `session_files`, 24 bytes) reads `{"attachments": []}` — i.e., this run has zero attachments, so the live evidence above shows the **shape** of the gap rather than the data-loss when attachments are present. For runs that **do** carry attachments today (any past run with PDFs, screenshots, or linked source documents), every per-attachment byte rolls into a single un-attributable `user_prompt` segment on the Consumption tab.

2. **The registry already templates the per-attachment ID — but no code emits it.** [`contract/artifacts.py:167-170`](src/dual_research/contract/artifacts.py) defines three `ArtifactDef`s in the `USER` family:
   ```python
   ArtifactDef("user_prompt", "User prompt", ArtifactKind.USER, "run", False),
   ArtifactDef("user_prompt.message", "Chat message", ArtifactKind.USER, "run", False),
   ArtifactDef("user_prompt.attachment.<id>", "Attachment · {title}", ArtifactKind.USER, "run", False),
   ```
   The first is the legacy composite — what the emitter currently produces. The second and third are the canonical IDs the registry intends — what the emitter **should** produce. `display_name()` ([artifacts.py:244-258](src/dual_research/contract/artifacts.py)) already knows how to resolve `user_prompt.attachment.<id>` against a `title_for_id` map; the consumer side of the contract is already wired. The producer side never landed.

3. **The frontend speaks the pre-0117 short-key vocabulary in full-view modals.** [`run-detail.jsx:5071-5089`](src/dual_research/ui/static/run-detail.jsx) defines `INPUT_PIECE_LABEL`, `INPUT_PIECE_ORDER`, and `INPUT_PIECE_DEFAULT_COLLAPSED` keyed by the legacy short alphabet — `{system, brief, d1, d2, plan, hist, draft, histp}`. The same legacy keys are persisted to `inputs/<turnKey>.json` ([aggregator.py:734-779](src/dual_research/ui/aggregator.py); the anchor-run `turn_inputs` payload's `pieces` dict has keys `['d1','d2','hist','plan','brief','draft','histp','system']`). The Consumption tab speaks the canonical-ID dialect (via `hasNewVocabPieces` + `groupPiecesForPhase` at [run-detail.jsx:1992,2028,2061,2089,2168](src/dual_research/ui/static/run-detail.jsx)), so today's run-detail surface has the Consumption tab speaking one vocabulary and `InputTabContent` / `AgentInputDualPane` / the side-by-side modals speaking another. A "User prompt: Brief" row on the modal and a "user_prompt" segment on the consumption card are the same piece — but they read as different concepts to anyone scanning both surfaces in the same screen.

### 1.2 — Prior art: the reverted 0139 spec

A version of this work was drafted directly on `main` and then removed before any implementation landed. The history:

- **`757c588`** — `spec 0139 — canonical prompt-pieces, per-attachment token tracking, and full-view alignment`. Initial spec landed on `main` (202 lines).
- **`af0890f`** — `spec 0139 — add diagram regeneration + How It Works wire-up + CI parity test`. Extended §7 with the diagram regeneration plan.
- **`3dee8b1`** — `remove specs/0139 — moved to Notion review backlog`. Removed the on-disk spec; explicit commit message: *"the underlying functionality has not been built. Removing the on-disk spec frees the 0139 slot so the next reviewed item can take it. Full draft content preserved verbatim as Improvement 5 in the Notion 'Claude report: bugs, improvements, investigation' page."*

The reverted 0139 spec proposed **eight coordinated workstreams** in a single change: (1) decompose `user_prompt` in the emitter, (2) wire `system.preamble` and `system.task.closeout`, (3) replace the legacy UI piece vocabulary, (4) restructure single-view modals, (5) restructure side-by-side modals, (6) widen aggregator + per-turn JSON persistence, (7) regenerate `deep-research-pipeline.{light,dark}.svg`, (8) wire the regenerated diagram into How It Works. The breadth — and the implicit "land all eight or none" coupling — was a stated reason for the move-to-backlog decision: the workstreams interact tightly enough that none is meaningfully done without the others, but they don't all have the same urgency or risk surface.

### 1.3 — How this spec differs

This restart deliberately narrows the proposed change in three ways:

1. **The Supabase persistence path is the load-bearing addition.** Per-attachment tokens have to land in the schema (not just in transcript JSONB) so the Consumption tab can render historical runs without re-aggregating events. The reverted 0139 spec deferred the schema question to "out of scope; per-turn `inputs/<turnKey>.json` keys change in the same migration" — but the production database has no `inputs/<turnKey>.json` files; it has `events.payload` JSONB and the per-turn-key segments inside `prompt_pieces`. This spec proposes a **dedicated `turn_prompt_pieces` table** (one row per `(run_id, turn_key, artifact_id)` triple) so per-attachment tokens are first-class queryable columns rather than nested JSONB. Quoted migration sketch in §5.2.
2. **The UI piece-vocabulary swap is decoupled from the consumption-card rework.** Spec **0146** (consumption card rework) lands the visual restructure of the consumption row; this spec lands the data plumbing that 0146 will read. They share an ordering dependency (this spec lands first) but no shared file edits beyond the registry-driven label resolution.
3. **The diagram regeneration is deferred to a follow-up.** The reverted 0139 spec proposed regenerating `deep-research-pipeline.{light,dark}.svg` and re-wiring `how-it-works.jsx`. This restart keeps the diagram update as the **last** workstream (§5.4) but explicitly marks it as "land if time permits; otherwise file a follow-up". The protocol+persistence+UI changes ship without it. The CI diagram-parity test (reverted 0139's enforcement mechanism) lands with the diagram update, not now.

The net change: spec 0145 is **B15 minus the diagram-parity CI gate**, with the persistence path lifted from "incidental" to "load-bearing", and the UI rework narrowed to "make the modals read by canonical ID" (no consumption-card visual restructure — that's 0146).

The four other 0140-batch specs that touch overlapping surfaces — 0142 (prompt capture), 0143 (cost / token + header polish), 0144 (sources / provenance + critique cards), 0146 (consumption card rework) — are explicitly aware of this spec's ID renames; their own specs do not assume the legacy short-key vocabulary holds.

---

## 2. Goals

1. **Decompose `user_prompt` in the protocol emitter.** Every `pieces_for_*()` function in `protocol/prompt_pieces.py` emits one `user_prompt.message` key plus zero-or-more `user_prompt.attachment.<id>` keys (one per attachment). The aggregate `user_prompt` key is **dropped from the emitted dict** — historical runs that still carry it render via a read-path shim (Goal 5).

2. **Land the persistence path: `turn_prompt_pieces` table.** New Supabase table `turn_prompt_pieces` indexed by `(run_id, turn_key, artifact_id)` carrying per-piece token counts, attachment ID (nullable), and the resolved display title at push time. The push CLI populates this table from the `prompt_pieces` payload on every `turn_ended` event; the UI server's consumption endpoint reads it directly. The existing `events.payload.prompt_pieces` JSONB is **preserved unchanged** (no migration of historical events — the table is forward-looking and the legacy JSONB is the fallback).

3. **Aggregator + per-turn input persistence: passthrough the canonical IDs unchanged.** `src/dual_research/ui/aggregator.py` already forwards `prompt_pieces` verbatim ([aggregator.py:473-475, 521](src/dual_research/ui/aggregator.py)) — confirm no key-normalisation step exists, document the contract, add a regression test. The per-turn input-bundle persistence (`inputs/<turnKey>.json` via `_on_turn_inputs`) gains the same `user_prompt.message` + `user_prompt.attachment.<id>` keys produced by an updated `protocol/prompts.py::*_input_bundle()`.

4. **Replace the legacy UI piece vocabulary with canonical artifact IDs in the full-view modals.** `INPUT_PIECE_LABEL`, `INPUT_PIECE_ORDER`, `INPUT_PIECE_DEFAULT_COLLAPSED` ([run-detail.jsx:5071-5089](src/dual_research/ui/static/run-detail.jsx)) are deleted; a `displayNameOf(canonicalId, attachmentTitles)` helper resolves via `window.DrArtifacts.displayName` (already exposed at [run-detail.jsx:2090-2091](src/dual_research/ui/static/run-detail.jsx)); a `phaseOrderFor(phaseNum)` function defines per-phase arrival order keyed to the canonical IDs.

5. **Add a read-path shim for legacy-key runs.** Historical runs (the anchor `20260521-010637-dvs-backend-language-choice` is a representative case — its persisted `pieces` keys are still `{d1,d2,hist,plan,brief,draft,histp,system}`) render via a mapping `LEGACY_KEY_TO_CANONICAL` in the new `artifact-display.js` module. The shim is documented with a `# REMOVE AFTER 2026-08-01` comment; sunset is a follow-up spec post-anchor-run-rotation.

6. **Surface per-attachment rows on the Consumption tab.** `CcxCard` ([run-detail.jsx:2117-2406](src/dual_research/ui/static/run-detail.jsx)) gains a per-attachment row under its "User prompt" group when `user_prompt.attachment.<id>` keys are present. The group label collapses to a single "User prompt" total by default (matching today's behaviour), with an expand-affordance revealing the per-attachment breakdown. Visual restructure of the consumption row itself is **out of scope** (spec 0146).

7. **Full-view modals read by canonical ID.** `InputBriefModal` ([run-detail.jsx:5636](src/dual_research/ui/static/run-detail.jsx)) and `PreflightResponseModal` ([5682](src/dual_research/ui/static/run-detail.jsx)) restructure to three sections: System prompt · User prompt · Derived inputs. The existing Sources / Files tabs ([5659-5667](src/dual_research/ui/static/run-detail.jsx)) move into the User-prompt section under per-attachment rows; the `Content` tab is renamed `User prompt`. The side-by-side modals (`NegotiateReviewModal` [3982], `DraftReviewModal` [4414]) and `AgentInputDualPane` ([5005](src/dual_research/ui/static/run-detail.jsx)) drop their legacy-vocab pieces dict in favour of canonical-ID reads.

8. **No regressions on the consumption-card existing roll-up totals, no regressions on the anchor-run backfill rendering.** The anchor run renders with the same per-phase totals as today (the legacy-key shim translates pre-spec data on the read path); new runs render with per-attachment decomposition (which the anchor doesn't exercise because it has zero attachments).

---

## 3. Non-goals

- **No consumption-card visual restructure.** Spec **0146** owns the per-row layout, bar geometry, and grouping affordances. This spec changes only the **data** fed into the existing card.
- **No prompt-capture fix.** Spec **0142** owns the "what string actually went into the model" capture path. This spec assumes the captured string is correct and only changes how its component pieces are accounted for. If 0142 lands first and changes the captured shape, this spec absorbs the new shape (the `pieces_for_*()` signature is the boundary) without re-architecting.
- **No phase-converged protocol contract rewrite.** Convergence rules, item-lifecycle rules, the AGREED/AGREED_PLAN/AGREED_INTERPRETATION blocks, phase 1's one-shot contract, and phase 3's drafter selection are unchanged.
- **No backfill of historical Supabase rows into the new `turn_prompt_pieces` table.** Historical events stay in `events.payload.prompt_pieces` JSONB; the UI reads them via the shim. A backfill job is a follow-up if the analytics use case appears.
- **No output-side per-piece tokens.** Output artifacts keep their canonical IDs for provenance and timeline labelling, but `output_tokens` stays atomic per turn (provider-reported, not estimated per output piece). Explicit scope cut, carried over from the reverted 0139.
- **No diagram regeneration / How-It-Works rewire.** `deep-research-pipeline.{light,dark}.svg` is referenced in §5.4 as a follow-up. `how-it-works.jsx` continues to embed `02-phase-inputs.{light,dark}.svg` via the three `HiwDiagram` slots ([how-it-works.jsx:748,770,799](src/dual_research/ui/static/how-it-works.jsx)). If implementation has slack at the end, the diagram update lands; otherwise it's a follow-up.
- **No CI diagram-parity test.** That enforcement mechanism follows the diagram regeneration. Filing it now would gate a regeneration that this spec explicitly defers.
- **No `system.preamble` / `system.task.closeout` investigation.** The registry currently defines both at [artifacts.py:151-152, 163-164](src/dual_research/contract/artifacts.py) but no `pieces_for_*()` emits them. Resolving "is there an actual methodology preamble in the system prompt" requires a read of [protocol/prompts.py:937-1216](src/dual_research/protocol/prompts.py) and a coordinated touch across every emitter call site. **Filed as a follow-up spec.** This spec's emitter changes are additive on the user-prompt side only.
- **No removal of the legacy `user_prompt` `ArtifactDef`.** The registry entry at [artifacts.py:165-166](src/dual_research/contract/artifacts.py) stays for one release as the fallback path the read-shim resolves to. Removal tracked in the same follow-up that sunsets the shim.
- **No `repair` / `hashdrift` siblings get per-attachment decomposition this release.** Their turn keys already get the `_repair` suffix ([aggregator.py:468-469, 760-762](src/dual_research/ui/aggregator.py)); their `prompt_pieces` continue to flow through the same path; the per-attachment decomposition applies uniformly because `pieces_for_*()` is the producer. No separate handling.

---

## 4. Current-state audit

### 4.1 — Protocol prompt-piece emitter (Goal 1)

| Element | File | Lines | Current state |
|---|---|---|---|
| `pieces_for_preflight` | [prompt_pieces.py:53-76](src/dual_research/protocol/prompt_pieces.py) | 53–76 | Takes `user_prompt: str`; emits `"user_prompt": estimate_tokens(user_prompt)` (line 68). |
| `pieces_for_research_plan` | [prompt_pieces.py:79-90](src/dual_research/protocol/prompt_pieces.py) | 79–90 | Same signature; emits `"user_prompt"` (line 88). |
| `pieces_for_plan_negotiation` | [prompt_pieces.py:93-123](src/dual_research/protocol/prompt_pieces.py) | 93–123 | Same signature; emits `"user_prompt"` (line 112). |
| `pieces_for_drafting` | [prompt_pieces.py:126-150](src/dual_research/protocol/prompt_pieces.py) | 126–150 | Same signature; emits `"user_prompt"` (line 140). |
| `pieces_for_review` | [prompt_pieces.py:153-178](src/dual_research/protocol/prompt_pieces.py) | 153–178 | Same signature; emits `"user_prompt"` (line 169). |
| Orchestrator call sites | [dr_run.py:573,716,723,894,1105,1254](src/dual_research/orchestrator/dr_run.py) | various | Every call passes `user_prompt=brief_content`. `brief_content` is the brief text **alone**; attachments are not threaded in. |
| `renormalize` helper | [prompt_pieces.py:181-198](src/dual_research/protocol/prompt_pieces.py) | 181–198 | Scales piece counts to sum to `target_total`. Already key-agnostic — no change needed for §5.1's split. |

### 4.2 — Canonical registry (already in place)

| Element | File | Lines | Current state |
|---|---|---|---|
| `ArtifactDef` shape | [artifacts.py:141-147](src/dual_research/contract/artifacts.py) | 141–147 | `(id_template, display_template, kind, scope, per_agent)`. |
| `user_prompt` (legacy composite) | [artifacts.py:165-166](src/dual_research/contract/artifacts.py) | 165–166 | `"user_prompt" → "User prompt"`. Read-path shim target. |
| `user_prompt.message` | [artifacts.py:167-168](src/dual_research/contract/artifacts.py) | 167–168 | `"user_prompt.message" → "Chat message"`. **Not currently emitted.** |
| `user_prompt.attachment.<id>` | [artifacts.py:169-170](src/dual_research/contract/artifacts.py) | 169–170 | `"user_prompt.attachment.<id>" → "Attachment · {title}"`. Template-variable resolution via `title_for_id` map already wired in `display_name()`. **Not currently emitted.** |
| `display_name()` | [artifacts.py:244-280](src/dual_research/contract/artifacts.py) | 244–280 | Takes optional `title_for_id: dict[str, str]` to resolve `<id>` against attachment metadata. Returns the unchanged `artifact_id` if no template matches (registry-incomplete signal). |
| Template-var regex | [artifacts.py:222-235](src/dual_research/contract/artifacts.py) | 222–235 | `<agent>`, `<N>`, `<id>` placeholders compiled at import. `<id>` matches `[^.]+(?:\..+)?` — accommodates attachment IDs with dots in them. |

### 4.3 — Persistence path (Goal 2)

| Element | File | Lines | Current state |
|---|---|---|---|
| `runs` table | [supabase/migrations/0001_initial.sql:14-29](supabase/migrations/0001_initial.sql) | 14–29 | Carries `state JSONB` + `metrics JSONB`. The anchor run's `metrics` has top keys `[calls, ended_at, started_at, total_cost_usd, pricing_version, totals_by_agent, total_search_cost_usd]` — 39 `calls` entries; no per-piece breakdown column. |
| `events` table | [supabase/migrations/0001_initial.sql:33-42](supabase/migrations/0001_initial.sql) | 33–42 | `(run_id, seq, ts, kind, payload JSONB)`. The anchor's `turn_ended` event at `seq=83` has `payload.prompt_pieces` carrying the canonical-ID dict (verified live: `{user_prompt: 5251, phase1.claude: 10971, …}`). This stays as the source-of-truth event stream. |
| `session_files` table | [supabase/migrations/0001_initial.sql:44-50](supabase/migrations/0001_initial.sql) | 44–50 | `(run_id, path, content, size_bytes)`. The anchor's `attachments.json` row has `content = '{"attachments": []}\n'`, `size_bytes = 24` — i.e., this run has zero attachments. Per-attachment rows in this table would be `attachments/<filename>` paths with their text content (markdown attachments are materialised via `materialise_local_markdown_attachments` in [cli.py:295-298](src/dual_research/cli.py)). |
| `attachment_blobs` table | [supabase/migrations/0003_attachment_blobs.sql:14-21](supabase/migrations/0003_attachment_blobs.sql) | 14–21 | `(run_id, rel_path, mime, size_bytes, content_b64)`. Binary attachments (images / PDFs / opaque files). Spec 0025. |
| Migration sequence | [supabase/migrations/](supabase/migrations/) | — | 0001 initial, 0002 approved_emails, 0003 attachment_blobs, 0004 reconcile_results, 0005 onboarding_state. **Next free slot: 0006**. |

### 4.4 — Aggregator passthrough (Goal 3)

| Element | File | Lines | Current state |
|---|---|---|---|
| `_on_turn_ended` reads `prompt_pieces` | [aggregator.py:473-476](src/dual_research/ui/aggregator.py) | 473–476 | `pieces_raw = event.get("prompt_pieces") or {}`; coerces keys to str, values to int; no key normalisation. **This is exactly the contract this spec wants — verified, no code change needed.** |
| `TurnTokenUsage.prompt_pieces` | [aggregator.py:521](src/dual_research/ui/aggregator.py) | 521 | Stored verbatim on the per-turn usage struct, surfaced to the UI via `usage.promptPieces`. |
| `_on_turn_inputs` reads `pieces` | [aggregator.py:734-779](src/dual_research/ui/aggregator.py) | 734–779 | Writes `inputs/<turnKey>.json` with `pieces` keyed by whatever the orchestrator emitted (legacy short keys today — verified live: anchor's `turn_inputs` payload's `pieces` keys = `[d1,d2,hist,plan,brief,draft,histp,system]`). |

### 4.5 — Frontend consumption + full-view (Goals 4, 6, 7)

| Element | File | Lines | Current state |
|---|---|---|---|
| Legacy piece vocab | [run-detail.jsx:5071-5089](src/dual_research/ui/static/run-detail.jsx) | 5071–5089 | `INPUT_PIECE_LABEL = {system, brief, d1, d2, plan, hist, draft, histp}`, `INPUT_PIECE_ORDER = […]`, `INPUT_PIECE_DEFAULT_COLLAPSED = new Set(['system'])`. Three module-level dicts. |
| `InputTabContent` | [run-detail.jsx:5103-5141](src/dual_research/ui/static/run-detail.jsx) | 5103–5141 | Reads `bundle.pieces`, filters by `INPUT_PIECE_ORDER`, falls through to any extra keys. **Renders by legacy key.** |
| `InputSection` | [run-detail.jsx:5149-…](src/dual_research/ui/static/run-detail.jsx) | 5149+ | Resolves label via `INPUT_PIECE_LABEL[piece] || piece`. Char + token stats inline. |
| `displayNameForItem` | [run-detail.jsx:3868-3905](src/dual_research/ui/static/run-detail.jsx) | 3868–3905 | Already routes through `window.DrArtifacts.displayName` for canonical IDs. **The right resolver — just not wired into the full-view modals' piece-row labels yet.** |
| `window.DrArtifacts.displayName` shim | [run-detail.jsx:2086-2091](src/dual_research/ui/static/run-detail.jsx) | 2086–2091 | Returns the canonical display name if the registry-mirror module is present; falls through to the raw ID otherwise. |
| `CcxCard` | [run-detail.jsx:2117-2406](src/dual_research/ui/static/run-detail.jsx) | 2117–2406 | Renders `usage.promptPieces` via `hasNewVocabPieces` / `groupPiecesForPhase` / `legacyGroupPieces` ([1992, 2028, 2061](src/dual_research/ui/static/run-detail.jsx)). **Already canonical-aware on the consumption tab side.** |
| `consumptionLabel` | [run-detail.jsx:2089-…](src/dual_research/ui/static/run-detail.jsx) | 2089+ | Reads `window.DrArtifacts.displayName(artifactId)` directly. |
| `InputBriefModal` | [run-detail.jsx:5636-5680](src/dual_research/ui/static/run-detail.jsx) | 5636–5680 | Tabs: Content · Agent Input · Sources · Files. Sources & Files only render when the `attachments` array has matching entries; today's anchor run shows neither (no attachments). |
| `PreflightResponseModal` | [run-detail.jsx:5682-…](src/dual_research/ui/static/run-detail.jsx) | 5682+ | Same tab structure for per-agent preflight responses. |
| `NegotiateReviewModal` | [run-detail.jsx:3982-…](src/dual_research/ui/static/run-detail.jsx) | 3982+ | Side-by-side dual-pane. `leftPaneTabsFor` ([4928](src/dual_research/ui/static/run-detail.jsx)) maps phase × round → left-pane document, currently labelled by phase-specific phrase. |
| `DraftReviewModal` | [run-detail.jsx:4414-…](src/dual_research/ui/static/run-detail.jsx) | 4414+ | Same dual-pane shape as Negotiate; left pane is the agreed plan / current draft depending on round. |
| `AgentInputDualPane` | [run-detail.jsx:5005-…](src/dual_research/ui/static/run-detail.jsx) | 5005+ | Renders legacy-keyed input pieces dual-pane (Claude vs GPT). Reads `bundle.pieces`. |

### 4.6 — Diagrams (Goal: deferred follow-up)

| Element | File | Lines | Current state |
|---|---|---|---|
| `diagrams/` authoring source | [diagrams/](/Users/alexlisitzky/dual-research/diagrams/) | — | `deep-research-pipeline.dark.svg`, `deep-research-pipeline.light.svg`, `how-it-works/` subdirectory. |
| `how-it-works/02-phase-inputs.{light,dark}.svg` | [diagrams/how-it-works/](/Users/alexlisitzky/dual-research/diagrams/how-it-works/) | — | The diagram currently bundled into `HiwDiagram` at three call sites. |
| `HiwDiagram` template | [how-it-works.jsx:517-535](src/dual_research/ui/static/how-it-works.jsx) | 517–535 | `src = /diagrams/how-it-works/${name}.${variant}.svg?v=0133a`. Cache-bust suffix `v=0133a` (spec 0133). |
| Three `02-phase-inputs` call sites | [how-it-works.jsx:748,770,799](src/dual_research/ui/static/how-it-works.jsx) | 748, 770, 799 | Phase 0, Phase 1, Phase 2 sections all embed `diagramName: '02-phase-inputs'`. |
| Legacy pipeline SVG | [how-it-works.jsx:56](src/dual_research/ui/static/how-it-works.jsx) | 56 | Changelog entry explicitly notes the legacy `deep-research-pipeline.{light,dark}.svg` remains in `/diagrams/` but is unreferenced. |

---

## 5. Proposed change

### 5.1 — Protocol: piece-id assignment + canonical registry shape

**Signature change** in `src/dual_research/protocol/prompt_pieces.py`. Replace `user_prompt: str` on every `pieces_for_*()` with a composite:

```python
# protocol/prompt_pieces.py — new signature shape
from dataclasses import dataclass
from collections.abc import Iterable

@dataclass(frozen=True)
class Attachment:
    """The minimal piece-emitter view of an attachment.

    Spec 0145 §5.1 — `id` is the canonical attachment ID used in
    `user_prompt.attachment.<id>`; `title` is the human-readable
    string resolved by `display_name()`'s `title_for_id` map at
    render time (lives in `attachments.json`); `content` is the
    text-or-byte payload the model actually sees. Token estimate
    uses `len(content)` like every other piece.
    """
    id: str
    title: str
    content: str


def pieces_for_preflight(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    prior_turns: Iterable[object] | None = None,
    ledger: str | None = None,
    closeout_request: str | None = None,
) -> dict[str, int]:
    out: dict[str, int] = {
        "system.task.input": estimate_tokens(system_task),
        "user_prompt.message": estimate_tokens(user_prompt_message),
    }
    for att in attachments:
        out[f"user_prompt.attachment.{att.id}"] = estimate_tokens(att.content)
    if prior_turns:
        out["prior_turns.phase0"] = _estimate_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out
```

The same shape applies to `pieces_for_research_plan`, `pieces_for_plan_negotiation`, `pieces_for_drafting`, `pieces_for_review`. The aggregate `user_prompt` key is **never written** by any of these — the read-path shim in `artifact-display.js` is the only path that ever surfaces it (for historical-run rendering).

**Emitted key set per phase** (after the change):

- **Phase 0 preflight** → `system.task.input`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, optionally `prior_turns.phase0`, `ledger.standing_items`, `closeout.request`.
- **Phase 1 research plan** → `system.task.research_plan`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`.
- **Phase 2 plan negotiation** → `system.task.plan_negotiation`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, optionally `prior_turns.phase2`, `ledger.standing_items`, `closeout.request`.
- **Phase 3 drafting** → `system.task.drafting`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, `phase2.agreement.plan`, optionally `all_p2_turns`, `carry_forward.phase2`.
- **Phase 4 review** → `system.task.review`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `current_draft`, optionally `prior_turns.phase4`, `ledger.standing_items`, `closeout.request`.

**Orchestrator call-site migration.** Every site in `dr_run.py` that currently calls `pieces_for_*(user_prompt=brief_content, …)` becomes `pieces_for_*(user_prompt_message=brief_content, attachments=attachments_for_run, …)`. The `attachments_for_run` iterable is built once at the top of `dr_run.run_session()` from the brief's already-materialised `attachments` list (already populated by [cli.py:295-298](src/dual_research/cli.py) via `materialise_local_markdown_attachments`). Each `Attachment` is constructed with `id = attachment.id`, `title = attachment.title`, `content = attachment.content` (text attachments) or `content = "<binary>"` placeholder for non-text (their token contribution is the encoded prompt size, which today is opaque to the protocol layer — spec 0142 may revisit; for now, binary attachments contribute zero to the heuristic estimate but still get their own row).

**Six call sites to migrate**: [dr_run.py:573, 716, 723, 894, 1105, 1254](src/dual_research/orchestrator/dr_run.py). All six pass `user_prompt=brief_content` today; all six need the new `attachments=` kwarg too. The signature change is a hard break (Python keyword-only arg, no default), which forces every call site to be updated in one commit — by design.

**Event payload contract.** No change to the `TurnEnded` event schema. The `prompt_pieces` dict carries the new keys; the aggregator already passes it through unchanged ([aggregator.py:473-476](src/dual_research/ui/aggregator.py)). Existing consumers (the Supabase push path, the in-process aggregator, the consumption-tab read path) all stay the same shape.

### 5.2 — Persistence: Supabase schema delta

**New migration**: `supabase/migrations/0006_turn_prompt_pieces.sql`.

```sql
-- Spec 0145 — per-piece token attribution table, indexed by (run_id, turn_key, artifact_id).
--
-- Apply via Supabase Dashboard → SQL editor (single migration, idempotent).
-- Re-running is safe: IF NOT EXISTS guards both the table and the index.
--
-- The push CLI populates this table from the `prompt_pieces` payload on
-- every `turn_ended` event. Each (run_id, turn_key) gets one row per
-- artifact_id emitted by the protocol-side `pieces_for_*()` function.
-- For attachments, `artifact_id` carries the resolved canonical ID
-- (e.g. `user_prompt.attachment.abc123`); `attachment_id` (nullable)
-- is the raw attachment ID for joinability against `session_files` and
-- `attachment_blobs`; `display_title` is the resolved human-readable
-- title at push time (the value `display_name()` would return given
-- the contemporaneous `attachments.json`).
--
-- The UI server's `/api/runs/<id>/consumption` endpoint reads this
-- table directly when available; falls through to `events.payload.prompt_pieces`
-- JSONB when the table has no rows for the run (historical pre-spec runs).
--
-- Backfill of historical runs into this table is OUT OF SCOPE.

CREATE TABLE IF NOT EXISTS turn_prompt_pieces (
    run_id          TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    turn_key        TEXT NOT NULL,
    artifact_id     TEXT NOT NULL,
    tokens          INT NOT NULL,
    attachment_id   TEXT,
    display_title   TEXT,
    PRIMARY KEY (run_id, turn_key, artifact_id)
);

CREATE INDEX IF NOT EXISTS turn_prompt_pieces_run_idx
    ON turn_prompt_pieces (run_id, turn_key);
```

**Push-CLI integration.** When the push CLI iterates the `events` stream, every `turn_ended` event with a non-empty `prompt_pieces` dict produces one INSERT per `(artifact_id, tokens)` pair. The `attachment_id` is parsed via the same regex `_id_template_to_regex("user_prompt.attachment.<id>")` already compiled in [artifacts.py:222-235](src/dual_research/contract/artifacts.py) — when an artifact_id matches, the captured `id` group becomes `attachment_id`. The `display_title` is resolved via `display_name(artifact_id, title_for_id=attachments_index)` at push time; the at-rest title may be stale if a later run rewrites `attachments.json`, but that's deliberate (the value should reflect what the operator saw when the turn ran).

**No change to `runs.metrics` JSONB**, **no change to `events.payload` JSONB**, **no change to `session_files`, `attachment_blobs`, `reconcile_results`, `approved_emails`, `onboarding_state`** — all five existing tables are untouched. Re-pushing a session-dir replaces the new table's rows on conflict (the push CLI's existing upsert pattern extends to the new table by primary key).

**Sample row** for the anchor run, post-migration, derived from the live `turn_ended` `seq=83`:

| run_id | turn_key | artifact_id | tokens | attachment_id | display_title |
|---|---|---|---|---|---|
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `system.task.plan_negotiation` | 1903 | NULL | "Plan-negotiation instructions" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `user_prompt.message` | 5251 | NULL | "Chat message" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `phase1.claude` | 10971 | NULL | "Claude's research plan" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `phase1.openai` | 5525 | NULL | "GPT's research plan" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `phase0.agreement.interpretation` | 2321 | NULL | "Agreed interpretation" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `prior_turns.phase2` | 5482 | NULL | "Prior negotiation turns" |
| `20260521-010637-dvs-backend-language-choice` | `phase2_round1_a` | `ledger.standing_items` | 903 | NULL | "Ledger (standing items)" |

(The anchor run carries zero attachments, so no `user_prompt.attachment.*` rows. For a hypothetical run with two attachments, expect two additional rows with `artifact_id = user_prompt.attachment.<id1>`, `user_prompt.attachment.<id2>`, the matching `attachment_id` populated, and `display_title = "Attachment · <resolved title>"`.)

### 5.3 — Backend pipeline: aggregator passthrough + per-attachment token attribution

**Aggregator path** (`src/dual_research/ui/aggregator.py`):

- **No code change in `_on_turn_ended`** ([aggregator.py:473-476, 521](src/dual_research/ui/aggregator.py)). The `prompt_pieces` passthrough is already key-agnostic. Add a one-line comment block explaining the contract is load-bearing for spec 0145 and that any future normalisation must be added at the *consumer* side, not here.
- **`_on_turn_inputs`** ([aggregator.py:734-779](src/dual_research/ui/aggregator.py)) similarly carries the legacy short-key `pieces` dict verbatim today. Once `protocol/prompts.py::*_input_bundle()` (the producer of the `pieces` dict for the per-turn JSON file) is updated to emit canonical IDs, `_on_turn_inputs` writes the new keys to `inputs/<turnKey>.json` without code change. (The change is in the producer, not here.)

**Per-attachment token computation.** Per-attachment tokens use the same `estimate_tokens(text)` helper ([prompt_pieces.py:26-30](src/dual_research/protocol/prompt_pieces.py)) — `max(1, round(len(text) / 3.5))`. For text attachments (markdown files materialised via `materialise_local_markdown_attachments`), the `content` is the full file text. For binary attachments (image / PDF / opaque file), the protocol layer doesn't have visibility into the actual prompt-encoded token cost (which depends on the provider's binary-to-token encoding), so the heuristic returns 0 for missing `content`. Binary-attachment cost lands in the provider-reported `input_tokens` — the consumption-tab renormaliser ([prompt_pieces.py:181-198](src/dual_research/protocol/prompt_pieces.py)) scales every piece proportionally so the sum matches the billed total. A zero-content binary attachment thus contributes a zero-width row to the consumption card but is still listed (with title and "≈ — t" indicator). A follow-up spec can plumb provider-specific binary token estimates if the gap matters; not in scope.

**Push-CLI side.** The CLI gains one new step in its event-replay loop: when a `turn_ended` event has `prompt_pieces`, derive `turn_key` (the same key shape the aggregator computes — see [aggregator.py:455-462](src/dual_research/ui/aggregator.py)), iterate `prompt_pieces.items()`, parse out attachment IDs where the artifact_id matches the registry template, and upsert rows into `turn_prompt_pieces`. Implementation lives in a new helper `_push_turn_prompt_pieces(run_id, event)` called from the existing `turn_ended` handler in the push pipeline. No change to the existing JSONB write path.

### 5.4 — Frontend: consumption tab + full-view modals + How-It-Works diagram

**New module**: `src/dual_research/ui/static/artifact-display.js`.

```js
// Spec 0145 — JS mirror of contract/artifacts.py REGISTRY display templates,
// plus the legacy-key read-shim used during the transition release.
//
// The Python REGISTRY is the source of truth; this module is regenerated
// at build time from a JSON dump emitted by `contract/artifacts.py` (the
// CI test in §7 asserts parity between the two). The hand-written file
// below is the initial seed; the build step replaces it once 0145 lands.
//
// Exposes:
//   window.DrArtifacts.displayName(artifactId, attachmentTitles?)
//   window.DrArtifacts.phaseOrderFor(phaseNum)
//   window.DrArtifacts.canonicaliseLegacyKey(legacyKey)  // shim

(function () {
  const TEMPLATES = [
    { idTemplate: 'system.preamble', displayTemplate: 'Methodology preamble' },
    { idTemplate: 'system.task.input', displayTemplate: 'Preflight instructions' },
    { idTemplate: 'system.task.research_plan', displayTemplate: 'Research-plan instructions' },
    // … (full list mirrors REGISTRY at contract/artifacts.py:150-217)
    { idTemplate: 'user_prompt.message', displayTemplate: 'Chat message' },
    { idTemplate: 'user_prompt.attachment.<id>', displayTemplate: 'Attachment · {title}' },
    // …
  ];

  // Spec 0145 §5.1 / Goal 5 — legacy short-key → canonical-ID shim. The
  // read-path uses this to translate historical runs (anchor run included)
  // into the new vocabulary. REMOVE AFTER 2026-08-01 (sunset spec tracked
  // as a follow-up; see §6).
  const LEGACY_KEY_TO_CANONICAL = {
    'system': 'system.task.input',      // best-effort; phase-specific in practice
    'brief':  'user_prompt.message',
    'd1':     'phase1.claude',
    'd2':     'phase1.openai',
    'plan':   'phase2.agreement.plan',
    'hist':   'prior_turns.phase2',
    'draft':  'current_draft',
    'histp':  'prior_turns.phase4',
  };

  function displayName(artifactId, attachmentTitles) { /* template-match + substitute */ }
  function phaseOrderFor(phaseNum) { /* per-phase canonical-ID ordering */ }
  function canonicaliseLegacyKey(legacyKey) { return LEGACY_KEY_TO_CANONICAL[legacyKey] || legacyKey; }

  window.DrArtifacts = window.DrArtifacts || {};
  window.DrArtifacts.displayName = displayName;
  window.DrArtifacts.phaseOrderFor = phaseOrderFor;
  window.DrArtifacts.canonicaliseLegacyKey = canonicaliseLegacyKey;
})();
```

**`run-detail.jsx` changes**:

- **Delete** `INPUT_PIECE_LABEL`, `INPUT_PIECE_ORDER`, `INPUT_PIECE_DEFAULT_COLLAPSED` ([5071-5089](src/dual_research/ui/static/run-detail.jsx)).
- **Update `InputTabContent`** ([5103-5141](src/dual_research/ui/static/run-detail.jsx)) to derive its render-order from `window.DrArtifacts.phaseOrderFor(item.phase)`. For each `pieces` key that doesn't match the canonical phase order, translate via `canonicaliseLegacyKey` (legacy-key shim) and append to the end.
- **Update `InputSection`** ([5149+](src/dual_research/ui/static/run-detail.jsx)) to resolve its label via `window.DrArtifacts.displayName(piece, attachmentTitlesMap)`. The `attachmentTitlesMap` comes from `window.useAttachments(run.id)` already in scope at the modal level.
- **`InputBriefModal`** ([5636-5680](src/dual_research/ui/static/run-detail.jsx)) restructure to three sections within a single "User prompt" tab (renamed from "Content"):
  - **System prompt** — collapsible, one row per `system.*` piece.
  - **User prompt** — one row for `user_prompt.message`, then one row per `user_prompt.attachment.<id>` in attachment-list order. Each attachment row carries the title (from `attachmentTitlesMap`), the estimated tokens, and a rendered preview (markdown for text; thumbnail for image; download link for binary). Sources / Files tabs deleted; their content moves into this section.
  - **Derived inputs** — collapsed by default, one row per remaining piece.
- **`PreflightResponseModal`** ([5682+](src/dual_research/ui/static/run-detail.jsx)) — same three-section restructure under its `input` tab.
- **`AgentInputDualPane`** ([5005+](src/dual_research/ui/static/run-detail.jsx)) — reads piece keys by canonical ID. Dual-pane layout unchanged; only the per-row label resolution swaps to `displayName()`.
- **`NegotiateReviewModal`** ([3982+](src/dual_research/ui/static/run-detail.jsx)) and **`DraftReviewModal`** ([4414+](src/dual_research/ui/static/run-detail.jsx)) — left-pane document label resolves via `displayName()` against the canonical artifact ID for the (phase, round) pair (the mapping is already implicit in `leftPaneTabsFor` at [4928](src/dual_research/ui/static/run-detail.jsx); this change is label-only).

**`CcxCard` per-attachment surfacing** ([2117+](src/dual_research/ui/static/run-detail.jsx)). The card already speaks canonical IDs via `hasNewVocabPieces` / `groupPiecesForPhase`. The only behavioural change is in the User-prompt group renderer:

- When `piecesRaw` contains any `user_prompt.attachment.<id>` keys, the User-prompt group renders a single "User prompt" row (showing the sum: `user_prompt.message` + all attachment tokens) with a small expand affordance (▸ chevron).
- On expand, the group reveals one sub-row per `user_prompt.attachment.<id>` plus the `user_prompt.message` row, each with its own bar segment using the existing `renderInputRow` shape.
- Visual style of the expanded sub-rows matches the existing per-row layout (no new tokens / no new CSS additions beyond a `.ccx-bar-row--sub` class for the indented sub-row).

**How-It-Works diagram update** (deferred follow-up — see §3 non-goals). If implementation has slack, the three `02-phase-inputs` references at [how-it-works.jsx:748, 770, 799](src/dual_research/ui/static/how-it-works.jsx) swap to `deep-research-pipeline`, and the cache-bust suffix at [519](src/dual_research/ui/static/how-it-works.jsx) bumps from `v=0133a` to `v=0145a`. Diagram regeneration itself is its own follow-up (spec 0148 candidate).

**Cache-bust**. Bump the static-asset query string in [`app.jsx`](src/dual_research/ui/static/app.jsx) to `?v=0145a`. Same convention as spec 0133, 0138.

---

## 6. Out of scope

Repeated from §3, with two clarifications surfaced after the deep-dive:

- **No consumption-card visual rework.** Spec **0146** owns the card geometry. This spec only adds the per-attachment data shape; 0146 decides whether the per-attachment rows render as nested sub-bars, indented inline rows, or a separate disclosure cluster.
- **No prompt-capture refactor.** Spec **0142** owns the upstream "what string was actually sent" record. The `Attachment.content` field this spec adds is the orchestrator-side view; if 0142's capture path diverges, this spec's emitter signature is the place to reconcile.
- **No phase-converged protocol contract rewrite.** Convergence / item-lifecycle / phase boundaries unchanged.
- **No backfill of historical events into `turn_prompt_pieces`.** Anchor run renders via the JSONB fallback through the shim.
- **No `system.preamble` / `system.task.closeout` wire-up.** Filed as a follow-up. The registry definitions stay; no emitter changes for those two IDs.
- **No diagram regeneration / How-It-Works rewire.** Deferred. Cache-bust still bumps because the JS bundle changes.
- **No CI diagram-parity test.** Lands with the diagram regeneration follow-up.
- **No removal of the legacy `user_prompt` ArtifactDef** ([artifacts.py:165-166](src/dual_research/contract/artifacts.py)) **or the legacy short-key shim**. Both stay for one release as the read-path for historical data.
- **No output-side per-piece token attribution.** Output tokens stay atomic per turn.

---

## 7. Test plan

### 7.1 — Schema migration

- [ ] **Apply migration 0006 on a fresh DB**, then on an existing DB; verify both succeed (idempotent guards in place).
- [ ] **Re-apply migration**: no errors, no row duplication (PK constraint).
- [ ] **Insert a sample row**: `(run_id='test', turn_key='phase0_a', artifact_id='user_prompt.attachment.abc', tokens=42, attachment_id='abc', display_title='Attachment · Foo.md')` — confirm round-trip via `SELECT *`.
- [ ] **Foreign-key cascade**: delete a row from `runs`, confirm the matching `turn_prompt_pieces` rows are cascaded.

### 7.2 — Piece-id assignment unit tests

- [ ] **`pieces_for_preflight` with zero attachments**: emitted dict carries `user_prompt.message` and no `user_prompt.attachment.*` keys.
- [ ] **`pieces_for_preflight` with two attachments**: emitted dict carries `user_prompt.message` + `user_prompt.attachment.a` + `user_prompt.attachment.b`.
- [ ] **No `user_prompt` aggregate key** in any phase's emitted dict (the registry's `display_name()` would still resolve it via the legacy ArtifactDef, but the producer never writes it).
- [ ] **Idempotency**: calling `pieces_for_preflight(..., attachments=[Attachment('a','A',content)])` twice yields equal dicts.
- [ ] **Stability of attachment ID ordering**: the order of `user_prompt.attachment.<id>` keys in the emitted dict matches the order of the `attachments` iterable. (Python 3.7+ dict insertion-order semantics carry this.)
- [ ] **`is_known()`** (or equivalent registry check) returns True for every key any `pieces_for_*()` can emit. CI gate: a new piece-id must be added to the registry first.

### 7.3 — Per-attachment token attribution

- [ ] **Empty-content text attachment**: contributes a `user_prompt.attachment.<id>` row with `tokens = 0`.
- [ ] **`estimate_tokens` round-off** on a small text payload: assert against the canonical formula `max(1, round(len/3.5))`.
- [ ] **Binary attachment with no content** (the placeholder case): row is still emitted with `tokens = 0`.
- [ ] **Sum invariant**: sum of all piece tokens via the new keys equals the same sum the legacy `user_prompt` aggregate would have produced (for the no-attachment case — guarantees no token-counting regression for the anchor run).

### 7.4 — Aggregator passthrough

- [ ] **Regression test** loading a fixture `turn_ended` event with the new canonical keys; assert `TurnTokenUsage.prompt_pieces` carries them verbatim, with no key normalisation.
- [ ] **Legacy-fixture regression**: loading the anchor run's `turn_ended` event payload (the live `prompt_pieces` dict quoted in §1.1) through the aggregator yields the same dict on `TurnTokenUsage.prompt_pieces` — no in-aggregator translation.

### 7.5 — Push-CLI integration

- [ ] **Push a run with a `turn_ended` event** carrying the new canonical keys; assert one `turn_prompt_pieces` row per artifact_id, with correct `tokens`, `attachment_id` (parsed for attachment rows), and `display_title` (resolved from contemporaneous `attachments.json`).
- [ ] **Re-push the same session-dir**: rows are replaced via upsert; row count unchanged.
- [ ] **Push a run with zero attachments** (anchor-run shape): no `user_prompt.attachment.*` rows; one `user_prompt.message` row.

### 7.6 — Frontend consumption-render snapshot

- [ ] **`CcxCard` snapshot** on a fixture turn with no attachments: identical to today's render (the "User prompt" row resolves to the same total).
- [ ] **`CcxCard` snapshot** on a fixture turn with two attachments: a new "User prompt" parent row + two expand-revealed sub-rows; total still sums to the billed input tokens.
- [ ] **`InputBriefModal` snapshot**: three sections (System / User / Derived) replace the four-tab structure (Content / Agent Input / Sources / Files).
- [ ] **`displayNameOf('user_prompt.attachment.foo', {foo: 'My document'})`** returns `Attachment · My document`. Fallback to literal ID when title-map is empty.
- [ ] **Legacy-key shim**: `canonicaliseLegacyKey('d1')` returns `'phase1.claude'`; `canonicaliseLegacyKey('unknown')` returns `'unknown'`.

### 7.7 — Anchor-run backfill smoke

- [ ] **Open the hosted run** `20260521-010637-dvs-backend-language-choice` against a UI build with this spec deployed. The Consumption tab shows the same per-phase totals as today (the legacy-key shim translates pre-spec data on the read path). No per-attachment rows (the run has zero attachments).
- [ ] **Open the run's `phase2-r1-claude` turn modal**: the input section reads the canonical labels ("Chat message" replaces "User prompt: Brief", "Claude's research plan" replaces "Claude's Phase 1 draft", etc.).
- [ ] **Cross-vocabulary parity**: the Consumption tab and the full-view modal use the **same** label for the same piece (no more "User prompt: Brief" in the modal vs "Chat message" in the card).

### 7.8 — Cross-language registry parity

- [ ] **Build-step test**: `contract/artifacts.py` emits `REGISTRY` to a JSON dump; `artifact-display.js`'s `TEMPLATES` array is the same content. CI fails on divergence.
- [ ] **Display-name parity**: for every registry ID, `display_name(id, title_for_id={...})` (Python) and `displayName(id, attachmentTitlesMap)` (JS) return byte-identical strings.

### 7.9 — Pytest + lint

- [ ] `uv run pytest tests/ -q` passes.
- [ ] No frontend type-checker configured; manual JSX import audit covers parity.

### 7.10 — Cache bust

- [ ] After deploy, hard-reload the run-detail page; confirm the new modal structure renders and the `?v=0145a` cache-bust took effect.

---

## 8. Risks

- **Schema-migration risk: the migration runs on a hot Supabase database.** `CREATE TABLE IF NOT EXISTS` is safe; `CREATE INDEX IF NOT EXISTS` is safe. The migration adds no NOT-NULL constraints on existing tables. **Mitigation:** the migration is purely additive; rollback is a single `DROP TABLE turn_prompt_pieces`. Test on the dev project first (`SUPABASE_URL` non-prod) before applying to prod.
- **Backfill volume.** Even without explicit backfill, the next push of a long-running session-dir (every existing run's next re-push) will populate the new table. The anchor run has 39 `calls` entries; at ~7 pieces per turn that's ~270 rows. Across the production run-set (low hundreds of runs as of 2026-05) the expected new-table size is sub-100k rows — negligible for Postgres. **Mitigation:** none needed.
- **ID stability across re-runs.** An attachment's `id` is generated at brief-ingest time ([cli.py:295-298](src/dual_research/cli.py); behind `materialise_local_markdown_attachments`). If the same brief is re-run with a different attachment-set, the same logical document may get a different ID. The `turn_prompt_pieces.attachment_id` column captures the ID at the moment of the turn — historically correct. **Mitigation:** none in this spec; attachment-ID stability is its own design question (filed for review in the same follow-up as `system.preamble`).
- **Cross-language registry drift.** Python `REGISTRY` and JS `TEMPLATES` can fall out of sync if a future spec adds a piece in Python without updating JS. **Mitigation:** CI parity test in §7.8; failing CI gates the merge.
- **Per-turn `inputs/<turnKey>.json` format change.** When `protocol/prompts.py::*_input_bundle()` switches to canonical IDs, the persisted JSON file's `pieces` dict keys change. Historical files (the anchor run has the legacy keys) are read via the shim. **Mitigation:** the shim's `# REMOVE AFTER 2026-08-01` comment makes the temporary nature explicit.
- **Aggregator key normalisation regressions.** Confirming no normalisation step exists today (verified — [aggregator.py:473-476](src/dual_research/ui/aggregator.py) only does `str(k) → int(v)` casts). Adding any future normalisation step would now silently break the canonical-ID contract. **Mitigation:** the aggregator-passthrough regression test in §7.4 is a guard; the inline comment in §5.3 documents the contract.
- **Consumption card width on per-attachment-rich runs.** A run with 10+ attachments could push the expanded per-attachment row count past the consumption card's vertical budget. **Mitigation:** the default-collapsed parent row keeps the card compact; expansion is an explicit affordance. 10+ attachments is rare in practice; if it becomes common, spec 0146 (consumption card rework) can introduce a "show first 5" pattern.
- **`display_title` staleness in `turn_prompt_pieces`.** The title is captured at push time. If a user renames an attachment in `attachments.json` between runs (extremely unlikely — the file is generated by the CLI from the brief), the cached title goes stale. **Mitigation:** the column is the rendering source-of-truth; runtime resolution uses the row's `display_title` rather than re-resolving against current `attachments.json`. By design.

---

## 9. Open questions

- **§5.2 push-CLI placement** — does the per-piece persistence land in the push CLI's existing `turn_ended` handler, or in a separate `_push_turn_prompt_pieces` helper called from the same handler? Recommend the helper for testability. Confirm at implementation.
- **§5.4 `InputBriefModal` tab consolidation** — the reverted 0139 spec proposed renaming `Content` → `User prompt` and folding Sources / Files into the three-section structure. Confirm before merging that the consolidation reads well on the existing single-attachment runs (anchor run carries zero, so the visual test needs a synthetic fixture or a freshly seeded run).
- **§5.4 `phaseOrderFor(phaseNum)`** — should the canonical-ID phase ordering live in JS (this spec) or be exported from Python alongside the registry (a `phase_arrival_order(phase)` function in `contract/artifacts.py`)? The latter is cleaner architecturally but adds a Python-side surface for a UI-only concern. Recommend JS-side for now; promote to shared if the diagram regeneration follow-up needs the same ordering.
- **§5.4 read-shim deletion deadline** — `# REMOVE AFTER 2026-08-01` is a guess. Tie the actual removal to the lifecycle of the oldest "live" historical run we care about rendering; the anchor run's date is 2026-05-21, so 2.5 months of overlap should be sufficient. Confirm or set a different deadline at implementation.
