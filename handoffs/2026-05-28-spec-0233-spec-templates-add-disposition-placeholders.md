---
spec: "0233"
date: 2026-05-28
version: "1.58.1"
pr: "https://github.com/Lexiz/dual-research/pull/280"
kind: post-deploy
---

# Spec 0233 — Spec templates carry `disposition` placeholders (v1.58.1)

## What landed

- All five spec templates under [`specs/_templates/`](specs/_templates/) — `new-feature.md`, `bug.md`, `refactoring.md`, `test.md`, `breaking.md` — now declare `disposition:` and `disposition_reason:` placeholder keys directly after `promoted_from_draft: ""`, with an inline comment block citing the spec 0229 §2.5 carve-out-disposition convention and the three-value vocabulary.
- The literal placeholder value `ship | defer | archive` is intentional per spec §2: the bar string is **not** in `VALID_DISPOSITIONS = {"ship", "defer", "archive"}` (see [`scripts/spec_lifecycle/validator.py:24`](scripts/spec_lifecycle/validator.py:24)), so a verbatim-template author who forgets to pick a value still hits a clear vocabulary error rather than silently shipping a placeholder. The placeholder doubles as the cheat-sheet for what values are valid.
- The `disposition_reason:` placeholder is a non-empty single-sentence string that satisfies the validator's non-empty + single-sentence shape gate but is obviously a placeholder — left for reviewer catch in PR review.
- Verifier: spec 0229.1 contract preserved unchanged. The existing test [`tests/test_spec_0229_1_validator_disposition.py::test_no_existing_spec_fails_specifically_on_disposition`](tests/test_spec_0229_1_validator_disposition.py) still passes — templates are excluded from that walk per spec 0229.1 §2.3 backfill scope, so this change doesn't widen the in-repo invariant set.

## Scope-adjacent fix shipped in the same PR

While writing the §3 step 6 invariant test (the new file at [`tests/spec_lifecycle/test_template_disposition_placeholders.py`](tests/spec_lifecycle/test_template_disposition_placeholders.py)), three templates failed the parse-as-YAML half of the assertion. Root cause: their `title:` placeholders contained an unquoted colon — `title: Fix: <symptom>` in `bug.md`, `title: Refactor: <area>` in `refactoring.md`, `title: Tests: <area>` in `test.md`. The YAML scanner reads that as `mapping values are not allowed here`, and the tolerant frontmatter parser at [`scripts/spec_lifecycle/frontmatter.py:59`](scripts/spec_lifecycle/frontmatter.py:59) silently returns an empty dict on `YAMLError`. A verbatim-template author would therefore have hit a full-frontmatter-missing validator error, not just the disposition error — a strictly louder version of the same trip-up the spec exists to remove.

Fix shipped inline: titles quoted (`title: "Fix: <symptom>"` etc.). On-mission per spec's stated goal of "verbatim-template authors don't trip the spec 0229.1 validator gate" — fixing the disposition placeholders alone would not have delivered the goal for three of the five templates because the validator would never have reached the disposition check.

## Invariant test design

[`tests/spec_lifecycle/test_template_disposition_placeholders.py`](tests/spec_lifecycle/test_template_disposition_placeholders.py) is intentionally strict: it parses each template's frontmatter through the same `scripts.spec_lifecycle.frontmatter.parse` function the validator uses, then asserts both `disposition` and `disposition_reason` are present in the resulting dict. This catches **both** classes of regression:

- A future template added without the disposition placeholders → missing keys.
- A future template that accidentally breaks YAML parse (unquoted colon, tab vs space, BOM, etc.) → empty dict, missing keys.

Both surface with the same error message naming the offending file. README-style index files would be excluded (`p.name != "README.md"`) — placeholder for the case where a templates README gets added later.

## Files touched

| File | Change |
|---|---|
| `specs/_templates/new-feature.md` | + 6 lines (comment block + 2 placeholder keys) |
| `specs/_templates/bug.md` | + 6 lines, + title quote-fix |
| `specs/_templates/refactoring.md` | + 6 lines, + title quote-fix |
| `specs/_templates/test.md` | + 6 lines, + title quote-fix |
| `specs/_templates/breaking.md` | + 6 lines |
| `tests/spec_lifecycle/test_template_disposition_placeholders.py` | new file, 2 tests |
| `pyproject.toml` | 1.58.0 → 1.58.1 |
| `src/dual_research/__init__.py` | 1.58.0 → 1.58.1 |
| `src/dual_research/ui/static/version-notes.json` | regenerated via `scripts/build_version_notes.py` |
| `CHANGELOG.md` | new `## [1.58.1] — 2026-05-28` section |
| `uv.lock` | passive version bump |

## Tests

- `uv run pytest tests/ -q` → **2326 passed in 32.13s** (green).
- New invariant test passes on the post-fix templates and would have surfaced any of the three colon-broken templates as a missing-keys failure (verified manually on a checkpoint between the placeholder-add step and the title-quote step — three failures, exactly the templates with unquoted colons).
