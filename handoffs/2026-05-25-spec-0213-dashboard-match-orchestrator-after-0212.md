---
spec: "0213"
date: 2026-05-25
kind: post-deploy
version: "1.44.18"
pr: "https://github.com/Lexiz/dual-research/pull/249"
branch: spec/0213-dashboard-match-orchestrator-after-0212
merge_sha: df0524f0cdada71bcaf9cbf7a996557afd3841f5
---

# Spec 0213 — Collapse 11-stage timeline to 7 honest spans + decimal sub-spec treatment

PATCH refactor of the spec dashboard renderer to reflect /dev-next's actual
emission cadence after specs 0211 + 0212 landed. Zero orchestrator-behaviour
change; the spec was explicit that this restructures the *renderer* to fit
the events that already exist.

## What landed

**Timeline collapses from 11 single-event rows to 7 honest spans.** The
canonical row list in [stages.py:42-55](scripts/spec_lifecycle/stages.py:42)
and the JS mirror at
[render_dashboard.py:3556-3562](scripts/spec_lifecycle/render_dashboard.py:3556)
now encode `(start_event, end_event)` pairs:

| # | Row name      | start_event     | end_event            |
|---|---------------|-----------------|----------------------|
| 1 | Pre-flight    | `cycle_started` | `preflight_ok`       |
| 2 | Read & plan   | `handoff_read`  | `reconcile_complete` |
| 3 | Implement     | `branched`      | `implement_complete` |
| 4 | Test          | `tests_started` | `tests_green`        |
| 5 | Ship          | `pr_opened`     | `merged`             |
| 6 | Deploy        | `merged`        | `deployed`           |
| 7 | Handoff       | `deployed`      | `handoff_written`    |

`StageDef` gets explicit `start_event` + `end_event` fields (was just `event`).
`compute_stages` walks the pairs directly — `duration_seconds = end_ts - start_ts`
— and carries a legacy fallback so historical specs missing their start_event
fall back to the prior row's end_event as the start anchor. This was the
deciding constraint from §2.2: pages for already-shipped specs should still
render non-zero durations.

**`_note_for` consolidates** in
[stages.py:115-188](scripts/spec_lifecycle/stages.py:115) — the Read & plan
note merges handoff_read + spec_read + reconcile_complete into a single line;
Implement prepends the branch name; Ship combines pr_opened + merged.

**Metrics chart bucketing realigns 1:1** in
[render_dashboard.py:781-794](scripts/spec_lifecycle/render_dashboard.py:781).
The `_STAGE_GROUPS` table now mirrors `STAGES` row-for-row with the same
`(start, end)` pairs and a distinct `chart-*` token per row. A new consistency
test at [tests/spec_lifecycle/test_spec_0213_stages_groups_parity.py](tests/spec_lifecycle/test_spec_0213_stages_groups_parity.py)
makes drift between the two tables a CI failure.

**Decimal sub-spec affordance** lands across three surfaces via two small
helpers in
[render_dashboard.py:313-359](scripts/spec_lifecycle/render_dashboard.py:313):

- `_parent_id_for_decimal("0211.3") → "0211"`; returns `None` for plain ints.
- `_sub_spec_chip(spec_id)` emits `<span class="chip tone-neutral no-dot chip-sub-spec">↳ <a href="spec-0211.html">0211</a></span>` when applicable, empty string otherwise. Uses the existing chip primitive from `design-system/SPEC.md §6`; no new component, just a `chip-sub-spec` slot for spacing.
- `_sub_spec_modifier(spec_id, base)` appends `<bem-root>--sub-spec` to `base` for sub-specs. Derives the modifier from the FIRST class in `base` so the single CSS rule `.qrow--sub-spec .qrow__id { padding-left: 16px }` covers both queue-style and history-style rows.

Wired into `_render_hero_inflight` (chip + indent on the hero title),
`_render_all_specs` (chip + indent on the History row), and `render_spec_page`
(chip only on the H1 — no sibling rows to indent against per §6 Risks). JS
mirrors `subSpecChip` / `subSpecModifier` keep the 5s `/api/data` repaint
byte-identical to first paint.

**Doctrine comments** in both
[stages.py:13-19](scripts/spec_lifecycle/stages.py:13) and the JS `STAGE_DEFS`
block at
[render_dashboard.py:3548-3553](scripts/spec_lifecycle/render_dashboard.py:3548)
explicitly call out that Deploy + Handoff ticking simultaneously is correct
under spec 0212's buffer-events doctrine, not a bug.

**Mockup updated.** [dashboard/mockups/dashboard-redesign-v3-horizontal.html](dashboard/mockups/dashboard-redesign-v3-horizontal.html)
now reflects the 7-row anatomy so the structural-parity test in
[test_dashboard_mockup_parity.py](tests/spec_lifecycle/test_dashboard_mockup_parity.py)
stays green.

Files changed: 16 (13 modified + 3 new tests). +992 / -308 lines in the squash.

## Test changes

New tests:
- [tests/spec_lifecycle/test_spec_0213_stages_groups_parity.py](tests/spec_lifecycle/test_spec_0213_stages_groups_parity.py) — 3 tests: STAGES vs _STAGE_GROUPS label parity, (start, end) pair parity, chart-token distinctness.
- [tests/spec_lifecycle/test_spec_0213_bootstrap_stage_defs.py](tests/spec_lifecycle/test_spec_0213_bootstrap_stage_defs.py) — 3 tests: JS STAGE_DEFS post-fix triple-tuple shape, antipodal absence of pre-0213 labels (`Read handoff`, `Read spec`, `Branch`, `PR`, `Merge` standalone + two-tuple shape), computeStages indexes def[2] for the end-event check.
- [tests/spec_lifecycle/test_spec_0213_sub_spec_affordance.py](tests/spec_lifecycle/test_spec_0213_sub_spec_affordance.py) — 9 tests: helper units + render-time integration on all three surfaces + JS-mirror source-pattern + CSS rule presence.

Updated tests:
- [tests/spec_lifecycle/test_stages.py](tests/spec_lifecycle/test_stages.py) — rewritten to assert the 7-row anatomy, span durations, and legacy-fallback behaviour. Includes a deliberate fixture for the buffered-batch case (Read & plan must NOT absorb the gap between preflight_ok and the buffered handoff_read flush) and the spec 0212 doctrine case (Deploy + Handoff with shared end timestamps render zero-duration Handoff cleanly).
- [tests/spec_lifecycle/test_stages_new_tolerated_steps.py](tests/spec_lifecycle/test_stages_new_tolerated_steps.py) — `tests_started` graduated from tolerated to stage start_event. The test now asserts both the old guarantee (no unknown_events trip) and the new categorisation.
- Three dashboard parity / count tests updated from `== 11` to `== 7` / `_with_seven_steps`.

## Verification

- `uv run pytest tests/ -q` — 1935 passed (was 1916 pre-PR; +19 new tests across the three new files; updated tests stayed green).
- End-to-end render smoke against the live repo (214 specs + 1 draft): hero emits 7 `tl__step` nodes; 8 sub-spec rows + 8 sub-spec chips render across the History list; pre-0213 row labels (`Read handoff`, `Read spec`, `Branch`, `PR`, `Merge`) absent from output.
- `gh run watch 26398402222` — `status=completed conclusion=success`. deploy.yml ran the full pytest job, fly deploy, and post-deploy sweep against `dual-research-alex.fly.dev`.
- `curl https://dual-research-alex.fly.dev/` — HTTP 200. App version `1.44.18` live.

## Cycle observations

- **Queue-state merge conflict at `gh pr merge`.** My cycle-start commit
  (`17d1cd0`) included `dashboard/queue-state.json` in the bulk `git add`. By
  the time the merge call ran, main had advanced by ~10 `--push-to-main` calls
  during implementation and the squash-merge couldn't 3-way-merge the file.
  Resolved with a one-shot `git checkout origin/main -- dashboard/queue-state.json
  && git commit && git push`, then `gh pr merge` succeeded. The lesson: when
  the cycle-start commit lands code changes, `git add -A` is too broad —
  queue-state writes flow through plumbing and the branch should never carry
  modifications to that file. Worth investigating whether a `.gitattributes`
  merge=ours strategy on the file would let the skill keep using `git add -A`
  without this manual reconciliation, or whether the skill should explicitly
  exclude `dashboard/queue-state.json` from the cycle-start commit. **Logged
  as a follow-up** but not blocking — the recovery is one commit.
- **Reconciler "mechanical drift" was a cosmetic false positive.** The 21
  flags were all the spec body's bare-filename display labels in markdown
  links like `[render_dashboard.py:3468](scripts/spec_lifecycle/render_dashboard.py:3468)`.
  The reconciler matches the display label, not the href — but the hrefs all
  resolved to extant lines. Treated as clean. No actual file/line drift.
- **Spec 0212 buffer-events doctrine held cleanly.** Post-merge events
  (`deploy_started`, `deployed`, `deploy_health_check_ok`) all stayed local-
  only until step 23's atomic push-files-to-main. No deploy-main concurrency
  pivot fired; defensive block at step 20 stayed silent.

## Next

Queue is empty after this spec. Refactor noted in cycle observations re:
queue-state.json in cycle-start commits is a candidate for a future
process spec.
