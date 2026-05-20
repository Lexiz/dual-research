# Design system — `dual-research/design-system/`

This folder is the **canonical text reference** for the dual-research design system. It pairs with the **live implementation** in [`src/dual_research/ui/static/`](../src/dual_research/ui/static/) and the **in-app visual reference** at [`/#/language`](../src/dual_research/ui/static/design-language.jsx).

The design system is based on Material 3, with a pastel sable + sage palette and a calm, terminal-adjacent aesthetic specific to dual-research. The previous (pre-Material-3) design system is archived under [`_archive/v1/`](_archive/v1/) for historical reference and is no longer maintained.

This folder exists for one reason: to enable a clean **two-way collaboration loop** between Claude Code (terminal) and Claude Design (claude.ai chat), with GitHub as the synchronisation layer.

---

## What lives where

| Artifact | Role |
|---|---|
| [`SPEC.md`](SPEC.md) | Canonical text spec. The single source of truth for the design system. |
| [`PROMPT-FOR-CLAUDE-DESIGN.md`](PROMPT-FOR-CLAUDE-DESIGN.md) | Paste-able prompt for the Claude Design project on claude.ai. Use this at the start of any new design exercise or pin as project context. |
| [`CHANGELOG.md`](CHANGELOG.md) | Human-readable history of design system changes. Append-only. |
| [`assets/Design System v2.html`](assets/Design%20System%20v2.html) | **Canonical visual reference** — open in a browser to see every primitive and composed component rendered. |
| [`assets/styles/tokens-and-primitives.css`](assets/styles/tokens-and-primitives.css) | Source-of-truth CSS for the M3 token layer + primitives. Live `tokens.css` + `components.css` mirror this. |
| [`assets/styles/composed-components.css`](assets/styles/composed-components.css) | Source-of-truth CSS for the composed components used in the visual reference. |
| [`notion-issues/`](notion-issues/) | Historical capture of the 17 known-issues batch from the Notion bug log that drove specs 0098–0117. Reference for what each spec was solving. |
| [`audits/`](audits/) | Research audits that feed into design system updates. Active entries: `2026-05-18-responsive-audit/` (52 screenshots, 4 viewport × theme combinations) and `2026-05-20-hiw-rework/` (clickable mockup for the HiW rework). |
| [`skills/`](skills/) | Packaged agent-facing skills (e.g., the diagram skill) that Claude Design can consult when a proposal calls for a specific artefact. See `skills/README.md`. |
| [`_archive/v1/`](_archive/v1/) | The deprecated pre-M3 spec. Not maintained; preserved for code-archaeology purposes. |
| [`_archive/seeding/`](_archive/seeding/) | The original M3 briefing artifacts (`V2-BRIEFING.md` + `CLAUDE-CODE-PROMPT.md`) from mid-2026. Historical record of how the M3 design system entered the repo. |
| [`../src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css) | **Live implementation.** CSS custom properties — `--md-*` tokens. **Authoritative for actual token values in production.** |
| [`../src/dual_research/ui/static/base.css`](../src/dual_research/ui/static/base.css) | Live implementation. Resets, type role utilities, `:focus-visible` ring. |
| [`../src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) | Live implementation. All component CSS. **Authoritative for actual visual rules in production.** |
| [`../src/dual_research/ui/static/theme.css`](../src/dual_research/ui/static/theme.css) | Live implementation. Body-class additives (`body.tint-secondary`, `body.compact`). |
| [`../src/dual_research/ui/static/design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) | Live in-app reference at `/#/language`. DNA one-pager + Full reference. |
| [`../src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) | Live in-app design system primitives (React function-components). |

---

## The invariant

> **Every PR that modifies design must touch `SPEC.md` AND the live implementation files in the same commit.**

The text spec, the canonical visual reference HTML, and the actual app must always agree. If they don't, the design system has drifted — the next PR's first job is to bring them back in sync.

The invariant guards against text↔code drift inside the design system. It does **not** apply to reference-only additions (e.g., a new audit folder, a new skill, an archival README) — those are documentation about the system, not the system itself.

---

## How to contribute

### From Claude Code (terminal, this repo)

1. Open a branch named `spec-NNNN-<descriptor>` (matches the spec-per-PR convention).
2. Write the spec file at `specs/NNNN-<descriptor>.md`.
3. Edit `SPEC.md` and the live implementation files in the same PR.
4. Append an entry to `design-system/CHANGELOG.md` and to the root `CHANGELOG.md`.
5. Open the PR. Merge when green. Deploy.

### From Claude Design (claude.ai chat, via GitHub connector)

1. Paste [`PROMPT-FOR-CLAUDE-DESIGN.md`](PROMPT-FOR-CLAUDE-DESIGN.md) at session start (or pin as project context).
2. Open a branch named `design-system/<short-descriptor>`.
3. Edit `SPEC.md` and the live implementation files within the whitelist (see prompt § "What you may edit").
4. Append an entry to `design-system/CHANGELOG.md`.
5. Open a PR against `main` following the template in the prompt.
6. Claude Code (terminal) reviews + merges. Per-surface JSX work (e.g., updating `run-detail.jsx` to adopt a new pattern) gets called out as "Out of scope" in the PR description and Claude Code picks it up as a follow-up.

---

## What's not in this folder

- **`docs/`** — none of the design system lives there anymore. (The brief `docs/design-system-v2/` location was retired in spec 0127; its contents are now under `design-system/assets/` + `design-system/notion-issues/` + `design-system/_archive/seeding/`.)
- **Application-surface JSX** — per-surface files (`run-detail.jsx`, `run-list.jsx`, `how-it-works.jsx`, `compare.jsx`, etc.) consume the design system but are not part of it. They live next to the other live-implementation files but are off-limits to design-only PRs.
- **Backend / data layer** — none of the design system reaches into Python, the orchestrator, the Supabase schema, the queue, the protocol. Design changes never touch them.
