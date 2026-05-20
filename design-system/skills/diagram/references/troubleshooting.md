# Troubleshooting

Common failure modes and how to recover. Read this when a diagram came out wrong, or when the skill behaved oddly. Add new entries as patterns emerge.

> **Mode awareness.** Most entries here apply to **both** the Pixel and Material modes — the workflow gates (Step 1 restatement, Step 4 spec, etc.) and the structural rules (orphan arrows, label rotation, density caps) are mode-agnostic. The five **dark-theme** entries (cream leakage, invisible elevation, indigo legibility, light/dark drift, PDF export) reference Pixel-specific token names (`#f5f1ea`, `--indigo` `#4f5fb8`, etc.) and apply directly to Pixel. The equivalent Material failure modes follow the same shape — the fix is in `references/material/foundations.html` rather than `references/pixel/foundations.html`. Cross-mode entries (mixing modes within a proposal, wrong mode for the diagram's purpose) sit at the bottom of this file.

---

## The diagram doesn't match what the user described

**Symptom:** Generated diagram represents a different structure than the user intended, or omits key elements they mentioned.

**Cause:** Step 1 ("Understand and restate") was skipped or done too briefly. The model jumped to drawing with an incomplete or wrong interpretation of the input.

**Fix:** Re-do Step 1. Read the input again, fully. Restate explicitly in 3–5 lines: what's the dominant structure, what are the entities, what's the natural reading direction. Pick the template only after the restatement is solid. If the input is genuinely ambiguous, ask one focused question before drawing — that's cheaper than regenerating the whole SVG.

---

## The diagram is visually inconsistent — drifted from the design system

**Symptom:** Wrong gradients, wrong card styles, fonts at the wrong sizes, animations that aren't in the registry.

**Cause:** Step 3 ("Load context") was rushed — `foundations.html` or `components.html` wasn't read fully — or the model improvised because no primitive matched what it needed.

**Fix:** Re-read `references/foundations.html` (tokens) and `references/components.html` (primitives). Use only named surface gradients, named card variants, named shadows, registered animations. If you genuinely need something not in the system, that's a signal to fall back to `freeform`, not to invent.

---

## Icons collide with card titles

**Symptom:** Icons rendered on top of card title text, partly overlapping.

**Cause:** Card primitive wasn't used — geometry was hand-rolled.

**Fix:** Use the named card variants from `references/components.html`. Each card has a reserved icon slot at top-left (36×36 with 20/20 inset). Don't place icons outside the slot. If a card doesn't need an icon, omit the slot entirely — don't fill the slot with a decoration.

---

## Icons drift / sit at different baselines across cards

**Symptom:** Icons in a row of same-rank cards all look slightly misaligned — one is higher, one is lower, one is offset to the right. The titles look fine but the icons feel "off."

**Cause:** Each icon was placed via a freehand `<g transform="translate(X, Y)">` with hand-computed coordinates, without a slot rect to anchor it. Even small per-card math errors compound into visible drift across a row.

**Fix:** Always use the **two-step icon pattern** from `components.html` §02.1:
1. Draw the 36×36 slot rect at `(card.x + 20, card.y + 20)` first. The slot is the load-bearing geometry — it locks the icon's anchor.
2. Wrap the icon ART in `<g transform="translate(card.x+38, card.y+38)">` (the slot center) and draw all shape coordinates relative to `(0, 0)`.

Never skip step 1. The slot rect is what guarantees consistent baselines across cards.

---

## Orphan arrows — arrows that float between cards

**Symptom:** An arrow starts in the gutter between two cards (with no clear source) or ends in empty space. The reader can't tell what the arrow is connecting.

**Cause:** The arrow was drawn to span a region (e.g. "the gap between bounded contexts") rather than to connect two specific cards. This happens when the author tries to show "this region writes to that region" but doesn't bind the arrow to the actual sender or receiver card.

**Fix:** Apply `connectors.html` §04.5d (Arrow Anchoring):
- Every arrow's `M x y` must start at a defined card edge (with `--arrow-stub` 8 inset).
- Every arrow's marker-end must land at another defined card edge.
- If you can't identify a specific source card or target card, the arrow is wrong — either pick one, or delete the arrow.

If you genuinely need to show a region-level flow ("Profile & Consent writes envelopes" not "Profile aggregate writes envelopes"), make the region a group card with a real boundary, and anchor the arrow to that group boundary.

---

## State machine curves collide / labels overlap

**Symptom:** In a state machine or dense flow diagram, multiple curved arrows between the same hub state and surrounding states sweep through each other's label zones. Labels get stacked vertically, or two labels overlap, or a label sits on top of a line.

**Cause:** Long C-curves were used everywhere. Curves don't have predictable label-anchor surfaces — labels float at the midpoint, which for adjacent curves means the same screen region.

**Fix:** Switch to orthogonal routing (`connectors.html` §04.3a). Each arrow becomes a sequence of straight horizontal and vertical segments joined by small (`--corner-radius` 10) arcs. Labels go on the horizontal segments, which gives each label a predictable, non-colliding anchor surface. The state-machine return-loop pattern (two parallel orthogonal lanes between the same pair of cards, forward on top lane, return on bottom) is the canonical fix for hub-and-spoke state machines.

---

## Arrows overlap or labels are rotated 90°

**Symptom:** Multiple arrows crossing badly; connector labels rotated vertically; labels colliding with lines or with each other.

**Cause:** Connector contract wasn't applied — routing, label zones, or density rules ignored.

**Fix:** Reload `references/connectors.html` and apply the contract:
- Labels go in zone A (above-line caps), B (below-line italic), or C (on-line pill). **No rotation, ever.** If a label can't fit horizontally, the line jogs or the label becomes a `chip.label` on the source card.
- `--arrow-clearance` is 16px from any unrelated card; `--arrow-stub` is 8px from the connected card edge.
- `--lane-gutter` is 16px between parallel arrows. If more than 3 arrows run parallel between the same pair, collapse into a single trunk with a `chip.count`.
- Maximum 3 crossings per diagram. Shorter / secondary arrow jogs over longer / primary; jog arc 6px.
- Maximum 6 arrows per card.

---

## Two diagrams in the same proposal look inconsistent

**Symptom:** Same service rendered with different gradient, icon, or label spelling across two diagrams in one set.

**Cause:** Either the diagram-set manifest wasn't created, or it wasn't read before the second diagram.

**Fix:** See `references/manifest.html`. Create `diagram-set-manifest.yaml` when starting a multi-diagram proposal. Read it before *every* subsequent diagram in the set. Apply pinned assignments verbatim — including label spelling.

---

## ViewBox content overflows / diagram feels cramped

**Symptom:** Cards crammed against edges, labels colliding because there's no room, or the model silently widened viewBox past 1660.

**Cause:** Tried to fit too much into one diagram.

**Fix:** Do NOT widen viewBox. Two options:
1. Split into two diagrams (e.g. "Research → Dev" and "Dev → Application" as separate landscape views).
2. Use `freeform` with one of its multi-column strategies (B or C), which are explicitly designed to fit within viewBox 1660.

---

## SVG renders broken or doesn't animate in Notion

**Symptom:** Notion shows a broken SVG, or animations don't play, or the SVG looks fine in a browser but wrong in Notion.

**Cause:** Notion's SVG renderer has quirks. Some features that work in browsers don't work in Notion's preview.

**Fix:** Test in a browser first (drag the SVG file into a blank tab). If it renders correctly there, it's a Notion limitation, not a skill bug. Common Notion quirks: `<animateMotion>` with `<mpath>` references can be unreliable; complex `<style>` blocks sometimes get stripped. If Notion is the target and an animation fails, drop the animation rather than fight it. The diagram should still read clearly without animation.

---

## Skill triggers for unrelated queries

**Symptom:** The diagram skill loads for requests that have nothing to do with diagrams.

**Cause:** Description is too broad.

**Fix:** Add more specific negative triggers to the description in SKILL.md. Already present: "Do NOT use for: prose explanations without a visual deliverable, mermaid-style text diagrams, hand-drawn aesthetic." Extend if a new false-positive pattern emerges.

---

## Skill doesn't trigger when it should

**Symptom:** User clearly asks for a diagram, but the skill doesn't load.

**Cause:** Description missing trigger phrases the user actually said.

**Fix:** Add the user's phrasing to the description in SKILL.md. Common triggers should include: "draw", "diagram", "chart", "visualise", "show as", "create a [diagram type]", "architecture", "schema", "flow", "topology", "integration map".

---

## Skill is slow or output is degraded

**Symptom:** Output takes a long time, or quality dropped.

**Cause (per the building-skills guide):** SKILL.md too large, too many skills enabled simultaneously, or all content loaded instead of progressively.

**Fix:** Keep SKILL.md under 5,000 words (currently ~2,200). Detailed docs already live in `references/` and are loaded only when needed. If degradation persists, audit how many skills are enabled in the same Claude Code session.

---

## Cream leaks into a dark-theme SVG

**Symptom:** Opening `<slug>.dark.svg` on a dark host shows a cream rectangle peeking behind a card, or surrounding part of the diagram, or filling an icon background. The dark variant looks like the light variant punched through in places.

**Cause:** A `<rect>`, `<linearGradient>`, or icon `<g>` in the SVG defs still has a hardcoded light-theme hex (`#f5f1ea`, `#ece8e0`, `#ffffff`, `#f0ebe3`, `#ebe6db`) that the theme pass missed. Usually the canvas-background gradient or the chip-pill rect.

**Fix:**
- Every gradient id in `<defs>` must have its `stop-color` swapped to the dark equivalents from `foundations.html` §01.2. The canvas gradient (`bgGrad`) is the most common offender — its stops should be `#1a1a1f → #14141a` in the dark file.
- Search the SVG for any literal `#f5f1ea`, `#ece8e0`, `#ffffff`, `#f0ebe3`, `#ebe6db`, `#e8e2d8`, `#ddd5c6`, `#1a1a18` (in `fill=` not `flood-color=`), `#4a4845`, `#706e67`, `#9e9b95`. None should remain in the dark file.
- If the diagram was generated as two separate passes (light then dark) rather than one layout + theme application, the dark pass may have missed elements. Re-generate by sharing the structure from the light file and applying the dark token set, not by re-drawing.

---

## Drop shadows are invisible in dark theme

**Symptom:** Light cards look flush with the canvas in the dark variant — they don't appear elevated. Dark categorical cards (e.g. Postgres `surfaceSql`) merge into the background and the diagram reads as a flat sheet of color blocks.

**Cause:** The light-theme shadow filters use `flood-color="#1a1a18"` (near-black against cream). On a `#1a1a1f` dark canvas, near-black shadow flood is a no-op. The diagram was emitted with the light-theme filter bodies copied verbatim.

**Fix:** Use the dark-theme shadow filter bodies (`foundations.html` §01.5):
- **Light cards on dark:** `cardShadow` becomes `<feDropShadow dx="0" dy="0" stdDeviation="1.5" flood-color="#ffffff" flood-opacity="0.08"/>` — a near-zero white halo that reads as a 1px luminous stroke. The drop shadow is replaced; elevation comes from the halo + the card's own `#252531` fill against `#1a1a1f` canvas.
- **Dark categorical cards on dark:** `cardShadowDark` becomes `<feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="#000000" flood-opacity="0.55"/>` — same shape, deeper and flood-black so it actually does work against the dark canvas.

Filter ids stay the same (`cardShadow`, `cardShadowDark`) — only the bodies differ between theme files. Every card's `filter="url(#cardShadow)"` reference works unchanged.

---

## Indigo arrows look muddy in dark theme

**Symptom:** Arrow strokes in the dark variant read as a dim purple-grey, hard to follow against the canvas. Connector labels paired with the arrows have the same problem.

**Cause:** Brand-locked indigo `#4f5fb8` is correct on cream but lands at only 5.0:1 against `#1a1a1f` — readable but not crisp. The dark theme uses a lifted indigo (`#7785d4`) at 6.4:1 specifically to avoid this.

**Fix:** In the dark SVG, every `stroke="#4f5fb8"` and `fill="#4f5fb8"` (markers, label text) becomes `#7785d4`. Same for the `surfacePrimary` gradient stops (`#6573c9 → #3a4a8a` becomes `#7785d4 → #4d5db0`). All these substitutions are mechanical — see the token map in `foundations.html` §01.0 and §01.2.

If the muddy indigo is on an `<animateMotion>` motion-dot, ensure the path itself uses the dark stroke; otherwise the dot is fine and the line is the problem.

---

## Light and dark variants diverge

**Symptom:** The two emitted files look like *different diagrams* — card positions shifted, an arrow that's in one isn't in the other, label spelling differs, an icon is in the light version but absent from the dark version.

**Cause:** The two variants were generated in two separate passes through the canonical spec (a "redraw for dark") instead of as one layout with two theme applications. Any small per-pass variation in routing or labeling means the two diverge.

**Fix:** Re-do Step 5. Generate **one** SVG body (layout + connections + animations); then apply each theme token set to the same body to produce two files. The light and dark files should be byte-identical *except* in the values inside `<defs>`, the canvas `<rect>` fill, and the literal color attributes on text/stroke/fill/marker fills.

A useful check: `diff <(grep -o '<rect\|<text\|<path\|<line\|<circle' light.svg | sort | uniq -c) <(grep -o '<rect\|<text\|<path\|<line\|<circle' dark.svg | sort | uniq -c)` — the element counts should match exactly. If they don't, the diagrams have structural drift and need to share a layout.

---

## PDF export looks broken when using the dark variant

**Symptom:** Notion → PDF export drops a dark-themed SVG into a light PDF page, producing a dark rectangle floating on white. Or the diagram's text becomes invisible because dark inks landed on a light page.

**Cause:** Notion's PDF export assumes a light page surface. The dark SVG was designed for a dark host; PDF is not one.

**Fix:** For PDF export, always paste the `<slug>.light.svg`, even if the source Notion page is in dark mode. Document this in the proposal's authoring notes. The skill emits both files specifically to give the author this choice; the dark variant is screen-only by current design.

If a dark-on-dark PDF is needed in the future (a dark-themed branded PDF), that's a separate ask — generate the PDF from a dark Notion duplicate page that doesn't get exported normally. Not in scope for v1 of dual-output.

---

## Cross-mode failure modes (Pixel ↔ Material)

The entries below are specific to running two design systems side-by-side. They didn't exist before v2.0.0.

### A multi-diagram proposal accidentally mixed Pixel and Material

**Symptom:** Three diagrams in a proposal look like siblings; the fourth looks like a stranger — different font, different palette, different surface gradients — even though it's the same Partner Vetting set.

**Cause:** The manifest's `mode:` pin wasn't honored. Either (a) the first diagram was authored without a manifest and the second one's invocation specified a different mode, or (b) the manifest exists but `mode:` was omitted and the skill defaulted to Pixel mid-set.

**Fix:** A proposal is a coherent reader experience. Pick one mode and re-render every diagram in the set against that mode. Add `mode: pixel` (or `material`) to the manifest's `set:` block explicitly. From spec §07.5: per-diagram mode override is a hard error — the skill should reject it; if it didn't, that's a bug in the skill, not a styling tradeoff.

### Wrong mode for the diagram's purpose

**Symptom:** A general-purpose architecture diagram was rendered in Material mode, and the warm sable-bronze surfaces produce an unintended brand association — readers infer a specific product context from the palette that doesn't fit the subject.

**Cause:** The user's request didn't name a mode and the default kicked in correctly to Pixel — but the user later asked for "the Material version" without thinking about what it would imply.

**Fix:** Default to Pixel for subject-agnostic architecture diagrams. Use Material when the diagram should share visual DNA with an M3 product surface that this skill is documenting. The mode chip in the request matters — surface it during Step 1 restatement so the user sees what they're picking.

### Token-name confusion across modes

**Symptom:** A skill generation references `--surface-sql` (a Pixel token) inside a Material-mode SVG, or vice versa. The fill resolves to a brown-bronze gradient that wasn't intended.

**Cause:** The Step 3 context-load wasn't actually mode-routed — the agent read `references/pixel/foundations.html` while the request asked for Material.

**Fix:** Re-verify the mode detected in Step 1, then re-load §01.2 from the matching mode's `foundations.html`. Material's categorical surfaces are named `--ds-surface-sql` etc. (prefixed with `--ds-` to mark them as diagram-skill-namespaced derivations of V2 palette tokens). Pixel's are `--surface-sql` (no prefix; they're standalone). The prefix collision is intentional — it's a fail-fast signal that mode routing slipped.

### Material accent looks "wrong" against a dark canvas

**Symptom:** Info-blue `#6b9cf0` on Material's `#0d0f12` dark canvas reads "OK but not crisp" — visibly different from Pixel's lifted indigo `#7785d4` on the Pixel dark canvas at the same comparable elements.

**Cause:** Not a bug. Material's accent is intentionally theme-portable — the same hex in both themes — because info-blue is the V2 reference's focus-ring color and behaves predictably across both M3 surfaces. Pixel's accent lifts because indigo `#4f5fb8` would be unreadable on near-black; Material doesn't need that lift because `#6b9cf0` is already crisp on both.

**Fix:** Nothing to fix. Don't apply a Pixel-style lift inside a Material SVG — that would break the theme-portability contract documented in `references/material/foundations.html` §01.2 "Dark variant · accent stays put."
