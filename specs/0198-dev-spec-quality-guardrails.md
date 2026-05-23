---
kind: dev
spec: "0198"
slug: dev-spec-quality-guardrails
title: Dev-spec quality guardrails — no questions, source traceability, BDD acceptance criteria
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: merged
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-23
queued_at: "2026-05-23T21:33:29Z"
started_at: "2026-05-23T21:44:03Z"
merged_at: "2026-05-23T21:56:37Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/226"
handover: ""
failure_step: ""
source_session: promoted-from-draft-001
promoted_from_draft: "001"
---

# Spec 0198 — Dev-spec quality guardrails

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds validator rules + template sections + skill prose without breaking existing specs.
> **Evidence:** Conversation analysis of the critique-iteration → 0167/0168/0173 drift. Three concrete failure modes identified after hours of token spend fixing bugs that shouldn't have shipped.

---

## 1. Context

Three failure modes have repeatedly caused dev specs to ship the wrong code:

1. **Dev specs still contain questions.** Spec-queue Step 2 forbids "Open questions" in prose, but the validator only catches `[TBD]` literal markers. There's no structural enforcement and no terminal gate. Specs slip through with unresolved decisions baked in, and the implementing agent makes the decision unilaterally at ship time (e.g. spec 0166 §2.5 keeping the brand-color dot, spec 0173 §2.9 substituting QuestionThread bubbles for the iter-12 lifecycle layout).

2. **Requirements lose fidelity between source artifact and spec body.** When NOTES.md (or an ideation doc, or a canvas) is cited as the source of truth, there's no requirement that every atomic item make it into the spec. Spec 0168 cited NOTES.md, picked up nine sub-sections, then shipped only §2.1 — the other eight were silently deferred. Spec 0165 §2.1 quoted a drift item without verifying against current code and shipped a no-op.

3. **Templates lack behaviour-driven acceptance criteria.** Current §3 (`UX / Behavior`) says "*Omit if not user-facing. If included: before/after, explicit user flows, screenshot links if any.*" That's prose. There's nothing a Playwright test can grip onto, so implementation drift goes undetected until a user opens the page and notices.

### Traceability table — user's stated issues → spec sections

| User-flagged issue | Source verbatim | Spec section |
|---|---|---|
| "Development specs still have a question section. We agreed that the development spec can never have questions." | this conversation, 2026-05-23 | §2.1 |
| "If the question is too big to resolve here, refuse — tell the user 'drafting first might be wiser'." | spec-queue SKILL.md Step 2 (existing rule, not enforced) | §2.1 |
| "The way these requirements got translated into specs and ultimately got coded is not what was delivered. The specs should be grounded to 100% truth and if the information is there it should be reflected in the spec." | this conversation, 2026-05-23 | §2.2 |
| "It is clear that the way the skills ask it to translate requirements misses a lot of things." | this conversation, 2026-05-23 | §2.2 |
| "Our template is currently missing user stories, behaviour-driven explanations of what is expected from this feature to work well so that this can be later translated into front-end tests" | this conversation, 2026-05-23 | §2.3 |

No items deferred. All three failure modes ship in this spec.

---

## 2. Proposed change

### 2.1 — Hard ban on questions in dev specs

**File: `scripts/spec_lifecycle/validator.py`**

Add a new check `_check_no_open_questions(body)` that fails the spec if any of the following appear as a markdown heading at any level:

- Case-insensitive regex match: `/^#{1,6}\s+(open\s+questions?|unresolved\s+questions?|to\s+decide|tbd|outstanding\s+decisions?)/`
- Inline `[TBD]` markers (existing rule) widened to catch `[TODO]`, `[FIXME]`, and `???` followed by 3+ characters.

Error message: `"body contains an open-questions heading ('${heading}') — dev specs must ship with all decisions resolved. Move to a draft via /spec-draft, or fold into §5 Out of scope with an explicit deferral target."`

**File: `~/.claude/skills/spec-queue/SKILL.md`**

Strengthen Step 2 from prose to a terminal gate:

- Walk the conversation for unanswered questions (heuristic regex: questions ending in `?`, plus phrases like "should we…", "what about…", "do we want…", "I'm not sure…").
- For each one found, the skill MUST either (a) get an explicit resolution from the user via `AskUserQuestion` and fold the answer into the spec body, (b) move the question into §5 Out of scope with a named deferral target (e.g. "deferred to spec 0XXX — Σ Summary cleanup"), or (c) refuse to commit and surface `"<N> unresolved questions detected — invoke /spec-draft to resolve, then re-run /spec-queue."`

**File: `~/.claude/skills/spec-promote/SKILL.md`**

Identical terminal gate applies. Drafts MAY carry questions; the moment they become dev specs, every question is closed.

**File: `specs/_templates/*.md`** (all five)

Add a top-of-template comment block:

```markdown
<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->
```

### 2.2 — Source-artifact traceability

**File: `scripts/spec_lifecycle/validator.py`**

Add `_check_source_traceability(body)`:

- Detect cited source artifacts: file links matching `/prototypes/.*-iteration/NOTES.md`, `/prototypes/.*-iteration/V2-SNAPSHOT.md`, or any reference of the form "ideation doc", "mockup", "canvas" in §1 Context.
- When detected, require a Markdown table in §1 with columns `source item | source quote/ref | spec section`. The table must have ≥ 1 row per atomic item in the source (iter row, drift letter, mockup screen). If the source is a NOTES.md with N iters + M drift items, the table must have N+M rows.
- Each row's `spec section` cell must point to either a `§2.X` heading present in the body OR `§5 (deferred to spec NNNN — <reason>)` with a named follow-up target.
- Failure: `"source traceability table missing or incomplete. Source artifact ${path} has ${N} atomic items but spec lists ${M}. Every item must either ship in §2.N or defer to §5 with a named follow-up spec."`

**File: `~/.claude/skills/spec-queue/SKILL.md`**

Add Step 1e (after the existing Step 1d decomposition check):

- "**Source-artifact enumeration.** If the conversation cites a NOTES.md, V2 snapshot, ideation doc, or canvas prototype, open the file and enumerate every atomic item (iter row, drift letter, mockup state). Build the traceability table for §1 Context. For every item, decide whether it ships in this spec or defers to a follow-up. **Silent drops are a validator failure.**"

Add Step 1f:

- "**Verify against current code.** Before claiming `live currently lacks X` or `live currently does Y`, open the cited file at the cited line and confirm. Drift items can become stale (the spec 0165 §2.1 no-op is exactly this failure)."

**File: `~/.claude/skills/spec-promote/SKILL.md`**

Apply the same enumeration + verification gates when promoting a draft.

### 2.3 — User stories & BDD acceptance criteria

**File: `specs/_templates/new-feature.md` and `specs/_templates/bug.md`**

Replace the current `## 3. UX / Behavior` section with:

```markdown
## 3. User stories & acceptance criteria

### 3.1 — User stories

REQUIRED for any spec that touches files under `src/dual_research/ui/` or `design-system/`. Format:

> As a `<role>`, I want `<goal>`, so that `<outcome>`.

At least one story per user-visible feature. Roles: `researcher`, `dev`, `viewer`, `admin`, `unauthenticated visitor`.

### 3.2 — Acceptance scenarios (BDD)

REQUIRED for any UI-touching spec. ≥ 2 scenarios per spec. Format:

> **Scenario 1:** `<short name>`
> GIVEN `<precondition observable in the DOM or app state>`
> WHEN `<user action: click, type, navigate, hover>`
> THEN `<observable result: element visible, attribute set, text content matches, network call fires>`

Each scenario must be expressible as a Playwright test. The validator regex-matches `/GIVEN.+\n.*WHEN.+\n.*THEN.+/i` and requires ≥ 2 hits.
```

**File: `specs/_templates/refactoring.md`, `specs/_templates/breaking.md`, `specs/_templates/test.md`**

Optional `## 3. User stories & acceptance criteria` section. Refactoring specs must instead document **behaviour preservation** (which they already do); breaking specs must document the contract change. Test specs document the new coverage.

**File: `scripts/spec_lifecycle/validator.py`**

Add `_check_user_stories_for_ui_specs(body, files_touched)`:

- If the spec body or `Proposed change` section references any path under `src/dual_research/ui/` or `design-system/assets/`, the spec is UI-touching.
- For UI-touching specs: require ≥ 1 line matching `/As an? .+, I want .+, so that .+/i` AND ≥ 2 BDD scenario triples matching `/GIVEN[^\n]+\n[^\n]*WHEN[^\n]+\n[^\n]*THEN[^\n]+/is`.
- Failure: `"UI-touching spec missing user stories or BDD acceptance criteria. Need ≥ 1 'As a X, I want Y' and ≥ 2 'GIVEN/WHEN/THEN' scenarios."`

---

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a **dev** writing a spec, I want the skill to refuse to queue a spec that contains open questions, so that I can't accidentally ship a half-decided change that the implementing agent will resolve unilaterally at the wrong moment.

> As a **dev** authoring a spec from a source artifact (NOTES.md / V2 snapshot / mockup), I want every atomic item in the source to be visible in the spec — either as a `§2.N` deliverable or an explicit `§5` deferral with a named follow-up — so that nothing drops on the floor between ideation and code.

> As a **dev** reading a UI spec for the first time, I want a numbered list of "user does X, sees Y" scenarios, so that I can write Playwright tests that fail if the implementation drifts from the intended behaviour.

### 3.2 — Acceptance scenarios

> **Scenario 1:** validator rejects open-questions section
> GIVEN a spec body containing a heading `## Open questions`
> WHEN `uv run python -m scripts.spec_lifecycle.validator <file>` runs
> THEN the exit code is non-zero AND the stderr contains `"open-questions heading"`.

> **Scenario 2:** validator rejects spec citing NOTES.md without a traceability table
> GIVEN a spec body §1 that links to `prototypes/critique-iteration/NOTES.md` but has no Markdown table mapping iter rows to §2.N entries
> WHEN the validator runs
> THEN the exit code is non-zero AND the stderr contains `"source traceability table missing"`.

> **Scenario 3:** spec-queue refuses to commit a spec with an unanswered question
> GIVEN a conversation that ends with the user asking "*should we keep the All button or drop it?*" without resolution
> WHEN `/spec-queue` is invoked
> THEN the skill either (a) asks the user via `AskUserQuestion` and folds the answer into the spec, OR (b) refuses to commit with the message `"<N> unresolved questions detected — invoke /spec-draft to resolve, then re-run /spec-queue."`

> **Scenario 4:** validator rejects UI spec missing user stories
> GIVEN a spec body referencing `src/dual_research/ui/static/components.css` with no `As a X, I want Y` line and no `GIVEN/WHEN/THEN` scenarios
> WHEN the validator runs
> THEN the exit code is non-zero AND the stderr contains `"UI-touching spec missing user stories"`.

> **Scenario 5:** non-UI spec passes without user stories
> GIVEN a refactoring spec body that only touches `scripts/spec_lifecycle/validator.py`
> WHEN the validator runs
> THEN the exit code is zero and no user-story error is raised.

---

## 4. Data / Schema deltas

None. Template and validator changes only.

---

## 5. Out of scope

- **Retroactive validation of existing specs.** This spec adds gates to new specs going forward. Existing dev specs (0001 through current) are not re-validated and not rejected if they fail the new rules.
- **Auto-generation of traceability tables.** The dev/skill builds the table manually from the source artifact; the validator only confirms its presence and row count. A future spec could add an auto-enumeration helper.
- **Playwright test scaffolding.** This spec defines the BDD format. A separate spec wires Playwright to consume the scenarios and generate test stubs.
- **The V2 promotion specs themselves** (critique-iteration V2 → live, timeline-iteration V2 → live). Those are downstream consumers of this spec's improved rules.

---

## 6. Test plan

- [ ] Validator: a spec with `## Open questions` heading fails with the documented error message.
- [ ] Validator: a spec citing `prototypes/critique-iteration/NOTES.md` without a traceability table fails with the documented error.
- [ ] Validator: a UI-touching spec without user stories fails; a non-UI spec without user stories passes.
- [ ] Validator: a spec with ≥ 1 `As a X, I want Y` line and ≥ 2 `GIVEN/WHEN/THEN` triples passes.
- [ ] spec-queue skill: a conversation with a literal "?" question that wasn't resolved triggers an `AskUserQuestion` prompt or a refusal — never a silent commit.
- [ ] spec-promote skill: same as spec-queue.
- [ ] Template smoke test: `uv run python -m scripts.spec_lifecycle.validator specs/_templates/new-feature.md` does not fail on the template itself (the template comment block + structure are well-formed).
- [ ] Backward compatibility: existing merged specs (0167, 0168, 0173) are not re-validated by the new rules — they ran under the old contract.

---

## 7. Risks

- **Risk:** the open-questions heading regex over-matches, blocking innocent uses of the word "question". *Mitigation:* the regex is anchored to markdown headings (`^#{1,6}\s+`) so prose mentions like "the question is whether…" don't fire. Test with the existing spec corpus before shipping.
- **Risk:** traceability tables become bureaucratic for small specs with no source artifact. *Mitigation:* the rule only fires when a source artifact path is cited in §1; specs without source artifacts (the majority) are unaffected.
- **Risk:** the BDD requirement adds friction for tiny UI tweaks. *Mitigation:* ≥ 2 scenarios is the floor, not a target. A one-line CSS tweak can ship with two two-line scenarios — that's still cheap insurance against silent regressions like the iter-12 → QuestionThread substitution.
- **Risk:** the validator gets out of sync with the skill prose. *Mitigation:* the validator is the source of truth; the skills cite the validator's error messages verbatim so any divergence shows up as a contradiction at commit time.
