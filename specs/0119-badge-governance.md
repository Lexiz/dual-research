---
spec: 0119
title: Badge governance — unified chip primitive, vocabulary, and surface-level rollout
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.4.0
created: 2026-05-20
pr: ""
---

# Spec 0119 — Badge governance

> Ship bucket: **Foundation**
> Depends on: **0114 (contract module), 0115 (per-category chips + Item model), 0116 (modal cleanup)**
> Blocks: **Spec 0120 (turn-modal Open Questions / Claims rework)** — that spec reuses this vocabulary verbatim.
> Complexity: **L** (broad surface; touches `run-detail.jsx`, `shared.jsx`, `components.css`, `design-language.jsx`, `design-system/SPEC.md`).
> Targeted version bump: **MINOR** — visible UI changes across timeline + critique pane; no backend, no data-layer changes.

## 1. Context

The user-facing badge layer has accreted ad-hoc components over 30+ specs. Spec 0115 consolidated some of this (single `Item` model, per-category timeline chips with `standing · raised · closed`) but stopped short of unifying every chip surface. An audit conducted in conversation 2026-05-20 surfaced the following issues simultaneously, all rooted in the same missing governance:

1. **Multiple chip primitives.** `<Chip>` (shared.jsx) coexists with `StatChip` (run-detail.jsx:3631), `StatusInline` (~:3785), `ConvergedChip` (~:3759), `GhostedRoundsBadge` (~:7120), `SearchChip`, and the custom `.drift-chip` (`components.css:6258`). The critique pane filter row uses `<Tab>` inside `<TabGroup>` (`CritiqueTypeFilter` ~:6375) — a different primitive from the timeline's `<Chip>`. Inside expanded critique cards, per-turn rows render verdicts as colored inline text (`_mapVerdict` ~:7225) rather than as chips at all.
2. **Provider / activity wedged together.** Timeline turn headers render `<qref qref-full><AgentIcon/> Claude · turn 1</qref>` at `run-detail.jsx:984` — one combined span with a `·` separator. The user's review explicitly called this out: provider and round must be visually separate.
3. **Legacy vocabulary still leaking.** `run-detail.jsx:6604, 7038, 7052` still reference `claim` as a category label even though [`contract/categories.py:8`](src/dual_research/contract/categories.py) declares the claim kind dead post-0114 ("The legacy `claim` kind is gone — the new prompts never ask for it"). The critique pane shows "CONCEDED" and "ANSWERED" as per-turn verdicts ([`ui/disagreements.py`](src/dual_research/ui/disagreements.py)), neither of which appears in the canonical 6-state lifecycle ([`contract/lifecycle.py:22-27`](src/dual_research/contract/lifecycle.py)).
4. **Verbose chip text overflows narrow columns.** The 0115 chip format `Questions  4 standing · 2 raised · 1 closed` is ~165 px wide. Two per turn card + provider + round + status = 480 px on the chip row alone. When the critique pane is open the timeline column collapses to ~400 px and the chips overflow or wrap into illegibility. Per Phase 4 (4 categories), even at full width the chip row regularly wraps.
5. **Inconsistent provider attribution in critique pane.** Cards in `CritiqueExplorer` (`~:5963`) use "Raised by Claude" as text inside an `extraChips[i].label` with an embedded `<BrandMark>` — different rendering than the timeline's brand-coloured Claude/GPT chip. Same provider, four different visual forms across surfaces.
6. **Run-wide drift counter is stale vocabulary.** The critique pane header still renders a custom `.drift-chip` showing `⚠ 15 drift`. Per [spec 0114 line 340](specs/0114-deep-research-protocol.md:340), drift in the new protocol is a per-turn debug signal (rare); the legacy run-wide aggregation no longer reflects the data model. `validate-run` CLI is now the canonical surface for per-run drift totals.
7. **Status chip is sometimes absent.** Turn cards display nothing on the right when the turn completed without emitting AGREED. The user requested an explicit "round completed" signal — never bare.
8. **Repair status still in CSS/code paths even though removed protocol-side.** `repair` references in `_call.py:48`, `phase2.py:112-116`, etc., are legacy. The CSS tone-warn `repair` chip on turn cards is dead vocabulary.

Behind these symptoms is one cause: **there is no single source of truth for what badges exist, what they mean, where they appear, and how they compose.** Every surface inherited its chips from whichever spec introduced it. This spec installs that source of truth, retires the ad-hoc components, and wires every chip-bearing surface to the canonical system.

The companion document is the ideation mockup developed in conversation: `/tmp/badge-governance-mockup.html` (iteration 3, dated 2026-05-20). The mockup is the visual reference. This spec is the implementation reference.

## 2. Goals

1. **One primitive.** A single `<Chip>` component replaces every ad-hoc chip / badge / pill / verdict-label in the UI.
2. **One vocabulary.** Category names, lifecycle states, turn statuses, and modifiers each have exactly one canonical set, sourced from the contract module. No surface invents local vocabulary.
3. **One legend.** The Critique pane filter row at the top is the canonical legend for category meaning — full-word labels with letter-bubble icons + counts. Every dense-form chip on every other surface (timeline cards, phase headers, critique card headers, lifecycle rows) uses the same bubble + color combination so a reader can scroll up to the legend any time.
4. **Never-bare status.** Every completed timeline card carries a right-aligned status chip. Live = `running`. Agreed = `✓ agreed`. Otherwise = bare `✓` (UX marker for "this turn finished, didn't emit AGREED"). Pre-run = `queued`.
5. **Compact yet legible at narrow widths.** Phase 4 turn cards (4 category chips + provider + round + status) fit on one line at the typical narrow-timeline width of ~600 px, with graceful wrap below that.
6. **Vocabulary cleanup.** All legacy verbs (`conceded`, `answered`, `noted`), legacy categories (`claim`), and legacy statuses (`repair`) are removed from JSX, CSS, and label maps. The compiler is the enforcement mechanism.
7. **Design-system documentation.** `design-system/SPEC.md` gains a "Badge governance" section that future specs reference instead of inventing local rules.

## 3. Non-goals (out of scope)

- **Turn modal Open Questions / Claims panel restructure.** Spec 0120 (planned, follows this) covers the per-segment labelling of `> quote / **stars** / body` inside the modal and the addition of a "raised by" badge to those cards. That spec reuses this spec's vocabulary verbatim, but introduces its own card-internal layout rules.
- **Run-list page, header chrome, consumption tab chip migration.** Inventoried below but explicitly deferred to a follow-up spec. Those surfaces have fewer chips and lower friction; spec'ing them separately keeps this spec's review surface manageable.
- **Backend / protocol changes.** No edits to `src/dual_research/contract/`, `src/dual_research/orchestrator/`, `src/dual_research/protocol/`, `src/dual_research/events/`. The data layer is already sufficient (see § 5).
- **New data fields on `Item`, `TurnCategoryStats`, `CategoryCounters`, `ItemTransition`, or `EvidenceRecord`.** Existing fields drive every chip; nothing new is required.
- **Migration of historical run artifacts.** Legacy renderer remains in place for pre-0114 runs (per 0115 § "legacy mode"). This spec touches the new-protocol render path only.
- **Sources widget visual design.** The collapsible-row `SourceRow` (spec 0115 step 3) is kept exactly as is — confirmed during ideation that the visual treatment is the intended form.

## 4. The unified Chip primitive

### 4.1 Component shape

One React component, replacing all chip-like JSX patterns:

```jsx
<Chip
  tone="info | ok | warn | err | idle | claude | gpt | neutral"
  shape="pill | square"          // default: pill. square ONLY for identifier chips.
  size="default | lg"            // default: 22 px height. lg: 26 px.
  mono={false}                   // monospace font + 10.5 px
  dim={false}                    // 55 % opacity, secondary number tints
  iconOnly={false}               // tighten padding for single-glyph chips (e.g. bare ✓)
  // slots — mutually exclusive leading element:
  leadingDot={false}             // 6 px filled circle, color = tone
  leadingIcon={<Icon.X />}       // 12 px SVG icon
  categoryBubble="Q | D | I | C" // 14 px filled circle, knockout-white letter
  // content slots:
  label="Questions"              // optional textual label
  value={4}                      // optional large bold number (standing count)
  add={2}                        // optional +N delta (green)
  sub={1}                        // optional −N delta (red)
  trailingSuffix={"⊘ 1"}         // optional small monospace suffix
  ariaLabel="..."                // accessibility override (required when label is omitted)
>
  {children /* freeform for content the slots don't cover */}
</Chip>
```

Render order inside the chip: `leadingDot | leadingIcon | categoryBubble` → `label` → `value` → `add` → `sub` → `trailingSuffix` → `children`. Slots that are absent render no DOM and no gap.

Defined in `src/dual_research/ui/static/shared.jsx` alongside the existing `Chip` (which is upgraded in place — same export, new slots).

### 4.2 Tones

Eight canonical tones, M3-style filled tonal pastel pill (currentColor = tone color; background = color-mix 18 % opacity onto surface):

| token | color (dark) | semantics |
|---|---|---|
| `info` | `--info` `#6b9cf0` | open / live / questions / informational |
| `ok` | `--ok` `#6fb380` | resolved / converged / agreed / done |
| `warn` | `--warn` `#d4a056` | disagreements / acknowledged / closeout / modifier |
| `err` | `--err` `#d96a6a` | issues / capped / errored / unverified |
| `idle` | `--idle` `#7d8290` | comments / withdrawn / queued / inert |
| `claude` | `--agent-a` `#d4a574` | Claude provider |
| `gpt` | `--agent-b` `#7cc4b8` | OpenAI / GPT provider |
| `neutral` | surface-container-high | activity / round / sources / "All" filter / brief |

Tokens already exist in `tokens.css`. The only new addition is `--idle` (currently scoped under `--p-idle`; promote to a top-level token used by `.t-idle`).

### 4.3 Visual rules

- Height: 22 px (default) / 26 px (lg).
- Border-radius: pill (`--r-pill = 999px`) except identifier chips (square, `--r-1 = 4px`).
- Horizontal padding: 9 px (default) / 6 px (iconOnly).
- Gap between slots: 5 px.
- Font: 11 px / 1 / weight 500 (label), 12 px / 700 (value), 11 px / 600 (add, sub), 10.5 px mono (mono variant).
- `add` colored `--ok`, `sub` colored `--err`, both tabular-nums. `dim` chips render both at `--fg-3` (muted).
- Leading-dot is 6 px filled circle in `currentColor`. Leading-icon is 12 px in `currentColor`. Category-bubble is 14 px filled circle in tone color with knockout-white letter inside (font-weight 800, font-size 9 px). The three are mutually exclusive — one chip never carries more than one leading element.

## 5. Chip kinds (the nine canonical surfaces)

| kind | leading | label | value | deltas | tone | shape | where used |
|---|---|---|---|---|---|---|---|
| **Provider** | provider-icon (12 px) | "Claude" / "GPT" | — | — | claude / gpt | pill | every card header, every lifecycle row, every filter |
| **Activity / round** | — | "brief" / "preflight" / "research plan" / "turn N" / "draft" / "review rN" | — | — | neutral | pill (mono) | every timeline card; lifecycle rows ("round N") |
| **Category counter (dense)** | category-bubble (Q/D/I/C) | — | standing | +raised, −closed | info / warn / err / idle | pill | timeline turn cards; phase headers; critique card header (with label set to "Question" / "Disagreement" / etc. instead of value+deltas — see § 5.1) |
| **Category filter (legend)** | category-bubble | "Questions" / "Disagreements" / "Issues" / "Comments" | total | — | info / warn / err / idle | pill | critique pane filter row only |
| **Status (right-aligned)** | dot OR check-glyph | "running" / "agreed" / "queued" or none | — | — | info / ok / idle | pill | every timeline card (right-aligned); critique card header (right-aligned) |
| **Item lifecycle verb** | — | "raised" / "addressed" / "resolved" / "acknowledged" / "withdrawn" / "capped" | — | — | info / ok / warn / idle / err | pill | lifecycle rows inside expanded critique cards |
| **Modifier** | optional glyph (↻, ⊘, ⚠) | "via hard cap" / "via ghost cap" / "↻ closeout" / "⚠ unverified" / "⚠ ledger drift" / "⊘ N capped" | — | — | neutral / warn / err | pill (mono) | timeline cards (closeout modifier); critique card header (cap reason); category chip suffix (⊘ N) |
| **Sources** | — | "Sources" | count | — | neutral | pill | critique card header when item has linked evidence |
| **Identifier** | — | "Q-plan-c-04" | — | — | neutral | **square** (mono) | inline reference text ONLY — never in card headers |

### 5.1 Category-counter on critique-card header vs timeline

The category chip has two display modes driven by surface context:

- **Timeline / phase-header dense mode**: `[bubble] {standing} +{raised} −{closed}` (no label word). Color and bubble glyph carry the identity. Legend at the top of the critique pane is the disambiguator.
- **Critique-card-header mode**: `[bubble] {label}` (e.g., `[Q] Question`). No numbers — the card IS one item, the kind chip just marks the kind. Same chip primitive, different slot population.

Both modes use the same `<Chip categoryBubble=… tone=…>` JSX; the value/add/sub slots are simply omitted in critique-card-header mode.

### 5.2 Canonical color-to-category map (FIXED — never swap)

- Q = `info` (blue) — "I'm asking"
- D = `warn` (amber) — "I object"
- I = `err` (red) — "there's a problem in the draft"
- C = `idle` (grey) — "soft remark"

### 5.3 Canonical chip order (FIXED — never reorder)

When multiple category chips appear together: **Q → D → I → C**, left to right, always. Enables down-column scanning across consecutive turns.

### 5.4 Bare ✓ status chip

A new chip variant for the "turn completed, agent did not emit AGREED" case. Rendered as:

```jsx
<Chip tone="ok" iconOnly leadingIcon={<CheckGlyph />} ariaLabel="Round completed" />
```

The `CheckGlyph` is a 12 px SVG check (`Icon.Check` already exists). `iconOnly` tightens horizontal padding from 9 px to 6 px so the chip stays compact (~24 px wide). This chip is a pure UX marker — `TurnStatus` in `contract/status.py` remains `IN_PROGRESS | AGREED`; the bare-✓ chip represents the UI affordance of "this card represents a completed turn that was IN_PROGRESS at close." Documented in § 3 governance rules.

## 6. Composition rules

These are invariants the implementation must enforce:

1. **Provider FIRST.** On every card header and every lifecycle row, the provider chip is the leftmost element. No exceptions.
2. **Activity/round SECOND.** Adjacent to provider, always. Never wedged with provider into a combined span.
3. **Category chips THIRD** (when applicable), in fixed Q → D → I → C order.
4. **Modifier chips FOURTH** (when applicable). Closeout, via-cap, unverified, drift, etc.
5. **Status chip RIGHT-ALIGNED**, always. `<span class="spacer" style="flex:1"></span>` separates the left cluster from the status chip.
6. **No public-ID chips in card headers.** The category chip + provider + round disambiguates the item. The orchestrator-assigned ID (`Q-plan-c-04`) is rendered as small mono inline text inside the card body (`.crit-card-id`), copyable but not a primary visual badge.
7. **Status is never bare** on a completed timeline card. Every card carries a right-aligned chip from { `running`, `✓`, `✓ agreed`, `queued` }.
8. **Zero-activity chips render dim** (opacity 0.55) but still present, so category columns align visually across rounds.
9. **The filter row at the top of the critique pane is the legend** and the canonical "what does each bubble mean" reference. Always rendered with full-word labels (Questions / Disagreements / Issues / Comments / All). Never collapses to icon-only.

## 7. Vocabulary cleanup (the dictionary)

Every label, verb, and category currently in JSX/CSS must source from this list. The PR adds an ESLint rule (custom) or a unit test that scans JSX for forbidden literals.

### 7.1 Canonical labels

| context | canonical (allowed) | forbidden (existing → must remove) |
|---|---|---|
| Categories | Questions, Disagreements, Issues, Comments | Claim / Claims, OQ, BD, OI, QCR1 |
| Item lifecycle | raised, addressed, resolved, acknowledged, withdrawn, capped | conceded, answered, noted, accepted, non_blocking_limitation |
| Turn status | running, agreed (preceded by ✓), queued; bare ✓ for "completed" | repair, NEGOTIATING, REVIEWING, APPROVED, BRIEF_OK, BRIEF_NEEDS_INPUT, drafting, responding, thinking |
| Phase status | running, converged (preceded by ✓), errored | — (no removals here; phase chrome lives in 0098/0099) |
| Modifier | via hard cap, via ghost cap, ⊘ N capped, ↻ closeout, ⚠ unverified, ⚠ ledger drift | ghosted N rounds, drift (run-wide) |
| Activity | brief, preflight, research plan, turn N, draft, review rN, AgentInput | — |

### 7.2 Specific JSX/CSS cleanup callsites

- `src/dual_research/ui/static/run-detail.jsx`:
  - `~:6604` — remove "Phase 2 → Question / Disagreement / Claim" comment + dead branch on claim kind.
  - `~:7038` — remove "Question / Disagreement / Issue / Comment / Claim" tuple from kind-label map.
  - `~:7052` — remove `claim: 'Claim'` label entry.
  - `_mapVerdict` (~:7225) — remove inline-text verdict rendering; per-turn rows inside critique cards switch to chip-cluster (see § 8.4).
  - `<StatChip>` (~:3631–3717) — delete; replaced by `<Chip categoryBubble=… value=… add=… sub=…>`.
  - `<StatusInline>` (~:3785–3800) — delete; replaced by `<Chip>` lifecycle-verb variant.
  - `<ConvergedChip>` (~:3759–3783) — delete; replaced by `<Chip tone="ok" leadingIcon={<Check/>} label="agreed">`.
  - `<GhostedRoundsBadge>` (~:7120–7130) — delete entirely (vocabulary "ghosted N rounds" gone per § 7.1).
  - `<SearchChip>` — delete; web-search indicator becomes a Modifier chip if it stays at all (see § 11 risks).
  - `<CritiqueTypeFilter>` (~:6375–6395) — replace `<Tab>` rendering with `<Chip>` filter primitives. The TabGroup component is no longer needed for this surface.
  - `qref qref-full` (~:984–993) — replace the combined provider+activity span with two adjacent `<Chip>` elements per § 6.1/§ 6.2.
- `src/dual_research/ui/static/components.css`:
  - `.drift-chip` (~:6258) — remove the CSS class entirely; the run-wide drift chip is removed.
  - `.stats-chip` / `.stat-chip` / `.converged-chip` / `.ghosted-rounds-badge` / `.status-inline` — remove if present (canonicalize on `.chip`).
  - `.qref` / `.qref-full` / `.qref-by` / `.qref-n` — remove; provider+activity now rendered as two `<Chip>` elements, not a single composite span.
  - `.md-status` and the `.md-status--*` modifiers (`~:1356-1370`) — collapse into the unified `.chip.t-*` tone system. The `--running` / `--converged` / `--drift` / `--errored` / `--idle` variants are reachable as `<Chip tone="info|ok|warn|err|idle">`.
- `src/dual_research/ui/disagreements.py`:
  - `_TERMINAL_STATES` (`~:76`) — remove `"non_blocking_limitation"`, `"conceded"`, `"accepted"`. New protocol uses contract-module lifecycle exclusively.
  - `_to_terminal_action()` (`~:395`, `~:402`) — remove "conceded" return value.
  - The disagreement-explorer's progression renderer is migrated to use `<Chip>` lifecycle-verb variants instead of inline text + verdict label.
- `src/dual_research/orchestrator/repair.py` — left intact (legacy compatibility for in-flight pre-0114 runs); this spec does NOT delete the file. The CSS `repair` chip class is what gets removed.

## 8. Surface-by-surface migration

### 8.1 Timeline turn card (Phase 0 / 2 / 4 interaction phases)

Replace the current `<header className="qt-head">` block (`run-detail.jsx:982-1033`) with:

```jsx
<header className="tl-card-head">
  <Chip tone={providerTone} leadingIcon={<AgentIcon agent={agent} />} label={agentName} />
  <Chip mono tone="neutral" label={activityLabel} />
  {modifierChips}             {/* ↻ closeout, ⚠ ledger drift if any */}
  {chipCategories.map(cat => (
    <Chip
      key={cat}
      tone={CATEGORY_TONE[cat]}
      categoryBubble={CATEGORY_BUBBLE[cat]}
      value={categories[cat].standing}
      add={categories[cat].raised}
      sub={categories[cat].closed}
      trailingSuffix={categories[cat].capped > 0 ? `⊘ ${categories[cat].capped}` : null}
      dim={categories[cat].raised + categories[cat].closed === 0}
    />
  ))}
  <span className="spacer" />
  <StatusChip kind={statusKind} />     {/* running | ok-check | ok-check-agreed | queued */}
</header>
```

Where `chipCategories` is `['questions', 'disagreements']` for Phase 0 / 2 and `['questions', 'disagreements', 'issues', 'comments']` for Phase 4 (already encoded in `run-detail.jsx:939-941`). `CATEGORY_TONE` is the canonical map from § 5.2; `CATEGORY_BUBBLE` is `{questions:'Q', disagreements:'D', issues:'I', comments:'C'}`.

Status logic:

```jsx
function StatusChip({ item, isLive }) {
  if (isLive) return <Chip tone="info" leadingDot label="running" />;
  if (item.agreed) return <Chip tone="ok" leadingIcon={<CheckGlyph/>} label="agreed" />;
  if (item.status === 'queued') return <Chip tone="idle" leadingDot label="queued" />;
  return <Chip tone="ok" iconOnly leadingIcon={<CheckGlyph/>} ariaLabel="Round completed" />;
}
```

### 8.2 Phase header summary

The header above each phase's set of turn cards renders the same compact-form category chips, but aggregated across both agents and showing the phase-end state (see [models.py:393](src/dual_research/ui/models.py:393) `PhaseCategoryStats`). Replaces existing phase-header rendering at the top of each `.tl-phase` block (`run-detail.jsx:752-829`).

```jsx
<div className="tl-phase-head">
  <span className="tl-phase-name">{phaseTitle}</span>
  <span className="tl-phase-meta">· {duration} · {roundsLabel}</span>
  <span className="spacer" />
  {chipCategories.map(cat => <Chip … />)}      {/* same shape as 8.1 */}
</div>
```

The summary chips fit on one line because each chip is ~70-90 px (provider + round absent on phase header).

### 8.3 Critique pane filter row (the legend)

Replace `<CritiqueTypeFilter>` (`run-detail.jsx:6375-6395`) with a `<Chip>` row:

```jsx
<div className="crit-filter-row">
  {CATEGORIES.map(cat => (
    <Chip
      key={cat}
      tone={CATEGORY_TONE[cat]}
      categoryBubble={CATEGORY_BUBBLE[cat]}
      label={CATEGORY_LABEL_PLURAL[cat]}      {/* "Questions" / "Disagreements" / … */}
      value={counts[cat]}
      onClick={() => setActiveCategory(cat)}
      data-active={activeCategory === cat}
    />
  ))}
  <Chip tone="neutral" label="All" value={total} />
  <span style={{ width: 12 }} />
  <Chip tone="info" leadingDot label="Open" value={openCount} />
  <Chip tone="ok" leadingDot label="Resolved" value={resolvedCount} />
</div>
```

Active state shows via `[data-active="true"]` CSS rule — typically a 2 px outline ring in tone color.

### 8.4 Critique card header

Replace `CardHeadline` (`run-detail.jsx:7046-7105`) with:

```jsx
<div className="crit-card-head">
  <Chip tone={providerTone} leadingIcon={<AgentIcon agent={item.raiser}/>} label={agentName(item.raiser)} />
  <Chip tone={CATEGORY_TONE[item.kind]} categoryBubble={CATEGORY_BUBBLE[item.kind]} label={CATEGORY_LABEL_SINGULAR[item.kind]} />
  <Chip mono tone="neutral" label={`raised in r${item.raised_round}`} />
  {item.evidence.length > 0 && <Chip tone="neutral" label="Sources" value={item.evidence.length} />}
  {item.capped_via && <Chip mono tone="neutral" label={`via ${item.capped_via.replace('_', ' ')}`} />}
  <span className="spacer" style={{ flex: 1 }} />
  <Chip tone={STATE_TONE[item.current_state]} leadingDot label={item.current_state} />
</div>
```

Where `CATEGORY_LABEL_SINGULAR = {question:'Question', disagreement:'Disagreement', issue:'Issue', comment:'Comment'}`.

The public-ID chip is removed. The ID renders as small mono inline text below the body via `<div className="crit-card-id">id: {item.id}</div>` — copyable but not a primary visual badge.

### 8.5 Lifecycle rows inside expanded critique card

Replace today's inline-text verdict rendering (`run-detail.jsx:7177-7280`) with chip-cluster rows:

```jsx
{item.transitions.map((t, i) => (
  <div key={i} className="lc-row">
    <div className="lc-row-chips">
      <Chip tone={providerTone(t.actor)} leadingIcon={<AgentIcon agent={t.actor}/>} label={agentName(t.actor)} />
      <Chip mono tone="neutral" label={`round ${t.round}`} />
      <Chip tone={STATE_TONE[t.to_state]} label={lifecycleVerb(t.from_state, t.to_state)} />
    </div>
    <div className="lc-row-body">"{t.reason}"</div>
  </div>
))}
```

`lifecycleVerb(from, to)` maps a transition to the appropriate canonical verb. Implementation:

| transition | verb |
|---|---|
| `open → addressed` | addressed |
| `open → withdrawn` | withdrawn |
| `addressed → resolved` | resolved |
| `addressed → open` (counter-argued) | raised again |
| `addressed → withdrawn` | withdrawn |
| `addressed → acknowledged` (mutual) | acknowledged |
| `* → capped` | capped |
| (item creation) | raised |

Defined in a small helper module — likely `src/dual_research/ui/static/lifecycle-verbs.js` (new tiny file).

### 8.6 Critique-pane header (run-level)

Remove the custom `.drift-chip` rendering (`~:6258`). Replace with just the canonical pane-title text. If a future spec wants to surface drift in chrome, it does so per spec 0119 § 11 (Risks) — likely as a `<Chip tone="warn" leadingIcon={<Alert/>} label="ledger drift" value={N} />` if and when it's ever needed.

### 8.7 Phase 1 / Phase 3 cards (research plan / draft)

No category chips (Phase 1 and Phase 3 raise nothing per protocol). The card renders:

```jsx
<div className="tl-card is-resolved">
  <Chip tone={providerTone} leadingIcon={<AgentIcon …/>} label={agentName} />
  <Chip mono tone="neutral" label={activityLabel} />
  {/* optional: <Chip tone="warn" label="⚠ ledger drift" /> if drift fired */}
  <span className="spacer" />
  <StatusChip … />
</div>
```

### 8.8 Phase 0 brief card (shared, no agent)

The shared brief card on Phase 0 input renders:

```jsx
<div className="tl-card is-resolved">
  <Chip tone="neutral" leadingIcon={<Icon.FileDocument />} label="brief" />
  <span className="spacer" />
  <Chip tone="ok" iconOnly leadingIcon={<CheckGlyph/>} ariaLabel="Brief loaded" />
</div>
```

`Icon.FileDocument` exists in `icons.jsx`.

## 9. Files touched (exhaustive list)

| file | change | sections |
|---|---|---|
| `src/dual_research/ui/static/shared.jsx` | upgrade `<Chip>` component with new slots; add `<CheckGlyph>` SVG inline; add `lifecycleVerb()` helper or extract to new module | §4, §5.4, §8.5 |
| `src/dual_research/ui/static/run-detail.jsx` | extensive — see § 7.2 + § 8.1-8.8 for each callsite | §7, §8 |
| `src/dual_research/ui/static/components.css` | remove `.drift-chip`, `.qref*`, legacy chip variants; add `.cat-bubble`, `.t-claude`, `.t-gpt`, `.add`, `.sub`, `.chip-icon-only` rules; collapse `.md-status--*` into `.chip.t-*` | §4.2, §7.2 |
| `src/dual_research/ui/static/tokens.css` | promote `--idle` to a top-level token (currently only `--p-idle` exists scoped to status palette) | §4.2 |
| `src/dual_research/ui/static/design-language.jsx` | rebuild the in-app chip gallery to show all 9 chip kinds with the new vocabulary | §5 |
| `src/dual_research/ui/static/icons.jsx` | no changes; existing icons are sufficient | — |
| `src/dual_research/ui/static/live-data.jsx` | no changes; `item.stats.categories.{questions,disagreements,issues,comments}` already populated by aggregator | §5 |
| `src/dual_research/ui/disagreements.py` | remove "conceded" / "accepted" / "non_blocking_limitation" from `_TERMINAL_STATES`; remove related branches in `_to_terminal_action` | §7.2 |
| `src/dual_research/ui/static/lifecycle-verbs.js` (new) | small helper module exporting `lifecycleVerb(from, to)` per § 8.5 table | §8.5 |
| `design-system/SPEC.md` | new top-level section "Badge governance" capturing § 4-7 of this spec for designer reference | §10 |
| `tests/test_ui_aggregator.py` | additions per § 12 | §12 |
| `CHANGELOG.md` | entry under `[Unreleased]` | — |
| `src/dual_research/__init__.py` | version bump to `1.4.0` at PR-merge time | — |
| `src/dual_research/ui/static/index.html` | static cache-bust bump at PR-merge time | — |

No backend files. No `pyproject.toml`. No migrations. No new dependencies.

## 10. Design system documentation

`design-system/SPEC.md` gains a section "Badge governance" with:

- The 9 chip kinds (§ 5 of this spec)
- The 8 tones + token mapping (§ 4.2)
- The 4 composition rules (§ 6)
- The vocabulary tables (§ 7.1)
- Reference to this spec for the implementation source-of-truth

This makes the design system the canonical reference future specs read FROM rather than write into. Subsequent UI specs should import the chip kinds and refer to them by name (`category-counter`, `lifecycle-verb`, etc.) rather than inventing local chip designs.

## 11. Risks

- **Color-coded category tones overlap with status tones.** Issues = `err` red could read like an error chip; Comments = `idle` grey could read like queued. Mitigation: category chips always carry a category-bubble (never appears on status chips); shape of the leading element disambiguates. Plus the legend at top of critique reinforces meaning. If user testing surfaces confusion, the fallback is to bump Issues to `warn` and route Disagreements to a new `--disagree` token.
- **Letter-bubble accessibility.** Screen readers should announce "Questions" not "Q". Mitigation: every chip with a category-bubble has `aria-label="Questions"` (or whichever full word) sourced from `CATEGORY_LABEL_PLURAL[kind]`. The visible Q glyph is decorative; the aria-label is canonical.
- **0115's "never abbreviate" rule is being evolved, not abandoned.** The single-letter glyph inside a colored bubble is treated as a designed icon, with the full word always one scroll away in the filter legend. This spec explicitly captures the rule evolution (§ 4-5) so future readers understand the intent.
- **Compact chips on Phase 4 cards (4 categories + provider + round + status).** Measured: at 600 px column width the row is ~580 px and fits; at 500 px it wraps to a second row gracefully. Below 400 px wrap becomes ugly. Mitigation: the timeline column has a `min-width: 480 px` via the pane grid (already present); if pushed narrower the wrap is acceptable. Not a blocker.
- **`<SearchChip>` retirement removes the web-search audit indicator.** That chip currently shows "consulted N sources" on turns that ran with search enabled. Decision pending: either fold into a Modifier chip (`⚠ search` or similar) or punt. § 13 open-questions captures this.
- **Legacy run rendering.** Pre-0114 runs render via the legacy code path (per 0115 § "legacy mode"). This spec touches new-protocol render only; the legacy renderer continues to work. Snapshot tests on a fixture legacy run guard against accidental shared-component regressions.
- **Spec 0120 dependency.** This spec must merge before 0120 (turn-modal Open Questions / Claims rework) can use the canonical chip primitive. If 0119 slips, 0120 can be drafted in parallel but cannot merge first.
- **Compile-time enforcement of vocabulary.** A custom ESLint rule (or a unit test that grep-scans JSX) detecting forbidden literals ("conceded", "claim", "ghosted N", "repair" in chip context) is suggested. Without it, regressions are easy. The implementation PR should land at least the grep-test version.

## 12. Test plan

- [ ] **Unit — `<Chip>` component.** Each slot renders correctly: leadingDot present iff prop set; categoryBubble carries correct letter + tone; add/sub render in green/red with `+`/`−` signs; trailingSuffix renders; iconOnly tightens padding; dim applies opacity 0.55.
- [ ] **Unit — `lifecycleVerb(from, to)`** maps every transition in `contract/lifecycle.py:TRANSITIONS` to the expected verb per § 8.5 table.
- [ ] **Snapshot — timeline turn card** for each phase (0 / 1 / 2 / 3 / 4) with realistic `item.stats.categories` fixtures. Asserts chip order (provider → activity → categories Q→D→I→C → status), color tones, dim state on zero-activity chips.
- [ ] **Snapshot — critique card header** in each lifecycle state (open / addressed / resolved / acknowledged / withdrawn / capped). Asserts no public-ID chip in header, provider chip leftmost, status chip rightmost.
- [ ] **Snapshot — lifecycle row** for each canonical transition. Asserts provider + round + verb chip cluster + indented body.
- [ ] **Snapshot — critique pane filter row** with non-zero counts in each category. Asserts full-word labels, active-state outline ring.
- [ ] **Snapshot — phase-header summary** for Phase 0 / 2 / 4 with aggregated `PhaseCategoryStats`. Asserts one-line fit at the typical pane width.
- [ ] **Vocabulary scan** — grep-test in CI that scans `run-detail.jsx`, `shared.jsx`, `disagreements.py` for forbidden literals: `'conceded'`, `'answered'`, `'noted'`, `'Claim'` (with capital C, to avoid false positives), `'QCR1'`, `'OQ'`, `'BD'`, `'OI'`, `'repair'` (in chip-label context), `'ghosted'` (in chip-label context).
- [ ] **Manual — narrow column.** Resize the timeline column to 600 px / 500 px / 400 px; verify category chips wrap gracefully and never overflow.
- [ ] **Manual — color accessibility.** Each chip tone (info / ok / warn / err / idle) has contrast ratio ≥ 4.5:1 against `--bg-2`. Measure with a contrast checker.
- [ ] **Manual — keyboard accessibility.** Category filter chips are focusable, Enter/Space toggles them, focus ring visible. Lifecycle-row provider chips do not steal focus (they're decorative).
- [ ] **Regression — legacy run.** Open a pre-0114 fixture run in the UI; verify the legacy renderer still produces a readable timeline + critique pane.
- [ ] **`uv run pytest tests/ -q`** → green.

## 13. Acceptance criteria

- [ ] `git grep -l "StatChip\|StatusInline\|ConvergedChip\|GhostedRoundsBadge\|drift-chip"` returns 0 hits in `src/dual_research/ui/static/`.
- [ ] `git grep "claim" src/dual_research/ui/static/run-detail.jsx` returns 0 hits except in comments referring to the legacy renderer for back-compat (which lives elsewhere).
- [ ] `git grep -E "'(conceded|answered|noted)'"` returns 0 hits in `src/dual_research/ui/static/`.
- [ ] Every `.tl-card` in a Phase 0 / 2 / 4 turn renders a right-aligned status chip (running, ✓, ✓ agreed, or queued). DOM probe: `document.querySelectorAll('.tl-card:not(:has(.chip[data-role="status"]))').length === 0`.
- [ ] Every critique-card header begins with a provider chip (DOM: `.crit-card .crit-card-head > .chip:first-child[class*="t-claude"], .crit-card .crit-card-head > .chip:first-child[class*="t-gpt"]`). No public-ID chip in any critique card header (DOM: `.crit-card .crit-card-head .chip.mono.square` count is 0).
- [ ] The critique pane filter row renders `Questions / Disagreements / Issues / Comments / All` as full-word labels (no abbreviations).
- [ ] Computed contrast ratio on `.chip.t-info`, `.t-ok`, `.t-warn`, `.t-err`, `.t-idle` against `.tl-card` background ≥ 4.5:1.
- [ ] `design-system/SPEC.md` contains a "Badge governance" section linking to this spec.

## 14. Out of scope (explicit)

- Turn modal Open Questions / Claims panel restructure → **spec 0120** (next).
- Run-list page chip migration → future spec.
- Header chrome chip migration → future spec.
- Consumption-tab chip migration → future spec.
- Sources widget visual changes (kept as designed per 0115).
- Backend / protocol / contract module changes.
- New data fields on Item / TurnCategoryStats.
- Migration of pre-0114 historical run artifacts.
- Version bump + cache-bust deferred to the merge commit (per current project pattern, see 0116 § 5).

## 15. Open questions

- **Q1.** Is the Issues=err-red / Comments=idle-grey color mapping acceptable, or should I try a less-alarming alternative for Issues? Default in this spec: red.
- **Q2.** Should clicking a category chip on a timeline turn card open a filtered critique view scoped to that category (and ideally to that round)? Spec 0115's uniformity invariant implies yes; this spec scopes it but leaves the wiring as a § 8.3 enhancement that can ship in the same PR or land separately.
- **Q3.** Should the bare `✓` chip on a completed turn card include the round number on hover (tooltip), or stay completely opaque? Default in this spec: aria-label="Round completed" only.
- **Q4.** Web-search audit indicator (`<SearchChip>`) — retire entirely or fold into a Modifier chip? If retained, where? Default in this spec: fold into a Modifier chip if it stays at all; explicit deferral to the implementation PR.
- **Q5.** Ledger-drift modifier chip when drift fires on a turn — verify there's still an event in the new event stream the UI can hook to. If not, this is a no-op slot until the orchestrator emits it. Default in this spec: chip primitive exists; emission is best-effort and falls back silently.

## 16. Backend touched?

**no.** Pure frontend + design-system docs.
