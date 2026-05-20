# Archived — Design System v2 seeding artifacts

This folder holds the artifacts from the **seeding of design system v2** (mid-2026). All content here is historical record. None of it is authoritative for any current decision.

The current design system lives at [`design-system/SPEC.md`](../../SPEC.md), with the canonical visual reference at [`design-system/assets/Design System v2.html`](../../assets/Design%20System%20v2.html) and the token / primitive CSS at [`design-system/assets/styles/`](../../assets/styles/).

## What's here

- `V2-BRIEFING.md` — the long-form Material 3 briefing that seeded specs 0092–0104. Originally landed as `docs/design-system-v2/README.md` via the seeding PR. Frames v2 as "a briefing-only PR; no application code changes; the deliverable is a spec plan" — that planning round is done; the briefing is preserved for the record.
- `CLAUDE-CODE-PROMPT.md` — the original prompt that instructed Claude Code to commit the v2 brief under `docs/design-system-v2/` and reply with a spec plan. Both phases shipped (the brief landed, the spec plan was produced); kept here as the audit trail of how v2 entered the repo.

## What this folder is NOT

- Not a current spec. Do not point readers here.
- Not loaded by Claude Design. The `PROMPT-FOR-CLAUDE-DESIGN.md` and `SPEC.md` are the canonical entry points.
- Not the place to add new briefing material. New design proposals go through the standard PR workflow against the live `SPEC.md` and live implementation.

If a future "v3" planning round happens, prefer adding it as `SPEC-v3-proposal.md` in the active `design-system/` folder under a clear "proposal" framing — don't reproduce the `docs/design-system-vN/` pattern that this archive exists to clean up.
