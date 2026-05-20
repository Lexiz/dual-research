# Archived — Design System v1

This folder holds the **deprecated v1 design system spec**, archived on 2026-05-20 as part of [spec 0127](../../../specs/0127-design-system-v2-canonicalization.md).

**The current design system is at [`design-system/SPEC.md`](../../SPEC.md).** That file describes the v2 (Material 3) design system, which is the only design system in active use.

## What's here

- `SPEC.md` — the v1 design system text reference. Snapshot of `main` as of `0fd9b95` (v0.69.12). Documents the pre-Material-3 token system, the IBM Plex type pair, the 5-step surface model, and the component primitives that preceded the M3 migration.

## Why we keep it

- **Historical context for code archaeology.** Older PRs and CHANGELOG entries reference v1 token names (`--bg-1`, `--fg-2`, `var(--sans)`); this file documents what those meant.
- **Reference for the migration.** Specs 0092–0131 trace the v1 → v2 transition. Reading the v1 spec alongside those specs makes the diff legible.

## What this folder is NOT

- Not a maintained spec. Do not edit `SPEC.md` here.
- Not authoritative for any new work. All new design proposals target the v2 SPEC.md in the parent folder.
- Not loaded by Claude Design. The `PROMPT-FOR-CLAUDE-DESIGN.md` points at the v2 SPEC.md, not this folder.

If you find yourself reading this folder to decide something, you're looking at the wrong document. Stop and go read [`design-system/SPEC.md`](../../SPEC.md) instead.
