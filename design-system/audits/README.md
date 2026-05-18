# Design system audits

This folder collects **research artefacts** that inform future design system updates. Audits are typically authored by Claude Code (Playwright sweeps, screenshot comparisons, density analyses) or by the user; they feed into Claude Design's V1+ deliverables and into Claude Code's spec arcs.

Audits are **not specs**. They identify problems and propose directions; specs convert direction into implementable change.

---

## Index

| Audit                                                                          | Date       | Focus                                                                                                  | Status                            |
|--------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------|-----------------------------------|
| [`2026-05-18-responsive-audit/`](2026-05-18-responsive-audit/)                 | 2026-05-18 | Density gap between MacBook 14" laptop (1512×982) and Samsung Odyssey G7 (2560×1440). 52 screenshots × 7 surfaces × 2 viewports × 2 themes. | Open — awaiting Claude Design V1 to integrate density tokens. |

---

## Authoring conventions

When adding a new audit:

1. Create `audits/<YYYY-MM-DD>-<short-slug>/`.
2. Drop a `BRIEFING.md` (the audit doc), `screenshots/` (or other artefacts), and any capture scripts.
3. Add a row to the index above.
4. If the audit recommends design system changes, the recommendations should be phrased in terms of:
   - **Tokens** to add/change (referring to `tokens.css`).
   - **Components** to add/restyle (referring to entries in `SPEC.md § 3 Components`).
   - **Patterns** to introduce or modify (referring to `SPEC.md § 4 Patterns`).
5. The audit is **never** the implementation. Implementation lands in a separate spec (or a Claude Design PR) that references the audit.
