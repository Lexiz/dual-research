---
spec: 0133
title: Diagram skill v2.0.0 — mode-aware split + Material mode + how-it-works regen
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.7.0
created: 2026-05-20
pr: ""
---

# Spec 0133 — Diagram skill v2.0.0: mode-aware split + Material mode

> Closes the **deferred open item** from `design-system/SPEC.md § 12` ("Diagram skill palette alignment") that was originally introduced by spec 0127.
>
> Complexity: **M** (additive — preserves the existing Pixel design system intact; adds a parallel Material design system; mode-routes the workflow; regenerates the 16 in-app diagram assets in Material vocabulary).
>
> Drive mode: **by hand** for the Material design-system authoring (foundations / components / connectors / icons / templates HTML pages + the anchor canonical SVG). **Mechanical** for the remaining 16 canonical SVGs and the 16 `dual-research/diagrams/` regen — via a documented Pixel→Material sed transform script that swaps canvas / surfaces / inks / accent / shadow-flood / type-family tokens while preserving layout, geometry, arrows, and icon paths.

## 1. Context

The vendored diagram skill at [`design-system/skills/diagram/`](../design-system/skills/diagram/) has shipped on the **cream + indigo** design system since v1 (codified by spec 0127 as the "v1.1 dual-theme extension"). The skill produces general-purpose architecture diagrams for proposals — Notion-, GitHub-, and PDF-friendly SVG pairs that work across both light and dark hosts.

After the v1 → v2 M3 migration arc closed (specs 0127 → 0131), the dual-research application runs on **sable + sage** Material 3 vocabulary. The application's own reference diagrams (the spec-0121 how-it-works set at [`diagrams/how-it-works/`](../diagrams/how-it-works/), 14 SVGs) were authored using the v1 diagram skill — they're functional but their cream + indigo chrome reads as "from a different visual era" next to the M3 app.

`SPEC.md § 12` flagged this as an open item: "If we want the skill output to share visual DNA with the app, a follow-up spec aligns it to the M3 palette." This is that follow-up.

The decision (made during planning): **add Material as a second mode alongside Pixel — don't replace Pixel**. The skill produces general-purpose architecture diagrams in many contexts (not all of them dual-research-related), so the existing cream + indigo identity stays as the default. Material is opt-in for diagrams that need to share DNA with the app.

## 2. Goals

1. The diagram skill becomes **mode-aware** with `pixel` (default) and `material` modes. Mode is detected from the user's request in Step 1 of the workflow; default is `pixel` to preserve the behavior of every existing invocation.
2. Pixel mode is **preserved verbatim** — its visual language, primitives, canonical examples, and reference pages all carry forward unchanged, just reorganized into a `references/pixel/` subfolder.
3. Material mode is **fully recreated** — full parity with Pixel (foundations / components / connectors / icons / templates / 18 canonical SVGs / `_shared.css`), but every visual decision follows the dual-research V2 M3 design system. Lives in a parallel `references/material/` subfolder.
4. Mode is **part of the output filename** — `<slug>.<mode>.{light,dark}.svg` — so both mode versions of one diagram can coexist in the same folder without collision.
5. Manifest gains a `mode:` field with **per-set pinning** (same rule as the existing `theme:` pin — per-diagram override is a hard error).
6. The 14 how-it-works SVGs (plus 2 legacy `deep-research-pipeline.{light,dark}.svg` files) in `dual-research/diagrams/` are regenerated in Material vocabulary, in place, with the cache-buster bumped in `how-it-works.jsx` + `onboarding.jsx`.
7. `design-system/SPEC.md § 12` Open items list is updated: the diagram-skill alignment line is struck-through and marked **done**.
8. The 4 Cursor-feedback polish items roll up with the rework: `version: 2.0.0` on SKILL.md frontmatter, tightened frontmatter description, README first-30 audit, inlined destination convention (the external `Q12` punt is killed).

## 3. Non-goals

- No backend changes. Pure documentation + diagram-asset changes. `contract/`, `orchestrator/`, `protocol/`, `events/`, and other backend code untouched.
- No replacement of the Pixel mode. The cream + indigo design system stays as the default mode forever.
- No structural validator (an optional flex evaluated during planning; user opted to keep the manual visual review gate documented in SKILL.md Step 6).
- No backward-compatibility symlinks for the 18 Pixel canonical SVGs that gain `.pixel.` suffix — clean break per user decision. Inside `dual-research/diagrams/`, filenames are preserved so the app itself is unaffected.

## 4. Implementation map

The work landed in 5 internal phases (P1 through P5 in the personal skill copy at `~/.claude/skills/diagram/`, then P6 sync to vendored copy + this spec PR).

### P1 — Pixel cleanup + mode scaffold

- `SKILL.md` frontmatter: add `version: 2.0.0`; rewrite description to name both modes and the mode-aware trigger surface.
- Workflow Steps 1, 3, 5, 6, 7 updated to detect mode and route by `references/<mode>/...`.
- Destination convention inlined (no more external `design-doc/references/open-questions.md` Q12 punt). Convention: save to `diagrams/<slug>.<mode>.{light,dark}.svg` adjacent to the referencing document; ask if no anchoring document.
- References reorganized: all 7 mode-specific HTML pages + `_shared.css` moved into `references/pixel/`; 18 canonical SVGs renamed to `<slug>.pixel.{light,dark}.svg`. Mode-shared content stays at `references/` root: README, CHANGELOG, troubleshooting, OPEN-QUESTIONS, index.html, manifest.html, plus the 9 template input contracts at `references/templates/<name>.md`.
- `manifest.html`: new `mode:` field with default `pixel`; new §07.5 "Mode pinning" section parallel to §07.4 Theme pinning; updated pin table + schema YAML + worked example.
- `README.md`: first 30 lines rewritten to answer in order — what is this skill / what does it produce / when to invoke / input contract / output contract; folder map updated for the new structure.
- `references/material/` stub created with a placeholder README.

### P2 — Material foundations + anchor

- `references/material/foundations.html` — 8 sections mirroring Pixel's foundations:
  - **§01.0 Theme model** — same dual-theme contract (every theme-dependent token has a `-dark` sibling; gradient/filter ids stable across themes); explains the Material-specific palette and font choices.
  - **§01.1 Canvas** — 1660 width locked, M3 canvas gradients (`--md-surface → --md-surface-dim` resolved hexes).
  - **§01.2 Color palette** — V2 base palette intro (sable / sage / info / ok / warn / err / idle); accent identity (`--accent` = `--md-tertiary` = info-blue `#6b9cf0`, theme-portable); 7 categorical surface gradients derived from V2 palette tokens via `color-mix` recipes (`--ds-surface-primary` / `-neutral` / `-slate` / `-sql` / `-secure` / `-store` / `-cache` + `-deferred`); light + dark variants for each.
  - **§01.3 Typography** — Roboto Flex (plain) + Roboto Serif (brand); 9 type roles mapped to the M3 type scale with documented diagram-spec letter-spacing overrides for section labels (1.6) and connector labels (0.8).
  - **§01.4 Spacing** — 14 spacing tokens, identical to Pixel for cross-mode portability, each mapped to its `--md-sp-N` M3 equivalent (or `--ds-sp-*` namespaced where the diagram-layout value doesn't fit the M3 base scale).
  - **§01.5 Shadows** — two filter ids (`cardShadow`, `cardShadowDark`) with light + dark recipes mirroring Pixel's "mixed elevation" pattern (light cards on dark canvas use a near-zero white halo replacement; dark cards on dark canvas deepen the drop with `#000000` flood at 0.55).
  - **§01.6 Animations** — same 5 keyframes / 7 classes as Pixel (theme-portable); `tick` keyframe re-spec to interpolate between V2 ok-green tones; rationale documented for keeping diagram motion independent of M3 motion vocabulary.
  - **§01.7 Cross-template consistency** — mode + theme pin rules referenced.
- `references/material/_shared.css` — reviewer-site stylesheet mirroring Pixel's class-for-class with palette swap (M3 tokens, Roboto Flex/Serif, info-blue accent).
- Anchor canonical SVG pair: `examples/system-context.material.{light,dark}.svg` — hand-built, structurally identical to the Pixel anchor (Partner Vetting · System Context), visually verified via headless Chrome render against the Step 6 checklist.

### P3 — Material reference pages

- `references/material/components.html` — 10 sections covering 7 cards / 4 chips / 6 nodes / stages / lanes / groups / callouts / library index with side-by-side light/dark previews.
- `references/material/connectors.html` — 9 sections covering 8 arrow types, marker registry, 4 curve modes (L/Q/C/O), parallel-arrow gutters, label zones A/B/C with the no-rotation rule, crossing rules, density caps, contract checklist.
- `references/material/templates.html` — visual contract for each of 9 templates (Components / Icons / Layout / Arrows / Anti-patterns) with mode-shared `templates/<name>.md` input contracts.
- `references/material/icons.html` — 78 icons hand-drawn in M3 outlined style (1.8px stroke, round caps + joins) across 9 categories + canonical icon→gradient map + monogram fallback rule.
- `references/material/examples.html` — viewer for all 18 canonical SVGs.

### P4 — 16 remaining canonical SVGs + how-it-works regen

- **Skill canonical examples (16):** Generated via mechanical token substitution from Pixel originals. Script at `/tmp/transform-pixel-to-material.sh` (documented in commit message) handles canvas / surfaces / inks / accent / shadow-flood / type-family swaps; light + dark themes have separate substitution tables because the surface lifts differ. Layout, geometry, arrows, and icon paths are preserved exactly — only color values, shadow filter bodies, and canvas gradient stops differ from the Pixel original. Visual verification via headless Chrome render on a sampled subset (pipeline-flow light, layered-architecture dark).
- **In-app diagrams (16):** Same script applied in place to `dual-research/diagrams/how-it-works/*.{light,dark}.svg` (14 files) and `dual-research/diagrams/deep-research-pipeline.{light,dark}.svg` (2 files, unreferenced but kept). Filenames preserved so no JSX wiring change required — only the cache-buster bumps from `?v=0124a` to `?v=0133a` in `how-it-works.jsx` (1 ref) and `onboarding.jsx` (1 ref) so browsers reload the new visuals.

### P5 — cross-mode wiring

- `references/material/examples.html` wired with all 18 rendered SVGs.
- `references/index.html` gains a parallel Material identity panel below the Pixel one (same primitives, two visual languages). The "Material under construction" warn callout from P1 is removed.
- `references/troubleshooting.md` adds 4 cross-mode failure-mode entries: accidental mode mix in a multi-diagram set, wrong mode for the diagram's purpose, token-name confusion across modes, theme-portable accent expectations.

### P6 — sync + spec

- `rsync -av --delete --exclude=_archive ~/.claude/skills/diagram/ design-system/skills/diagram/` — mirrors the personal copy over the vendored copy.
- `design-system/SPEC.md § 12` open-items list: diagram-skill alignment bullet struck-through with the "done as of spec 0133" note.
- This spec doc + the changelog entry land in the same PR.

## 5. Acceptance

- [ ] `design-system/skills/diagram/SKILL.md` frontmatter has `version: 2.0.0` and a two-mode description.
- [ ] `design-system/skills/diagram/references/pixel/` exists with 7 HTML pages + `_shared.css` + 18 `<slug>.pixel.{light,dark}.svg` canonical SVGs.
- [ ] `design-system/skills/diagram/references/material/` exists with 7 HTML pages + `_shared.css` + 18 `<slug>.material.{light,dark}.svg` canonical SVGs + 78 icons hand-drawn in M3 outlined style.
- [ ] `design-system/skills/diagram/references/templates/<name>.md` (9 files) sits at root — mode-shared input contracts.
- [ ] `design-system/skills/diagram/references/manifest.html` has `mode:` field with default `pixel` and a §07.5 Mode pinning section.
- [ ] `diagrams/how-it-works/*.{light,dark}.svg` (14 files) regenerated in Material vocabulary; filenames preserved.
- [ ] `diagrams/deep-research-pipeline.{light,dark}.svg` (2 files) regenerated likewise.
- [ ] `src/dual_research/ui/static/how-it-works.jsx` and `src/dual_research/ui/static/onboarding.jsx` have `?v=0133a` cache-busters on diagram URLs.
- [ ] `design-system/SPEC.md § 12` diagram-skill open item is struck-through and marked done.
- [ ] `CHANGELOG.md [Unreleased]` includes the spec 0133 entry.
- [ ] Visual check: `/#/how-it-works` route renders the regenerated SVGs in both light and dark themes; M3 chrome reads coherently against the app's M3 chrome.

## 6. Open follow-ups

- Future polish: the 16 mechanically-transformed Material canonical SVGs (everything except the system-context anchor) preserve Pixel icon paths. Some inline icons are filled silhouettes; the M3-outlined icon style documented in `material/icons.html` is the future direction. A follow-up spec could redraw inline icons in canonical examples to match the M3-outlined style — non-urgent.
- The Pixel rename breaks any external Notion / GitHub / PDF docs that link to old `<slug>.{light,dark}.svg` paths (now `<slug>.pixel.{light,dark}.svg`). No telemetry on how many exist; documented in the CHANGELOG entry. If a follow-up audit surfaces consumers, the fix is a one-character path edit.
