---
spec: "0205"
date: 2026-05-24
version: "1.44.2"
pr: "https://github.com/Lexiz/dual-research/pull/235"
kind: cycle-handoff
---

# Spec 0205 — Fix: P4 critique card five visual regressions (shipped v1.44.2)

Five visual regressions on the P4 Review critique pane landed as one coherent PATCH bundle, matching the user's "bugfix pack" framing in the spec.

- **Bug 1 — Sources segment + expanded SourceRow layout.** `.item-card__sources` now carries `padding: 10px 16px 14px` so the segment sits inside the card chrome (matches the lifecycle section's 16 px interior gutter); each expanded row's content excerpt renders as a tinted `<blockquote>` with `--md-outline` brand-toned left border and italic-serif typography. URL · FETCHED · SEARCH QUERY render as `(t-overline label) · value` grid rows instead of inline spans. Pre-0205 the excerpt was a `<pre>` block that read as raw debug output and the whole segment went full-bleed against the card frame.
- **Bug 2 — Lifecycle leads Issue / Comment bodies.** `ItemCardIssueBody` / `ItemCardCommentBody` stripped the standalone `<Markdown text={String(item.body)}/>` block above the lifecycle. `ItemCardLifecycleSection` already carries `item.body` as the raise row's quote (lc-row-quote at L1647-1651), so the standalone block was a duplicate. The inline anchor blockquote (`.item-card__quote-inline`) — a different field, the quoted span the item attaches to in the source draft — sits below the lifecycle with `margin: 0 16px 14px` to align with the lifecycle's interior gutter.
- **Bug 3 — Canonical sources glyph.** `mdi:link-variant` on `.item-card__sources-hd` segment header and the P3 ReviewCard's Sources chip. Same glyph as the head's evidence-required chip + the lifecycle source-requested / source-provided chips so every sources surface reads as one visual vocabulary. Documented in `design-system/SPEC.md` §4.7.
- **Bug 4 — Kind filter chips use the Chip primitive.** Bar 2 swapped from `<TabGroup variant="kind-tabs">` + four `<Tab variant="kind">` segmented buttons to four `<Chip>` instances inside a new `.kind-chip-row` wrapper. Per-kind tone (`info` / `warn` / `err` / `idle`), Q/D/I/C `categoryBubble`, `label`, trailing count `value`, and `data-active="true"` for the active-state lift via `--md-elev-1`. `_ITEM_KIND_TONE` / `_ITEM_KIND_LETTER` / `_ITEM_KIND_LABEL` (`run-detail.jsx` L1521-L1530) stay the single source of truth — same constants the head's kind chip reads, so the filter and card vocabulary stay locked.
- **Bug 5 — Provider raiser on every critique card.** **Root cause was a wire-name mismatch**, not a missing field. The unified `Item` shape (`models.py:480`) carries `raiser: str` ("claude" | "openai") and is projected to `run.phaseStats.items` for ItemCard consumption — camelized to `raiser` on the wire, not `raisedBy`. `ItemCard` was reading only `item.raisedBy`. `ItemCardLifecycleSection` already checked both at L1554 (`item.raisedBy || item.raiser`); the head was the only surface missing the alias. Two-pronged fix: (1) head now reads both. (2) The fallback for an unresolved raiser is no longer `<SystemChip />` (reserved for the Phase 0 brief card per DS §4.4) — it's an `err`-toned `Unknown raiser` chip plus a `console.warn` so any future data-layer regression surfaces loudly. Documented in DS §4.8 + the `SystemChip` row of the Identity primitives table.

DS prose updated in `design-system/SPEC.md` §4.7 (sources glyph + interior gutter + excerpt blockquote shape), §4.8 (lifecycle-first stacking for Issue / Comment, Bar 2 chip primitive, provider must be Claude or GPT), and the `SystemChip` row of the §4 Identity primitives table (reserved-scope clarification). CSS landed in BOTH `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css` per the DS same-commit invariant.

## State at deploy

- Both machines (`2870421c037148`, `2873d39cd92438`) running `deployment-01KSC1RJ7J5V5TRF90PBMRBTFD` (release 630).
- `/api/health` returns `{"ok":true,"version":"1.44.2","backend":"supabase"}` in ~2 s.
- Tests: **1870 passed** (`uv run pytest tests/ -q`, 23.33 s). Eight new in `tests/test_spec_0205_critique_card.py`; two updated in `tests/spec0172/test_critique_card_markdown_and_no_sid.py` to reflect the lifecycle-first body shape.

## Deploy notes

`fly deploy` returned exit 0 cleanly. The five-case matrix triggered on /api/health timing out after the initial deploy — both machines were `stopped` and an auto-start request looped on `machines API returned an error: "machine ID 2870421c037148 lease currently held by 218ae43d-f1d6-…@tokens.fly.io, expires at 2026-05-24T03:58:00Z"`. This is the canonical fly lease drift scenario (`project_fly_lease_drift_recovery.md`): the new image was already live (version 630 with the new image hash), but the deploy command's lease hadn't been released, so the proxy's auto-start couldn't acquire the machines to start them. After the lease's natural expiry at `03:58:00Z`, both machines started cleanly (one at 1/1, the other warming at 0/1) and `/api/health` returned 1.44.2 in ~2 s. `scripts/sweep_stale_blues.sh` reported `sweep: no stale blues on dual-research-alex` — under rolling, the tag-based primary filter finds zero candidates and the image-based fallback handles cleanup.

The 30 s curl `HTTP 000 / INTERNAL_ERROR` early diagnostic was a symptom of the lease-held auto-start loop, not a real cluster failure. Matrix case routing was effectively case 2 (mixed/all new but slow to converge) — proceed-with-verification rather than halt; the resolution path was waiting for the lease to expire rather than redeploying.

## What was changed

- `src/dual_research/ui/static/run-detail.jsx` — Bug 5 (head raiser fallback at L1849 + providerChip block); Bug 2 (Issue / Comment body shape); Bug 4 (kind filter row → `.kind-chip-row` with four `Chip` instances); Bug 3 (Sources segment header + ReviewCard chip both gain `Mdi name="link-variant"`); Bug 1 (SourceRow body restructured: label · value rows + `<blockquote>` excerpt).
- `src/dual_research/ui/static/components.css` — `.item-card__sources` interior padding; `.item-card__sources-hd` flex layout for icon + label; `.source-row__field` two-column grid; `.source-row__excerpt` tinted blockquote; `.source-row__excerpt-wrap` gap; `.item-card__quote-inline` margin to align with lifecycle gutter; `.kind-chip-row` wrapper + active-state lift + narrow-mode label collapse.
- `design-system/assets/styles/composed-components.css` — mirrors all of the above per the DS same-commit invariant.
- `design-system/SPEC.md` — §4.7 (sources glyph + interior gutter + excerpt blockquote prose); §4.8 (lifecycle-first stacking for Issue / Comment, Bar 2 chip primitive note); SystemChip row of the §4 Identity primitives table (reserved scope).
- `tests/test_spec_0205_critique_card.py` — 8 new static-pattern tests, one pair per Bug N.
- `tests/spec0172/test_critique_card_markdown_and_no_sid.py` — updated `test_issue_body_renders_full_markdown` → `test_issue_body_does_not_split_on_newline` (lifecycle leads now) and `test_comment_body_unchanged_shape` → `test_comment_body_lifecycle_leads`.
- `CHANGELOG.md`, `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — version bump 1.44.1 → 1.44.2 + release notes.

## Deferred during implementation

- **Playwright DOM tests as prescribed by spec §5.** The spec called for Playwright tests at `tests/ui/test_p4_critique_card.py`, but this codebase has no Playwright infrastructure (no `playwright` import in any test, no harness, no fixture set). Substituted with static-pattern tests in `tests/test_spec_0205_critique_card.py` that lock the same anatomical contract via the JSX / CSS source (one pair of tests per Bug N — kind-chip-primitive presence + absence of legacy variant attrs, lifecycle-as-first-child + absence of Markdown body block, sources `<blockquote>` + brand-toned border, `item.raisedBy || item.raiser` + absence of `<SystemChip>` in the fallback). The live-browser verification (Claude Preview MCP at `localhost:6173`) provides the runtime check the static tests can't. If the project ever stands up a Playwright harness, follow-up dev spec converts the 8 source-pattern tests to DOM tests against a fixture run.

- **8-capture ItemCard parity grid in the PR description.** Spec §8 risks called out the `design-system/SPEC.md:378` (spec 0179) requirement to embed a side-by-side image grid (4 kinds × 2 states next to the four reference shots). The PR description includes a single-frame screenshot of the post-fix P4 Review showing the kind chip row + a Claude-headed Issue card body with lifecycle leading, but not the full 8-capture grid. The reference shots themselves predate spec 0203's head rewrite + this spec's body reordering — the cleanest path is a follow-up spec that refreshes the reference set against the new lifecycle-first shape and embeds the grid.

- **Dead `.kind-tab` / `.kind-tabs` CSS rules + `shared.jsx` `variant="kind"` / `variant="kind-tabs"` JSX branches.** Spec §3.4 authorised removal IFF nothing else depends on them. Grep confirmed no other call sites in `src/dual_research/ui/static/`. Left in place to keep the bugfix PR scoped to the regression bundle — the cleanup is unrelated to the user-visible symptoms and would add removal risk for a future surface that hasn't migrated. The DS prose at §4.8 explicitly notes the legacy rules survive for "any pre-0205 surface that hasn't migrated".

## Out of scope (per spec §7, unchanged)

- ItemCardLifecycleSection internals (chip cluster + `.lc-row-quote` formatting).
- Terminal-state footer (`lifecycleFooter` at `run-detail.jsx:1843-1849`).
- Wire-format changes beyond the head's raiser-name alias.
- Σ Summary or P0 / P2 critique sub-renderers — P4-only per the user-reported screenshots.
- `design-system/SPEC.md` updates beyond §4.7 (sources glyph + excerpt shape), §4.8 (stacking order + filter chip primitive), and the §4 SystemChip row.
