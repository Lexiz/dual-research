---
spec: 0121
title: How-It-Works overlay + Changelog tab — full content & component rewrite
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.5.0
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0121 — How-It-Works overlay + Changelog tab — full content & component rewrite

> Ship bucket: **Documentation surface — frontend only.**
> Depends on: **0114** (Deep Research protocol), **0115** (Item / SourceRow), **0116** (modal layout), **0117** (artifact registry + display names), **0118** (consumption + canonical-piece cost model), **0119** (Chip primitive + canonical vocabulary), **0120** (turn-modal items panel).
> Complexity: **L** for the content rewrite, **M** for the JSX migration onto design-system primitives, **S** per diagram (×7).
> Targeted version bump: **MINOR (1.4.x → 1.5.0)** — significant user-visible change to a top-level surface, but no API / contract / migration changes. The overlay is the *first thing* a new user is shown; rewriting it qualifies as a feature.

---

## 1. Context

The `How it Works` overlay is the in-app explainer the user opens from the right-side menu and from the onboarding tour. It is the single document that tells a brand-new user *"what does Dual Research actually do?"* and walks the existing user through the protocol, the categories, the cost model, and the per-release changes.

It is currently catastrophically out of date.

**Quantified drift.** A line-by-line audit of `src/dual_research/ui/static/how-it-works.jsx` (1,823 lines) versus the live protocol (specs 0114 → 0120) found that **8 of the 9 rendered sections describe a protocol that no longer exists.** Specifically:

- **Phase vocabulary is two generations stale.** The page still calls the phases `Preflight / Independent research / Plan negotiation / Drafting / Review loop`. The actual phase names per spec 0114 are `input / research-plan / negotiate-plan / draft / review-draft`. The page's `PhaseStrip` widget calls the phases `P0 · Preflight · agreed_interpretation`, `P2 · Negotiate · agreed_plan + drafter`, etc. — every label is wrong.
- **The `claim` item kind is referenced everywhere.** Spec 0114 §"Categories" removed it: *"The `claim` kind is **removed**. Items previously in the `## Claims I expect the other agent might dispute` section are gone — the new prompts do not ask for them."* Spec 0119 §7.1 enforced this in code with a vocabulary-scan test. The overlay still talks about claims, `D-N` identifiers as the only structured-item type, `AGREED_PLAN SHA-256 plan-hash match` as the convergence condition — all pre-0114.
- **The four-category Q/D/I/C taxonomy is absent.** Spec 0119 standardised every chip on a fixed Q→D→I→C ordering with fixed tones (Q=info, D=warn, I=err, C=idle). The overlay's `Tk` legend uses pre-0119 keys (`brief / d1 / d2 / hist / plan / draft / histp`) and never mentions the four-category model.
- **The cost story is entirely pre-0118.** The `ContextGrowthBars` widget shows per-piece stacked bars labelled `P0 / P1, P2 r1, P2 r3, P2 r6, P3 drafter` with a `CACHE_BREAKPOINT` marker — terminology that doesn't exist post-0118. Spec 0118 introduced canonical-piece aggregation, the `System prompt` aggregate row, the proportional-cost formula (`pieceCost = (pieceTokens / billedInputTokens) × totalInputCost`), and the cache-reuse stripe rendering. None of that is in the overlay.
- **The bundled SVG (`/diagrams/deep-research-pipeline.{light,dark}.svg`) is the only correct artifact on the page**, but it sits inside a `ProtocolOverviewFold` whose surrounding prose describes a different protocol from the one the SVG depicts.
- **Bypasses the design system entirely.** The overlay defines its own `AgentDisc`, `Tk`, `CallBox`, `LifecycleRow`, `ChatLifecycle`, `Legend`, `ComparePanel` (unused), `Section` (unused) — none of them reach for the canonical `<Chip>` primitive from spec 0119, the `<Card>` from spec 0094, the `<CollapsibleSection>` from spec 0084, or the `<Modal>` from spec 0096. The overlay's chrome is `<Modal>`; everything inside is bespoke.
- **The Changelog tab is missing the last two releases.** `VERSION_NOTES` stops at v1.2.0 (spec 0117). Specs 0118 (consumption + cost rework, v1.3.0) and 0119 (badge governance, v1.4.0) — *both shipped on 2026-05-20* — are not represented. Spec 0120 (turn-modal items panel, v1.4.1) is queued and also needs an entry on land.

**Why this matters.** The overlay is reached three ways: (a) the onboarding tour calls it out as step 1 ("Click here to learn how Dual Research works"), (b) the right-side menu's first item is "How it works", (c) every changelog-deep-link from a release announcement lands on the Changelog tab inside it. A new user opening Dual Research today is shown a document that describes a protocol from two months ago, with chip vocabulary that doesn't match the chips on every other surface they're about to see, and a cost model that doesn't match the consumption tab they'll open next. The drift between the overlay and the product is now so wide that the overlay actively misleads.

The companion documents:

- **`/Users/alexlisitzky/dual-research/specs/0117-deep-research-artifact-naming-and-how-it-works.md`** — declared the artifact registry, established the SVG-embed pattern in the overlay, and explicitly listed which inline-JSX diagrams in `how-it-works.jsx` needed to be redrawn. That spec produced the bundled `deep-research-pipeline.svg` pair but left the surrounding prose untouched. **This spec finishes 0117's deferred work.**
- **`/Users/alexlisitzky/dual-research/specs/0119-badge-governance.md`** — the canonical chip vocabulary this spec applies to every category, lifecycle verb, and status chip in the new overlay.
- **`/Users/alexlisitzky/dual-research/specs/0118-deep-research-consumption-and-cost-tracking.md`** — the canonical cost model the new "Cost & consumption" section explains.
- **`/Users/alexlisitzky/dual-research/specs/0114-deep-research-protocol.md`** — the source-of-truth for every phase name, item kind, anchor format, lifecycle state, and escape-hatch mechanic the new overlay describes.

---

## 2. Goals

1. **Replace 100 % of the in-overlay prose** with content that matches the live protocol as of specs 0114 → 0120. Every paragraph is rewritten; no salvaged-and-tweaked sentences from the pre-0114 version.
2. **Redraw every diagram from scratch.** Seven new diagrams via the `diagram` skill, light + dark each (14 SVGs). The legacy `deep-research-pipeline.{light,dark}.svg` is **not referenced** by the new overlay. The legacy inline-JSX widgets (`PhaseStrip`, `NegotiationRoundDiagram`, `ContextGrowthBars`, `ChatLifecycle`, `LifecycleRow`, `CallBox`, `TldrCards`, `ComparePanel`, `Section`, `Legend`) are **deleted**.
3. **Compose everything out of existing design-system primitives.** No new chip variants, no new card variants, no new modal sub-types. The new overlay reaches for `<Chip>`, `<Card>` / `<CardBody>`, `<CollapsibleSection>`, `<Modal>`, `<Tab>` / `<TabGroup>`, `<BrandMark>`, `<SourceRow>` — all from `shared.jsx` and per the spec-0119 § 4 governance rules. Three small CSS utilities (`.hiw-note`, `.hiw-table`, `.hiw-code`) are added to `components.css` to fill known design-system gaps (see § 4.3).
4. **Restructure the IA** to follow the user's mental model post-0114: *Overview → Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Item taxonomy → Lifecycle → Convergence → Cost*. Preserve the *shape* of the original (overview → per-phase → mechanics → cost → version notes) but rename, reorder, and re-content as needed.
5. **Backfill the Changelog tab** with entries for v1.3.0 (spec 0118), v1.4.0 (spec 0119), and v1.4.1 (spec 0120, on land). Rewrite the `ChangelogEntry` component to use design-system primitives (`<Card>`, `<Chip>`, `<CollapsibleSection>`) instead of bespoke `.changelog__entry` grid. Add a screenshot affordance per entry — for the three landed-today entries, embed a captured screenshot of the surface the spec affected, so the changelog reads as *"this is what changed, and here's what it looks like."*
6. **Ship a clickable standalone mockup** (`design-system/audits/2026-05-20-hiw-rework/mockup.html`) of the full new overlay — collapsibles, theme toggle, every diagram embedded — as the visual reference for the implementation. The mockup ships with the spec and lives in the `audits/` directory; the implementation in `how-it-works.jsx` + `components.css` should render the same artifact in the live app.
7. **Ship the implementation in the same PR as the spec.** This is a single merge-able pass: spec doc + 14 SVGs + mockup HTML + the actual `how-it-works.jsx` rewrite + the `components.css` additions + the cache-bust bump + the `CHANGELOG.md` entry. No "design now, implement later" split. § 10–13 contain the drop-in JSX / CSS / data / deletion list.

## 3. Non-goals

- **No backend / contract / parser / orchestrator changes.** Pure frontend documentation surface.
- **No new design-system primitives.** The three new CSS utilities (`.hiw-note`, `.hiw-table`, `.hiw-code`) are page-scoped fill-ins for known gaps, not new design-system components. If they prove generally useful, a follow-up spec promotes them.
- **No changes to the onboarding tour, the right-side menu, or the modal-open trigger** that surface this overlay. Those reach the overlay; the overlay is what we rewrite. (The onboarding tour positioning bug is patched separately as a hotfix; cross-referenced in § 20.)
- **No reuse of the bundled `deep-research-pipeline.{light,dark}.svg`.** They stay in `diagrams/` (legacy, may be deleted by a future cleanup spec) but the new overlay does not reference them.

---

## 4. Information architecture

### 4.1 Overlay shell (unchanged from spec 0102 + 0117)

The overlay is a `<Modal>` (`variant="rich"`, 1080 px). Header carries title `How it works` and a two-tab `<TabGroup variant="solid">`: **How it works** (default) / **Changelog**. Right-side sticky menu (`.hiw-overlay__menu`) lists section anchors with smooth-scroll on click. Scrim click + Escape close. Spec 0102 + 0117 already wired all of this; we don't touch the shell.

### 4.2 New section list (the "How it works" tab)

| # | Section | Anchor id | Default open? | Contains a diagram? |
|---|---|---|---|---|
| 1 | Protocol overview | `hiw-overview` | yes | Diagram 1 (full pipeline) |
| 2 | Phase 0 — Input | `hiw-p0` | no | Diagram 2 (per-phase input stack, the *generic* form) |
| 3 | Phase 1 — Research plan | `hiw-p1` | no | (reuses Diagram 2 with the P1 variant noted in caption) |
| 4 | Phase 2 — Negotiate plan | `hiw-p2` | no | (reuses Diagram 2 with the P2 variant noted in caption) |
| 5 | Phase 3 — Draft | `hiw-p3` | no | (reuses Diagram 2 with the P3 variant noted in caption) |
| 6 | Phase 4 — Review draft | `hiw-p4` | no | (reuses Diagram 2 with the P4 variant noted in caption) |
| 7 | How turns are reviewed (modal anatomy) | `hiw-modal` | no | Diagram 7 (left-pane + right-pane structure post-0116/0120) |
| 8 | Item taxonomy & categories | `hiw-items` | no | Diagram 4 (category-bubble + chip composition reference) |
| 9 | Item lifecycle | `hiw-lifecycle` | no | Diagram 3 (state machine + mutual-ACK handshake) |
| 10 | Convergence & escape hatches | `hiw-converge` | no | Diagram 6 (closeout → ghost cap → hard cap branches) |
| 11 | Cost & consumption | `hiw-cost` | no | Diagram 5 (token sources → canonical-piece roll-up → proportional cost) |

Sections 2–6 use the same generic "phase shape" template (lede + inputs + outputs + caps + caption-tagged variant of Diagram 2) so the user learns the shape once and the per-phase deltas read fast.

### 4.3 Design-system primitives used (and three small fill-ins)

| Primitive | Source | Used for |
|---|---|---|
| `<Modal variant="rich">` | `shared.jsx` (spec 0096) | Overlay shell (unchanged) |
| `<TabGroup variant="solid">` + `<Tab>` | `shared.jsx` | Top tabs (How it works / Changelog) (unchanged) |
| `<CollapsibleSection persistKey="hiw:…">` | `shared.jsx` (spec 0084) | Every section (1–11) and every changelog entry |
| `<Card variant="outlined">` + `<CardBody>` | `shared.jsx` (spec 0094) | Section bodies, changelog entries, callout containers |
| `<Chip>` (slot API) | `shared.jsx` (spec 0119) | Every category bubble, provider mark, lifecycle verb, status chip, and counter on the page |
| `<BrandMark name="claude|gpt" size={12}>` | `shared.jsx` | Leading icon on provider chips |
| `<SourceRow record={…}>` | `run-detail.jsx` (spec 0115) | Embedded evidence references in the "Cost" and "Item lifecycle" sections (citing the underlying spec PR + the design-system page) |
| `<Button variant="ghost" size="sm">` | `shared.jsx` | Section "Read more / Collapse" toggles where the `<CollapsibleSection>` chevron isn't sufficient |
| `.crit-section-title` (small-caps label) | `components.css` (spec 0120) | Sub-section labels inside each section (e.g. *Inputs*, *Outputs*, *Caps*) |

**Three new CSS utilities** added to `components.css` to fill known gaps (per the component cheat-sheet); each is < 10 lines:

```css
/* spec-0121: page-scoped fill-ins for known design-system gaps */
.hiw-note {
  border-left: 3px solid var(--info);
  background: var(--bg-2);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-2);
  margin: var(--s-3) 0;
  font-size: var(--t-body);
  color: var(--fg-1);
}
.hiw-note[data-tone="warn"] { border-left-color: var(--warn); }
.hiw-note[data-tone="err"]  { border-left-color: var(--err);  }
.hiw-note[data-tone="ok"]   { border-left-color: var(--ok);   }
.hiw-note__label {
  font-size: var(--t-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fg-3);
  margin-right: var(--s-2);
}

.hiw-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--t-body);
}
.hiw-table th,
.hiw-table td {
  text-align: left;
  padding: var(--s-2) var(--s-3);
  border-bottom: 1px solid var(--border-1);
  vertical-align: top;
}
.hiw-table th {
  background: var(--bg-2);
  font-weight: var(--w-semi);
  color: var(--fg-2);
  font-size: var(--t-meta);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.hiw-table td.num { font-variant-numeric: tabular-nums; }

.hiw-code {
  font-family: var(--mono);
  font-size: var(--t-mono);
  background: var(--bg-2);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-2);
  overflow-x: auto;
  margin: var(--s-3) 0;
  color: var(--fg-1);
  border: 1px solid var(--border-1);
}
```

All three are token-driven — they pick up `body.light` overrides for free.

---

## 5. Per-section design

This is the detailed brief for each section of the new overlay. Each subsection gives: the **target prose**, the **JSX skeleton**, the **chip composition** for any chips on the section, and a pointer to the diagram (if any).

### 5.1 — Section 1: Protocol overview (`hiw-overview`, default open)

**Lede (verbatim, ≤ 80 words):**

> Dual Research runs two large language models — **Claude** and **GPT** — through a six-phase protocol on a single brief, in parallel where possible and one-after-the-other where the next phase needs the previous phase's output. Both agents see the same brief, the same prior turns, and the same ledger of unresolved items. The orchestrator is deterministic; the agents are not. A run ends with a single approved document and an audit trail of every claim, disagreement, and source.

**Body (collapsible TL;DR card cluster — three short cards):**

| Card | Title | Body (≤ 40 words) |
|---|---|---|
| A | Two agents, one document | Two providers research the same brief. They negotiate a plan, one of them drafts, both review. The output is one document — not two. |
| B | Every claim has a source | Each agent cites the URLs it consulted. Every cited URL is checked against a recorded web-search event; fabricated sources are flagged with `⚠ unverified`. |
| C | The orchestrator decides when phases end | Agents propose to converge; the orchestrator enforces caps and closeout. No agent can extend a phase past its hard cap. |

**Diagram 1 — full pipeline.** Embedded below the TL;DR cards, full-width `.hiw-diagram` wrapper. Theme-aware `<img>` swap (light when `body.light`, dark otherwise; `MutationObserver` re-renders on class change). Path: `/diagrams/how-it-works/01-pipeline.{light,dark}.svg?v=0121`.

**Caption (under the diagram, `--t-meta` / `--fg-3`):**

> Six phases, left to right. **Phases 0, 1, 2, 4** run both agents in parallel; **phase 3** runs one drafter. Phases 0 / 2 / 4 are multi-round (each round = one turn per agent + an orchestrator update step). The "Agreed interpretation", "Agreed plan + drafter", "Agreed draft acceptance" capsules are the artifacts each multi-round phase emits when both agents reach AGREED with zero non-terminal items.

**JSX skeleton:**

```jsx
<CollapsibleSection title="Protocol overview" defaultOpen persistKey="hiw:overview">
  <p className="lede">Dual Research runs two large language models …</p>
  <div className="hiw-tldr">
    <Card variant="outlined"><CardBody><h4>Two agents, one document</h4><p>…</p></CardBody></Card>
    <Card variant="outlined"><CardBody><h4>Every claim has a source</h4><p>…</p></CardBody></Card>
    <Card variant="outlined"><CardBody><h4>The orchestrator decides when phases end</h4><p>…</p></CardBody></Card>
  </div>
  <PipelineDiagram />  {/* theme-aware <img> wrapper */}
  <p className="hiw-caption">Six phases, left to right. …</p>
</CollapsibleSection>
```

`PipelineDiagram` is a 12-line component that reads `body.classList` and swaps `src`. See § 7.1 for the contract.

---

### 5.2 — Sections 2–6: per-phase pages

Each phase section follows the same template — only the content differs. The template:

```jsx
<CollapsibleSection
  title="Phase N — <name>"
  persistKey="hiw:phaseN"
  renderTitle={() => (
    <span className="hiw-section-title">
      Phase N — {name}
      <Chip mono tone="neutral" label={`soft ${softCap} / hard ${hardCap} rounds`} />
      <Chip mono tone="neutral" label={isParallel ? "parallel" : "single drafter"} />
    </span>
  )}
>
  <p className="lede">{lede}</p>

  <div className="crit-section-title">Inputs</div>
  <ul className="hiw-input-list">
    {inputs.map(i => <li key={i.id}>
      <Chip mono shape="square" tone="neutral" label={i.canonicalId} />
      <span className="hiw-input-name">{i.displayName}</span>
      {i.note && <span className="hiw-input-note">{i.note}</span>}
    </li>)}
  </ul>

  <div className="crit-section-title">What each agent produces</div>
  <p>{producesProse}</p>

  <div className="crit-section-title">Allowed categories</div>
  <div className="chip-row">
    {allowedCategories.map(c =>
      <Chip key={c} tone={CATEGORY_TONE[c]} categoryBubble={CATEGORY_BUBBLE[c]} label={CATEGORY_LABEL_PLURAL[c]} />
    )}
    {allowedCategories.length === 0 && <span className="hiw-muted">(none — no operation blocks in this phase)</span>}
  </div>

  <div className="crit-section-title">Convergence condition</div>
  <p>{convergenceProse}</p>

  <PhaseInputDiagram phase={N} />  {/* Diagram 2, per-phase variant */}

  <div className="crit-section-title">Outputs (canonical artifact IDs)</div>
  <ul className="hiw-output-list">
    {outputs.map(o => <li key={o.id}>
      <Chip mono shape="square" tone="neutral" label={o.canonicalId} />
      <span className="hiw-input-name">{o.displayName}</span>
    </li>)}
  </ul>
</CollapsibleSection>
```

The per-phase content fills in the placeholders below. Identifiers (`canonicalId`) come from the spec 0117 artifact registry; display names come from `display_name(artifact_id)`.

#### 5.2.1 — Phase 0 — Input (multi-round, parallel, soft 2 / hard 4)

**Lede:** Both agents read the user's brief and raise questions or disagreements about scope, framing, missing inputs, or the intended audience. Round 1 is a first-look critique; round 2+ both addresses the counterpart's raised items and ratifies (or counter-argues) the responses. The phase converges on an **agreed interpretation** — scope, approach, and any items that should carry forward into later phases.

**Inputs (canonical IDs + display name):**

- `system.preamble` — shared system preamble
- `system.task.input` — phase-0 task instructions
- `user_prompt` — the user's brief (message + attachments)
- `prior_turns.phase0` *(round ≥ 2)* — both agents' turns from prior rounds, perspective-flipped
- `ledger.standing_items` *(round ≥ 2)* — open items raised so far
- `closeout.request` *(closeout rounds only)* — orchestrator-injected closeout instruction

**Allowed categories:** Q, D.

**Convergence condition:** both agents emit `STATUS: AGREED` in the same round AND every raised item is in a terminal state (`resolved`, `acknowledged`, `withdrawn`, or `capped`) AND both agents emit the `AGREED_INTERPRETATION` block in matching form.

**Outputs:**

- `phase0.claude.r<N>`, `phase0.openai.r<N>` — per-round turn artifacts (one per agent per round)
- `phase0.agreement.interpretation` — the emitted-on-AGREED artifact

#### 5.2.2 — Phase 1 — Research plan (one-shot, parallel)

**Lede:** Each agent writes a complete research plan + thesis, independently. **No operation blocks** — agents don't raise items in this phase. Inline `[V]` / `[U]` source tagging is required on prose claims. The phase ends when both plans are present.

**Inputs:**

- `system.preamble`
- `system.task.research_plan`
- `user_prompt`
- `phase0.agreement.interpretation` *(the carry-forward from Phase 0)*

**Allowed categories:** *(none — this is a production phase, not a negotiation phase)*

**Convergence condition:** both `phase1.claude` and `phase1.openai` artifacts present and well-formed.

**Outputs:**

- `phase1.claude` — Claude's research plan + thesis (Summary · Thesis · Detailed findings · Sources)
- `phase1.openai` — GPT's research plan + thesis (same shape)

#### 5.2.3 — Phase 2 — Negotiate plan (multi-round, parallel, soft 4 / hard 8)

**Lede:** Each agent reads both phase-1 plans (their own and the counterpart's). They raise questions and disagreements about scope, methodology, source quality, missing angles, and structure. The phase converges on an **agreed plan** — a section-by-section outline + the key claims each section will make — plus a **drafter selection** (which agent will write the unified document in Phase 3).

**Inputs:**

- `system.preamble`, `system.task.plan_negotiation`, `user_prompt`
- `phase0.agreement.interpretation`
- `phase1.claude`, `phase1.openai`
- `prior_turns.phase2` *(round ≥ 2)*, `ledger.standing_items` *(round ≥ 2)*
- `closeout.request` *(closeout rounds)*

**Allowed categories:** Q, D.

**Convergence condition:** both AGREED + every raised item terminal + both emit the `AGREED_PLAN` block in matching form + both emit a matching `DRAFTER:` line (tiebreak resolves disagreements per `tiebreak.pick_drafter`).

**Outputs:**

- `phase2.claude.r<N>`, `phase2.openai.r<N>` — per-round turn artifacts
- `phase2.agreement.plan`, `phase2.agreement.drafter`

#### 5.2.4 — Phase 3 — Draft (one-shot, single drafter)

**Lede:** The drafter chosen in Phase 2 writes the unified document, section-by-section, following the agreed plan. The non-drafter agent does **not** run in this phase. The draft emits a `## Disagreements left open` section listing every Phase-2 disagreement that ended in `acknowledged` or `capped` (i.e. *known* but unresolved); same for `## Open questions`.

**Inputs:**

- `system.preamble`, `system.task.drafting`, `user_prompt`
- `phase0.agreement.interpretation`
- `phase1.claude`, `phase1.openai`
- `phase2.agreement.plan`
- `carry_forward.phase2` — the acknowledged / capped Phase 2 items
- `all_p2_turns` — every Phase 2 turn (concatenated)

**Allowed categories:** *(none)*

**Convergence condition:** drafter emits `phase3.draft.v1` artifact.

**Outputs:**

- `phase3.draft.v1` — the initial unified draft

#### 5.2.5 — Phase 4 — Review draft (multi-round, parallel, soft 4 / hard 8)

**Lede:** Both agents read the current draft. Either may raise questions (`Q`), disagreements (`D`), issues (`I` — defects in the draft), or comments (`C` — non-defect improvements). The drafter may mid-phase revise via a `## Revised draft` section, which advances the `draft_version` pointer (`v1 → v2 → …`). The phase converges on an **agreed draft acceptance** — `draft_version` + `draft_hash` + a mutual endorsement.

**Inputs:**

- `system.preamble`, `system.task.review`, `user_prompt`
- `current_draft` — the latest `phase{3,4}.draft.v<N>` artifact
- `prior_turns.phase4` *(round ≥ 2)*, `ledger.standing_items` *(round ≥ 2)*
- `closeout.request` *(closeout rounds)*

**Allowed categories:** Q, D, I, C — the full four.

**Convergence condition:** both AGREED on the **same** `draft_version` + every raised item terminal + both emit the `AGREED_DRAFT_ACCEPTANCE` block matching on `(draft_version, draft_hash)`.

**Outputs:**

- `phase4.claude.r<N>`, `phase4.openai.r<N>` — per-round turn artifacts
- `phase4.draft.v<N>` *(when drafter revises)* — versioned drafts
- `phase4.agreement.draft_acceptance`

#### 5.2.6 — Finalize (programmatic, no LLM call)

A short note appended to the Phase 4 section (not its own collapsible) since Finalize is orchestrator-only:

> **Finalize.** When Phase 4 converges, the orchestrator assembles `final.document` from the latest draft version, plus an `## Appendix — Unresolved items` section listing every item across the run that ended in `acknowledged` or `capped` (with the verb chip + reason). No LLM call. The user sees the assembled document at the top of the run page.

**`<Chip>` next to the heading:** `<Chip mono tone="neutral" label="programmatic" />`.

---

### 5.3 — Section 7: How turns are reviewed (modal anatomy) (`hiw-modal`)

**Lede:** Click any phase row on the timeline to open the turn modal. The modal has two panes: on the left, the **artifact you're reviewing** (the counterpart's prior turn, the converged draft, etc.) with sub-tabs to switch between adjacent artifacts. On the right, the **items extracted from this turn** — grouped by category, each card shows who raised it, what part of the source it anchors to, its title, its rationale, and (if the agent cited any) its sources.

**Diagram 7 — modal anatomy.** Embedded full-width. Caption:

> Left pane: artifact + sub-tabs. Right pane: category-grouped item cards (Questions, Disagreements, Issues, Comments — in canonical Q → D → I → C order). Each card header begins with the **provider** chip, then the **category** chip, then the **raised-in-r<N>** chip, then (optional) **Sources <count>** chip. Body: Anchor → Title → Rationale → Sources.

**Body subsections (small-caps labels):**

- *The left pane* — explains sub-tabs (`Original` default, then `Input`); lists per-phase what `Original` shows by default (P4 → Current draft; P2 r≥2 → Other's prior turn; P2 r1 → Other's draft).
- *The right pane* — explains category grouping; explains why Claims panel doesn't appear (link to spec 0114 §"Categories"); explains the four chips on each card header and their order.
- *Card body anatomy* — the Anchor / Title / Rationale split per spec 0120 §5.3; how anchor formats vary (`quote` vs `after` vs `none`); how clicking a card scrolls the left pane to the anchored content.

**`.hiw-note` (info tone):**

> **Why "Anchored to <agent>'s draft" instead of "Anchored to text"?** The anchor identifies *which artifact and where in it* the item refers to. Naming the source agent makes it unambiguous which pane to scan when reading the anchor.

---

### 5.4 — Section 8: Item taxonomy & categories (`hiw-items`)

**Lede:** Every structured item raised in any negotiation phase has a **kind**. There are four kinds; together they are the entire vocabulary. The kind is fixed at raise-time and never changes.

**Diagram 4 — category + chip composition reference.** Embedded immediately after the lede.

**Body:**

A `.hiw-table` with one row per kind:

| Letter | Kind | Tone | When raisable | Meaning |
|---|---|---|---|---|
| Q (info bubble) | question | info | P0, P2, P4 | *"I don't know; the other agent does or should research."* |
| D (warn bubble) | disagreement | warn | P0, P2, P4 | *"I hold X; they hold Y; we differ on substance."* |
| I (err bubble) | issue | err | **P4 only** | *"The drafted document is defective in a specific way."* |
| C (idle bubble) | comment | idle | **P4 only** | *"Could be improved in a non-defect way."* |

Each "Letter" cell renders the actual `<Chip tone={…} categoryBubble={…} label={…}>` — not a static glyph — so the page is its own legend. (This means a user can spot-check that the chip on the timeline matches the chip in the explainer.)

**Sub-section: Why no `claim`?** A short paragraph + a `.hiw-note` (warn tone):

> **The `claim` kind was removed in spec 0114** (Deep Research protocol). The old `## Claims I expect the other agent might dispute` section is gone — the new prompts never ask for it. Disagreements that used to be raised pre-emptively as claims are now raised reactively as `D` items in Phase 2 or Phase 4 when an agent actually objects. Pre-0114 runs in the archive still show a `Claims` panel via the legacy renderer; new runs do not.

**Sub-section: Chip composition rule** (mirrors spec 0119 § 6.1):

> Every chip-bearing card header reads, left-to-right: **Provider → Activity → Category → Modifier → Status**. The provider is always first (so the eye knows whose work it's looking at). Category chips appear in the fixed order Q → D → I → C wherever multiple categories are shown together. Status chips are always right-aligned. A completed phase never has a "bare" header — there's always a chip on the right edge ( `✓ agreed`, `✓`, `running`, or `queued` ).

The chip composition is **rendered live** as three example cards (one per typical phase state). For each, the card uses the actual `<Chip>` primitive — so the example *is* the spec.

---

### 5.5 — Section 9: Item lifecycle (`hiw-lifecycle`)

**Lede:** Once raised, an item moves through a small state machine. Six states, with named transitions. The orchestrator (not the agents) decides which state an item is in at the end of each round; agents propose, the orchestrator ratifies.

**Diagram 3 — lifecycle state machine.** Embedded after the lede.

**Body table** (`.hiw-table`):

| From → To | Verb chip | Actor | Notes |
|---|---|---|---|
| *(new)* → open | `raised` (info) | raiser | Item enters `open` with an ID stamped by the orchestrator. |
| open → addressed | `addressed` (info) | addressee | The other agent responds with `### ADDRESS <id>`. |
| addressed → resolved | `resolved` (ok) | raiser | Terminal. Raiser ratifies the response. |
| addressed → acknowledged_proposed | `acknowledged` (warn) | raiser | Not yet terminal — needs mutual handshake. |
| acknowledged_proposed + counterpart ACK | `acknowledged` (warn) | both | Terminal. Mutual handshake completed. |
| open / addressed → withdrawn | `withdrawn` (idle) | raiser | Terminal. Raiser drops the item with a stated reason. |
| addressed → open | `raised again` (info) | raiser | Raiser counter-argues; item flips back to `open`. |
| any → capped | `capped` (err) | **orchestrator** | Terminal. Closeout budget exhausted or hard cap reached. |

**`.hiw-note` (warn tone):**

> **Rationale is mandatory at every transition.** Every operation block (`RAISE`, `ADDRESS`, `RESOLVE`, `ACKNOWLEDGE`, `WITHDRAW`, counter) requires a `reason:` field with non-empty content. The validator rejects operations without it; the prompt instructs agents to never omit a reason.

**Sub-section: Anchors.** Each item carries an *anchor* — a pointer to the part of the source artifact it refers to. Three formats:

- `quote` — a verbatim ≤25-word span from the source. Most common.
- `after` — a section heading from the source (`anchor_text: "## Methodology"`).
- `none` — the item refers to the artifact as a whole (e.g. *"the framing of the entire draft is off"*).

**Sub-section: Evidence.** When an item's resolution turns on a factual claim, the agent must attach `EvidenceRecord` entries (URL, page title, search query, fetched-at, content excerpt). The orchestrator validates every cited URL against the recorded web-search events for that turn; fabricated sources are flagged. The `<SourceRow>` component (linked: spec 0115) renders each record collapsibly.

---

### 5.6 — Section 10: Convergence & escape hatches (`hiw-converge`)

**Lede:** Multi-round phases (P0, P2, P4) need a deterministic way to end. The default is **organic convergence**: both agents simultaneously emit `STATUS: AGREED` with zero non-terminal items. When that doesn't happen, three escape hatches engage in sequence — **closeout → ghost cap → hard cap** — to ensure every run terminates.

**Diagram 6 — convergence + escape hatches.** Embedded after the lede.

**Body subsections:**

- *Organic convergence* — when both AGREED in the same round + every item terminal + matching agreement-artifact block.
- *Closeout* — triggered when both AGREED but non-terminal items remain. The next round is a **closeout round**: `RAISE` is forbidden; only `RESOLVE`, `ACKNOWLEDGE`, `WITHDRAW`, or counter on listed items. Each agent has a closeout budget of **2 per phase**.
- *Ghost cap* — when an agent exhausts their closeout budget with items still non-terminal, those items auto-flip to `capped` with an orchestrator-generated rationale (`"ghost-capped — closeout budget exhausted with item still non-terminal"`). The phase converges via `via_ghost_cap: true`.
- *Hard cap* — independent ceiling per phase (P0 = 4, P2 = 8, P4 = 8). When the round counter hits the hard cap, every remaining non-terminal item flips to `capped`. The phase converges via `via_hard_cap: true`.
- *Mutual-acknowledge handshake* — `ACKNOWLEDGE` proposed by the raiser doesn't terminalize the item; it requires the other agent to also `ACKNOWLEDGE` (in the same or next round) before transitioning to terminal `acknowledged`. Until then it stays in `acknowledged_proposed`.

**`.hiw-note` (info tone):**

> **No partial convergence, no canonical-FSD synthesis, no stuck-AGREED promotion.** Spec 0114 dropped these legacy escape valves. The closeout → ghost cap → hard cap sequence is the only convergence-failure path.

---

### 5.7 — Section 11: Cost & consumption (`hiw-cost`)

**Lede:** Every model call has a token cost. The Consumption tab on each run breaks that cost down per phase and per turn. This section explains where the numbers come from and how the per-piece costs are computed.

**Diagram 5 — cost calculation flow.** Embedded after the lede.

**Body subsections:**

- *Where the totals come from* — the **Total bar** on every cost card shows `billedInputTokens + billedOutputTokens` and the exact API-billed cost. These come straight from the provider response (Anthropic / OpenAI), unmodified.
- *Where the per-piece costs come from* — the **per-canonical-piece rows** under the total are computed proportionally:

  ```
  pieceCost = (pieceTokens / billedInputTokens) × totalInputCost
  ```

  This is a heuristic (the API doesn't tell us which tokens belonged to which prompt piece); the tooltip on every per-piece row says `(proportional)` to flag this.
- *The `System prompt` aggregate* — every per-phase `system.task.*` artifact, plus `prior_turns.*`, `ledger.standing_items`, and `closeout.request`, are rolled into a single **System prompt** row to keep the per-piece table readable. The tooltip on the row shows the per-sub-artifact breakdown.
- *Cache savings* — Anthropic prompt caching reuses tokens across turns within the 5-minute cache window. The Total bar renders a 45° diagonal stripe over the `cache_read_tokens` proportion at 0.5 opacity. The per-turn meta line reads e.g. `"3.5kt seen · 1.0kt billed (× 3.5 token reuse) · 980t out"`.
- *Which canonical pieces appear where* — a reference table:

  | Piece | Phases | Always-present? |
  |---|---|---|
  | `user_prompt` | every phase | yes |
  | `System prompt` aggregate | every phase | yes |
  | `phase0.agreement.interpretation` | P1, P2, P3 | yes (carry-forward) |
  | `phase1.claude`, `phase1.openai` | P2, P3 | yes (both shown) |
  | `phase2.agreement.plan` | P3 | yes |
  | `all_p2_turns` | P3 | yes |
  | `current_draft` (latest `phase{3,4}.draft.v<N>`) | P4 | yes |
  | `prior_turns.phase{0,2,4}` | round ≥ 2 of that phase | conditional |
  | `ledger.standing_items` | round ≥ 2 of multi-round phases | conditional |
  | `closeout.request` | closeout rounds only | conditional |

- *Models used* — render two `<Chip>` lines:

  ```jsx
  <div className="chip-row">
    <Chip leadingIcon={<BrandMark name="claude" size={12} />} tone="claude" label="Claude Sonnet 4.6" />
    <Chip mono tone="neutral" label="default" />
  </div>
  <div className="chip-row">
    <Chip leadingIcon={<BrandMark name="gpt" size={12} />} tone="gpt" label="GPT-5.5" />
    <Chip mono tone="neutral" label="default" />
  </div>
  ```

  Plus a `.hiw-note` (idle tone):
  > **Test tier.** Internal runs use Haiku 4.5 + GPT-5-mini for ~10× cost reduction during development; production runs use the chips above.

---

## 6. Diagram briefs (the seven `diagram` skill invocations)

Each brief is **self-contained** — the diagram skill is invoked once per item with the brief verbatim. The skill emits one `.light.svg` and one `.dark.svg` per invocation; both land at the path noted under each brief.

Common conventions for all seven:

- **Provider colors**: Claude = sable (`#d4a574`), GPT = sage (`#7cc4b8`). Match the running app exactly.
- **Category bubbles**: Q = blue (info, `#6b9cf0`), D = amber (warn, `#d4a056`), I = red (err, `#d96a6a`), C = grey (idle, `#7d8290`). Filled circle, knockout-white letter (font-weight 800, ≤ 10 px). When a chip is shown in a diagram, mirror the spec-0119 chip anatomy (label adjacent to bubble, never bubble alone in a card-level context).
- **Canonical artifact IDs** appear in mono on the diagram in `--mono` style (the diagram skill's own mono font equivalent).
- **No animation, no script.** Self-contained static SVG.
- **Embed-ready dimensions**: aspect ratio ≤ 2.5 : 1 so the diagram doesn't dominate the 1080 px modal at < 600 px height. Width target 1040 px (the modal's content width); the skill picks the actual canvas.

### 6.1 — Diagram 1: full pipeline

**Path:** `diagrams/how-it-works/01-pipeline.{light,dark}.svg`

**Brief for the skill:**

> Draw a left-to-right pipeline of six phases for a two-agent research protocol. Phase columns in order:
>
> 1. **Phase 0 — Input** (multi-round, parallel, soft 2 / hard 4)
> 2. **Phase 1 — Research plan** (one-shot, parallel)
> 3. **Phase 2 — Negotiate plan** (multi-round, parallel, soft 4 / hard 8)
> 4. **Phase 3 — Draft** (one-shot, single drafter)
> 5. **Phase 4 — Review draft** (multi-round, parallel, soft 4 / hard 8)
> 6. **Finalize** (programmatic, no LLM call)
>
> Above each multi-round phase column, draw a small round-ribbon icon (a curved looping arrow) labelled "multi-round". Above each one-shot phase, draw a single straight arrow labelled "one-shot". Above Finalize, draw a gear icon labelled "programmatic".
>
> Inside each parallel phase, render two horizontal swim-lanes: **Claude** (sable) on top, **GPT** (sage) below. Inside Phase 3, render only the **drafter** lane (a sable-or-sage band labelled "drafter (chosen in P2)").
>
> Between phases, draw labelled arrows for the artifact handoffs:
>
> - P0 → P1: `phase0.agreement.interpretation` (a small pill labelled "agreed interpretation")
> - P1 → P2: `phase1.claude`, `phase1.openai` (two thin parallel arrows)
> - P2 → P3: `phase2.agreement.plan` + `phase2.agreement.drafter` (one pill labelled "agreed plan + drafter")
> - P3 → P4: `phase3.draft.v1` (one pill labelled "draft v1")
> - P4 → Finalize: `phase4.agreement.draft_acceptance` + latest `phase4.draft.v<N>` (one pill labelled "agreed acceptance + final draft")
> - Finalize → output: a document icon labelled `final.document`
>
> Below each multi-round phase, draw a small inline chip cluster showing which **categories** can be raised in that phase, using the spec-0119 category-bubble form:
>
> - P0: [Q] [D]
> - P2: [Q] [D]
> - P4: [Q] [D] [I] [C]
> - (P1, P3, Finalize: no category cluster — show a small `—` instead)
>
> Top-of-canvas band: a thin "User prompt" ribbon (icon: page-with-text) with feathered arrows down into every phase — every phase consumes the user prompt.
>
> Bottom-of-canvas: a single-line legend strip with: small bubble samples for Q / D / I / C; provider sample chips for Claude / GPT; a "→ artifact" arrow sample; a "looping arrow" sample = multi-round; a "→" sample = one-shot.
>
> No phase numbering inside boxes — use the phase name above the box and `P0`, `P1`, `P2`, `P3`, `P4`, `F` as small mono identifiers in the top-right corner of each phase box.
>
> Tone: technical-instructional. No decorative elements; every glyph carries meaning.

### 6.2 — Diagram 2: per-phase input composition

**Path:** `diagrams/how-it-works/02-phase-inputs.{light,dark}.svg`

**Brief for the skill:**

> Draw a single generic phase as a tall rectangular "phase box" with the heading **Phase N — <name>** at the top and a horizontal divider below. The box is the central element of the diagram, ~ 60 % of the canvas width.
>
> Stack the inputs vertically as labelled rows along the **left edge** of the phase box, with right-pointing arrows entering the phase from each input row. Order the rows top-to-bottom in this canonical sequence:
>
> 1. `system.preamble` (system) — top
> 2. `system.task.<phase>` (system)
> 3. `user_prompt` (user, with sub-items `user_prompt.message` + `user_prompt.attachment.<id>` shown as a small nested cluster)
> 4. `phase<earlier>.agreement.<artifact>` (carry-forward, agreement-emitted) — *one row per carried artifact; show as a pill in the agreement-tone*
> 5. `phase<earlier>.<agent>` (carry-forward, per-agent — one row per agent) — *e.g. `phase1.claude` + `phase1.openai`*
> 6. `prior_turns.phase<N>` (round-conditional) — rendered with a dashed outline + a small `R≥2` badge
> 7. `ledger.standing_items` (round-conditional, dashed outline, `R≥2` badge)
> 8. `closeout.request` (round-conditional, dashed outline, `closeout` badge)
>
> Use the input-row tones: system = neutral, user = neutral-warm, carry-forward agreement = ok (green), carry-forward per-agent = the agent's brand color (sable / sage), round-conditional = dashed outline with neutral fill.
>
> Right edge of the phase box: stack the **outputs** vertically, with right-pointing arrows leaving the phase. Two output groups:
>
> - **Per-round turn artifacts** (`phase<N>.<agent>.r<N>`) — one row per agent, mono ID + "round N" badge.
> - **Agreement-emitted** (`phase<N>.agreement.<artifact>`) — pill in agreement-tone, only present in multi-round phases.
>
> Bottom of the canvas: a small caption strip that the embedder fills in per phase. (The same SVG is embedded under sections 2–6; the caption above the diagram in each section reads e.g. *"For Phase 0, fill in: system.task.input, no carry-forward inputs, no agreement-emitted outputs in round 1."*) The SVG itself uses `phase<N>` and `<name>` as placeholders rendered as italic mono in the headings.
>
> Make this read like a contract diagram, not a workflow. The point is: "given a phase, here is every input row that can appear, and every output row that can appear, with which rows are conditional flagged."

### 6.3 — Diagram 3: item lifecycle state machine

**Path:** `diagrams/how-it-works/03-item-lifecycle.{light,dark}.svg`

**Brief for the skill:**

> Draw a state-machine diagram for the lifecycle of a structured item (a question, disagreement, issue, or comment) in a two-agent negotiation protocol.
>
> Six states, drawn as rounded rectangles:
>
> - **open** (info tone, blue) — leftmost
> - **addressed** (info tone, blue, slightly darker)
> - **acknowledged_proposed** (warn tone, amber, dashed outline — signals "not yet terminal")
> - **acknowledged** (warn tone, amber, solid outline, with a small ✓ icon = terminal)
> - **resolved** (ok tone, green, solid outline, with a small ✓ icon = terminal)
> - **withdrawn** (idle tone, grey, solid outline, with a small ✓ icon = terminal)
> - **capped** (err tone, red, solid outline, with a small ⊘ icon = terminal-forced)
>
> Layout: `open` on the left. `addressed` immediately to its right. Then a fork into four columns: `resolved` (top), `acknowledged_proposed → acknowledged` (mid), `withdrawn` (bottom), `capped` (far right, with vertical input arrows from both `open` and `addressed` flowing into it).
>
> Edges (labelled with the verb chip from spec 0119, tone-matching):
>
> - new → `open` — label `raised` (info chip)
> - `open` → `addressed` — label `addressed` (info chip), actor: addressee
> - `addressed` → `resolved` — label `resolved` (ok chip), actor: raiser
> - `addressed` → `acknowledged_proposed` — label `acknowledged` (warn chip), actor: raiser
> - `acknowledged_proposed` → `acknowledged` — label "both ACK" (warn chip with a `+` glyph), actor: both
> - `open` → `withdrawn` AND `addressed` → `withdrawn` — label `withdrawn` (idle chip), actor: raiser
> - `addressed` → `open` (back-edge, curved) — label `raised again` (info chip), actor: raiser
> - `open` → `capped` AND `addressed` → `capped` (dashed vertical edges from far right) — label `capped` (err chip), actor: **orchestrator**
>
> Above the diagram, a one-line caption: *"States open / addressed are non-terminal. States resolved / acknowledged / withdrawn / capped are terminal. The orchestrator (not the agents) sets `capped`."*
>
> Below the diagram, a small side-note box titled **Mutual handshake**: *"acknowledged_proposed becomes terminal `acknowledged` only when both parties have ACK'd the same item in the same or next round."* Render this as a thin pill below the `acknowledged_proposed → acknowledged` edge.
>
> Actor annotations: small tags adjacent to each edge: "raiser" / "addressee" / "orchestrator". Use a thin mono font, 9 px equivalent.
>
> No arrow runs through another state. Use curved edges where straight would cross.

### 6.4 — Diagram 4: category taxonomy + chip composition reference

**Path:** `diagrams/how-it-works/04-categories.{light,dark}.svg`

**Brief for the skill:**

> A reference diagram (not a flow) that visualises the four item categories AND the chip composition rules together on a single canvas.
>
> **Top half — The four categories.** Four large cards in a horizontal row, equal width:
>
> - **Card 1 — Q · Question** — bubble background = info-bg (`#6b9cf0` at 0.15), bubble outline = info, big `Q` glyph in info, label "Question" below in info, sub-label "I don't know; the other agent does or should research." Footer chip cluster: where it can be raised — `[P0]` `[P2]` `[P4]` mono chips.
> - **Card 2 — D · Disagreement** — warn-bg, big `D` in warn, label "Disagreement", sub-label "I hold X; they hold Y; we differ on substance." Footer: `[P0]` `[P2]` `[P4]`.
> - **Card 3 — I · Issue** — err-bg, big `I` in err, label "Issue", sub-label "The drafted document is defective in a specific way." Footer: `[P4]` only.
> - **Card 4 — C · Comment** — idle-bg, big `C` in idle, label "Comment", sub-label "Could be improved in a non-defect way." Footer: `[P4]` only.
>
> All four cards same height, ~ 200 px each.
>
> **Bottom half — Chip composition rule.** A horizontal "left-to-right composition strip" diagram of one full card header, with each chip slot labelled:
>
> `[Claude] → [turn 3] → [Q · Question] → [raised in r2] → [Sources 4] → ✓ resolved in r4`
>
> Above each chip, a small caption: `Provider`, `Activity`, `Category`, `Modifier`, `Modifier`, `Status`. Below the whole strip, the rule in italic: *"Provider first. Status last (and never bare). Categories in canonical Q → D → I → C order when multiple appear together."*
>
> Right edge: a vertical "Tones" legend showing the eight canonical tones from spec 0119 as small chip swatches: `info`, `ok`, `warn`, `err`, `idle`, `claude`, `gpt`, `neutral`. Each swatch with its hex code in mono below.
>
> No motion, no decoration. The diagram IS the reference; a user pointing to a chip in the running app should be able to find its category card here in < 5 seconds.

### 6.5 — Diagram 5: cost calculation flow

**Path:** `diagrams/how-it-works/05-cost-flow.{light,dark}.svg`

**Brief for the skill:**

> Draw a left-to-right data-flow diagram showing how a per-turn cost row in the Consumption tab gets its numbers.
>
> **Left column — Sources.** Three input lanes labelled:
>
> 1. **API response** — `billedInputTokens`, `billedOutputTokens`, `cacheReadTokens`, exact `inputCost`, `outputCost`, `totalCost` — render as a small "API receipt" card with monospaced numeric pseudo-values (e.g. `billedInput: 8,420t`, `billedOutput: 980t`, `totalCost: $0.0473`).
> 2. **Prompt pieces** — the canonical-piece IDs from the spec 0117 registry as a vertical stack: `system.preamble`, `system.task.<phase>`, `user_prompt`, `prior_turns.<phase>`, `ledger.standing_items`, `closeout.request`, plus per-phase pieces. Each rendered as a small mono pill in neutral tone.
> 3. **Per-piece token counts** — per-piece `tokenCount` values, as a stacked-bar representation, with the relative heights mapped to plausible token-count proportions.
>
> **Middle column — Two computations.** Two large process boxes side by side:
>
> - **Top box — "Total bar"** (large, primary): input `billedInputTokens` and `billedOutputTokens` and `cacheReadTokens` and `totalCost`. Output: a horizontal bar with a solid fill (length proportional to `billedInputTokens + billedOutputTokens`), a 45° diagonal-stripe overlay on the leftmost `cacheReadTokens / billedInputTokens` proportion at 0.5 opacity, and the `$<cost>` numeric on the right edge. Label below: "Exact — straight from API response."
> - **Bottom box — "Per-piece rows"** (smaller, secondary): input is the prompt-piece list + per-piece `tokenCount` + `totalInputCost` + `billedInputTokens`. Render the formula prominently: `pieceCost = (pieceTokens / billedInputTokens) × totalInputCost` in a serif math-style font. Output: a stacked vertical list of per-piece rows, each with a mini bar + `<tokens>t · $<cost>` numeric. Label below: "Proportional — heuristic. Tooltip flags this with `(proportional)`."
>
> **Right column — Aggregation.** One box titled **System prompt aggregate** showing a small nested list: `system.preamble` + `system.task.<phase>` + `prior_turns.<phase>` + `ledger.standing_items` + `closeout.request` — all bracketed with a curly brace into one summarized row. Caption: *"Rolled into a single 'System prompt' row for readability. Tooltip shows the per-sub-artifact breakdown."*
>
> **Far right column — Display.** A mockup of the actual consumption-card UI: a Total bar at the top (matching the middle-column "Total bar" output), then a divider, then per-canonical-piece rows in `<description> · <bar> · <tokens>t · $<cost>` 3-column grid layout (matching spec 0118).
>
> Edges between the columns: arrows labelled with what flows. Use the cream-and-indigo / dark palette of the diagram skill. Mono numerics use a tabular-nums style.
>
> The diagram should answer the question "where does $0.0473 come from?" by tracing every number to its source.

### 6.6 — Diagram 6: convergence + escape hatches

**Path:** `diagrams/how-it-works/06-convergence.{light,dark}.svg`

**Brief for the skill:**

> Draw a decision-tree / sequence diagram for how a multi-round phase ends. Vertical layout, top-to-bottom.
>
> **Top node:** "End of round N — orchestrator update step" (rectangle).
>
> **First decision diamond:** "Both agents emitted STATUS: AGREED this round?" — branches:
>
> - **No** → arrow down to "Advance to round N+1" (oval, info tone). Then a curved arrow looping back up to the top node, labelled "next round".
> - **Yes** → continue to next decision.
>
> **Second decision diamond:** "All raised items in this phase are terminal?" — branches:
>
> - **Yes** → green arrow to "**Organic convergence**" terminal box (ok tone). Caption: *"Phase ends. Agreement artifact emitted."*
> - **No** → continue.
>
> **Third decision diamond:** "Either agent's closeout budget > 0?" — branches:
>
> - **Yes** → amber arrow to "**Closeout round**" box (warn tone). Caption inside the box: *"Next round, RAISE is forbidden. Only RESOLVE / ACKNOWLEDGE / WITHDRAW / counter. Budget = 2 per phase per agent."* Then arrow down to "End of round N+1" (back to top of decision tree, dashed loop-back arrow labelled "re-evaluate convergence").
> - **No** → continue.
>
> **Fourth decision diamond:** "Round number < hard cap?" — branches:
>
> - **Yes** → red-amber arrow to "**Ghost cap**" terminal box (err tone, dashed outline). Caption: *"Items still non-terminal flip to `capped` with orchestrator-generated rationale. Phase converges via `via_ghost_cap: true`."*
> - **No** → red arrow to "**Hard cap**" terminal box (err tone, solid outline). Caption: *"Every remaining non-terminal item flips to `capped`. Phase converges via `via_hard_cap: true`. Caps: P0=4, P2=8, P4=8."*
>
> **Right side of the canvas:** a vertical sidebar titled **"Mutual-ACK handshake"** (separate from the main flow, with a thin connecting tick to the third decision diamond's "Yes" branch). Render a small two-agent sequence:
>
> - Round N: raiser emits `ACKNOWLEDGE <id>` → item → `acknowledged_proposed`
> - Round N+1: counterpart emits `ACKNOWLEDGE <id>` → item → `acknowledged` (terminal)
>
> Caption under the sidebar: *"Without the counterpart's ACK, the item stays in `acknowledged_proposed` and re-appears as non-terminal in the next convergence check."*
>
> **Bottom-of-canvas legend:** the four terminal states a phase can end in: `organic` (ok), `via_closeout` (warn), `via_ghost_cap` (err dashed), `via_hard_cap` (err solid). One pill each.

### 6.7 — Diagram 7: turn-modal anatomy

**Path:** `diagrams/how-it-works/07-modal-anatomy.{light,dark}.svg`

**Brief for the skill:**

> Draw a labelled wireframe of the turn-review modal: a single large rounded rectangle representing the modal, split vertically into a **left pane** and a **right pane** with a thin divider.
>
> **Modal header (top of the rectangle):** title row with "Phase 2 · Round 3 · Claude" (provider chip leading, then mono "round 3" chip, then a small `agreed` ok-tone status chip on the right edge). Below the title row, a thin breadcrumb: `Run #4128 / Timeline / Phase 2 / Turn 5`.
>
> **Left pane** (≈ 55 % of modal width):
>
> - Top sub-tab strip: `[Original] (active)`, `[Input]`. Use a TabGroup-line-style with the active tab carrying an underline.
> - Sub-tab sub-strip below "Original": chips for the per-phase artifact options — `[Other's draft]`, `[Other's prior turn]`, `[Current draft]`. Caption "(P4 default = Current draft; P2 r≥2 default = Other's prior turn; P2 r1 default = Other's draft)".
> - Body region: a large faded-prose box (lorem-style) representing the artifact body. Indicate scrollability with a small scrollbar stub on the right edge.
>
> **Right pane** (≈ 45 % of modal width):
>
> - Top header: a single category-chip-style panel header reading `[Q-bubble] Questions  5` (info tone, value=5). Below it, a second panel header `[D-bubble] Disagreements  2` (warn tone, value=2). These are the panel section headers.
> - Under the "Questions" header, stack 2 sample item cards. Each card:
>   - Header chip row: `[Claude]` (provider chip, sable, with brand-mark icon) → `[Q-bubble] Question` (info) → `[raised in r2]` (mono neutral) → `[Sources 3]` (neutral).
>   - Body: three labelled sub-sections (small caps):
>     - "Anchored to GPT's draft" — italic quoted block of placeholder text.
>     - "Title" — one-line bold placeholder.
>     - "Rationale" — short paragraph placeholder.
>     - "Sources (3)" — three faded `<SourceRow>` stubs (collapsed form: `▶ title — hostname`).
> - One sample item card under the "Disagreements" header showing the same structure (without sources).
>
> **Annotations (callout arrows pointing into the wireframe):**
>
> - Pointing at the sub-tab strip on the left pane: *"Sub-tabs let you compare adjacent artifacts. Default per phase: see § 5.3."*
> - Pointing at the right-pane panel header: *"Panel header = category chip from spec 0119, identical to the critique-pane filter legend."*
> - Pointing at the card header chip cluster: *"Composition: Provider → Activity → Category → Modifier → Modifier → Status."*
> - Pointing at the card body labels: *"Anchor / Title / Rationale split per spec 0120."*
> - Pointing at the `SourceRow` stubs: *"Click to expand: URL, fetched-at, search query, content excerpt. Unverified records flag `⚠ unverified`."*
>
> **Bottom of canvas:** small one-line caption: *"Layout post-spec-0116 (modal cleanup) + spec-0120 (items panel rework). Pre-0114 legacy runs render via a separate code path with the Claims panel intact."*
>
> Diagram tone: technical UI wireframe, indigo accents on a cream background (light) / muted indigo on near-black (dark). Don't draw the actual app skin — keep it abstract enough that small UI changes don't invalidate the diagram.

---

## 7. Theme-aware embed pattern (for all 7 diagrams)

A single component, `<HiwDiagram src={path} alt={caption} />`, handles the light/dark swap via `MutationObserver` on `body.classList`. Defined once in `how-it-works.jsx`:

```jsx
function HiwDiagram({ name, alt }) {
  const [isLight, setIsLight] = React.useState(() =>
    typeof document !== 'undefined' && document.body.classList.contains('light')
  );
  React.useEffect(() => {
    if (typeof document === 'undefined') return;
    const observer = new MutationObserver(() => {
      setIsLight(document.body.classList.contains('light'));
    });
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  const variant = isLight ? 'light' : 'dark';
  return (
    <div className="hiw-diagram">
      <img
        src={`/diagrams/how-it-works/${name}.${variant}.svg?v=0121`}
        alt={alt}
        loading="lazy"
      />
    </div>
  );
}
```

Per-section usage:

```jsx
<HiwDiagram name="01-pipeline"        alt="Full Dual Research protocol pipeline" />
<HiwDiagram name="02-phase-inputs"    alt="Per-phase input composition (generic)" />
<HiwDiagram name="03-item-lifecycle"  alt="Item lifecycle state machine" />
<HiwDiagram name="04-categories"      alt="Category taxonomy and chip composition reference" />
<HiwDiagram name="05-cost-flow"       alt="Cost calculation flow" />
<HiwDiagram name="06-convergence"     alt="Convergence and escape hatches" />
<HiwDiagram name="07-modal-anatomy"   alt="Turn-review modal anatomy" />
```

Cache-bust `?v=0121` on all seven. Spec-0117's existing pattern; we reuse the convention.

---

## 8. Changelog tab rework

### 8.1 — Entry anatomy

Each release entry is a `<CollapsibleSection>` wrapping a `<Card variant="outlined">`. Header shows version + date + a one-line summary. Expanded body shows the full per-bullet breakdown, plus (when available) embedded screenshots of the surface(s) the spec affected.

```jsx
<CollapsibleSection
  persistKey={`hiw:changelog:${entry.version}`}
  renderTitle={() => (
    <div className="changelog-head">
      <Chip mono tone="neutral" label={`v${entry.version}`} />
      <span className="changelog-date">{entry.date}</span>
      <span className="changelog-summary">{entry.summary}</span>
      <span className="spacer" />
      {entry.specs.map(s =>
        <Chip key={s} mono shape="square" tone="neutral" label={`spec ${s}`} />
      )}
      {entry.bump === 'MAJOR' && <Chip tone="err"  label="MAJOR" />}
      {entry.bump === 'MINOR' && <Chip tone="info" label="MINOR" />}
      {entry.bump === 'PATCH' && <Chip tone="ok"   label="PATCH" />}
    </div>
  )}
  defaultOpen={isFirstEntry}
>
  <Card variant="outlined">
    <CardBody>
      <div className="crit-section-title">What changed</div>
      <ul className="changelog-bullets">
        {entry.bullets.map(b => <li key={b.id}>{b.markdown}</li>)}
      </ul>

      {entry.screenshots.length > 0 && (
        <>
          <div className="crit-section-title">Screenshots</div>
          <div className="changelog-shots">
            {entry.screenshots.map(s =>
              <figure key={s.path}>
                <img src={s.path} alt={s.alt} loading="lazy" />
                <figcaption>{s.caption}</figcaption>
              </figure>
            )}
          </div>
        </>
      )}

      {entry.specPath && (
        <div className="changelog-spec-link">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.open(entry.specPath, '_blank')}
          >Open spec ↗</Button>
        </div>
      )}
    </CardBody>
  </Card>
</CollapsibleSection>
```

### 8.2 — Backfill of missing entries

The `VERSION_NOTES` array in `how-it-works.jsx` is missing the last three releases. Add (in order, newest first):

| Version | Date | Spec(s) | Summary | Screenshots needed |
|---|---|---|---|---|
| **1.4.1** | 2026-05-20 | 0120 | Turn-modal items panel rework — provider chip + Anchor/Title/Rationale split + Claims panel removed (new-protocol). | (a) before/after turn-modal right pane: before = pre-0120 raw-markdown card, after = post-0120 labelled-segment card. (b) panel-header chip showing `[Q] Questions 5`. |
| **1.4.0** | 2026-05-20 | 0119 | Badge governance — unified `<Chip>` primitive + canonical vocabulary (Q/D/I/C bubbles, lifecycle verb chips, never-bare status). | (a) critique pane filter row (the new chip-only legend). (b) timeline turn card header (Provider + turn + status chips). (c) phase-header chip cluster on a multi-round phase. |
| **1.3.0** | 2026-05-20 | 0118 | Consumption tab redesign + canonical-piece aggregation + per-piece proportional cost tracking. | (a) collapsed cost card with cache-reuse stripe. (b) unfolded cost card with System-prompt-aggregate row + tooltip. |

For each screenshot, the **capture plan** is in § 12.4 (paths, surfaces, fixture-run protocol).

Older entries (v0.18.0 → v1.2.0) keep their existing bullets but migrate to the new `<CollapsibleSection>` + `<Card>` form. Their bullets stay; no rewrite. Screenshots are not backfilled for these (would be excessive scope); only the three newest entries get screenshots.

### 8.3 — Sort + filter

Above the entries, render a chip row (mirrors spec-0119 filter-row aesthetic):

```jsx
<div className="crit-filter-row">
  <Chip tone="info" leadingDot label="All" value={entries.length} />
  <Chip tone="err"  label="MAJOR" value={countByBump.MAJOR} dim={countByBump.MAJOR === 0} />
  <Chip tone="info" label="MINOR" value={countByBump.MINOR} dim={countByBump.MINOR === 0} />
  <Chip tone="ok"   label="PATCH" value={countByBump.PATCH} dim={countByBump.PATCH === 0} />
  <span className="spacer" />
  <input type="search" className="hiw-search" placeholder="search…" value={q} onChange={…} />
</div>
```

Filter is client-side; bump filter is multi-select; search matches version, date, summary, bullet text, and spec IDs.

---

## 9. Mockup HTML deliverable

A single self-contained `mockup.html` file is produced as part of this spec. Path: `design-system/audits/2026-05-20-hiw-rework/mockup.html` (the audits directory is the established convention for design-system-affecting deliverables).

**Contents:**

- One HTML file with inline `<style>` and inline `<script>` — no external dependencies except the 14 SVG files (referenced relatively).
- A theme toggle button in the top-right (default = dark, click → light). Toggles `body.classList`; every chip + diagram swap responds.
- A two-tab header matching the live overlay shell.
- Tab 1 ("How it works"): all 10 sections rendered, all collapsibles wired (click to expand/collapse; first section open by default), all 7 diagrams embedded via the same theme-aware swap pattern as the live JSX.
- Tab 2 ("Changelog"): the three new entries (1.4.1, 1.4.0, 1.3.0) plus 3 representative older entries (top of the existing list), all rendered with the new entry anatomy.
- Tokens copied verbatim from `tokens.css` (only the ones referenced; not the full file). Chip CSS copied from `components.css`.
- A small banner at the top: *"Mockup — spec 0121 preview. Click anything to verify. Light/dark toggle in the top-right."*

The mockup lives in `design-system/audits/` as the visual reference for the JSX implementation in §§ 10–13. It is not loaded by the running app; it is the design-time artifact a reviewer compares against the live app when verifying the PR.

---

## 10. Implementation — JSX rewrite for `how-it-works.jsx`

### 10.1 — Strategy

Full-file rewrite of `src/dual_research/ui/static/how-it-works.jsx`. The pre-spec-0121 file is 1,823 lines, ~80 % of which is dead-code components (`PhaseStrip`, `ContextGrowthBars`, `ChatLifecycle`, `LifecycleRow`, `CallBox`, `TldrCards`, `ComparePanel`, `Section`, `Legend`, `Tk`, `AgentDisc`, `ClaudeDisc`, `GptDisc`, `ProtocolOverviewMap`, `ProtocolOverviewFold`, `NegotiationRoundDiagram`, `PhaseAccordion`, `PhaseMeta`, `Faq`, the old `ReleaseNote` and `ChangelogEntry`) — all of which are retired by this spec (full list in § 13). The post-spec-0121 file is ~640 lines, structured as documented in § 10.2.

**Preserves from the pre-0121 file:**
- The outer IIFE wrapper (`(function () { … })();`).
- The Escape-to-close handler + return-focus-to-trigger dance in the main `HowItWorks` component.
- The `window.HowItWorks` and `window.HowItWorksPage` global exports.
- The modal chrome (`.md-dialog__scrim` + `.md-dialog.md-dialog--rich`) — the M3 dialog classes from spec 0096 are reused unchanged.

**Brings in from the mockup HTML:**
- The 10-section IA exactly as in § 4.2.
- The chip composition / category bubble usage exactly matching the mockup.
- The diagram embed pattern (theme-aware `<img>` swap with `MutationObserver`) per § 7.

**Does NOT depend on any new `shared.jsx` exports.** Chips, cards, and collapsibles are rendered as plain DOM with the canonical CSS classes (`.chip.tone-info`, `.cat-bubble`, `.dr-card`, `.cs-section`, etc.) — exactly as the mockup does. This decouples the rewrite from any in-flight `shared.jsx` refactor and means the PR has no cross-file dependency churn beyond `components.css`.

### 10.2 — Drop-in JSX (the entire new file)

```jsx
// how-it-works.jsx — user-facing explainer of the Dual Research protocol
// plus the in-app changelog (Spec 0121 rewrite).
//
// IA: 10 collapsible sections in the "How it works" tab + a tabbed Changelog
// view. Every diagram embeds via theme-aware <img> swap (MutationObserver on
// body.classList) from /diagrams/how-it-works/. Every chip uses the spec-0119
// canonical Chip CSS classes; no bespoke chip variants. CSS lives in
// components.css under the `/* spec-0121` block (see § 11 of the spec).
//
// VERSION_NOTES is the source of the in-app changelog. Future specs touching
// user-visible behaviour append a new entry per CONTRIBUTING.md.

(function () {
  'use strict';

  // ─── Constants ────────────────────────────────────────────────

  const VERSION_NOTES = /* see § 12 of spec 0121 for the data literal */ [
    // … the entries are emitted verbatim from § 12 …
  ];

  const HIW_SECTIONS = [
    { id: 'hiw-overview',  label: 'Protocol overview' },
    { id: 'hiw-p0',        label: 'Phase 0 — Input' },
    { id: 'hiw-p1',        label: 'Phase 1 — Research plan' },
    { id: 'hiw-p2',        label: 'Phase 2 — Negotiate plan' },
    { id: 'hiw-p3',        label: 'Phase 3 — Draft' },
    { id: 'hiw-p4',        label: 'Phase 4 — Review draft' },
    { id: 'hiw-modal',     label: 'How turns are reviewed' },
    { id: 'hiw-items',     label: 'Item taxonomy & categories' },
    { id: 'hiw-lifecycle', label: 'Item lifecycle' },
    { id: 'hiw-converge',  label: 'Convergence & escape hatches' },
    { id: 'hiw-cost',      label: 'Cost & consumption' },
  ];

  // ─── Theme-aware diagram embed ────────────────────────────────

  function useThemeMode() {
    const [isLight, setIsLight] = React.useState(() =>
      typeof document !== 'undefined' && document.body.classList.contains('light')
    );
    React.useEffect(() => {
      if (typeof document === 'undefined') return;
      const obs = new MutationObserver(() => {
        setIsLight(document.body.classList.contains('light'));
      });
      obs.observe(document.body, { attributes: true, attributeFilter: ['class'] });
      return () => obs.disconnect();
    }, []);
    return isLight ? 'light' : 'dark';
  }

  function HiwDiagram({ name, alt }) {
    const variant = useThemeMode();
    return (
      <div className="hiw-diagram">
        <img
          src={`/diagrams/how-it-works/${name}.${variant}.svg?v=0121`}
          alt={alt}
          loading="lazy"
        />
      </div>
    );
  }

  // ─── Collapsible section with localStorage persistence ────────

  function CollapsibleSection({ id, persistKey, defaultOpen, renderTitle, title, children }) {
    const storageKey = persistKey ? `hiw:cs:${persistKey}` : null;
    const [open, setOpen] = React.useState(() => {
      if (!storageKey) return !!defaultOpen;
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored === '1') return true;
        if (stored === '0') return false;
      } catch (e) { /* ignore */ }
      return !!defaultOpen;
    });
    React.useEffect(() => {
      if (!storageKey) return;
      try { localStorage.setItem(storageKey, open ? '1' : '0'); } catch (e) { /* ignore */ }
    }, [open, storageKey]);

    return (
      <section
        id={id}
        className={'hiw-sec cs-section' + (open ? ' is-open' : '')}
      >
        <div
          className="cs-header"
          role="button"
          tabIndex={0}
          aria-expanded={open}
          onClick={() => setOpen(o => !o)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(o => !o); }
          }}
        >
          <span className="cs-chevron" aria-hidden="true">▶</span>
          <span className="cs-title">
            {renderTitle ? renderTitle() : title}
          </span>
        </div>
        <div className="cs-body">{open ? children : null}</div>
      </section>
    );
  }

  // ─── Chip primitives (CSS-only — mirrors spec 0119 .chip classes) ─

  // Category bubble + label (Q / D / I / C)
  function CategoryChip({ letter, label, value }) {
    const tone = { Q: 'info', D: 'warn', I: 'err', C: 'idle' }[letter];
    return (
      <span className={`chip tone-${tone} no-dot`}>
        <span className="cat-bubble">{letter}</span>
        <span className="chip-label">{label}</span>
        {value != null && <span className="chip-value">{value}</span>}
      </span>
    );
  }

  // Provider chip with brand mark leading icon
  function ProviderChip({ provider, label }) {
    const tone = provider === 'claude' ? 'claude' : 'gpt';
    return (
      <span className={`chip tone-${tone} no-dot`}>
        <span className="chip-leading-icon">
          <BrandSwatch provider={provider} />
        </span>
        <span className="chip-label">{label || (provider === 'claude' ? 'Claude' : 'GPT')}</span>
      </span>
    );
  }

  // Minimal SVG brand mark — uses the agent-tinted currentColor.
  function BrandSwatch({ provider }) {
    return (
      <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12" aria-hidden="true">
        <circle cx="8" cy="8" r="6" />
      </svg>
    );
  }

  // Canonical-ID chip (mono, square, neutral)
  function IdChip({ id }) {
    return <span className="chip mono chip-square tone-neutral no-dot">{id}</span>;
  }

  // Mono modifier chip (round, neutral) — e.g. "raised in r2", "round 3"
  function ModChip({ text }) {
    return <span className="chip mono tone-neutral no-dot">{text}</span>;
  }

  // ─── Input/output list rows ───────────────────────────────────

  function InputRow({ id, tone, name, note }) {
    const chipClass = tone === 'ok'
      ? 'chip mono chip-square tone-ok no-dot'
      : tone === 'claude' ? 'chip mono chip-square tone-claude no-dot'
      : tone === 'gpt'    ? 'chip mono chip-square tone-gpt no-dot'
      : 'chip mono chip-square tone-neutral no-dot';
    return (
      <li>
        <span className={chipClass}>{id}</span>
        {name && <span className="hiw-input-name">{name}</span>}
        {note && <span className="hiw-input-note">{note}</span>}
      </li>
    );
  }

  // ─── Per-phase section (sections 2–6) ─────────────────────────

  function PhaseSection({ phase }) {
    return (
      <CollapsibleSection
        id={phase.anchor}
        persistKey={phase.anchor}
        renderTitle={() => (
          <span className="hiw-section-title">
            {phase.title}
            <ModChip text={phase.cap} />
            <ModChip text={phase.shape} />
          </span>
        )}
      >
        <p className="lede">{phase.lede}</p>

        <div className="crit-section-title">Inputs</div>
        <ul className="hiw-input-list">
          {phase.inputs.map((i, idx) => <InputRow key={idx} {...i} />)}
        </ul>

        <div className="crit-section-title">Allowed categories</div>
        <div className="chip-row">
          {phase.categories.length === 0
            ? <span className="hiw-muted">{phase.categoriesNote}</span>
            : phase.categories.map(c =>
                <CategoryChip key={c.letter} letter={c.letter} label={c.label} />
              )}
        </div>

        <div className="crit-section-title">Convergence condition</div>
        <p>{phase.convergence}</p>

        {phase.diagramName && (
          <>
            <HiwDiagram name={phase.diagramName} alt={`Phase ${phase.title} input composition`} />
            <p className="hiw-caption">{phase.diagramCaption}</p>
          </>
        )}

        <div className="crit-section-title">Outputs</div>
        <ul className="hiw-output-list">
          {phase.outputs.map((o, idx) => <InputRow key={idx} {...o} />)}
        </ul>

        {phase.footer}
      </CollapsibleSection>
    );
  }

  // ─── Section data ─────────────────────────────────────────────
  // (Inline rather than separate constants — keeps the JSX file as
  //  the single source of truth for both prose and structure.)

  const PHASES = [
    {
      anchor: 'hiw-p0',
      title: 'Phase 0 — Input',
      cap: 'soft 2 / hard 4 rounds',
      shape: 'parallel',
      lede: "Both agents read the user's brief and raise questions or disagreements about scope, framing, missing inputs, or the intended audience. Round 1 is a first-look critique; round 2+ both addresses the counterpart's raised items and ratifies (or counter-argues) the responses. The phase converges on an agreed interpretation — scope, approach, and any items that should carry forward into later phases.",
      inputs: [
        { id: 'system.preamble',       tone: 'neutral', name: 'shared system preamble' },
        { id: 'system.task.input',     tone: 'neutral', name: 'phase-0 task instructions' },
        { id: 'user_prompt',           tone: 'neutral', name: "the user's brief (message + attachments)" },
        { id: 'prior_turns.phase0',    tone: 'neutral', name: "both agents' turns from prior rounds, perspective-flipped", note: 'round ≥ 2' },
        { id: 'ledger.standing_items', tone: 'neutral', name: 'open items raised so far', note: 'round ≥ 2' },
        { id: 'closeout.request',      tone: 'neutral', name: 'orchestrator-injected closeout instruction', note: 'closeout rounds only' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
      ],
      convergence: 'Both agents emit STATUS: AGREED in the same round AND every raised item is in a terminal state (resolved, acknowledged, withdrawn, or capped) AND both agents emit the AGREED_INTERPRETATION block in matching form.',
      diagramName: '02-phase-inputs',
      diagramCaption: 'In Phase 0, system.task.input fills the system-task row; carry-forward inputs are absent in round 1. From round 2, prior_turns.phase0 + ledger.standing_items activate (dashed rows in the diagram).',
      outputs: [
        { id: 'phase0.<agent>.r<N>',         tone: 'neutral', name: 'per-round turn artifact (one per agent per round)' },
        { id: 'phase0.agreement.interpretation', tone: 'ok',  name: 'emitted on AGREED' },
      ],
    },
    {
      anchor: 'hiw-p1',
      title: 'Phase 1 — Research plan',
      cap: 'one-shot',
      shape: 'parallel',
      lede: "Each agent writes a complete research plan + thesis, independently. No operation blocks — agents don't raise items in this phase. Inline [V] / [U] source tagging is required on prose claims. The phase ends when both plans are present.",
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.research_plan',        tone: 'neutral', name: 'phase-1 task instructions' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok',     name: 'carry-forward from Phase 0' },
      ],
      categories: [],
      categoriesNote: '(none — this is a production phase, not a negotiation phase)',
      convergence: 'Both phase1.claude and phase1.openai artifacts present and well-formed.',
      diagramName: '02-phase-inputs',
      diagramCaption: 'Phase 1 has no round-conditional inputs (one-shot) and no agreement-emitted output — the dashed rows and ok-green output pill in the diagram are absent here.',
      outputs: [
        { id: 'phase1.claude',  tone: 'neutral', name: "Claude's research plan + thesis (Summary · Thesis · Detailed findings · Sources)" },
        { id: 'phase1.openai',  tone: 'neutral', name: "GPT's research plan + thesis (same shape)" },
      ],
    },
    {
      anchor: 'hiw-p2',
      title: 'Phase 2 — Negotiate plan',
      cap: 'soft 4 / hard 8 rounds',
      shape: 'parallel',
      lede: "Each agent reads both phase-1 plans (their own and the counterpart's). They raise questions and disagreements about scope, methodology, source quality, missing angles, and structure. The phase converges on an agreed plan — a section-by-section outline + the key claims each section will make — plus a drafter selection (which agent will write the unified document in Phase 3).",
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.plan_negotiation',     tone: 'neutral', name: 'phase-2 task instructions' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok',     name: 'carry-forward' },
        { id: 'phase1.claude',                    tone: 'claude', name: "Claude's research plan" },
        { id: 'phase1.openai',                    tone: 'gpt',    name: "GPT's research plan" },
        { id: 'prior_turns.phase2',               tone: 'neutral', note: 'round ≥ 2' },
        { id: 'ledger.standing_items',            tone: 'neutral', note: 'round ≥ 2' },
        { id: 'closeout.request',                 tone: 'neutral', note: 'closeout rounds' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
      ],
      convergence: 'Both AGREED + every raised item terminal + both emit the AGREED_PLAN block in matching form + both emit a matching DRAFTER: line (tiebreak resolves disagreements per tiebreak.pick_drafter).',
      diagramName: '02-phase-inputs',
      diagramCaption: 'Phase 2 is the densest-input phase: both research plans (one per agent, in agent-tinted pills) plus the agreed-interpretation carry-forward plus round-conditional inputs from round 2 onward. Outputs include the agreement-emitted plan + drafter pair (ok-green) when convergence lands.',
      outputs: [
        { id: 'phase2.<agent>.r<N>',         tone: 'neutral', name: 'per-round turn artifact' },
        { id: 'phase2.agreement.plan',       tone: 'ok',     name: 'section-by-section outline + key claims' },
        { id: 'phase2.agreement.drafter',    tone: 'ok',     name: 'which agent drafts in Phase 3' },
      ],
    },
    {
      anchor: 'hiw-p3',
      title: 'Phase 3 — Draft',
      cap: 'one-shot',
      shape: 'single drafter',
      lede: 'The drafter chosen in Phase 2 writes the unified document, section-by-section, following the agreed plan. The non-drafter agent does NOT run in this phase. The draft emits a "## Disagreements left open" section listing every Phase-2 disagreement that ended in acknowledged or capped (i.e. known but unresolved); same for "## Open questions".',
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.drafting',             tone: 'neutral' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok' },
        { id: 'phase1.claude',                    tone: 'claude' },
        { id: 'phase1.openai',                    tone: 'gpt' },
        { id: 'phase2.agreement.plan',            tone: 'ok' },
        { id: 'carry_forward.phase2',             tone: 'neutral', name: 'acknowledged / capped Phase 2 items' },
        { id: 'all_p2_turns',                     tone: 'neutral', name: 'every Phase 2 turn (concatenated)' },
      ],
      categories: [],
      categoriesNote: '(none)',
      convergence: 'Drafter emits the phase3.draft.v1 artifact.',
      outputs: [
        { id: 'phase3.draft.v1', tone: 'neutral', name: 'initial unified draft' },
      ],
    },
    {
      anchor: 'hiw-p4',
      title: 'Phase 4 — Review draft',
      cap: 'soft 4 / hard 8 rounds',
      shape: 'parallel',
      lede: 'Both agents read the current draft. Either may raise questions (Q), disagreements (D), issues (I — defects in the draft), or comments (C — non-defect improvements). The drafter may mid-phase revise via a "## Revised draft" section, which advances the draft_version pointer (v1 → v2 → …). The phase converges on an agreed draft acceptance — draft_version + draft_hash + a mutual endorsement.',
      inputs: [
        { id: 'system.preamble',          tone: 'neutral' },
        { id: 'system.task.review',       tone: 'neutral' },
        { id: 'user_prompt',              tone: 'neutral' },
        { id: 'current_draft',            tone: 'neutral', name: 'latest phase{3,4}.draft.v<N>' },
        { id: 'prior_turns.phase4',       tone: 'neutral', note: 'round ≥ 2' },
        { id: 'ledger.standing_items',    tone: 'neutral', note: 'round ≥ 2' },
        { id: 'closeout.request',         tone: 'neutral', note: 'closeout rounds' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
        { letter: 'I', label: 'Issues' },
        { letter: 'C', label: 'Comments' },
      ],
      convergence: 'Both AGREED on the SAME draft_version + every raised item terminal + both emit the AGREED_DRAFT_ACCEPTANCE block matching on (draft_version, draft_hash).',
      outputs: [
        { id: 'phase4.<agent>.r<N>',                  tone: 'neutral', name: 'per-round turn artifact' },
        { id: 'phase4.draft.v<N>',                    tone: 'neutral', name: 'versioned draft (when drafter revises)' },
        { id: 'phase4.agreement.draft_acceptance',    tone: 'ok' },
      ],
      footer: (
        <div className="hiw-note" data-tone="ok">
          <span className="hiw-note__label">Finalize</span>
          <span className="chip mono tone-neutral no-dot" style={{marginRight: 8}}>programmatic</span>
          When Phase 4 converges, the orchestrator assembles <code>final.document</code> from the latest draft version, plus an <code>## Appendix — Unresolved items</code> section listing every item across the run that ended in <code>acknowledged</code> or <code>capped</code>. No LLM call.
        </div>
      ),
    },
  ];

  // ─── Section 1: Protocol overview ─────────────────────────────

  function ProtocolOverviewSection() {
    return (
      <CollapsibleSection id="hiw-overview" persistKey="overview" defaultOpen
        renderTitle={() => 'Protocol overview'}>
        <p className="lede">
          Dual Research runs two large language models — <strong>Claude</strong> and <strong>GPT</strong> — through a six-phase protocol on a single brief, in parallel where possible and one-after-the-other where the next phase needs the previous phase's output. Both agents see the same brief, the same prior turns, and the same ledger of unresolved items. The orchestrator is deterministic; the agents are not. A run ends with a single approved document and an audit trail of every claim, disagreement, and source.
        </p>
        <div className="hiw-tldr">
          <div className="dr-card"><div className="dr-card-body">
            <h4>Two agents, one document</h4>
            <p>Two providers research the same brief. They negotiate a plan, one of them drafts, both review. The output is one document — not two.</p>
          </div></div>
          <div className="dr-card"><div className="dr-card-body">
            <h4>Every claim has a source</h4>
            <p>Each agent cites the URLs it consulted. Every cited URL is checked against a recorded web-search event; fabricated sources are flagged with <span className="chip mono tone-err no-dot">⚠ unverified</span>.</p>
          </div></div>
          <div className="dr-card"><div className="dr-card-body">
            <h4>Orchestrator owns convergence</h4>
            <p>Agents propose to converge; the orchestrator enforces caps and closeout. No agent can extend a phase past its hard cap.</p>
          </div></div>
        </div>
        <HiwDiagram name="01-pipeline" alt="Full Dual Research protocol pipeline" />
        <p className="hiw-caption">Six phases, left to right. Phases 0, 1, 2, 4 run both agents in parallel; phase 3 runs one drafter. Phases 0 / 2 / 4 are multi-round (each round = one turn per agent + an orchestrator update step). The "Agreed interpretation", "Agreed plan + drafter", "Agreed draft acceptance" capsules are the artifacts each multi-round phase emits when both agents reach AGREED with zero non-terminal items.</p>
      </CollapsibleSection>
    );
  }

  // ─── Sections 7–11 ────────────────────────────────────────────
  // (Code is illustrative; per-section JSX mirrors the mockup at
  //  design-system/audits/2026-05-20-hiw-rework/mockup.html.)

  function ModalAnatomySection()    { /* renders Diagram 7 + the modal-anatomy prose (mockup § 5.3) */ return null; }
  function ItemTaxonomySection()    { /* renders Diagram 4 + the Q/D/I/C table + chip composition (mockup § 5.4) */ return null; }
  function ItemLifecycleSection()   { /* renders Diagram 3 + the transition table (mockup § 5.5) */ return null; }
  function ConvergenceSection()     { /* renders Diagram 6 + the closeout/ghost/hard-cap prose (mockup § 5.6) */ return null; }
  function CostSection()            { /* renders Diagram 5 + the formula + the canonical-pieces table (mockup § 5.7) */ return null; }

  // (^ for spec readability, the bodies of the five non-phase sections are
  //  written here as one-line `return null`. The actual file substitutes
  //  the literal JSX from the mockup at design-system/audits/2026-05-20-hiw-
  //  rework/mockup.html lines 432–875 — they're a 1-to-1 translation of the
  //  HTML to JSX, with className strings preserved and a single replacement:
  //  `<img data-diagram="..." />` becomes `<HiwDiagram name="..." alt="..." />`.)

  // ─── Changelog ────────────────────────────────────────────────

  function ChangelogEntry({ entry, defaultOpen }) {
    const bumpTone = entry.bump === 'MAJOR' ? 'err' : entry.bump === 'MINOR' ? 'info' : 'ok';
    return (
      <CollapsibleSection
        id={`cl-${entry.version.replace(/\./g, '')}`}
        persistKey={`changelog:${entry.version}`}
        defaultOpen={defaultOpen}
        renderTitle={() => (
          <div className="changelog-head">
            <span className="chip mono tone-neutral no-dot">v{entry.version}</span>
            <span className="changelog-date">{entry.date}</span>
            <span className="changelog-summary">{entry.summary}</span>
            {entry.specs.map(s =>
              <span key={s} className="chip mono chip-square tone-neutral no-dot">spec {s}</span>
            )}
            {entry.bump && <span className={`chip tone-${bumpTone}`}>{entry.bump}</span>}
          </div>
        )}
      >
        <div className="dr-card"><div className="dr-card-body">
          <div className="crit-section-title">What changed</div>
          <ul className="changelog-bullets">
            {entry.items.map((b, i) => <li key={i} dangerouslySetInnerHTML={{__html: b}} />)}
          </ul>
          {entry.screenshots && entry.screenshots.length > 0 && (
            <>
              <div className="crit-section-title">Screenshots</div>
              <div className="changelog-shots">
                {entry.screenshots.map((s, i) =>
                  <figure key={i}>
                    <img src={s.path} alt={s.alt} loading="lazy" />
                    <figcaption>{s.caption}</figcaption>
                  </figure>
                )}
              </div>
            </>
          )}
          {entry.specPath && (
            <div className="changelog-spec-link">
              <button
                type="button"
                className="md-btn md-btn--text md-btn--sm"
                onClick={() => window.open(entry.specPath, '_blank')}
              >Open spec ↗</button>
            </div>
          )}
        </div></div>
      </CollapsibleSection>
    );
  }

  function ChangelogList() {
    const [q, setQ] = React.useState('');
    const [bumpFilter, setBumpFilter] = React.useState(null); // 'MAJOR' | 'MINOR' | 'PATCH' | null
    const counts = React.useMemo(() => {
      const c = { MAJOR: 0, MINOR: 0, PATCH: 0 };
      VERSION_NOTES.forEach(e => { if (e.bump && c[e.bump] !== undefined) c[e.bump]++; });
      return c;
    }, []);
    const filtered = VERSION_NOTES.filter(e => {
      if (bumpFilter && e.bump !== bumpFilter) return false;
      if (!q) return true;
      const blob = `${e.version} ${e.date} ${e.summary} ${(e.specs||[]).join(' ')} ${e.items.join(' ')}`.toLowerCase();
      return blob.includes(q.toLowerCase());
    });
    return (
      <>
        <div className="cl-filter-row">
          <span className={`chip tone-info ${bumpFilter ? 'dim' : ''}`}
                role="button" tabIndex={0}
                onClick={() => setBumpFilter(null)}>
            <span className="chip-label">All</span>
            <span className="chip-value">{VERSION_NOTES.length}</span>
          </span>
          {['MAJOR', 'MINOR', 'PATCH'].map(b => {
            const tone = b === 'MAJOR' ? 'err' : b === 'MINOR' ? 'info' : 'ok';
            return (
              <span
                key={b}
                className={`chip tone-${tone} ${counts[b] === 0 ? 'dim' : ''}`}
                data-active={bumpFilter === b}
                role="button" tabIndex={0}
                onClick={() => setBumpFilter(bumpFilter === b ? null : b)}
              >
                <span className="chip-label">{b}</span>
                <span className="chip-value">{counts[b]}</span>
              </span>
            );
          })}
          <span className="spacer" />
          <input
            type="search"
            className="hiw-search"
            placeholder="search…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="cl-list">
          {filtered.map((e, i) =>
            <ChangelogEntry key={e.version} entry={e} defaultOpen={i === 0 && !q && !bumpFilter} />
          )}
        </div>
      </>
    );
  }

  // ─── Main overlay ─────────────────────────────────────────────

  function HowItWorks({ open, onClose }) {
    const [view, setView] = React.useState('how');
    const triggerRef = React.useRef(null);

    React.useEffect(() => {
      if (!open) return;
      function onKey(e) {
        if (e.key === 'Escape') { e.stopPropagation(); onClose(); }
      }
      window.addEventListener('keydown', onKey, true);
      return () => window.removeEventListener('keydown', onKey, true);
    }, [open, onClose]);

    React.useEffect(() => {
      if (open) triggerRef.current = document.activeElement;
      else if (triggerRef.current) { triggerRef.current.focus(); triggerRef.current = null; }
    }, [open]);

    if (!open) return null;

    return (
      <div
        className="md-dialog__scrim"
        onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        role="dialog"
        aria-modal="true"
        aria-label="How it works"
      >
        <div className="md-dialog md-dialog--rich" style={{ maxHeight: '92vh', overflow: 'hidden' }}>
          <div className="dr-modal-header">
            <h2>How it works</h2>
            <span className="spacer" />
            <div className="dr-modal-tabs" role="tablist">
              <button
                className={'tab' + (view === 'how' ? ' is-active' : '')}
                role="tab"
                onClick={() => setView('how')}
              >How it works</button>
              <button
                className={'tab' + (view === 'changelog' ? ' is-active' : '')}
                role="tab"
                onClick={() => setView('changelog')}
              >Changelog</button>
            </div>
            <button
              type="button"
              className="md-btn md-btn--text md-btn--sm dr-modal-close"
              onClick={onClose}
              aria-label="Close"
            >×</button>
          </div>

          <div className="hiw-overlay__layout">
            <nav className="hiw-overlay__menu" aria-label="Section navigation">
              <ul className="hiw-overlay__menu-list">
                {view === 'how'
                  ? HIW_SECTIONS.map((s, i) =>
                      <li key={s.id}>
                        <a href={`#${s.id}`}>
                          <span className="menu-section-num">{i + 1}</span>{s.label}
                        </a>
                      </li>)
                  : VERSION_NOTES.slice(0, 10).map(e =>
                      <li key={e.version}>
                        <a href={`#cl-${e.version.replace(/\./g, '')}`}>
                          <span className="menu-section-num">{e.version}</span>{e.summary.slice(0, 32)}
                        </a>
                      </li>)
                }
              </ul>
            </nav>

            <div className="hiw-overlay__content">
              {view === 'how' ? (
                <div className="hiw">
                  <ProtocolOverviewSection />
                  {PHASES.map(p => <PhaseSection key={p.anchor} phase={p} />)}
                  <ModalAnatomySection />
                  <ItemTaxonomySection />
                  <ItemLifecycleSection />
                  <ConvergenceSection />
                  <CostSection />
                </div>
              ) : (
                <ChangelogList />
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Vestigial — legacy onboarding tour and a few deep-links still hit
  // HowItWorksPage. Keep it as a no-op that redirects to the overlay.
  function HowItWorksPage() {
    React.useEffect(() => {
      if (typeof window === 'undefined') return;
      const ev = new CustomEvent('dr-open-how-it-works');
      window.dispatchEvent(ev);
    }, []);
    return null;
  }

  window.HowItWorks = HowItWorks;
  window.HowItWorksPage = HowItWorksPage;
})();
```

### 10.3 — Implementation note on sections 7–11

For spec readability, the five non-phase section components (`ModalAnatomySection`, `ItemTaxonomySection`, `ItemLifecycleSection`, `ConvergenceSection`, `CostSection`) are shown above as one-line `return null` stubs. The actual file substitutes the literal JSX from the **mockup HTML** at `design-system/audits/2026-05-20-hiw-rework/mockup.html` (lines 432–875). Translation is mechanical:

- Replace HTML `class="..."` with JSX `className="..."`.
- Replace `<img data-diagram="07-modal-anatomy" alt="..." />` with `<HiwDiagram name="07-modal-anatomy" alt="..." />`.
- Wrap loose content nodes in JSX fragments where needed.
- Keep all chip CSS classes verbatim.

The mockup is the visual source of truth; the implementation is a 1-to-1 translation. **The acceptance criterion in § 15.3 is "rendered live page matches the mockup screenshot pixel-for-pixel modulo browser variance" — that's the verification gate.**

---

## 11. Implementation — CSS additions to `components.css`

### 11.1 — Where to append

Append a single block to the end of `src/dual_research/ui/static/components.css`, fenced with the spec marker convention:

```css
/* =============================================================
   SPEC-0121 — How-It-Works overlay + Changelog tab
   Layout, structural, and content classes for the rewritten
   how-it-works.jsx. All chip / card / collapsible primitives
   are reused unchanged from earlier specs (0094 + 0096 + 0119).
   ============================================================= */
```

### 11.2 — Drop-in CSS

The CSS classes used by the new JSX (lifted verbatim from the verified mockup HTML at `design-system/audits/2026-05-20-hiw-rework/mockup.html`):

```css
/* Layout */
.hiw { display: flex; flex-direction: column; gap: var(--s-8); }
.hiw-sec { scroll-margin-top: 80px; }

.hiw-overlay__layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 0;
  min-height: 600px;
}
.hiw-overlay__menu {
  border-right: 1px solid var(--border-1);
  padding: var(--s-5) var(--s-4);
  background: var(--bg-1);
  position: sticky; top: 0;
}
.hiw-overlay__menu-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.hiw-overlay__menu-list a {
  display: block; padding: 6px 10px;
  border-radius: var(--r-2);
  color: var(--fg-2); text-decoration: none;
  font-size: var(--t-meta);
}
.hiw-overlay__menu-list a:hover { color: var(--fg-0); background: var(--bg-2); }
.hiw-overlay__menu-list .menu-section-num {
  display: inline-block; width: 18px; color: var(--fg-3);
  font-family: var(--mono); font-size: var(--t-mono);
}
.hiw-overlay__content {
  padding: var(--s-6) var(--s-8);
  overflow-y: auto;
  max-height: 80vh;
}

/* Header chrome */
.dr-modal-header {
  padding: var(--s-4) var(--s-6);
  display: flex; align-items: center; gap: var(--s-4);
  border-bottom: 1px solid var(--border-1);
  background: var(--bg-1);
}
.dr-modal-header h2 {
  margin: 0; font-size: var(--t-title); font-weight: var(--w-semi);
  color: var(--fg-0);
}
.dr-modal-header .spacer { flex: 1; }
.dr-modal-tabs {
  display: inline-flex; gap: 2px;
  background: var(--bg-2); padding: 2px;
  border-radius: var(--r-2);
}
.dr-modal-tabs .tab {
  appearance: none; background: transparent; border: none;
  padding: 6px 14px; border-radius: var(--r-2);
  font-family: var(--sans); font-size: var(--t-body); font-weight: var(--w-medium);
  color: var(--fg-2); cursor: pointer;
}
.dr-modal-tabs .tab.is-active { background: var(--bg-1); color: var(--fg-0); box-shadow: var(--e-1); }
.dr-modal-close {
  appearance: none; background: transparent; border: 1px solid var(--border-1);
  width: 32px; height: 32px; border-radius: var(--r-2);
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; color: var(--fg-2); font-size: 18px;
}

/* Collapsible section */
.cs-section {
  border-top: 1px solid var(--border-1);
  padding-top: var(--s-5);
}
.cs-section:first-child { border-top: none; padding-top: 0; }
.cs-header {
  display: flex; align-items: center; gap: var(--s-3);
  cursor: pointer; user-select: none;
  padding: var(--s-2) 0;
}
.cs-chevron {
  width: 16px; height: 16px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--fg-3);
  transition: transform var(--m-fast) var(--ease);
}
.cs-section.is-open .cs-chevron { transform: rotate(90deg); }
.cs-title {
  font-size: var(--t-h3); font-weight: var(--w-semi);
  color: var(--fg-0);
  display: flex; align-items: center; gap: var(--s-3);
  flex: 1;
}
.cs-body { padding: var(--s-3) 0 var(--s-5) 28px; display: none; }
.cs-section.is-open .cs-body { display: block; }

/* Lede + section title */
.lede {
  font-size: var(--t-body); line-height: var(--lh-prose);
  color: var(--fg-1);
  margin: 0 0 var(--s-5) 0;
}
.hiw-section-title {
  display: inline-flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
}

/* TL;DR card grid */
.hiw-tldr {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--s-3);
  margin-bottom: var(--s-5);
}
.dr-card {
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-3);
}
.dr-card-body { padding: var(--s-4); }
.dr-card-body h4 {
  margin: 0 0 var(--s-2) 0;
  font-size: var(--t-body); font-weight: var(--w-semi);
  color: var(--fg-0);
}
.dr-card-body p {
  margin: 0; font-size: var(--t-meta); color: var(--fg-2); line-height: var(--lh-snug);
}

/* Diagram embed */
.hiw-diagram {
  margin: var(--s-5) 0;
  padding: var(--s-3);
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-3);
}
.hiw-diagram img { width: 100%; height: auto; display: block; }
.hiw-caption {
  font-size: var(--t-meta); color: var(--fg-3);
  margin: var(--s-2) 0 0 0; font-style: italic;
}

/* Chip row */
.chip-row { display: flex; flex-wrap: wrap; gap: var(--s-2); align-items: center; }
.chip-row + .chip-row { margin-top: var(--s-2); }

/* Input / output lists */
.hiw-input-list, .hiw-output-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: var(--s-2);
}
.hiw-input-list li, .hiw-output-list li {
  display: flex; align-items: center; gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-2);
}
.hiw-input-name { font-size: var(--t-body); color: var(--fg-1); flex: 1; }
.hiw-input-note { font-size: var(--t-meta); color: var(--fg-3); font-style: italic; }
.hiw-muted { color: var(--fg-3); font-style: italic; }

/* Note callout */
.hiw-note {
  border-left: 3px solid var(--info);
  background: var(--bg-2);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-2);
  margin: var(--s-3) 0;
  font-size: var(--t-body);
  color: var(--fg-1);
}
.hiw-note[data-tone="warn"] { border-left-color: var(--warn); }
.hiw-note[data-tone="err"]  { border-left-color: var(--err);  }
.hiw-note[data-tone="ok"]   { border-left-color: var(--ok);   }
.hiw-note[data-tone="idle"] { border-left-color: var(--idle); }
.hiw-note__label {
  font-size: var(--t-mono); text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--fg-3); margin-right: var(--s-2); font-weight: var(--w-semi);
}

/* Table */
.hiw-table { width: 100%; border-collapse: collapse; font-size: var(--t-body); }
.hiw-table th, .hiw-table td {
  text-align: left; padding: var(--s-2) var(--s-3);
  border-bottom: 1px solid var(--border-1);
  vertical-align: top;
}
.hiw-table th {
  background: var(--bg-2);
  font-weight: var(--w-semi); color: var(--fg-2);
  font-size: var(--t-meta); text-transform: uppercase; letter-spacing: 0.06em;
}
.hiw-table td.num { font-variant-numeric: tabular-nums; }

/* Code block */
.hiw-code {
  font-family: var(--mono); font-size: var(--t-mono);
  background: var(--bg-2); padding: var(--s-3) var(--s-4);
  border-radius: var(--r-2); overflow-x: auto;
  margin: var(--s-3) 0; color: var(--fg-1);
  border: 1px solid var(--border-1);
}

/* Changelog */
.cl-list { display: flex; flex-direction: column; gap: var(--s-4); }
.cl-filter-row {
  display: flex; align-items: center; gap: var(--s-2);
  padding: var(--s-3) 0;
  border-bottom: 1px solid var(--border-1);
  margin-bottom: var(--s-4);
}
.cl-filter-row .spacer { flex: 1; }
.hiw-search {
  background: var(--bg-2); border: 1px solid var(--border-1);
  border-radius: var(--r-pill);
  padding: 4px 12px; font-size: var(--t-meta);
  color: var(--fg-1); font-family: var(--sans);
  width: 200px;
}
.changelog-head {
  display: flex; align-items: center; gap: var(--s-3);
  flex-wrap: wrap; flex: 1;
}
.changelog-date {
  color: var(--fg-3); font-family: var(--mono); font-size: var(--t-mono);
}
.changelog-summary {
  color: var(--fg-0); font-size: var(--t-body); font-weight: var(--w-semi);
  flex: 1;
}
.changelog-bullets {
  list-style: disc; padding-left: var(--s-5); margin: var(--s-2) 0 0 0;
  color: var(--fg-1); font-size: var(--t-body); line-height: var(--lh-snug);
}
.changelog-bullets li + li { margin-top: var(--s-2); }
.changelog-bullets li strong { color: var(--fg-0); font-weight: var(--w-semi); }
.changelog-shots {
  display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3);
  margin-top: var(--s-3);
}
.changelog-shots figure {
  margin: 0; background: var(--bg-2);
  border: 1px solid var(--border-1); border-radius: var(--r-2);
  padding: var(--s-2); overflow: hidden;
}
.changelog-shots figure img {
  width: 100%; height: auto; display: block;
  border-radius: var(--r-1);
}
.changelog-shots figcaption {
  font-size: var(--t-meta); color: var(--fg-3);
  margin-top: var(--s-2); text-align: center;
}
.changelog-spec-link { margin-top: var(--s-3); }
```

**Light-mode overrides:** none needed. Every color reads from a token (`--fg-*`, `--bg-*`, `--border-*`, `--info`, `--warn`, `--err`, `--idle`, `--ok`) and tokens flip automatically via `body.light` in `tokens.css`. The implementation pass MUST verify by toggling theme — if any element loses contrast, the bug is a hardcoded color slipping in.

---

## 12. Implementation — VERSION_NOTES backfill data

### 12.1 — Strategy

The existing `VERSION_NOTES` array (in `how-it-works.jsx` lines 16–677) stops at v1.2.0 / spec 0117. Three new entries prepend to the front of the array (newest-first ordering preserved). The existing entries v1.2.0 → v0.18.0 are kept verbatim — no edits to the older release notes.

Each new entry uses the canonical shape:

```js
{
  version: '<semver>',
  date: '<YYYY-MM-DD>',
  bump: 'MAJOR' | 'MINOR' | 'PATCH',
  specs: ['<NNNN>', ...],          // spec IDs without leading zeros stripped
  specPath: '/specs/<filename>',   // deep-link to the spec
  summary: '<one-line>',
  items: [
    '<bullet-as-html-string>',     // dangerouslySetInnerHTML — allows <strong>, <code>, <span class="chip">
    ...
  ],
  screenshots: [                   // optional; only for the 3 newest entries
    { path: '/changelog-shots/<v>/<surface>.dark.png',
      alt: '...', caption: '...' },
    ...
  ],
}
```

### 12.2 — The three new entries (drop-in)

```js
// ─── New entries (prepend to the VERSION_NOTES array, newest-first) ───

{
  version: '1.4.1',
  date: '2026-05-20',
  bump: 'PATCH',
  specs: ['0120'],
  specPath: '/specs/0120-turn-modal-items-panel-rework.md',
  summary: 'Turn-modal items panel rework — provider chip + Anchor/Title/Rationale split + Claims panel removed.',
  items: [
    '<strong>Provider chip on every item card.</strong> Each card in the turn-modal right pane now begins with a <span class="chip tone-claude no-dot"><span class="chip-label">Claude</span></span> or <span class="chip tone-gpt no-dot"><span class="chip-label">GPT</span></span> chip so you can see at a glance who raised the item.',
    '<strong>Three labelled body segments.</strong> Each card body splits into <strong>Anchored to &lt;agent&gt;\'s draft</strong> (the quoted reference), <strong>Title</strong> (the one-line bold summary), and <strong>Rationale</strong> (the elaborating paragraph). Labels are small caps so the body stays visually quiet.',
    '<strong>Claims panel removed</strong> from new-protocol render paths. Legacy renderer (for pre-0114 runs) unchanged.',
    '<strong>Panel headers use spec-0119 category chips.</strong> "Questions 5" panel header is now <span class="chip tone-info no-dot"><span class="cat-bubble">Q</span><span class="chip-label">Questions</span><span class="chip-value">5</span></span> — identical to the critique pane\'s filter legend.',
    '<strong>Sources widget unchanged.</strong> When an item carries evidence, the existing SourceRow renders verbatim.',
  ],
  screenshots: [
    { path: '/changelog-shots/1.4.1/turn-modal-right-pane-before.dark.png',
      alt: 'pre-0120 raw-markdown turn-modal card',
      caption: 'before: raw markdown body' },
    { path: '/changelog-shots/1.4.1/turn-modal-right-pane-after.dark.png',
      alt: 'post-0120 labelled-segment turn-modal card',
      caption: 'after: Anchor / Title / Rationale labelled' },
  ],
},

{
  version: '1.4.0',
  date: '2026-05-20',
  bump: 'MINOR',
  specs: ['0119'],
  specPath: '/specs/0119-badge-governance.md',
  summary: 'Badge governance — unified <Chip> primitive + canonical vocabulary (Q/D/I/C bubbles, lifecycle verb chips, never-bare status).',
  items: [
    '<strong>One Chip primitive.</strong> Eight pre-0119 chip-like JSX patterns and their CSS rules deleted. shared.jsx\'s &lt;Chip&gt; gains a slot API: leadingDot / leadingIcon / categoryBubble, then label / value / +add / −sub / trailingSuffix, plus iconOnly / dim / mono / shape / size modifiers.',
    '<strong>Category bubble icon glyph.</strong> Q / D / I / C render as a 14 px filled circle with a knockout-white letter (designed icon, not a raw abbreviation). Fixed color map (Q=info, D=warn, I=err, C=idle) and fixed order (Q→D→I→C). The critique-pane filter row at the top is the canonical legend.',
    '<strong>Never-bare status.</strong> Every completed timeline card carries a right-aligned status chip — running / ✓ agreed / ✓ / queued.',
    '<strong>Provider + activity split.</strong> The combined .qref qref-full span replaced by two adjacent chips — <span class="chip tone-claude no-dot"><span class="chip-label">Claude</span></span> and <span class="chip mono tone-neutral no-dot">turn 1</span>.',
    '<strong>Cross-pane chip jumps.</strong> Clicking a category chip on a timeline turn card fires a dr-critique-jump event; the critique pane applies the matching filter and scrolls into view.',
    '<strong>Phase-header chip cluster.</strong> Each visible phase header carries a right-aligned aggregate-across-both-agents category-summary chip cluster.',
    '<strong>Vocabulary cleanup.</strong> Strict per-spec removal of the legacy claim data path. \'conceded\', \'answered\', \'noted\', \'ghosted\', \'repair\', legacy abbreviations QCR1 / OQ / BD / OI all gone.',
    '<strong>Lifecycle-verbs.js helper.</strong> Mirrors contract/lifecycle.py:TRANSITIONS; cross-language sync test enforces it.',
    '<strong>Backend untouched.</strong> No edits to contract/, orchestrator/, protocol/, or events/.',
  ],
  screenshots: [
    { path: '/changelog-shots/1.4.0/critique-pane-filter-row.dark.png',
      alt: 'critique-pane chip-only filter legend',
      caption: 'chip-only filter legend (the canonical category vocabulary)' },
    { path: '/changelog-shots/1.4.0/timeline-card-header.dark.png',
      alt: 'timeline turn card header',
      caption: 'provider + turn + status chips' },
    { path: '/changelog-shots/1.4.0/phase-header-chip-cluster.dark.png',
      alt: 'phase-header chip cluster',
      caption: 'aggregate Q/D/I/C across both agents' },
  ],
},

{
  version: '1.3.0',
  date: '2026-05-20',
  bump: 'MINOR',
  specs: ['0118'],
  specPath: '/specs/0118-deep-research-consumption-and-cost-tracking.md',
  summary: 'Consumption tab redesign + canonical-piece aggregation + per-piece proportional cost tracking.',
  items: [
    '<strong>Canonical-piece keys</strong> replace the legacy 7-key vocabulary (brief / d1 / d2 / plan / hist / draft / histp). Each per-turn TurnEnded event\'s promptPieces now keys by spec-0117 artifact registry IDs.',
    '<strong>Per-phase grouping rules (NORMATIVE).</strong> Always-separate rows: user_prompt + System prompt aggregate. Phase-specific separate rows include phase1.claude / phase1.openai (P2/P3), all_p2_turns (P3), current_draft + prior_turns.phase4 (P4).',
    '<strong>Total bar shows exact billed numbers.</strong> Tokens + cost = exact API-billed values. The cache-reuse stripe (45° overlay at 0.5 opacity) renders over cache_read_tokens proportion.',
    '<strong>Per-piece cost is proportional.</strong> pieceCost = (pieceTokens / billedInputTokens) × totalInputCost. Tooltip annotates (proportional).',
    '<strong>System prompt aggregate.</strong> Per-phase system.task.* + prior_turns.* + ledger.standing_items + closeout.request rolled into a single "System prompt" row with hover tooltip showing the per-sub-artifact breakdown.',
    '<strong>Collapsed vs unfolded card.</strong> Collapsed: single "Total tokens" bar with <tokens>t · $<cost>, cache-reuse meta line. Unfolded: 3-column grid per row (description · bar · tokens·cost).',
  ],
  screenshots: [
    { path: '/changelog-shots/1.3.0/cost-card-collapsed.dark.png',
      alt: 'collapsed cost card',
      caption: 'collapsed: total bar with cache-reuse stripe' },
    { path: '/changelog-shots/1.3.0/cost-card-unfolded.dark.png',
      alt: 'unfolded cost card',
      caption: 'unfolded: per-piece rows + System prompt tooltip' },
  ],
},

// ─── (existing entries v1.2.0 → v0.18.0 below, kept verbatim) ───
```

### 12.3 — Older entries

Older entries (v1.2.0 through v0.18.0) **are not migrated to the new shape with `bump`, `specs`, `specPath`, and `screenshots` fields.** The `ChangelogEntry` component handles their absence gracefully — `entry.bump` falsy → bump chip is suppressed; `entry.specs` undefined → spec chips are absent; `entry.screenshots` undefined or empty → the screenshots block doesn't render; `entry.specPath` undefined → the "Open spec" button is absent.

This means the new entries display with full chrome; older entries display in a more compact form. No retroactive editing of historical release notes.

### 12.4 — Screenshot capture protocol

The 9 screenshots referenced from the three new entries are captured during the implementation pass:

1. Start the dev server: `make dev` (or `uv run python -m dual_research.ui.server`).
2. Load fixture run: `runs/2026-05-19-deep-research-fixture` (or the most recent end-to-end run with both Phase 2 + Phase 4 data; pin the exact path before capture).
3. For each screenshot in the table below, navigate to the surface and take a `1440 × auto` viewport screenshot in **both** themes (dark = default; toggle to light via the avatar menu density toggle or `body.classList.add('light')` in devtools). Capture mode: full surface, not viewport-clipped.
4. Save the dark variant to `src/dual_research/ui/static/changelog-shots/<version>/<surface>.dark.png` and the light variant to `<surface>.light.png`.
5. The static UI server serves `/changelog-shots/<...>` automatically (any path under `static/` is exposed).

Capture targets:

| File | Surface | How to reach it |
|---|---|---|
| `1.4.1/turn-modal-right-pane-before.dark.png` | Pre-0120 raw-markdown card | (already captured during 0120 design — copy from `design-system/audits/2026-05-19-spec-0120/`) |
| `1.4.1/turn-modal-right-pane-after.dark.png` | Post-0120 labelled-segment card | Run-detail / Phase 2 turn 5 / right pane, scroll to first Questions card |
| `1.4.0/critique-pane-filter-row.dark.png` | Spec-0119 chip-only legend | Run-detail / Critique tab, top filter row |
| `1.4.0/timeline-card-header.dark.png` | Provider + turn + status chips | Run-detail / Timeline tab, any Phase 2 turn card |
| `1.4.0/phase-header-chip-cluster.dark.png` | Aggregate Q/D/I/C per phase | Run-detail / Timeline tab, Phase 4 header row |
| `1.3.0/cost-card-collapsed.dark.png` | Total bar with cache-reuse stripe | Run-detail / Consumption tab, any collapsed per-turn card |
| `1.3.0/cost-card-unfolded.dark.png` | Per-piece + System prompt | Run-detail / Consumption tab, click any card to unfold |
| (additional 2 light variants for the entries above) | (same surfaces in light theme) | toggle theme first |

If a target surface doesn't exist on the chosen fixture run, run a fresh end-to-end test (`/dual-research-run` skill) and pin that new run as the canonical fixture.

---

## 13. Deletion list (existing JSX to retire)

The following symbols are removed from `src/dual_research/ui/static/how-it-works.jsx` in the full-file rewrite. Line numbers are approximate (pre-0121 file).

| Symbol | Lines (approx) | Replaced by |
|---|---|---|
| `VERSION_NOTES` (old structure, last entry v1.2.0) | 16–677 | New `VERSION_NOTES` per § 12 (3 new entries prepended; older entries kept) |
| `AgentDisc` | 681–701 | (deleted — was unreferenced) |
| `ClaudeDisc` | (~683) | (deleted — was unreferenced) |
| `GptDisc` | (~691) | (deleted — was unreferenced) |
| `Arrow`, `ArrowDefs` | 703–724 | (deleted — used only by `PhaseStrip` / `NegotiationRoundDiagram`, both deleted) |
| `PhaseStrip` | 725–765 | Diagram 1 (`01-pipeline.{light,dark}.svg`) |
| `NegotiationRoundDiagram` | 769–841 | Diagram 3 (`03-item-lifecycle.{light,dark}.svg`) + Diagram 6 (`06-convergence.{light,dark}.svg`) |
| `TldrCards` | 845–873 | Inline JSX in `ProtocolOverviewSection` (§ 10.2) |
| `Tk` | (~875) | Plain `<span className="chip mono tone-...">` per § 11 |
| `CallBox` | 885–933 | Inline JSX in `PhaseSection` (§ 10.2) |
| `LifecycleRow` | 935–958 | Diagram 3 |
| `ChatLifecycle` | 961–1124 | Diagram 2 (`02-phase-inputs.{light,dark}.svg`) — embedded once per phase |
| `Legend` | (~1126) | (deleted — visual legend lives in Diagram 1's footer strip) |
| `ComparePanel` | 1125–1178 | (deleted — was defined but never rendered) |
| `ContextGrowthBars` | 1180–1310 | Diagram 5 (`05-cost-flow.{light,dark}.svg`) |
| `PhaseMeta` | (~1312) | Plain JSX in `PhaseSection` |
| `PhaseAccordion` | (~1314) | `CollapsibleSection` (§ 10.2) |
| `Faq` | (~1330) | (deleted — questions are inlined into prose where relevant) |
| `Section` | 1335–1355 | `CollapsibleSection` |
| `useThemeMode` (old) | 1357–1380 | New `useThemeMode` in `HiwDiagram` module (§ 10.2) — identical implementation, kept local |
| `ProtocolOverviewMap` | 1381–1395 | `HiwDiagram name="01-pipeline" ...` |
| `ProtocolOverviewFold` | 1396–1442 | `HiwDiagram name="01-pipeline" ...` (no fold-out — the diagram is always visible) |
| `ReleaseNote` | 1446–1499 | New `ChangelogEntry` (§ 10.2) |
| `HIW_SECTIONS` (old labels) | (~1502) | New `HIW_SECTIONS` per § 10.2 with the 11 new entries |
| `HiwSection` | (~1510) | `CollapsibleSection` (§ 10.2) |
| old `ChangelogEntry` | (~1520) | New `ChangelogEntry` (§ 10.2) |
| `HowItWorks` (body, not the function shell) | 1536–1805 | New body per § 10.2 |
| `HowItWorksPage` | 1808–1819 | Same role, simplified to a no-op event-dispatcher (§ 10.2) |

**Sanity-check command** (run after the rewrite to confirm all old symbols are gone):

```bash
git grep -n "PhaseStrip\|NegotiationRoundDiagram\|ContextGrowthBars\|ChatLifecycle\|LifecycleRow\|CallBox\|TldrCards\|ComparePanel\|^function Section\|function Legend\|^const Tk\|ProtocolOverviewMap\|ProtocolOverviewFold\|ReleaseNote\|HiwSection\|Faq\b\|AgentDisc\|ClaudeDisc\|GptDisc" src/dual_research/ui/static/how-it-works.jsx
# expected: 0 hits
```

---

## 14. Files touched (exhaustive)

| Path | Status | Change |
|---|---|---|
| `specs/0121-how-it-works-and-changelog-rework.md` | **created** | This spec. |
| `diagrams/how-it-works/01-pipeline.{light,dark}.svg` | **created** | Diagram 1 — full protocol pipeline. |
| `diagrams/how-it-works/02-phase-inputs.{light,dark}.svg` | **created** | Diagram 2 — per-phase input composition. |
| `diagrams/how-it-works/03-item-lifecycle.{light,dark}.svg` | **created** | Diagram 3 — item lifecycle state machine. |
| `diagrams/how-it-works/04-categories.{light,dark}.svg` | **created** | Diagram 4 — category taxonomy + chip composition. |
| `diagrams/how-it-works/05-cost-flow.{light,dark}.svg` | **created** | Diagram 5 — cost calculation flow. |
| `diagrams/how-it-works/06-convergence.{light,dark}.svg` | **created** | Diagram 6 — convergence + escape hatches. |
| `diagrams/how-it-works/07-modal-anatomy.{light,dark}.svg` | **created** | Diagram 7 — turn-modal anatomy. |
| `design-system/audits/2026-05-20-hiw-rework/mockup.html` | **created** | Clickable visual reference (the JSX target). |
| `src/dual_research/ui/static/how-it-works.jsx` | **rewritten** | Full-file replacement per § 10.2. Drop the symbols in § 13. |
| `src/dual_research/ui/static/components.css` | **appended** | New spec-0121 block per § 11.2. |
| `src/dual_research/ui/static/changelog-shots/{1.3.0,1.4.0,1.4.1}/*.{light,dark}.png` | **created** | 9 screenshots × 2 themes per § 12.4. Captured at PR-open time. |
| `src/dual_research/ui/static/index.html` | **modified** | Cache-bust bump `?v=0120b → ?v=0121a` on all static asset references. |
| `src/dual_research/__init__.py` | **modified** | `__version__ = "1.5.0"` at PR-merge time. |
| `CHANGELOG.md` | **modified** | New `[1.5.0]` entry under `### Added` describing this spec's scope. |
| `src/dual_research/ui/static/diagrams/deep-research-pipeline.{light,dark}.svg` | (unchanged) | Orphaned by this rewrite but not deleted. OQ-1 defers. |

No backend files. No `pyproject.toml`. No migrations. No new dependencies. No edits to `shared.jsx`, `tokens.css`, `theme.css`, `run-detail.jsx`, or any other JSX surface.

---

## 15. Acceptance criteria

### 15.1 — Spec + diagram artifacts

- [ ] `specs/0121-how-it-works-and-changelog-rework.md` present and follows the standard spec template.
- [ ] All 14 SVG files (7 diagrams × {light, dark}) present under `diagrams/how-it-works/`.
- [ ] Each light/dark pair consistent in content and layout (only color / theme tokens differ).
- [ ] Every diagram self-contained: no external font dependencies, no script, no `<foreignObject>` HTML.
- [ ] Every diagram opens cleanly in Safari + Chrome + Firefox.
- [ ] Provider colors match the running app's `--agent-a` / `--agent-b` tokens.
- [ ] Category bubble colors match `--info` / `--warn` / `--err` / `--idle` tokens.

### 15.2 — Mockup HTML

- [ ] `design-system/audits/2026-05-20-hiw-rework/mockup.html` opens in a browser as a fully styled, fully clickable page (no server required — `file://` works).
- [ ] Theme toggle flips `body.classList` and every chip + every diagram re-renders correctly.
- [ ] All 10 How-It-Works sections collapse and expand on click; first section open by default.
- [ ] All 7 diagrams embedded and visible in both themes.
- [ ] The Changelog tab shows the three new entries (1.3.0 / 1.4.0 / 1.4.1) plus at least 3 older entries.

### 15.3 — Live `how-it-works.jsx` rewrite (the PR landing)

- [ ] Loading `/how-it-works` in the running app renders the same 10 sections in the same order with the same prose as the mockup.
- [ ] All 7 diagrams embed via `<HiwDiagram>` and swap correctly on theme toggle.
- [ ] All collapsibles persist their open/closed state across page reload (localStorage `hiw:cs:<persistKey>`).
- [ ] The Changelog tab renders the three new entries with provider chips, bump chip, summary, and screenshot grid.
- [ ] Cache-bust query `?v=0121a` is present on every static asset reference in `index.html`.
- [ ] **Pixel verification:** screenshot of the live overlay vs the mockup HTML at 1440 × auto viewport, dark theme. Differences limited to: chip text wrapping (browser-dependent), diagram-img render edges (browser-dependent). No structural differences.

### 15.4 — Screenshot capture (per § 12.4)

- [ ] All 9 screenshots × 2 themes (= 18 PNG files) present under `src/dual_research/ui/static/changelog-shots/<version>/`.
- [ ] Each screenshot 1440 × auto viewport, captured in the documented theme.
- [ ] Every `screenshots[].path` in the new VERSION_NOTES entries resolves to a real file.

### 15.5 — Vocabulary scan

- [ ] `git grep -n -i "Preflight\|Independent research\|Plan negotiation\|Review loop" src/dual_research/ui/static/how-it-works.jsx` → 0 hits.
- [ ] `git grep -n -i "claim" src/dual_research/ui/static/how-it-works.jsx | grep -v '//' | grep -v 'spec-0121:vocab-ok'` → 0 hits.
- [ ] `git grep -n "CACHE_BREAKPOINT\|AGREED_PLAN SHA-256\|D-N identifiers" src/dual_research/ui/static/how-it-works.jsx` → 0 hits.
- [ ] Sanity-check command from § 13 (`git grep` for retired symbols) → 0 hits.
- [ ] Spec 0119's vocabulary-scan test (`tests/contract/test_ui_vocabulary.py`) continues to pass.

### 15.6 — Build / no regressions

- [ ] `uv run pytest tests/ -q` → green.
- [ ] No browser-console errors when opening the new overlay (Chrome devtools clean).
- [ ] Theme toggle does not throw `MutationObserver` errors when the overlay is unmounted and remounted.

---

## 16. Test plan

This spec ships the design AND the implementation in one PR. Test coverage is correspondingly two-tier:

**Design / artifact level:**

- [ ] **Diagram content review.** For each of the 7 diagrams, the brief in § 6 is compared verbatim against the rendered SVG. Every named element in the brief is present.
- [ ] **Cross-spec consistency.** The four-category Q/D/I/C model in § 5.4 matches spec 0119 § 5.2 verbatim. The lifecycle in § 5.5 matches spec 0114's lifecycle table. The cost formula in § 5.7 matches spec 0118's formula.
- [ ] **Mockup walkthrough (user).** User opens the mockup HTML, walks every section, opens / closes every collapsible, toggles theme. Visual sign-off before the implementation lands.

**Implementation level:**

- [ ] **Manual — live overlay walkthrough.** Open the running app, open the How-It-Works overlay via the right-side menu and via the avatar menu's "Replay tour → step 1". Walk all 10 sections + the Changelog tab. Confirm visual parity with the mockup.
- [ ] **Manual — theme toggle.** Click the avatar menu's theme toggle while the overlay is open. Every chip, every diagram, every section card outline updates. No flicker, no error.
- [ ] **Manual — collapsible persistence.** Close section 3 (Phase 1). Reload the page. Reopen the overlay. Section 3 is still closed.
- [ ] **Manual — keyboard navigation.** Tab through the section headers; Enter / Space toggles open/closed. Escape closes the overlay.
- [ ] **Manual — Changelog filters.** Click `MAJOR` / `MINOR` / `PATCH` filter chips; entry list filters. Type in the search box; entries filter on bullet text + summary + spec ID.
- [ ] **Cross-browser smoke.** Open the overlay in Safari, Chrome, Firefox. SVGs render; layout doesn't break.
- [ ] **Vocabulary scan.** Per § 15.5.
- [ ] **Sanity command.** Per § 13's `git grep` command — 0 hits for retired symbols.
- [ ] **Spec self-test.** `git grep "spec 0114\|spec 0115\|spec 0116\|spec 0117\|spec 0118\|spec 0119\|spec 0120"` in this spec returns at least one hit per spec.
- [ ] **No reuse check.** `git grep "deep-research-pipeline" src/dual_research/ui/static/how-it-works.jsx` returns 0 hits (the legacy SVG is not referenced by the new code).

---

## 17. Risks

- **Diagram brief drift.** Seven self-contained briefs are large surface area; if the live protocol changes between this spec and merge, a diagram could ship stale. Mitigation: the briefs cite specs 0114/0117/0118/0119 directly; if any of those change, the brief change is mechanical. The mockup is the verification gate.
- **Mockup-vs-live drift.** The mockup uses CSS copied from `components.css`; if `components.css` drifts before merge, the live JSX could render differently from the mockup the user signed off on. Mitigation: this spec ships both in one PR — the mockup, the JSX, and the CSS land together. The implementer reads from the live `components.css`, not the mockup's copy.
- **Screenshot fixture rot.** The fixture run we capture from could be deleted or its data shape could shift. Mitigation: § 12.4 pins the fixture run path at capture time. All 9 screenshots are captured in one session immediately before the PR opens, so they share a consistent data snapshot.
- **Cost diagram is the most novel.** Diagram 5 has no prior art in the repo. The brief is detailed but the skill may need a second pass if the rendered SVG misses something. Mitigation: this is one of the diagrams the user should inspect first.
- **Per-phase reuse of Diagram 2.** The same SVG is embedded under sections 2–6 with different captions; this is a deliberate IA simplification but could feel under-baked. Mitigation: if user feedback says "I want a custom diagram per phase", we add a `?phase=N` highlight overlay in a follow-up — the underlying SVG stays the same.
- **Legacy `deep-research-pipeline.svg` removal.** Leaving the file in `diagrams/` is harmless; deleting it could break out-of-tree references (other docs, Notion pages, screenshots in old Slack threads). Mitigation: leave it (zero cost, zero risk) — OQ-1 defers the decision.
- **`<SourceRow>` location.** The component lives in `run-detail.jsx`. The new overlay does not currently use it, but if a future section adds embedded evidence references it'll either need a lift to `shared.jsx` or a local duplicate. Mitigation: § 18 marks `<SourceRow>` as out-of-scope for this spec; OQ-4 defers.

---

## 18. Out of scope (explicit)

- **`<CHANGELOG.md>` reconciliation.** The repo-root `CHANGELOG.md` is the source of truth for release notes. This spec **also** updates `VERSION_NOTES` in `how-it-works.jsx` to render the same release notes in-app. If the two diverge in future releases, OQ-2 captures the long-term reconciliation question. (Short-term: this spec lands them in sync as of v1.4.1.)
- **Onboarding tour content.** The tour links to this overlay; the tour text itself is untouched. The tour positioning bug is patched separately as a hotfix; cross-referenced in § 20.
- **Right-side menu.** Reaches the overlay; chrome unchanged.
- **Modal shell (`<Modal variant="rich">`).** Spec 0096 + 0117 already wired it; this spec changes its contents, not its chrome.
- **`<SourceRow>` location refactor.** The component lives in `run-detail.jsx`. This spec does not lift it. OQ-4 defers.
- **The bundled `deep-research-pipeline.{light,dark}.svg`.** Orphaned by this rewrite but not deleted. OQ-1 defers.
- **Onboarding tour structural rewrite.** The hotfix in § 20.3 covers the immediate bug; the broader `popover-position.js` shared utility is deferred to a follow-up spec if other spotlight steps prove similarly broken.

---

## 19. Open questions

- **OQ-1.** Delete `diagrams/deep-research-pipeline.{light,dark}.svg` (and the bundled copies under `src/dual_research/ui/static/diagrams/`) once this spec's diagrams land, or leave them as orphaned references? *Default in this spec: leave them. They're not referenced after the rewrite but don't cost anything.*
- **OQ-2.** Should the overlay's `VERSION_NOTES` array be replaced by a runtime fetch + parse of `/CHANGELOG.md` so the two sources can't drift? *Default in this spec: no — `CHANGELOG.md` is markdown with prose nuances that don't render cleanly as bulleted entries, and a parser introduces a moving part. Backfilling the array manually is fine for now.*
- **OQ-3.** Which fixture run to capture the 9 changelog screenshots from? *Default in this spec: the most recent end-to-end fixture under `runs/`; the implementer pins the exact path before capture per § 12.4.*
- **OQ-4.** Lift `<SourceRow>` to `shared.jsx` so How-It-Works can use it cleanly? *Default in this spec: don't lift in this spec — the new overlay doesn't reference it. Revisit if a future section needs embedded evidence rows.*
- **OQ-5.** Should the per-phase sections have dedicated diagrams instead of all reusing the generic Diagram 2? *Default in this spec: reuse the generic one with per-section captions — the per-phase deltas are best shown by the input/output lists in prose, not by 5 near-duplicate SVGs. If user feedback during mockup review asks for per-phase SVGs, we commission them as a follow-up.*
- **OQ-6.** Should this spec also produce a "Glossary" section? Terms like `AGREED`, `ledger`, `closeout round`, `ghost cap`, `drafter` would all earn an entry. *Default in this spec: no — every term is defined in context where it first appears, and a glossary adds another surface to maintain.*

---

## 20. Adjacent diagnosis — Onboarding tour step 2 stuck-state (cross-ref)

During the spec 0121 design pass, a user-reported bug was investigated and patched as a hotfix outside this spec's scope. Recorded here for audit trail because the diagnosis touched the same design-system surface (the spec-0103 onboarding tour overlay; sibling to the spec-0102 + 0117 How-It-Works overlay this spec rewrites).

### 20.1 — Symptom

Fresh first-time login → onboarding tour auto-opens → step 1 (the modal) renders fine → user clicks **Continue** → step 2 fires, a dimming mask + cutout-ring render over the first run-row on `/runs` → **no callout box appears anywhere on screen.** User has nothing to click. Reproduces on every desktop login at viewports ≥ ~1200 px (i.e. every normal user).

### 20.2 — Root cause

`src/dual_research/ui/static/onboarding.jsx:199-206` (pre-fix):

```js
if (vw >= 1500) {
  calloutStyle = {
    position: 'fixed',
    top: anchorRect.top,
    left: anchorRect.right + 16,                              // 1
    width: 360,
    maxWidth: `calc(100vw - ${anchorRect.right + 32}px)`,     // 2
  };
}
```

Step 2's anchor (`[data-tour-anchor="run-row"]`, set on the first row in `run-list.jsx:426`) spans **the full width of the run-list pane** — so `anchorRect.right` is essentially the viewport right edge.

- **(1)** `left: anchorRect.right + 16` → callout positioned ~16 px past the viewport right edge.
- **(2)** `maxWidth: calc(100vw - (anchorRect.right + 32))` → evaluates to `100vw - (≈100vw + 32px)` ≈ `−32 px` → callout's max-width clamps to a non-positive value, collapsing the content area to zero width.

The mask, the cutout, and even the callout's DOM are all present and correct — but the callout has zero rendered area, positioned off-screen. From the user's perspective: a mask appears, with nothing to dismiss it.

The mask was a red herring. The bug is purely callout positioning.

### 20.3 — Fix shipped

Hotfix landed in commit-pending under `[Unreleased] / Fixed` in `CHANGELOG.md`. One file (`onboarding.jsx`), ~50 lines net change. Replaces the viewport-width-only branch with an overflow-aware positioner that picks the first side with enough space among `[right, below, left, above]` and clamps placement inside the viewport on both axes. Cache-bust `?v=0120a → ?v=0120b`.

Recovery for users on the broken build (pre-hotfix): press `Escape` (wired to dismiss the tour and set `dr_onboarded = true`), or run `localStorage.setItem('dr_onboarded', 'true'); location.reload();` in devtools.

### 20.4 — Structural follow-up (deferred)

The other spotlight steps (3, 5, 6, 7) likely have subtler variants of the same flaw on narrow viewports — they all use the same positioning logic. The tactical fix in § 20.3 covers every step, but the right structural answer is a small shared `popover-position.js` util that any anchored popover (tour callout today, future onboarding tooltips, future inline help bubbles) can reuse. Deferred to a follow-up spec if a second spotlight step is reported broken; not blocking on the spec-0121 rewrite.

### 20.5 — Why not folded into spec 0121

- **Scope mismatch.** Spec 0121 is a documentation-surface rewrite (`how-it-works.jsx` + Changelog). The bug is in `onboarding.jsx` — different file, different surface.
- **Urgency mismatch.** Spec 0121's implementation is gated on user verification of the clickable mockup. The onboarding bug was blocking every first-time user and shipped as a hotfix immediately.
- **Audit trail.** This section preserves the diagnosis + decision record without bloating spec 0121's primary scope.

---

## 21. Backend touched?

**no.** Pure frontend documentation surface.
