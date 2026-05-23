---
spec: "0190"
date: 2026-05-23
version: 1.37.2
pr: "https://github.com/Lexiz/dual-research/pull/219"
---

# Spec 0190 — TimelineTabs `data-active` migration finished — shipped

Closes the dual-selector debt spec 0173 §2.3 left in place. The
`<Tab variant="solid">` branch in `shared.jsx` no longer emits the legacy
`'is-active'` className; active state is signalled solely by
`data-active={active ? 'true' : undefined}`, matching how bar-2 status /
agent segments have emitted active state since spec 0173. Both CSS files
drop the `.tab-solid.is-active,` arm of the dual selector.

## What landed

- **[src/dual_research/ui/static/shared.jsx:1086](../src/dual_research/ui/static/shared.jsx)** — `<Tab variant="solid">` now emits `data-active={active ? 'true' : undefined}` and drops `active && 'is-active'` from the `_cn(…)` className call. Doc-comment block above the branch records the spec 0190 migration.
- **[src/dual_research/ui/static/components.css:2194](../src/dual_research/ui/static/components.css)** — `.tab-solid[data-active="true"]` is now the sole active-state selector. The leading `.tab-solid.is-active,` arm is gone. Comment block rewritten to reference both spec 0173 §2.3 and 0190.
- **[design-system/assets/styles/composed-components.css:779](../design-system/assets/styles/composed-components.css)** — mirror of the above. Both CSS files land in the same commit per CLAUDE.md two-files-in-sync rule.
- **[design-system/SPEC.md:366](../design-system/SPEC.md)** — §11 Critique pane note rewritten. The prior "`is-active` retained as backwards-compat selector for non-bar-2 call sites (notably TimelineTabs) until they migrate" line replaced with "`.tab-solid.is-active` is fully retired; the `<Tab variant="solid">` branch in shared.jsx now emits `data-active` only."
- **[tests/spec0190/test_tab_solid_data_active.py](../tests/spec0190/test_tab_solid_data_active.py)** — 7 new structural tests:
  - Solid branch emits `data-active`; solid branch does NOT emit `is-active`.
  - Other variants (`kind`, `phase`, `md-btn--text`, default `tab`) still use `is-active` (guard against accidental sweep per spec §5).
  - Both CSS files drop the dual selector and keep the canonical attribute selector (two assertions per file).
- **CHANGELOG / version** — `1.37.1` → `1.37.2` (PATCH per refactoring type).

Full suite: 1700 passed (was 1693).

## Live smoke

```
$ curl -sS https://dual-research-alex.fly.dev/shared.jsx?v=0181a \
    | grep -A 4 "variant === 'solid'"
  if (variant === 'solid') {
    // Spec 0190 — finished the spec 0173 §2.3 `[data-active]` migration.
    // The button no longer emits the legacy `is-active` className; active
    // state is signalled solely via the `data-active="true"` attribute,
    // matching how bar-2 status / agent segments in run-detail.jsx have
```

Confirmed: the deployed bundle carries the migrated branch.
`fly status -a dual-research-alex`: two app machines on version 492 running
image `01KSARWQC7Q5239RPZYDKJ3NJS`.

## Deploy notes

- `fly deploy` hit the now-routine held-lease pattern documented in
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md).
  Two failed release attempts (v490, v491) before v492 brought up the
  greens healthy. `scripts/sweep_stale_blues.sh` would have been a no-op
  here — Fly's orchestrator never tagged the v489 blues as
  `safe_to_destroy`. Fell straight to manual
  `fly machine destroy --force <v489-machine-id>` for both zombies.
  Final state: 2 v492 machines, both passing.

## What this DOES NOT do

- **Touch other Tab variants.** `kind`, `phase`, `md-btn--text`, default `tab`
  — all keep their `is-active` className. Separate selectors, separate
  spec if anyone wants to extend the migration.
- **Touch `tt-cell` theme tabs.** Not a `tab-solid` consumer; out of scope.
- **Change the `Tab` component's `active` prop contract.** The caller-facing
  API is unchanged. Internally `variant === 'solid'` now maps `active` to
  `data-active`; `TimelineTabs` and bar-2 segments needed no edits.
- **Touch the `.tab-solid[data-active="true"] .chip-value` sub-rule.** It
  was already in canonical form (no `is-active` partner); left alone.

## Rebase note

PR #219's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as all four previous specs in this drain. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0190.jsonl`, force-with-lease-pushing, then admin-squashing.
This conflict will keep happening until spec 0191's python supervisor batches
event emission.
