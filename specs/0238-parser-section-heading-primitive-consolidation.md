---
kind: dev
spec: "0238"
slug: parser-section-heading-primitive-consolidation
title: "Parser: consolidate every specific-literal-heading anchor onto one tolerant `section_heading_re` primitive in markers.py"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0232"]
complexity: M
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Closes the parser-fragility class (Bug A) at the agent-output surface. Without it every round-by-round phase remains vulnerable to model-emitted glued-heading prose and will dead-lock the orchestrator into an empty-turn retry loop. Live evidence at tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/. Cowork sign-off at cowork/briefs/2026-05-27-0238-0239-design-answers.md."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0238 — Parser primitive consolidation: one tolerant `section_heading_re` for every specific-literal-heading anchor

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0232 (so I2.6's reporting oracle exists to verify the fix lands cleanly).
> **Bump:** MINOR — adds a new public primitive in `markers.py`, changes the regex shape of 8 SECTION_*_RE constants and several other heading-anchored finders, adds a process rule to `CLAUDE.md`. Parser-tolerance invariants ARE the contract per the CLAUDE.md "contract-changing specs are not bugs" rule.
> **Evidence:** failing-run fixture [`tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/`](tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/); Cowork pressure-test brief `cowork/briefs/2026-05-27-rerun-142625-pressure-test.md`; Cowork design-answers brief `cowork/briefs/2026-05-27-0238-0239-design-answers.md`; predecessor spec 0231 (partial-coverage patch on `extract_fenced_section` only).

---

## 1. Context

The 2026-05-27 live re-run `20260527-142625-backend-language-choice` died at phase 2 round 1 → round 2 boundary with $3.72 spent. Root cause: claude's round-1 output ([tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/phase2/round-01-claude.md:23](tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/phase2/round-01-claude.md:23)) contained the heading:

```
## New items I'm raisingNow I have the evidence I need. Let me raise the items.
```

`SECTION_NEW_ITEMS_RE` at [`src/dual_research/contract/markers.py:34`](src/dual_research/contract/markers.py:34) is `r"^##\s+New items I'?m raising\b"`. The `\b` (word boundary) is false when the next character is itself a word character (`N` in `raisingNow`), so the regex fails. The section is never opened, all 5 `### RAISE` blocks inside it are dropped, the orchestrator sees claude as having produced no structured items, fires `empty_turn_detected`, and immediately retries with byte-identical input — the user killed the spin after observing it.

This is the **same bug class** as spec 0231 ("parser heading tolerance") at a **different surface**. 0231 loosened [`extract_fenced_section` at src/dual_research/protocol/parse.py:179](src/dual_research/protocol/parse.py:179) to accept glued prose after a heading. It did NOT touch [`markers.py`](src/dual_research/contract/markers.py) and it did NOT touch the [`_extract_section_body` extractor at src/dual_research/protocol/parse.py:1372](src/dual_research/protocol/parse.py:1372) that consumes the SECTION_*_RE family from `parse_turn_v2`. Cowork's pressure-test brief (`cowork/briefs/2026-05-27-rerun-142625-pressure-test.md`) confirms: 0231 **missed** this path, it did not knowingly defer it.

The parser-fragility class therefore remains open on every heading-anchored finder that uses a specific-literal regex with the `\b` (or any other word-boundary-style) terminator. Today's failure surfaced on `SECTION_NEW_ITEMS_RE`; the next surface is whichever other specific-literal-heading finder a model output happens to glue first.

## 2. Proposed change

Three layers ship together in one PR.

### Layer 1 — `section_heading_re(name)` primitive in `markers.py`

Add a single public factory in [`src/dual_research/contract/markers.py`](src/dual_research/contract/markers.py) that constructs heading-anchor regexes with a tolerant terminator:

```python
def section_heading_re(
    name_pattern: str,
    *,
    flags: int = re.MULTILINE | re.IGNORECASE,
) -> "re.Pattern[str]":
    """Compile a `^## <name>` heading anchor with a glued-prose-tolerant terminator.

    `name_pattern` is a raw regex fragment (NOT an arbitrary string).
    Callers pass literal text via `re.escape()` themselves; callers that
    need internal alternation (e.g. an optional apostrophe, an "Open
    questions for X" suffix) pass the regex fragment directly. The
    factory does not auto-escape — auto-escaping would prevent the
    legitimate-alternation case and re-introduce drift between callers.
    """
    return re.compile(
        rf"^##\s+{name_pattern}(?:\s*$|(?=\S))",
        flags,
    )
```

**Why the `(?:\s*$|(?=\S))` terminator:** matches *either* end-of-line (optionally with trailing whitespace) *or* a non-whitespace follow-on character (the glued-prose case). Cowork verified both branches against the literal failing line and against 7 realistic variants (clean / trailing whitespace / no-apostrophe / ALL-CAPS / trailing period / trailing colon+text / glued-letter); all 7 match. The form is the same one [`extract_fenced_section` at src/dual_research/protocol/parse.py:179](src/dual_research/protocol/parse.py:179) already uses post-0231 — Layer 2 leverages this to collapse the two implementations.

**Why a raw regex fragment, not an auto-escaped string:** four of the callsites genuinely need internal alternation (`I'?m`, `Open questions for .+?`, `(?:\d+\.\s+)?Open Questions`). Auto-escaping the input would break those. Forcing callers to pass raw fragments and use `re.escape()` themselves at the no-alternation sites is the lesser of two evils — it keeps the primitive's API single-purpose and prevents the "I'?m got escaped" footgun the Cowork API-shape note flagged.

### Layer 2 — Rebuild every specific-literal-heading anchor through the primitive

Replace 8 SECTION_*_RE constants in [`src/dual_research/contract/markers.py`](src/dual_research/contract/markers.py) lines 25–48:

```python
SECTION_STANCE_RE                = section_heading_re(re.escape("Stance"))
SECTION_ADDRESSING_RE            = section_heading_re(re.escape("Addressing items raised against me"))
SECTION_RATIFYING_RE             = section_heading_re(re.escape("Ratifying my own items"))
SECTION_NEW_ITEMS_RE             = section_heading_re(r"New items I'?m raising")          # internal alternation kept
SECTION_PHASE_ARTIFACT_RE        = section_heading_re(re.escape("Phase artifact"))
SECTION_STATUS_RE                = section_heading_re(re.escape("Status"))
SECTION_REVISED_DRAFT_RE         = section_heading_re(re.escape("Revised draft"))
SECTION_CLOSEOUT_CONSTRAINTS_RE  = section_heading_re(re.escape("Closeout constraints"))
```

Replace [`_REVISED_DRAFT_HEADING_RE` at src/dual_research/protocol/parse.py:385](src/dual_research/protocol/parse.py:385) (`r"^##\s+Revised draft\s*$"`) with a re-export of `markers.SECTION_REVISED_DRAFT_RE`. Update all callers (only [`extract_revised_draft_inclusive` at src/dual_research/protocol/parse.py:389](src/dual_research/protocol/parse.py:389) consumes it directly today).

Refactor [`extract_review_items` at src/dual_research/protocol/parse.py:1069](src/dual_research/protocol/parse.py:1069) to consume `section_heading_re` for its two specific-literal heading anchors (lines 1086 and 1095):
- `r"^##\s+Open questions for .+?$"` → `section_heading_re(r"Open questions for .+?")`
- `r"^##\s+(?:\d+\.\s+)?Open Questions\s*$"` → `section_heading_re(r"(?:\d+\.\s+)?Open Questions")`

Refactor [`extract_fenced_section` at src/dual_research/protocol/parse.py:179](src/dual_research/protocol/parse.py:179) to call `section_heading_re(re.escape(heading_name))` internally instead of constructing its regex inline. This is the consolidation Cowork's brief calls out as "the real structural fix" — extract_fenced_section and the SECTION_*_RE family stop being two heading implementations that can drift.

Refactor [`_extract_section_body` at src/dual_research/protocol/parse.py:1372](src/dual_research/protocol/parse.py:1372) callers (lines 1679–1681 in `parse_turn_v2`) — no signature change; the function already takes a `pattern` argument and the patterns it receives are now built via `section_heading_re`, so the consolidation happens at the construction site, not at the function. Spec 0122's body-scoring (`_extract_section_body`'s reasoning-preamble disambiguation) remains untouched.

### Layer 3 — Explicit scope boundary (what we do NOT change)

Per Cowork's sign-off on the scope rule, **boundary** and **capture** heading regexes are different abstractions and stay separate:

- [`_TOP_HEADING_RE` at src/dual_research/protocol/parse.py:386](src/dual_research/protocol/parse.py:386) — `r"^##\s+\S"` — boundary scanner; finds the next H2 to bound a section. NOT touched.
- [`_H2_RE` at src/dual_research/protocol/parse.py:133](src/dual_research/protocol/parse.py:133) — `r"^##\s+\S"` — same boundary role. NOT touched.
- [`_DRAFT_SECTION_HEADING_RE` at src/dual_research/protocol/parse.py:683](src/dual_research/protocol/parse.py:683) — `r"^##\s+(.+?)\s*$"` — capture regex that extracts arbitrary heading names from draft bodies for indexing. NOT touched.

The principled scope rule is documented in this spec and surfaced as a `CLAUDE.md` rule (see Layer 4) so future work does not silently re-merge the abstractions.

### Layer 4 — `CLAUDE.md` rule: live-failure fix discipline

Add the following section to [`CLAUDE.md`](CLAUDE.md) under the existing "Tests" heading (after the "UI test doctrine (spec 0206)" paragraph), shipped in the same PR as Layers 1–3:

```markdown
### Live-failure fix discipline (spec 0238)

A spec whose stated cause-of-death is a captured live-run failure MUST
include at least one test that exercises the **real entry point** of
the failing call path against the captured artifact (e.g. invoke
`parse_turn_v2` on the captured turn file). Function-level unit tests
that exercise a helper are insufficient on their own — they let a fix
land on the wrong function and pass.

Worked example: spec 0231 patched `extract_fenced_section` and tested
it in isolation. The live failure surfaced via `parse_turn_v2 →
_extract_section_body → SECTION_*_RE` — a path the 0231 tests never
exercised. The patch passed CI and the same bug class re-emerged on
the very next live run (spec 0238 root cause). The rule above prevents
the same shape of miss going forward.
```

This is the worked-example pairing Cowork called out (precedent: spec 0227 shipped its process rule with the motivating work).

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

None. No new event types, no state-file field changes, no migrations. The change is a regex-shape edit + a function extraction + a `CLAUDE.md` paragraph.

## 5. Out of scope

- **EDIT_SECTION anchor brittleness.** Drafter delta application matches `ANCHOR:` fields by exact string literal — same parser-fragility class at the delta-application surface, not the heading-anchoring surface. Parked at [`specs/drafts/draft-005-edit-section-exact-literal-anchor-brittleness.md`](specs/drafts/draft-005-edit-section-exact-literal-anchor-brittleness.md) with `disposition: defer`. Promotion trigger documented in the draft.
- **Block-level structured parser that ignores headings entirely.** Cowork explicitly rejected this as Q1's alternative on the grounds that it would regress spec 0122's body-scoring disambiguation. Not in scope; section structure remains load-bearing.
- **Boundary and capture regex changes.** `_TOP_HEADING_RE`, `_H2_RE`, `_DRAFT_SECTION_HEADING_RE` stay as-is (different abstractions, different roles, no glued-prose bug class).
- **Verifier I2.6 promotion to gating.** Tracked under spec 0232's §5 — promotion fires only after this spec ships AND the I2.6 verdict on the 142625 fixture flips to `pass`.
- **Retry-cap on `empty_turn_detected`.** Covered by spec 0239, lands in parallel; out of scope here.

## 6. Test plan

Tests live in a new file [`tests/test_spec_0238_parser_section_tolerance.py`](tests/test_spec_0238_parser_section_tolerance.py) (pure stdlib + `pytest`, no Playwright). Helper patterns adapted from [`tests/_ui_pattern_helpers.py`](tests/_ui_pattern_helpers.py) where useful.

- [ ] **Positive-pattern test (per regex, 11 total).** Each of the 8 SECTION_*_RE constants, plus the rebuilt `_REVISED_DRAFT_HEADING_RE`, plus the 2 `extract_review_items` patterns matches its canonical clean heading form.
- [ ] **Antipodal-absence-becomes-presence test (per regex, 11 total).** Each of the same 11 regexes, when fed the glued-prose variant (`"## <heading>Now I have the evidence…"` or analogous for the named heading), matches post-fix. Pre-fix this test would fail; post-fix it must pass. The test asserts the post-fix behaviour.
- [ ] **Variant battery on `SECTION_NEW_ITEMS_RE`** — match against (clean / trailing-whitespace / no-apostrophe / ALL-CAPS / trailing-period / trailing-colon+text / glued-letter). All 7 must match.
- [ ] **Integration test on the captured failing turn.** Load [`tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/phase2/round-01-claude.md`](tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/phase2/round-01-claude.md). Run `parse_turn_v2(text)`. Assert `len(parsed.raised_this_turn) == 5` AND `{r for r in parsed.raised_this_turn} == {"D-go-vs-csharp-21", "D-java-rank", "D-kotlin-mcp", "Q-csharp-implicit-penalty", "Q-rust-azure-sdk-ga"}` (verifies the 5 IDs that the STATUS line declared and the parser dropped). This is the worked example of the new CLAUDE.md "live-failure fix discipline" rule.
- [ ] **Spec 0122 regression guard.** Run the existing [`tests/test_spec_0122_*.py`](tests/) suite (or whatever name covers `_extract_section_body`'s body-scoring) and confirm green. If 0122 lacks an explicit test for the reasoning-preamble disambiguation, add one in this PR: a turn body with two `## Stance` headings (one as a reasoning preamble, one as the real STATUS-section sibling) must resolve to the second.
- [ ] **Backwards-compat on clean reference fixture.** Run `uv run pytest tests/ -q` end-to-end after the change. No pre-existing test changes verdict beyond the new tests added by this spec.
- [ ] **Verifier I2.6 verdict flip on the 142625 fixture.** Once I2.6 (spec 0232) is shipped and snapshot baselines are regenerated against the post-fix parser, the 142625 fixture's I2.6 entry must move from `fail (5 declared, 0 registered)` to `pass`. The 054652 fixture's pre-existing I2.6 verdict must remain unchanged (or also flip to pass — both outcomes acceptable, but no fixture goes from pass to fail).
- [ ] **CLAUDE.md rule added** under "Tests → Live-failure fix discipline (spec 0238)" with the worked-example text in Layer 4.
- [ ] **CHANGELOG entry under a new `## [X.Y+1.0] — 2026-05-27` heading** (MINOR bump) with `### Added` bullets for the primitive + the CLAUDE.md rule, and a `### Changed` bullet for the rebuilt SECTION_*_RE family; `pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.

## 7. Risks

- **Regex behaviour shift on call-sites we don't anticipate.** The new terminator is *strictly more permissive* than `\b` — every heading that matched pre-fix still matches post-fix, plus the glued cases now match. The only way the change can break a caller is if some downstream code relies on the section *not* matching when prose is glued (i.e. uses the bug as a feature). We searched for that pattern; no such reliance exists. Mitigation: the backwards-compat test (`uv run pytest tests/ -q` clean) catches anything we missed.
- **Auto-escape-vs-raw-fragment API choice.** Forcing callers to pass raw regex fragments creates a footgun where someone passes a string containing a regex metacharacter (e.g. a `.` or `(`) unescaped. Mitigation: every callsite in the same PR uses either `re.escape(...)` (the literal-heading callers) or a deliberate alternation pattern (the four with internal regex constructs). A future caller would have to actively bypass this convention; review will catch it. Alternative considered: a two-function API (`section_heading_literal(name)` vs `section_heading_pattern(name_pattern)`) — rejected as over-design for the number of callsites we have.
- **Drift between `extract_fenced_section`'s internal regex and the new primitive.** Mitigation: Layer 2 replaces `extract_fenced_section`'s inline regex with a call to `section_heading_re(re.escape(heading_name))` — the two paths share one source of truth post-merge. A test specifically asserts both paths return the same match-bounds for a representative heading.
- **CLAUDE.md rule misses a future class.** The rule names "captured live-run failure" as the trigger. A spec born from a hypothetical or anticipated failure would not be covered. Mitigation: the rule is a *floor*, not a *ceiling*; specs with synthetic-only evidence are still encouraged to test the real entry point. We do not codify this stronger form yet because it would require defining "real entry point" for non-live-failure specs, which is harder to make objective.
- **Revert path.** All three layers are local: a primitive function, regex re-bindings, function-extraction at one site, a CLAUDE.md paragraph. Reverting is a single `git revert` of this spec's PR; no migration to unwind. If post-merge surveillance shows a regression, we revert and re-design rather than patch.
