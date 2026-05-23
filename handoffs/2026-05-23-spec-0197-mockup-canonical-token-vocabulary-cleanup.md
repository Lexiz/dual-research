---
spec: "0197"
date: 2026-05-23
version: 1.39.3
pr: "https://github.com/Lexiz/dual-research/pull/225"
---

# Spec 0197 — mockup canonical DS token vocabulary cleanup — shipped

The dashboard mockup at `dashboard/mockups/dashboard-redesign-v3-horizontal.html`
now uses canonical DS token names end-to-end. The spec-0184 parity-test
allowlist `_MOCKUP_SHORTHAND_ALLOWLIST` shrank from 3 entries to `set()`,
matching its intended steady state. No live-render change; pure vocabulary
hygiene that closes the spec-0184 deferral.

## What landed

- **[dashboard/mockups/dashboard-redesign-v3-horizontal.html](../dashboard/mockups/dashboard-redesign-v3-horizontal.html)** — bulk rename of all three shorthand tokens:
  - 8 `var(--accent)` references → `var(--p-info)` (matches what the live `.counter--accent` rule already emits).
  - 40+ `var(--font-plain)` references → `var(--md-font-plain)`.
  - 13+ `var(--font-data)` references → `var(--md-font-data)`.
  - 4 declaration lines updated to match (the dark `:root` block has all three; the light `html[data-theme="light"]` block has the `--accent` override).
  - Total: 62 `var()` references + 4 declarations = 66 renamings across one HTML file.
  - The BEM class `counter--accent` is intentionally preserved (it's a class name, not a CSS variable — the `--accent` in `counter--accent` is part of the BEM modifier syntax, not a token reference).

- **[tests/spec_lifecycle/test_dashboard_mockup_parity.py:294](../tests/spec_lifecycle/test_dashboard_mockup_parity.py)** — `_MOCKUP_SHORTHAND_ALLOWLIST` collapses from 3 entries to `set()`. Comment block rewritten to explain the empty state is by design — kept as the single named extension point for any future renaming-pass shorthand drift. All 6 parity tests in the file still pass.

- **CHANGELOG / version** — `1.39.2` → `1.39.3` (PATCH per refactoring type).

Full suite: 1727 passed (same count as pre-spec — no behaviour change).

## Live smoke

```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://dual-research-alex.fly.dev/
200
```

The live deployed dashboard is byte-identical post-merge — the live renderer at `scripts/spec_lifecycle/render_dashboard.py` was already emitting canonical names; only the standalone-preview mockup file changed. The mockup's standalone preview (opened directly in a browser) renders identically because hex values + font stacks are unchanged — only token names are.

## Deploy notes

`fly deploy` hit the routine "machine not found" lease error during bluegreen rollout. **Unique to this deploy: the cluster converged on its own** — by the time the health-check wait loop exited, `fly status` already showed only 2 healthy v531 machines, no zombies. Running `bash scripts/sweep_stale_blues.sh` returned `no stale blues on dual-research-alex` (nothing to do). This is the cleanest deploy of the entire 11-spec drain today.

Either fly's orchestrator caught up faster on this last deploy or the deployment timing happened to dodge the lease-holder process. The spec-0193 fallback didn't get exercised here, but its 6 unit tests + the earlier two real-world identifications (specs 0195, 0196 deploys) cover the bug path comprehensively.

## What this DOES NOT do

- **Rename the mockup's other non-canonical tokens** (`--bg`, `--surface-*`, `--text-*`, `--info`, `--ok`, `--warn`, `--err`, `--idle`, `--hair`, `--hair-strong`, `--chart-*`). Per spec §5, those create no parity-test pressure and reshaping them would expand scope to "rewrite the whole mockup's token vocabulary."
- **Broaden the parity test's regex coverage.** Out of scope; remains as in spec 0184.
- **Touch the live renderer, the DS stylesheets, or any prototype mockup.** Risk-check confirmed no real consumers of the renamed tokens existed outside the dashboard mockup (other file matches were either BEM class names or self-declared tokens in unrelated prototypes).
- **Add per-theme `--p-info` to the canonical DS.** Out of scope; the mockup keeps its own per-theme override for standalone-preview continuity.

## Rebase note

PR #225's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as every prior spec in today's drain. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0197.jsonl`, force-with-lease-pushing, then admin-squashing.

## End of queue

Spec 0197 is the last queued spec in today's 11-spec drain. The queue is now
empty.
