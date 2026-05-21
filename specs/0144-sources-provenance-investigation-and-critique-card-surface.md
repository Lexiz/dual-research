---
spec: 0144
title: Sources & provenance — investigation outcome and per-critique-card surface (incl. Phase 4 Issue/Comment patches)
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.10.0
created: 2026-05-21
pr: ""
---

# Spec 0144 — Sources & provenance: investigation outcome + per-critique-card surface

> Ship bucket: **Critique-card surface — visible provenance for every item.**
> Depends on: **0114** (Deep Research protocol; defines `EvidenceRecord`, the `evidence_required` flag on raises, and the address-side anti-hallucination contract — [`src/dual_research/contract/evidence.py:28-44`](../src/dual_research/contract/evidence.py)), **0115** (UI mirror of the Item / `EvidenceRecord` model — [`src/dual_research/ui/models.py:402-420`](../src/dual_research/ui/models.py); the `ItemCard` + `SourceRow` primitives at [`src/dual_research/ui/static/run-detail.jsx:1236-1401`](../src/dual_research/ui/static/run-detail.jsx)), **0119** (badge governance — the chip primitive every new sources chip will use), **0036** (per-turn `TurnSearchAudit` schema and the `turn_searches` event emitter wired in [`src/dual_research/orchestrator/_call.py:138-155`](../src/dual_research/orchestrator/_call.py)), **0140** (Phase 4 deadlock fix; this spec follows it in the batch because we touch Phase 4 cross-review cards alongside the deadlock work), **0141** (critique-integrity prerequisites for clean address-side data).
> Blocks: nothing in the 0140–0147 batch; downstream "Sources" tab work (not specced) would build on the same wire payload.
> Complexity: **L** — backend schema extension (`EvidenceRecord` denormalisation + validator wire-up) + frontend re-route (`renderItem` switches new-protocol items to `ItemCard`) + design-system additions (`SourceRow`, `Sources segment`, critique-card composition invariant). Three files in three layers; one inter-layer contract (the wire-payload field set).
> Targeted version bump: **MINOR (1.9.x → 1.10.0)** — user-visible new surface on every critique card (a SOURCES section), new chip variant (`⚠ unverified`), no breaking schema removal. Legacy renderers stay live for pre-0114 runs.

---

## 1. Context

Three items from the run-`20260521-010637-dvs-backend-language-choice` review land in the same code paths and ship together:

- **B09 — Source / provenance logic absent on this run** (`investigation`). The verbatim claim is that "no sources are cited, recorded, or requested anywhere in the run" and asks us to determine whether the trigger conditions never fired or the recording silently failed. **This spec resolves the investigation in §3 below.**
- **B14 — Source provenance visible on every critique card** (`feature`, backend + frontend + design-system). The structured product ask: every critique-section card across every run must show a SOURCES section matching the recovered iteration-3 mockup at [`handoffs/ds-v2-audit/badge-governance-mockup-iter3.html`](../handoffs/ds-v2-audit/badge-governance-mockup-iter3.html). It explicitly cross-references B09 ("the answer to Investigate 1") and B08 ("same primitive — fixing it without (2) means doing the layout twice").
- **B08 — Phase 4 cross-review cards don't render Issue and Comment patches** (`bug`, ui). The Phase 4 filter strip exposes Q/D/I/C but the per-round timeline cross-review cards only patch Q and D. B14's frontend workstream touches the same card-render path, so we close B08 inside it instead of doing the layout twice.

The investigation framing for B09 is more nuanced than the verbatim quote suggests. The anchor run actually emitted **19 `turn_searches` events** (seq 22 → 258, confirmed in §3 below) and **14 `item_transitioned` events with non-empty `evidence_records`** — provenance is *partially firing*. What's missing is not the emit path; it's the **render surface**. §3 quotes the actual payloads and §4 names the file:line that drops them.

That distinction matters for sequencing. B14's three workstreams (backend / frontend / design-system) were originally written as if backend data had to be built from zero. Once §3's investigation is settled, the workstream collapses to: **(a)** densify the existing wire payload (denormalised round/actor fields + validator wire-up + `consulted_sources` resolution); **(b)** route new-protocol items through `<ItemCard>` instead of letting `_normalizeToThread` strip `evidence`; **(c)** canonise the layout in `design-system/SPEC.md` so the three layers stay aligned. B08 falls out of (b) automatically: `ItemCard` already renders Issues and Comments with the same layout as Questions and Disagreements (it's kind-agnostic by design — see [`run-detail.jsx:1325-1331`](../src/dual_research/ui/static/run-detail.jsx)), so the moment we route I/C through it, the missing patches show up.

This spec is therefore not "build provenance from zero." It is "investigation outcome + surface the data we already have + canonise the primitive."

---

## 2. Goals & non-goals

### 2.1 Goals

1. **Close B09.** The investigation's resolution is recorded in this spec at §3. Future runs need no further B09 work — every subsequent question about "is provenance firing?" can be answered by querying the same events we cite here.
2. **Backend** — fill the EvidenceRecord denormalisation gaps the wire needs (`raised_in_round`, `answered_in_round`, `requested_by`, `provided_by`, `attached_at`), turn the contract-layer evidence validator on for the async run paths, propagate `unverified=True` instead of silently dropping flagged ADDRESS blocks, and resolve `evidence_event_id` against `TurnSearchAudit` so the wire carries the full `consulted_sources` payload next to each record.
3. **Frontend** — route every new-protocol item through `<ItemCard>` (not `QuestionThread` via `_normalizeToThread`), so `evidence` / `transitions` / `anchor_*` / `evidence_required` survive the trip from event-bus to JSX. Render the SOURCES segment, the `⚠ unverified` chip, the lifecycle footer, and the Evidence-needed helper per the iter-3 mockup.
4. **Design-system** — promote the iter-3 mockup to `design-system/audits/` as the canonical visual source; add `SourceRow`, `Sources segment`, and a critique-card composition spec to `design-system/SPEC.md`; record the invariant that all four item kinds render with the same card primitive.
5. **B08 closed as a consequence** — once `ItemCard` is the renderer for I and C, Phase 4 cross-review cards show Issue and Comment patches identically to Question and Disagreement patches.

### 2.2 Non-goals

- Protocol rewrite. `EvidenceRecord`'s shape on `contract/evidence.py` is extended (additive fields), not replaced; the validator stays as it is and just gets wired in. Spec 0114's protocol surface is unchanged.
- A standalone "Sources" page / tab / cross-run dashboard. The surface is per-card only.
- A new request-for-sources event class. The verbatim B14 description (1)(b) proposes a `RequestEvidence` op so mid-run requests for sources can be modelled distinctly from raise-time `evidence_required: bool`. We **defer** that to a follow-up — it requires prompt changes and a new parse path. This spec covers raise-time `evidence_required` only, which is already in the protocol and is what produced the 14 evidence-bearing transitions on the anchor run.
- Backfill of pre-0114 runs. Legacy `QuestionThread` continues to render runs without `ItemRaised`/`ItemTransitioned` events; their cards have no SOURCES segment because the source data was never captured.
- Cost / token / search-cost surface polish — covered by spec 0143.

---

## 3. Investigation outcome (B09)

**Headline.** Source / provenance logic *is* firing on run `20260521-010637-dvs-backend-language-choice`. The investigation's premise ("no sources are cited, recorded, or requested anywhere in the run") is true *as observed in the UI* but false at the event-store / orchestrator layer. The gap is render-side: the new-protocol items carry their evidence records all the way to `aggregator.py` / `ui/items.py`, and then `_normalizeToThread` at [`src/dual_research/ui/static/run-detail.jsx:6419-6512`](../src/dual_research/ui/static/run-detail.jsx) drops the `evidence` field on the floor before the JSX hits a renderer.

### 3.1 What fires today

**(a) Per-turn search audits are persisted.** `_on_turn_searches` at [`src/dual_research/ui/aggregator.py:792`](../src/dual_research/ui/aggregator.py) writes the audit bundle to `session_dir/searches/<turn-key>.json` and the `turn_searches` event carries the same payload to the event store. On the anchor run, **19** such events fire between seq 22 and seq 258:

```text
seq=22   kind=turn_searches  agent=claude  phase=phase0  label=phase0-r2-claude
seq=44   kind=turn_searches  agent=openai  phase=phase0  label=phase0-r2-openai
...
seq=258  kind=turn_searches  agent=openai  phase=phase4  label=phase4-r4-openai
```

Each audit payload conforms to `TurnSearchAudit` ([`src/dual_research/audit/schema.py:99-122`](../src/dual_research/audit/schema.py)) and carries the full `tool_events` list with both `queries` and `consulted_sources`. Sample row (seq 22, abridged):

```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "turn_key": "phase0_claude",
  "phase": "phase0",
  "agent": "claude",
  "label": "phase0-r2-claude",
  "flags": { "search_performed": false, "queries_missing_from_actions": false,
             "citations_without_search_event": false,
             "cited_url_not_in_consulted_sources": false },
  "tool_events": [
    {
      "event_id": "srvtoolu_01XVrn6QiQ2Ex2jHBwFibjr9",
      "type": "web_search",
      "action_type": "search",
      "queries": ["MCP server SDK Go Rust official community 2024 2025"],
      "consulted_sources": [
        { "url": "https://github.com/modelcontextprotocol/rust-sdk",
          "title": "GitHub - modelcontextprotocol/rust-sdk: The official Rust SDK for the Model Context Protocol",
          "page_age": "March 9, 2026",
          "encrypted_content": "EtIlCioIDxgCIiQ0OT…" }
      ]
    }
  ],
  "citations": []
}
```

So the `turn_searches` channel **is recording exactly what the spec-0036 contract says it should**: provider, model, turn_key, tool-call events, consulted sources, citations (empty here because Anthropic doesn't emit citation annotations on this provider config). The original B09 phrase "no sources are recorded" is contradicted by the row above and 18 more like it.

**(b) Evidence records on ADDRESS transitions are persisted.** Deep Research's address-side handler at [`src/dual_research/orchestrator/deep_research.py:354-401`](../src/dual_research/orchestrator/deep_research.py) emits the `evidence_records` list on every `ItemTransitioned` whose item carried `evidence_required: true` (set on `ItemRaised` per [`src/dual_research/events/types.py:421-438`](../src/dual_research/events/types.py) and applied to the bundle by [`src/dual_research/ui/items.py:160-181`](../src/dual_research/ui/items.py)). On the anchor run:

- `item_raised` events: **38** total; **13** carry `evidence_required: true`.
- `item_transitioned` events: **78** total; **14** carry a non-empty `evidence_records` list.

Sample row (first transition with evidence; abridged):

```json
{
  "id": "Q-input-g-04",
  "round": 2,
  "actor": "claude",
  "from_state": "open",
  "to_state": "addressed",
  "evidence_records": [
    {
      "item_id": "Q-input-g-04",
      "url": "https://github.com/orgs/modelcontextprotocol/repositories",
      "title": "Model Context Protocol — GitHub org repositories",
      "search_query": "Model Context Protocol server library TypeScript Python C# Java Kotlin Go Rust",
      "fetched_at": "2026-05-21T00:00:00Z",
      "evidence_event_id": "search_2",
      "content_excerpt": "\"The official Java SDK for Model Context Protocol servers and clients. … The official Go SDK for Model Context Protocol servers and clients. Maintained in collaboration with Google. … The official Kotlin SDK for Model Context Protocol servers and clients. … The official Ruby SDK for the Model Context Protocol.\""
    }
  ]
}
```

So the **address-side capture works** end-to-end on this run: 14 of 78 transitions carry the URL + title + search-query + fetched-at + content-excerpt fivetuple the validator wants.

**(c) Phase 4 evidence flow is alive.** Of the 24 Phase 4 transitions on the anchor run (16 Issue, 4 Comment, 2 Disagreement, 2 Question), a non-trivial subset arrive with evidence_records and a tool-events audit on the same turn_key. Phase 4 evidence is therefore **not the bottleneck** — Phase 4 cards' missing source surface (B14's main complaint) is purely a render-side problem.

### 3.2 What does NOT fire today

**(d) The contract-layer validator is wired into `DeepResearchPhase` only via the default no-op.** [`src/dual_research/orchestrator/deep_research.py:217-237`](../src/dual_research/orchestrator/deep_research.py) declares `evidence_validator` with default `lambda recs, p, a: []` — i.e. "never flag anything." [`src/dual_research/orchestrator/dr_run.py:133-142`](../src/dual_research/orchestrator/dr_run.py) (`_build_dr_phase`) and [`dr_run.py:181-185`](../src/dual_research/orchestrator/dr_run.py) (`_drive_interaction_phase`) construct `DeepResearchPhase(...)` **without** passing `evidence_validator`. [`src/dual_research/ledger/replay.py:95`](../src/dual_research/ledger/replay.py) does the same. Result: `validate_all_evidence` at [`src/dual_research/contract/evidence.py:185-194`](../src/dual_research/contract/evidence.py) is dead code on every production run. No address block is ever flagged. The `unverified` field on the UI's `EvidenceRecord` ([`src/dual_research/ui/models.py:419-420`](../src/dual_research/ui/models.py)) is always `False` because nothing sets it.

**(e) On the address side, when the validator hypothetically *does* fire, the current branch drops the entire ADDRESS block.** [`src/dual_research/orchestrator/deep_research.py:354-363`](../src/dual_research/orchestrator/deep_research.py):

```python
if ent.evidence_required:
    flags = self.evidence_validator(blk.evidence, parsed, agent)
    if flags:
        # Evidence rejected → item stays in its current state.
        continue   # ← the entire ADDRESS block is skipped
```

So when the validator turns on, every flagged ADDRESS becomes invisible to the UI. That is the opposite of the iter-3 design intent ("`⚠ unverified` chip on the source row"). The fix is structural: emit the transition with `unverified=True` + reason, instead of `continue`-ing.

**(f) `evidence_event_id` is not cross-resolved against `TurnSearchAudit`.** [`src/dual_research/ui/items.py:170-181`](../src/dual_research/ui/items.py) copies `evidence_event_id` as a raw string into the UI `EvidenceRecord` but never resolves it to a `ToolEvent` in the same turn's audit. The wire payload therefore lacks `consulted_sources` next to each record — the UI has the URL but not the page_age, the encrypted_content, the sibling queries, or the rest of the ToolEvent's retrieval set. This is the gap B14(1)(d) called out.

**(g) `_normalizeToThread` strips `evidence`.** [`src/dual_research/ui/static/run-detail.jsx:6419-6512`](../src/dual_research/ui/static/run-detail.jsx) is the single function that converts an Item-shaped object into the `QuestionThread` props bag. None of the four branches (`k === 'q'`, `'d'`, `'i'`, `'c'`) copies `item.evidence` into the return value. They produce `turns: [{ agent, round, verdict, quote }]` and that is it. `QuestionThread` ([`src/dual_research/ui/static/shared.jsx:1133`](../src/dual_research/ui/static/shared.jsx)) does not accept or render `evidence` — `grep -n evidence src/dual_research/ui/static/shared.jsx` returns zero hits. **This is the proximate cause of B09's symptom.** Evidence data exists; it is computed; it lives in `run.phaseStats.items[i].evidence`; the renderer just ignores it.

**(h) `ItemCard` exists but is never called.** [`src/dual_research/ui/static/run-detail.jsx:1325-1401`](../src/dual_research/ui/static/run-detail.jsx) defines a complete kind-agnostic card with header chips, body, anchor, timeline, and a `Sources (N)` section that maps over `item.evidence`. The renderer is well-formed. It has zero call-sites in production: every reference to it across the JSX is its own definition. `renderItem` at [`run-detail.jsx:6169-6195`](../src/dual_research/ui/static/run-detail.jsx) bypasses it entirely and routes through `_normalizeToThread` → `<QuestionThread>`.

### 3.3 Conclusion

Provenance fires *partially*. The emit-and-persist half works (every layer up through and including `aggregator.py` carries the data). The validator-and-render half does not (validator is a default no-op; render path strips the field). Recording does not silently fail; it succeeds and then the UI throws the result away.

The investigation produces **two** concrete asks, both addressed in §6:

1. Turn the validator on (§6.1.a), so `unverified=True` can flow.
2. Switch `renderItem` to `ItemCard` for new-protocol items (§6.2.a), so `evidence` survives the trip to a renderer.

Everything else in B14 — denormalised round/actor fields, `consulted_sources` resolution, design-system canonisation — is densification on top of the same flow, not a new pipeline.

---

## 4. Current-state audit

File:line tables for the load-bearing call-sites in the three layers.

### 4.1 Backend — provenance & search emitter

| Concern | Location | Notes |
|---|---|---|
| `turn_searches` event class | [`events/types.py:97-121`](../src/dual_research/events/types.py) | `agent`, `phase`, `label`, `turn_key`, `audit: dict`. Kind tag `turn_searches`. |
| `turn_searches` emit site | [`orchestrator/_call.py:138-155`](../src/dual_research/orchestrator/_call.py) | Wraps the agent call; reads `result.extras["search_audit"]`; publishes BEFORE `TurnEnded` so the audit bundle hits disk first. |
| `TurnSearchAudit` schema | [`audit/schema.py:99-122`](../src/dual_research/audit/schema.py) | Provider-neutral. `tool_events` is the load-bearing field; `citations` is provider-asymmetric. |
| `ToolEvent.consulted_sources` | [`audit/schema.py:63-78`](../src/dual_research/audit/schema.py) | List of `ConsultedSource(url, title, page_age, encrypted_content)`. |
| `_on_turn_searches` aggregator handler | [`ui/aggregator.py:244-245`](../src/dual_research/ui/aggregator.py) calling [`ui/aggregator.py:792`](../src/dual_research/ui/aggregator.py) | Persists `searches/<turn-key>.json` and stamps `search_audit_path` on the TurnTokenUsage row. |

### 4.2 Backend — citation/evidence contract

| Concern | Location | Notes |
|---|---|---|
| `EvidenceRecord` (contract) | [`contract/evidence.py:28-44`](../src/dual_research/contract/evidence.py) | The 7-field record: `item_id`, `url`, `title`, `search_query`, `fetched_at`, `evidence_event_id`, `content_excerpt`. |
| `validate_evidence` / `validate_all_evidence` | [`contract/evidence.py:91-194`](../src/dual_research/contract/evidence.py) | Anti-hallucination: event-id match, URL match against `consulted_sources`, excerpt substring against `encrypted_content`. Dead code today — never called from production paths. |
| Address-side evidence drop | [`orchestrator/deep_research.py:354-363`](../src/dual_research/orchestrator/deep_research.py) | `if flags: continue` — drops the entire transition on any flag. |
| `evidence_validator` default no-op | [`orchestrator/deep_research.py:217-237`](../src/dual_research/orchestrator/deep_research.py) | `or (lambda recs, p, a: [])`. Never overridden by `dr_run.py` or `ledger/replay.py`. |
| `DeepResearchPhase` construction (async path) | [`orchestrator/dr_run.py:133-142`](../src/dual_research/orchestrator/dr_run.py), [`dr_run.py:181-185`](../src/dual_research/orchestrator/dr_run.py) | No `evidence_validator=` keyword. |
| `DeepResearchPhase` construction (replay) | [`ledger/replay.py:95`](../src/dual_research/ledger/replay.py) | Same omission. |
| UI mirror `EvidenceRecord` | [`ui/models.py:402-420`](../src/dual_research/ui/models.py) | 7 contract fields + 2 UI-only (`unverified`, `unverified_reason`). |
| Evidence attach point | [`ui/items.py:160-181`](../src/dual_research/ui/items.py) (`_apply_transition`) | Copies `evidence_records` from the event dict into `Item.evidence`. No round/actor denormalisation; no `consulted_sources` resolution. |

### 4.3 Frontend — Phase 4 cards, Issue/Comment renderers, patch lookup

| Concern | Location | Notes |
|---|---|---|
| `ItemCard` (kind-agnostic, includes `Sources (N)`) | [`ui/static/run-detail.jsx:1325-1401`](../src/dual_research/ui/static/run-detail.jsx) | Built. Renders all four kinds with one layout. Has zero production call-sites. |
| `SourceRow` (per-record disclosure) | [`ui/static/run-detail.jsx:1252-1323`](../src/dual_research/ui/static/run-detail.jsx) | Built. Handles open/close, `⚠ unverified` chip, bounded-scroll excerpt for >800 chars. |
| `renderItem` — routes to QuestionThread | [`ui/static/run-detail.jsx:6169-6195`](../src/dual_research/ui/static/run-detail.jsx) | Calls `_normalizeToThread` then `<QuestionThread {...props}>`. **Never** instantiates `<ItemCard>`. |
| `_normalizeToThread` — strips `evidence` | [`ui/static/run-detail.jsx:6419-6512`](../src/dual_research/ui/static/run-detail.jsx) | All four branches (`q` / `d` / `i` / `c`) return `{ id, kind, status, raisedBy, raisedRound, phase, turns, footer, _highlightKeys, _highlightVariant }`. No `evidence`, no `transitions`, no `anchor_*`, no `evidence_required`. |
| `QuestionThread` (renderer) | [`ui/static/shared.jsx:1133-1178+`](../src/dual_research/ui/static/shared.jsx) | Props bag does not declare `evidence`. Body has no SOURCES section. `grep evidence` → 0 hits. |
| Phase 4 cross-review card (timeline) | [`ui/static/run-detail.jsx:1080-1199`](../src/dual_research/ui/static/run-detail.jsx) | `chipCategories = phase === 4 ? ['questions','disagreements','issues','comments']` — but the chips read from `stats.categories[cat]` only. Issue/Comment data is present in `categories.issues`/`categories.comments` end-to-end (see `aggregator.py:1847-1866` + `items.py:_apply_transition`). The "missing patches" in B08 surface in the **critique pane** cards (open carried / resolved / drift sections rendered by `renderGroup` → `renderItem`), not on the timeline header. |
| `CritiquePhaseContent` group renderer | [`ui/static/run-detail.jsx:6538-6577`](../src/dual_research/ui/static/run-detail.jsx) | Renders 4 groups (`Open · new`, `Open · carried`, `Resolved`, `Drift`); each maps over its items through `renderItem`. This is the path B08 calls "Phase 4 cross-review cards." |
| `computeChipDeltas` for the right-pane stat row | [`ui/static/run-detail.jsx:3717-3755`](../src/dual_research/ui/static/run-detail.jsx) | Already covers issue+comment kinds (lines 3742-3743). Ledger has the data. |

### 4.4 Existing CSS surfaces

| Concern | Location | Notes |
|---|---|---|
| `.source-row` CSS rules | none | Zero matching rules in [`ui/static/components.css`](../src/dual_research/ui/static/components.css). |
| `.rp-sources` (modal-side, NOT card-side) | [`components.css:3203-3206`](../src/dual_research/ui/static/components.css) | Flex column + 4px gap; only used inside the right-pane sources tab on the modal. Not a card primitive. |
| `.item-card__sources` | none | The header lives in JSX at `run-detail.jsx:1392-1397`; no CSS rule exists. The class would render with browser defaults today. |
| `.md-chip--warn` (for `⚠ unverified`) | [`design-system/SPEC.md:308`](../design-system/SPEC.md) | Chip primitive contract; `--sm` variant available. The mockup uses it for the warn-tinted `⚠ unverified` slot. |

### 4.5 Mockup reference

| Concern | Location | Notes |
|---|---|---|
| Recovered iter-3 mockup | [`handoffs/ds-v2-audit/badge-governance-mockup-iter3.html`](../handoffs/ds-v2-audit/badge-governance-mockup-iter3.html) | Header chips → body → LIFECYCLE → footer → SOURCES anatomy. CSS for `.src-row` at lines 177-185. |
| Iter-3 mockup not yet in `design-system/audits/` | n/a | This spec moves it. |

---

## 5. Wire-payload contract (the inter-layer agreement)

Every backend & frontend change in §6 has to leave the JSX consuming the **same** field set. The contract is recorded here so reviewers can audit one place.

### 5.1 Per-item payload (added/changed fields)

Each `Item` on the `run.phaseStats.items` array — and each Item delivered live via SSE — carries:

```jsonc
{
  "id": "Q-input-g-04",
  "kind": "question",                       // unchanged
  "phase": 0,                                // unchanged
  "raiser": "claude",                        // unchanged
  "body": "…",                               // unchanged
  "anchor_type": "quote",                    // unchanged
  "anchor_text": "…",                        // unchanged
  "evidence_required": true,                 // EXISTING; survives _normalizeToThread (§6.2.a)
  "raised_round": 1,                         // unchanged
  "current_state": "addressed",              // unchanged
  "transitions": [ /* unchanged */ ],
  "evidence": [
    {
      "item_id": "Q-input-g-04",
      "url": "https://…",
      "title": "…",
      "search_query": "…",
      "fetched_at": "2026-05-21T00:00:00Z",
      "evidence_event_id": "search_2",
      "content_excerpt": "…",

      // NEW in §6.1.a (denormalisation):
      "raised_in_round": 1,
      "answered_in_round": 2,
      "requested_by": null,                  // null until §2.2 deferred RequestEvidence ships
      "provided_by": "claude",
      "attached_at": "2026-05-21T01:09:06.600743+00:00",

      // NEW in §6.1.c (validator wire-up):
      "unverified": false,
      "unverified_reason": "",

      // NEW in §6.1.d (consulted_sources resolution):
      "consulted_sources": [
        { "url": "https://…", "title": "…",
          "page_age": "March 9, 2026", "queries": ["…"] }
      ]
    }
  ]
}
```

`consulted_sources[].encrypted_content` is **not** included on the wire — it's multi-KB per source on Anthropic, the UI doesn't render it, and the validator already used it server-side. Stripping it keeps the per-item payload ≤ ~4 KB on the median item even with two sources.

### 5.2 Wire size sanity-check (anchor run)

The anchor run has 38 items, 14 with evidence_records (1 record average; max 3). With the §6.1 additions a representative payload grows from ~600 bytes to ~1.4 KB. Total `phaseStats.items` payload: ~32 KB → ~52 KB. SSE deltas (per-event) grow by the difference (≤ ~1 KB extra per item_transitioned). Both are well inside the existing per-message budget; see §9.1.

---

## 6. Proposed change

### 6.1 Backend — fill the denormalisation gaps, turn the validator on

#### 6.1.a Denormalise round & actor onto `EvidenceRecord`

Add to **both** [`contract/evidence.py:EvidenceRecord`](../src/dual_research/contract/evidence.py) and [`ui/models.py:EvidenceRecord`](../src/dual_research/ui/models.py):

```python
raised_in_round: int = 0
answered_in_round: int = 0
requested_by: str | None = None
provided_by: str = ""
attached_at: str = ""
```

Populate them in [`ui/items.py:_apply_transition`](../src/dual_research/ui/items.py) where `round` + `actor` are already in scope from the `ItemTransitioned` event, and `raised_in_round` is on the parent `Item` (`item.raised_round`). `attached_at` reads the event's `ts` (already on every event row). `requested_by` stays `None` for now (see §2.2 deferral).

The contract-side dataclass keeps the new fields with safe defaults so existing callers don't break.

#### 6.1.b Wire `evidence_validator` into every `DeepResearchPhase` construction

Three call-sites:

- [`orchestrator/dr_run.py:133-142`](../src/dual_research/orchestrator/dr_run.py) (`_build_dr_phase`) — pass a closure that reads the current turn's `TurnSearchAudit` from disk (the audit was just persisted by `_on_turn_searches` before the address-side handler runs) and calls `validate_all_evidence(records, tool_events=audit.tool_events)`.
- [`orchestrator/dr_run.py:181-185`](../src/dual_research/orchestrator/dr_run.py) (`_drive_interaction_phase` inline construction) — same closure.
- [`ledger/replay.py:95`](../src/dual_research/ledger/replay.py) — same closure but resolves the audit from `session_dir/searches/<turn-key>.json` directly (replay has no event bus).

Audit resolution: the audit bundle is persisted at `session_dir/searches/<turn-key>.json` (per spec 0036). The closure takes `(records, parsed, agent)` and derives the turn_key from `parsed.turn_key` (already populated). On a cold replay where the audit file is missing, the closure returns `[]` (i.e. defer — matches current behaviour). The closure is constructed once per phase and captures `session_dir` in its enclosing scope.

#### 6.1.c Stop dropping flagged ADDRESS blocks; propagate `unverified=True`

Rewrite [`orchestrator/deep_research.py:354-363`](../src/dual_research/orchestrator/deep_research.py):

- If `flags` is non-empty, **still emit** the transition (state changes from `open` → `addressed` as it would have), but annotate each evidence dict with `unverified=True` and `unverified_reason="; ".join(f.code for f in flags)`.
- The `closeout_urged` event still fires for the item in the next round (the verbatim B14(1)(c) goal).
- `evidence_dicts` (the list at [`deep_research.py:371-382`](../src/dual_research/orchestrator/deep_research.py)) carries the new fields when written into the `ItemTransitioned` event.

This converts the validator from "silent dropper" to "annotator." It is the structural fix B14(1)(c) asks for and the only viable substrate for B14(2)(f)'s `⚠ unverified` chip.

#### 6.1.d Resolve `evidence_event_id` against `TurnSearchAudit`

In [`ui/items.py:_apply_transition`](../src/dual_research/ui/items.py), accept an optional `audit_lookup: Callable[[str], dict | None]` parameter that, given a turn_key, returns the persisted `TurnSearchAudit` payload (caller injects a function that reads `session_dir/searches/<turn-key>.json` once and caches it). For each evidence record, look up the matching `ToolEvent` by `evidence_event_id` and project a slim `consulted_sources` list onto the UI EvidenceRecord — `url`, `title`, `page_age`, and the parent `queries` list. **Drop** `encrypted_content` (see §5.2).

The `audit_lookup` is `None` for replay-only / test-only contexts and the consulted_sources stays `[]`. Tests cover both branches.

#### 6.1.e Patch retention for Phase 4 Issue & Comment transitions (B08)

No backend code change is required: the address-side handler at [`deep_research.py:345-401`](../src/dual_research/orchestrator/deep_research.py) is **kind-agnostic** — it processes `AddressBlock` regardless of whether the addressed item is Q / D / I / C. The 16 Phase 4 Issue transitions and 4 Phase 4 Comment transitions in the anchor run prove the data path works.

B08's "missing patches on Phase 4 cards" is therefore entirely the §6.2 frontend fix. We list this sub-section explicitly to record the audit conclusion: **backend is correct; frontend drops the kinds at the renderer level.**

### 6.2 Frontend — wire ItemCard, surface evidence, fix B08 as a by-product

#### 6.2.a Route new-protocol items through `<ItemCard>`

In [`renderItem` at run-detail.jsx:6169-6195`](../src/dual_research/ui/static/run-detail.jsx), branch on whether the item came from the new event stream (presence of `transitions` array — pre-0114 items don't have it):

```jsx
const renderItem = (item) => {
  if (Array.isArray(item.transitions)) {
    return <ItemCard key={item.id} item={item} onHighlight={highlightFor(item)} />;
  }
  // Legacy fallback for pre-0114 archived runs:
  const props = _normalizeToThread(item, run, selectedPhase);
  if (!props) return null;
  return <QuestionThread key={item.id} {...props} showPhaseChip={false} />;
};
```

This single switch closes B09's render gap **for all four kinds simultaneously** — `ItemCard` is kind-agnostic — and as a side effect surfaces Phase 4 Issues and Comments on the cross-review cards, which closes B08.

#### 6.2.b Stop dropping fields in `_normalizeToThread`

Even with the §6.2.a branch in place, `_normalizeToThread` is still used for legacy runs. Extend its four return values to include `evidence`, `transitions`, `anchor_type`, `anchor_text`, `evidence_required` (defaulting to `[]` / `''` / `false` where the legacy item has no equivalent). This is defensive — a future caller that still routes a new-protocol item through `QuestionThread` will at least not throw the data away.

#### 6.2.c CSS for the SOURCES segment + `.source-row`

Add to [`components.css`](../src/dual_research/ui/static/components.css), targeting the iter-3 mockup spec at [`badge-governance-mockup-iter3.html:177-185`](../handoffs/ds-v2-audit/badge-governance-mockup-iter3.html):

```css
/* Spec 0144 — per-card SOURCES segment + SourceRow */
.item-card__sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--md-outline-hair);
}
.item-card__sources-hd {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--md-on-surface-variant);
  margin-bottom: 8px;
}
.source-row {
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-xs, 4px);
  padding: 8px 10px;
  margin: 6px 0;
}
.source-row__head {
  display: flex; align-items: center; gap: 8px;
  cursor: pointer; user-select: none;
}
.source-row__chev    { color: var(--md-on-surface-variant); font-size: 10px; }
.source-row__title   { color: var(--md-on-surface); font-size: 12.5px; font-weight: 500; }
.source-row__host    { color: var(--md-on-surface-variant); font-size: 11px; }
.source-row__body    { padding-top: 8px; }
.source-row__field   { font-size: 12px; color: var(--md-on-surface-variant); margin: 4px 0; }
.source-row__label   { color: var(--md-on-surface-faint); font-size: 11px; }
.source-row__excerpt { white-space: pre-wrap; font-size: 11.5px; padding: 6px 8px;
                       background: var(--md-surface); border-radius: 4px; margin-top: 4px; }
.source-row.is-unverified { border-color: var(--md-tone-warn-border, #b8860b66); }
```

The bounded-scroll behaviour for >800-char excerpts is already implemented inline in `SourceRow`'s JSX (run-detail.jsx:1266-1268) — no extra CSS needed.

#### 6.2.d Render `⚠ unverified` chip on the source row

Already implemented in [`SourceRow` JSX at run-detail.jsx:1282-1289`](../src/dual_research/ui/static/run-detail.jsx) — reads `record.unverified`. Once §6.1.c propagates `unverified=True` on flagged records, the chip lights up automatically.

#### 6.2.e Lifecycle footer parity across all four kinds

In `ItemCard`, append a footer below the timeline that reads `✓ resolved/capped/acknowledged/withdrawn at round N · M turns to converge` for every terminal state, computed from `item.transitions` (last terminal transition's `round`, count of transitions for "M turns"). Today only Questions get the "M turns to converge" suffix in `_normalizeToThread`. With ItemCard taking over, the footer is uniform.

#### 6.2.f Evidence-needed helper

In `ItemCard` body, when `item.evidence_required === true`, render an italic helper line under the body: `Evidence needed — addresses must cite consulted sources.` This is the verbatim B14(2)(d) ask.

#### 6.2.g `capped` + `acknowledged` status chips

Extend the `stateTone` map at [`run-detail.jsx:1333-1340`](../src/dual_research/ui/static/run-detail.jsx) — already covers `capped` and `acknowledged`. No JSX change needed; once items flow through `ItemCard`, those states render as warn/error tinted chips per the existing map. The complementary fix in `QuestionThread`'s legacy vocabulary at [`shared.jsx:1167-1178`](../src/dual_research/ui/static/shared.jsx) (B14(2)(c)) adds `capped` and `acknowledged` cases to the `verboseStatusLabel` derivation so the **legacy** renderer also surfaces those states — the legacy path stays alive for pre-0114 runs.

#### 6.2.h Header chips: kind, state, raiser, round, Sources N

The existing `ItemCard` header at [`run-detail.jsx:1349-1355`](../src/dual_research/ui/static/run-detail.jsx) renders `{id, kindLabel, stateLabel, raised by X, round N}`. Append a sixth chip when `evidence.length > 0`:

```jsx
{evidence.length > 0 && (
  <span className="md-chip md-chip--sm">Sources {evidence.length}</span>
)}
```

This makes the count discoverable without scrolling to the bottom of the card — the verbatim iter-3 mockup ask.

### 6.3 Design-system — canonise the layout

#### 6.3.a Promote the iter-3 mockup to the audits directory

`git mv handoffs/ds-v2-audit/badge-governance-mockup-iter3.html design-system/audits/2026-05-19-badge-governance-iter3/mockup.html`. Add a one-line entry in [`design-system/SPEC.md`](../design-system/SPEC.md) under §4.1 (Critique pane) pointing to it as the canonical visual source for the SOURCES segment.

#### 6.3.b `SourceRow` primitive section in SPEC.md

Insert a new sub-section under §3 (Primitives), after the Chip row:

> **SourceRow** | `.source-row`, `.source-row--unverified` | `<SourceRow>` | Per-evidence-record collapsible row inside a critique card. Collapsed: ▶ chevron + title + host badge. Expanded: URL link + fetched-at + search-query + content-excerpt (bounded scroll above 800 chars). `⚠ unverified` chip slot uses `.md-chip--sm` + `--warn` tone. One instance per record; multiple per card.

#### 6.3.c `Sources segment` composed-component in SPEC.md

Insert under §4 (Composed components):

> **4.7 — Sources segment.** Label: `Sources (N)` in `.t-overline` style. Placement: immediately after the lifecycle footer on every critique card. Separator: dashed top border (`--md-outline-hair`). Empty-state behaviour: when N === 0, **hide the entire segment** (no label, no border, no empty list). Rendered exclusively as a vertical stack of `<SourceRow>` instances.

#### 6.3.d Critique-card composition spec

Insert under §4 as a new sub-section §4.8 (Critique card composition):

> **4.8 — Critique card composition.** All four item kinds (Q · D · I · C) render with the same card primitive (`<ItemCard>` in `run-detail.jsx:1325`). The stacking order, top-to-bottom:
> 1. Header chip row — `id` (mono) · kind · state · `raised by X` · `round N` · `Sources N` (when N>0).
> 2. Body — item text. When `anchor_type !== 'none'`, a tinted blockquote follows.
> 3. **Evidence-needed helper** — italic single line, rendered only when `evidence_required === true`.
> 4. LIFECYCLE — vertical timeline of transitions; each row is `Round N — from → **to** (via) · by Actor` with the reason underneath in a muted block.
> 5. Footer — single dashed-top line: `✓ {terminalState} at round N · M turns to converge`. Always rendered when the item is terminal; never rendered when it is still open.
> 6. SOURCES (N) — the §4.7 segment.
> Only the category chip in (1) varies between kinds. **No kind-specific card variant exists.** This is the invariant that closes B08: Phase 4 Issues and Comments inherit the exact layout Questions and Disagreements use.

#### 6.3.e Rendered visual reference

Add a rendered example of the full card to `design-system/assets/Design System v2.html`, copying the iter-3 mockup's per-card markup. The SPEC + visual reference + live JSX must agree (the §1 design-system invariant); this third surface lands in the same PR as §6.1 + §6.2 so all three converge.

#### 6.3.f Invariant sentence

Add to SPEC.md §1 (Principles):

> **All four critique-item kinds (Question, Disagreement, Issue, Comment) render with the same card layout; only the category chip varies.**

---

## 7. Out of scope

- **No new protocol surface.** No new `RequestEvidence` op (deferred — see §2.2). No change to `evidence_required` semantics or how it's set on the raise side.
- **No standalone Sources page / tab / cross-run dashboard.** Per-card only.
- **No backfill of pre-0114 archived runs.** Legacy renderer stays alive; legacy runs simply don't get a SOURCES segment because they never captured one.
- **No cost / token surface polish.** Covered by spec 0143.
- **No live timeline determinism work.** Covered by spec 0147.
- **No prompt rewrite for sources.** Specifically: we don't change how Claude / GPT are asked to cite. The 14 / 78 = 18% address-with-evidence rate on the anchor run is what the current prompts produce, and that rate is acceptable for this spec. If product wants to raise it, that's a follow-up spec on prompt-pieces.

---

## 8. Test plan

### 8.1 Investigation closure (B09)

A documentation test in `tests/test_provenance_present_on_anchor_run.py`:

- Fixture: a pinned slice of the anchor run's event stream (19 turn_searches + 14 evidence-bearing transitions, materialised from the events table at PR-time).
- Assertion 1: `aggregate_items_from_transcript(fixture)` produces 14 items whose `.evidence` list is non-empty.
- Assertion 2: the same fixture, run through the new `audit_lookup`, produces evidence records whose `consulted_sources` lists are non-empty for at least 10 of the 14.
- Failure of either assertion means the investigation has *re-opened* — provenance has regressed from the partial-firing baseline this spec is built on.

### 8.2 Validator wire-up

`tests/test_evidence_validator_wired.py`:

- Build a `DeepResearchPhase` via `_build_dr_phase` and assert `phase.evidence_validator` is NOT the default no-op lambda (introspect via `getattr` / module identity).
- Same assertion against the replay-path construction in `ledger/replay.py`.

### 8.3 Annotator behaviour (not dropper)

`tests/test_address_block_unverified.py`:

- Craft a `Parsed` payload with one `AddressBlock` whose evidence_event_id doesn't exist in the turn's audit.
- Drive `DeepResearchPhase.apply_turn` and assert: (a) an `ItemTransitioned` event IS emitted (state goes `open → addressed`), (b) its `evidence_records[0]` carries `unverified=True` and `unverified_reason="evidence_event_id_fabricated"`, (c) the `closeout_urged` event also fires.

### 8.4 Patch retention for Phase 4 I/C (B08)

`tests/test_phase4_issue_comment_patches_render.py` — a JSX-renderer test (Jest + jsdom against the bundled JSX):

- Mount `CritiquePhaseContent` with a fixture that contains one Issue and one Comment Item raised in Phase 4 round 2, both with one evidence record.
- Assert the rendered HTML for both contains `Sources (1)` and one `<div class="source-row">`.

### 8.5 Visual regression for the new card surface

Add to `tests/test_visual_critique_card.py`:

- Three snapshot states per kind: open · resolved · capped.
- Each snapshot includes the full ItemCard markup with one evidence record.
- Compare against committed fixtures; diff on any structural change.

### 8.6 Anchor-run replay

A one-off CI step that fetches the anchor run's events table, runs the aggregator + renderer end-to-end, and asserts:

- 38 ItemCards mount.
- 14 of them have a non-empty SOURCES section.
- Zero `console.error` from React or PropTypes.

### 8.7 Wire-payload size budget

`tests/test_wire_payload_budget.py`:

- Serialise the anchor-run aggregator output with the §6.1 additions and assert `phaseStats.items` payload ≤ 64 KB. Prevents accidental re-inclusion of `encrypted_content` in the wire.

---

## 9. Risks

### 9.1 Payload size growth

The §5.2 sanity-check is anchored on one run; runs with heavier source citation could push per-item payload up. The §8.7 budget test caps it. If the cap is hit in production, the next-step retreat is: drop `consulted_sources[].title` for sources whose title duplicates the host (saves ~30 bytes/source) and drop `queries` if they exceed 200 chars (rare).

### 9.2 Backfill: pre-0114 runs

Legacy runs have no `transitions` array on their items, so the §6.2.a branch routes them through `QuestionThread` — no SOURCES segment. This is **correct behaviour**: those runs never captured source data and a SOURCES segment showing `(0)` would be misleading. The empty-state hide-segment rule at §6.3.c makes the absence invisible. Risk: users opening pre-0114 archived runs may ask "where are the sources for this old run?" The mitigation is documentation in How-It-Works: the Sources surface is a v1.10+ feature; older runs predate the capture path.

### 9.3 Visual noise on cards with many sources

A card with 5+ sources has a tall SOURCES segment. The collapsed default-state of each `<SourceRow>` keeps it tight (~28 dp per row), but a card with 10 sources is still 280 dp of source rows. Mitigation: when `evidence.length > 4`, collapse the SOURCES segment behind a `Sources (N) ▶` disclosure at the segment level (the SOURCES segment itself becomes collapsible). Defer the visual mitigation to a follow-up — for the 14 items on the anchor run the max evidence count per item is 3, so we are far from the threshold.

### 9.4 Validator over-flagging

Turning the validator on means some currently-clean ADDRESS blocks may surface as `unverified=True`. On the anchor run, the validator has not been run end-to-end against the persisted audits — running it as part of §8.1 will reveal how many of the 14 evidence records flag. If >50% flag, the §6.1.c "annotator not dropper" rewrite is doing what it should (visibility into a real problem) but the prompt-side fix becomes urgent. We treat that as a discovery, not a blocker for this spec.

### 9.5 The `evidence_event_id` shape gap

The anchor run's evidence records carry `evidence_event_id="search_2"` — a logical, model-emitted handle — not the audit's actual `event_id` (`srvtoolu_01XVrn6QiQ2Ex2jHBwFibjr9` on the same turn). The audit_lookup will therefore miss on every record unless we add a logical→physical mapping in the audit_lookup closure (e.g. enumerate tool_events and accept `search_N` as the N-th tool event in turn-order). The closure documented in §6.1.d MUST do this enumeration; the test at §8.1 will fail otherwise. The right place to do it is in `audit_lookup` itself so the contract validator stays unaware of the convention.

---

## 10. Open questions

1. **Does the `search_N` ↔ `event_id` mapping survive provider asymmetry?** Anthropic's `event_id` is opaque (`srvtoolu_…`); OpenAI's may be sequential / SDK-assigned. If OpenAI's per-turn `tool_events` enumeration is ordered the same way the model would emit `search_N`, the closure in §9.5 works. If not, we may need provider-specific normalisation. Verify against an OpenAI-side turn before merging.

2. **Should the `Sources N` header chip take the per-card-jump dispatch like timeline category chips do?** Today, clicking a timeline category chip jumps to (category, round) in the critique pane (run-detail.jsx:1191-1195). The Sources chip on the card already IS in the critique pane, so a jump is incoherent — but a click-to-expand-all-source-rows would be a reasonable affordance. Defer to UX; current default is "no click handler."

3. **Should the `⚠ unverified` chip be a card-level chip too, or only on the offending source row?** The iter-3 mockup puts it only on the source row. If a card has 3 sources and only 1 is unverified, a card-level chip is misleading. We follow the mockup (row-level only).

