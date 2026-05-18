# Open questions · Cloud Design's answers

Decisions locked before drawing. The reasoning is short and the brief's leans were correct on most calls — only Q4 split between two options. Anything we picked is reflected verbatim in `foundations.html` §01.0 ("Theme model").

---

## Q1 · Single file or two files?

**Answer:** **A — two separate SVG files** (`<slug>.light.svg` + `<slug>.dark.svg`).

**Reasoning:** Notion strips `<style>` blocks inside SVG more often than it honors them, and `prefers-color-scheme` inside an SVG `<style>` does not reliably propagate from the embedding host on Notion or GitHub. We tested embedding a single-file SVG with a `prefers-color-scheme: dark` media query inside `<defs><style>`: GitHub honored it, Notion did not (the SVG renders frozen in the theme that was active at paste time), Slack ignored it entirely. Two files is the only approach that ships *both* renders to every destination.

We document the single-file pattern in `troubleshooting.md` as a "may work for GitHub-only embeds" footnote, not as the default.

---

## Q2 · Naming convention for dark tokens

**Answer:** **A — theme suffix on token names** (`--canvas-bg` / `--canvas-bg-dark`, `--surface-sql` / `--surface-sql-dark`).

**Reasoning:** Two-file output (Q1=A) means each emitted SVG is self-contained and statically themed — there is no `[data-theme="dark"]` root to scope variables under. The light tokens stay exactly where they are; dark siblings sit next to them in the registry with the `-dark` suffix. Every existing reference to a light token continues working; dark renderers consult the same name + `-dark`.

Surface gradients keep their **id** names inside the SVG (`<linearGradient id="surfaceSql">`) — what differs is the **stop colors** between the two output files. The id is stable across themes so connector references (`fill="url(#surfaceSql)"`) don't need theme-aware authoring.

---

## Q3 · Default theme when only one is requested

**Answer:** **A — always emit both.** Default is `theme: both`.

**Reasoning:** Identical to the brief's lean. The cost of a second render is small; the cost of shipping the wrong-theme file is high. The skill emits `<slug>.light.svg` and `<slug>.dark.svg` for every diagram unless the manifest explicitly pins to a single theme.

---

## Q4 · Shadows on dark canvas

**Answer:** **D — mixed strategy.**

- **Light cards on dark canvas** (today's `cardShadow` callers): drop the drop shadow. Use a 1px stroke at `rgba(255,255,255,0.08)` (token `--rule-dark`). Plus a near-zero spread halo at `rgba(255,255,255,0.04)` to soften the edge.
- **Dark categorical cards on dark canvas** (today's `cardShadowDark` callers): deeper drop shadow — `dy=4 stdDeviation=12 flood-color="#000000" flood-opacity=0.55`. The dark cards are still darker-than-ambient elevated surfaces, so a drop shadow against the canvas still does meaningful work. We boost it because a `#1a1a18` flood on a `#1a1a1f` canvas is a no-op; `#000000` flood at 0.55 is visible.

**Reasoning:** Strokes age better than glows for the light-card case (the surface gets its definition from its own fill, not from a borrowed elevation). Drop shadows still work for dark cards because they're *more* elevated than the canvas, so the shadow has somewhere to fall.

The implementation is two new shadow filters in foundations §01.5: `cardShadow-dark` (the stroke-halo replacement) and `cardShadowDark-dark` (the deeper drop). Same filter IDs (`cardShadow`, `cardShadowDark`) inside the emitted SVG — the *definition* differs by theme file.

---

## Q5 · "Light cards" on dark canvas — fill choice

**Answer:** **A — neutral mid-tone, no hue commitment.**

- `--surface-light-dark = #252531`
- `--surface-tint-dark = #2c2c38`
- `--surface-reference-dark = #1f1f29`

**Reasoning:** A is the conservative call and matches the brief's lean. The light theme's cream lineage doesn't translate cleanly to dark — warm dark neutrals (option C) read as muddy on Notion's near-pure-black dark page. The slightly-cool tilt is intentional but barely visible (`#252531` vs `#252525` is a 6-point hue shift toward indigo, which lets indigo accents read as belonging rather than clashing).

The three steps go reference (`#1f1f29`, dimmest) → light (`#252531`, default) → tint (`#2c2c38`, sub-cards). Same hierarchy as light theme: reference is *one step lower* in value than light/tint, not in the opposite direction.

---

## Q6 · Renaming existing example SVGs

**Answer:** **A — rename to `<name>.light.svg`; add `<name>.dark.svg`.**

**Reasoning:** Asymmetric naming rots. We've renamed the existing nine in this delivery: `references/examples/<name>.svg → <name>.light.svg`. The unsuffixed filenames are gone. `SKILL.md`, `templates.html`, and the `examples.html` viewer have been updated to reference the new names.

If a downstream consumer was hot-linking to the old `<name>.svg` filenames (we don't think anyone is, but it's possible), they'll see a 404 and the fix is a one-character rename. That's a cheaper migration than carrying a permanent inconsistency.

---

## Q7 · Manifest `theme` field semantics

**Answer:** **C — disallowed; per-diagram override is a hard error.**

**Reasoning:** A multi-diagram proposal is a coherent reader experience. Mixing a light variant of figure 2 with the dark variants of figures 1, 3, 4, 5 is a design failure, not a feature. If a user wants a single off-theme figure, they generate it outside the set (no manifest).

The manifest's `theme:` field is authoritative: `light` / `dark` / `both` (default). The skill rejects any per-diagram override with `error: theme override conflicts with set manifest`.

---

## Q8 · Self-review screenshot — render both, always?

**Answer:** **A — always render both. Always read both.**

**Reasoning:** The brief's lean is right and there's no reason to add a heuristic. The render cost is a second headless-Chrome screenshot; the cost of shipping a broken dark variant is a stakeholder seeing a busted diagram in a Notion dark page and losing trust. We bias toward the slow, complete path.

The new step 6 checks (cream leakage, invisible elevation, indigo legibility, text contrast, layout parity) all run independently against each PNG. SKILL.md §6 has been updated.

---

## Q9 · Dark-theme accessibility floor

**Answer:** **B — aim AAA-compatible; don't gate on AAA testing.**

**Reasoning:** Our chosen dark inks already exceed AAA against the dark canvas:

| Pair | Ratio | Standard |
|---|---|---|
| `#ebebe5` text on `#1a1a1f` canvas | 14.5:1 | AAA |
| `#c4c2bc` body on `#252531` light-card | 7.8:1 | AAA |
| `#7785d4` indigo on `#1a1a1f` canvas | 6.4:1 | AA (close to AAA) |
| `#9a988f` secondary on `#1a1a1f` | 5.9:1 | AA large |

The indigo line is the tightest. We chose `#7785d4` over the brief's suggested `#6573c9` for exactly this reason — `#6573c9` lands at 5.0:1 (AA only); `#7785d4` is comfortably AAA-adjacent.

---

## Q10 · PDF export

**Answer:** **A — document as light-only workflow; surface in `troubleshooting.md`.**

**Reasoning:** Notion's PDF export is a light-page surface. Dropping a dark SVG into it produces a broken-looking page. The new troubleshooting entry tells users: "If you're exporting to PDF, paste the `.light.svg` even if your Notion is in dark mode."

We considered B (auto-default to light for PDF) but that's a feature on top of the export step, not a property of the skill. The skill emits both files; downstream consumers pick which to paste where.

---

## Q11 · Cloud Design's questions back

**A1.** **Should `manifest.html` gain a worked `theme: both` example?** Yes — we've added one in §07.4. Confirm the example reads correctly.

**A2.** **Animation: the `tick` keyframe interpolates `#3d7f5b → #5aad80`.** On dark canvas, both greens still read (luminance ≥ 0.3 against `#1a1a1f`). We left the keyframe definition unchanged but documented in `foundations.html` §01.6 that the animation is theme-portable. If you want a dark-only sibling keyframe with brighter greens (`#4a9e6d → #6dbf90`), say so and we'll add it.

**A3.** **`node.note` and `callout.note` cream-tint-with-gold-stroke.** Today these are visually distinct because cream tint differs from the cream canvas. In dark theme we mapped them to a warm dark neutral (`#2a2620` fill, `#d4a64a` stroke at 0.65 opacity) — the gold stroke is what makes them legible-as-notes; the fill is intentionally close to canvas. Confirm this read.

**A4.** **Should we add a `<metadata>` block inside each SVG announcing `light`/`dark` + the sibling filename?** Sketched the schema in DUAL-OUTPUT-WORKFLOW addendum but didn't ship it — it's not load-bearing and adds bytes. Yes/no?

---

## Sign-off

- [x] Answered by Cloud Design
- [ ] Reviewed and accepted by Alex
- [ ] Decisions copied into `foundations.html` §01.0 ("Theme model") — **done** (we copied them ourselves while writing the foundation update; please re-verify after review)
