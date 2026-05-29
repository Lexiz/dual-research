---
spec: "0238"
date: 2026-05-27
version: 1.53.0
pr: https://github.com/Lexiz/dual-research/pull/274
---

# Spec 0238 — Parser primitive consolidation: one tolerant `section_heading_re` for every specific-literal-heading anchor

## What landed

A single public factory `section_heading_re(name_pattern, *, flags)` in [`src/dual_research/contract/markers.py`](src/dual_research/contract/markers.py) is now the source of truth for every specific-literal-heading anchor in the parser. The factory compiles `^## <name>(?:\s*$|(?=\S))` with default flags `re.MULTILINE | re.IGNORECASE`. The terminator branch `(?:\s*$|(?=\S))` matches either end-of-line (optionally with trailing whitespace) or a non-whitespace follow-on character (the glued-prose case that killed the 142625 run). The factory takes a raw regex fragment, not an auto-escaped string — callers needing internal alternation (`I'?m`, `Open questions for .+?`, `(?:\d+\.\s+)?Open Questions`) pass the fragment directly; literal-heading callers call `re.escape()` themselves.

Eight `SECTION_*_RE` constants in `markers.py` (Stance, Addressing, Ratifying, NewItems, PhaseArtifact, Status, RevisedDraft, CloseoutConstraints) are now built through the primitive. `_REVISED_DRAFT_HEADING_RE` at [`src/dual_research/protocol/parse.py:385`](src/dual_research/protocol/parse.py) is re-exported as a direct alias of `SECTION_REVISED_DRAFT_RE` so the "Revised draft" anchor cannot drift from the rest of the family. `extract_review_items` at [`src/dual_research/protocol/parse.py:1069`](src/dual_research/protocol/parse.py) builds its two anchors via the primitive. `extract_fenced_section` at [`src/dual_research/protocol/parse.py:179`](src/dual_research/protocol/parse.py) now calls `section_heading_re(re.escape(heading_name))` instead of constructing its regex inline — the two heading-anchor implementations Cowork's brief flagged as the real structural drift risk are now one.

Layer-3 scope boundary is preserved as spec §2.3 specified: `_TOP_HEADING_RE`, `_H2_RE`, `_DRAFT_SECTION_HEADING_RE` are boundary/capture regexes (different abstractions, different roles) and are NOT touched. The principled scope rule is now executable: every literal-heading anchor must go through `section_heading_re`, every boundary/capture scanner stays independent.

Layer-4 lands a new `### Live-failure fix discipline (spec 0238)` section in [`CLAUDE.md`](CLAUDE.md) under `## Tests` (immediately after the spec-0206 UI test doctrine paragraph). Specs whose stated cause-of-death is a captured live-run failure must include at least one test that exercises the **real entry point** of the failing call path against the captured artifact — function-level unit tests on helpers are insufficient on their own. The 0231 → 0238 mismatch is the worked example.

## Files touched

- [`src/dual_research/contract/markers.py`](src/dual_research/contract/markers.py) — `section_heading_re` factory + 8 SECTION_*_RE constants rebuilt through it.
- [`src/dual_research/protocol/parse.py`](src/dual_research/protocol/parse.py) — `section_heading_re` import; `extract_fenced_section` body simplified to one factory call; `_REVISED_DRAFT_HEADING_RE` re-exported as alias of `SECTION_REVISED_DRAFT_RE`; `extract_review_items`'s two anchor constructions go through the primitive.
- [`CLAUDE.md`](CLAUDE.md) — new `### Live-failure fix discipline (spec 0238)` section.
- [`tests/test_spec_0238_parser_section_tolerance.py`](tests/test_spec_0238_parser_section_tolerance.py) — 34 tests total: 11 positive × clean + 11 antipodal × glued parametrised cases, a 7-shape variant battery on `SECTION_NEW_ITEMS_RE`, an integration test invoking `parse_turn_v2` on the captured 142625 phase-2 r1 claude turn (verifies both the STATUS-line action array of 5 IDs *and* the 5 RaiseBlocks that the bug previously dropped), the `extract_fenced_section ⇄ SECTION_*_RE` shared-source-of-truth match-bounds invariant, an end-to-end round-trip through `extract_fenced_section` on a glued-prose heading, and source-pattern lock-in on the primitive's terminator + default flags.
- [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py), [`src/dual_research/ui/static/version-notes.json`](src/dual_research/ui/static/version-notes.json), `uv.lock` — MINOR bump 1.52.0 → 1.53.0.

`uv run pytest tests/ -q` → 2215 passed (34 new + 2181 pre-existing). Deploy `success` on GH Actions run [26532049027](https://github.com/Lexiz/dual-research/actions/runs/26532049027). `/api/health` reports `version: 1.53.0`.

## Deferred during implementation

- **Verifier I2.6 verdict flip on the 142625 fixture.** Spec §6 carried an expectation that the 142625 fixture's I2.6 entry would move from `fail (5 declared, 0 registered)` to `pass` once the parser fix lands. It does not. The verifier reads `transcript.jsonl` (frozen at the dead state — zero `item_raised` events were ever registered) plus the turn files; the parser fix does not retroactively populate the frozen transcript. The verdict flip requires re-running the fixture's turns through the post-fix parser and `apply_turn` to generate fresh `item_raised` events, which is the same regen-fixture machinery the [spec 0232 handoff §44](handoffs/2026-05-27-spec-0232-verifier-i2-6-status-raised-event-cross-check.md) already flagged as a "separate small spec per §5" (the §6 promotion trigger for I2.6 → gating). The `test_snapshot_142625_i2_6_slug_drop_fail` test in `tests/test_verifier.py:946` continues to pass green post-fix — the snapshot and the frozen reality remain consistent. No regression; the gap is solely in §6's verdict-flip expectation, which conflated the parser fix's effect on new runs with its effect on frozen fixtures.

## Notes for follow-ups

- **Risk that did not materialise.** Spec §7 named "regex behaviour shift on call-sites we don't anticipate" — `extract_fenced_section` and `_REVISED_DRAFT_HEADING_RE` going through `section_heading_re` pick up `re.IGNORECASE` as a side effect. Full `pytest tests/ -q` clean indicates no caller relied on the prior case sensitivity. The CHANGELOG `### Changed` bullet calls out the behaviour shift explicitly for downstream readers.
- **Risk that the consolidation introduced.** The `extract_fenced_section ⇄ SECTION_*_RE` shared-source-of-truth match-bounds invariant (test in `tests/test_spec_0238_parser_section_tolerance.py:178`) is the single executable lock against the two paths drifting again — any future edit to the primitive that changes match bounds would surface there. If a future spec needs the two paths to diverge intentionally, that test must be updated, not deleted.
- **EDIT_SECTION anchor brittleness (spec §5 out of scope).** Parked at [`specs/drafts/draft-005-edit-section-exact-literal-anchor-brittleness.md`](specs/drafts/draft-005-edit-section-exact-literal-anchor-brittleness.md) with `disposition: defer`. Promotion trigger documented in the draft.
- **Retry-cap on `empty_turn_detected` (spec §5 out of scope).** Covered by spec 0239 per the spec body — separate landing.
