# Design system skills

This folder collects **agent-facing skills** — packaged instructions an agent can consult when producing specific kinds of artefacts for the design system. Each skill lives in its own subdirectory with a `SKILL.md` (the brain) and a `references/` directory (templates, examples, troubleshooting).

Skills here are **reference material** for Claude Design and other agents that operate against this repo. They are deliberately *not* installed into `.claude/skills/` — placing them here keeps them out of any local Claude Code skill auto-loader, while remaining readable via the GitHub connector and via direct file reads.

A skill is **how** an agent does a thing. A spec is **what** changes in the product. The two are independent.

---

## Index

| Skill                  | Purpose                                                                                                                                                                                                                                                                                              | Status |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| [`diagram/`](diagram/) | Produces paired light + dark SVG diagrams in a locked cream-and-indigo visual style. Nine templates cover system context, layered architecture, pipeline/flow, sequence, ER data schema, infrastructure/deployment, event-driven flow, connector/integration map, plus a freeform catch-all view. | Active |

---

## Authoring conventions

When adding a new skill:

1. Create `skills/<skill-name>/`.
2. Author `SKILL.md` with YAML frontmatter (`name`, `description`) plus the full operating instructions.
3. Put templates, examples, troubleshooting docs, and any other supporting material under `skills/<skill-name>/references/`.
4. Add a row to the index above.
5. If the skill produces visual output that must match the design system, link to the relevant `SPEC.md` sections from inside `SKILL.md`.

When updating an existing skill:

- Edit in place — these directories mirror the canonical author's working copy. Add a CHANGELOG entry under `design-system/CHANGELOG.md` describing what changed.
- If the skill drifts from the design system (e.g., colors no longer match `tokens.css`), reconciling the drift is the next PR's first job — same invariant as SPEC.md.
