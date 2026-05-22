# Design system — CHANGELOG

Human-readable history of design system changes. Append-only. Entry order: newest first.

Format:
```
## YYYY-MM-DD — short descriptor
- One bullet per material change.
- Linked PR when applicable.
- Component / token / pattern affected.
```

---

## 2026-05-22 — Critique card · ItemCard + SOURCES segment visual reference (spec 0144)
- **New §13 in `Design System v2.html`: "Critique card · ItemCard + Sources".** Rendered visual reference for the canonical per-card primitive that all four kinds (Question · Disagreement · Issue · Comment) share. Anatomy block lists the six-step stacking order; three example cards demonstrate resolved-with-sources, capped-with-unverified-source, and open-with-evidence-needed-but-no-sources. A SourceRow detail block shows collapsed vs expanded states.
- **Legacy QuestionThread section relabelled.** The prior §13 "QuestionThread" is now §13b "QuestionThread (legacy)" with a `history` note clarifying the routing rule: `Array.isArray(item.transitions)` → `<ItemCard>`; else → `<QuestionThread>`. Pre-0114 archived runs keep the legacy renderer.
- **New rail entry.** `#itemcard · Critique card · Sources` slotted between Critique header and the legacy QuestionThread.
- **Principle 11 added** to §1 Principles cards: *One card primitive per surface* — closes B08 (Phase 4 cards missing Issue/Comment patches) and B14 (per-card sources) on the same primitive. Mirrors the canonical text already in `SPEC.md §1`.
- **`composed-components.css` (mirrored to `v2-m3-page.css` via symlink) gains the v2.4 block** — `.crit-card{,.is-*}`, `.crit-card-head`, `.crit-card-body{,em.evidence-needed}`, `.crit-card-id`, `.crit-section-title`, `.lc-row{,-chips,-body}`, `.lc-footer` (ok / warn / err / idle variants), `.item-card__sources{,-hd}`, `.source-row{,.is-unverified,__head,__chev,__title,__host,__body,__field,__label,__url,__excerpt}`, `.chip-unverified`. All rules read from the M3 `--md-*` token vocabulary; no hex codes.
- **No `SPEC.md` change** — the canonical text contract for SourceRow (§3 Primitives), Sources segment (§4.7), Critique card composition (§4.8), and Principle 11 was already merged in the spec 0151 PR. This PR ships only the §6.3.e visual reference + the supporting CSS.

---

## 2026-05-21 — Consumption card visual rework (spec 0146)
- **§14 Consumption row rewritten.** Header is a 3-column grid (icon + name · bracketed `(X.X% of 1M)` right-aligned to the bar end · chevron) instead of the prior `tokens · cost · % of 1M` trio. Tokens and cost live on the bar (collapsed) or inside the totals block (unfolded), not in the header.
- **Per-attachment sub-rows auto-show** when the card is unfolded — the User-prompt row's `Chat message` + one `Attachment · {title}` per attachment from spec 0145 render without a second click.
- **`.ccx-totals` child order swapped** to label-left / value-right (was value-left / label-right in the v2 reference). Mirrors the bar-row grid above it.
- **Capital-T bar-row section labels** (`Total tokens`, `Output`); totals-block lines stay lowercase (`input cost`, `total input`).
- **One-decimal cost displays** inside the consumption card (via the JS `fmtCost1` helper); the run-detail footer aggregate keeps 4-decimal precision as the audit number.
- **`composed-components.css` mirror updated** with the new `.ccx-header` grid + `.hd-id` wrapper.
- **Design System v2 reference HTML §14** updated — every `.ccx-header` block wraps the icon + name in `<span class="hd-id">` and the `.stats` span carries only the bracketed percentage; all `.ccx-totals .line` children re-ordered `.l` then `.v`.

---

## 2026-05-20 — v2 canonicalization (spec 0127)
- **V2 (Material 3) design system promoted to canonical.** `SPEC.md` rewritten end-to-end to describe the Material 3 design system as the single current design system. No more "v1" / "v2" framing in active text — the previous design system is archived.
- **V1 SPEC.md archived** at [`_archive/v1/SPEC.md`](_archive/v1/SPEC.md), with a brief `_archive/v1/README.md` pointing readers at the current SPEC.
- **V2 brief contents moved into `design-system/`.** The old `docs/design-system-v2/` location was retired entirely. Its contents now sit at:
  - `design-system/assets/Design System v2.html` — canonical visual reference.
  - `design-system/assets/styles/tokens-and-primitives.css` (renamed from `v2-m3.css`) — source-of-truth M3 token + primitive CSS.
  - `design-system/assets/styles/composed-components.css` (renamed from `v2-m3-page.css`) — source-of-truth composed-component CSS.
  - `design-system/notion-issues/` — the 17 known-issues batch (21 screenshots) that drove specs 0098–0117.
  - `design-system/_archive/seeding/V2-BRIEFING.md` + `CLAUDE-CODE-PROMPT.md` — historical record of how v2 entered the repo.
- **CSS source-of-truth files renamed.** `v2-m3.css` → `tokens-and-primitives.css`; `v2-m3-page.css` → `composed-components.css`. The `v2-m3-` prefix was a briefing-phase artifact and became noise once v1 was archived.
- **`README.md` rewritten.** Drops v1/v2 framing; updated folder map; clarified that `_archive/` and `skills/` are reference material the design-system invariant doesn't apply to.
- **`PROMPT-FOR-CLAUDE-DESIGN.md` updated to v2 conventions** — Roboto Flex + Roboto Serif (replacing the v1 "IBM Plex Sans" guidance), `--md-*` token vocabulary (replacing v1 `--bg-*` / `--fg-*` examples), Material Symbols Outlined for icons, M3 elevation + state-layer + motion language. Added a heads-up about the active live-code migration (specs 0128–0131 to follow).
- **Live frontend code untouched** — the live `tokens.css` / `base.css` / `components.css` / `theme.css` / JSX files continue to run on the additive layering pattern introduced by spec 0092 (v1 + v2 token vocabularies coexist). The live-code v2 migration is deferred to specs 0128–0131. (Migration completed 2026-05-20 when spec 0131 shipped; the historical `SPEC.md § 12 Migration status` section was deleted in that same PR.)

## 2026-05-19 — diagram skill vendored as agent-facing reference
- New `design-system/skills/` subfolder introduced as the canonical home for agent-facing skills consulted while authoring design-system proposals. Companion `skills/README.md` documents the index and authoring conventions.
- Vendored the `diagram` skill at [`design-system/skills/diagram/`](skills/diagram/) — paired light + dark SVG production in the locked cream-and-indigo style. Includes `SKILL.md` plus `references/` (templates, examples, troubleshooting, foundations/components/connectors/icons HTML, `_shared.css`). `_archive/` excluded.
- `PROMPT-FOR-CLAUDE-DESIGN.md` updated with a "Skills available to you" section pointing Claude Design at the diagram skill, plus a bullet under "Where the design system lives" referencing `skills/`.
- No SPEC.md or live implementation change — this PR adds reference material only. The design-system invariant ("every PR touches SPEC.md AND the live implementation") does not apply to reference-only additions; the invariant guards against text↔code drift inside the system, not against expanding the surrounding documentation.

## 2026-05-18 — folder + SPEC introduced; design-language drift fixed
- New `design-system/` folder created as canonical text reference. Pairs with the live implementation in `src/dual_research/ui/static/` and the in-app reference at `/#/language`.
- `SPEC.md` bootstrapped from the current state of `tokens.css` + `components.css` + `design-language.jsx` at `0fd9b95` (v0.69.12).
- `design-language.jsx`: added `<LoadingState>` Spotlight (drift fix; SPEC-0084 had introduced the primitive but no Spotlight existed).
- `design-language.jsx`: updated **Consumption row** Spotlight to reflect SPEC-0086 (phase header above the row, not glued to card edges).
- `design-language.jsx`: updated **Agent Input panel** Spotlight to reflect SPEC-0085 (3-tier hierarchy: System Prompt collapsed → User Prompt expanded with nested 'From chat' + 'External resources mentioned' → Child Pages as top-level entries).
- Responsive audit dropped at [`audits/2026-05-18-responsive-audit/`](audits/2026-05-18-responsive-audit/) — proposes a `--density` token + `body.compact` class for the laptop/wide viewport gap. Not yet implemented; awaiting integration with Claude Design's V1.

## Pre-history (before this CHANGELOG existed)

Changes prior to 2026-05-18 are documented in [`../CHANGELOG.md`](../CHANGELOG.md) (project root) and in individual spec files at [`../specs/`](../specs/). Notable design-system arc: specs 0066–0087 over 2026-05-16/17/18 — design unification, AgentStrip, GhostedAnnotation, CardHeadline, PaneButton, RoundScrubber, BrandMark, LoadingState, Agent Input rework, Consumption rework, cross-cutting polish.
