---
kind: dev
spec: "0227"
slug: reclassify-contract-amending-specs-and-process-rule
title: "Refactor: reclassify 4 contract-amending specs (0137 / 0140 / 0218 / 0219) from `bug` + add CLAUDE.md contract-change process rule"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: 1.46.1
status: queued
depends_on: []
complexity: S
created: 2026-05-26
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0227 — Refactor: reclassify 4 contract-amending specs + add CLAUDE.md contract-change process rule

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH (1.46.0 → 1.46.1) — docs/metadata only, no source-code behaviour change
> **Evidence:** Cowork synthesis [`2026-05-26-logic-cutoff-synthesis.md`](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) §1.4 + §4 + §6 action 5 identify spec mislabeling as the root cause of the "we keep going in circles" feeling. Four specs filed as `type: bug` actually amended the 0114 contract (added behaviour). The 0226 debrief at [`2026-05-26-spec-0226-recommendation.md`](../cowork/feedback/2026-05-26-spec-0226-recommendation.md) §5 surfaced a sixth invariant (verifier-invariants count as contract changes too) that closes the implementation-cycle drift gap.

---

## 1. Current state

### 1.1 Source traceability

Every atomic item from the cited Cowork artifacts is accounted for below. Silent drops are a validator failure (spec 0198) — every row maps to a §2.N section that ships in this spec, with no deferrals.

| source item | source quote / ref | spec section |
|---|---|---|
| synthesis §1.4 — "the root cause of the recurring-bug feeling is the mislabeling itself" | [synthesis.md:50-54](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §1.3 Motivation |
| synthesis §4 row 0137 — "Adds the `via_artifact_promotion` convergence path + new event; 0114 explicitly retired escape valves, so this *amends* the contract." | [synthesis.md:227](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §2.1 0137 edits |
| synthesis §4 row 0140 — "Adds a one-agent-AGREED convergence trigger that 0114's 'both AGREED' rule did not permit." | [synthesis.md:228](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §2.2 0140 edits |
| synthesis §4 row 0218 — "Introduces a wholly new phase-4 drafter sub-protocol (section deltas, STATUS-first ordering, max_tokens→parse-failure)." | [synthesis.md:229](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §2.3 0218 edits |
| synthesis §4 row 0219 — "Adds a new `EDIT_SECTION` op kind, heading-mismatch hard-fail, and a new persisted `phase4_round` field." | [synthesis.md:230](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §2.4 0219 edits |
| synthesis §4 process-rule note — "a spec that changes convergence, lifecycle, categorisation, or phase semantics must carry a `feature`/`breaking` label … A `bug` label asserts 'no contract change' — and should be reviewable on exactly that claim." | [synthesis.md:235-237](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §2.5 CLAUDE.md addition |
| synthesis §6 action 5 — "Reclassify §4 spec frontmatter + add the process rule. *Acceptance:* 0137/0140/0218/0219 relabeled; CLAUDE.md states 'contract-changing specs may not be labeled `bug`.'" | [synthesis.md:279-280](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) | §7 Acceptance |
| 0226 debrief §5 verifier-invariant addendum — "spec 0225 shipped with **22 invariants**, 3 more than the 19 we agreed … does CLAUDE.md's contract rule apply during implementation too, or only at spec-authoring time?" (Cowork's 6th-bullet ask) | [2026-05-26-spec-0226-recommendation.md:47-53](../cowork/feedback/2026-05-26-spec-0226-recommendation.md) | §2.5 CLAUDE.md addition — bullet 6 (verifier invariants) |

### 1.2 Current frontmatter on the four target specs

Verified by reading each file at HEAD = `dae45a6`. Two of the four use the older frontmatter schema (`label:` only, no `type:` field, `version-bump:` with hyphen); two use the current schema (`type:` + `label:`, `version_bump:` with underscore). The per-spec edits in §2 distinguish *add* from *update* and *rename* accordingly — this is the most important precision in this spec, because a naive `s/bug/new-feature/` would either miss the `type:` field on 0137/0140 or leave `version-bump:` (hyphen) in place where the lifecycle tooling expects `version_bump:` (underscore).

- [`specs/0137-substantive-convergence-escape-valve.md:1-10`](specs/0137-substantive-convergence-escape-valve.md) — old schema. Has `label: bug` and `version-bump: PATCH`. No `type:` field. No `kind: dev`, `slug:`, `complexity:`, `queued_at:`, etc. — predates dev-spec frontmatter standardisation.
- [`specs/0140-phase4-deadlock-extractor-and-escape-valve.md:1-10`](specs/0140-phase4-deadlock-extractor-and-escape-valve.md) — old schema. Same shape as 0137. (Note: actual filename ends `-and-escape-valve.md`, not `-escape-valve-breadth.md` as the original briefing prompt described; the underlying spec is the same — the "breadth" framing comes from the spec body.)
- [`specs/0218-phase4-status-survives-truncation.md:1-22`](specs/0218-phase4-status-survives-truncation.md) — current schema. Has `type: bug`, `label: bug`, `version_bump: PATCH`.
- [`specs/0219-phase4-section-delta-contract-v2.md:1-22`](specs/0219-phase4-section-delta-contract-v2.md) — current schema. Same shape as 0218.

All four are at `specs/` (none in `specs/archive/`).

### 1.3 Motivation

Per synthesis §1.4 (one of the seven agreements both independent briefs converged on): "the root cause of the recurring-bug feeling is the mislabeling itself. … the team believed it was fixing while it was redesigning. … every subsequent 'bug' spec is silently patching one of those holes."

The four mislabeled specs above each amended the 0114 contract under a `bug` label, which by definition asserts "no contract change." Reviewers reading the queue under that assumption could not see — at frontmatter level — that the contract surface was moving. That invisibility is what produced the thrash 0114 → 0137 → 0140 → 0218 → 0219.

Reclassification fixes the historical record. The CLAUDE.md process rule (§2.5) prevents recurrence. The 6th bullet on verifier invariants (added per the 0226 debrief §5 Cowork ask) closes the implementation-cycle drift gap that spec 0225 itself ran into (22 invariants shipped vs. 19 agreed in v3 sign-off — same drift class, one cycle inward from spec authoring).

### 1.4 CLAUDE.md "Spec workflow" section — current state

[`CLAUDE.md:26`](CLAUDE.md) opens the `## Spec workflow` section. It currently documents the five lifecycle skills (`/spec-draft`, `/spec-queue`, `/spec-promote`, `/dev-next`, `/dev-queue-run`) and the two-worktree split. It contains no rule constraining when `bug` vs. `new-feature` / `breaking` / `refactoring` labels may be used — the labeling discipline lives only as informal convention, which is precisely how the four mislabeled specs slipped through.

---

## 2. Target state

### 2.1 Spec 0137 — frontmatter edits

Final frontmatter shape:

- **ADD** `type: new-feature` (line immediately after `title:`; field did not previously exist)
- **CHANGE** `label: bug` → `label: new-feature`
- **RENAME + CHANGE VALUE** `version-bump: PATCH` → `version_bump: MINOR` (hyphen → underscore in key; PATCH → MINOR in value)

Body untouched. All other frontmatter fields (`spec`, `title`, `status`, `target-version`, `created`, `pr`) preserved as-is. Reason per synthesis §4: "Adds the `via_artifact_promotion` convergence path + `ArtifactCanonicallyPromoted` event. 0114 explicitly retired escape valves, so this is a contract amendment."

### 2.2 Spec 0140 — frontmatter edits

Final frontmatter shape:

- **ADD** `type: new-feature` (line immediately after `title:`; field did not previously exist)
- **CHANGE** `label: bug` → `label: new-feature`
- **RENAME + CHANGE VALUE** `version-bump: PATCH` → `version_bump: MINOR`

Body untouched. Reason per synthesis §4: "Adds a one-agent-AGREED convergence trigger that 0114's 'both AGREED' rule did not permit."

### 2.3 Spec 0218 — frontmatter edits

Final frontmatter shape:

- **CHANGE** `type: bug` → `type: breaking`
- **CHANGE** `label: bug` → `label: breaking`
- **CHANGE VALUE** `version_bump: PATCH` → `version_bump: MAJOR` (key already uses underscore — no rename)

Body untouched. Reason per synthesis §4: "Introduces a wholly new phase-4 drafter sub-protocol (section deltas, STATUS-first ordering, `max_tokens` → ProtocolParseError)."

### 2.4 Spec 0219 — frontmatter edits

Final frontmatter shape:

- **CHANGE** `type: bug` → `type: new-feature`
- **CHANGE** `label: bug` → `label: new-feature`
- **CHANGE VALUE** `version_bump: PATCH` → `version_bump: MINOR`

Body untouched. Reason per synthesis §4: "Adds a new `EDIT_SECTION` op kind, heading-mismatch hard-fail, persisted `phase4_round` field."

### 2.5 CLAUDE.md addition — verbatim

Append the following subsection to the existing `## Spec workflow` section ([`CLAUDE.md:26`](CLAUDE.md)). Insertion point: at the end of `## Spec workflow`, immediately before the next top-level heading (`## Dashboard` at [`CLAUDE.md:43`](CLAUDE.md)). Preserve all existing content of the Spec workflow section above.

```markdown
### Contract-changing specs are not `bug`s

A spec that introduces, removes, or modifies behaviour in **any** of:

- phase mechanics (entry / exit / artifact);
- convergence rules or the closeout / escape-valve partition;
- the lifecycle state machine (states, edges, terminal rules);
- the categorisation taxonomy (kinds, ID format, namespace);
- any first-class event type;
- **any verifier invariant (gating or reporting)** — including invariants introduced or modified at implementation time, not just at spec-authoring time;

— must carry a `new-feature`, `breaking`, or `refactoring` label, **not** `bug`. A `bug` label is an assertion of "no contract change"; it should be reviewable on exactly that claim.

Drift was the root cause of the 0114 → 0219 thrash: 0137, 0140, 0218, and 0219 all amended the contract under a `bug` label, hiding the change. See `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md` §5 MF1 for the full diagnosis. The verifier (spec 0225) is the executable form of the contract — its invariants ARE the contract. Implementation-cycle additions to that invariant set count as contract changes too.
```

The 6-bullet list (5 base bullets from synthesis §4 + 1 verifier-invariant bullet from the 0226 debrief §5) is load-bearing. The verifier-invariant bullet closes the gap the synthesis didn't surface: an implementer adding a verifier invariant under what was meant to be a strict-implementation cycle is the same drift class spec-authoring-time mislabeling produces, one cycle inward.

### 2.6 CHANGELOG entry — verbatim

Insert directly under `## [Unreleased]` (at [`CHANGELOG.md:11`](CHANGELOG.md), above the existing `## [1.46.0]` entry):

```markdown
## [1.46.1] — 2026-05-26

### Changed

- **Reclassified 4 contract-amending specs from `bug` and added CLAUDE.md "Contract-changing specs are not `bug`s" process rule ([spec 0227](specs/0227-reclassify-contract-amending-specs-and-process-rule.md)).** Per Cowork synthesis [`cowork/briefs/2026-05-26-logic-cutoff-synthesis.md`](../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md) §4: [spec 0137](specs/0137-substantive-convergence-escape-valve.md) (`bug` → `new-feature`, PATCH → MINOR) added the `via_artifact_promotion` convergence path that 0114 explicitly retired; [spec 0140](specs/0140-phase4-deadlock-extractor-and-escape-valve.md) (`bug` → `new-feature`, PATCH → MINOR) added a one-agent-AGREED convergence trigger 0114's "both AGREED" rule did not permit; [spec 0218](specs/0218-phase4-status-survives-truncation.md) (`bug` → `breaking`, PATCH → MAJOR) introduced a wholly new phase-4 drafter sub-protocol (section deltas, STATUS-first ordering, `max_tokens` → ProtocolParseError); [spec 0219](specs/0219-phase4-section-delta-contract-v2.md) (`bug` → `new-feature`, PATCH → MINOR) added a new `EDIT_SECTION` op kind, heading-mismatch hard-fail, and persisted `phase4_round` field. Frontmatter `type:` + `label:` + `version_bump:` corrected on all four (0137 and 0140 additionally migrated from the older `label`-only / `version-bump` schema to the current `type` + `label` / `version_bump` schema while we were in the file); spec bodies unchanged. Added a new `### Contract-changing specs are not `bug`s` subsection to [`CLAUDE.md`](CLAUDE.md) under `## Spec workflow` listing six categories of behaviour-change (phase mechanics, convergence rules, lifecycle state machine, categorisation taxonomy, first-class event types, verifier invariants) that may not ship under a `bug` label. The sixth bullet (verifier invariants, gating or reporting, including implementation-time additions) was added per the 0226 debrief at [`cowork/feedback/2026-05-26-spec-0226-recommendation.md`](../cowork/feedback/2026-05-26-spec-0226-recommendation.md) §5 to close the implementation-cycle drift gap that spec 0225 itself ran into (22 invariants shipped vs. 19 agreed in the v3 sign-off — same drift class as 0137/0140/0218/0219, one cycle inward from spec authoring). No source-code behaviour change; PATCH bump.
```

### 2.7 Version bump

- [`pyproject.toml:3`](pyproject.toml): `version = "1.46.0"` → `version = "1.46.1"`
- [`src/dual_research/__init__.py:1`](src/dual_research/__init__.py): `__version__ = "1.46.0"` → `__version__ = "1.46.1"`

PATCH per `## Versioning and CHANGELOG` in `CLAUDE.md` — `refactoring` maps to PATCH.

---

## 3. Stepwise migration

Each step is independently revertable. Land in one commit at the end (single PR) — the steps are logical, not commit boundaries.

- **Step 1:** Edit `specs/0137-substantive-convergence-escape-valve.md` frontmatter per §2.1. Verify with `head -12 specs/0137-substantive-convergence-escape-valve.md`.
- **Step 2:** Edit `specs/0140-phase4-deadlock-extractor-and-escape-valve.md` frontmatter per §2.2. Verify with `head -12 specs/0140-phase4-deadlock-extractor-and-escape-valve.md`.
- **Step 3:** Edit `specs/0218-phase4-status-survives-truncation.md` frontmatter per §2.3. Verify with `head -22 specs/0218-phase4-status-survives-truncation.md`.
- **Step 4:** Edit `specs/0219-phase4-section-delta-contract-v2.md` frontmatter per §2.4. Verify with `head -22 specs/0219-phase4-section-delta-contract-v2.md`.
- **Step 5:** Append the `### Contract-changing specs are not `bug`s` subsection to `CLAUDE.md` per §2.5. Insert at end of the `## Spec workflow` section, immediately before `## Dashboard`.
- **Step 6:** Insert the `## [1.46.1] — 2026-05-26` CHANGELOG entry per §2.6, directly under `## [Unreleased]`.
- **Step 7:** Bump `pyproject.toml` and `src/dual_research/__init__.py` per §2.7.
- **Step 8:** (Optional, see §5) Add a small assertion test that the four reclassified specs carry the expected new `type:` + `label:` + `version_bump:` values.
- **Step 9:** Run `uv run pytest tests/ -q` — must pass unchanged (no source-code touches).

---

## 4. Behavior preservation

This is a docs/metadata-only refactor. No source-code behaviour change. The existing test suite must pass unchanged.

- [ ] `uv run pytest tests/ -q` passes against HEAD before any changes (baseline).
- [ ] `uv run pytest tests/ -q` still passes after Steps 1–7 land — same test count, same outcomes. Any test that newly fails or errors is a regression and blocks merge.
- [ ] (Optional, Step 8) New file `tests/test_spec_0227_reclassification_lock.py` asserts the four reclassified specs carry the expected new frontmatter values. Pure stdlib (`re` + `pathlib`), follows the source-pattern doctrine from spec 0206 — protects against accidental reverts in future PRs touching these files.

The behaviour preservation contract for this refactor is simple and verifiable: no `.py` files under `src/` are modified, so no runtime path can change. The only runtime touch is `src/dual_research/__init__.py`'s version string (Step 7), which is read by no test assertion and surfaces only in `dual-research --version`.

---

## 5. Out of scope

**Explicit: this spec adds no new feature.** Any feature work that depends on this refactor lives in a follow-up spec.

The following are deliberately excluded and named:

- **No body edits to the four reclassified specs.** Updating the spec bodies to read as `new-feature` / `breaking` rather than `bug` (e.g. rewriting "Fix:" headlines, restructuring sections per the type-template) is out of scope — frontmatter accuracy is the load-bearing fix; body prose is historical record. Deferred indefinitely (low value; spec bodies are not consumed by the lifecycle tooling).
- **No full migration of 0137 and 0140 to the current dev-spec frontmatter schema.** This spec normalises only the fields it must touch (`type:`, `label:`, `version_bump:`). It does not backfill `kind: dev`, `slug:`, `complexity:`, `queued_at:`, `started_at:`, etc. on 0137 and 0140 — those specs were merged before that schema existed. Deferred indefinitely (the lifecycle tooling does not query historical specs).
- **The optional regression-lock test (Step 8) is OPTIONAL, not required for acceptance.** Build it if it falls out cleanly; skip if it would balloon scope. The acceptance criteria do not depend on it.
- **No implementation of the synthesis §6 actions 3 and 6** (the `ProtocolViolation`-emission spec on dropped state-machine ops; the addressee-obligation feature spec). Those are independent follow-up specs Cowork will author per [`2026-05-26-spec-0226-recommendation.md:42-44`](../cowork/feedback/2026-05-26-spec-0226-recommendation.md). This spec ships action 5 only.
- **No automated PR-review gate** that asserts CLAUDE.md's "Contract-changing specs are not `bug`s" rule. This spec ships the rule as documented policy enforced by reviewers (human + Cowork). Mechanising the rule (a `/dev-next` step that greps the diff for verifier-invariant additions in a `bug`-labeled PR) is deferred to a follow-up dev spec to be drafted post-merge if the documented rule turns out to be insufficient.

---

## 6. Risks

What could go wrong, ordered most→least likely:

1. **Schema-mismatch slip-up on 0137 / 0140.** The two old-format specs lack a `type:` field — a naive `Edit` that targets `label: bug` → `label: new-feature` will not surface the missing-`type:` issue. Mitigation: §2.1 and §2.2 explicitly say "ADD `type: new-feature`" and "RENAME `version-bump` → `version_bump`" as separate operations from the value change. Implementer reads the per-spec subsections, not the table.
2. **CHANGELOG insertion drift.** Another PR could land between queue-and-implement that shifts `## [Unreleased]` or adds a new release entry above `## [1.46.0]`. Mitigation: the implementer re-reads `CHANGELOG.md:1-15` immediately before Step 6 and inserts directly under `## [Unreleased]`, whatever line that now lives on.
3. **Test suite has a pre-existing failure unrelated to this spec.** Mitigation: run `uv run pytest tests/ -q` at HEAD before Step 1 to establish a baseline. If a test fails at baseline, that failure is not this spec's responsibility — record the baseline-failure list in the handoff and proceed.
4. **The CLAUDE.md insertion accidentally introduces a fenced-code-block render bug** (e.g. backtick-in-backtick from the inline `` `bug` `` literals). Mitigation: the verbatim block in §2.5 uses standard one-backtick code spans inside a ```` ``` ```` fenced block, which is unambiguous in CommonMark. Implementer copies the block as-is.
5. **Validator rejects the spec at queue time** because the body cites a synthesis section that doesn't exist as written. Mitigation: every cited section (`§1.4`, `§4`, `§6 action 5`) was verified by reading the synthesis file end-to-end before drafting this spec. The §1.1 traceability table cites line numbers for every claim.

No source-code paths are touched, so production-runtime risks are zero by construction.

---

## 7. Acceptance criteria

Per synthesis §6 action 5 acceptance: "0137/0140/0218/0219 relabeled; CLAUDE.md states 'contract-changing specs may not be labeled `bug`.'" Expanded to operational checks:

- [ ] [`specs/0137-substantive-convergence-escape-valve.md`](specs/0137-substantive-convergence-escape-valve.md) frontmatter has `type: new-feature`, `label: new-feature`, `version_bump: MINOR` (key with underscore, not hyphen).
- [ ] [`specs/0140-phase4-deadlock-extractor-and-escape-valve.md`](specs/0140-phase4-deadlock-extractor-and-escape-valve.md) frontmatter has `type: new-feature`, `label: new-feature`, `version_bump: MINOR`.
- [ ] [`specs/0218-phase4-status-survives-truncation.md`](specs/0218-phase4-status-survives-truncation.md) frontmatter has `type: breaking`, `label: breaking`, `version_bump: MAJOR`.
- [ ] [`specs/0219-phase4-section-delta-contract-v2.md`](specs/0219-phase4-section-delta-contract-v2.md) frontmatter has `type: new-feature`, `label: new-feature`, `version_bump: MINOR`.
- [ ] Spec bodies for all four are byte-identical below the closing `---` of the frontmatter (verifiable with `git diff` showing only frontmatter lines changed).
- [ ] [`CLAUDE.md`](CLAUDE.md) contains a new `### Contract-changing specs are not `bug`s` subsection under `## Spec workflow` containing all 6 bullets verbatim per §2.5 (phase mechanics; convergence rules; lifecycle state machine; categorisation taxonomy; first-class event types; verifier invariants).
- [ ] [`CHANGELOG.md`](CHANGELOG.md) has a new `## [1.46.1] — 2026-05-26` section under `### Changed` per §2.6.
- [ ] [`pyproject.toml`](pyproject.toml) has `version = "1.46.1"`; [`src/dual_research/__init__.py`](src/dual_research/__init__.py) has `__version__ = "1.46.1"`.
- [ ] `uv run pytest tests/ -q` passes with no new failures vs. the pre-change baseline.
