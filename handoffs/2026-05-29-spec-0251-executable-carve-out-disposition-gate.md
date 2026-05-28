---
spec: "0251"
date: 2026-05-29
version: 1.62.0
pr: https://github.com/Lexiz/dual-research/pull/289
kind: post-deploy
---

# Spec 0251 — Make the carve-out disposition gate executable in the queue picker

**Shipped v1.62.0** (MINOR, `new-feature`). PR [#289](https://github.com/Lexiz/dual-research/pull/289), merged `7a487bf`, deployed via GH Actions `deploy.yml` (run 26607615184, green). Live app responds 200.

## What landed

CLAUDE.md's doctrine — *"a carve-out reaches `/dev-next` only when its disposition is `ship`"* — was enforced by nothing. The queue picker filtered on `kind == "dev" and status == "queued"` only. Spec 0251 makes the gate **executable** and expands it from carve-out-only to **all** queued dev specs.

- **§2.1 — gate the picker.** [`pick_next_number.py`](scripts/spec_lifecycle/pick_next_number.py): `current_queue` now additionally requires frozen-frontmatter `disposition == "ship"`. The gate logic lives in a new `_partition_queued(specs_dir) → (runnable, skipped)` helper; `current_queue`'s `[(spec_id, fm), …]` signature is unchanged so `queue_drain_supervisor` and all existing tests keep working.
- **§2.2 — never drop silently.** New companion `skipped_queued_specs(specs_dir)` returns the queued specs excluded for `disposition != "ship"`. `/dev-next` step 6 (SKILL.md) now logs `skipped N queued specs (disposition≠ship): [ids]`. The dashboard gains a **Parked** lane on both surfaces:
  - [`render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py): new `_is_runnable_queued` / `_is_parked` classifiers, a `SpecRow.disposition` property, a Parked column in `_render_pipeline`, and a `.pipe__bar--parked` CSS token (reuses `--p-warn`, no new token). The "Queued" lane now counts only runnable specs.
  - [`functions/api/data.js`](functions/api/data.js): per-spec `runnable_queued` / `parked` derivation in the queue-state overlay block — parity twin of the Python classifiers.
- **§2.3 — honest status.** [`validator.py`](scripts/spec_lifecycle/validator.py): `parked` added to `VALID_STATUSES` (a non-runnable authoring status). The `/dev-next` step 24.5 deferral subagent template, `/spec-queue`, and `/spec-promote` skills now set `status` from disposition (`ship` → `queued`, else `parked`), so frozen frontmatter stops lying with `queued`.
- **§2.4 — doctrine + cleanup.** [`CLAUDE.md`](CLAUDE.md) updated: the gate is executable and applies to all queued dev specs (any spec without explicit `disposition: ship` is un-runnable until promoted — the intended fail-safe, never silent). Fixed step-number drift in [`deferrals.py`](scripts/spec_lifecycle/deferrals.py) docstring (`25.5` → `24.5`).

## Tests

New [`tests/test_spec_0251_disposition_gate.py`](tests/test_spec_0251_disposition_gate.py) — gate inclusion/exclusion (ship vs archive/defer vs missing), skip collector, decimal IDs, signature preservation, validator `parked` accept + bogus reject, dashboard Parked-lane functional (render_dashboard) + source-pattern parity (data.js), and skill skip-when-absent contract (step 6 skip-log, step 24.5 status-from-disposition). Existing `current_queue`/supervisor fixtures updated to carry `disposition: ship` (their intent — overlay/ordering — is orthogonal to the gate). **Full suite: 2406 passed.**

## Skill-file edits (outside the repo, not in the PR)

Per the established pattern (specs 0211/0247), the `/dev-next`, `/spec-queue`, and `/spec-promote` SKILL.md files at `~/.claude/skills/` were edited to match §2.2a/§2.3. Source-pattern tests read them directly with skip-when-absent guards.

## Notes for the next session

- The live queue currently has no other `queued` spec. Any future spec authored without `disposition: ship` will be skipped by the gate and surface in the dashboard **Parked** lane + the step-6 skip-log — by design.
- The deploy run logged GitHub cache `Failed to save/restore` warnings — these are GitHub Actions infrastructure hiccups, not deploy failures; both `Deploy to fly.io` and `Sweep stale blue machines` steps were green.
