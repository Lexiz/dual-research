---
spec: 0111
title: Critique cards — bucket correctness, expanded-card scroll, badge cleanup, height parity with Timeline
label: bug
version-bump: PATCH
status: merged
target-version: 0.76.13
created: 2026-05-19
pr: "https://github.com/Lexiz/dual-research/pull/119"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0111 — Critique cards: bucket · scroll · badges · height

> Ship bucket: **Composed**
> Depends on: **0097, 0098, 0110**
> Complexity: **M**
> Targeted version bump: **PATCH** (four pre-test bug fixes to the Critique pane; no new features, no breaking changes).

## 1. Context

Source: [Notion · Known issues v2](https://www.notion.so/Known-issues-v2-36599f3e507f80a8ad5fdb26b143a695) — the user reported ten issues against the v2 Critique / Timeline / modal surfaces while pre-test polishing. The ten issues split into four coherent units of work; this spec resolves **the Critique-pane unit**: Notion issues **1, 2, 4, 5**. The remaining six are scheduled separately:

- Header text-overflow (Notion 3) → its own spec.
- Full-view modal vertical/horizontal fill (Notion 6, 7, 9) → its own spec.
- Turn / Cross-Review modal phase-stepper + input/output orientation + data correctness (Notion 8, 10) → its own spec.

The four issues in this spec all touch `QuestionThread` (the unified Critique card from spec 0097) and `CritiquePhaseContent` (the Open/Resolved/Drift accordion shell from spec 0098). Grouping them avoids re-touching the same files four times and keeps the diff reviewable as one Critique-pane patch.

### Notion issues addressed (verbatim user phrasing, abbreviated)

1. **Issue 1 — Expanded card body is clipped.** When a comment card inside Resolved is unfolded, its long body content extends past the visible container with no scroll affordance; the trailing text is unreachable.
2. **Issue 2 — `open` card filed under Resolved.** A card displaying an `open` status pill appears inside the Resolved accordion. The status pill on the card disagrees with the section it sits in.
3. **Issue 4 — Cluttered, duplicated, abbreviated badges.** The card-header badge row reads `Q · 01 · Claude · r1` + `resolved · r2` + `P2` — three pills carrying overlapping information in abbreviated form. User wants: type, raised-by, raised-on-round, resolved-in-round as four discrete pills, with no badge encoding two facts.
4. **Issue 5 — Critique cards are visibly taller than Timeline Phase 0 cards.** Same card content shape, different heights. The Timeline (shorter) height is the correct target; Critique cards must match.

## 2. Proposed change

Four sub-changes, in implementation order (lowest-risk first):

### 2.1 — Card height parity (Notion Issue 5)

**Current state.** Timeline `.card` (`components.css:216`) uses `padding: 6px 12px`. The Critique card `.qthread` (`components.css:494`) uses `padding: 16px 20px`. Same content shape, different paddings → different rendered heights.

**Fix.**

- Introduce a shared padding token in `src/dual_research/ui/static/tokens.css`:
  ```css
  --dr-card-pad-v: 6px;
  --dr-card-pad-h: 12px;
  ```
- Switch `.card` rule at `components.css:216` and `.qthread` rule at `components.css:494` to consume the token: `padding: var(--dr-card-pad-v) var(--dr-card-pad-h);`.
- Audit every other class that is rendered as a list-item card in Critique or Timeline (search: `.sc` at `components.css:1848`, `.crit-group__body > article`, `.tl-phase__body > *`) and route their vertical padding through the same token so future tweaks land in one place.

**Acceptance.** A Critique `.qthread` and a Timeline `.card` rendered with single-line content have the same computed `height` (±0 px) in DevTools.

### 2.2 — Bucket correctness (Notion Issue 2)

**Current state.** `pushItem()` at `src/dual_research/ui/static/run-detail.jsx:5837-5856` sorts each item into Drift / Open · new / Open · carried / Resolved. The Resolved branch fires whenever `it.status !== 'open'` — i.e. it is the implicit default. Any item whose status is missing, malformed, or any unexpected value falls into Resolved by accident. That matches the screenshot the user attached: a card with an `open` pill rendered inside the Resolved accordion.

**Backend status vocabulary** (discovered during implementation, per `src/dual_research/ui/models.py`):

- Questions: `'open' | 'answered'`. `'answered'` is the closure state.
- Issues: `'open' | 'resolved'`.
- Disagreements: `'open' | 'resolved-claude' | 'resolved-gpt' | 'resolved-both'`. Three variants encode which side conceded.
- Comments: no `status` field. Non-blocking commentary, "noted" forever.

The original implementation's `!== 'open'` accidentally routed all four kinds' closure states into Resolved correctly (because they're all not-`open`). My initial strict allow-list (`=== 'resolved'`) was too narrow and broke disagreements and questions; the predicate has to recognise the wider vocabulary.

**Fix.** Tighten the bucket predicate to a strict allow-list:

- Drift: `isDrift(it)` is true (unchanged).
- Open: `it.status === 'open' || it.status === 'open-new'`. Open · new vs Open · carried split by `round >= latestRound`.
- Resolved: matches `'resolved'`, `'answered'`, or any string starting with `'resolved-'` (covers the three disagreement variants). Encapsulated in a single `_isResolvedStatus(s)` helper so the predicate has one definition.
- Comments (`critiqueKind === 'c'`): always Resolved bucket. They have no closure protocol, but they are non-blocking — they belong with the items the user has already processed.
- Anything else (`undefined`, `null`, unexpected string): bucket under **Open · carried** (safest fallback — keeps unknown items visible to the user) and emit `console.warn('[critique] unknown item.status:', it.status, it)` in dev so the data desync is caught.

Also normalise comments inside `_normalizeToThread` so their thread-level `status` prop is `'resolved'` (not `'open'`). This is the actual root cause of Notion issue 2: comments were rendered as `status: 'open'` (warn-tinted pill) while being bucketed into Resolved (ok-tinted section) — a self-evident contradiction. With the normalisation, the pill matches the bucket.

Add a dev-only invariant inside `QuestionThread` (`src/dual_research/ui/static/shared.jsx:1029`) that fires when the card's `status` prop and the `data-tone` of its containing `.crit-group` disagree. The assertion logs to `console.error` with both values so a UI/data desync is immediately visible during development.

**Acceptance.** A run that includes at least one item with each kind (Q · D · I · C) and each closure state renders zero cards whose visible status pill conflicts with the surrounding accordion's tone. The dev-mode console emits no `unknown item.status` warnings and no `status/section mismatch` errors on the canonical run.

### 2.3 — Expanded-card body scroll (Notion Issue 1)

**Current state.** `QuestionThread` renders its expanded body (`<ol className="qt-timeline">`, `shared.jsx:1108`) inline inside the same `.qthread` article. Neither `.qthread`, `.qt-timeline`, nor `.crit-group__body` (`components.css:1841-1845`) sets a `max-height` or `overflow` rule. The parent `.crit2__body` carries `overflow: auto` (`components.css:2271`). In the screenshot the user attached, an expanded comment card has clearly long body text that the user reports as unscrollable inside the Resolved container.

**Fix.** Audit and unblock the scroll chain in the Critique pane:

- The Critique pane outer scroller is `.crv__body` (per spec 0098). Confirm it has `overflow-y: auto` AND no `max-height` ancestor that clips it shorter than the viewport's available height. If an ancestor sets `overflow: hidden` plus a bounded height, lift that constraint — the Critique pane should be free to grow to the viewport.
- For the expanded `.qthread` body specifically, do **not** introduce a local max-height + internal scroll. Two scroll regions one-inside-the-other on the same axis make the wheel target ambiguous and have been a recurring pain point. Instead, lean on the pane-level scroller.
- Verify the dialog/modal hosting case: when a `.qthread` is opened inside the Brief Critique full-view modal (spec 0110 modal primitive), the modal's `.dr-modal-body` already has `overflow: auto` per spec 0110 § 1 — same rule applies; no per-card scroll.

**Acceptance.** Open the longest-body item in any Critique bucket (Resolved included) on a 1400×900 viewport. The user must be able to scroll the pane until the very last line of the expanded card body is on screen, without the page itself scrolling past the pane's bottom edge.

### 2.4 — Badge cleanup (Notion Issue 4)

**Current state.** `QuestionThread` renders its header at `shared.jsx:1080-1104`:

```jsx
<header className="qt-head" onClick={onCardClick}>
  <QuestionRef
    id={threadKind === 'question' ? id : null}
    number={displayNum}
    raisedBy={raisedBy}
    round={raisedRound}
    kindLetter={kindLetter}
    format="full"
  />
  <Chip tone={statusTone}>{statusLabel}</Chip>
  {phase && <span className="md-chip md-chip--sm">P{phase}</span>}
  <span className="right">…chevron…</span>
</header>
```

With `format="full"`, `QuestionRef` (`shared.jsx:989-1019`) renders a single pill containing: kind letter (`Q`), number (`04`), agent badge (`[Claude]`), and round (`r1`). The next `<Chip>` adds status + a duplicated round-marker (`resolved · r3`). The phase chip adds an opaque `P2`. Net effect: one pill carries four facts (type, number, agent, raised-round); the next pill carries two facts (status, resolved-round); the phase chip is a cryptic two-character code.

**Fix.** Split the badge cluster into four discrete pills, each carrying exactly one fact, in this fixed order:

1. **Type + number** — pill reads `Q · 04` (or `D · 01`, `I · 02`, `C · 03`). No agent, no round.
2. **Raised by** — pill reads `Raised by Claude` (or `Raised by GPT`) with the agent icon. No round.
3. **Raised on round** — pill reads `Raised on round 1`.
4. **Status** — pill reads `Resolved in round 2` when `status === 'resolved'`; reads `Open` for `open`; `Open · new` for `open-new`; `Drift` for `drift`. The status tone (info/warn/ok/err) stays on the pill colour.
5. **Phase chip** — keep only if the card can be displayed outside its phase grouping; when nested inside a `.crit-group` whose header already names the phase, **drop the phase chip entirely**. Implementation: pass an explicit `showPhaseChip={false}` prop down from `CritiquePhaseContent` when rendering inside its own phase section, and default `true` for any out-of-context callsite (Σ Summary, search results, etc.).

Concretely:

- In `shared.jsx`, add a new format `format="split"` to `QuestionRef` that renders ONLY the type + number portion (`Q · 04`) and returns `null` for the agent and round sub-spans.
- In `QuestionThread`'s header (`shared.jsx:1080-1104`), replace the single `<QuestionRef format="full" />` with four sibling pills:
  ```jsx
  <QuestionRef … format="split" />
  <Chip tone="neutral">
    <AgentIcon agent={raisedBy} size={14} />
    Raised by {agentLabel}
  </Chip>
  <Chip tone="neutral">Raised on round {raisedRound}</Chip>
  <Chip tone={statusTone}>{verboseStatusLabel(status, lastRound)}</Chip>
  {showPhaseChip && phase && <span className="md-chip md-chip--sm">Phase {phase}</span>}
  ```
- `verboseStatusLabel(status, lastRound)`: a small helper that maps `'resolved' → 'Resolved in round ' + lastRound`, `'open' → 'Open'`, `'open-new' → 'Open · new'`, `'drift' → 'Drift'`.
- Replace the abbreviated `P{phase}` chip with the verbose `Phase {phase}` chip.

**Acceptance.** A Critique card renders four (or five, when the phase chip applies) discrete pills, none of which encodes two facts. No pill text contains `r1`-style abbreviations — rounds are spelled out as `round 1`. No pill text reads `P2` — phases are spelled out as `Phase 2`.

## 3. Files touched

- `src/dual_research/ui/static/tokens.css` — add `--dr-card-pad-v`, `--dr-card-pad-h` (§ 2.1).
- `src/dual_research/ui/static/components.css` — route `.card` (`:216`), `.qthread` (`:494`), `.sc` (`:1848`) padding through the new tokens (§ 2.1); audit and remove any ancestor `overflow: hidden` + bounded-height combo that clips `.crv__body` (§ 2.3).
- `src/dual_research/ui/static/shared.jsx` — extend `QuestionRef` with `format="split"` (`:989-1019`); rebuild `QuestionThread` header (`:1080-1104`) per § 2.4; add the dev-only status-vs-section invariant (§ 2.2).
- `src/dual_research/ui/static/run-detail.jsx` — tighten `pushItem()` predicate (`:5837-5856`) per § 2.2; pass `showPhaseChip={false}` down to `QuestionThread` from `CritiquePhaseContent` (§ 2.4).
- `src/dual_research/ui/static/__init__.py` — cache-bust `?v=…` → next.
- `src/dual_research/ui/static/index.html` — cache-bust to match.
- `pyproject.toml` — `0.76.12` → `0.76.13`.
- `CHANGELOG.md` — `0.76.13` entry.

## 4. Acceptance criteria

- [ ] **Issue 5 — Height parity.** Computed height of a `.qthread` rendered with one row of badges equals the computed height of a `.card` rendered with one row of content, ±0 px. Verified in DevTools on 1400×900 light AND dark.
- [ ] **Issue 5 — Token.** `tokens.css` defines `--dr-card-pad-v: 6px;` and `--dr-card-pad-h: 12px;`. `.card`, `.qthread`, `.sc` all consume those tokens; no `padding: …px …px;` literal remains in those three rules.
- [ ] **Issue 2 — Bucket correctness.** Resolved branch in `pushItem()` is `it.status === 'resolved'` (exact). The fallback `Open · carried` branch logs `console.warn('[critique] unknown item.status:', …)` when status is anything other than `open`, `open-new`, `resolved`, `drift`.
- [ ] **Issue 2 — Dev assertion.** Rendering a `.qthread.is-open` inside a `.crit-group[data-tone="ok"]` (Resolved) fires `console.error('[critique] status/section mismatch: status=open, section=resolved', …)` in dev.
- [ ] **Issue 1 — Scroll reach.** On a 1400×900 viewport, the longest-body item in the Resolved accordion can be scrolled to its last line via the Critique pane's `.crv__body` scroller. The page outside the pane does NOT also scroll. The card body itself has no inner scrollbar.
- [ ] **Issue 4 — Discrete badges.** The card header DOM matches:
      ```
      .qt-head
        > .qref.qref-split (type + number only — Q · 04)
        > .md-chip[data-tone=neutral] (Raised by {agent} — verbose)
        > .md-chip[data-tone=neutral] (Raised on round {N} — verbose)
        > .md-chip[data-tone={info|warn|ok|err}] (verbose status — "Open" / "Open · new" / "Resolved in round N" / "Drift")
        > .md-chip[opt] (Phase {N} — verbose, present only when showPhaseChip)
        > .right (chevron)
      ```
- [ ] **Issue 4 — No abbreviations.** Visual inspection (and a DOM textContent grep on the rendered header) finds zero matches for `r\d+`, `P\d`, `Q · \d+ · Claude` in any rendered `.qt-head`. Rounds spelled out; agent on its own pill; phases spelled out.
- [ ] **Issue 4 — Phase chip suppression.** Inside `CritiquePhaseContent` the `Phase {N}` chip does NOT render (its phase is implied by the surrounding `.crit-group`). In Σ Summary mode and in search-result callsites, it DOES render.
- [ ] `uv run pytest tests/ -q` → all green.
- [ ] Cache-bust query string in `index.html` and `__init__.py` matches `pyproject.toml` version `0.76.13`.

## 5. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<a run with at least one of each kind across P2 and P4>`. Capture: P2 Negotiate state, P4 Review state, with each of Open · new / Open · carried / Resolved / Drift accordions expanded (open one at a time, screenshot each).
- `2200×1300 light` — same.
- `1400×900 dark` — same; additionally screenshot the longest-body item EXPANDED inside Resolved, scrolled to its last visible line, to prove Issue 1 fix.
- `1400×900 light` — same.
- `820×1180 dark` — single-column; verify badge wrapping (the four pills should wrap to a second line gracefully, not overflow horizontally).
- `820×1180 light` — same.

All six required. The badge restructure changes the header's intrinsic width on every card across the pane; narrow-viewport wrapping is the regression risk.

## 6. Anti-pattern checks

- [ ] No emoji as icons. Agent badges use `<AgentIcon>` (existing primitive).
- [ ] No hex codes in component CSS. Tones go through `--md-tone-*` tokens.
- [ ] No off-grid spacing in the new chip cluster — gap between pills follows the existing `.qt-head` gap.
- [ ] No `r\d+` or `P\d` abbreviations anywhere in the rendered DOM (grep the build output).
- [ ] No nested scroll regions on the same axis inside the Critique pane (Issue 1 fix must not introduce one).
- [ ] No console errors in production build (the dev-only invariants from § 2.2 must be gated behind `process.env.NODE_ENV !== 'production'` or equivalent).
- [ ] Focus ring visible on every focusable (the `.qthread` card stays `tabIndex={0}`; the chip cluster is non-focusable).

## 7. Risks

- **Risk: badge text overflow on narrow viewports.** Spelling out `Raised by Claude` + `Raised on round 12` + `Resolved in round 14` makes the header noticeably wider. Mitigation: rely on `.qt-head { flex-wrap: wrap }` (already present in spec 0098). Visual verification matrix § 5 includes 820 px wide screenshots specifically to catch this.
- **Risk: bucket-fallback hides a real data bug.** Sending unknown-status items into Open · carried could mask a backend regression that emits a malformed status. Mitigation: the `console.warn` in § 2.2 surfaces it on every render in dev; CI build with `--abort-on-warning` style enforcement is out of scope here, but the warn message gives ops a grep target.
- **Risk: removing the phase chip inside `CritiquePhaseContent` reduces information density when a user has filtered to a single phase.** Mitigation: the surrounding `.crit-group` header in spec 0098 already prints the phase name; the chip on the card is genuinely redundant in that context. If user testing shows confusion, flip `showPhaseChip` back to `true` — single line change.
- **Risk: the height-parity change breaks line clamping or two-line wraps inside the card body.** Mitigation: visual verification matrix § 5 includes all four `.crit-group` states on each viewport.

## 8. Out of scope

- Anything in Notion Issues 3, 6, 7, 8, 9, 10 — separate specs.
- Backend schema changes (no new fields required; the bucket fix is pure frontend predicate-tightening).
- Renaming the `QuestionRef` component itself — too much surface-area churn for a polish spec; the new `format="split"` is additive.
- Animation tuning on the accordion expand/collapse — handled in spec 0098.
- Filter behaviour of the kind-tabs and agent / status segmented controls in Bar 2 — handled in spec 0098.

## 9. Backend touched?

**no.** All four fixes are frontend-only (CSS tokens, JSX badge restructure, JS predicate tightening). No new fields, no API changes, no migrations. The backend already emits `status` ∈ `{ open, open-new, resolved, drift }`; this spec just trusts that contract more strictly.

## 10. Handover read

> *First task on running this spec: read `handoffs/<latest>-spec-0110-modal-rail-contrast-critique-polish.md` end-to-end (the queue convention). Spec 0110 already touched `.qt-row` and `.dr-modal-body` — confirm none of the rules added there conflict with the padding-token routing in § 2.1 or the scroll-chain audit in § 2.3.*

## 11. Spec rewrite mandate

> *If implementation surfaces a constraint that invalidates any acceptance criterion above, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift.*
