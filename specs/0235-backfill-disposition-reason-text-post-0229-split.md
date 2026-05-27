---
kind: dev
spec: "0235"
slug: backfill-disposition-reason-text-post-0229-split
title: "Refactor: split `backfill_disposition.py` reason-text by spec-ID era so post-0229 specs no longer carry the misleading `Pre-spec-0229 carve-out` marker"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0229.1"]
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "deferred-from-0229.1"
promoted_from_draft: ""
disposition: defer
disposition_reason: "The disposition value itself is structurally correct; only the literal reason text is mildly misleading for a small post-0229 cohort, which makes this a polish item rather than a correctness item."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0235 — Refactor: era-aware disposition reason text in backfill script

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0229.1 (the backfill script this spec amends)
> **Bump:** PATCH — internal restructure of a one-off CLI's default-string logic; no behaviour change for the disposition value itself.
> **Evidence:** Spec 0229.1 handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:33`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:33) flags: *"The deterministic backfill stamps every retroactive entry with `\"Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention.\"`, including for specs queued after 0229 itself (the PR #270 case). The disposition value (`archive`) is structurally correct — 0232 was queued without triage intent — but the literal `\"Pre-spec-0229\"` phrasing isn't accurate for those specs."*

---

## 1. Current state

The backfill CLI at [`scripts/spec_lifecycle/backfill_disposition.py`](scripts/spec_lifecycle/backfill_disposition.py) inserts a single fixed `disposition_reason:` string into every spec/draft that doesn't already declare one. The string is hard-coded:

> `"Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."`

This works for the ~235 specs that predate spec 0229 (the doctrinal carrier of the disposition convention). But the script also fires on specs queued *after* spec 0229 itself that happened to omit the field — concretely, spec 0232 was queued mid-flight of PR #269 without the field and got the same retroactive reason via PR #270's hotfix backfill. The phrasing "Pre-spec-0229" is structurally false for 0232 since spec 0232 was queued at commit 1df9c8e, which post-dates the merge of spec 0229.

The handoff identified this and named two options:
- **(a)** keep the one-line marker (cheap, semantically OK, slightly inaccurate);
- **(b)** split the script into two paths — pre-0229 vs post-0229 — with different default reasons.

This spec ships path (b) since the script remains in-tree for any future audit pass per spec 0229.1 §2.3 and a future re-run on a wider scope would propagate the inaccuracy further.

## 2. Target state

`backfill_disposition.py` grows an era-detection helper. The era for a given spec file is determined by parsing the spec ID from the filename and comparing it to the cutoff: spec IDs `< 0229` use the legacy "Pre-spec-0229 carve-out" reason; spec IDs `>= 0229` (including decimal children like `0229.1`, `0229.2`, plus `0230+`) use the post-0229 reason:

> `"Post-spec-0229 carve-out queued without explicit disposition; backfilled to archive — see [spec 0235](specs/0235-backfill-disposition-reason-text-post-0229-split.md) for the policy split rationale."`

Implementation surface — [`scripts/spec_lifecycle/backfill_disposition.py`](scripts/spec_lifecycle/backfill_disposition.py):

1. Add `_era_reason(filename: str) -> str` helper. Parse the leading `NNNN` (and optional `.M`) from the filename via the existing `parse_spec_id` in [`scripts/spec_lifecycle/pick_next_number.py`](scripts/spec_lifecycle/pick_next_number.py) or a local regex; return the pre-0229 string for `< 229` and the post-0229 string for `>= 229`.
2. For drafts (`specs/drafts/draft-NNN-*.md`), use the post-0229 reason unconditionally — drafts are a newer construct and the pre-0229 phrasing wouldn't be accurate for any of them.
3. The insertion logic stays text-level (no yaml round-trip) per the spec 0229.1 §2.3 design intent. Only the choice of reason string changes; the field-insertion mechanics are untouched.
4. Update the existing tests in [`tests/test_spec_0229_1_validator_disposition.py`](tests/test_spec_0229_1_validator_disposition.py) (the idempotency test) — the test already asserts a specific reason string; it must be updated to test era selection: a synthetic spec named `9999-foo.md` gets the post-0229 reason; a synthetic spec named `0099-foo.md` gets the pre-0229 reason.

The existing in-repo backfilled specs are not re-touched — running the new logic against them would produce a diff (the post-0229 cohort's reason would change), but a retroactive re-stamp is itself a no-op for the operational lever (disposition value). Leaving them is the cheaper, lower-noise choice; future audit passes on the wider corpus will use the era-aware logic.

## 3. Stepwise migration

- **Step 1:** Add `POST_0229_REASON` module constant + `_era_reason(filename)` helper to [`scripts/spec_lifecycle/backfill_disposition.py`](scripts/spec_lifecycle/backfill_disposition.py). Verifies by: `python -m scripts.spec_lifecycle.backfill_disposition` run as a smoke check still reports "skipped — already had disposition" for all in-repo files (idempotency intact).
- **Step 2:** Update the existing idempotency test in [`tests/test_spec_0229_1_validator_disposition.py`](tests/test_spec_0229_1_validator_disposition.py) to assert era-based reason selection. Add two new test cases:
  - `test_backfill_uses_pre_0229_reason_for_low_spec_ids` — synthetic spec `0099-foo.md` gets the pre-0229 reason.
  - `test_backfill_uses_post_0229_reason_for_high_spec_ids` — synthetic spec `9999-foo.md` gets the post-0229 reason.
- **Step 3:** `uv run pytest tests/test_spec_0229_1_validator_disposition.py -q` — full file green.

## 4. Behavior preservation

- [ ] `disposition: archive` value is unchanged for every backfilled file. Only the reason text differs by era.
- [ ] The script remains idempotent — a second run still reports `0 backfilled / N skipped`.
- [ ] The in-repo invariant `test_no_existing_spec_fails_specifically_on_disposition` still passes — both era reasons are non-empty single-sentence strings and pass the validator's `_check_disposition_shape`.

## 5. Out of scope

**Explicit: this spec adds no new feature.** It restructures the default-reason logic inside a one-off CLI to be era-aware. The validator behaviour, disposition vocabulary, and backfill insertion mechanics are unchanged.

Specifically out of scope:

- **Re-stamping the post-0229 cohort in this commit.** Touching the existing files' reason text would produce a noisy diff for a non-operational field. The change applies only to future runs; the in-repo files keep their current pre-0229 marker. Future audit passes that re-run the script will pick up the era-aware reason naturally.
- **A configurable cutoff or era list.** The 0229 boundary is the only one that matters today; making it configurable would over-engineer a one-off script.
- **Tightening the "single sentence" heuristic in the validator.** The new post-0229 reason contains a markdown link with parentheses that could in principle confuse the period-count check; the existing heuristic at [`scripts/spec_lifecycle/validator.py:474-480`](scripts/spec_lifecycle/validator.py:474) tolerates this (the reason is one sentence by every reasonable reading, regardless of period count).

## 6. Risks

- **R1 — The post-0229 reason contains a markdown link with parentheses (`[spec 0235](specs/...)`).** The validator's "more than two periods" warning could fire if periods count beyond the heuristic. *Mitigation:* the new reason has exactly one period (the terminal one). The link contains a hyphen-separated path but no periods. Verified by counting: `"Post-spec-0229 carve-out queued without explicit disposition; backfilled to archive — see [spec 0235](specs/0235-backfill-disposition-reason-text-post-0229-split.md) for the policy split rationale."` — one period.
- **R2 — Era detection misclassifies a non-standard filename.** Filenames not matching `NNNN[.M]-slug.md` would fall through. *Mitigation:* the script already skips non-`*.md` files and the helper raises on parse failure — making the failure mode "loud script error during backfill" rather than "silent wrong era."
- **R3 — Drafts get the post-0229 reason but the drafts dir contains pre-0229-authored drafts that were never backfilled before spec 0229.1.** *Mitigation:* the existing in-repo drafts (`draft-001`, `draft-002`) were already backfilled by spec 0229.1 with the pre-0229 marker. This spec doesn't touch them. Any new draft authored after this spec ships gets the post-0229 reason, which is accurate.
