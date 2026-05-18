---
spec: 0072
title: Critique pane structural — filter strip, Phase 4 split, summary copy
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.65.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/72
---

# Spec 0072 — Critique pane structural pass

## Context

Ship 6 of 9 in the tweak-cycle arc. Targets three coupled issues in
the critique pane (right side of run-detail):

- **`14.45`** — three-axis critique filter strip: top row
  (kind: All / Questions / Disagreements / Claims) has rightmost
  tab cut off; bottom row (agent + status, separated by a divider:
  All / Claude / GPT | All / Open / Resolved / Drift) is too tightly
  packed with no breathing room. User wants spacing fixed, no
  cutoff, tooltips on hover explaining what each chip filters,
  better alignment (top row anchored left, bottom row centered),
  and the bottom row tightened to save space.
- **`15.06`** — summary panel opens with "Mostly positive — Claude
  approved the brief but flagged 4 minor issues." Too terse. User
  wants 2 sentiment sentences + 1 stats sentence using the
  data-model's actual terminology (issues raised, claims raised,
  questions, disagreements raised/resolved, etc.).
- **`19.41`** — Phase 4 critique pane shows Issues and Comments
  mixed in a single section. User wants them in two separate
  collapsible sections.

Depends on SPEC-0067 (chip vocabulary — full-word filter labels),
SPEC-0071 (CollapsibleSection primitive — D12 of 0071).

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Three-axis filter strip — overflow fix** — change container `flex-wrap: nowrap; overflow-x: auto` to `flex-wrap: wrap` so the strip wraps onto two visual lines instead of cutting off. Combined with D2-D3 spacing, the cutoff is eliminated. | Direct fix to 14.45 top-row cutoff. |
| D2  | **Top row (kind axis) anchored left** — left-align the row inside its parent flex container. Chips: `All`, `Questions`, `Disagreements`, `Claims`. Use `<Tab variant="solid" dot>` from SPEC-0053. | Per user — top row aligned left. |
| D3  | **Bottom row (agent + status axes) centered** — the second visual line contains the agent sub-axis (All / Claude / GPT) and the status sub-axis (All / Open / Resolved / Drift), separated by a `·` divider. Center the whole row in the container; reduce per-chip padding so they fit comfortably. | Per user — bottom row centered. |
| D4  | **Tooltip on every filter chip** — `title` attribute on each tab explaining what it filters: e.g. "Show only Questions" / "Show only items raised by Claude" / "Show only Drift items (ghosted for multiple rounds)" etc. | Per 14.45 — "When you hover over this, it is clear what it does." |
| D5  | **Spacing tightening on bottom row** — reduce horizontal gap between bottom-row chips from `gap: 8` to `gap: 6`; reduce per-chip horizontal padding from `12 → 10`. The bottom row was the one user called out as "tightened more (save some space)." | Per 14.45 specifically. |
| D6  | **Section split — Phase 4 Issues vs Comments** — currently a single critique-list section in Phase 4. Split into two `<CollapsibleSection>` wrappers (using SPEC-0071's D12 primitive): one for **Issues** with its count chip, one for **Comments** with its count chip. Default expanded. | Per 19.41. |
| D7  | **Summary panel copy regeneration** — rewrite the summary string at the top of the Summary tab. Three-sentence template using data-model terminology:
- Sentence 1: sentiment with leading verdict — e.g. `Mostly positive — both agents converged on the core architecture.` (verdict from `convergence` state + sentiment hint).
- Sentence 2: a brief qualitative — e.g. `Claude flagged 4 minor issues; GPT raised 2 follow-up questions but both were resolved by round 3.` (auto-composed from the aggregated data).
- Sentence 3: stats — `Totals: 26 questions raised (24 resolved), 10 disagreements raised (8 resolved), 4 issues raised, 12 claims tracked.` (counts pulled from `run.summary` / aggregator output). | Per 15.06's three-sentence structure. |
| D8  | **Summary copy generation** — pure frontend; pulls from the aggregator's existing per-run counts. If a count is unavailable (older runs), the stats sentence renders only the available counts. No backend changes. | Scope discipline. |
| D9  | **Sentiment verdict vocabulary** — `Mostly positive` / `Mostly negative` / `Mixed` / `Inconclusive` based on (resolved / total) ratio + (drift ratio): >70% resolved, <20% drift → positive; <40% resolved OR >40% drift → negative; otherwise mixed. | Deterministic; document the thresholds in the spec. |
| D10 | **Summary panel rendered as `<Markdown>`** — supports bold, italic in the sentiment sentence; allows future iteration without code changes. (Currently raw text per SPEC-0057's Σ Summary panel.) | Future flexibility. |
| D11 | **Filter strip behaviour preserved** — three-axis AND logic from SPEC-0057 (kind ∩ agent ∩ status). URL state preserved (sync with hash params). | Don't regress. |
| D12 | **Drift status chip removed from status axis if kind=Questions** — when "Questions" is selected as the kind filter, the status axis's "Drift" option becomes disabled (greyed) because drift only applies to disagreements per the data model. (Decide-and-document; alternative is to leave it always enabled but show "(0)" if no drift items match.) | Defensive UX. |
| D13 | **Cache-bust bumped to `?v=0072`.** | Per arc convention. |
| D14 | **No backend changes.** | Frontend only. |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — three-axis filter strip restructure (D1-D5, D11-D12); Phase 4 split with `<CollapsibleSection>` wrappers (D6); Summary panel copy generation (D7-D10).
- `src/dual_research/ui/static/shared.jsx` — verify `<CollapsibleSection>` from SPEC-0071 supports the use here; no new primitive expected.
- `src/dual_research/ui/static/components.css` — filter strip layout rules (flex-wrap, gap, centering); summary panel typography tweaks if any.
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Disagreement modal "PROGRESSION" rewrite** — see SPEC-0073.
- **Markdown rendering inside Issue / Comment bodies** — see SPEC-0073.
- **PhaseRail / phase-header collapsibility** — done in SPEC-0071.
- **Disagreement row chip pair (raised-by / conceded-by)** — done in SPEC-0067 D7.
- **Adding new filter axes** — three axes stay; this spec only fixes presentation.

## Test plan

- 735 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`):
  - Filter strip top row: All, Questions, Disagreements, Claims — visible, no cutoff, left-aligned.
  - Filter strip bottom row: All · Claude · GPT · | · All · Open · Resolved · Drift — visible, centered, tightened spacing.
  - Hover over any filter chip → tooltip shows what it filters.
  - Click Questions → only questions render; the status-axis Drift chip greys out (D12).
  - Phase 4 (if any P4 data — partner-vetting has comments + issues): Issues and Comments render as two separate collapsible sections, each with their own count chip in the header.
  - Click Phase 4's Issues section header → collapses; reload preserves.
  - Summary tab on the Σ panel: three sentences as per D7.
  - Sentiment verdict consistent with the run's data (partner-vetting is "Mostly positive" given high resolve ratio).
- Both themes; zero console errors. Cache-bust + `/api/health`.

## Risks

- **`flex-wrap: wrap` on the filter strip** may cause the strip to grow vertically when the container is narrow, pushing critique cards down. Verify at 1024 px viewport.
- **Sentiment thresholds (D9)** are subjective — partner-vetting may verdict differently than user expects. Document thresholds in CHANGELOG; tune by user feedback.
- **Phase 4 section split (D6)** assumes the data model has separate `phase4.issues` and `phase4.comments` arrays. Verify in the aggregator output before assuming. If they're merged in the current API, this spec **does not** add a backend split — implementer needs to either:
  (a) request the aggregator to expose two arrays (small Python change inside out-of-scope; punt to follow-up), OR
  (b) partition client-side by the `kind` field on each item.
  Decide and document.
- **Summary copy regeneration (D7)** runs on every render of the Summary tab — verify it's memoized so it doesn't re-compute per scroll.
- **URL state for filter** — when filter+kind change interact (e.g., Questions selected, status was Drift, now status auto-resets to All), hash params must update consistently. Verify.

## Brief mapping

`SUR-11` (three-axis critique filter — revisit), `SUR-14` (summary panel — copy revision). New: Phase 4 sub-section split (no brief ID, user-feedback-driven).

## Design system alignment (per arc M1)

- **Filter-strip layout pattern codified** — `flex-wrap: wrap` + top-row anchored left + bottom-row centered + tightened gaps becomes a documented system pattern for "multi-axis filter strips." Captured in `components.css` under a named class (e.g., `.filter-strip-multi`).
- **Tooltip discipline** — every interactive filter chip carries an explanatory `title`. Codified as a system rule (any new `<Tab>` or `<Chip>` used as a filter MUST have a `title`).
- **`<CollapsibleSection>` from SPEC-0071** — reused for Phase 4 Issues + Comments sections. No new primitive.
- **Three-sentence summary pattern** — `[Sentiment verdict] [Qualitative line] [Stats line]` becomes the documented Summary-panel pattern. The verdict + threshold logic (>70%/<40%/etc) becomes part of the design system narrative (codified in `aggregator.py` if backend) or a frontend helper (`composeSummary(run)` in shared.jsx).
- **Sentiment verdict vocabulary fixed** — `Mostly positive` / `Mostly negative` / `Mixed` / `Inconclusive` are the four canonical verdicts. Documented in the design system's content vocabulary section.
- **`<Markdown>` reuse** — Summary panel renders via the existing `<Markdown>` primitive (consistent with critique-card bodies post-SPEC-0073). Codifies "long-form text uses `<Markdown>` always."
- **Disabled-filter UX pattern** — for cross-axis dependencies (e.g., Drift disabled when kind=Questions), use opacity 0.5 + `cursor: not-allowed` + tooltip explanation. Becomes the documented "axis-coupling" UX rule.

---

## Pre-draft notes for the implementing session

- **Read SPEC-0057 handover** — it documents the three-axis filter and the Σ Summary panel. This spec polishes both without removing functionality.
- **Filter strip** is at run-detail.jsx — search for `kindFilter`, `agentFilter`, `statusFilter` state and the JSX block that renders the three rows of tabs.
- **`<CollapsibleSection>` from SPEC-0071** — verify the primitive is on `window`; use as:
  ```jsx
  <CollapsibleSection title="Issues" count={issues.length} persistKey={`dr_p4_issues_${runId}`}>
    {issues.map(i => <IssueCard ...>)}
  </CollapsibleSection>
  <CollapsibleSection title="Comments" count={comments.length} persistKey={`dr_p4_comments_${runId}`}>
    {comments.map(c => <CommentCard ...>)}
  </CollapsibleSection>
  ```
- **Summary copy generation** — read `aggregator.py` to find which counts are exposed. Typical:
  - `run.summary.totals.questions.raised`, `.resolved`
  - `run.summary.totals.disagreements.raised`, `.resolved`
  - `run.summary.totals.issues.raised`
  - `run.summary.totals.claims.raised`, `.resolved`
  If these don't exist, derive client-side from the critique-list arrays.
- **`render` skeleton for summary**:
  ```jsx
  function SummaryCopy({ run }) {
    const v = deriveVerdict(run); // 'positive' | 'negative' | 'mixed' | 'inconclusive'
    const sentiment = SENTIMENT_LABEL[v]; // 'Mostly positive' etc.
    const qualitative = composeQualitative(run); // e.g. "Claude flagged 4 minor issues..."
    const stats = composeStats(run); // "Totals: 26 questions raised (24 resolved), ..."
    return <Markdown>{`**${sentiment}** — ${qualitative}\n\n${stats}`}</Markdown>;
  }
  ```
- **D12 disabled-Drift chip** — render it visually disabled (lower opacity, `cursor: not-allowed`) when `kindFilter === 'questions'`. Don't hide; consistent layout.
- **Don't change the highest-leverage-thread feature** from SPEC-0057 SUR-14 — that's the QuestionThread embedded below the summary copy. The 3-sentence summary lives ABOVE that.
