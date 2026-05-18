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
