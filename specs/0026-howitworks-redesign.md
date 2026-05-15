---
spec: 0026
title: How-it-works restructure — chat-lifecycle diagram, phase accordions, v3.5 process map
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.24.0
created: 2026-05-16
pr: ""
---

# Spec 0026 — How-it-works restructure

## Context

Spec 0023 shipped the first cut of `#/how-it-works`: a single long
column with a hero, an inline phase-flow SVG, a five-paragraph
phase walkthrough, an FAQ, and the release-notes block. It worked,
but it has two problems now:

1. **The most counter-intuitive fact about the protocol is buried.**
   Users keep asking the same thing: "do they share a chat between
   rounds?" The page does answer it (one FAQ entry tucked in the
   middle), but the answer is load-bearing for understanding the cost
   shape, the prompt-caching behaviour, and why Phase 2 history grows
   unbounded. It deserves a dedicated section with a diagram.

2. **The page reads as a wall of prose.** No accordions, no expandable
   regions, no card grid for at-a-glance scanning. For a page whose
   job is to explain a 5-phase state machine, this is the wrong shape —
   readers want to drill into one phase at a time, not scroll past the
   other four.

There's also a third-party prompt: the original `dual-research-protocol-
diagram.svg` (a cream-and-indigo landscape, hand-authored before the
diagram skill existed) is a genuinely useful reference but lives in
Downloads, not in the app. It should live on the page, behind a
fold-out so it doesn't dominate the dark-themed layout above it.

This spec is **UI-only**. No prompt changes, no orchestrator changes,
no wire-format changes. The behaviour described in the page is
already true — the page just stopped under-selling it.

## Design decisions

| # | Decision | One-liner |
|---|---|---|
| D1 | **Chat lifecycle is the new centrepiece section** | A 3-column grid (phase · Claude lane · OpenAI lane) showing every API call across all five phases, with the exact context bundle inside each call rendered as colour-coded chips. The "stateless per call" claim becomes visual. |
| D2 | **Phase walkthrough → accordions** | Five `<details>` blocks, one per phase, default-open on Phase 0. Each carries a `dt/dd` meta block (input, chats, output, gate, caps) so the mechanics read at a glance. |
| D3 | **FAQ → accordions** | The eight FAQ entries become individually-collapsible `<details>` blocks. Default closed; the headlines alone already telegraph the topics. |
| D4 | **TL;DR strip of four cards** above the phase flow | One-screen read of the protocol: models · transport (stateless) · timing (parallel) · exit (mechanical convergence). |
| D5 | **Context-growth bars + CACHE_BREAKPOINT marker** | Stacked horizontal bars per phase showing how the prompt grows (brief → +drafts → +history). Makes the "prefix cached, tail billed full" cost shape concrete. |
| D6 | **Stateless-vs-persistent compare panel** | Two-column callout that names what we deliberately don't do (no `thread_id`, no Assistants API) alongside what we actually do (re-inlining via filesystem state). |
| D7 | **v3.5 protocol overview behind a "View full process map" fold-out** | Embedded inline (not `<img>` referenced) so it always renders. Light cream-and-indigo surface; explicitly doesn't follow the theme toggle. Authored via the diagram skill (Step 1 restate → Step 4 canonical spec → 3-pass render). Companion static-asset `protocol-overview.svg` ships in `static/` so the "Open SVG ↗" link gives a downloadable copy. |
| D8 | **Reverses 0023's D7 on the diagram skill — selectively** | 0023 skipped the skill because cream-and-indigo would clash with the dark theme. That reasoning still holds for the inline visuals (chat lifecycle, context bars, round-up-close — all theme-coloured). The fold-out is the explicit exception: a separate "reference map" surface where cream-and-indigo is the right choice. |
| D9 | **Inline visuals remain hand-authored**, theme-aware | Phase strip, chat-lifecycle grid, context-growth bars, negotiation-round diagram all use `--agent-a` / `--agent-b` / `--fg-*` / `--bg-*` tokens. Light/dark toggle continues to work for the page proper. |
| D10 | **Spec number 0026, not the slot 0025 reserved** | Spec 0025 mentioned 0026/0027 as the inline-comments follow-ups, but those weren't formally filed. Strict sequential per CONTRIBUTING.md. Inline-comments work can take 0027/0028 when it lands. |

## Behaviour reference

The page is built around the same facts as spec 0023 (which read the
code end-to-end). Nothing changed in the orchestrator since; the new
"Chat lifecycle" section just spells out the per-phase API-call shape
that was already implicit. Specifically:

- `agents/anthropic_agent.py:60-127` builds a single-message `messages`
  array on every call. No thread state.
- `agents/openai_agent.py:42-144` calls `responses.create` with a
  single `input` string. No session.
- `protocol/prompts.py:70` defines `CACHE_BREAKPOINT`; the marker is
  inserted between the stable prefix and the volatile suffix in each
  phase's prompt builder.
- `orchestrator/_turns.py::list_turns` reads all prior round files
  from disk and re-inlines them on every new turn.
- `phase3.py:53` and the Phase 3 prompt builder confirm the drafter
  receives `brief + both P1 drafts + agreed plan + injected FSDs + the
  full P2 conversation`.

## Proposed change

### 1. Rewrite `how-it-works.jsx`

`src/dual_research/ui/static/how-it-works.jsx` becomes a longer file
(~1200 lines) organised as:

```
VERSION_NOTES (top)
  ↓
Small SVG helpers (AgentDisc / ClaudeDisc / GptDisc / Arrow / ArrowDefs)
  ↓
PhaseStrip                 — horizontal phase-flow card grid
NegotiationRoundDiagram    — kept from 0023 (CACHE_BREAKPOINT mention added)
TldrCards                  — NEW · 4-card strip
Tk, CallBox, LifecycleRow,
ChatLifecycle, Legend,
ComparePanel               — NEW · chat-lifecycle subsystem
ContextGrowthBars          — NEW · stacked-bar visual
PhaseMeta, PhaseAccordion  — NEW · phase deep-dive accordions
Faq                        — NEW · FAQ accordion
ProtocolOverviewMap,
ProtocolOverviewFold       — NEW · inlined v3.5 landscape + fold-out
ReleaseNote                — extracted from inline rendering
Section                    — common section wrapper (kicker · h2 · lede)
  ↓
HowItWorks (main component)
```

The page itself renders in this order:

1. Hero (kicker + title + lede + `TldrCards`)
2. **Overview** — `PhaseStrip` + the new `ProtocolOverviewFold`
3. **Chat lifecycle** — `ChatLifecycle` grid + `Legend` + `ComparePanel`
4. **Cost shape** — `ContextGrowthBars`
5. **Deep-dive** — five `PhaseAccordion` blocks (P0 default-open)
6. **Zoom in** — `NegotiationRoundDiagram` (kept)
7. **FAQ** — eight `Faq` accordion entries
8. **Changelog** — `VERSION_NOTES` rendered via `ReleaseNote`

All styles inline (matching the existing file's pattern). Native
`<details>`/`<summary>` for accordions — chevron is a static `▶`
character (no rotation animation to avoid `<style>`-injection in this
file).

### 2. Drop the v3.5 SVG as a static asset

`src/dual_research/ui/static/protocol-overview.svg` (new). 1660×880,
cream-and-indigo, Inter, no animations, no scripts. Authored via the
diagram skill; ships verbatim for the "Open SVG ↗" link in the
fold-out footer to point at. The same SVG content is also inlined
inside `ProtocolOverviewMap` so the page doesn't depend on the static
fetch resolving.

Both copies stay in sync by convention — if the diagram changes,
update both. The skill-canonical version lives on disk as the
single-file deliverable; the JSX copy is the rendered duplicate.

### 3. VERSION_NOTES entry

```js
{
  version: '0.24.0',
  date: '2026-05-16',
  summary: 'How-it-works restructure — chat-lifecycle diagram, phase accordions, v3.5 process map.',
  items: [
    'New "Chat lifecycle" section…',
    '"Context grows…" stacked-bar visual…',
    'Phase walkthrough converted to expandable accordions…',
    'FAQ entries collapsed into accordions…',
    'TL;DR strip of four cards…',
    'New "View full process map" fold-out…',
    'Stateless-vs-persistent comparison panel…',
  ],
}
```

Prepended above the existing 0.23.0 entry.

### 4. Version + CHANGELOG

- `pyproject.toml`, `__init__.py`: `0.23.0` → `0.24.0`.
- `CHANGELOG.md`: new `## [0.24.0] — 2026-05-16` entry under
  `### Added`, with the standard 4–6 sentence write-up linking to
  this spec.

## Out of scope

- **Inline comments on phase-2/3/4 drafts.** Still owned by the
  follow-up specs originally numbered 0026/0027 in spec 0025 (now
  available as 0027/0028).
- **LLM-generated TL;DR for the input card or final doc.** Heuristic
  remains as 0025 introduced it.
- **Re-rendering the static `dual-research-protocol-diagram.svg` from
  Downloads as a primary inline asset.** The v3.5 reference map lives
  behind the fold-out, not on the main scroll, on purpose.
- **Theme-aware v3.5 fold-out.** Light cream-and-indigo is the
  intended look of the reference diagram; it stays light regardless
  of the chrome bar's theme toggle.
- **Animations in the v3.5 fold-out.** The original SVG had `live-dot`,
  `tick`, and `loop-pulse` animations. The skill version is static —
  this page is a static reference, not a live dashboard.
- **Mobile layout pass.** The chat-lifecycle grid drops to one column
  under a 720px media query in the local HTML preview; we accept the
  JSX inheriting the same `grid-template-columns: 110px 1fr 1fr` and
  letting overflow scroll horizontally on narrow screens. The hosted
  audience is desktop.
- **CONTRIBUTING.md changes.** Spec 0023 already documented the
  `VERSION_NOTES` update step; no additions needed.

## Test plan

- [ ] Manual: open `#/how-it-works` locally (`uv run python -m dual_research --serve`), confirm the page renders end-to-end without JS errors. All accordions expand/collapse on click. The fold-out opens to reveal the cream-and-indigo v3.5 map. Theme toggle (chrome bar) flips the inline visuals but leaves the fold-out map light.
- [ ] Manual: same on the hosted Fly app after deploy. `/protocol-overview.svg` resolves directly (download link in the fold-out footer).
- [ ] Manual: light-mode pass. Token chips, accordion chevrons, and the lifecycle grid lanes remain legible on light cream.
- [ ] Confirm spec 0025's existing tests still pass (`pytest`). No backend changes here, so a stale snapshot is the only realistic regression.
- [ ] Visual review of the v3.5 fold-out: each card label readable at 100% zoom, no text overflow, all arrows hit their target stages, the APPROVED arrow is green and the others indigo.
- [ ] Release-notes entry shows at the bottom of the page with the right version + date + bullet list.

## Risks

- **Inline SVG file size.** `how-it-works.jsx` grows from ~550 lines to
  ~1200, with the v3.5 SVG inlined as ~280 lines of JSX. That's an
  extra ~17 KB of static asset for everyone. Mitigation: it's a static
  page hit infrequently; the chrome bar's `<script src>` already loads
  React + Babel + marked, so a 17 KB bump is in the noise. If the
  cost becomes real we can swap the inline SVG for an `<object>` tag
  pointing at the static-asset copy.
- **JSX SVG translation typos.** SVG attribute case differs in JSX
  (`stroke-width` → `strokeWidth`, `font-family` → `fontFamily`, etc.).
  Manual visual check covers this; if anything is mis-cased the
  diagram will render but the styling will be off. The original
  standalone SVG is the canonical version.
- **Skill drift if the diagram is regenerated.** The diagram skill's
  locked style is currently cream-and-indigo. If the skill is
  re-invoked later for an updated version of this diagram and the
  style drifts, both the static asset and the inlined JSX copy need
  to be updated together. Document this in the file's leading comment.
- **Two copies of the same SVG go out of sync.** Most likely failure
  mode. Mitigation: leading comment in `how-it-works.jsx` names the
  contract ("the same file ships as protocol-overview.svg in this
  directory for download"); a future spec can add a
  `tests/ui/test_protocol_overview_consistency.py` that diffs the two.
  Out of scope for this spec.
- **Spec-number collision with 0025's planned 0026/0027.** Documented
  in D10. The trade-off is "strict sequential per CONTRIBUTING.md"
  vs. "respect planning prose in a merged spec". Going with strict
  sequential; the inline-comments work renumbers when it lands.
