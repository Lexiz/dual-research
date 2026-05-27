---
kind: dev
spec: "0233"
slug: spec-templates-add-disposition-placeholders
title: "Refactor: add `disposition:` + `disposition_reason:` placeholders to all five spec templates so verbatim-template authors don't trip the spec 0229.1 validator gate"
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
disposition: ship
disposition_reason: "Templates are the canonical onboarding surface for new spec authors and currently produce hard validator failures on verbatim use, so the cost of leaving the gap exceeds the trivial cost of patching the five files."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0233 — Refactor: spec templates carry `disposition` placeholders

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0229.1 (validator gate that this fixes the UX surface for)
> **Bump:** PATCH — author-facing scaffold change, no validator-behaviour change.
> **Evidence:** Spec 0229.1 §5 named the templates explicitly as deferred; the spec 0229.1 handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:31`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:31) reiterates: *"Authors who use the template verbatim get a clear validator error, but the better UX is to ship the placeholder."*

---

## 1. Current state

The five spec templates under [`specs/_templates/`](specs/_templates/) — `new-feature.md`, `bug.md`, `refactoring.md`, `test.md`, `breaking.md` — define the canonical YAML frontmatter block every new dev spec inherits. As of spec 0229.1, the validator at [`scripts/spec_lifecycle/validator.py:32-45`](scripts/spec_lifecycle/validator.py:32) requires `disposition` and `disposition_reason` as part of `DEV_REQUIRED_FRONTMATTER`. None of the five templates currently declare those fields.

Concrete evidence — `new-feature.md` template ends its frontmatter at [`specs/_templates/new-feature.md:21-23`](specs/_templates/new-feature.md:21):

```yaml
source_session: ""
promoted_from_draft: ""
---
```

`bug.md` mirrors the same shape at [`specs/_templates/bug.md:21-23`](specs/_templates/bug.md:21). `refactoring.md`, `test.md`, and `breaking.md` follow the identical pattern. Verbatim use produces:

```
ERROR: missing required frontmatter keys: ['disposition', 'disposition_reason']
```

The pain: every author of a new spec from a fresh template hits this error and has to look up the convention. The validator error message is good (it cites CLAUDE.md and spec 0229 §2.5) but the author shouldn't need to read the error at all when the template could carry a placeholder + comment explaining what to fill in.

## 2. Target state

Each of the five templates grows two new frontmatter keys directly under `promoted_from_draft: ""`, with the placeholder value commented to make the author-time choice explicit:

```yaml
promoted_from_draft: ""
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship | defer | archive
disposition_reason: "One-sentence justification for the disposition choice."
---
```

The literal placeholder value `ship | defer | archive` is intentional — it fails the validator's vocabulary check (the bar string isn't in `VALID_DISPOSITIONS`), so an author who forgets to pick one still hits a clear error rather than silently shipping with the placeholder. The error message names the valid set, mirroring the placeholder.

The `disposition_reason:` placeholder is a non-empty string that passes the non-empty check but is obviously a placeholder, so authors will replace it. (We accept the failure mode where an author leaves the literal placeholder string — the reviewer catches that in PR review, same as any other "did you customise the template?" check.)

## 3. Stepwise migration

Each step is one template; running the validator on a synthetic spec built from each template verifies the placeholder shape.

- **Step 1:** Patch [`specs/_templates/new-feature.md:21-23`](specs/_templates/new-feature.md:21) — add the comment block + two new keys between `promoted_from_draft: ""` and the closing `---`. Verifies by: build a synthetic spec from the patched template, replace `disposition: ship | defer | archive` with `disposition: ship`, replace placeholder reason with a real one-sentence reason, run `validate_dev_spec` — passes.
- **Step 2:** Patch [`specs/_templates/bug.md:21-23`](specs/_templates/bug.md:21) — same edit. Verifies via same synthetic-spec procedure.
- **Step 3:** Patch [`specs/_templates/refactoring.md:21-23`](specs/_templates/refactoring.md:21) — same edit.
- **Step 4:** Patch [`specs/_templates/test.md:21-23`](specs/_templates/test.md:21) — same edit.
- **Step 5:** Patch [`specs/_templates/breaking.md:21-23`](specs/_templates/breaking.md:21) — same edit.
- **Step 6:** Add a new in-repo invariant test at [`tests/spec_lifecycle/test_template_disposition_placeholders.py`](tests/spec_lifecycle/test_template_disposition_placeholders.py) (new file) that iterates every `*.md` under `specs/_templates/`, parses the frontmatter, and asserts both keys exist. This prevents a future template add from regressing the placeholder pattern.

## 4. Behavior preservation

- [ ] Existing test `tests/test_spec_0229_1_validator_disposition.py::test_no_existing_spec_fails_specifically_on_disposition` still passes — templates are excluded from that walk per spec 0229.1 §2.3 (backfill scope), so this change doesn't widen the in-repo invariant set.
- [ ] No spec validator code is touched. Sole code change is the new test added in Step 6.
- [ ] `uv run pytest tests/ -q` stays green.

## 5. Out of scope

**Explicit: this spec adds no new feature.** It only patches author-facing scaffold files and adds one invariant test that re-asserts the spec 0229.1 contract over the templates directory.

Out of scope:

- **Modifying the validator's vocabulary or shape rules.** This spec changes templates only; validator behaviour is governed by spec 0229.1 unchanged.
- **Adding `disposition` to non-template files (specs, drafts).** Already handled by spec 0229.1's backfill.
- **Author-side UX changes in the `/spec-queue` / `/spec-promote` / `/spec-draft` skills** — those are out-of-repo skill files and the parallel deferred item from the 0229.1 handoff. Tracked separately.

## 6. Risks

- **R1 — Authors copy the literal `ship | defer | archive` placeholder string and ship it.** *Mitigation:* the bar character produces a vocabulary failure at validation, which is caught at `/spec-queue` time before the spec lands. The error message names the valid set so the author knows what to swap in.
- **R2 — A future template added under `specs/_templates/` could regress the placeholder convention.** *Mitigation:* the Step 6 invariant test asserts every `*.md` under `specs/_templates/` (excluding `README.md`-style index files if added) carries both keys, so a new template missing them fails CI.
- **R3 — Template edits could conflict with mid-flight `/spec-queue` operations.** *Mitigation:* the templates are read at skill-invocation time and there's no live in-memory cache. The edit is deterministic and the validator gate is the safety net.
