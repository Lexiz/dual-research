# Handover — Spec 0151 — Design-system parity for critique surface + canonical Agent Input grouping + run-ID copy affordance (v1.16.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#173](https://github.com/Lexiz/dual-research/pull/173) (merged, squash, branch deleted)
- **Spec:** [specs/0151-critique-parity-agent-input-grouping-run-id-copy.md](../specs/0151-critique-parity-agent-input-grouping-run-id-copy.md)
- **Design-system source of truth:** [`design-system/notion-issues/ISSUES.md`](../design-system/notion-issues/ISSUES.md) Issue 2; screenshots `02-critique-target.png` (toolbar), `07-question-card-duplicate.png` (Question), `08-disagreement-card.png` (Disagreement), `09-issue-card.png` (Issue), `10-comments-card.png` (Comment).
- **Supersedes:** spec 0119 §8.6 (the run-wide drift pill on bar1, retired by 0119, is restored by 0151 per the design-system target).
- **Version:** `1.15.0 → 1.16.0` (MINOR — visible UI changes across critique pane, Agent Input modal, and the run-ID header badge).
- **Tests:** full pytest suite 1460 passing (was 1460); GitHub Actions `test` job passed in 30 s on PR #173.

## What landed

Four discrete UI regressions accumulated across the 0140–0150 batch closed in a single release. None are functional bugs; each diverged from the design-system reference or from an originally-requested affordance that was dropped during scoping.

### Bug 1 — Preflight Agent Input three-section grouping

[`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)

Pre-spec the Phase-0 preflight turn modal opened `NegotiateReviewModal` → `AgentInputDualPane` → `AgentInputPane`, which rendered each prompt piece as a flat `InputSection` row inside a per-agent card. Every other full-view modal (`DocumentModal`, `PreflightResponseModal`, `InputBriefModal`) used `InputTabContent`, which buckets pieces into SYSTEM PROMPT / USER PROMPT / DERIVED INPUTS collapsible sections via `sectionFor()`. Spec 0145 introduced the three-section structure but skipped the split-view path; spec 0151 closes the gap.

The refactor extracts the shared logic:

```
function PromptPiecesThreeSectionView({ turnKey, attachmentTitles, frame }) {
  // (loading / error / empty / populated states)
  // groups by sectionFor → renders one <InputSectionGroup> per bucket
  // `frame` ∈ {'single','split'} toggles inter-section gap only
}

function InputTabContent({ turnKey, attachmentTitles }) {
  return <PromptPiecesThreeSectionView … frame="single" />;
}

function AgentInputPane({ slot, turnKey, run }) {
  return (
    <div className={`agent-input__pane agent-input__pane--${slot}`}>
      <div className="agent-input__head"><AgentStrip … /><StatusBadge … /></div>
      <div className="agent-input__body">
        <PromptPiecesThreeSectionView turnKey={turnKey} frame="split" />
      </div>
    </div>
  );
}
```

The per-agent frame (AgentStrip + StatusBadge) is preserved; only the body delegates to the shared view.

### Bug 2 — Empty-piece `(empty)` placeholder

[`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) + [`components.css`](../src/dual_research/ui/static/components.css)

Pre-spec `InputTabContent` filtered out any piece whose value was a falsy string before grouping (`Object.keys(pieces).filter((k) => pieces[k])`). When the backend emitted a canonical piece with an empty string — e.g. `phase1.claude = ""` at Phase 2 round 1 before Claude's draft lands — the piece silently disappeared. If every piece in a section was empty, the section header vanished too.

Fix:

- Drop the truthy filter; pass `pieces` directly to `orderPiecesForPhase`. Every key in the bundle now reaches the renderer.
- In `InputSection`, when `text` is falsy, render `<span className="prompt-piece__empty">(empty)</span>` instead of `<Markdown>`. The `isAgentDefault` italic note still renders above when applicable.
- Section headers stay visible whenever the section has ≥1 piece (populated or empty). Sections with zero pieces in the bundle remain hidden.
- New `.prompt-piece__empty` rule in `components.css` (italic, faint, 11.5 px).

### Bug 3 — Run-ID copy button

[`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) + [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) + [`components.css`](../src/dual_research/ui/static/components.css)

Spec 0138 §5.3 introduced `RunIDChip` as a single click-anywhere pill that copied the run ID; spec 0143 extended the payload to `id · cost · tokens`. The original product requirement — a small visual divider on the right of the badge and a dedicated copy button beside it — was never written into a spec and never shipped. The single-pill affordance was non-discoverable.

`RunIDChip` is now compound:

```
<div className="rid">
  <span className="rid__id">{id}</span>
  <span className="rid__divider" aria-hidden="true" />
  <button className="rid__copy" onClick={onCopy} title={copyTitle}
          aria-label={`Copy run id ${id}`}>
    <Mdi name="content-copy" size={12} />
  </button>
</div>
```

The outer container is non-interactive. The consumer at [`run-detail.jsx:316-324`](../src/dual_research/ui/static/run-detail.jsx) passes `onCopy={copyRunId}` instead of `onClick`; the existing `copyRunId` callback (with its copied-state tooltip swap behaviour) is unchanged. New `.rid--with-copy`, `.rid__id`, `.rid__divider`, `.rid__copy` CSS in components.css. Backward-compatibility: when `onCopy` is not provided the chip renders as identity-only (no divider, no button) so non-copy surfaces still work.

### Bug 4 — Critique surface pixel-parity

[`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) + [`components.css`](../src/dual_research/ui/static/components.css)

**Toolbar — design-system target `02-critique-target.png`:**

- Kind-tab row migrated from inline `<Chip … value={count}>` calls to the canonical `<TabGroup variant="kind-tabs">` + `<Tab variant="kind" count={…}>` primitives (CSS already present at `components.css:2070+`). Order: All / Issues / Comments / Questions / Disagreements (target order; pre-spec emitted Q / D / I / C / All). Counts surface as separate visual tokens via the `Tab variant="kind"` slot, not appended to label strings via `${t.label} (${t.count})` munging. Dead `KIND_TABS` descriptor + its three private helpers (`_phaseItemsForCount`, `_itemCountByKind`, `_displayCount`) removed.
- Agent filter migrated from `<Chip leadingIcon={<AgentIcon>}>` to the canonical `.fgroup` segmented control: `[All] [• Claude] [• GPT]` with dots tinted via `var(--claude)` / `var(--gpt)`.
- State filter migrated to a second `.fgroup`: `[All] [Open] [Resolved] [Drift?]` (Drift hidden when `kindFilter === 'questions'`).
- **Run-wide drift pill reinstated** on bar1, gated on `runWideDrift > 0`. `runWideDrift = allPhaseItems.filter(isDrift).length` (uses the existing `isDrift` predicate). New `.crit-drift-pill` / `__n` / `__lbl` rule in components.css (warn-tone background with `Mdi name="alert"` glyph). **Supersedes spec 0119 §8.6** — that decision retired the surface on the grounds that per-phase drift on timeline headers + `validate-run` were canonical. Spec 0151 returns it per the design-system target; both alternative surfaces remain.

**Card bodies — design-system targets `07/08/09/10`:**

`ItemCard` is now a slim shell that delegates body rendering to three per-kind sub-renderers (defined adjacent to `ItemCard` in `run-detail.jsx`, local-scoped per the spec's open-question default):

- `ItemCardDQBody({item, transitions, stateLabel, stateTone, isTerminal})` — renders Question + Disagreement bodies. Anatomy matches `08-disagreement-card.png`:
  - Meta row: short id + state pill + `N turns` right-aligned.
  - Verdict row (terminal only): `[state] — <last-terminal.reason>`.
  - Per-turn rows via `ItemCardTurnRow`: the initial raise (raiser + raisedRound + `raised` + item.body) plus one row per `ItemTransition` ({actor, round, _transitionVerb(t), reason}). Verbs map per the design: `addressed → pushed back`, `addressed → open → restated`, `* → acknowledged → aligned`, `* → resolved|withdrawn → conceded`, `* → capped → capped`.
- `ItemCardIssueBody({item, stateLabel, stateTone, anchorType, anchorText})` — matches `09-issue-card.png`:
  - Title row: `<short code (e.g. C-1)> [state] — <first body line>`.
  - Inline anchor: `> quote: <anchor>` (when `anchor_type === 'quote'`).
  - Body paragraph (markdown).
  - Seen row: `[flagged by <Agent>] [first seen R<N>] [last seen R<M>]`.
  - Bottom anchor blockquote.
- `ItemCardCommentBody({item, anchorType, anchorText})` — matches `10-comments-card.png`:
  - Body markdown.
  - Inline anchor blockquote.
  - Seen row: `[noted by <Agent>] [R<N>]`.
  - Bottom anchor blockquote.

Header chips reduced to the slim set per the target — `[id]` + `[kindLabel]` + `[state]` + optional `[Sources N]`. The pre-spec `raised by X` + `round N` badges are removed; those signals now live inside the per-turn rows where they belong.

Terminal footer replaced by a kind-aware green strip:

```
const _FOOTER_VERBS = {
  disagreement: { resolved: 'both aligned', acknowledged, capped, withdrawn },
  question:     { resolved: 'answered',     acknowledged, capped, withdrawn },
  issue:        { resolved: 'resolved',     acknowledged, capped, withdrawn },
  comment:      { resolved: 'noted', acknowledged: 'noted', capped: 'noted', withdrawn: 'noted' },
};
```

→ `✓ both aligned in round 2` / `✓ answered in round 3` / `✓ resolved in round 1` / `✓ noted in round 2`. The pre-spec `✓ resolved at round N · M turns to converge` text is retired.

**Hover elevation per `ISSUES.md` Issue 3:** `data-hoverable="true"` on the `<article className="item-card">` wrapper, plus a new `.item-card[data-hoverable="true"]:hover { box-shadow: var(--md-elev-2); }` rule mirroring the existing `.md-card[data-hoverable]` behaviour.

### Bug 4b note — legacy `QuestionThread` fallback path

The spec proposed retiring the `_normalizeToThread` + `QuestionThread` fallback in `renderItem` and forcing every item through `ItemCard`. During implementation a constraint emerged: `QuestionThread` is also a consumer in [`CritiquePhaseContent`'s summary view at run-detail.jsx:7540](../src/dual_research/ui/static/run-detail.jsx), so the definition in `shared.jsx` cannot be deleted outright.

The original mitigation — "shim `transitions: []` on legacy items at the projection layer" — turned out to be a no-op because [`ui/models.py:483`](../src/dual_research/ui/models.py) already declares `transitions: list[ItemTransition] = field(default_factory=list)`. Every Item dataclass serializes with `transitions: []` by default, so `Array.isArray(newItem.transitions)` is `true` for every new-protocol item that reaches `phaseStats.items`. The legacy fallback only fires for items that don't appear in `phaseStats.items` at all — rare on modern runs.

Net: no code change for Bug 4b. The router stays as-is; ItemCard is the dominant path; `QuestionThread` remains defined in shared.jsx for the CritiqueSummaryView consumer.

## Files touched

### Frontend (JSX)
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — `PromptPiecesThreeSectionView` extraction (Bug 1); empty-piece filter drop + placeholder (Bug 2); `RunIDChip` consumer signature flip (Bug 3); critique-toolbar rebuild + drift pill + `runWideDrift` calc (Bug 4a); `ItemCard` slim shell + four per-kind sub-renderers + kind-aware footer + `data-hoverable` (Bug 4c).
- [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) — `RunIDChip` compound primitive (Bug 3).
- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — `.prompt-piece__empty`, `.rid__id` / `.rid__divider` / `.rid__copy`, `.crit-drift-pill`, `.item-card[data-hoverable]`, `.item-card__bmeta` / `__sid` / `__turn-count` / `__verdict` / `__turns` / `__turn` / `__agent`, `.item-card__title-row` / `__quote-inline` / `__seen-row` / `__anchor--bottom`, `.item-card__footer` / `__footer--ok`.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-buster `?v=0150a → ?v=0151a` across all 25 imports.

### Misc
- [`pyproject.toml`](../pyproject.toml), [`src/dual_research/__init__.py`](../src/dual_research/__init__.py), [`uv.lock`](../uv.lock) — `1.15.0 → 1.16.0`.
- [`CHANGELOG.md`](../CHANGELOG.md) — `[1.16.0]` entry.
- [`specs/0151-critique-parity-agent-input-grouping-run-id-copy.md`](../specs/0151-critique-parity-agent-input-grouping-run-id-copy.md) — spec, status `ready`.

## Vocabulary scan markers

Spec 0119 §13 has a vocabulary scan (`tests/contract/test_ui_vocabulary.py`) that forbids certain verb literals in chip-rendering surfaces. Five literals introduced by spec 0151 are documented chip labels lifted directly from the design-system references:

- `'answered'` at `run-detail.jsx:1418` (footer verb for Question terminal state) — `// spec-0119:vocab-ok (spec 0151 §3.4.3 design-system verb)`.
- `'noted'` at `run-detail.jsx:1422-1423` (footer verb for Comment terminal states) — same marker.
- `'conceded'` at `run-detail.jsx:1434` (`_transitionVerb` return for `resolved`/`withdrawn` transitions) — same marker.
- `'conceded'` at `run-detail.jsx:1440` (`_verbTone` comparison; data-layer) — `// spec-0119:vocab-ok (data-layer comparison)`.

The markers preserve the design-system intent without disabling the scan for the rest of the file. Future verb additions outside spec 0151's footprint still fail the scan unless explicitly marked.

## What I did not do (deferred)

- **Narrow-viewport label collapse for the new toolbar.** The pre-spec `.crit2 .bar2.crit-filter-row .chip[data-kind-filter]` rules at `components.css:907+` targeted the old `<Chip>`-based row. The new `<TabGroup variant="kind-tabs">` + `.fgroup` controls don't carry those class hooks, so at viewports < 1799 px the row no longer auto-collapses to bubble-only mode. The design-system target is captured at wide desktop; mobile/narrow responsiveness is out of scope per spec §4. Will likely surface on the next narrow-viewport audit.
- **Collapsed-state header chevron on `ItemCard`.** The design references show a collapsed/expanded toggle (`>` chevron). The current implementation always renders the expanded body. Adding collapsible state is a follow-up; not blocking for the current parity pass.
- **`<QuestionBody>` / `<DisagreementBody>` / `<IssueBody>` / `<CommentBody>` hoist to `shared.jsx`.** Sub-renderers stay local in `run-detail.jsx` per the open-question default in spec §7. Can be lifted if a second consumer materialises.

## Open follow-ups

- **Live visual diff.** The PR landed after a static-only smoke test. After the fly deploy, walk through preflight → Phase 2 → critique pane on a recent run and capture screenshots; diff against `02/07/08/09/10`. Likely candidates for tweak: chip sizing inside per-turn rows, exact `.fgroup` padding, drift-pill icon vertical centering.
- **Spec 0119 vocabulary scan rule for spec 0151.** The four kind-aware footer verbs (`both aligned` / `answered` / `resolved` / `noted`) and the four transition verbs (`pushed back` / `restated` / `aligned` / `conceded` / `raised`) are now part of the design-system vocabulary. Future cleanup could promote them into the canonical allowed-verb set so the per-literal `vocab-ok` markers can drop. Tracked as a low-priority cleanup; not blocking.

## Anchor-run notes

`20260521-010637-dvs-backend-language-choice` was the implicit anchor during static checks (UI server at v1.16.0 served the page, JSX file is fetched with the new identifiers, run detail API returns 200 with 463 KB payload). No data-layer changes in this spec, so no migration / no backfill / no replay required.

---

🤖 Spec implementation co-authored by Claude Opus 4.7 (1M context).
