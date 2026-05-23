---
spec: "0171"
date: 2026-05-23
version: 1.34.2
pr: "https://github.com/Lexiz/dual-research/pull/199"
---

# Spec 0171 — Agent Input single-column rewrite (v1.34.2)

## What landed

The Agent Input sub-tab inside the split-pane turn modal (`NegotiateLeftPane`, `sub === 'input'` branch) now renders single-column. Replaces the spec-0101 dual-card frame that survived spec 0151 §3.1's body migration and was the root cause of the horizontal-scroll regression flagged twice on Notion (`Specs 2205 (AL)` Issue 1 / `Specs 2205 (Claude)` Bug 1).

### Changes

- **New `AgentInputSingleColumn`** ([`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)) adjacent to `NegotiateLeftPane`. Anatomy:
  - Canonical `.tab-group-solid` + `.tab-solid` segmented control (post-spec-0173 DS pattern, `data-active` for selected state, leading agent dots `var(--claude)` / `var(--gpt)`).
  - One `<PromptPiecesThreeSectionView frame="single" turnKey={selectedTurnKey} />` underneath.
  - `selectedTurnKey` resolves via the same `buildTimeline(run)` paired-turn lookup the dual-pane used; default agent = `item.agent` when truthy, else `claude`.
- **Consumer swap** at the `sub === 'input'` branch in `NegotiateLeftPane` — `<AgentInputDualPane>` → `<AgentInputSingleColumn>`.
- **Retired primitives** — `function AgentInputDualPane` and `function AgentInputPane` deleted. Both had exactly one consumer site and no external references (verified via repo-wide grep).
- **CSS deleted in lock-step** per CLAUDE.md DS-canonical / live-copy sync rule:
  - [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) — the `.agent-input`, `.agent-input__pane`, `.agent-input__pane--a`, `.agent-input__pane--b`, `.agent-input__head`, `.agent-input__body` rules and the 1499 px media query.
  - [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) — mirror rules.
  - [`design-system/assets/Design System v2.html`](design-system/assets/Design System v2.html) — §15 catalog demo retired alongside the primitive it documented.
- **Stale comments updated** — `PromptPiecesThreeSectionView` and `InputTabContent` preambles no longer reference the deleted `AgentInputPane`; the `NegotiateLeftPane` historical-default comment now mentions the spec-0171 collapse so future readers searching for `AgentInputDualPane` get a pointer.
- **Test guard** at [`tests/spec0171/test_agent_input_single_column.py`](tests/spec0171/test_agent_input_single_column.py) — 6 pytest static-analysis assertions:
  1. `AgentInputDualPane` / `AgentInputPane` symbols and JSX call-sites gone.
  2. `AgentInputSingleColumn` defined and wired at the `sub === 'input'` branch.
  3. Segmented control uses the canonical `.tab-group-solid` + `.tab-solid` + `data-active=` shape.
  4. `.agent-input*` removed from `components.css`.
  5. `.agent-input*` removed from `composed-components.css`.
  6. `InputTabContent` keeps `frame="single"` delegation untouched.

### Why pytest instead of the vitest DOM test the spec requested

The spec called for a vitest DOM test in `tests/ui/static/` mounting `NegotiateLeftPane`. The repo has no vitest harness for `run-detail.jsx` (loaded via in-browser babel `<script type="text/babel">`, not bundled). Standing up that infrastructure for a single PATCH test is out of scope; the static-analysis assertions cover the structural contract (no dual-pane symbols, single-column consumer wired, CSS deleted) and the actual layout was verified manually at both 1440×900 and 1728×1080.

## Verification

Manual verification against the live dev server at the exact viewports spec 0171 called out:

| Viewport | `modal-body.scrollWidth` | `modal-body.clientWidth` | Horizontal overflow | `.cs-title "System prompt"` count |
|---|---|---|---|---|
| 1440×900 (MacBook default) | 1247 | 1247 | none | 1 |
| 1728×1080 (MacBook 16″) | 1247 | 1247 | none | 1 |

Segmented control toggled between Claude and GPT; the three-section panel re-rendered against the right `turnKey` each time. Onboarding overlay dismissed for a clean screenshot in the second viewport.

## Deploy notes

`fly deploy` ran on the bluegreen path. First attempt hit a lease conflict (`failed to acquire lease ... lease currently held by 89f4c34c-...@tokens.fly.io, expires at 2026-05-23T08:31:56Z`) at the cutover — the previous deploy from earlier in the day left a stuck lease that hadn't expired yet. Second attempt errored on `machine not found` for one of the version-433 originals (fly cleaned it up in parallel). Third attempt completed the bluegreen cycle cleanly: two new v434 machines came up healthy, the lingering v433s stopped and destroyed.

Stale-blue sweep (`scripts/sweep_stale_blues.sh`):

```
sweep: no stale blues on dual-research-alex
```

`/api/health` returns `{"ok":true,"version":"1.34.2","backend":"supabase"}`.

## Out of scope (next steps surfaced during implementation)

None — the spec scope was tight and the implementation matched. The vitest-harness gap (above) is the only deferred consideration, and it's broader than this spec.
