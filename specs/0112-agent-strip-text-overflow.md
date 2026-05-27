---
spec: 0112
title: Agent strip — stop wrapping the model id and activity label when the box is tight
label: bug
version-bump: PATCH
status: merged
target-version: 0.76.14
created: 2026-05-19
pr: "https://github.com/Lexiz/dual-research/pull/120"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0112 — Agent strip text overflow

> Ship bucket: **Composed**
> Depends on: **0087, 0094, 0105**
> Complexity: **S**
> Targeted version bump: **PATCH** (one isolated visual fix to the top-of-run agent bar; no new features, no breaking changes).

## 1. Context

Source: [Notion · Known issues v2](https://www.notion.so/Known-issues-v2-36599f3e507f80a8ad5fdb26b143a695) — Notion **issue 3**.

User report (verbatim, summarised): the run-detail page has a horizontal "agent bar" with two side-by-side boxes — Claude on the left, GPT on the right. Each box shows: agent icon · agent name · model id (e.g. `claude-sonnet-4-6`) · token count · dollar cost · coloured activity dot · activity phrase (e.g. `negotiating · round 5`). On the Claude side, the model id `claude-sonnet-4-6` wraps to a second line (breaking after `claude-sonnet-4-`), and `negotiating · round 5` also wraps to a second line. The GPT side renders on one line because `gpt-5.5` happens to fit. Result: the two boxes are different heights, the row looks unbalanced, and content below is pushed down.

User-suggested direction: *"there is just a little bit better way to structure this so that we will foresee at the tail of it a bit more space. That way the box can dynamically resize itself to the right when the name is bigger so that it doesn't push the content the way it does now."* Translation: let the box grow horizontally to absorb longer strings, and stop letting text break mid-word.

This is the second of the four Notion-issues-v2 specs. Specs already shipped or planned:

- **0111 (merged)** — Critique cards: bucket / scroll / badges / height (Notion 1, 2, 4, 5).
- **0112 (this spec)** — Agent strip text overflow (Notion 3).
- *Future* — Full-view modal vertical & horizontal fill (Notion 6, 7, 9).
- *Future* — Turn / Cross-review modal cleanup + input/output data correctness (Notion 8, 10).

## 2. Proposed change

Three sub-changes, in implementation order (lowest-risk first):

### 2.1 — `white-space: nowrap` on the text labels

**Current state.** `.as-name` (`components.css:189`) and `.as-model` (`components.css:190`) do not declare `white-space`. With the default `white-space: normal`, text breaks at word boundaries (and at hyphens — which is exactly why `claude-sonnet-4-6` wraps after `claude-sonnet-4-`). The inline-styled activity label in `run-detail.jsx:162-168` carries `overflow: 'hidden'` and `textOverflow: 'ellipsis'` but is also missing `white-space: nowrap`, so `text-overflow: ellipsis` never engages — the text wraps onto a second line instead of being clipped with an ellipsis.

**Fix.**

- Add `white-space: nowrap;` to `.as-name`, `.as-model` in `components.css`.
- Add `white-space: nowrap;` to the inline style on the activity-label `<span>` at `run-detail.jsx:162-168`.
- Result: no string inside the agent strip can break onto a second line, regardless of how narrow the box is. If the box is too narrow, the text will overflow (handled by §2.3) — never wrap.

This change alone resolves the visible double-line bug. §2.2 and §2.3 are the structural improvements the user explicitly asked for.

### 2.2 — Let the agent boxes grow horizontally

**Current state.** `.as.as-timeline` (`components.css:188`) is pinned at `width: 460px; min-width: 460px; flex: 0 0 auto`. The boxes never grow even when the parent `.agent-bar` row has extra horizontal space. SPEC-0087 introduced the hard width to enforce visual symmetry between Claude and GPT pills (which previously lived in different flex containers).

**Fix.**

- Change `.as.as-timeline` to: `flex: 1 1 460px; min-width: 460px; max-width: 720px;`.
  - `flex: 1 1 460px` — grow and shrink around a 460 px basis. The two boxes share the parent's space evenly when there's extra room; they shrink toward their min when the viewport is narrow.
  - `min-width: 460px` — preserves the existing visual floor; nothing collapses smaller than today.
  - `max-width: 720px` — caps the growth so on very wide viewports (e.g. 2200 px) the two boxes don't stretch comically wide. A pair of 720 px pills + the row's `var(--md-sp-6)` (24 px) gap totals ~1464 px, comfortably below the 1440 px content max defined by `--md-content-max`.
- The two pills remain visually symmetric because both consume the same flex rule against the same parent.

This satisfies the user's "box can dynamically resize itself to the right when the name is bigger" requirement without re-introducing the asymmetry SPEC-0087 originally fixed.

### 2.3 — Make the activity-label width responsive, not hard-coded

**Current state.** The activity-label span at `run-detail.jsx:162-168` carries an inline-style `maxWidth: 140`. That number was chosen for the previous fixed-460-px box; it has no relationship to the actual available space when the box grows or shrinks. On a wide pill there's wasted room next to the label; on a narrow pill 140 px may be too generous and force wrapping (with §2.1 in place, instead of wrapping the text would overflow — also undesirable).

**Fix.**

- Move the activity-label styling out of inline `style` and into a CSS class. Add to `components.css`:
  ```css
  .as-activity {
    /* Spec 0112 — responsive label; absorbs whatever space remains in
       .as-right. min-width: 0 is required to let flex children shrink
       below their content size so text-overflow: ellipsis can engage. */
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
  }
  ```
- In `run-detail.jsx:162-168`, replace the inline-style `<span>` with `<span className="as-activity" style={{ color: phraseColor }}>{phrase}</span>`. Keep the dynamic colour (`phraseColor`) as inline style — it changes per live/idle state and doesn't belong in CSS.
- Ensure `.as-right` (`components.css:178`) sets `min-width: 0` so its grandchild ellipsis works inside the nested flex chain. Add `min-width: 0;` to the existing rule.

**Acceptance for §2.1 + §2.2 + §2.3 together.** On every viewport width tested in § 5, the model id and the activity label both render on a single line, the two agent pills are the same height, and on narrow viewports the activity label clips with an ellipsis rather than wrapping or overflowing the pill.

## 3. Files touched

- `src/dual_research/ui/static/components.css`:
  - `.as-name` (~`:189`) — add `white-space: nowrap;`.
  - `.as-model` (~`:190`) — add `white-space: nowrap;`.
  - `.as.as-timeline` (~`:188`) — change `width: 460px; min-width: 460px; flex: 0 0 auto;` to `min-width: 460px; max-width: 720px; flex: 1 1 460px;`.
  - `.as-right` (~`:178`) — add `min-width: 0;`.
  - Add new rule `.as-activity { … }` per § 2.3.
- `src/dual_research/ui/static/run-detail.jsx`:
  - `TimelineAgentPill` activity label (~`:159-170`) — drop the inline `maxWidth/overflow/textOverflow` style block; replace with `className="as-activity"` and keep only the dynamic `color` as inline style.
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0103` → `?v=0104` (21+ occurrences via sed).
- `pyproject.toml` — `0.76.13` → `0.76.14`.
- `src/dual_research/__init__.py` — `__version__` `0.76.13` → `0.76.14`.
- `CHANGELOG.md` — `0.76.14` entry under `## [0.76.14] — 2026-05-19`.

## 4. Acceptance criteria

- [ ] `.as-name` and `.as-model` carry `white-space: nowrap;` in `components.css` (DevTools computed style verifies on the live page).
- [ ] The activity-label `<span>` carries `class="as-activity"` and the inline `style` no longer contains `maxWidth` / `overflow` / `textOverflow` (only `color`).
- [ ] `.as.as-timeline` resolves to `min-width: 460px; max-width: 720px; flex: 1 1 460px;`. The Claude and GPT pills render at the SAME computed width on every viewport tested.
- [ ] On a 1400×900 viewport with `claude-sonnet-4-6` + `negotiating · round 5`: both strings render on a single line in the Claude pill. The pill is the same height as the GPT pill. Verified via DevTools computed `height`.
- [ ] On a 820×1180 viewport: both strings still render on a single line; if the box is too narrow to fit the activity phrase, the phrase clips with an ellipsis (CSS `text-overflow: ellipsis` engages) — it does NOT wrap to a second line and does NOT overflow the pill.
- [ ] On a 2200×1300 viewport: each pill is wider than 460 px but no wider than 720 px. The row of two pills + the gap fits within the page's content max.
- [ ] `uv run pytest tests/ -q` → 924+ green.
- [ ] Cache-bust `?v` value in `index.html` matches `pyproject.toml` `0.76.14`.

## 5. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<canonical>`. Capture: full agent bar showing both pills.
- `2200×1300 light` — same.
- `1400×900 dark` — same. This is the viewport where the user reported the original bug; the screenshot must show `claude-sonnet-4-6` and `negotiating · round 5` each on a single line.
- `1400×900 light` — same.
- `820×1180 dark` — same. This is the stress test for the ellipsis path; the activity phrase should clip with an ellipsis if it doesn't fit.
- `820×1180 light` — same.

All six required. Pill height parity + single-line rendering are the visual contract this spec ships.

## 6. Anti-pattern checks

- [ ] No emoji as icons. The agent icon stays as the existing `<ClaudeMonogram>` / `<OpenAIMonogram>` SVG.
- [ ] No hex codes in the new `.as-activity` rule; colour is set inline via the `phraseColor` prop and routes through `--fg-*` tokens.
- [ ] No `width: <px>` hard-pin remains on `.as.as-timeline`. The post-fix rule must be expressed entirely as `min-width` + `max-width` + `flex`.
- [ ] No JavaScript width measurement / resize observer added. The fix is pure CSS + a JSX className swap.
- [ ] No nested scroll regions or `overflow` on the pill itself.
- [ ] The activity label's `font-size: 11px` literal in `.as-activity` matches what the inline style had — if a font-size token (`--md-label-s-size` or similar) covers 11px, prefer the token; otherwise keep the literal (this is purely a sizing fix, not a typography rework).

## 7. Risks

- **Risk: the 720 px max-width is wrong for the user's actual workflow.** The agent bar may legitimately need to grow beyond 720 px on ultra-wide displays. Mitigation: 720 px is a starting cap chosen to keep the pair under `--md-content-max` (1440 px) with the row gap; if the user wants more, bump the value — single-line change. Visual matrix § 5 includes 2200 px width to surface any awkwardness.
- **Risk: removing the inline `maxWidth: 140` lets the activity phrase eat all available space inside `.as-right`, squeezing the token/cost numbers.** Mitigation: `.as-right` is a flex row; the `.as-activity` rule uses `min-width: 0` + `overflow: hidden` + `text-overflow: ellipsis`, so it shrinks first. Token/cost siblings stay at their natural width.
- **Risk: SPEC-0087's symmetry guarantee is weakened.** That spec pinned the width because Claude and GPT pills lived in separate flex containers. Per `TimelineAgentBar` (`run-detail.jsx:186-193`), today the two pills share a single parent (`.agent-bar`) — so `flex: 1 1 460px` on both children produces identical computed widths automatically. Verified in § 5's matrix.
- **Risk: text-overflow ellipsis on the activity label hides the round number on very narrow viewports.** This is the user-acceptable failure mode — the user explicitly preferred this over a two-line wrap. A tooltip with the full phrase could be a follow-up if anyone complains.

## 8. Out of scope

- Anything in Notion Issues 1, 2, 4, 5 (covered by spec 0111, merged).
- Anything in Notion Issues 6, 7, 8, 9, 10 (separate specs).
- The agent-icon SVG, the agent name string, the token/cost formatting — only the layout / wrapping behaviour changes.
- Adding a tooltip to surface a truncated activity phrase — possible follow-up, not required to ship this spec.
- Re-tuning typographic scale for the agent strip — out of scope; the spec uses the same 11 px label size as today.

## 9. Backend touched?

**no.** Pure frontend — CSS rule changes and a JSX className swap. The backend already emits the model id, activity phrase, token count, and cost; this spec doesn't change any data, only how it's laid out.

## 10. Handover read

> *First task on running this spec: read `handoffs/<latest>-spec-0111-critique-cards-bucket-scroll-badges-height.md` end-to-end (the queue convention). Spec 0111 added the shared `--dr-card-pad-*` tokens — confirm the agent-strip selectors here don't accidentally consume them (they shouldn't; the agent strip uses `var(--s-3)` etc., not the card tokens).*

## 11. Spec rewrite mandate

> *If implementation surfaces a constraint that invalidates any acceptance criterion above, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift.*
