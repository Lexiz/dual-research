---
spec: 0038
title: Web search audit UI + agent-pill alignment fix
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.35.0
created: 2026-05-16
pr: ""
---

# Spec 0038 — Web search audit UI + agent-pill alignment fix

## Context

Spec 0036 captured per-turn web-search audit data (queries + retrieved
URLs + cited snippets + validator flags) and persisted it to
`session_dir/searches/<turn-key>.json`, with HTTP endpoints at
`/api/runs/<id>/searches/{index,turn_key}` on both fs and Supabase
backends. The data layer is done; the UI doesn't yet read it. Every
turn that fired a web search has a bundle sitting on disk with no way
for a human reviewer to see what the model actually retrieved or what
it claimed each citation said. This spec surfaces that data so the
audit goal — *confidence that the final result really had all the
necessary inputs as it moved through the pipeline* — lands.

Three observable signals across the existing card UI:
1. **A `🔎 N` chip on every collapsed card** whose turn fired web
   search, sitting alongside the existing token/cost chips. Quiet on
   turns where search didn't happen.
2. **A one-line gist on every expanded card** that name-checks the
   retrieval volume and gives a click affordance into the full audit.
3. **A new `Web Search` tab on every full-view modal** showing the
   queries, the retrieved-URL list with `page_age` + title (Anthropic;
   URL-only on OpenAI), and — on Anthropic — the `cited_text` snippet
   the model attributes to each citation. Hallucinated-citation
   warnings (cited URL not in any retrieval set) surface inline.

Plus one carryover layout fix the user flagged after Spec 0035 landed:
the per-agent activity pills sit on opposite edges across two adjacent
toolbar rows — Claude on the right of the `PaneHeader`, GPT on the
**left** of the `PaneToolbar`. The user explicitly asked: both pills
should align on the right edge of their rows so a horizontal column
forms. This spec lands the alignment fix alongside the UI surfacing
because both touch the Timeline pane's toolbar region and a separate
PR for a two-line CSS change would be wasteful.

Prior context: spec 0033 established the lazy-load + collapsible-tab
pattern this spec mirrors (`useInputBundle` → `useSearchBundle`,
`InputTabContent` → `WebSearchTabContent`, the per-piece accordion in
`InputSection` → per-query accordion in `QueryGroup`). Spec 0035
established the in-Timeline pill placement; this spec adjusts only
where GPT's pill sits within the toolbar row. The empirical probe
results during 0036 ideation showed the provider asymmetry that this
spec must render honestly: Anthropic gives 10 results per search +
`cited_text` per citation; OpenAI returns URL-only sources via
`include` and offset-only citation annotations with no source-side
snippet.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **A new `useSearchBundle(turnKey)` hook in `live-data.jsx` lazy-loads `/api/runs/<id>/searches/<turn_key>`.** | Mirrors spec 0033's `useInputBundle` byte-for-byte — same `{bundle, loading, error}` shape, same `authedFetch` path, same 404-tolerant flow (404 → bundle stays `null`). Window-exported via the same `Object.assign(window, ...)` pattern so the existing modal layer can call `window.useSearchBundle(turnKey)` without import wiring. |
| D2 | **A new `useSearchIndex(runId)` hook returns the list of turn-keys with audit data.** | Mirrors `useInputIndex` (currently called inline). Powers the chip + gist visibility: a card only renders the search chip when the active run's search index contains that card's `turn_key`. Computed once per run-id; React-Context-cached so cards don't refetch. |
| D3 | **The `🔎 N` chip lives on `ArtifactCard`'s existing chip row, alongside the token + cost chips.** | Looks at the card's `turnKey` (already threaded by spec 0033 for the Input tab) and resolves into the search index. `N` is the count of `tool_events` in the bundle. When `searches == 0` or the bundle is absent, the chip doesn't render — quiet by default. Tooltip on hover: `N web searches · M URLs retrieved`. |
| D4 | **The expanded-card gist appends a single line, NOT a sentence inside the existing summary.** | Existing `composeGist` / sentiment paragraph stays untouched. A new `<SearchGistLine>` sits between the sentiment paragraph and the existing affordance row. Text: `Pulled M results across N queries · click to inspect →`. Click hands off to the same `onOpen` handler the rest of the card row uses (opens full view modal). Provider-aware copy: OpenAI without sources (`consulted_urls` empty) renders `M citations · click to inspect →`. |
| D5 | **The new `Web Search` tab is a sibling of `Content` / `Input` on every full-view modal.** | One-pane modals (Phase 0 critique, Phase 1 plan, Phase 3 doc, Phase 5 final): tab order `Content | Input | Web Search | Sources | Files`. Side-by-side modals (Phase 2 / Phase 4): the tab joins the **left pane's** tab strip alongside `Original | Input`, becoming `Original | Input | Web Search`. The strip already exists from spec 0033; one more entry. |
| D6 | **`WebSearchTabContent` renders a per-query accordion of `QueryGroup` cards.** | Each `QueryGroup` is collapsible (header row + result list). Header: query string (or `(query not exposed)` for OpenAI `open_page`/`find_in_page` actions), action-type chip, result count, hallucinated-citation warning dot when any citation in this group has `matched_query_id === null`. Body: list of `ConsultedSourceCard`s for the query's retrievals + (Anthropic only) a divider-separated citation block per `cited_text`. Default-collapsed when the bundle has more than 2 queries; default-expanded otherwise (so most turns surface their content immediately). |
| D7 | **`ConsultedSourceCard` is provider-aware via the shape of the data, not via a provider switch.** | `url` is required and renders as a linked title. `title` is rendered as a `host · title` line when present (Anthropic); falls back to `host` only (OpenAI). `page_age` renders as a small muted chip when present (Anthropic only). `cited_text` renders as a monospace block when present (Anthropic only) with a subtle `cited from this URL` label. Cards in the consulted-URL list that *were* cited get a small `[cited]` tag; ones that weren't get nothing (so cited results read as the foreground, unused retrievals as the negative-space audit). Provider asymmetry is expressed by what's present in the data; the UI doesn't dispatch. |
| D8 | **Hallucinated-citation warning renders three places.** | (a) Tab-title chip on the `Web Search` tab itself when `flags.cited_url_not_in_consulted_sources` is true — small red dot. (b) `QueryGroup` header warning dot when any citation with `matched_query_id === null` was attributed to that query (rare; matches the validator's "first event wins" cross-ref). (c) Per-citation warning row inside the per-query body: a callout listing the citation's URL + title + `not in any retrieval set` label. The validator already populated `matched_query_id`; the UI just reads it. |
| D9 | **No on-page "fix this" affordance for hallucinated citations.** | A spec-0038-vintage reviewer's job is to *notice* and decide what to do with the run, not to edit it. The audit is read-only. Out-of-band: the reviewer can re-run the prompt, file the source for human review, etc. — orthogonal to this spec. |
| D10 | **Session-level audit summary lives in the run-detail header.** | A new `<RunSearchSummary>` element sits in the existing run header chip row (alongside cost / status / errors). Renders only when the run has at least one audited turn. Format: `🔎 12 · 47 URLs` (total searches across all turns · total consulted URLs); when any turn flags hallucinated citations, appends a `· ⚠ 1 unmatched` chip with the count. Click jumps the user to the timeline tab and scrolls the first flagged card into view (a small affordance — not a dedicated "audit dashboard" view). |
| D11 | **`Web Search` tab is the LAST default tab in the modal's tab strip.** | Content stays primary (it's what the model produced). Input second (what went in, spec 0033). Web Search third (what the model pulled mid-inference). Existing `Sources` / `Files` tabs on the Phase 0 brief modal slot after. The order reflects reader intent: read the output → audit the input → audit the retrievals → audit attachments. Same order on side-by-side modals' left pane. |
| D12 | **Empty-state copy is provider-aware AND replay-safe.** | Three honest states the UI must render: (a) **No bundle on disk** (pre-0036 transcript or `web_search_enabled() == false`) → `Web search audit not recorded for this turn. This run pre-dates spec 0036 or web search was disabled.` (b) **Bundle present but no tool events** (search was enabled but the model didn't invoke it) → `Web search was available but not used in this turn.` (c) **OpenAI bundle with empty `consulted_sources`** (regression case: provider stopped returning `sources`) → `Provider returned no retrieval list — only citations are auditable.` Each case reads as deliberate rather than as a missing-feature glitch. |
| D13 | **`cited_text` is the load-bearing field; the UI must never hide it.** | When Anthropic populated `cited_text`, the citation card renders it verbatim — no truncation, no `…(expand)`. The whole audit value is that the human can read what the model claims it extracted. The block is monospace, soft-wrapped, no max-height. Same rule as spec 0033's input bundles which are also never truncated. |
| D14 | **GPT's pill moves from the LEFT to the RIGHT of the `PaneToolbar`.** | Current layout (spec 0035): row 1 `PaneHeader` has Claude pill on the right; row 2 `PaneToolbar` has GPT pill on the **left**, then live-count chip, `[flex]`, then `Conversation | Consumption` tabs on the right. New layout: row 2 `PaneToolbar` has the live-count chip on the left, then `[flex]`, then `Conversation | Consumption` tabs, then GPT pill on the right. Result: Claude pill on row 1 right, GPT pill on row 2 right, vertically aligned. Tabs sit immediately to the left of GPT. |
| D15 | **No data-model changes, no event changes.** | Pure consumption of spec 0036's persisted bundles + an existing `flags` object. The wire format gains nothing; the frontend gains a new tab + a few chips. |
| D16 | **The spec ships behind no flag.** | The data layer (spec 0036) is additive; the UI surfacing is also additive — a new tab and chips on existing cards. Pre-0036 transcripts hit the D12(a) empty-state which is its own deliberate piece of UX. We've shipped this many additive-UI passes; no flag needed. |
| D17 | **Provider-aware empty messages do NOT shame OpenAI.** | The OpenAI snippet gap is real but the framing should be neutral — "this provider doesn't expose source-side snippets" rather than "OpenAI is worse than Anthropic." The user explicitly asked for honest asymmetry display; not for provider blame. Spec 0036's deferred re-fetch is the path to closing the gap if it bites in practice. |
| D18 | **No cross-reference rendering of `[V]` tags inside the model's markdown output.** | Tempting to scan the Content tab's markdown for `[V]` numeric tags and highlight the corresponding citation row in the Web Search tab. Out of scope — the spec 0036 cross-reference is already structural (`matched_query_id` on each Citation); rendering anchored cross-references inside the rendered markdown would require a markdown-renderer hook and is its own surface. The Web Search tab is self-sufficient. |

## Proposed change

### 1. `useSearchBundle` + `useSearchIndex` hooks — `live-data.jsx`

Add two hooks alongside the existing `useInputBundle` / `useAppMeta`.
Window-exported via the same pattern.

```js
// Spec 0038: lazy-fetch a per-turn search audit bundle.
// 404 is the legitimate "no audit recorded" case — bundle stays null,
// loading flips false, no error raised. Mirror useInputBundle.
function useSearchBundle(turnKey) {
  const ctx = React.useContext(RunContext);
  const runId = ctx?.runId || getActiveRunId();
  const [bundle, setBundle] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!turnKey || !runId) { setBundle(null); return; }
    let cancelled = false;
    setLoading(true);
    setBundle(null);
    setError(null);
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/searches/${encodeURIComponent(turnKey)}`)
      .then(r => r.status === 404 ? null : r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(data => { if (!cancelled) { setBundle(data); setLoading(false); } })
      .catch(e => { if (!cancelled) { setError(String(e)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [turnKey, runId]);
  return { bundle, loading, error };
}

// Spec 0038: list of turn-keys with persisted search audit. Used by the
// chip-on-collapsed-card layer to decide whether to render.
function useSearchIndex(runId) {
  const [keys, setKeys] = React.useState(null);
  React.useEffect(() => {
    if (!runId) { setKeys(null); return; }
    let cancelled = false;
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/searches/index`)
      .then(r => r.ok ? r.json() : { keys: [] })
      .then(data => { if (!cancelled) setKeys(new Set(data?.keys || [])); })
      .catch(() => { if (!cancelled) setKeys(new Set()); });
    return () => { cancelled = true; };
  }, [runId]);
  return keys;  // Set<string> | null (null while loading)
}

// Window-export at the same Object.assign call site that handles
// useInputBundle / useAppMeta.
Object.assign(window, { useSearchBundle, useSearchIndex });
```

Threaded into `RunContext` so all consumers share one index per run.
The index is small (1-30 keys per run); fetched once on run-detail
mount, invalidated on `runId` change.

### 2. Search chip on collapsed cards — `ArtifactCard`

`run-detail.jsx::ArtifactCard` (line ~1476). The card already accepts
`item.turnKey` (spec 0033). Read the run's search index; if it
contains `item.turnKey`, render a `<SearchChip turnKey={...} />` in
the existing chip row alongside the token + cost chips.

```jsx
function SearchChip({ turnKey, run }) {
  const { bundle } = window.useSearchBundle(turnKey);
  if (!bundle) return null;
  const queries = bundle.tool_events?.length || 0;
  const urls = (bundle.tool_events || []).reduce(
    (n, ev) => n + (ev.consulted_sources?.length || 0), 0,
  );
  if (queries === 0) return null;
  const hasWarning = bundle.flags?.cited_url_not_in_consulted_sources;
  return (
    <span title={`${queries} web search${queries === 1 ? '' : 'es'} · ${urls} URL${urls === 1 ? '' : 's'} retrieved`}
          style={{ ...searchChipStyle }}>
      🔎 {queries}{hasWarning && <span style={{ color: 'var(--warn)' }}> ⚠</span>}
    </span>
  );
}
```

A lighter-weight surface that uses *only* the index (count of
events) is fine for the index-path. But fetching the bundle for
every collapsed card would mean N parallel requests on a busy
timeline. Mitigation: instead of `useSearchBundle` on the chip,
extend `useSearchIndex` to return a Map of `turnKey → { queries,
urls, hasWarning }` — server returns a small `index/summary` payload.
Trade-off note in §3.

Lighter path picked: extend the existing `/api/runs/<id>/searches/index`
to optionally return per-key summary stats. New query parameter
`include=summary` → response shape becomes `{ keys: [...], summary:
{ <key>: { queries: N, consulted: M, has_warning: bool } } }`. The
chip layer fetches summary once; per-card chip reads from the Map. No
per-card network call.

### 3. Server: `searches/index?include=summary` — `server.py`

Both fs and Supabase backend variants extend `_list_search_audit_keys_*`
into a small wrapper that, when summary is requested, opens each
JSON, computes:

- `queries` = `len(tool_events)`
- `consulted` = sum of `len(ev.consulted_sources)` across events
- `has_warning` = `bool(flags.cited_url_not_in_consulted_sources)`

Streamed back as `{ keys, summary: { ... } }`. When the param is
absent, the existing shape is preserved (backward compatible).

For Supabase: `session_files` rows for `searches/*.json` get fetched
in one query and decoded server-side. Same loop structure as
`_list_input_bundle_keys_supabase`.

### 4. Gist line on expanded cards — `ArtifactCard`

The expanded body (currently rendered when the card is not collapsed)
gains a `<SearchGistLine>` between the existing sentiment paragraph
and the affordance row. Uses the same per-key summary from
`useSearchIndex(runId, { withSummary: true })`. Empty when no audit
data for this turn-key.

Copy:
- Anthropic: `Pulled M results across N queries · click to inspect →`
- OpenAI (with sources): same shape, possibly smaller numbers
- OpenAI (no sources): `K citations · click to inspect →`
- With warning: prepend `⚠ ` and append `· 1 cited URL not in any retrieval set`

Click handler: same as the existing `View in full mode` button —
opens the full-view modal pre-positioned to the Web Search tab.

### 5. Full-view modal `Web Search` tab — `run-detail.jsx`

Three modal frames touch this:

(a) **One-pane modals** (Phase 0 `PreflightResponseModal`, Phase 1
`DraftReviewModal` left pane (skip — see §5d below), Phase 3
`DocumentModal`, Phase 5 final). Each currently has a `tabs` array
of `{ name, content }` pairs (the spec 0033 pattern). Add a new
entry between `Input` and the existing `Sources`/`Files` (if any):

```jsx
{
  name: 'Web Search',
  content: <WebSearchTabContent turnKey={item.turnKey} />,
  ...optional warning badge per D8(a)
}
```

(b) **Side-by-side modals** (`NegotiateReviewModal`, Phase 2/Phase 4).
The left pane already has `Original | Input` sub-tabs. Add `Web
Search` as a third sub-tab. The right pane (the critique view)
stays untouched — Web Search is about *this turn's own* retrievals,
which belong on the left where the turn's content lives.

(c) **Brief modal** (`InputBriefModal`). The Phase 0 shared `input`
key has no `searches/<key>.json` (no model call yet), so the tab is
hidden on this modal entirely. Cleaner than rendering the empty-state.

(d) **Phase 1 `DraftReviewModal`** (spec 0034). Its left pane is the
brief, not a turn. The brief had no model call; the *draft* on the
right is the turn. Right pane gains the Web Search tab — same `tabs`
array pattern. Same `turnKey` plumbing from spec 0033.

### 6. `WebSearchTabContent` + `QueryGroup` + `ConsultedSourceCard`

New component cluster in `run-detail.jsx`. Mirror the spec-0033
`InputTabContent` → `InputSection` shape.

```jsx
function WebSearchTabContent({ turnKey }) {
  const { bundle, loading, error } = window.useSearchBundle(turnKey);
  if (loading) return <LoadingStub />;
  if (error) return <ErrorStub error={error} />;
  if (!bundle) return <EmptyState kind="no-bundle" />;
  const events = bundle.tool_events || [];
  if (events.length === 0) return <EmptyState kind="no-search" />;

  return (
    <div>
      {bundle.flags?.cited_url_not_in_consulted_sources && <HallucinationBanner bundle={bundle} />}
      {events.map((ev, i) => (
        <QueryGroup
          key={ev.event_id || i}
          event={ev}
          citations={bundle.citations || []}
          defaultCollapsed={events.length > 2}
        />
      ))}
    </div>
  );
}
```

`QueryGroup` renders:
- Collapsible header row: `[chevron] [query string] [actionType pill] [N results] [optional ⚠]`
- Body (when open): list of `ConsultedSourceCard` for each `consulted_source`,
  followed by a `Citations` sub-section that filters the parent
  bundle's `citations` to those whose `matched_query_id === event.event_id`.
- Empty `consulted_sources` (OpenAI without `include` or regression):
  the body shows only the Citations sub-section.

`ConsultedSourceCard` renders:
- Linked title (or `host` when title is null) → `target="_blank"`
- `host` subtitle line
- `page_age` chip (Anthropic only)
- A small `[cited]` tag in the corner if this URL appears in any
  citation's URL (after the same `normalize_url` stripping rule the
  backend validator uses — exposed via a tiny client-side helper
  that strips `utm_source=…`, lowercases the host, drops trailing /)
- For Anthropic citations: a monospace `cited_text` block below the
  card (one per citation pointing to this URL — usually 1, sometimes
  more if the model cited the same URL twice)

The `cited from this URL` label uses a soft accent border-left on
the monospace block so it's visually anchored to its source card.

### 7. Hallucination warning — three placements

(a) Tab-title chip on the `Web Search` tab. The tab strip already
supports a per-tab badge in the spec-0033 `tabs` array (used for the
input bundle's "(repair)" badge in some modal frames). Reuse:
`tabs.push({ name: 'Web Search', badge: hasWarning ? '⚠' : null, ... })`.

(b) `QueryGroup` header dot: when any of `bundle.citations` has
`matched_query_id === event.event_id` AND that citation's `url` is
NOT in `event.consulted_sources` (cross-event mismatch; rare). The
common case is `matched_query_id === null` for hallucinated cites,
which gets folded into the per-tab badge but NOT the per-event badge
(because by definition the validator couldn't pin those to a query).

(c) `<HallucinationBanner>` at the top of `WebSearchTabContent` when
the tab-level flag is set. Lists the offending citations:

```
⚠ 1 citation references a URL that wasn't in any retrieval set
   • https://fabricated.example.invalid/x
     "Title from the citation annotation"
```

This is the most concrete piece of audit output the user gets — a
named claim the model cited that the search backend never returned.

### 8. Session-level audit summary — run header

`run-detail.jsx::RunDetailHeader` (line ~12). The header's chip row
already carries cost + status. Add `<RunSearchSummary>` after the
cost chip:

```jsx
function RunSearchSummary({ summary }) {
  if (!summary) return null;
  const totalQueries = sum(summary.values(), s => s.queries);
  const totalUrls = sum(summary.values(), s => s.consulted);
  const warnings = Array.from(summary.values()).filter(s => s.has_warning).length;
  if (totalQueries === 0) return null;
  return (
    <button onClick={onJumpToFirstWarning} style={{ ...chipStyle }}>
      🔎 {totalQueries} · {totalUrls} URLs
      {warnings > 0 && <span style={{ color: 'var(--warn)' }}> · ⚠ {warnings} unmatched</span>}
    </button>
  );
}
```

`onJumpToFirstWarning` scrolls the timeline to the first card whose
`turn_key` has `has_warning === true`. If no warnings, the click
opens the first card with web search content. If no audit data,
the element doesn't render.

### 9. GPT pill alignment fix — `Timeline` toolbar

`run-detail.jsx::Timeline` toolbar layout (line ~375-394). Current:

```jsx
<PaneToolbar>
  <AgentStrip agent="gpt" run={run} />          {/* LEFT */}
  [live-count chip]
  <span style={{ flex: 1 }} />
  <TimelineTabs active={tab} onChange={setTab} prominent />  {/* RIGHT */}
</PaneToolbar>
```

New:

```jsx
<PaneToolbar>
  [live-count chip]                              {/* LEFT */}
  <span style={{ flex: 1 }} />
  <TimelineTabs active={tab} onChange={setTab} prominent />
  <AgentStrip agent="gpt" run={run} />          {/* RIGHT — aligned with Claude on row 1 */}
</PaneToolbar>
```

The `gap` between `TimelineTabs` and `AgentStrip` should match the
existing internal spacing (likely `gap: 12px` on the toolbar's flex
container — verify before changing). No CSS additions; pure
JSX-reorder.

### 10. Empty states + replay safety

`<EmptyState kind="...">` renders one of three messages per D12. The
component picks the message based on the kind and the bundle
shape. Always rendered inside the `Web Search` tab — never raises
errors, never causes the modal to fail to open. Pre-0036
transcripts hit `kind="no-bundle"` cleanly; the chip + gist + run
summary all gracefully report nothing.

### 11. Tests

Almost entirely visual; the unit-testable surface is:

- **Backend** — `tests/ui/test_server.py`: extend `TestSearchAuditEndpoints`
  with a `test_index_with_summary` case that asserts the
  `?include=summary` query param adds a `summary` object keyed by
  turn-key with `queries` / `consulted` / `has_warning` per key.
  Backwards-compatibility: the existing `test_index_lists_keys_present_on_disk`
  must still pass without changes.

- **Hook contract** — frontend tests don't have a runner in this
  repo (per the project's "frontend = manual" convention from spec
  0033's test plan). A small `tests/ui/test_search_index_helper.py`
  asserting the `_list_search_audit_keys_fs` + new
  `_search_audit_summary_fs` helpers return the right shape over a
  fixture session directory is the equivalent backend coverage.

- **No new orchestrator / protocol tests.** This spec doesn't touch
  those layers.

Manual UI verification: explicit checklist in the Test plan section.

### 12. Files touched

Backend:
- `src/dual_research/ui/server.py` — extend `/searches/index`
  with optional `?include=summary` on both fs + Supabase apps.
  Add helpers `_search_audit_summary_fs` /
  `_search_audit_summary_supabase`.

Frontend:
- `src/dual_research/ui/static/live-data.jsx` — `useSearchBundle`
  + `useSearchIndex` (with summary), window-exports.
- `src/dual_research/ui/static/run-detail.jsx`:
  - `WebSearchTabContent` + `QueryGroup` + `ConsultedSourceCard` +
    `HallucinationBanner` + `EmptyState` (for the search tab) +
    `SearchChip` + `SearchGistLine` + `RunSearchSummary`.
  - `ArtifactCard` chip row + expanded body gain the chip + gist line.
  - `PreflightResponseModal`, `DocumentModal`, `final` modal,
    `NegotiateReviewModal` (left pane), `DraftReviewModal` (right
    pane) gain the `Web Search` tab in their `tabs` arrays.
  - `RunDetailHeader` gains `<RunSearchSummary>` in its chip row.
  - `Timeline` `PaneToolbar` re-orders children: live-count + flex +
    tabs + GPT pill (D14).
  - `InputBriefModal` (Phase 0 shared input) deliberately does NOT
    gain a Web Search tab — explicit comment.

Tests:
- `tests/ui/test_server.py` — `TestSearchAuditEndpoints` extended
  with summary-param coverage.
- `tests/ui/test_search_summary_helper.py` (new) —
  `_search_audit_summary_fs` over a fixture session dir.

### 13. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.34.0 → 0.35.0.
- `CHANGELOG.md`: new `## [0.35.0] — YYYY-MM-DD` entry covering the
  three user-visible deltas (chip + gist + tab, hallucination
  warning, GPT pill alignment fix) and the small server-side
  `?include=summary` extension.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`.

## Out of scope

- **Server-side re-fetch of cited URLs** (deferred from spec 0036).
  Would close OpenAI's snippet gap and hedge link rot, but introduces
  network failure surfaces (403/paywall/JS-rendered/ToS), content
  extractor maintenance, and storage growth. Wait until the gap bites
  in real reviews.
- **Notion-as-MCP for agents** (deferred from spec 0036). Runtime
  tool the agents would invoke mid-inference — a different audit
  axis from web search and best designed alongside re-fetch.
- **Cross-reference rendering of `[V]` tags inside model markdown.**
  D18 — out-of-scope; the Web Search tab is self-sufficient.
- **Audit-grade `[V]`-tag-to-citation linking back to the source
  card.** Would be the bridge in the other direction (citation row
  highlights the markdown's `[V]` tag). Same scope concern as above.
- **Editing or annotating the audit.** Read-only.
- **An audit dashboard** that aggregates across runs (e.g.
  "hallucinated citations per model per week"). Single-run only.
- **OpenAI `web_search_preview` tool variant.** Stays on `web_search`
  per spec 0036.
- **Reasoning-model `open_page` / `find_in_page` action visualisation.**
  The data layer captures them (`action_type` survives); the UI
  renders the action-type chip in `QueryGroup`'s header but doesn't
  build a custom view for those actions. Future spec if needed.
- **Inline diff between cited URL and retrieved URL** when both are
  present but normalisation made them match. The match is implicit
  via `matched_query_id`; we don't render side-by-side normalisation
  trails.
- **Per-citation expand-to-context** showing surrounding output_text
  beyond `text_span_start`/`end`. The model's full text is on the
  Content tab; expanding the highlight is a different UX.
- **Header reflow on the run-detail page beyond the GPT pill
  realignment.** Spec 0035's two-row header layout stays.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0038 adds 2 new
      tests (server `?include=summary`, helper unit). 572+2 = 574.
- [ ] Manual: fresh prod-tier run with web search enabled. Visit
      the run page. The run header chip row shows
      `🔎 N · M URLs` after the run completes.
- [ ] Manual: collapsed cards on the Conversation timeline show a
      `🔎 N` chip on every card whose turn fired web search; chip
      tooltip reports `N web searches · M URLs retrieved`. Turns
      with no search (Phase 0 preflight typically) show no chip.
- [ ] Manual: expand a card. Below the sentiment paragraph, the
      gist line reads `Pulled M results across N queries · click to
      inspect →`. Click → full-view modal opens with the `Web Search`
      tab pre-selected.
- [ ] Manual: on the `Web Search` tab, the per-query accordion
      lists each search the model performed. Anthropic turns show
      query string + 10 results per query with title + host +
      `page_age` chip + `[cited]` tags on cited URLs + `cited_text`
      monospace blocks attributed to each citation. OpenAI turns
      show query string + URL-only consulted sources + URL+title
      citations with no `cited_text`.
- [ ] Manual: synthesise a hallucinated citation (e.g. via the same
      fixture pattern as `tests/audit/test_validate.py` —
      `cited_url_not_in_consulted_sources` flag set). The card's
      chip shows `⚠`; the modal's tab title shows `⚠`; the tab
      content opens with a `HallucinationBanner` listing the
      offending URL + title; the run-header summary shows
      `⚠ 1 unmatched`.
- [ ] Manual (replay safety): load a pre-0036 transcript. No chip
      on cards. No gist line. No run-header `🔎 …` chip. Opening any
      full-view modal shows `Web Search` tab content reading
      `Web search audit not recorded for this turn. This run pre-dates
      spec 0036 or web search was disabled.`
- [ ] Manual (no-search turn): open a Phase 0 preflight card's
      modal in a fresh run. `Web Search` tab reads `Web search was
      available but not used in this turn.`
- [ ] Manual (alignment fix): on the run-detail page, the Claude
      pill (top right of `PaneHeader`) and the GPT pill (now top
      right of `PaneToolbar`) align on the same right edge across
      consecutive toolbar rows. The `Conversation | Consumption`
      tabs and the live-count chip sit between them, both shifted
      to maintain spacing.
- [ ] Manual (hosted UI): deploy 0.35.0. `/api/runs/<id>/searches/index?include=summary`
      returns the summary map; the run-header chip + per-card
      chips render against the hosted data the same way.
- [ ] Manual (large-result turn): a turn with 5 queries × 10
      results = 50 cards on the tab. Scrolling is smooth; each
      accordion collapses cleanly; the cited-text blocks
      soft-wrap without horizontal overflow.

## Risks

- **Per-card `useSearchBundle` would fan out to N parallel requests
  on a busy timeline.** Mitigation: the summary path (D2 → §3) means
  per-card chip + gist read from a single `?include=summary` fetch;
  only the modal's tab fetches the full bundle. One request per
  page-load + one per opened modal.
- **`hasWarning` from the summary mis-reports because the validator
  ran differently than the UI's read.** The summary is computed at
  index-list time from the persisted JSON's `flags` field, NOT
  re-derived. As long as `validate_search_audit` is the only writer
  of those flags (it is, via `_on_turn_searches`), summary and tab
  agree byte-for-byte.
- **`InputBriefModal` shouldn't show the Web Search tab BUT the user
  might still expect it to.** Mitigation: comment in the modal
  body explaining the absence + the Phase 0 critique modal does
  show it (the per-agent critique IS a turn). If the user complains,
  add a "no model call on the brief" empty-state in a follow-up.
- **OpenAI `consulted_sources` empty case visually reads as broken.**
  Mitigation: the explicit D12(c) empty-state copy names the
  provider behaviour. The citation list still renders below it so
  the tab isn't empty.
- **GPT pill alignment fix breaks at narrow viewports.** Same
  spec-0035 concern: two pills + tabs + live-count + flex needs
  ~720px to fit cleanly. Mitigation: `flex-wrap: wrap` on the
  `PaneToolbar` already exists (per spec 0035); wraps gracefully
  on narrow screens. Verify at 640px / 1280px.
- **`cited_text` blocks can be long (Anthropic citations are
  sometimes 300+ chars).** D13 says no truncation. Risk: a
  Phase 4 turn with 14 citations × 300 chars each = ~4KB of mono
  text in the tab. Trivial for rendering; just visually long.
  Acceptable per the spec's audit goal.
- **`?include=summary` adds per-key JSON parsing on the server
  index path.** On Supabase, that's one row per turn-key —
  reasonable. On large runs (~30 turn-keys), the parse is
  millisecond-scale. Mitigation: if it ever becomes slow, a
  follow-up spec can persist the summary alongside the audit at
  write time (in `_on_turn_searches`).
- **The session-level summary chip's click handler depends on
  knowing the timeline tab is active.** When the user is on the
  Consumption tab + clicks the run-header chip, the handler
  should switch tabs. Mitigation: the click handler always sets
  `timelineTab = "conversation"` before scrolling — clean fallback.
- **Adding a new tab to side-by-side modals' left pane shifts
  existing tab indices in any per-modal state.** Mitigation: the
  spec-0033 tab strip already takes `tabs` as a named array, not
  index-based — switching by name (`Original` / `Input` / `Web
  Search`) is stable through additions.
- **Pre-0036 runs hit the `no-bundle` empty-state on every full-
  view modal, which might feel noisier than expected.** Acceptable
  — the message is honest about why and the user can ignore it on
  pre-spec runs.

## Open questions

- Whether the chip should show `🔎 N` (count) or `🔎` alone with a
  tooltip carrying the count. v1 picks `🔎 N` — denser but more
  scannable. Easy to swap.
- Whether the per-citation warning row inside `QueryGroup` body
  should auto-expand its parent accordion when the tab is opened
  via the warning chip. v1 doesn't auto-expand; the user clicks
  through. If the click flow feels clunky in practice, follow-up
  can deep-link.
- Whether `RunSearchSummary` should also count *cited* URLs
  (currently counts retrieved only). The cited-URL count is the
  number of `bundle.citations` entries. Tempting; v1 skips it to
  keep the chip narrow. Tooltip can carry it instead.
- Whether the OpenAI URL-only consulted source cards should show
  the URL hostname-prominently (`example.com` big, full URL
  smaller) given there's no title to anchor them. v1 picks
  host-only as the title; tooltip carries the full URL. Easy to
  flip if it reads as too sparse.
- Whether the GPT pill alignment fix should also reverse on the
  other axis (Claude on LEFT of PaneHeader, GPT on LEFT of
  PaneToolbar) — i.e. both pills on the LEFT. The user's
  redirect was for both-on-right. v1 follows that explicitly;
  a future redesign can revisit.
