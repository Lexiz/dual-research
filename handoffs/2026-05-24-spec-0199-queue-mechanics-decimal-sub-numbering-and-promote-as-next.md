---
spec: "0199"
date: 2026-05-24
version: "1.41.0"
pr: "https://github.com/Lexiz/dual-research/pull/227"
---

# Spec 0199 — Queue mechanics: decimal sub-numbering, /spec-next, drop queue_position

Shipped four §2 sections that re-architect how the queue knows what runs next, and retired the second-source-of-truth `queue_position` frontmatter field.

## What landed

### §2.1 — Decimal sub-numbering

[scripts/spec_lifecycle/pick_next_number.py](scripts/spec_lifecycle/pick_next_number.py) gains three new functions and updates `current_queue`:

- `SPEC_ID_RE = re.compile(r"^(\d{4})(?:\.(\d+))?-")` — captures parent + optional one-level decimal.
- `parse_spec_id(name_or_id)` — accepts either a bare ID (`"0170.1"`) or a filename stem (`"0170.1-slug"` / `"0170.1-slug.md"`). Returns `(parent_int, child_int)` with `child=0` for plain integers. Raises `ValueError("two-level decimal IDs are forbidden: …")` on `0170.1.1` and `ValueError("malformed spec id: …")` on anything else.
- `format_spec_id(parent, child=0)` — inverse: `(170, 0)` → `"0170"`, `(170, 1)` → `"0170.1"`.
- `next_decimal_child(specs_dir, parent)` — scans for `{parent}.*-*.md`, returns `f"{parent}.{max_child+1}"` (or `f"{parent}.1"` if none exist). Refuses to descend a level: `next_decimal_child(specs, "0170.1")` raises.
- `next_dev_number(specs_dir)` now ignores decimal children when computing the next integer. Specs `0170`, `0170.1`, `0171` → next-integer is `"0172"`, not `"0171.1"`.
- `current_queue(specs_dir)` return shape changed from `[(queue_position_int, fm), …]` to `[(spec_id_str, fm), …]`, sorted by `(parent, child)` tuple. `next_queue_position` is deleted entirely.

Sort key tuple ordering everywhere a queue sorts: `0170 → (170, 0)`, `0170.1 → (170, 1)`, `0170.2 → (170, 2)`, `0171 → (171, 0)`.

### §2.2 — `/spec-next <id>` skill (out-of-band)

[`~/.claude/skills/spec-next/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/spec-next/SKILL.md) is new. Re-IDs a queued integer spec as a decimal child of the currently in-flight spec so it runs next. Pre-flight: must run from `dual-research-author/`, refuses from queue worktree. Step 1 validates target is `status: queued` on `main`. Step 2 finds the single `status: in_progress` spec (refuses if zero or > 1). Step 3 calls `next_decimal_child` and plans the cascade — target itself becomes the first free child slot; any existing decimal children of the target line up sequentially after. Step 4 `git mv`s the spec file + the event sidecar + any matching handoff sidecars (typically zero for queued specs). Step 5 sweeps every spec for `depends_on:` references to the renamed `old_id`s and rewrites them to the new IDs. Step 6 validates each renamed file. Step 7 commits + pushes atomically: `spec: promote-as-next <new_target> (was <target>)<+ N children>`. Step 8 appends a `promoted_as_next` event. Step 9 reports. Refusal cases enumerated in the skill body cover: no in-flight, target not queued, target is decimal, in-flight is decimal, validator fails on renamed file.

Skill is CLI-only — no dashboard affordance for promote-as-next yet (§5 deferral). No session-title stamping; the user is in their authoring session.

### §2.3 — Smarter deferral decision in `/dev-next` step 25.5 (out-of-band)

[`~/.claude/skills/dev-next/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/dev-next/SKILL.md) step 25.5 subagent prompt template now carries a three-rule routing decision (first match wins, default = next-integer):

1. Item's title or context explicitly references the parent spec's slug, ID, or a `## 2.N` subsection of the parent → **decimal sub-spec** (`next_decimal_child('specs', 'NNNN')`).
2. Item is described as a "**should but didn't**" / "drop on the floor" / "left out" / "punted from this cycle" → **decimal sub-spec**.
3. Otherwise → **next-integer** (default, `next_dev_number('specs')`).

The subagent does NOT consult the user — it can't, by its `general-purpose` background-agent contract. The user reviews and re-routes via `/spec-next` after the fact. Decimal sub-specs get `depends_on: ["NNNN"]` automatically so the parent linkage is explicit in frontmatter.

The subagent's final report includes the routing-rule fired per item, e.g. "spec 0170.1 as decimal sub-spec of 0170 — rule a matched (referenced parent §2.3)" or "spec 0245 as next-integer (default — no continuation signal)".

### §2.4 — Drop `queue_position` from the contract

`queue_position` is removed everywhere:

- [scripts/spec_lifecycle/pick_next_number.py](scripts/spec_lifecycle/pick_next_number.py): `next_queue_position` deleted; `current_queue` no longer reads the field.
- [scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py): emits a soft warning ("`queue_position` is deprecated; remove from frontmatter — queue order is intrinsic to the spec ID") if the field reappears in newly-authored frontmatter. Two new filename checks: `SPEC_FILENAME_RE` (`^\d{4}(?:\.\d+)?-[a-z0-9-]+\.md$`) for canonical grammar; `SPEC_FILENAME_TWO_DECIMAL_RE` for the dedicated two-level rejection message.
- [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py): `SpecRow.number` returns the full ID including decimal (was `path.stem[:4]`, which would have truncated `0170.1-slug` to `0170.`). New `SpecRow.sort_key` returns `(parent, child)`. Every `int(s.number or "0")` and `int(s.fm.get("queue_position") or 999)` swapped over to `s.sort_key`. Queue-row template renders 1-based rank derived from the already-sorted order (no `queue_position` field). JS half gains `parseSpecId` + `compareSpecId` helpers; `parseInt(b.number, 10)` comparator and `(a.queue_position || 999) - (b.queue_position || 999)` sorts both rewired.
- [functions/api/data.js](functions/api/data.js): regexes admit `\d{4}(?:\.\d+)?` in spec / handoff / event-sidecar filenames; `extractNumber` for specs captures the decimal segment.
- Skills at `~/.claude/skills/{spec-queue,spec-promote,dev-next}/SKILL.md` (out-of-band): stop calling `next_queue_position`, stop writing `queue_position` to frontmatter, and `/dev-next` step 24's re-rank sub-clause is gone.
- Templates [specs/_templates/{new-feature,bug,refactoring,test,breaking}.md](specs/_templates/new-feature.md) lose the `queue_position: 0` line.
- [CONTRIBUTING.md](CONTRIBUTING.md) replaces the `queue_position: <int, …>` line with a note that queue order is intrinsic to the spec ID.

Hook update at [`~/.claude/hooks/cleanup-session-prefixes.py`](file:///Users/alexlisitzky/.claude/hooks/cleanup-session-prefixes.py) — the lifecycle-prefix regex widens from `^(\d{4})$` to `^(\d{4}(?:\.\d+)?)$` so `[DR · 0170.1 · O]` and `[DR · queue · 0170.1 in flight · O]` parse correctly. The downstream `_derive_status_from_spec` glob `f"{spec_id}-*.md"` already handles decimals natively, so no further code change was needed.

### Bulk-strip

50 existing spec frontmatter blocks that still carried `queue_position:` got the field stripped in a dedicated mechanical commit (`chore: strip deprecated queue_position from existing spec frontmatter (spec 0199 §2.4)`). Spec 0199's own queue_position was stripped as part of the in-progress flip earlier in this cycle. The 198 → 50 number difference is because most older specs (pre-0152) never carried the field.

### Tests

- New [tests/spec_lifecycle/test_pick_next_number.py](tests/spec_lifecycle/test_pick_next_number.py) suite covers `parse_spec_id` / `format_spec_id` round-trip for integers + decimals + two-level rejection + malformed input; `next_decimal_child` first / increment / decimal-parent rejected; `next_dev_number` skipping decimal children; `current_queue` interleaving `[0170, 0170.1, 0171]` and ignoring lingering `queue_position`.
- New [tests/spec_lifecycle/test_render_dashboard_spec_0199.py](tests/spec_lifecycle/test_render_dashboard_spec_0199.py) covers `SpecRow.number` + `sort_key` for decimal IDs; renderer no-crash on `int("0170.1")` regression at the old line 1629; full-render decimal-interleaved queue order.
- Additions to [tests/spec_lifecycle/test_validator.py](tests/spec_lifecycle/test_validator.py): canonical decimal filename passes; two-level decimal fails with dedicated message; non-canonical filename fails; `queue_position` in frontmatter warns (not errors); absent `queue_position` emits no warning. The 21 existing fixture paths under `tmp_path / "spec.md"` got renamed to `tmp_path / "0156-thing.md"` so the new canonical filename gate doesn't trip them.
- [tests/spec_lifecycle/test_queue_drain_supervisor.py](tests/spec_lifecycle/test_queue_drain_supervisor.py)'s `_write_spec` helper stops writing `queue_position` (kwarg kept for back-compat call sites with `del queue_position` noop).
- [tests/js/dashboard-bootstrap.test.js](tests/js/dashboard-bootstrap.test.js) + [tests/js/staleness-chip.test.js](tests/js/staleness-chip.test.js) fixtures drop `queue_position`.

Full Python suite: **1774 passed** (same count as pre-spec). Full JS suite: **10 passed** (vitest) — `parseSpecId`/`compareSpecId` exercised via the bootstrap-render path.

## Deploy notes

- Initial `fly deploy` hit lease drift (`failed to get lease on VM 8e612ea77e0d18: machine not found`) on the v546 attempt — same pattern as spec 0198. Per `project_fly_lease_drift_recovery`, checked `fly status` afterward: a follow-up v547 release shipped successfully (`deployment-01KSBG78BJXZRKMQTKFZQ1R4RY`) less than a minute later from `alex.lisitzky@gmail.com`, almost certainly the GitHub Actions auto-deploy triggered by the merge to main. v547 ran the post-merge commit, so the v546 lease failure is functionally inert.
- Stale-blue sweep output: `sweep: no stale blues on dual-research-alex` — the v545 machines that lingered briefly during v547's bluegreen cutover were cleaned up by fly itself before the sweep ran.
- Live smoke: `GET https://dual-research-alex.fly.dev/` → 200.

## Next

Queue head is now spec 0200 (fly-deploy-simplification) at position 1, followed by spec 0201 (branch-and-safety-hygiene). Both queued in parallel during this cycle. The queue-mechanics groundwork shipped here means future deferral routing can drop a `0200.1` ahead of unrelated 0202+ if the deferral subagent decides it's tightly coupled.
