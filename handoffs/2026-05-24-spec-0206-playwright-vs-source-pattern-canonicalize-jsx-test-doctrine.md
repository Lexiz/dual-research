---
spec: "0206"
date: 2026-05-24
version: "1.44.5"
pr: "https://github.com/Lexiz/dual-research/pull/238"
kind: cycle-handoff
---

# Spec 0206 — Canonical UI test doctrine + shared source-pattern helpers (shipped v1.44.5)

Test PATCH that canonicalizes **source-pattern tests** (not Playwright / DOM) as the project's UI test doctrine for the JSX-loaded-via-babel runtime. Closes the deferred decision called out at `handoffs/2026-05-24-spec-0205-fix-p4-critique-card-five-visual-regressions.md:45` ("If the project ever stands up a Playwright harness, follow-up dev spec converts the 8 source-pattern tests to DOM tests against a fixture run."). The follow-up shipped here picks the *other* branch — keep source-pattern, document the rationale, codify the canonical idiom — and adds an authoring-time validator nudge so the silent path substitution that happened in spec 0205 gets surfaced at queue time instead.

Net diff: 11 files changed, 353 insertions(+) / 129 deletions(-) across 1 commit. Docs + helper module + validator nudge + two back-ported test files — no runtime / UI code change.

## State at deploy

- Both machines (`2870421c037148` and `2873d39cd92438`) updated to image `deployment-01KSCVZ…`. Rolling deploy on first try; the transient "app is not listening on the expected address" warning during boot is benign (smoke checks subsequently passed).
- `/api/health` returns `{"ok":true,"version":"1.44.5","backend":"supabase"}`.
- Tests: **1870 passed** (`uv run pytest tests/ -q`, 22.32 s). Same count pre- and post-back-port — no assertion semantic drift.
- Spec §4.2 acceptance scenarios verified:
  - **Scenario 1** — DS SPEC §13 reachable from `CLAUDE.md` "## Tests" via markdown link ✓.
  - **Scenario 2** — validator emits WARNING (not ERROR) on `tests/ui/*.py` mentions in `type: test` / `type: bug` specs (verified against `specs/0205-fix-p4-critique-card-five-visual-regressions.md` — fires; against `specs/0205.2-...md` — does not fire) ✓.
  - **Scenario 3** — helper imported in exactly two files (`grep -rn _ui_pattern_helpers tests/`) ✓.

## Deploy notes

Clean rolling deploy on first try — both machines acquired leases, updated, and reached good state. No spec-0200 matrix routing needed.

Post-deploy sweep: `bash scripts/sweep_stale_blues.sh` → `sweep: no stale blues on dual-research-alex`. Rolling-strategy primary tag filter found zero candidates (expected under rolling).

## What was changed

**New module:**

- `tests/_ui_pattern_helpers.py` — three functions (~90 lines including docstrings):
  - `read_repo_text(*parts)` — anchors at the test-package repo root, returns UTF-8 text.
  - `assert_jsx_contains(text, pattern, *, msg, flags=0)` — positive regex assertion; returns the match so callers can scope the search then assert inside the captured group.
  - `assert_jsx_lacks(text, pattern, *, msg, flags=0)` — antipodal-absence assertion; surfaces the matched snippet on failure.

**Documentation:**

- `design-system/SPEC.md` §13 — "UI test doctrine (spec 0206)" — three subsections:
  - §13.1 why source-pattern (not Playwright / DOM): the JSX-loaded-via-babel runtime has no module boundary; harness cost is disproportionate; Claude Preview MCP screenshot in the PR description is the runtime cross-check; spec 0179's 8-capture parity grid mandatory for ItemCard-touching specs.
  - §13.2 canonical shape: one test pair per anatomical contract (positive regex + antipodal-absence), file at `tests/test_spec_NNNN_<surface>.py`, helper idiom, Bug 3 of spec 0205 as the worked example.
  - §13.3 DOM/Playwright out of scope: explicit revisit trigger (if the runtime moves off `@babel/standalone` to a real build).
- `CLAUDE.md` "## Tests" — extended with a one-line UI doctrine summary linking to DS §13.

**Validator:**

- `scripts/spec_lifecycle/validator.py` — new `NON_CANONICAL_UI_TEST_PATH_RE` constant + `_check_ui_test_path_convention(spec_type, body)` helper. Emits a WARNING (not ERROR) when a `type: test` or `type: bug` spec body references a path under `tests/ui/*.py`. Wired into `validate_dev_spec` alongside the other §2.x checks.

**Tests (back-ported, no semantic drift):**

- `tests/test_spec_0205_critique_card.py` (8 tests) — dropped local `REPO_ROOT` + `_read()`; imports `read_repo_text`, `assert_jsx_contains`, `assert_jsx_lacks` from `tests._ui_pattern_helpers`. Bug 3 (the `mdi:link-variant` glyph parity across segment header + ReviewCard chip) uses the full canonical idiom — scope-then-assert inside the captured group, two anatomical checks per test. Bugs 1/2/4/5 keep their existing assertion shape but route reads through the helper.
- `tests/spec0172/test_critique_card_markdown_and_no_sid.py` (7 tests) — dropped pytest fixtures, replaced with module-level `read_repo_text` reads (scope="module" was the original fixture intent anyway). One test uses `assert_jsx_contains` for the `ItemCardCommentBody` function-body capture; others stay as substring `in` / `not in` checks (degenerate regex case — the doctrine explicitly accommodates simple substring asserts).

**Version + changelog:**

- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — 1.44.4 → 1.44.5 (PATCH per spec frontmatter).
- `CHANGELOG.md` — new `## [1.44.5] — 2026-05-24` section under `### Added` with bullet-by-bullet attribution.

## Reconcile

Clean pre-flight reconcile (no mechanical drift, no semantic drift). All 9 spec body citations resolved against current `main`.

## Out of scope (per spec §2.3, unchanged)

- Standing up a Playwright harness. Option (a) from the original deferral (port the 8 static tests to DOM) is rejected; the cost/value math is documented in DS §13.1 and the explicit revisit trigger is named in §13.3.
- Converting the existing static-pattern tests under `tests/spec0172/` and `tests/test_spec_0205_critique_card.py` to anything other than the new helper idiom. Behavior of those tests is preserved (15/15 pass pre- and post-back-port).
- Any change to the `tests/ui/` directory naming convention beyond the validator warning — the directory does not exist today and this spec does not create it.

## Notes on the cycle itself

Two non-fatal frictions worth flagging (not in scope for this spec to fix, both already have follow-up specs queued):

1. **Buffered-event drift on push-to-main writes.** Steps 8/9/11 emitted `cycle_started` / `preflight_ok` / `handoff_read` / `spec_read` / `planning_started` / `reconcile_complete` *without* `--push-to-main`. The step-12 `set --push-to-main` then read origin's snapshot, applied the in_progress delta, and pushed — losing the buffered local events. Dashboard timeline for spec 0206 will show 0 duration for pre-flight stages. Mechanism: the `queue_state` push-to-main plumbing snapshots origin before applying its diff; locally-buffered events aren't merged into the snapshot. The pre-flight events that *should* end up in the timeline get stomped. A follow-up should either (a) make `append-event` (no flag) write to a sidecar that the next push-to-main flushes, or (b) make every step-8-through-step-11 event use `--push-to-main` by default.
2. **Local-main hydration after `gh pr merge`.** `gh pr merge --admin --squash --delete-branch` succeeded on the remote but its post-merge local `git checkout main` failed because `dashboard/queue-state.json` was dirty (from local plumbing writes that ran *after* the last stash). The orchestrator recovered with a stash + `git pull --ff-only` + stash drop, but the friction is symmetric with the case spec 0210 already names: when local main and the queue worktree's working tree diverge from origin/main, the `gh pr merge` post-hooks can't hydrate cleanly. Spec 0210 will fix the broader pattern.

Both notes are observability-only — the spec landed clean, tests are green, and the merge + deploy completed end-to-end.
