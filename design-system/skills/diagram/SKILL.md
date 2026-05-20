---
name: diagram
version: 2.0.0
description: Produces polished SVG diagrams in two parallel design systems — **Pixel** (cream + indigo, the default) and **Material** (Material 3, sable + sage). Every diagram emits a light + dark SVG pair under the requested mode, self-contained and host-portable to Notion, GitHub, Slack, PDF. Nine templates cover system context, layered architecture, pipeline/flow, sequence, data schema (ER), infrastructure/deployment, event-driven flow, connector/integration map, plus a freeform catch-all. The skill first restates the user's input, classifies the dominant structure, normalises into the canonical template spec, then renders. Use any time the user wants to visualise, diagram, or chart a system — "draw this", "show me X as a diagram", "create a chart for this", "visualise this architecture / data model / flow / topology", or "give me a Material dark version of this". Do NOT use for: prose explanations without a visual deliverable, mermaid-style text diagrams, hand-drawn aesthetic.
---

# Diagram skill

You produce a pair of self-contained SVG files (light + dark variant of one diagram) matching a locked visual style. The skill ships **two design systems** — pick one per request:

- **Pixel** (`pixel`) — cream + indigo on a polished document page. The default mode. Hand-tuned, general-purpose, subject-agnostic. 78-icon custom library.
- **Material** (`material`) — Material 3 design language: sable + sage palette, Roboto Flex + Roboto Serif type, M3 surfaces / shape / motion, Material Symbols Outlined icons. The Material reference pages consume an internal V2 design system (vendored at `references/app-v2/`) as their source of truth — when V2 evolves, Material inherits. Use when the diagram should share visual DNA with an M3 product surface.

Each mode has its own reference bundle and its own 18 canonical example SVGs:

- `references/pixel/` → foundations / components / connectors / icons / templates / examples + 18 canonical SVGs
- `references/material/` → same structure, Material vocabulary

Mode-agnostic content (template input contracts, manifest schema, troubleshooting, README) lives at `references/` root and is shared by both modes.

The SVGs in `references/<mode>/examples/` are the canon for that mode — they define the style. Each diagram exists as a pair: `<name>.<mode>.light.svg` + `<name>.<mode>.dark.svg`. Read both when generating. This skill is a thin contract that keeps every diagram visually coherent with them.

## What this produces

- **Two `.svg` files** — `<slug>.<mode>.light.svg` + `<slug>.<mode>.dark.svg`, no external assets — all gradients, filters, markers, motion paths, and `@keyframes` inlined in `<defs>`.
- `<mode>` is **`pixel`** (default) or **`material`**. The mode is part of the filename so the design system is self-documenting.
- Locked viewBox width of **1660**; height chosen to fit content with ~40px breathing room top and bottom. Same height across the pair.
- **Same diagram, two backgrounds:** identical layout, identical arrow routes, identical icon choices and labels. Only canvas, surface stops, inks, shadows, and connector stroke colors swap between the light and dark variants of one mode.

### Mode at a glance

| Mode | Light canvas | Dark canvas | Accent | Type |
|---|---|---|---|---|
| **Pixel** (default) | `#f5f1ea → #ece8e0` cream | `#1a1a1f → #14141a` near-black | indigo `#4f5fb8` / `#7785d4` | Inter |
| **Material** | `#faf9f6 → #ece8de` warm M3 light | `#0d0f12 → #08090b` M3 dark canvas | info-blue `#6b9cf0` (`--md-tertiary`) | Roboto Flex (plain) + Roboto Serif (brand) |

---

## Workflow

Seven steps. Steps 1, 2, and 4 are the ones that prevent the inconsistency this skill used to suffer from. Step 6 (self-review via screenshot) catches the routing/alignment failures that look fine in source but bad in render. Don't skip them.

### Step 1 — Understand and restate (THE CONTENT GATE)

Before reading any template, before any SVG, before anything visual: read the user's input fully and restate what you understood. This step exists because the most common failure mode is the model jumping to SVG with a half-correct interpretation of what the user described.

Do this:

1. **Read everything the user provided.** Prose, pasted docs, code, prior diagrams. Don't skim.
2. **Detect the requested mode + theme.** Look for explicit phrasing in the request:
   - `"pixel light"` / `"pixel dark"` / `"pixel both"` → mode `pixel`
   - `"material light"` / `"material dark"` / `"material both"` → mode `material`
   - `"both"` with no mode word → mode defaults to `pixel`, both themes
   - **No mode word at all** → mode defaults to **`pixel`** (preserves the original skill's behavior); theme defaults to `both`
   - **If a manifest is active for a multi-diagram set**, the manifest's `mode:` and `theme:` pins are authoritative — a request that contradicts them is a hard error (do not override per-diagram).
3. **Identify the dominant structure.** Pick exactly one:
   - **Static structure** — components and how they relate; no time component
   - **Time-ordered flow** — order matters (sequence of operations, lifecycle)
   - **Data model** — entities with typed fields and relationships
   - **Topology** — physical or cloud deployment layout
   - **Integration surface** — what talks to what at a system boundary
   - **Mixed / multi-view** — composite views or full-project landscapes
4. **Restate to the user in 3–5 lines.** Keep it tight:
   - "Here's what I understood: [system X, doing Y, with these N parts/stages/entities]."
   - "Dominant structure: [classification]."
   - "Mode: [pixel | material] · theme: [light | dark | both]."
   - "I'm going to build a [template name] diagram. Tell me if that's wrong before I start."
5. **Wait for correction only if the input was ambiguous.** If the input was clear, restate and proceed in the same response. The restatement is a checkpoint, not a blocker.

This is the cheapest place to catch a misread. A user can redirect with one sentence; regenerating a diagram costs much more.

### Step 2 — Classify and pick a template

Map your structure classification (from Step 1) to a template:

| Classification | Template |
|---|---|
| Static structure (layers, internal components) | `layered-architecture` |
| Static structure (hub + spokes / integrations) | `connector-map` |
| Time-ordered flow (numbered stages, pipeline) | `pipeline-flow` |
| Time-ordered flow (messages between actors) | `sequence` |
| Data model | `data-schema` |
| Topology (cloud, regions, compute/storage) | `infrastructure` |
| Integration surface (boundary view, C4-L1) | `system-context` |
| Event-driven topology (producer / topic / consumer) | `event-flow` |
| Mixed / multi-view / full landscape | `freeform` |

**For architectural proposals** when the user asks for "all the diagrams for a new application", generate in this order:
1. `system-context` — scope and stakeholders
2. `layered-architecture` — internal component layers
3. `sequence` — key request/event flows
4. `data-schema` — data model
5. `infrastructure` — deployment topology
6. `event-flow` — async event topology (if applicable)

**Fall back to `freeform` whenever:**
- The input genuinely mixes structures (e.g. "show the context AND the data model in one diagram").
- The user wants a full-project landscape diagram with multiple regions.
- No single template's input contract cleanly matches the input shape.

Don't force-fit a template that doesn't match. Force-fitting is where most visible inconsistency comes from. `freeform` is a real fallback — use it.

If the choice is genuinely ambiguous (could reasonably be two templates), ask once: "I can show this as a sequence diagram (focused on the order of operations) or a layered-architecture (focused on the static structure). Which fits your audience better?"

### Step 3 — Load context

The visual spec is split across mode-specific HTML pages (the design system, components, icons, connectors) plus mode-shared content (template input contracts, manifest schema). **Route by mode**: read from `references/<mode>/...` where `<mode>` is the one detected in Step 1 (defaults to `pixel`). Read in this order. Don't skip files — each one constrains the output.

1. **`references/<mode>/foundations.html`** — the locked design tokens for the active mode.
   - **§01.0 "Theme model"** — the dual-theme architecture: every theme-dependent token has both a light name and a dark sibling. Gradient and filter *ids* stay stable across themes — only their bodies (stop values, flood-color, opacity) differ between the two output files.
   - **§01.1 Canvas** — viewBox 1660, canvas gradients, margins.
   - **§01.2 Color palette** — mode-specific accent identity, categorical surfaces (light + dark stops), ink scale, status colors.
   - **§01.3 Typography** — sizes/weights/spacing theme-agnostic; only colors swap. Font family is mode-specific (Pixel: Inter · Material: Roboto Flex + Roboto Serif).
   - **§01.4 Spacing** — spacing tokens, theme-agnostic.
   - **§01.5 Shadows** — shadow filter registry. Light cards on dark and dark cards on dark have different recipes.
   - **§01.6 Animations** — keyframes theme-portable.
   - **§01.7 Cross-template consistency** — theme is pinned per set; mode is pinned per set.
2. **`references/<mode>/components.html`** — the closed component library: card variants, chip types, node shapes, stages, lanes, groups, callouts. Every structural element in the diagram is a named primitive from here. Read the **"Dark variant"** note in each section.
3. **`references/<mode>/connectors.html`** — the connector geometry system: arrow taxonomy, marker registry, curve rules (`--bend-radius`, `--max-bend-angle`), lane/gutter system, label placement zones A/B/C (**no rotated labels, ever**), crossing rules, clearance, density caps. Geometry is theme-agnostic; arrow strokes + marker fills swap per theme.
4. **`references/<mode>/icons.html`** — only for `infrastructure`, `system-context`, `connector-map`, or `freeform`. Icons documented as a **2×2 matrix**: (variant: on-light-card / on-dark-card) × (theme: light / dark). When no icon matches, use the mode's `icon.generic-service` monogram fallback — never invent a bespoke shape.
5. **`references/<mode>/templates.html`** — the visual contract for the chosen template under the active mode. Each template has a "Dark variant" note.
6. **`references/templates/<name>.md`** — the chosen template's **input contract** and **worked example** (prose → canonical spec). **Mode-agnostic and theme-agnostic** — lives at `references/` root, shared by both modes.
7. **`references/<mode>/examples/<name>.<mode>.light.svg` AND `<name>.<mode>.dark.svg`** — the canonical visual anchors for both themes of the active mode. Open both when generating; they share layout and differ only in theme tokens.
8. **`references/manifest.html`** and any existing `diagram-set-manifest.yaml` — only if this is the second-or-later diagram in a multi-diagram set. The manifest carries a `mode:` field (`pixel` / `material`, default `pixel`) and a `theme:` field (`light` / `dark` / `both`, default `both`). Both are authoritative per-set; per-diagram override is a hard error.

### Step 4 — Normalize input into the canonical spec (THE INTERPRETATION GATE)

Every template has an **Input contract** section. It defines the shape of structured data the layout pass consumes. Your job in this step is to translate the user's prose into that shape — *explicitly, in writing*, before any SVG generation.

**Translate without loss.** Every component, stage, entity, or actor the user named must land somewhere in the canonical spec; every element in the spec must land somewhere in the SVG. Compression is allowed — collapsing five sub-steps into a single stage with a list footer is fine. Silent omission is not — if something can't fit the chosen template, fall back to `freeform` or split into multiple diagrams. This is the same discipline `design-doc` applies to prose; the visual analog is just as load-bearing.

This is the second gate that prevents inconsistency. Without an explicit normalization, the model jumps from messy prose to pixels and the result drifts.

Do this:

1. Open the chosen template's Input contract section.
2. For each field the contract asks for, extract or infer the value from the user's input.
3. Write the canonical spec out (in your reasoning, not necessarily to the user). It must be complete — every required field filled.
4. If a required field is missing from the input, ask one focused question. Don't make up content; don't draw with placeholders.
5. If the input is rich enough that you have *more* detail than the spec accommodates, trim — the spec is the contract, and the diagram should fit the spec, not the prose.

**Worked example** (for `pipeline-flow`):

> User said: "We ingest documents, validate them, run them through a classifier, then store them in Postgres."
>
> Canonical spec:
> ```
> title: Document Ingestion Pipeline
> subtitle: PDF/DOCX/MD in, classified records out
> stages:
>   - 1. Ingest        — input: PDF/DOCX/MD files
>   - 2. Validate      — schema + size checks
>   - 3. Classify      — ML classifier; outputs (category, confidence)
>   - 4. Store         — Postgres; indexed by classification
> connectors: solid-primary between sequential stages
> animations: motion dots on the 1→2→3→4 path (one animation class only)
> ```

This intermediate spec is the contract between "what the user said" and "what the SVG looks like." Without it, the model improvises and inconsistency follows.

### Step 5 — Generate in three passes

Polish is too high for one-shot. Generate the SVG in three passes within the same response. You don't have to emit three intermediate files — the passes are a thinking discipline. **The layout is generated once; the theme is applied twice.**

- **Pass 1 — Skeleton.** Background, title, all cards in their layers/stages with labels. Get the layout right before anything else. Validate spacing tokens: card-to-card breathing room, canvas margins, group padding. Reference token *names*, not literal colors yet.
- **Pass 2 — Connections.** Arrows, paths, connection labels. Check that no arrow crosses a card edge with less than the design system's clearance value. Check that no two labels collide. **For each orthogonal arrow, apply the empty-space test (`connectors.html` §04.3b.1): does any horizontal segment thread through or graze a card it doesn't terminate at? If yes, re-route via above-row or below-row zone.**
- **Pass 3 — Animations + status.** Ring rotations, pulse dots, motion-path dots, terminal carets — whichever serve the meaning. Cap at 3 animation classes per diagram (more = noise).
- **Theme pass — apply each token set from the active mode.** Now that layout / connections / animations are static, render the SVG twice using the **mode's** token set from `references/<mode>/foundations.html`. The two files share `id`s and structure; only the *values* inside `<defs>` and the literal color attributes differ between the light + dark output of one mode. If during this pass you discover something doesn't work in one theme — the fix is in that mode's `foundations.html`, not a one-off override in the output. Otherwise the two variants drift over time.
  - **Pixel:** light canvas `#f5f1ea → #ece8e0`, indigo `#4f5fb8`, ink `#1a1a18`, 7 categorical surfaces at light stops; dark canvas `#1a1a1f → #14141a`, indigo `#7785d4`, ink `#ebebe5`, lifted categorical surfaces.
  - **Material:** light canvas `#faf9f6 → #ece8de`, info accent `#6b9cf0`, M3 ink ladder via `--md-on-surface-*`; dark canvas `#0d0f12 → #08090b`, same accent, dark M3 ink ladder. Categorical surfaces derived from V2 palette tokens via `color-mix` — see `references/material/foundations.html` §01.2.

The passes prevent the model from burning attention on animation details while the layout is still wrong.

### Step 6 — Render and self-review

Before treating the SVG as final, render both variants to PNG and look at them. The mental model of "where the arrows go" diverges from the rendered reality more often than you'd expect — especially for orthogonal routes through dense regions where a 10px miscalculation puts a label on top of a card edge. With dual output, you render twice and check twice.

**Render commands** (macOS, Chrome headless). Substitute `<mode>` for `pixel` or `material`:

```bash
# Light render
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars \
  --window-size=1660,<svg_height> \
  --screenshot=/tmp/diagram-review-light.png \
  "file:///absolute/path/to/diagram.<mode>.light.svg"

# Dark render — SAME svg_height, different file
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars \
  --window-size=1660,<svg_height> \
  --screenshot=/tmp/diagram-review-dark.png \
  "file:///absolute/path/to/diagram.<mode>.dark.svg"
```

Substitute the SVG's viewBox height for `<svg_height>` so each screenshot matches its native dimensions. Then read **both** PNGs.

**Apply these checks to each independently:**

1. **Arrow routing.** Does any horizontal segment slip along the edge of a card it doesn't terminate at? (Empty-space test, §04.3b.1.) If yes, re-route through a clean zone.
2. **Label clearance.** Are any two labels within `--label-clearance × 2` (24px) of each other? Are labels colliding with arrow lines?
3. **Icon alignment.** Do all icons in same-rank cards share the same baseline? Misalignment usually means a freehand transform without a slot rect (`components.html` §02.1).
4. **Same-rank height locking.** Cards in the same row should match height. If a 220px card sits beside a 180px card, the row reads ragged.
5. **Title/subtitle position.** Is the title visually centered? Subtitle one line below at consistent offset?
6. **Anything that looks "off" even if you can't name it.** Pixel-level layout problems are easier to spot in the rendered image than in the SVG source.

**Additional checks specific to the dark variant:**

7. **Light-canvas leakage.** Any region where the mode's *light* canvas bleeds through the dark render (Pixel: `#f5f1ea` stops · Material: `#faf9f6 / #ece8de` stops). Usually a `<rect>` or icon with a hardcoded light fill that didn't get swapped.
8. **Invisible elevation.** Cards reading flush with the canvas because drop shadows aren't visible on dark. If you see this, the mode's foundations elevation strategy is wrong, not the diagram — reach for the dark-theme rule-stroke replacement (light cards) or boost the dark-card shadow opacity per the mode's §01.5.
9. **Accent legibility.** Primary arrow / accent color must read clearly against the dark canvas. If muddy, you're using the wrong theme's accent token (Pixel light `#4f5fb8` vs dark `#7785d4`; Material accent `#6b9cf0` is theme-portable but may need its dark-mode container variant).
10. **Text contrast.** Every ink role must be legible against its own surface (not against the canvas). Mental WCAG AA check (4.5:1 body, 3:1 large).
11. **Light/dark layout parity.** The two PNGs must look like the *same diagram on different backgrounds*. If shapes have shifted, sizes have changed, or arrows route differently, the theme pass leaked into the layout pass. Fix that — they share layout by construction.

**If you spot a problem:** go back to Pass 1/2/3 in Step 5, fix the source, re-render BOTH variants, re-review both. Iterate until both rendered images are clean. Two iterations is normal for complex diagrams; four is a signal the layout needs a structural rethink, not more tweaks. **Count iterations against the worse variant** — if light passes on pass 1 but dark still has a contrast issue on pass 3, you're on iteration 3, not iteration 1.

**If one variant passes and the other fails**, the foundations tokens are wrong, not the diagram. Update tokens; regenerate both. Never apply a one-off override to the failing variant only.

This self-review step is mandatory for diagrams with 4+ arrows or any orthogonal routing. Single-template diagrams with simple straight arrows can skip a re-render, but **the dual output is never optional** — emit both files regardless.

### Step 7 — Output

Output TWO SVG files — `<slug>.<mode>.light.svg` and `<slug>.<mode>.dark.svg`. Each starts with `<?xml version="1.0" encoding="UTF-8"?>` and ends with `</svg>`. Each is self-contained. No prose around them. **Mode is part of the filename** — Pixel diagrams write to `.pixel.{light,dark}.svg`; Material diagrams write to `.material.{light,dark}.svg`. The mode-in-filename rule lets two design-system versions of the same diagram coexist in one folder without collision.

The Notion user pastes the file matching their host theme (or both, with the host switching). GitHub/Slack/PDF consumers each have known preferences (GitHub: viewer-theme-honoring embeds work; Slack: paste both; PDF: light only — see `troubleshooting.md`).

**Destination convention.** Save the pair to `diagrams/<slug>.<mode>.{light,dark}.svg` adjacent to the document that references the diagram (this is the convention every repo using this skill follows). If no anchoring document exists, ask the user where to save before writing — don't drop files at an arbitrary path.

Mention BOTH filenames in the response so the user knows what to pick up. Example:

> Generated `diagrams/partner-vetting-context.pixel.light.svg` and `diagrams/partner-vetting-context.pixel.dark.svg`. Paste the one matching your Notion theme — or both for hosts that respect viewer preference.

If this diagram is part of a multi-diagram set and you wrote or updated the manifest in Step 3, mention that briefly after the SVG (one line: "Manifest updated with [new entity → gradient assignments]").

---

## Multi-diagram proposals

When generating 2+ diagrams for the same proposal, use a manifest to lock cross-diagram consistency. The manifest is a small YAML file (`diagram-set-manifest.yaml`) authored on the first diagram of a set and read by every later diagram. It pins:

- **`mode:`** the design system for the whole set — `pixel` (default) or `material`. Pinned per-set; a per-diagram override is a hard error. A proposal is a coherent reader experience and mixing design systems within one set is a design failure.
- **`theme:`** the theme(s) for the whole set — `light` / `dark` / `both` (default `both`). Same per-set pin rule.
- Each named entity → its surface gradient (e.g. `Vetting API → surfacePrimary`)
- Each named entity → its icon (e.g. `Postgres → icon.sql`)
- The exact label spelling for each entity (`Postgres`, not `Postgres DB` or `PG`)
- The viewBox width if the wide variant (2200) is in use
- The running tally of animation classes used across the set (against the 3-per-diagram cap)
- Third-party long tail: monogram + tile color per integration

Read `references/manifest.html` for the format, schema, and worked example. On the first diagram, *write* the manifest as you make assignments. On every subsequent diagram, *read* the manifest first and use the pinned assignments verbatim — including `mode:` and `theme:`.

If the user is generating ad-hoc diagrams not part of a coherent set, skip the manifest.

---

## Output rules

These come from the design contract — they apply to every diagram pair, both modes.

1. **A pair of single-file SVGs**, no external assets. All gradients, filters, markers, motion paths, and keyframes inline in `<defs>`. Both files contain the same structural content; only color values, shadow filter bodies, and canvas gradient stops differ.
2. **Filenames include the mode** — `<slug>.<mode>.{light,dark}.svg`. Pixel pair: `<slug>.pixel.light.svg` + `<slug>.pixel.dark.svg`. Material pair: `<slug>.material.light.svg` + `<slug>.material.dark.svg`. Never write a pair without the mode segment.
3. **Semantic IDs** from the active mode's foundations registry — `surfacePrimary`, `surfaceSql`, `cardShadow`, `arrowPrimary` (and Material equivalents). **The same id in both theme files of one mode** — the stop values inside differ. Never `gradient1`, `filter0`.
4. **XML comment dividers** between major sections of the SVG (foundations / surfaces / markers / animations / content):
   ```xml
   <!-- ================= SHADOWS ================= -->
   <!-- ================= GRADIENTS ================= -->
   <!-- ════════════════════════════════ TITLE ════════════════════════════════════ -->
   ```
5. **viewBox 1660 × height** (or the wide variant `2200` only for explicit landscape three-column overviews per the mode's `foundations.html` §01.1). Pick height to fit content with ~40px top/bottom breathing room. If content cannot fit, split into multiple diagrams or fall back to `freeform` — never silently widen past the canonical widths.
6. **Group by layer / stage / lane** with a leading section label (`AGENT LAYER`, `STAGE 2`).
7. **Letter-spacing on caps labels** — 1.5–2 on ALL-CAPS section markers, 0.5–1 on connection labels (Pixel); Material uses the M3 label-s utility's 0.5 track with the diagram-specific 1.6/0.8 overrides documented in `references/material/foundations.html` §01.3.
8. **Drop shadows from the mode's registry** — `cardShadow` / `cardShadowDark` filters present in both modes; bodies differ per mode and per theme. Don't invent new shadow params.
9. **Animations from the mode's registry** — keyframes and classes defined in `references/<mode>/foundations.html` §01.6. Max 3 animation classes per diagram (calm aesthetic). Don't invent new keyframes.
10. **Every card, chip, lane, stage, group, callout is a named primitive** from the mode's `components.html`. Slot positions are locked (icon slot top-left, status slot top-right, footer slot bottom). Don't invent.
11. **Every arrow obeys the connector contract** from the mode's `connectors.html`: a taxonomy type, a curve mode (L · Q · C · **O for dense regions and state machines**), a label in zone A/B/C (never rotated), **anchored source and target cards** (no orphan arrows starting or ending in gutters), parallel arrows respect `--lane-gutter`, crossings follow jog priority, density caps enforced.
12. **Every icon is from the mode's `icons.html` or the mode's `icon.generic-service` monogram fallback.** Never a bespoke shape.

---

## Quality bar

The result must feel like it belongs in a polished design document — not a whiteboard sketch and not a Lucidchart export. Signs it's wrong:

- Icons crashing through card titles (cards need an explicit icon slot)
- **Icons hand-positioned via `<g transform>` without a slot rect behind them** — they drift, each card's icon ends up at a slightly different baseline (see `components.html` §02.1 icon-placement callout for the canonical two-step pattern)
- Cards crammed up against canvas edges
- Inconsistent font sizing across same-rank elements
- Connection labels rotated 90° vertically (forbidden — route around if there's no room)
- Connection labels that overlap connection lines or other labels
- Animations everywhere (too busy)
- Bare arrows with no labels
- **Orphan arrows: arrows that start in a gutter or end in empty space** — every arrow must originate at one card edge and terminate at another card edge (`connectors.html` §04.5d)
- **Spaghetti curves through dense regions** — when 3+ arrows share a gutter band, switch to orthogonal routing (`connectors.html` §04.3a), not long sweeping C-curves that collide with each other's labels
- Floating ALL-CAPS labels with no clear anchor to a connector or region
- Same-rank cards with inconsistent heights (rows must height-lock to the tallest card)
- A legend with 2 items (rarely needed — add only when 4+ semantic colors are used and aren't self-evident)

If the first generation looks off, iterate. Move cards, re-pick the template, add breathing room. If the diagram needs more horizontal space than viewBox 1660 allows, that's a signal to split or fall back to `freeform`, not to widen silently.

---

## Current state, not history

Diagrams represent **how the system works now**, not how it was designed or evolved over time.

- **Only draw arrows that represent actual runtime data flow or control flow** in a single invocation. No arrows for iterative improvements, version history, or development lineage.
- **Internal loops** (e.g. "rounds 1–N inside Phase 2") belong inside the card for that phase. Show them as sub-structure, not as cross-phase back-arrows.
- **If the user describes how the system was built** (e.g. "we improved this in v2"), capture that as explanatory prose in the footer, not as a loop arrow in the flow.
- **Cross-phase feedback arrows** must correspond to something the orchestrator actually does during a run. If no such mechanism exists in the code, the arrow is misleading and must be omitted.

---

## Performance notes

Diagrams ship into stakeholder-facing proposal documents. Quality matters more than speed. When generating, you must NOT:

- **Skip Step 1 (the content gate).** Restate the input before drawing. Every time. Even when it feels obvious.
- **Skip Step 4 (the interpretation gate).** Write the canonical spec before generating SVG. Without it the model improvises and drifts.
- **Generate the SVG in one pass.** Use the four-pass discipline: skeleton → connections → animations → theme. Layout first, polish next, theme application last.
- **Emit only one theme variant.** Always emit both `<slug>.<mode>.light.svg` and `<slug>.<mode>.dark.svg`. Emitting only one is incomplete delivery — unless the manifest pins `theme: light` or `theme: dark` explicitly.
- **Apply one-off color overrides to a single variant.** If the dark version has a contrast bug, fix the mode's foundations token, not the rendered SVG. Otherwise the two variants drift.
- **Invent new gradients, shadows, animations, components, or icons.** Use the registries in `references/<mode>/foundations.html`, `references/<mode>/components.html`, `references/<mode>/icons.html`, `references/<mode>/connectors.html`. If you need something not in them, fall back to `freeform`, use the mode's `icon.generic-service` monogram fallback, or ask the user — don't improvise.
- **Cross modes mid-set.** If a manifest pins `mode: pixel`, do not render `material` for any diagram in the set, even if the user asks. The skill must surface the conflict, not silently honor the request.
- **Widen viewBox beyond 1660 to fit content.** Split into multiple diagrams or use `freeform` with a multi-column layout strategy.
- **Rotate connector labels 90°.** If a horizontal label doesn't fit, the line jogs to make room — or the label moves to a callout chip.

Take the time. A diagram that lands right on the first try saves more than it costs.

If something goes wrong, read `references/troubleshooting.md` — common failure modes and recovery procedures.

---

## What goes outside this skill's scope

- Static-only export (no animations) for PDF — not yet supported. If asked, generate the animated version and tell the user the animations will appear as static in PDF export.
- Gantt charts, mind maps, traditional swimlane diagrams — not templated. Decline politely or suggest the closest template.
- Hand-drawn / sketchy aesthetic — not this skill. This is a polished-document aesthetic.
- UML class diagrams with formal notation — use `data-schema.md` as the closest alternative.
- Network packet-level diagrams (OSI layers, TCP/IP) — use `infrastructure.md` for the topology; label connections with protocols.
