---
spec: "0230"
date: 2026-05-27
version: "1.50.0"
pr: "https://github.com/Lexiz/dual-research/pull/271"
---

# Spec 0230 — Reconciler: skip out-of-tree prefix paths

Deployed to https://dual-research-alex.fly.dev/ — `/api/health` returns `{"ok":true,"version":"1.50.0","backend":"supabase"}`.

## What landed

- **`scripts/spec_lifecycle/reconcile.py` — new `OUT_OF_TREE_PREFIXES` constant + new `out_of_tree` bucket.** A module-level `OUT_OF_TREE_PREFIXES: tuple[str, ...] = ("cowork/",)` sits adjacent to `CITATION_RE` / `LINK_DISPLAY_RE`. `reconcile_spec` grows an `out_of_tree_prefixes=` kwarg (defaulting to the module constant) so callers needing a different set can override per-invocation. The classification loop fires the prefix check before the on-disk existence check (spec §2.3), routing matches into a new `ReconcileReport.out_of_tree: list[Citation]` field with `classification="out_of_tree"` and `note="path begins with skip-list prefix; not classified against tree"`. `has_drift` and `has_blocking_drift` are unchanged — `out_of_tree` is purely informational. `format_report` surfaces a `"out-of-tree (informational): N"` line plus per-citation detail, ordered after `clean:` and before `mechanical drift:`. The module docstring updated to document four buckets instead of three.
- **`Citation.classification` string-enum grows `"out_of_tree"`** alongside the existing `clean / mechanical / semantic / unknown`. Backwards-compatible — existing readers that only inspect the three classifying buckets see no behavioural change beyond fewer entries in `semantic` for cowork-citing specs.
- **Regression target verified.** `python -m scripts.spec_lifecycle.reconcile specs/0229-addressee-obligation-invariant.md` now exits 0 (pre-fix: 3); the three prior `semantic` hits on `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:NNN` now surface under `out-of-tree (informational):`. Same exit-0 verified for `specs/0227-reclassify-contract-amending-specs-and-process-rule.md`.
- **`CHANGELOG.md` + version bump → 1.50.0.** `## [1.50.0] — 2026-05-27` section directly under `## [Unreleased]`, single `### Added` bullet citing this spec. `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock`, and `src/dual_research/ui/static/version-notes.json` (regenerated via `scripts/build_version_notes.py`) all moved to 1.50.0 in lockstep.
- **Tests at [`tests/test_spec_0230_reconciler_out_of_tree.py`](tests/test_spec_0230_reconciler_out_of_tree.py) (new, 11 tests).** Unit coverage for the four routing cases (default match / default non-match / custom prefix override / empty prefix list = pre-fix baseline); the trailing-slash sibling-dir guard from §7 R3 (`cowork-design-system/` does NOT match `cowork/`); source-pattern lock-in for the `OUT_OF_TREE_PREFIXES` constant (positive regex) and for the prefix-check-before-existence-check ordering inside `reconcile_spec` (positive + ordering assertion via `body.find` positions); runtime check that `OUT_OF_TREE_PREFIXES == ("cowork/",)` (catches sitecustomize-style import-time mutation); subprocess integration test that re-runs the reconciler on spec 0229 and asserts exit 0 + the `out-of-tree (informational):` line appears in stdout; `has_blocking_drift` invariant across multiple out-of-tree hits; CHANGELOG/version smoke (1.50.0 section exists, references spec 0230).
- **Full suite green**: `uv run pytest tests/ -q` → 2164 passed in 30s.

## Cycle notes

- **Bootstrap override at pre-flight reconcile.** Spec 0230 fixes the false-positive class that was blocking spec 0230's own pre-flight reconcile — 6 semantic-drift hits on spec-body example strings (the §6 unit-test fixtures + §1 memory pointer + §7 R3 hypothetical sibling-dir reference + §6 test 3 `../external/notes.md` + the 3 cowork citations the spec is designed to skip). The operator-override pattern documented on specs 0227.1 and 0229 was applied with verdict `"override — 6 false positives matching the bug being fixed by this spec; regression-asserted by the implementation"`. After the fix landed, the `cowork/`-prefixed pair routes to `out_of_tree`; the remaining 4 example paths still classify as `semantic` (correctly — they're test-plan inverse-case examples). The acceptance criteria in spec §3 target the operational regression on specs 0229 and 0227 explicitly, both verified exit 0.
- **No deploy flake this cycle.** GH Actions deploy.yml run [26511086768](https://github.com/Lexiz/dual-research/actions/runs/26511086768) ran clean — test job 38s, deploy job 40s, single push. The `Failed to save / Failed to restore` cache annotations are GH-side ephemeral; unrelated to the fly deploy itself.
- **Local queue-state lag during the cycle is normal.** Several `--push-to-main` calls advanced `origin/main` past the queue worktree's detached HEAD between the merge and the final atomic `push-files-to-main`. The branch-identity assertion + verified-delete + re-detach at step 19 (spec 0212) resolved cleanly without any worktree thrash.

## Deferred during implementation

Nothing significant deferred this cycle. The two follow-ups worth noting are pre-existing and out-of-scope per spec §5:

- **Verifying that out-of-tree paths exist relative to the spec's parent directory** (`../cowork/...`) — deferred per §5; would require path resolution + filesystem call per citation with no rollback story when `/dev-next` runs from a different worktree. Already in scope of a future spec if/when `cowork/` becomes git-tracked.
- **CLI flag (`--out-of-tree-prefixes`) to override the default per-invocation** — deferred per §5; the default `("cowork/",)` covers 100% of observed cases over two cycles. Adding the flag invites premature configurability.

Both are explicitly anchored in the original spec's `## Out of scope` section, not "should-but-didn't" carve-outs — no follow-up spec is owed.
