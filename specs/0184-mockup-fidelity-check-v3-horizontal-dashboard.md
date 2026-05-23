---
kind: dev
spec: "0184"
slug: mockup-fidelity-check-v3-horizontal-dashboard
title: "Tests: pixel + structural fidelity check of the live dashboard against `dashboard-redesign-v3-horizontal.html`"
type: test
label: test
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 7
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T21:55:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0177
promoted_from_draft: ""
---

# Spec 0184 — Tests: pixel + structural fidelity check of the live dashboard against `dashboard-redesign-v3-horizontal.html`

> **Type:** test  |  **Complexity:** S
> **Bump:** PATCH — test additions only.
> **Evidence:** Spec 0177 handoff `## Deferred during implementation` third bullet — [handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:42](handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:42). The implementer noted: *"the implementation followed the mockup's HTML/CSS contract, but no pixel-level comparison against `dashboard/mockups/dashboard-redesign-v3-horizontal.html` was done. The risk is small (mostly token swaps and structural mirroring), but minor spacing / proportion drift is possible."*

---

## 1. Coverage gap

The dashboard renderer at [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) emits production HTML+CSS matching a static mockup at [dashboard/mockups/dashboard-redesign-v3-horizontal.html](dashboard/mockups/dashboard-redesign-v3-horizontal.html). Spec 0177's test surface ([tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py)) asserts:

- the **count** of `.tl__step` nodes equals 11 (one per stage);
- the presence of `counter--accent` and `chart-card` classes;
- the existence of pastel `--chart-*` tokens in both themes;
- a `.pager` strip on long lists;
- `data-theme="light"` on first visit.

But nothing in the suite asserts **structural parity** between the rendered HTML and the mockup. There is no test that, for example, requires the `.tl` block to be a sibling of `.hero` (not a child), or that the 5-counter row sits *after* the hero (not before), or that the same grid-column proportions land. So a refactor that moves blocks around inside the page chrome (or a CSS regression that changes the `.tl__rail` proportions) lands silently as long as the individual elements still exist.

Two un-covered surfaces in particular:

- **DOM structure** — the spatial relationship between the hero, stage timeline, counter row, and tab strip. Mockup-derived. Not asserted today.
- **Computed style budget** — the rendered widths, heights, gaps, padding tokens used by `.tl`, `.tl__rail`, `.tl__rail-done`, `.tl__node`, `.tl__step`. Drifting from the mockup here is the "minor spacing / proportion drift" the implementer flagged.

## 2. Test approach

Two complementary tests, both pure-Python (no browser, no Playwright, no js2py) so they run inside the existing `uv run pytest tests/ -q` flow without new dependencies.

### 2.1 — Structural-parity assertions

A new test file `tests/spec_lifecycle/test_dashboard_mockup_parity.py` that loads both the rendered HTML and the mockup, parses both with the standard-library `html.parser`, and extracts a normalised "structural tree" — a tuple of `(tag, class_list)` pairs in document order, ignoring text nodes, inline event handlers, and `data-*` attributes that come from runtime state (the spec ids, timestamps, regions).

Then asserts that the rendered HTML's structural skeleton **contains as a subsequence** the mockup's structural skeleton for these key regions:

- The `.hero` → `.tl` → `.counters` ordering under `.page`.
- The 11-node `.tl__step` row immediately under `.tl__steps`.
- The 5-card `.counter` row under `.counters`, with the 5th carrying `counter--accent`.
- The tab strip's button order: `Now`, `Spec creation`, `History`, `Metrics`.

Subsequence (not exact) matching tolerates new wrapper divs the implementer adds for region-swap targets — exactly the kind of structure the mockup doesn't have but the live renderer does (`<div data-region="…">`). The test still catches reordering.

### 2.2 — Token-budget assertions

A second test in the same file extracts all `--md-*` and `--p-*` and `--chart-*` token references from the CSS classes used in the rendered output for the timeline, counters, and chart regions. Compares against the same references in the mockup's inline `<style>` block. Asserts:

- Every token the mockup uses for the timeline / counters / charts is also used in the corresponding region of the live render.
- No hex codes leaked into the live render (tokens-only rule from [CLAUDE.md](CLAUDE.md) "Design system" section).

This catches the case where the live renderer drifts to a non-token color (e.g. accidentally writing `#7c8aff` instead of `var(--p-accent)`), and the case where a future refactor swaps a token (e.g. `--md-on-surface` → `--md-on-surface-faint`) on a region that the mockup specifically called out.

### 2.3 — Optional follow-up (out of scope here)

A browser-driven pixel diff via Playwright would close the "minor spacing / proportion drift" risk fully — but it adds a heavy runtime dependency. Defer to a separate spec only if the structural + token tests prove insufficient over the next few cycles.

## 3. What it would catch

- **Spec 0177's deferred risk** — the implementer noted spacing / proportion drift is possible. A future spec that touches `.tl__rail` proportions (e.g. moving from `calc((done/total) * (100% - 28px))` at [scripts/spec_lifecycle/render_dashboard.py:3263](scripts/spec_lifecycle/render_dashboard.py:3263) to a different formula) would change the rendered `.tl__rail-done` `style` attribute. The structural test would flag the change as a diff against the mockup's reference proportion.
- **Reordering regressions** — a refactor that moves the counter row above the hero (vs the mockup's hero → timeline → counters ordering established at [scripts/spec_lifecycle/render_dashboard.py:903-1043](scripts/spec_lifecycle/render_dashboard.py:903)) would break the subsequence test immediately. Without this test, the regression lands silently because spec 0177's tests only count elements.
- **Token drift** — a future change that writes a hex code directly into the metrics chart SVGs (e.g. for a one-off accent) instead of using `--chart-*` would fail the token-budget test. Today nothing catches this except review.
- **Stage-count drift** — already covered by spec 0177's `test_idle_vs_inflight_hero`, but a different failure mode (the 11 steps render in the wrong order — e.g. `pr_opened` before `branched`) is NOT covered today and IS covered by the subsequence test in §2.1.

The historical class of failure mode this prevents: spec 0169 → 0177 went through several rounds of "the live dashboard looks different from the mockup we agreed on" without a programmatic guard. Each cycle relied on a manual visual compare. Codifying the mockup as the contract means the comparison runs on every PR.

## 4. Risks

- **False positives on legitimate edits.** A future spec that intentionally moves blocks around (e.g. swaps counter and timeline ordering for a v4 redesign) must update the mockup file *as part of the same PR*. Workflow risk — easy to forget. Mitigation: a one-paragraph note in [CLAUDE.md](CLAUDE.md) "Dashboard" section codifying "edit the mockup + the renderer in the same commit when reshaping the dashboard". Out of scope for this spec — that's a process change. The test author can opt to add the note inside this PR if it lands cleanly.
- **HTML-parser brittleness.** The standard-library `html.parser` is lenient but quirky. Mitigation: prefer `lxml.html` if it's already in the dev dependency set; otherwise stick with stdlib and add a focused unit test for the structural-extractor itself.
- **Slow test runs.** Parsing two HTML files and comparing tree shapes is sub-100ms per test. Total impact on the 19.6s suite from the 0177 handoff is negligible. No flakiness risk — both inputs are deterministic strings.
- **Over-mocking risk.** This test deliberately operates on the *real* rendered HTML (via `render_index` called with a small fixture) — not a stubbed version. The fidelity guarantee comes from comparing real output to the mockup, not from re-implementing the renderer inside the test. Resist the temptation to mock `render_index` or to short-circuit the comparison to single-element assertions.
- **Pixel-level drift not caught.** The structural + token tests catch *category* drift (wrong ordering, wrong token), not *pixel* drift (right token, wrong computed pixel after CSS cascade). A 2-pixel padding miss that no token would have caught is still invisible to this spec. The spec 0177 handoff said *"minor spacing / proportion drift is possible"* — accept that this spec catches the structural half and a follow-up Playwright-based spec (deferred) catches the pixel half.
