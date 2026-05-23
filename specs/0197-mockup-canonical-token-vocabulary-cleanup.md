---
kind: dev
spec: "0197"
slug: mockup-canonical-token-vocabulary-cleanup
title: "Refactor: rewrite dashboard mockup to use canonical DS token names so the parity allowlist shrinks to empty"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 3
depends_on: []
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T12:15:45Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0184
promoted_from_draft: ""
---

# Spec 0197 — Refactor: rewrite dashboard mockup to use canonical DS token names so the parity allowlist shrinks to empty

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — mockup vocabulary swap + test-side allowlist drop. No behavior change, no live-render change.
> **Evidence:** Spec 0184 handoff `## Deferred during implementation` — [handoffs/2026-05-23-spec-0184-mockup-fidelity-check-v3-horizontal-dashboard.md:44](handoffs/2026-05-23-spec-0184-mockup-fidelity-check-v3-horizontal-dashboard.md:44): *"Mockup uses 3 non-canonical shorthand tokens (`--accent`, `--font-data`, `--font-plain`) that pre-date the project's DS token naming pass. Live render uses canonical names. The token-budget test currently tolerates these via a documented `_MOCKUP_SHORTHAND_ALLOWLIST`. The proper fix is to rewrite the mockup to use canonical tokens — then this allowlist shrinks to `{}`. The mockup is 1140 lines so it's a separate edit, not a one-liner in the test file."*

---

## 1. Current state

The dashboard mockup at [dashboard/mockups/dashboard-redesign-v3-horizontal.html](dashboard/mockups/dashboard-redesign-v3-horizontal.html) declares and consumes three non-canonical CSS custom properties that pre-date the DS naming pass that produced the canonical `--md-*` / `--p-*` vocabulary in [design-system/assets/styles/tokens-and-primitives.css](design-system/assets/styles/tokens-and-primitives.css):

- `--accent` — declared at [dashboard/mockups/dashboard-redesign-v3-horizontal.html:29](dashboard/mockups/dashboard-redesign-v3-horizontal.html:29) (dark, `#a371f7`) and [dashboard/mockups/dashboard-redesign-v3-horizontal.html:59](dashboard/mockups/dashboard-redesign-v3-horizontal.html:59) (light, `#6639ba`); consumed at [dashboard/mockups/dashboard-redesign-v3-horizontal.html:268](dashboard/mockups/dashboard-redesign-v3-horizontal.html:268) (`.counter--accent .counter__num { color: var(--accent); }`) and a handful of mockup-banner / inline-style sites (`grep -n '\-\-accent\b' dashboard/mockups/dashboard-redesign-v3-horizontal.html` returns 8 references).
- `--font-plain` — declared at [dashboard/mockups/dashboard-redesign-v3-horizontal.html:30](dashboard/mockups/dashboard-redesign-v3-horizontal.html:30); consumed pervasively across `.dh__*`, `.hero__*`, `.tl__*`, `.counter__*`, `.tab*`, `.qrow__*`, `.feed__*` typography rules. Roughly 40+ references.
- `--font-data` — declared at [dashboard/mockups/dashboard-redesign-v3-horizontal.html:31](dashboard/mockups/dashboard-redesign-v3-horizontal.html:31); consumed in `.chip code`, `.hero__big`, `.counter__num`, `.qrow__id`, `.qrow__age`, `.feed__ts`, `.feed__dur`. Roughly 15+ references. (Combined font-token consumption: 54 references — `grep -c '\-\-font-data\|--font-plain' dashboard/mockups/dashboard-redesign-v3-horizontal.html`.)

The live renderer at [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) emits the canonical names: `var(--p-info)` for the accent counter at [scripts/spec_lifecycle/render_dashboard.py:2638](scripts/spec_lifecycle/render_dashboard.py:2638) (`.counter--accent .counter__num { color: var(--p-info); }`), and `var(--md-font-plain)` / `var(--md-font-data)` everywhere typography is set (see e.g. [scripts/spec_lifecycle/render_dashboard.py:1014](scripts/spec_lifecycle/render_dashboard.py:1014), [scripts/spec_lifecycle/render_dashboard.py:1088](scripts/spec_lifecycle/render_dashboard.py:1088), [scripts/spec_lifecycle/render_dashboard.py:2192](scripts/spec_lifecycle/render_dashboard.py:2192), [scripts/spec_lifecycle/render_dashboard.py:2221](scripts/spec_lifecycle/render_dashboard.py:2221) — and the SVG `font-family` attributes that emit `var(--md-font-data)` directly).

The pain: spec 0184's token-budget parity test at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:301](tests/spec_lifecycle/test_dashboard_mockup_parity.py) — `test_live_css_uses_every_token_the_mockup_uses_for_timeline_counters_charts` — would fail without the shorthand allowlist at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:294](tests/spec_lifecycle/test_dashboard_mockup_parity.py:294):

```python
_MOCKUP_SHORTHAND_ALLOWLIST = {
    "--accent",      # canonical: --p-accent
    "--font-data",   # canonical: --md-font-data
    "--font-plain",  # canonical: --md-font-plain
}
```

Three downstream costs of keeping this allowlist:

1. The mockup is no longer a faithful "what the live render should emit" reference — it's "what the live render should emit, modulo three tokens you have to know about." Future contributors who consult the mockup as the design contract will see `var(--accent)` and reasonably assume they should emit the same token in new live-render rules, then discover at PR-review time that the canonical name is different.
2. The parity test's failure message at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:313-320](tests/spec_lifecycle/test_dashboard_mockup_parity.py:313) explicitly says "Either the live render dropped them (regression) or the mockup needs updating to match a renamed token (workflow risk — flagged in spec 0184 §4)." That workflow risk is exactly what the allowlist papers over today — every new token renaming has to weigh "do I rename in the mockup or grow the allowlist?"
3. The handoff for spec 0184 also notes that the inaccuracy is asymmetric: the handoff prose says canonical is `--p-accent`, but the actual live render emits `--p-info` for the counter accent. Two near-but-not-identical naming hypotheses are coexisting in the codebase docs — exactly the kind of low-grade ambiguity a vocabulary-cleanup spec exists to remove.

## 2. Target state

[dashboard/mockups/dashboard-redesign-v3-horizontal.html](dashboard/mockups/dashboard-redesign-v3-horizontal.html) uses canonical DS token names end-to-end for the three shorthand entries. The replacements are:

- `--accent` → `--p-info` (matches what [scripts/spec_lifecycle/render_dashboard.py:2638](scripts/spec_lifecycle/render_dashboard.py:2638) actually emits for `.counter--accent`).
- `--font-plain` → `--md-font-plain` (declared at [design-system/assets/styles/tokens-and-primitives.css:91](design-system/assets/styles/tokens-and-primitives.css:91); referenced live e.g. at [scripts/spec_lifecycle/render_dashboard.py:2192](scripts/spec_lifecycle/render_dashboard.py:2192)).
- `--font-data` → `--md-font-data` (declared at [design-system/assets/styles/tokens-and-primitives.css:93](design-system/assets/styles/tokens-and-primitives.css:93); referenced live e.g. at [scripts/spec_lifecycle/render_dashboard.py:939](scripts/spec_lifecycle/render_dashboard.py:939)).

The mockup keeps its other locally-declared tokens unchanged (`--bg`, `--surface-*`, `--hair`, `--hair-strong`, `--text-1/2/3`, `--info`, `--ok`, `--warn`, `--err`, `--idle`, `--chart-*`) — those are scoped to selectors the parity test's `_TOKEN_REF_RE` at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:259](tests/spec_lifecycle/test_dashboard_mockup_parity.py:259) does not match (the regex only captures prefixes `md|p|chart|accent|panel|elev|font|dur|easing|on`). Those are local to the mockup's standalone-preview chrome and outside the scope of this cleanup; reshaping them would expand this spec into "rewrite the whole mockup's token vocabulary," which the deferral did not ask for and which has no parity-test pressure behind it.

The mockup's `:root` and `html[data-theme="light"]` blocks need a small structural change: today they declare `--accent` with two different hex values (dark / light), so a literal find-and-replace of the variable name plus a hex-aware swap is required. The canonical `--p-info` is declared once in [design-system/assets/styles/tokens-and-primitives.css:13](design-system/assets/styles/tokens-and-primitives.css:13) (`#6b9cf0`) and does not currently have a per-theme override there either — so the mockup's standalone preview gets a single `--p-info` declaration (one hex per theme block) preserving the existing visual differentiation between dark and light. The dark value stays `#a371f7` and the light value stays `#6639ba` for visual continuity of the mockup-as-image; canonical-name parity is what matters to the test, not exact hex values.

Concretely: the mockup keeps its own `--p-info` declarations in both `:root` and `html[data-theme="light"]` so its standalone preview renders identically to today. The live render's `--p-info` is what spec 0184's parity test compares against (token-name parity, not hex parity).

For the fonts: the mockup's `--md-font-plain` / `--md-font-data` declarations land in `:root` (no per-theme override needed — fonts don't vary by theme).

After the mockup rewrite, the test-side allowlist at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:294](tests/spec_lifecycle/test_dashboard_mockup_parity.py:294) shrinks from three entries to an empty set, and the comment block at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:288-293](tests/spec_lifecycle/test_dashboard_mockup_parity.py:288) is rewritten to record that the allowlist is now empty by design — kept as a hook for any future shorthand drift to be explicit about.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1 — Swap the three token declarations + every consumer site in [dashboard/mockups/dashboard-redesign-v3-horizontal.html](dashboard/mockups/dashboard-redesign-v3-horizontal.html).** A literal find-and-replace within the file body of `var(--accent)` → `var(--p-info)`, `var(--font-plain)` → `var(--md-font-plain)`, `var(--font-data)` → `var(--md-font-data)`. Then rename the three declarations themselves in `:root` and `html[data-theme="light"]` so the standalone preview still resolves. *Verifies:* `grep -n '\-\-accent\b\|--font-plain\b\|--font-data\b' dashboard/mockups/dashboard-redesign-v3-horizontal.html` returns zero lines. The standalone preview (open the HTML file directly in a browser) renders the same as today.

- **Step 2 — Shrink the allowlist in [tests/spec_lifecycle/test_dashboard_mockup_parity.py:294](tests/spec_lifecycle/test_dashboard_mockup_parity.py:294).** Replace the three-entry set with `_MOCKUP_SHORTHAND_ALLOWLIST: set[str] = set()`. Rewrite the comment block at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:288-293](tests/spec_lifecycle/test_dashboard_mockup_parity.py:288) to say the allowlist is now empty by design — preserved as a single named extension point if a future shorthand must be tolerated again. *Verifies:* `uv run pytest tests/spec_lifecycle/test_dashboard_mockup_parity.py -v` — all 6 assertions still pass (the parity assertion in particular now passes against an empty allowlist).

- **Step 3 — Full test suite + visual smoke.** `uv run pytest tests/ -q` should still be green at the same count it was post-spec-0184 (1676). Open the mockup HTML directly in a browser to confirm the standalone preview is visually unchanged. No live-render change to deploy or smoke. *Verifies:* zero regressions land with the rename; the mockup-as-static-design-doc still reads the same.

The three steps land as a single PR — they only make sense together, and reverting requires reverting all three. The "stepwise" framing is for review-time reasoning, not for separate commits.

## 4. Behavior preservation

- [ ] `uv run pytest tests/ -q` still green at 1676 passed (the same count spec 0184's handoff at [handoffs/2026-05-23-spec-0184-mockup-fidelity-check-v3-horizontal-dashboard.md:25](handoffs/2026-05-23-spec-0184-mockup-fidelity-check-v3-horizontal-dashboard.md:25) reports).
- [ ] `uv run pytest tests/spec_lifecycle/test_dashboard_mockup_parity.py -v` — all 6 assertions pass, including the token-budget assertion now matching against `_MOCKUP_SHORTHAND_ALLOWLIST == set()`.
- [ ] Existing test `tests/spec_lifecycle/test_render_dashboard_spec_0177.py` — unchanged, no edits to the renderer.
- [ ] Existing test `tests/spec_lifecycle/test_render_dashboard.py` — unchanged, no edits to the renderer.
- [ ] Manual visual smoke: open `dashboard/mockups/dashboard-redesign-v3-horizontal.html` in a browser; the standalone preview's colors and typography are visually identical to pre-rewrite (same hex values, same font stacks, just under canonical token names).
- [ ] No live-render changes: no edits anywhere under [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py), [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css), [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css), or [design-system/assets/styles/tokens-and-primitives.css](design-system/assets/styles/tokens-and-primitives.css). The live deployed dashboard at `https://dual-research-alex.fly.dev/` is byte-identical post-merge.

## 5. Out of scope

**Explicit: no new feature ships here.** This spec only renames mockup-internal tokens to match the canonical DS vocabulary so the test-side allowlist can collapse to empty. No live-render change, no DS-token addition, no test-coverage addition.

- **Renaming the mockup's other non-canonical tokens** (`--bg`, `--surface-*`, `--text-*`, `--info`, `--ok`, `--warn`, `--err`, `--idle`, `--hair`, `--hair-strong`, `--chart-*`). The parity test's `_TOKEN_REF_RE` at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:259](tests/spec_lifecycle/test_dashboard_mockup_parity.py:259) doesn't capture these prefixes, so they create no test-side pressure. If a future spec wants full canonical alignment of the mockup, that's a separate refactor with its own scope review. The deferral text named exactly three tokens; this spec stays inside that boundary.
- **Generalizing the mockup-parity test to cover the entire token vocabulary.** Spec 0184 §2.3 explicitly defers Playwright-based pixel diffing; broadening the token regex is the same shape of "stronger parity contract" that should ship as its own dedicated spec with its own risk review.
- **Canonical-naming changes anywhere outside the mockup file.** The renamer touches one HTML file and one test file. No `.py`, no `.css`, no other `.html`.
- **Adding a per-theme `--p-info` override to [design-system/assets/styles/tokens-and-primitives.css](design-system/assets/styles/tokens-and-primitives.css).** The canonical token is declared once today; the mockup gets its own per-theme override for standalone-preview continuity. Changing the DS itself to gain a per-theme accent would be a feature work landing under a separate spec.

## 6. Risks

- **Hidden behavior depending on internals — broken consumers of the old names.** If any other file in the repo references `--accent`, `--font-plain`, or `--font-data` (declared by the mockup's `:root`) and expects to inherit from a stylesheet that loads the mockup, those references break. *Mitigation:* the mockup is a standalone preview HTML — its `<style>` block is not loaded anywhere else; verify by `grep -rn '\-\-accent\b\|--font-plain\b\|--font-data\b' .` excluding `dashboard/mockups/` and `tests/spec_lifecycle/test_dashboard_mockup_parity.py` before the swap. Expected: zero matches under `src/`, `design-system/`, `scripts/`, `dashboard/` (excluding the mockup itself), and `prototypes/`. Any hit gets reviewed in-spec.
- **Performance regression.** N/A — token renames in a static HTML file have zero runtime cost.
- **Missed call site within the mockup.** The find-and-replace must cover both `var(--name)` lookups *and* the bare declaration lines in `:root` / `html[data-theme="light"]`. *Mitigation:* the post-step-1 verifier (`grep -n '\-\-accent\b\|--font-plain\b\|--font-data\b' dashboard/mockups/dashboard-redesign-v3-horizontal.html` returns zero lines) catches both halves in one check; if anything is missed the grep flags it before the test step.
- **Test-side comment drift.** The comment block at [tests/spec_lifecycle/test_dashboard_mockup_parity.py:288-293](tests/spec_lifecycle/test_dashboard_mockup_parity.py:288) currently explains why the allowlist exists. After the rename, that explanation is stale. *Mitigation:* step 2 explicitly rewrites the comment so the kept-but-empty allowlist stays as a self-documented extension point rather than a confusing artifact. If the allowlist itself is also removed (turned into an inline `set()` literal), the comment can be deleted entirely — author's choice at implementation time, both are acceptable.
- **Mockup-preview visual drift.** A typo in the rename (e.g. mistyping `--md-font-plain` as `--md-font-plian`) would silently fall back to the browser default font in the standalone preview, while the parity test against the canonical-named live render still passes (because the live render has the correct name). *Mitigation:* the manual visual smoke in step 3 is the last line of defense; cheap and high-signal (one browser refresh).
