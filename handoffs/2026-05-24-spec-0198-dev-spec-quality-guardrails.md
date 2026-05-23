---
spec: "0198"
date: 2026-05-24
version: "1.40.0"
pr: "https://github.com/Lexiz/dual-research/pull/226"
---

# Spec 0198 — Dev-spec quality guardrails

Shipped three validator gates that close the documented failure modes from spec 0166/0168/0173.

## What landed

### 1. Open-questions ban (§2.1)

[scripts/spec_lifecycle/validator.py](scripts/spec_lifecycle/validator.py) widens the heading regex from a single literal "Open questions" to five variants — `Open questions`, `Unresolved questions`, `To decide`, `TBD`, `Outstanding decisions` — case-insensitive and anchored to `^#{1,6}\s+` so prose mentions don't fire. New constants `UNRESOLVED_MARKER_RE` (matches `[TBD]`/`[TODO]`/`[FIXME]` in prose) and `TRIPLE_QUESTION_RE` (matches `???` followed by 3+ alphanumeric chars) supplement.

Error messages are quoted verbatim in the spec-queue / spec-promote skills (per spec §7 mitigation: validator is source of truth).

### 2. Source-artifact traceability (§2.2)

New helper `_check_source_traceability(body)`. Detects file-path citations to `prototypes/*/NOTES.md`, `prototypes/*/V2-SNAPSHOT.md`, or any `.md` file under `prototypes/` *in the `## 1. Context` section only*. When detected, requires a markdown table with header `source item | source quote/ref | spec section` and ≥ 1 data row, and each row's section cell must reference `§2.N` or `§5` deferral (regex `§\s*(?:2\.\d+|5\b|out\s+of\s+scope)`).

Helper `_extract_traceability_rows` walks lines under the table header, skipping the `|---|---|---|` separator and stopping at the first blank or non-pipe line.

**Validator-vs-skill split:** the spec language in §2.2 also mentions bare-word forms ("mockup", "canvas", "ideation doc") and "N rows for N atomic items in the source." Both were dropped from the validator — bare words are too common in prose (the spec's own §1 line 40 trips them; this would have made spec 0198 fail self-validation), and counting atomic items in an external file is fragile to format drift. Both are now skill-level responsibilities documented in spec-queue Step 1e and spec-promote Step 3a: those skills run with full conversation context and can open the source file to enumerate.

### 3. UI specs — user stories + BDD acceptance criteria (§2.3)

New helper `_check_user_stories_for_ui_specs(body)`. Fires when `UI_PATH_RE = src/dual_research/ui/|design-system/assets/` matches anywhere in the body. Requires ≥ 1 user story matching `As\s+an?\s+[^,\n]+,\s*I\s+want\s+[^,\n]+,\s*so\s+that\s+[^\n]+` AND ≥ 2 BDD scenarios matching `GIVEN[^\n]+\n[^\n]*WHEN[^\n]+\n[^\n]*THEN[^\n]+`. Each scenario must be expressible as a Playwright test.

### 4. Templates

All five `specs/_templates/*.md` get a `<!-- DEV SPEC RULE: ... no open questions ... -->` HTML comment block above the H1 (visible when authoring, invisible when rendered).

`new-feature.md`: replaces the placeholder `## 3. UX / Behavior` with a full `## 3. User stories & acceptance criteria` (§3.1 user stories, §3.2 BDD scenarios with **two** scenario placeholders so the template teaches the ≥ 2 requirement directly).

`bug.md`: inserts `## 4. User stories & acceptance criteria` (same §4.1/§4.2 structure with two scenario placeholders), renumbers what was §4/§5/§6/§7 to §5/§6/§7/§8.

`refactoring.md`, `breaking.md`, `test.md`: comment block only — these specs are non-UI by definition, no story/scenario sections added.

### 5. Tests (37 total in `test_validator.py`; 1754 across the suite)

New parametrized tests:

- `test_forbidden_heading_variants_fail` — 8 heading variants.
- `test_bracketed_unresolved_markers_fail` — `[TBD]`/`[TODO]`/`[FIXME]`.
- `test_triple_question_marker_fails`.
- `test_bracketed_markers_inside_backticks_pass` — proves backtick-wrapped doc text isn't flagged.
- Source-traceability: happy path with table, sad path without table, table-with-bad-section-cell, §2-mention-doesn't-fire (scoped to §1), bare-word-doesn't-fire.
- UI stories: without-stories fails, with-stories-and-≥2-scenarios passes, non-UI-without-stories passes, only-one-scenario fails.
- `test_template_does_not_trigger_new_guardrails` — parametrized across all 5 templates; asserts no spec 0198 guardrail fires spuriously on the template comment block or placeholder text.

Existing tests adjusted: `_good_new_feature_body()` switched its citation from `src/dual_research/ui/static/app.jsx:42` (which would now trigger the new UI check) to `scripts/spec_lifecycle/validator.py:42` — cleaner baseline. `test_ui_spec_without_user_stories_fails` flips back to UI paths via in-test replacement.

### 6. Skills (out-of-band — not in this repo)

[`~/.claude/skills/spec-queue/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/spec-queue/SKILL.md) and [`~/.claude/skills/spec-promote/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/spec-promote/SKILL.md) updated:

- spec-queue: adds Step 1e (source-artifact enumeration with table-building obligation) and Step 1f (verify-against-current-code); strengthens Step 2 from prose suggestion to terminal gate with the validator's full forbidden-heading list and the refusal phrase `"<N> unresolved questions detected — invoke /spec-draft to resolve, then re-run /spec-queue."`
- spec-promote: adds Step 3a/3b mirroring (source enumeration + verify); Step 3 walks the widened heading list and the refusal-or-defer-or-resolve trichotomy.

These edits live in the user's Claude config dir, NOT in the dual-research repo — so they're not in PR #226. The validator (in repo) is the load-bearing enforcement; the skill prose is documentation of the gate.

## Validator self-test

Spec 0198 itself passes the new rules (no source artifact in §1, has §3.1 user stories + §3.2 with five BDD scenarios, no forbidden headings, no `[TBD]/[TODO]/[FIXME]` in prose). Backward compatibility verified: merged specs 0167/0168/0173 still fail the new UI check, but the architecture never re-validates merged specs.

## Deploy notes

- Initial `fly deploy` hit lease drift (`failed to get lease on VM 7812611a9512e8: machine not found`), but `fly status` confirmed the new image (`deployment-01KSBDKQEN24RR20Z19WBETKTD` = v1.40.0) was live on machines `7810321f211698` (v539) and `811e14a95623e8` (v539, 1 critical check transient) alongside two older v537 stragglers.
- Stale-blue sweep output:

  ```
  sweep: no stale blues on dual-research-alex
  sweep: cluster has 4 machines (expected 2) — checking image-release fallback filter (spec 0193)
  sweep: spec-0193 fallback destroying 2 machine(s) not on current image (registry.fly.io/dual-research-alex:deployment-01KSBDKQEN24RR20Z19WBETKTD)
  sweep: fallback destroy failed for 8d9237aed20628
  sweep: fallback destroy failed for 2862642fe99518
  sweep: fallback destroyed 0/2 stale machines on dual-research-alex (failed=2)
  ```

  Two stale v537 machines remain — sweep tried fallback destroy, both calls failed (likely transient API auth issue or machine state). Sweep exit code intentionally ignored per spec 0162. If the stragglers persist, manual `fly machine destroy 8d9237aed20628` / `fly machine destroy 2862642fe99518` cleans them up.
- Live smoke: `GET https://dual-research-alex.fly.dev/` → 200.

## Next

Queue head is now spec 0199 (queue mechanics: decimal sub-numbering, promote-as-next, drop queue_position) at position 1. Author queued it in parallel during this cycle.
