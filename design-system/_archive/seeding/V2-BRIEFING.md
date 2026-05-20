# Dual-research dashboard — v2 design system + known-issues briefing

> **For Claude Code.** Read this file end-to-end before doing anything.
> Two streams are bundled here: (1) a complete rebuild of the design system under Material 3, and (2) 17 implementation bugs/inconsistencies the product owner logged in Notion. Your one deliverable for this round is **not code** — it is a specifications plan. See [§1 — Your task](#1--your-task).

---

## Table of contents

1. [Your task](#1--your-task)
2. [Hard constraints (read first)](#2--hard-constraints-read-first)
3. [What's in this PR](#3--whats-in-this-pr)
4. [Stream A — Design system v2 (Material 3)](#4--stream-a--design-system-v2-material-3)
5. [Stream B — 17 known issues from Notion (verbatim)](#5--stream-b--17-known-issues-from-notion-verbatim)
6. [Deep dive — Consumption rows (issues 12 / 13 / 14 / 15)](#6--deep-dive--consumption-rows-issues-12--13--14--15)
7. [Deep dive — Critique pane & QuestionThread (issues 2 / 3 / 4 / 7 / 8 / 9 / 10 / 11 / 16)](#7--deep-dive--critique-pane--questionthread-issues-2--3--4--7--8--9--10--11--16)
8. [Deep dive — Onboarding tour (must be an overlay)](#8--deep-dive--onboarding-tour-must-be-an-overlay)
9. [Deep dive — How It Works + Changelog (top-bar button)](#9--deep-dive--how-it-works--changelog-top-bar-button)
10. [Themes — dark + light](#10--themes--dark--light)
11. [Validation checklist before you hand back the plan](#11--validation-checklist-before-you-hand-back-the-plan)
12. [Where to find every asset](#12--where-to-find-every-asset)

---

## 1 · Your task

**Tell me how many specifications we need to cover everything in this briefing.**

Concretely, your deliverable is a **spec plan**: a list of specifications (titles + short scope + rough sequencing) that, when implemented one after the other, will:

- Resolve every one of the **17 known issues** logged in Notion (see §5).
- Land the **complete Material 3 visual rebuild** described in the design system (Stream A) on the live frontend.
- Implement the **specific behaviour rules** in §§ 6-10 (consumption granularity, onboarding overlay, How It Works button + right-side menu, both themes).

For each spec, include:

| Field | What goes in it |
|---|---|
| **#** | Sequence number |
| **Title** | What it ships |
| **Scope** | Bullet list of issues addressed + components touched |
| **References** | Which Notion issue numbers + which design-system sections |
| **Depends on** | Other spec numbers it must follow (e.g. tokens before components) |
| **Backend touched?** | Almost always *no* — flag explicitly when *yes* |

**Sequencing rule of thumb:** ship the token layer (colour / shape / type / elevation / motion) first, the primitive components next (buttons, chips, cards, status pills, badges), then the composed components (consumption, critique, question thread, timeline pane), then the page-level features (How It Works modal, onboarding overlay), then the polish issues. Use this as a starting point, not a constraint — propose the slicing you think is right.

The product owner will read your plan and either approve it or push back on the slicing. **Do not start implementing.** Plan first.

> The Notion page is the source of truth for the issues. Its URL is in §5. You have a Notion connector wired up — you can pull the page directly and pull the screenshots from S3 to compare with the current UI before writing each spec.

---

## 2 · Hard constraints (read first)

### Backend is frozen
We spent considerable time stabilising the backend protocol and we are happy with it. **Do not propose any backend changes.** Every issue and every design-system rework is frontend-only. If a frontend change requires data the backend does not expose, scope the spec to render what the frontend has and degrade gracefully — never propose adding a field.

### Material 3 is the visual language
The whole design system flipped to Material Design 3. Shapes, colours, fonts, elevation, state layers, motion, component anatomy — all M3. The palette is preserved (sable = primary, sage = secondary, info = tertiary, status hues unchanged). Specifications must reflect that visual flip, not patch the old visual language.

### Both themes ship together
Every spec must produce a result that works in **dark and light** with no extra work. Light isn't a follow-up — token roles are theme-agnostic, so a correctly written component renders both. Flag any spec where this isn't true.

### Read-only discipline
The dashboard is observability. No spec should add buttons that mutate run state. Filters, focus shifts, view switches — yes. State mutation — no.

### Density + responsiveness
Comfortable density by default (M3 spacing). Compact toggle exists. Responsive break-points: ≥1500 px (full), <1500 px (compact rail + denser grid), <900 px (single column). Specs that touch layout must address all three buckets or explicitly defer them with a follow-up note.

---

## 3 · What's in this PR

```
pr/
├── README.md                            ← you are here
└── assets/
    ├── Design System v2.html            ← the visual source of truth (open this in a browser)
    └── styles/
        ├── v2-m3.css                    ← M3 token layer + primitives
        └── v2-m3-page.css               ← page-level component CSS
```

The `Design System v2.html` file is **the canonical reference for every visual decision**. Whenever a spec mentions a component, point to the section anchor in that file (e.g. `#critique`, `#consumption`, `#timeline`, `#tour`, `#how`). The HTML uses inline-comments to mark each section.

Section index inside the design system file:

| Anchor | Section |
|---|---|
| `#identity` | Hero + identity overview |
| `#principles` | Voice & principles |
| `#palette` | Colour palette (M3 roles) |
| `#type` | Typography (Roboto Flex + Roboto Serif) |
| `#icons` | Iconography (Material Symbols Outlined) |
| `#fmt` | Data formatting |
| `#shape` | Shape & spacing scale |
| `#elevation` | Elevation, state layers, motion |
| `#system` | System layer (token roles) |
| `#atoms` | Buttons, chips, status pills, switches, FABs |
| `#cards` | Cards · AgentStrip · **Badges** (badge inventory) |
| `#tabs` | Tabs · Theme switch |
| `#critique` | **Critique pane header** (three states, collapsible groups) |
| `#thread` | **QuestionThread** (pill above quote, full-width) |
| `#consumption` | **Consumption row** (collapsed + unfolded + uniform-across-phases) |
| `#input` | Agent input panel |
| `#timeline` | **Timeline pane** (chrome + composition rules) |
| `#modal` | Modal · PhaseRail · RoundScrubber |
| `#tour` | Onboarding tour (8 steps + admin) |
| `#how` | How It Works (long-form, 9 sections) |
| `#admin` | Admin · ProgressSegs |
| `#loading` | Loading state |
| `#states` | States gallery |
| `#a11y` | Accessibility |
| `#light` | Light mode preview |
| `#responsive` | Responsiveness rules |
| `#changelog` | Changelog |

---

## 4 · Stream A — Design system v2 (Material 3)

The entire design system was rebuilt under Material 3. Below is the inventory of what changed, so you can scope specs that bring the frontend in line.

### 4.1 — Tokens (foundation)

| Layer | Before (v1) | Now (v2) |
|---|---|---|
| **Colour roles** | Direct hex tokens (`--agent-a`, etc.) | M3 roles: `--md-primary` (sable), `--md-secondary` (sage), `--md-tertiary` (info), `--md-error`, each with a `-container` + `on-*` pair |
| **Surface tiers** | 5 flat surface tokens (`--bg-0..4`) | M3 tonal surfaces: `surface`, `surface-container-{lowest, low, , high, highest}`, plus elevation-derived `--md-surface-1..5` (surface + primary tint at 5/8/11/12/14 % opacity via `color-mix`) |
| **Shape scale** | 4 named radii + pill | M3 six-step: `xs` 4 · `sm` 8 · **`md` 12 (default)** · `lg` 16 · `xl` 28 · `full` 9999 |
| **Type scale** | 7 rough sizes (`--t-display`, `--t-title`, etc.) | **M3 fifteen-role scale**: display L/M/S, headline L/M/S, title L/M/S, body L/M/S, label L/M/S |
| **Fonts** | IBM Plex Sans + Plex Serif | **Roboto Flex** (plain, UI) + **Roboto Serif** (brand / agent voice / displays + headlines). M3 defaults. |
| **Elevation** | 3 levels (`--e-0..2`) | **6 M3 levels** (`--md-elev-0..5`) using shadow recipes + tonal-overlay surface tint |
| **State layers** | Ad-hoc hover bg | M3 currentColor overlays at 8 / 10 / 12 / 16 % for hover / focus / pressed / dragged |
| **Motion** | 3 durations + one ease | M3 emphasized + standard easings, 8 duration tokens (short-1 … long-2) |
| **Icons** | ~16 hand-curated outlined glyphs | **Material Symbols Outlined** (~60 in 6 grouped catalogues). Agent brand marks (sable burst, sage rosette) stay custom |
| **Density** | comfortable + compact (auto under 1700 px) | Same toggle, now wired to M3 spacing tokens |

The palette is preserved verbatim. Sable `#d4a574`, sage `#7cc4b8`, info `#6b9cf0`, ok `#6fb380`, warn `#d4a056`, err `#d96a6a`, idle `#5e636d`. Pastel chromatics, neutral surfaces. Surface tint follows the active agent (sable on Claude pages, sage on GPT pages).

### 4.2 — Primitive components

| Primitive | Anatomy under M3 |
|---|---|
| **Buttons** | 5 variants — filled / tonal / outlined / text / elevated. Pill radius (`--md-shape-full`). 40 dp height, 24 dp horizontal padding, label-large type. Hover/press via state-layer overlay. |
| **FAB** | 56 × 56 dp, shape-lg corners, surface-1 tint, elevation-3. Extended FAB carries label after the icon. |
| **Icon button** | 40 × 40 dp, pill, state-layer overlay. |
| **Chips** | Assist · filter · input · suggestion. 32 dp height (24 dp for `sm`), shape-sm corners, label-large type. |
| **Status pills** | 22 dp height, pill, with leading 6 dp dot in currentColor. Six states: running · converged · drift · errored · idle · queued. |
| **Switches** | 52 × 32 dp, M3 thumb-grows-on-on. |
| **Segmented buttons** | Pill container, M3 secondary-container on selected. |
| **Cards** | 4 variants: elevated · filled · outlined · agent-tonal (primary-container / secondary-container). Shape-md (12 dp). |
| **Tabs** | Primary tabs with M3 active-indicator bar; secondary as solid segmented pill (used for theme + density + agent + status filters). |
| **Dialogs** | Shape-xl (28 dp), elevation-3, max-width 560 dp (basic) / 1080 dp (rich). |
| **Top app bar** | 64 dp, surface-container. |
| **Navigation rail** | 280 dp open, collapses to 80 dp icon-only under 1500 px. |
| **List items** | M3 three-line list anatomy (lead · headline · support). |

### 4.3 — Composed components (the heavy ones)

These are the components most of your specs will touch.

- **Critique pane header** (`#critique`) — Two bars. Bar 1 carries title + phase tabs (P2 Negotiate / P4 Review / Σ Summary) + run-wide totals (introduced · open · resolved · drift chip). Bar 2 carries kind tabs with per-phase counts (All / Issues / Comments / Questions / Disagreements) + agent + status segmented controls. Σ Summary state hides bar 2. Body uses **collapsible status-grouped sections** (`Open · new this round` info-strong tint, `Open · carried over` warn tint, `Resolved` ok tint, `Drift` err tint) — each with rotating chevron + count chip in matching tone.
- **QuestionThread** (`#thread`) — Three variants (resolved · open · drift) with border-left tinted by state. Each row: pill above + quote in serif italic taking the full card width (no left sidebar). Verdict vocabulary: `raised`, `pushback`, `conceded`, `resolved`, `ghosted`, `drift` (never abbreviated).
- **Consumption** (`#consumption`) — Three forms documented:
  - **Collapsed:** header (provider icon + name + total tokens + total cost + % of 1M) → total-in bar → total-out bar.
  - **Unfolded:** all of the above + breakdown sub-rows under total-in (system prompt, conversation history with `×N reuse` mark, round context, tool definitions `cached`, web sources `Nq`) and under total-out (reasoning, response, tool calls), each with a totals block (input tokens billed, input cost, web-search cost, cache savings line, grand total).
  - **Uniform-across-phases:** all cards share the same horizontal size across phases; round label sits *above* the card.
- **Timeline pane** (`#timeline`) — Header chrome only documented (Timeline · count title, pill-style Conversation / Consumption tabs, vertical phase indicator outside the column). Body is built from existing primitives: `.tl-phase` collapsible section + `.tl-turn` one-line row + `.tl-turn--open` expanded card. No new primitives — composition only.

### 4.4 — Page-level patterns

- **Onboarding tour** — 8 steps, all rendered as M3 dialogs / spotlights overlaid on the *live* app (see §8).
- **How It Works** — Long-form, 9 sections, surfaced via a top-bar button + right-side menu that toggles How It Works ↔ Changelog (see §9).
- **Admin · ProgressSegs** — 8-segment track per user (one per onboarding step).
- **Loading / States / A11y / Light mode / Responsiveness / Changelog** — documented sections, each with a clear acceptance bar.

---

## 5 · Stream B — 17 known issues from Notion (verbatim)

**Notion page:** https://www.notion.so/Known-issues-36499f3e507f80b0b5b6ccadbd0a900b?source=copy_link

> **Use the Notion connector.** You can fetch the page directly and pull each screenshot from S3 to verify your spec against the current implementation. The text below is captured verbatim. Screenshots live under each issue on the Notion page (image links resolve via short-lived signed URLs — refetch the page when you need them).

### Issue 1 — Model badges (Claude / GPT) have inconsistent heights

> As you can see on the screenshot, the height of the GPT badge and the height of the Claude badge on the right-hand side are not the same. It is probably because the Claude Sonnet 4-6 name pushes the content upwards. Also the GPT badge itself is a little bit too tight from a vertical space point of view.
>
> I would need to increase the height of the GPT 5 badge slightly. I would need you to make sure that the Claude badge is the exact same height and that they are both horizontally just a little bit longer so that the entirety of the Claude Sonnet 4-6 name would fit in there. I need you to take a screenshot afterwards to validate that it happened.

**Design system anchor:** `#cards` (AgentStrip · badge inventory), `#shape` (heights are on the 8 dp grid).

### Issue 2 — Critique section structure is wrong (use the design-system layout)

> As you can see in the screenshot below, this is how we currently implemented the critique section.
>
> And this is how you should have implemented it so please make sure that that's the design once you have fixed the issues.

**Design system anchor:** `#critique`. Bar 1 (title · phase tabs · totals + drift chip). Bar 2 (kind tabs with counts · agent · status). Body in collapsible status-grouped sections. Σ Summary hides bar 2.

### Issue 3 — Phase headers should be bigger than card headers + hover elevation on cards

> Issue number 3: it's the size of the face headers versus the cards inside. What I would like to do is I want to make sure that the face header is bigger than the card header.
>
> Please look at the screenshot below. That's a screenshot from the critique section. I want to make sure that the cards in the timeline section are the same size as the cards in the critique section. I want to make sure that the face headers for Phase 1, Phase 2, and Phase, and also the face headers in the critique section (drift, open, resolved, answered) will be slightly bigger than they are now so that they're just a little bit higher than the card inside it. Also in our design system we have elevation options. I would like to make sure that when you hover over a card (not a header) in both the timeline and the critique sections, the card will get an elevation on hover.

**Design system anchors:** `#critique`, `#timeline`, `#elevation` (the elevation tier to apply on hover is level-2).

### Issue 4 — All "OK" badges must use one consistent style

> If you look at the current screenshot on the right-hand side, we are showing batches with OKs. All our OK batches should look the same. We should pick one style and we should show that style. I need you to. The style I would like to pick is the lower two OKs. The first OK should not look like this. All the OKs should look like the green two OKs.

**Design system anchor:** `#atoms` (status pills). The chosen style is the standard `.md-status.md-status--converged` chip (pastel-green pill + dot + uppercase label).

### Issue 5 — Phase indicators on the timeline jump around / aren't anchored

> The timeline component is still broken. The indicators on the left of the headers, the green dot with P0, P1, P2, are not correctly anchored to the headers themselves as you can see on the various screenshots. They jump all over the place and do not have an understanding of how many headers there are currently displayed. As you can see in some of the screenshots, we only have three headers for phase one, for phase 0, 1, and 2, but somehow all the indicators are overlapping and showing phase 4 and other phases that we haven't even started yet.
>
> Most importantly none of them are anchored. If you can see on the screenshots, sometimes the face is open and sometimes this face is closed and all these dots are jumping all over the place. You need to make sure that you validate that, through several screenshots, once this feature is finished. When you open and unfold and have different types of scenarios where you have one, two, or five different headers and these headers are collapsed or open, the anchored indicators on the left should always be in the right spot.

**Design system anchor:** `#timeline`. The vertical phase rail in v2 lives outside the timeline column and renders exactly one marker per *visible* phase header. Markers must anchor to the phase header's vertical centre (top of the section), not float by index. If a phase has no data yet, the marker is hidden — not greyed.

### Issue 6 — Three headers in the run-detail strip should be reduced to two

> See screenshot below. We have three headers:
> 1. The header with the buttons all runs, compare, and search.
> 2. The header with dual search runs and spent.
> 3. The header with the filter buttons.
>
> I want this to be reduced from three headers to two headers. How do we do that?
> - You completely remove the icon and the text dual search.
> - You remove the empty word runs.
> - You move the buttons three runs and cost all the way to the right, aligned with the search.
> - You take the filter buttons below and put them in that spot where we just removed everything. Left aligned in the second header.
>
> That frees up the entire third header and we can completely remove that.

**Design system anchors:** `#tabs` (segmented controls), `#atoms` (buttons), `#cards` (badge cluster).

### Issue 7 — Question card duplicates the question at the top

> See the screenshot. We are in the questions card, repeating the question without any value. If you look at the top we start first with the question on D6 specification, review, OpenAI, and so forth. Then we have a quote and then we say Claude round one raised and we repeat the exact same question as we start with at the top.
>
> Let's not do that. I want to remove that first question at the top. Start directly with the provider who raised the question badge as the first chip and put the quote inside the relevant provider who actually had the quote.

**Design system anchor:** `#thread`. Quote belongs inside the tonal-tinted agent message bubble, not in the card header.

### Issue 8 — Disagreement card has the same duplication problem

> The exact same thing can be said about disagreements. Also there we start with a resolved batch and just at the top we already have a resolved batch so that's not needed. Let's start with the very first thing: the model who started it and then we chronologically follow the trail.

**Design system anchor:** `#thread` (the `.qthread` resolved/drift variants — header pill cluster + chronological turns; no duplicate quote at the top).

### Issue 9 — Issue card (review phase) has too much info, illogical sequence, duplicated quote

> I'm looking here at an issue card from the review phase and there's too much information there and some of it doesn't even align.
>
> At the top we start with issue 0.1, Claude, a batch for issue 0.1, a batch for Claude, followed by a batch that says "resolved". If we look below it we start with C1. I don't even know what C1 means. We have an anti-pattern that we cannot have these random letters and digits. If we want to say something, it should be clearly indicated with the batch and the batch should spell out the full name. Maybe that batch is not even needed there.
>
> We follow up with a status that says "open" while the issue says "resolved". I'm not sure: is it open, is it resolved? This is followed by, I guess, a title, but then followed by a quote and only then by some paragraph. This is then followed by "flagged by Claude", "first seen in round 1", "last seen in round 2", and then followed again by something random, which is the exact same quote. Followed again by the exact same quote. All of it just doesn't make sense.
>
> We need to clearly start by indicating who raised the issue and in what round. We can mention in what second round it was raised. We then mention the issue and we then have a quote below it so that is sequentially it makes sense to consume the information. In the header of the card we put the correct batches as well that would align but not overlap with the same info, that would provide information, but not overlap with information when you unfold the card.

**Design system anchor:** `#thread`. Anti-pattern: cryptic codes like "C1". Full-word vocabulary always.

### Issue 10 — Comments on the review tab have the same anti-patterns as issue 9

> The exact same thing as issue number nine can also be said about the comments on the review tab. Those cards also have an illogical sequence of presenting information. Quotes are duplicated and the badges are just not correct. Please make sure that you follow the same logic as you apply for number nine so that all of them show information that is relevant when it is closed, when it is open, and in the right sequence, and that there is no duplicate information present.

**Design system anchor:** `#thread`. Same fix as issue 9, applied to the Comments-kind variant.

### Issue 11 — Double divider line when unfolding the first card under Phase 4

> See if the attached screenshots when I unfold the first card under phase four, then it gets two divider lines instead of just showing one divider line. It looks awkward.

**Design system anchor:** `#timeline` (`.tl-turn--open` body uses *one* dashed top border between the row and the body).

### Issue 12 — Collapsed consumption card data points must change

> I would like to change the data points and visualisation and what we record on these cards. Let's go over it.
>
> When the card is collapsed right now we're showing three headers:
> 1. The first header with the cloud icon and cloud name
> 2. The second header with the cost
> 3. The third header with the bar
>
> That's what we have now.
>
> I would like to change the data points on the collapsed versions of our data consumption screens. What we would have to have is the following:
> 1. The first header should have the provider icon, the provider name, the total amount of tokens, and the total cost, and then the percentage in brackets of these total tokens compared to their available context.
> 2. On the second header, where we right now show input cost, output cost, and total cost, these data points should not be shown when the card is in a collapsed state. Instead we should show the total input bar.
> 3. As the third header, where we now have the total input bar, which now moves up on the third row, we show the total output bar. It's a new data point which we currently do not have.
>
> I repeat the new state would be:
> 1. First header: I can provide a name, total tokens, total cost, and percentage of total tokens against the context. These three data points should start aligning at the same level where the bar starts.
> 2. On the second header we show the total input bar.
> 3. On the third header we show the total output bar (output bar), and both bars can indicate the actual amount of tokens at the end of the bar, just like you do now.

**Design system anchor:** `#consumption` (collapsed form).

### Issue 13 — Unfolded consumption card data points must change

> Here I would like to change the data points of the unfolded version of the cards but we need to take into consideration the changes that we did for issue number 12.
>
> Once issue number 12 is implemented what I want to happen is that when you unfold the card, the first thing that we start with is total input tokens. We show the total bar then below it we show an entry for every single input that we record separately. We also show the bar for that.
>
> Once we've exhausted all the visualisations of the inputs, we show a separation line and below that we show in text:
> - the total input tokens as a number
> - the total input tokens as a cost
> - the web search as a cost if we did web search
> - the total cost for the input
>
> Then we show that total output bar and we follow the same logic. We show every individual entry that represents the output as a name plus bar. Once we have exhausted all of them, we show a new separation line and below that we show the same data points as above:
> - total output tokens
> - total output cost
> - any web searches that we did
> - the total cost there where you show that we had so much token reuse batches
>
> If there is a way how you could also visualise in this individual entries where reuse happened, that would be nice. I guess that's what you already do with the striped visualisation.

**Design system anchor:** `#consumption` (unfolded form). Cache reuse rendered as the diagonal-stripe overlay on the bar; reuse multiplier (`×5.9`) as a tiny chip on the *left* of the count with a hover tooltip carrying the dollar saving.

### Issue 14 — Consumption cards change horizontal size between phases

> As you can see on the screenshot, the cards where we visualise the consumption change all of a sudden change format when we go into the rounds of negotiation and later also in the rounds of review, and that causes complete chaos on screen. We need to make sure that the cards always stay the same size and the size is the exact size as you start in Phase 0 and Phase 1, and it should continue with the same size. We should find a way how we visualise round 1 differently. Perhaps we can put it at the top of each card so that all cards always have the exact same horizontal size.

**Design system anchor:** `#consumption` (uniform-across-phases form). Round label is a small chip rendered **above** the card, not inside the header; cards retain identical width across all phases.

### Issue 15 — Consumption legend should be a sticky bottom bar

> Also on the consumption tab below we have a legend but because we always have a lot of cards, that legend is all the way below and you have no visibility on all of this. Can you make it such that this becomes a sticky lower bottom bar and that when you scroll the content scrolls below it so that the legend always stays on screen?

**Design system anchor:** `#consumption`. Sticky bottom legend sits inside the consumption pane (not the page) — surface-container-high, hairline top border, elevation-1.

### Issue 16 — REPAIR-round explainer card

> When we have a round where we have a repair, can you please put the repair tag inside the card that says "GPT silent this turn"? Can you also actually explain what that means in a small sentence below it, like what happened and what's going to happen next, so that it's clear to the user what they're looking at?

**Design system anchor:** `#timeline`. REPAIR is a special turn row variant: the `.tl-turn` carries the `REPAIR` tag inline and the expanded body contains a single-sentence explanation (e.g. *"GPT was silent this turn. Claude will reissue the prompt on the next round with the same plan hash."*).

### Issue 17 — Top-bar layout when viewing an individual run

> As you can see on the screenshot, this is a view of the top bar when I'm viewing an individual run.
> 1. First of all for some reason we put the back button in between the version and the "How it works" button. That's not needed. Please remove the back button. We don't need it there.
> 2. Once we remove that we need to make sure that there is a separation line between the version tag and the "How it works" button.
> 3. We also need to make sure that they're both aligned the same way so that the version and "How it works" are equally aligned vertically so that they don't look like it's jumping.

**Design system anchor:** `#tabs` (top app bar pattern). Remove the back button entirely. Vertical 20 dp divider between version chip and How-It-Works button. Both elements baseline-aligned with the rest of the bar (40 dp control row).

---

## 6 · Deep dive — Consumption rows (issues 12 / 13 / 14 / 15)

The product owner has expanded the consumption visualisation significantly. **All four issues are one spec or a closely-linked pair.** Read together:

### 6.1 — Collapsed card (issue 12)

Three rows, in order:

1. **Header.** Provider icon (sable circle "C" / sage circle "G") · provider name · total tokens · total cost · `(N % of 1M)` percentage of context window. The three numeric values right-align to the bar's left edge so they sit in a column.
2. **Total input bar.** Label `total in` · bar · numeric count at the end. Bar uses the agent colour at full opacity.
3. **Total output bar.** Same layout, agent colour at ~55 % opacity.

No cost line, no per-bucket breakdown, no input vs output cost split. That's reserved for the unfolded state.

### 6.2 — Unfolded card (issue 13)

The collapsed view stays at the top, then expands downward with this exact order:

1. **Total input bar** (already shown when collapsed).
2. **Divider** (single line).
3. **Sub-rows under total in** — one row per recorded input bucket. Each: label · thin bar (same horizontal scale as the total) · count. The bars carry a **diagonal-stripe overlay** where cache reuse happened. Reuse multiplier renders as a tiny chip on the *left* of the count (`×5.9`, `cached`, `6q`) with a hover tooltip carrying the dollar saving.
4. **Input totals block.** A card with these lines in order:
   - `N` input tokens billed
   - `$X` input cost
   - `$Y` web search · `N queries` *(only if there were web searches)*
   - `−$Z` cache savings · `×N reuse on Mkt` *(only if there was reuse)*
   - `$T` **total input** *(grand-total line, bold rule above)*
5. **Spacer.**
6. **Total output bar.**
7. **Divider.**
8. **Sub-rows under total out** — same pattern, one row per recorded output bucket.
9. **Output totals block** — same structure as the input one.

**Granularity rule:** if the backend doesn't emit a particular bucket, *omit that sub-row* and recompute the totals block from what *is* available. Do not invent buckets. Do not hide the visualisation entirely — render whatever subset the backend gives.

### 6.3 — Uniform-across-phases (issue 14)

Cards keep the **same horizontal width** through P0 → P4. The round label (e.g. `P2 · round 1 of 6 soft`) is rendered as a small uppercase chip *above* the card, **not** inside the header trio. The phase grouping itself uses the `.phase-group-head` label.

### 6.4 — Sticky bottom legend (issue 15)

Place a legend bar at the bottom of the consumption pane that is sticky to the pane (not the viewport). Anatomy: surface-container-high background, hairline top border, elevation-1, padding ½ × full step. Inside: agent colour swatches, bar-overlay legend (solid = current charge · stripe = cache reuse · accent = web search), and short text legend lines.

---

## 7 · Deep dive — Critique pane & QuestionThread (issues 2 / 3 / 4 / 7 / 8 / 9 / 10 / 11 / 16)

These nine issues converge on **two components**: the critique pane (`#critique`) and the QuestionThread / item card (`#thread`).

### 7.1 — Critique pane (issues 2, 3, 4)

Implement the design-system layout exactly:

- **Bar 1** — title `Critique` · phase tabs (P2 Negotiate / P4 Review / Σ Summary) · run-wide totals (`introduced`, `open`, `resolved`) + drift chip on the right.
- **Bar 2** — kind tabs (All / Issues / Comments / Questions / Disagreements) with **per-phase counts** baked into each tab as a colored chip · agent segmented filter (All / Claude / GPT) · status segmented filter (All / Open / Resolved / Drift). Hide bar 2 in Σ Summary state.
- **Body** — **status-grouped collapsible sections** with a rotating chevron header:
  - `Open · new this round` (info-strong tint, info count chip)
  - `Open · carried over` (warn tint, warn count chip)
  - `Resolved` (ok tint, ok count chip — collapsed by default)
  - `Drift` (err tint, err count chip — collapsed by default)
- **Phase header sizing** — phase headers are *taller* than the cards inside them (issue 3). Use the M3 title-medium type role for the section header label, body-medium for the card title.
- **Hover** — every card (not the section header) gains elevation-2 on hover (issue 3).
- **Status pill style** — all "ok" pills follow the standard `.md-status.md-status--converged` style (issue 4). Don't invent variants.

### 7.2 — QuestionThread (issues 7, 8, 9, 10)

The thread component lives inside the expanded state of a question / disagreement / issue / comment card. Anatomy:

1. **Card header (always visible).** First chip = agent who raised it (AgentStrip, sable or sage). Second chip = `qref` (e.g. `Q · 03` with the kind letter colour-coded). Third chip = status (`open · new`, `open · carried`, `resolved · r3`, `drift`). Fourth chip = phase + round meta.
2. **Quote (only when expanded).** Render the quote *inside* the tonal-tinted message bubble of the agent who said it. Use serif italic, full card width, pill (`agent · round · verdict`) above on its own line.
3. **Subsequent turns.** Same bubble pattern, ordered chronologically — `raised` → `pushback` → `conceded` → `resolved`. Verdict vocabulary is fixed at six words: `raised`, `pushback`, `conceded`, `resolved`, `ghosted`, `drift`. Never abbreviate.
4. **Resolved or drift footer.** A single dashed top-border line carrying a one-line summary (`resolved at round 3 · 2 turns to converge · hash match` / `drift · recorded with full history · does not block exit`).

**Anti-patterns to remove** (issues 7, 8, 9, 10):

- ❌ Duplicating the question/disagreement title text *both* in the card header and again inside the first bubble.
- ❌ Cryptic codes like `C1`, `D3` without a full-word badge.
- ❌ Status mismatch between the card header pill and the inner bubble pill.
- ❌ Showing the quote more than once on a single card.
- ❌ "Flagged by Claude · first seen in round 1 · last seen in round 2" lines that duplicate badge info.

**Sequence rule:** who → when → what → quote. In that order. Always.

### 7.3 — Double divider on unfold (issue 11)

When a `.tl-turn--open` opens, render *one* dashed top border between the still-visible row and the body. No second solid divider underneath. Trim it to one rule.

### 7.4 — REPAIR-round explainer (issue 16)

A REPAIR turn (e.g. `GPT silent this turn`) renders as `.tl-turn` with the `REPAIR` tag inline and the expanded body containing one explanatory sentence: what happened, and what the orchestrator will do next. Sample copy: *"GPT was silent this turn. Claude will reissue the same plan on the next round. No data lost."*

---

## 8 · Deep dive — Onboarding tour (must be an overlay)

The design system documents an 8-step onboarding tour with welcome modal · row spotlight · run-detail header spotlight · phases explainer modal · timeline spotlight · critique pane spotlight · consumption spotlight · closing modal.

**Critical implementation rule:** the tour is an **overlay** over the live application. **Do not** render a tour-only re-creation of the run list, run-detail page, consumption tab, etc. The tour must:

1. Mount on top of the existing routed page (`/runs` for steps 1–2, `/runs/<id>` for steps 3–7).
2. Use real DOM nodes from the existing components as spotlight anchors. The spotlight cut-out reads the bounding box of `data-tour-anchor="..."` attributes on the live components.
3. Steps where a modal is shown (1 = welcome, 4 = phases explainer, 8 = closing) — the modal renders over a darkened mask of the same live page underneath, not over a redrawn shell.

Specifications must therefore add `data-tour-anchor` attributes to the existing components (run-row, run-detail header, phase rail, critique pane, consumption row), not refactor the tour to know component internals.

The phases-explainer modal (step 4) uses the canonical phases-overview diagram shipped in `assets/Design System v2.html#tour-4` — render the SVG inline as documented.

---

## 9 · Deep dive — How It Works + Changelog (top-bar button)

The dashboard's top bar carries a **"How It Works"** button. Clicking it opens a full-screen overlay (M3 dialog with shape-xl corners, max-width 1080 dp, surface-3 background).

Inside that overlay:

- **Left:** the long-form content area (the nine sections documented at `#how` in the design system). Body uses Roboto Flex at 16/24. Section heads use Roboto Serif at the headline-large role.
- **Right:** a sticky right-side menu, ~240 dp wide, with two top-level entries:
  - **How It Works** (default open) — expands to list the 9 sub-sections (`Protocol overview` · `Preflight` · `Independent research` · `Plan negotiation` · `Drafting` · `Review loop` · `Disagreement & convergence` · `Cost & consumption` · `Version notes`).
  - **Changelog** — opens the full changelog as documented at `#changelog`.

**Reduce overwhelm:** every long sub-section inside How It Works is **collapsible** by default. Heroes and diagrams stay visible; multi-paragraph prose collapses to a single sentence with a `Read more` chevron. The Changelog list collapses past entries — only the most recent is open by default.

Both themes (dark + light) must render correctly.

Removing today's behaviour where the top-bar back button is misplaced is part of issue 17.

---

## 10 · Themes — dark + light

The token layer is theme-agnostic. Light mode flips a body class, every component re-resolves. Specifications should:

- Never hard-code a colour in component CSS — read from `--md-*` role tokens.
- Test both themes after implementation. Acceptance bar: every component looks correct on dark and light without per-theme CSS overrides.
- The light-mode preview at `#light` is the comparison reference.

---

## 11 · Validation checklist before you hand back the plan

Before posting the spec plan to the product owner, validate it answers all of these. Tick each one explicitly:

- [ ] Every one of the **17 Notion issues** is referenced in at least one spec.
- [ ] Every issue that touches the same component is **grouped into one spec** (or explicitly sequenced together).
- [ ] The **token layer spec** (or equivalent foundation work) is **first** in the sequence — nothing depends on tokens that haven't shipped.
- [ ] **Primitives** (buttons, chips, status pills, cards, badges, M3 atoms) ship before **composed components** (consumption, critique, thread, timeline).
- [ ] Composed components ship before **page-level features** (How It Works overlay, onboarding overlay).
- [ ] **No spec proposes backend changes.** If a frontend change needs new backend data, the spec explicitly says "render what the backend exposes and degrade gracefully."
- [ ] Every spec **lists the design-system anchor(s)** it references (`#critique`, `#consumption`, etc.).
- [ ] Every spec specifies **both dark + light** in scope.
- [ ] The onboarding tour spec is scoped as **overlay-only** (no redraw of the underlying app).
- [ ] The How-It-Works spec specifies the **right-side menu with How It Works ↔ Changelog toggle** + collapsible sub-sections.
- [ ] The consumption specs cover **collapsed + unfolded + uniform-across-phases + sticky legend**, all four together.
- [ ] Each spec has rough estimated complexity (S / M / L) so the product owner can sequence delivery.
- [ ] The final number — *"N specifications"* — is at the top of your response.

---

## 12 · Where to find every asset

| Asset | Path |
|---|---|
| Briefing (this file) | `pr/README.md` |
| Design system v2 (canonical, open in browser) | `pr/assets/Design System v2.html` |
| M3 token + primitive CSS | `pr/assets/styles/v2-m3.css` |
| Page-level component CSS | `pr/assets/styles/v2-m3-page.css` |
| All 17 Notion issues (verbatim above + screenshots) | `pr/README.md#5--stream-b--17-known-issues-from-notion-verbatim` and https://www.notion.so/Known-issues-36499f3e507f80b0b5b6ccadbd0a900b |

---

## Final reminder before you start

> You're not implementing anything in this round. Your deliverable is the spec plan. Post it back to the product owner. They'll then either approve the slicing as-is or push back on individual specs before any of them are picked up for implementation.

Good luck.
