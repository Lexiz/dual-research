---
spec: 0023
title: Compact run-detail header, "How it works" page, and release notes
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.22.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/23"
---

# Spec 0023 — Compact header + "How it works" page + release notes

## Context

Two unrelated UX upgrades plus a release-notes process, bundled because
they all live in the chrome / header layer.

1. **The run-detail header eats four rows** of vertical space (top bar,
   topic, phase strip, footer-of-strip). Most of that is whitespace and
   redundant icons. A run detail should give the reader its identity,
   topic, phase, and headline status in one glance — without sacrificing
   a card-and-a-half of timeline real estate.

2. **There's no in-app explanation of what dual-research is doing.**
   Users see a timeline of "Phase 2 round 3, claude AGREED, gpt
   NEGOTIATING" but the protocol is opaque if you didn't build it. A
   dedicated "How it works" page exposed in the chrome bar fixes this.

3. **No surfaced version history.** We've shipped a lot in this track
   (push CLI, Fly deploy, OAuth, admin route, …) and there's nowhere a
   user can see what changed when. The "How it works" page is a
   natural home; CONTRIBUTING.md gets a one-liner about keeping it
   current.

## Design decisions

All low-reversal. Just decisions made for the sake of the spec body.

| # | Decision | One-liner |
|---|---|---|
| D1 | **Two-row run-detail header**, down from four | One primary row (back, id, topic, phase progress, cost, status, errors badge) + one subtle mono meta line (started, drafter, elapsed, phase outcome). |
| D2 | **Topic clamps to one line** on the primary row | Topic still drives identity; full text in `title` tooltip. Better-trafficked rows (phase, status, errors) get equal weight. |
| D3 | **Errors becomes a compact badge** | Same toggle behaviour, smaller pill. Click still swaps the main view to the errors panel. |
| D4 | **Phase progress moves right** of the topic on the same row | Closer to "completed/elapsed" status text where the eye is already looking. |
| D5 | **Chrome bar gets a "How it works" link** to the right of the connection pill | Conventional placement; matches the "design language" link pattern from spec 0022. |
| D6 | **"How it works" is a static React page** loaded at `#/how-it-works` | No API calls; lives entirely in the static bundle. The avatar gate still applies (the bundle is only reachable while signed in). |
| D7 | **Hand-authored SVGs in `--agent-a` / `--agent-b` theme colours** | Already the precedent (spec 0022 LandingScreen). Skipping the diagram skill — its cream-and-indigo palette would clash. |
| D8 | **Release notes embedded as a `VERSION_NOTES` JS array in `how-it-works.jsx`** | Single source of truth for the page; no extra fetch. Each entry: `{version, date, summary, items: []}`. |
| D9 | **CONTRIBUTING.md gets a one-paragraph note** about updating `VERSION_NOTES` when a spec changes user-visible behaviour | Process > tooling. Future specs that don't change anything visible can skip. |
| D10 | **Content grounded in real code**, not my recollection | I read `orchestrator/` and `protocol/` end-to-end before writing the page — see the spec's "Behaviour reference" below. |

## Behaviour reference (what the "How it works" page asserts)

These are the load-bearing facts the page is built around, sourced
from the actual code so I have something to point at if a future spec
drifts and the page goes stale:

- **Same brief, both agents.** `run.py` reads the brief once and passes
  it through to every phase. The only per-agent variation is the
  `agent_name` substitution in prompt builders (`protocol/prompts.py`).
- **Phase 0 / 1 / 2 / 4 all fire BOTH agents in parallel per round**
  via `asyncio.gather` (`phase0.py:51`, `phase1.py:51`, `phase2.py:129`,
  `phase4.py:105`). There is no fixed "who goes first."
- **No persistent chat.** Every turn is a fresh API call. The
  orchestrator builds the prompt with the full prior-turn history
  inlined (`_turns.py:25-50`). Anthropic prompt caching keeps the
  stable prefix cheap, but it's prefix caching — not a session.
- **Round 1 of Phase 2 can't AGREE by construction** — the prompt
  forbids it (`prompts.py::negotiation_round1_prompt`) and the
  validator doesn't require an AGREED_PLAN there.
- **Convergence** requires both agents in the same round to emit
  AGREED + matching DRAFTER + zero open questions + zero blocking
  disagreements + matching FSDs + a populated AGREED_PLAN whose
  normalized SHA-256 hash matches between the two
  (`convergence.is_plan_agreed`).
- **Tiebreak cascade** (`tiebreak.pick_drafter`): (1) matching
  recommendations win immediately; (2) domain-fit score (self +
  other's rating); (3) plan-alignment via word-set overlap with each
  agent's Phase 1 draft; (4) SHA-256(brief) coin flip as final
  fallback.
- **Phase 3** is single-shot by the chosen drafter
  (`phase3.py:53`) — full brief + both Phase 1 drafts + canonical
  agreed plan + full Phase 2 conversation inlined.
- **Phase 4 revised drafts** — only the drafter can include a
  `## Revised draft` section, which the orchestrator extracts and
  writes as `phase4/draft-v{N+1}.md`; next round reviews against the
  new draft (`phase4.py:184-205`).
- **Caps.** Soft cap = warn, keep going. Hard cap = abort, exit 51.
  Phase 4 hard-cap still emits a `final.md` with an unresolved-issues
  appendix and `confidence = LOW` (`finalize.py:24-25`).
- **Repair turns.** 1 attempt per agent per phase. Two consecutive
  malformed turns → exit 52 (`repair.py:100-102`).

## Proposed change

### Compact run-detail header (`src/dual_research/ui/static/run-detail.jsx`)

Replace `TopBar` + `PhaseStrip` with one `RunDetailHeader` component:

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [← All runs] [🔲 dual-research/70e3]  Compare SQLite vs Postgres…   •─•─•─•─•─●  PHASE 5 Done   $0.4228   ✓ completed   ⚠ 3        │
│   started 16:31 · drafter GPT · 12m 49s elapsed · converged in 12m 49s                                                            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

- **Primary row**: back chip, brand+id pill (merged), topic
  (single-line clamp with title tooltip), phase progress dots + phase
  label, cost, status badge, compact errors badge.
- **Secondary row**: smaller mono line — started clock, drafter,
  elapsed, phase-outcome text (e.g. "converged in 12m 49s", "hard
  cap", "halted").
- Total height ~62 px (down from ~120 px today). About one timeline
  card recovered.

`PhaseStrip` and `TopBar` deleted in favour of the new component.
`ErrorsToggleButton` becomes a small badge style; its toggle prop
plumbing stays.

### How-it-works page (`src/dual_research/ui/static/how-it-works.jsx`, new)

Reachable at `#/how-it-works`. Structure:

1. **Hero.** "How dual-research works" + 2-line lede + reuse of the
   `AgentDuoVisual` from `auth.jsx` (or a slightly larger variant).
2. **The five phases at a glance.** Inline SVG flow:
   `P0 → P1 → P2 → P3 → P4 → final.md`. Above each node, a small
   "parallel" / "turn-based" / "single-shot" hint chip.
3. **Phase-by-phase walkthrough.** Five sub-sections (P0…P4). Each
   has: short description, the actual prompt's intent in plain
   English, a small SVG showing parallelism (or lack thereof), and a
   note on convergence / completion criteria where applicable.
4. **The negotiation pattern in detail.** A larger inline SVG showing
   one Phase 2 round: brief + both Phase 1 drafts feed into both
   agents in parallel, two turn files emit, both files become input
   to the next round.
5. **What gets decided when.** Sequential micro-FAQ:
   - "Do they read each other's work?" → starting in Phase 2 yes;
     before that no.
   - "Who goes first?" → no one; per-round both agents fire in
     parallel.
   - "Same chat or fresh chats?" → fresh per turn; prompt caching is
     a transparent cost optimisation, not a session.
   - "How does it converge?" → matching AGREED status + plan-hash
     match in the same round.
   - "What if they don't converge?" → soft cap warns, hard cap aborts
     with confidence=LOW and an appendix of unresolved disagreements.
   - "Who picks the drafter?" → tiebreak cascade.
   - "What if an agent emits garbage?" → one repair attempt; two
     consecutive failures abort.
6. **Cost & caps.** Brief paragraph on prod-tier vs test-tier model
   pairs and what soft/hard cap defaults mean.
7. **Release notes.** Rendered from `VERSION_NOTES`, newest first.
   Each entry: version + date + 1–4 bullets. Seeded with entries for
   v0.18 → v0.22.

Use existing theme tokens throughout: `--bg-1` for cards,
`--agent-a` / `--agent-b` for visuals, `--fg-2` for secondary text.
Scrolls inside the `<main>` region — same shell as the design-language
page.

### Router + chrome bar (`router.jsx`, `app.jsx`)

- `parseHash` and `buildHash` learn `#/how-it-works`.
- Chrome bar's `RightCluster`:
  - Add a `HowItWorksLink` to the right of `ConnectionPill`
    (`Icon.Help` — needs a new entry in `Icon` map).
  - On click → navigate to `#/how-it-works`.
- `App` adds `route.view === 'how-it-works'` → `<HowItWorks />`.

### Maintenance note in CONTRIBUTING.md

One paragraph in the "Workflow" section: when a spec changes
user-visible protocol behaviour (parallelism, phase semantics, caps,
tiebreak, etc.) or ships a new visible feature, add a new entry to
`VERSION_NOTES` in `how-it-works.jsx`. Specs that touch internal
plumbing only can skip.

### Version + CHANGELOG

`pyproject.toml` 0.21.0 → 0.22.0. `__init__.py` ditto. CHANGELOG
gets `## [0.22.0]`.

## Out of scope

- **Localisation.** English only.
- **MDX / external markdown source.** Content lives inline as JSX so
  the page is one file. Could move to MDX if it grows past ~600 lines.
- **Per-section anchors / deep links.** `#/how-it-works` lands at the
  top; smooth-scroll-to-section is a future-spec polish.
- **Search / "find in page".** Native browser find is fine.
- **Versioning the "How it works" content itself.** If the protocol
  fundamentally changes (e.g. 3 agents, different convergence
  contract), a future spec rewrites the page; we don't keep historical
  versions.
- **Embedding the actual prompts** in the page. Linking to
  `protocol/prompts.py` would be nice but the bundle has no source
  browser today; GitHub link is sufficient.
- **Diagram-skill SVGs.** Hand-rolled to fit the dark theme.

## Test plan

Mostly UI — no JS test infrastructure today. The Python suite covers
backend behaviour and shouldn't change.

- [ ] `pytest tests/` stays green (currently 277).
- [ ] Manual: header now fits one card-row more vertically than before
      on a 1440px screen.
- [ ] Manual: `#/how-it-works` is reachable from the chrome bar link
      and from a direct hash, renders all sections, includes seeded
      release notes.
- [ ] Manual: SVGs render in both light and dark themes.

## Risks

- **Header redesign collisions** with the live-data flow. The header
  reads `run.status`, `run.phaseTimings`, `run.round`, `run.drafter`
  — all already populated by the aggregator. No new fields.
- **Visual regressions** in narrow widths. Topic clamp + phase
  progress on the same row will collide below ~900 px. Mitigation: at
  narrow widths, the topic gets smaller and progress dots stay
  reserved; phase label may wrap to the meta row. Acceptable.
- **Release notes drift.** A future spec might forget to update
  `VERSION_NOTES`. CONTRIBUTING.md note is the prompt; the cost of
  drift is low (just stale).
- **Anti-explanation drift.** The "How it works" page is a *user-
  facing* surface but its claims are tied to internal code. If a
  future spec changes parallelism or chat semantics, the page must
  follow. Mitigation: this spec's "Behaviour reference" section above
  is the canonical pointer-list a future contributor can re-check.

## Open questions

None.
