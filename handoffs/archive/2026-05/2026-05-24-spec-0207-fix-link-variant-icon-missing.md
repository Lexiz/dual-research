---
spec: "0207"
date: 2026-05-24
version: "1.44.6"
pr: "https://github.com/Lexiz/dual-research/pull/239"
kind: cycle-handoff
---

# Spec 0207 — Fix: link-variant icon missing from registry (shipped v1.44.6)

Bug PATCH that adds `'link-variant'` to the ICONS dict at [src/dual_research/ui/static/icons.jsx:55](src/dual_research/ui/static/icons.jsx). The five existing `<Mdi name="link-variant" />` call sites — P4 ItemCard head evidence-needed chip, P4 ItemCard sources segment header, P3 ReviewCard head Sources chip, plus two lifecycle-footer chips (`source-requested` / `source-provided`) — were rendering the open-square placeholder rect at [src/dual_research/ui/static/icons.jsx:103-108](src/dual_research/ui/static/icons.jsx) because the key was never registered. SVG path is the canonical MDI 7.x `link-variant` artwork, copied verbatim from the existing `'link'` key which already stored the same path data under a confusingly-named slot.

Net diff (post-squash): 7 files changed, 136 insertions(+) / 6 deletions(-) — registry entry + two regression tests + version bump + CHANGELOG.

## State at deploy

- Both machines (`2873d39cd92438` then `2870421c037148`) updated to the v1.44.6 image. Rolling deploy succeeded on first try; the "app is not listening on the expected address" warning during boot is the benign Fly framing issue noted in prior handoffs (smoke checks subsequently passed).
- `/api/health` returns `{"ok":true,"version":"1.44.6","backend":"supabase"}`.
- Tests: **1872 passed** (`uv run pytest tests/ -q`, 22.09 s). 1870 pre-change + 2 new.
- Spec §4.2 acceptance scenarios:
  - **Scenario 1** (evidence-needed chip path prefix) — locked in by `test_link_variant_resolves` asserting `'link-variant':` resolves to a non-empty path; the path stored is bit-identical to the existing `'link'` key whose prefix is `M10.59,13.41C11,13.8`, satisfying the scenario's asserted prefix.
  - **Scenario 2** (sources segment header) — same Mdi primitive call site reads the same key; the static test covers all five call sites uniformly.
  - **Scenario 3** (no placeholder-rect Mdi fallbacks in critique surfaces) — covered by `test_no_call_site_uses_missing_icon` which globally asserts every `<Mdi name="X" />` reference in the static JSX tree resolves to a registered key. Stronger than the spec's per-class-prefix assertion.

## Deploy notes

Clean rolling deploy on first try — both machines acquired leases, updated, reached good state. No spec-0200 matrix routing needed.

Post-deploy sweep: `bash scripts/sweep_stale_blues.sh` → `sweep: no stale blues on dual-research-alex`. Rolling-strategy primary tag filter found zero candidates (expected under rolling).

## What was changed

**Icon registry:**

- `src/dual_research/ui/static/icons.jsx` — one new key added to the `ICONS` dict in the "Content / docs" section, immediately after `'link'`:
  ```js
  'link-variant':    'M10.59,13.41C11,13.8 11,14.44 ... 13.41,9.17Z',
  ```
  Path is bit-identical to the existing `'link'` entry. No other dict keys touched; no call site changes (the five `<Mdi name="link-variant" />` invocations begin resolving the moment the key exists, per spec §3).

**Regression tests:**

- `tests/test_spec_0207_icon_registry.py` (new file, two tests):
  - `test_link_variant_resolves` — `assert_jsx_contains` on the ICONS file text asserts the `'link-variant':` key exists with a non-empty single-quoted value.
  - `test_no_call_site_uses_missing_icon` — parses the ICONS dict keys (`_ICONS_KEY_RE`) and every `<Mdi name="X" />` invocation across `src/dual_research/ui/static/*.jsx` (`_MDI_REF_RE`), asserts every referenced name is in the key set. Generalises the regression: any future caller using an un-registered name fails CI rather than reaching production as a blank rounded square.

**Version + changelog:**

- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — 1.44.5 → 1.44.6.
- `CHANGELOG.md` — new `## [1.44.6] — 2026-05-24 / ### Fixed` section.

## Reconcile

Pre-flight reconciler reported 4 mechanical drift items — all the same shorthand pattern `[icons.jsx:N](src/dual_research/ui/static/icons.jsx)` where the link text omitted the `src/dual_research/ui/static/` path prefix. The URL portion of every link was already correct (the markdown links worked); only the visible link text was loose. Patched via global replace of `[icons.jsx:` → `[src/dual_research/ui/static/icons.jsx:` in the spec body, re-reconciled to 13 clean / 0 drift, committed as `spec(0207): reconcile against main` on `main` before branching. No semantic drift.

## Deviation from spec body

- **Test file path** — the spec §5 names `tests/ui/test_icon_registry.py`; this cycle wrote the file at `tests/test_spec_0207_icon_registry.py` following spec 0206's canonical UI test doctrine (`tests/test_spec_NNNN_<surface>.py`, see [`design-system/SPEC.md` §13](design-system/SPEC.md) and the `## Tests` section of `CLAUDE.md`). The spec 0206 validator warned about this exact mismatch at queue time; the path substitution here is the doctrine resolving the warning. Test contents are identical in spirit (same two assertions, same regex patterns) — only the on-disk path moved. No `tests/ui/` directory was created.

## Cycle notes

One non-fatal friction worth flagging:

- **`dashboard/queue-state.json` merge conflict on first `gh pr merge` attempt.** The orchestrator staged the queue-state file alongside the code edits when committing the implementation, but origin/main had subsequently advanced via `--push-to-main` events (`tests_green`, `pr_opened`, `merged`). The squash-merge conflict was resolved by checking out `origin/main`'s `dashboard/queue-state.json` onto the branch and pushing a follow-up `spec(0207): sync dashboard/queue-state.json to origin/main` commit before retrying the merge. The retry succeeded fast-forward. Mechanism: queue-state is a push-to-main concern and should not be staged with branch commits. Worth a follow-up to either (a) auto-stash queue-state.json edits before branch commits, or (b) add a pre-commit hook that refuses to stage `dashboard/queue-state.json` from a feature branch. Not in scope for this spec to fix.

## Out of scope (per spec §7, unchanged)

- Renaming the existing `'link'` key (currently holds link-variant artwork). Deferred to a follow-up DS-cleanup if the duplicate-artwork ambiguity ever causes confusion.
- Proactive jsx-tree sweep for other `<Mdi name="X" />` invocations with missing keys. The new generalised test catches the entire class — CI surfaces any future case.
- Playwright DOM-render check that no fallback rect placeholders remain in the live page. Source-pattern tests cover the bug class without browser overhead; live DOM assertion is a follow-up.
- General "all DS-mandated icons present" audit cross-referencing every `mdi:*` in `design-system/SPEC.md` against the registry. Separate larger concern.
