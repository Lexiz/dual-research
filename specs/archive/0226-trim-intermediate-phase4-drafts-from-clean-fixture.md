---
kind: dev
spec: "0226"
slug: trim-intermediate-phase4-drafts-from-clean-fixture
title: "Refactor: trim intermediate phase4/draft-vN.md files from the clean anchor-run fixture"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: archived
depends_on: []
complexity: S
created: 2026-05-26
queued_at: "2026-05-26T21:22:16Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0226 — Refactor: trim intermediate phase4/draft-vN.md files from the clean anchor-run fixture

> **ARCHIVED — not shipped.** 2026-05-26 review concluded this spec is inert at runtime and not worth the diff. The verifier's `_TURN_FILE_RE` at [`src/dual_research/contract/verifier.py:70`](src/dual_research/contract/verifier.py:70) already filters `draft-vN.md` out of the turn-file set, so the seven 76-byte stubs in the clean fixture have no behavioral impact — the [spec 0225 implementer's own handoff](handoffs/2026-05-26-spec-0225-lifecycle-trace-verifier.md) flagged this follow-up as "cosmetic cleanup only" in its *Deferred during implementation* section. Standing project rule (CLAUDE.md, post-reclassification spec lineage): say "no" to low-value cosmetic follow-ups to break the accretion pattern that the project's recurring-bug diagnosis already flagged. The file remains in `specs/archive/` for the audit trail; the dashboard renderer ignores subdirectories so it will not be re-surfaced.

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — fixture-data cleanup, no behavior change
> **Evidence:** Spec 0225 handoff "Deferred during implementation" — the seven `draft-vN.md` files were left in the clean fixture under an ambiguous reading of spec 0225 §2.3's exclude list. Pure cosmetic; the verifier's turn-file parser already ignores them.

---

## 1. Current state

The clean-run fixture's `phase4/` directory carries seven 76-byte intermediate-draft stubs alongside the real `round-NN-{agent}.md` turn files:

- [`tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/phase4/draft-v2.md`](tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/phase4/draft-v2.md) — 76 bytes.
- `draft-v3.md` … `draft-v7.md` — same shape, 76-byte stubs each.
- `draft-v8.md` — 265 bytes (the final intermediate before run-root `final.md`).

[Spec 0225 §2.3](specs/0225-lifecycle-trace-verifier.md)'s exclude list reads: "Exclude: `phase1/`, `phase3/` (no item events), `inputs/`, **the assembled draft**, `searches/` audit bundles." The implementer recorded the ambiguity in [the 0225 handoff §"Deferred during implementation"](handoffs/2026-05-26-spec-0225-lifecycle-trace-verifier.md): "'The assembled draft' most naturally reads as the run-root `final.md` (the genuinely assembled artifact); the per-version `draft-vN.md` files are intermediate phase-4 turn artifacts." A strict reading of "the assembled draft" could extend the exclusion to every intermediate version — they are *also* assembled drafts, just at earlier rounds.

The verifier's turn-file parser is unaffected either way: [`src/dual_research/contract/verifier.py:70`](src/dual_research/contract/verifier.py) defines `_TURN_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")` — `draft-vN.md` names do not match the round-NN-agent shape, so they are never read for I4.4 or any other invariant. The files are inert in the verifier pipeline. They merely bloat the fixture surface and create one more thing a future fixture-curator has to decide about.

The other two corpus fixtures (`20260525-135006-backend-language-choice`, `20260526-102321-backend-language-choice`) do not have `phase4/` directories at all (silent-death runs that died before phase 4), so this cleanup currently applies only to the clean fixture.

## 2. Target state

The clean fixture's `phase4/` directory contains only the `round-NN-{agent}.md` turn files (the round-01 through round-08 pairs), matching the verbatim shape of what the verifier actually parses. The strict reading of [spec 0225 §2.3](specs/0225-lifecycle-trace-verifier.md)'s "the assembled draft" — extended to include intermediate per-version drafts — is the on-disk convention.

Files removed:

- [`tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/phase4/draft-v2.md`](tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/phase4/draft-v2.md)
- `…/phase4/draft-v3.md`
- `…/phase4/draft-v4.md`
- `…/phase4/draft-v5.md`
- `…/phase4/draft-v6.md`
- `…/phase4/draft-v7.md`
- `…/phase4/draft-v8.md`

Files preserved (`round-NN-{agent}.md`, the only files [`verifier.py:70`](src/dual_research/contract/verifier.py)'s `_TURN_FILE_RE` matches): the 16 turn files in the same directory.

The frozen `expected.json` baseline for this run is **unchanged** by definition — the verifier's turn-file enumeration filters by `_TURN_FILE_RE` before reading any file, so removing files that never matched cannot shift any verdict. The post-trim `verify_run` output equals the pre-trim output byte-for-byte for every invariant in §2.2 of spec 0225.

## 3. Stepwise migration

- **Step 1: Remove the seven files.** `git rm tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/phase4/draft-v*.md`. Single commit. No code changes.
- **Step 2: Confirm the verifier verdict is unchanged.** Run the snapshot test at [`tests/test_verifier.py:804`](tests/test_verifier.py) (`test_snapshot_clean_run_matches_baseline`) and the full `tests/test_verifier.py` suite. Both must pass against the existing `expected.json` without regenerating the baseline. If they do not pass, the assumption in §2 is wrong and the spec author was right to leave the files in — abort the cleanup and document the dependency in the test instead.

## 4. Behavior preservation

- [ ] [`tests/test_verifier.py:804`](tests/test_verifier.py) `test_snapshot_clean_run_matches_baseline` still passes — confirms `verify_run` on the trimmed clean fixture produces the same verdicts as the frozen `expected.json` baseline (no regeneration needed; the verifier's `_TURN_FILE_RE` at [`verifier.py:70`](src/dual_research/contract/verifier.py) already filters these files out).
- [ ] Full `uv run pytest tests/test_verifier.py -q` passes (covers all 22 invariants + all three snapshot fixtures + the CLI exit-code tests at `test_cli_exits_*`).
- [ ] Full `uv run pytest tests/ -q` passes — guards against any unrelated test that happened to glob `phase4/*.md` for the clean fixture.
- [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` still exits rc=0 with the frozen baseline (CLI smoke from the 0225 handoff §Verification, repeated here).

## 5. Out of scope

**Explicit: this spec adds no new feature.** No verifier behavior change, no new invariants, no schema migration, no UI work. Fixture-data cleanup only.

- **Trimming the other two fixtures' `phase4/`.** Neither `20260525-135006-backend-language-choice` nor `20260526-102321-backend-language-choice` has a `phase4/` directory today (silent-death runs that died upstream). If a future fixture grows a `phase4/` with intermediate drafts, the same trim convention should apply — but enforcing that pre-emptively is out of scope.
- **Codifying the exclude rule in a fixture-curation script or pre-commit hook.** The corpus is small and frozen; mechanically enforcing the rule has no payoff today. Revisit if the corpus grows past the three fixtures named in [spec 0225 §5](specs/0225-lifecycle-trace-verifier.md).
- **Amending [spec 0225 §2.3](specs/0225-lifecycle-trace-verifier.md) to spell out the strict reading.** The spec is shipped; this follow-up *is* the resolution of the ambiguity and the on-disk shape is now the authoritative reading.

## 6. Risks

- **Some unrelated test enumerates `phase4/*.md` without the round-NN filter and breaks when the seven files vanish.** Mitigation: §4's full-suite check (`uv run pytest tests/ -q`) catches this; abort the trim if it surfaces. The assumption is that only [`verifier.py:70`](src/dual_research/contract/verifier.py)'s `_TURN_FILE_RE` reads these directories, which a quick grep across the repo before the trim confirms.
- **Fixture-curator confusion if a future run is dumped into the corpus with intermediate drafts attached.** Mitigation: §5 names the convention. The handoff for this spec should reiterate it so the next corpus-extending spec inherits the rule.
- **`expected.json` accidentally regenerated and the diff hides a real verdict shift.** Mitigation: §3 step 2 explicitly forbids regenerating the baseline as part of this PR; if the snapshot test fails the spec aborts. The `regenerate_baseline()` helper at [`tests/test_verifier.py:900`](tests/test_verifier.py) is only for legitimate contract-change PRs (per the 0225 handoff §"Operational notes").
