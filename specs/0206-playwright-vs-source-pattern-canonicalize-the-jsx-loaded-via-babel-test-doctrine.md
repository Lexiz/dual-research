---
kind: dev
spec: "0206"
slug: playwright-vs-source-pattern-canonicalize-the-jsx-loaded-via-babel-test-doctrine
title: "Tests: canonicalize the JSX-loaded-via-babel test doctrine (Playwright harness or source-pattern as the documented project pattern)"
type: test
label: test
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-24
queued_at: "2026-05-24T04:03:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0206 — Tests: canonicalize the JSX-loaded-via-babel test doctrine

> **Type:** test  |  **Complexity:** M
> **Bump:** PATCH — test additions / documentation only, no runtime behavior change
> **Evidence:** spec 0205 §5 called for `tests/ui/test_p4_critique_card.py` Playwright tests; the implementer found no Playwright infrastructure in the repo and substituted static-pattern tests at `tests/test_spec_0205_critique_card.py:1` (8 tests, one pair per Bug N), documented as a project-wide deferral in `handoffs/2026-05-24-spec-0205-fix-p4-critique-card-five-visual-regressions.md:45`. This is the second time the question has surfaced (spec 0172's `tests/spec0172/test_critique_card_markdown_and_no_sid.py` is the same pattern). The project needs a documented canonical answer instead of re-deciding per spec.

---

## 1. Coverage gap

The `src/dual_research/ui/static/run-detail.jsx` file is the largest JSX surface in the repo and the most-touched by recent UI specs (0179, 0203, 0204, 0205). It loads in the browser via in-page Babel transform (`@babel/standalone`) at runtime, not via a webpack / esbuild build step, so the JSX has no Node-importable module shape — only the source text. The repo has zero Playwright tests (confirmed by `grep -r playwright tests/` → only the docstrings in `tests/test_spec_0205_critique_card.py:3` and `tests/spec_lifecycle/test_dashboard_mockup_parity.py:3` explaining their absence, plus prose mentions in fixture briefs).

Today the project oscillates between two patterns when a UI spec needs regression coverage:

- **Static-pattern tests** (the de-facto default). Each test reads the JSX / CSS source as text and asserts a regex pattern is present (post-fix shape) AND an antipodal regex is absent (pre-fix shape). Example: `tests/test_spec_0205_critique_card.py:39` (Bug 1, `.item-card__sources` interior padding + `<blockquote>` excerpt) and `tests/spec0172/test_critique_card_markdown_and_no_sid.py:1` (spec 0172, markdown + sid handling). Pure stdlib, no harness, ~2 ms per test, runs inside `uv run pytest tests/ -q`.
- **DOM tests** (zero instances today). Would need a Playwright (or Selenium / Pyppeteer) harness + a fixture run server + a per-test setup that boots the local UI server and navigates to a route. Cost: harness scaffolding (~200 lines), CI minutes (Playwright browser downloads + per-test startup), flake budget.

Each new UI spec re-litigates the choice in its §5 Regression-prevention test section. Specs that ask for Playwright (e.g. spec 0205 §5 at `specs/0205-fix-p4-critique-card-five-visual-regressions.md:211`) silently degrade to static-pattern at dev time; specs that ask for static-pattern leave the runtime-rendering claim un-verified. The handoff entry at `handoffs/2026-05-24-spec-0205-fix-p4-critique-card-five-visual-regressions.md:45` is the canonical articulation of the gap: *"If the project ever stands up a Playwright harness, follow-up dev spec converts the 8 source-pattern tests to DOM tests against a fixture run."*

## 2. Test approach

Resolve the doctrine question by **picking option (b)** below and documenting it as canonical. Then back-port the documentation so future UI specs don't re-litigate.

### 2.1 Decision: static-pattern is the canonical project pattern

**Rationale:**

- The JSX-loaded-via-babel runtime has no module boundary that Node could import — Playwright is the only DOM-rendering option, and the cost (browser downloads in CI, per-test startup, flake risk) is disproportionate to the value when the file structure makes source-pattern tests sufficient.
- Static-pattern tests have caught every UI regression they were written for (spec 0172, spec 0179, spec 0205) without false positives. The pattern is well-understood: read the JSX/CSS as text, assert a positive regex AND an antipodal-absence regex per bug, one test pair per anatomical contract.
- The Claude Preview MCP (used during `/dev-next` step 14) provides the live-browser verification that source-pattern tests cannot — it's the runtime cross-check, captured as a screenshot in the PR description (and required by spec 0179 for ItemCard PRs).
- The repo already has a multi-spec history of static-pattern tests: `tests/test_spec_0205_critique_card.py:1` (spec 0205, 8 tests), `tests/spec0172/test_critique_card_markdown_and_no_sid.py:1` (spec 0172), `tests/spec_lifecycle/test_dashboard_mockup_parity.py:1` (spec lifecycle).

### 2.2 What lands

1. **New section in `design-system/SPEC.md` §10 (or an adjacent §) titled "UI test doctrine (spec 0206)"** documenting:
   - The two patterns (static-pattern + DOM/Playwright) and why static-pattern is canonical for the JSX-loaded-via-babel runtime.
   - The canonical static-pattern shape: one test pair per anatomical contract (positive regex on post-fix shape + antipodal-absence regex on pre-fix shape), file lives at `tests/test_spec_NNNN_<surface>.py`, pure stdlib.
   - The Claude Preview MCP screenshot in the PR description is the runtime cross-check; for ItemCard-touching specs, spec 0179's 8-capture grid is mandatory.
   - DOM/Playwright is explicitly out of scope for the current architecture; if the runtime ever moves off babel-in-page to a real build, revisit.

2. **New section in `CLAUDE.md` "## Tests"** linking to the DS doctrine section + a one-line summary: *"UI specs lock anatomy via source-pattern tests at `tests/test_spec_NNNN_<surface>.py`; runtime is verified via Claude Preview MCP screenshot. Playwright is not used (see DS §10)."*

3. **New shared helper at `tests/_ui_pattern_helpers.py`** (or `tests/ui/_helpers.py`) that gives source-pattern tests a single canonical idiom:
   - `assert_jsx_contains(path, pattern, *, msg)` — fails with a useful diff when the post-fix pattern is absent.
   - `assert_jsx_lacks(path, pattern, *, msg)` — fails with a captured snippet when the pre-fix pattern still present.
   - `read_repo_text(*parts)` — anchors at `REPO_ROOT`, returns text.
   Back-port `tests/test_spec_0205_critique_card.py:39` and `tests/spec0172/test_critique_card_markdown_and_no_sid.py:1` to use the helper. No assertion semantics change; this is shape consolidation only.

4. **One example UI test in the new canonical style** — pick the simplest of the spec 0205 tests (Bug 3, the `mdi:link-variant` glyph parity at `tests/test_spec_0205_critique_card.py` for the Sources chip + segment header) and re-write it through the helper. The diff serves as the worked example referenced from the DS doctrine section.

5. **Frontmatter rule check in `scripts/spec_lifecycle/validator.py`** (warning, not error) — for `type: test` and `type: bug` specs whose `§5 Regression-prevention test` block names a path under `tests/ui/` (the Playwright convention) instead of `tests/test_spec_NNNN_*.py` (the canonical convention), surface a warning so the author knows the chosen path doesn't match doctrine. This keeps `/dev-next` honest about the substitution that happened silently in spec 0205.

### 2.3 What is explicitly NOT in this spec

- Standing up a Playwright harness. Option (a) from the deferral (port the 8 static tests to DOM) is rejected; the cost/value math is documented in §2.1 and §4.
- Converting the existing static-pattern tests under `tests/spec0172/` and `tests/test_spec_0205_critique_card.py` to anything other than the new helper idiom. Behavior of those tests is preserved.
- Any change to the `tests/ui/` directory naming convention beyond the validator warning — the directory does not exist today and this spec does not create it.

## 3. What it would catch

The chronic failure mode this canonicalization closes is **drift between what a spec's §5 says and what dev-next actually lands**. Specifically:

- Spec 0205 §5 at `specs/0205-fix-p4-critique-card-five-visual-regressions.md:211` named `tests/ui/test_p4_critique_card.py` (Playwright); dev-next silently shipped `tests/test_spec_0205_critique_card.py:1` (static-pattern). The user-visible artifact (the PR + the test file path + the test names) does not match the spec the work was queued against. This is documented as a deferred item, not a defect — but the next time a spec authors writes "Playwright" because the prior spec did, the same silent substitution will happen.
- The substitution is symmetric: if a spec authors writes "source-pattern tests at `tests/spec_NNNN/...`" (because that's what spec 0172 did), dev-next might land them at `tests/test_spec_NNNN_*.py` instead (the spec 0205 convention) and the author can't tell whether that's a meaningful difference. One canonical path stops the bikeshed.
- The validator warning in §2.2 step 5 surfaces the drift at queue time — before dev-next has to silently substitute.

A historical bug class this would have caught: spec 0179's `ItemCard parity verification` rule at `design-system/SPEC.md:378` was added precisely because specs 0138 / 0141 / 0144 / 0151 *"cited the reference screenshots in prose but did not verify the rendered output"*. The same family of failure — verbal-not-mechanical claims of test coverage — is what §2.2 step 5 catches at queue time.

## 4. User stories & acceptance criteria

### 4.1 User stories

> As a **spec author** writing a new UI spec's §5 Regression-prevention test section, I want one canonical project pattern documented in `design-system/SPEC.md` and `CLAUDE.md`, so that I don't re-derive "Playwright or source-pattern?" per spec and dev-next doesn't have to silently substitute.

> As a **dev-next implementer** picking up a queued UI spec, I want the spec's named test path to match the project's canonical convention, so that I don't silently land tests at a different path than the spec promised.

### 4.2 Acceptance scenarios (BDD)

> **Scenario 1:** Canonical doctrine is reachable from both docs
> GIVEN a spec author opens `CLAUDE.md` looking for the UI test convention
> WHEN they scan the "Tests" section
> THEN the section names the canonical static-pattern shape AND links to the `design-system/SPEC.md` §10 (or adjacent) doctrine section that explains the rationale.

> **Scenario 2:** Validator warns on the deprecated `tests/ui/` Playwright path
> GIVEN a queued `type: test` or `type: bug` dev spec whose body names a regression-prevention test at `tests/ui/...py`
> WHEN `uv run python -m scripts.spec_lifecycle.validator <path>` runs
> THEN the run prints a WARNING (not an ERROR) flagging the path as non-canonical and pointing at the DS doctrine section.

> **Scenario 3:** Shared helper preserves existing test behavior
> GIVEN `tests/test_spec_0205_critique_card.py` and `tests/spec0172/test_critique_card_markdown_and_no_sid.py` are back-ported to use `tests/_ui_pattern_helpers.py`
> WHEN `uv run pytest tests/ -q` runs
> THEN every test that passed pre-back-port still passes (no assertion-semantic drift) and the helper is imported in exactly the two back-ported files.

## 5. Risks

- **The canonicalization is a taste decision in the §2.1 framing.** Option (a) — actually standing up a Playwright harness — has real value when the JSX runtime grows beyond babel-in-page. Mitigation: §2.1 commits to revisit if the runtime moves off babel; the DS doctrine section names that explicit trigger.
- **Source-pattern tests are over-fitted to specific regexes.** A renamed CSS class or a slightly refactored JSX block can break them without the underlying anatomy actually regressing. Mitigation: the helper's `assert_jsx_contains` returns the captured context on failure, so the fix is usually a one-line regex update — not a re-derivation. The spec 0205 tests already demonstrate the shape works at scale (8 tests, none flaky across the merge).
- **The validator warning is advisory and could be ignored.** That's intentional — it's an authoring nudge, not a gate. Specs that legitimately want a different test path (e.g. an experiment) shouldn't be blocked. Mitigation: if the warning is ignored, dev-next still surfaces the path drift in its step-15 DS gate report.
- **The shared helper at `tests/_ui_pattern_helpers.py` adds one import surface across UI tests.** If the helper changes shape later, every back-ported test moves with it. Mitigation: the helper is intentionally tiny (three functions, ~30 lines total); the back-port in §2.2 step 3 covers two files only, so the blast radius is bounded.
