---
kind: dev
spec: "0207"
slug: fix-link-variant-icon-missing
title: "Fix: link-variant icon missing from registry — evidence/sources badges render as blank blue square"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-24
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

# Spec 0207 — Fix: link-variant icon missing from registry — evidence/sources badges render as blank blue square

> **Type:** bug  |  **Severity:** P2  |  **Affects:** P4 ItemCard head (evidence-needed chip), P4 ItemCard sources segment header, P3 ReviewCard head Sources chip, plus three lifecycle-footer call sites.
> **Bump:** PATCH — bug fix
> **Evidence:** User screenshot from /#/run/20260521-0106… P4 critique view showing a resolved Claude-raised Issue card with the head ending in `Claude · Raised · R1 · Issue · ▢` — the trailing icon-only blue chip is the evidence-needed modifier rendering as a blank rounded square because the requested `mdi:link-variant` glyph is missing from the ICONS dictionary.

---

## 1. Reproduction

**Environment:** Live app `https://dual-research-alex.fly.dev/`, any modern browser. Reproduces deterministically on any run that has at least one critique item with `evidence_required: true` or with a non-empty `sources` segment.

**Steps:**
1. Open the live app and navigate to any run that produced critique findings — e.g. the run featured in the user's screenshot (`/#/run/20260521-0106…`).
2. Scroll to the **Critique** section and expand the **Resolved** group at the P4 phase.
3. Inspect the head of any item card whose finding was raised with `evidence_required: true` — observe the trailing tone-info icon-only chip after the kind chip ("Issue").
4. Open browser devtools and inspect the `<svg>` inside that chip — confirm it is a stroked `<rect x="4" y="4" width="16" height="16">` instead of a path.

**Expected:** The trailing chip displays the canonical `mdi:link-variant` chain-link glyph (the "sources family" idiom per [design-system/SPEC.md:501](design-system/SPEC.md)), tinted via `--md-info-foreground`. Same glyph appears in the sources segment header ("Sources (N)") inside the expanded body.

**Actual:** The trailing chip displays an empty open square — the missing-icon fallback rect at [src/dual_research/ui/static/icons.jsx:104-107](src/dual_research/ui/static/icons.jsx). The sources segment header in the expanded body also renders the same empty square next to "Sources (N)". The chip is still tone-info (blue), so the user reads it as a "blank blue square."

## 2. Root cause hypothesis

The `Mdi` primitive at [src/dual_research/ui/static/icons.jsx:100-112](src/dual_research/ui/static/icons.jsx) looks up `name` in the `ICONS` dictionary defined at [icons.jsx:14-97](src/dual_research/ui/static/icons.jsx). When the lookup misses, the component intentionally renders an outlined square as a "loud" fallback ([icons.jsx:103-108](src/dual_research/ui/static/icons.jsx)) so missing icons are visible during development rather than silently absent.

`link-variant` was never added to the `ICONS` dictionary. The dictionary contains a `link` key at [icons.jsx:54](src/dual_research/ui/static/icons.jsx) whose SVG path data is in fact the MDI **link-variant** artwork (a single chain link at 45°), but the key name does not match the lookup string the call sites use, so every `<Mdi name="link-variant" />` invocation falls through to the placeholder rect.

Call sites currently affected — every one of them renders a blank rounded square instead of the canonical sources glyph:

- [src/dual_research/ui/static/run-detail.jsx:1639](src/dual_research/ui/static/run-detail.jsx) — `source-requested` lifecycle chip leading icon.
- [src/dual_research/ui/static/run-detail.jsx:1649](src/dual_research/ui/static/run-detail.jsx) — `source-provided` lifecycle chip leading icon.
- [src/dual_research/ui/static/run-detail.jsx:2002](src/dual_research/ui/static/run-detail.jsx) — P4 ItemCard head evidence-needed modifier chip (the chip in the user's screenshot).
- [src/dual_research/ui/static/run-detail.jsx:2112](src/dual_research/ui/static/run-detail.jsx) — P4 ItemCard expanded sources segment header glyph.
- [src/dual_research/ui/static/run-detail.jsx:6018](src/dual_research/ui/static/run-detail.jsx) — P3 ReviewCard head Sources chip leading icon.

The DS specification at [design-system/SPEC.md:501](design-system/SPEC.md) and [design-system/SPEC.md:506](design-system/SPEC.md) explicitly mandates `mdi:link-variant` as the canonical sources-family glyph carried across every evidence-bearing surface, so the desired behaviour is unambiguous — the registry just lacks the key.

## 3. Fix

Add a `link-variant` entry to the `ICONS` dictionary in [src/dual_research/ui/static/icons.jsx](src/dual_research/ui/static/icons.jsx), placed in the existing "Content / docs" section next to the current `'link'` entry around [icons.jsx:54](src/dual_research/ui/static/icons.jsx). Use the canonical MDI 7.x `link-variant` SVG path (the same single-chain-link artwork that is currently — confusingly — stored under the `'link'` key):

```js
  'link-variant':    'M10.59,13.41C11,13.8 11,14.44 10.59,14.83C10.2,15.22 9.56,15.22 9.17,14.83C7.22,12.88 7.22,9.71 9.17,7.76V7.76L12.71,4.22C14.66,2.27 17.83,2.27 19.78,4.22C21.73,6.17 21.73,9.34 19.78,11.29L18.29,12.78C18.3,11.96 18.17,11.14 17.89,10.36L18.36,9.88C19.54,8.71 19.54,6.81 18.36,5.64C17.19,4.46 15.29,4.46 14.12,5.64L10.59,9.17C9.41,10.34 9.41,12.24 10.59,13.41M13.41,9.17C13.8,8.78 14.44,8.78 14.83,9.17C16.78,11.12 16.78,14.29 14.83,16.24V16.24L11.29,19.78C9.34,21.73 6.17,21.73 4.22,19.78C2.27,17.83 2.27,14.66 4.22,12.71L5.71,11.22C5.7,12.04 5.83,12.86 6.11,13.65L5.64,14.12C4.46,15.29 4.46,17.19 5.64,18.36C6.81,19.54 8.71,19.54 9.88,18.36L13.41,14.83C14.59,13.66 14.59,11.76 13.41,10.59C13,10.2 13,9.56 13.41,9.17Z', // link-variant
```

No call-site changes required — the five existing `<Mdi name="link-variant" ... />` invocations begin resolving the moment the key exists. No CSS changes required — the chip styling and color tokens are already correct; the only failure was the SVG payload.

The `'link'` key is intentionally left alone. Its current path data is link-variant artwork, but renaming or repointing it is out of scope (no call site is reading `'link'` today — confirmed via grep — but flipping the key would still be an unrelated DS-side change that should be done as a follow-up cleanup, not bundled with this user-visible bug fix). See §7.

## 4. User stories & acceptance criteria

### 4.1 — User stories

> As a **researcher**, I want the evidence-needed chip on a critique card to display a recognisable chain-link glyph, so that I can identify which findings require source citations at a glance instead of seeing an ambiguous empty blue square.
>
> As a **researcher**, I want the "Sources (N)" segment header inside an expanded critique card to display the same chain-link glyph, so that the evidence-bearing surfaces of the app read as one consistent visual vocabulary (the "sources family" idiom from DS SPEC §4.7).
>
> As a **viewer** of the P3 review pane, I want the head "Sources (N)" chip to display the chain-link glyph, so that the review reads as the same sources idiom as the P4 critique surfaces.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Evidence-needed modifier chip renders the chain-link glyph
> GIVEN a P4 ItemCard whose finding was raised with `evidence_required: true` is rendered in the DOM
> WHEN the page finishes hydrating
> THEN the chip with `data-chip-role="evidence"` in that card's header contains a single `<svg>` whose first child is a `<path>` element (not a `<rect>` placeholder)
> AND the `<path>`'s `d` attribute starts with the substring `M10.59,13.41C11,13.8` (the canonical MDI link-variant path prefix).

> **Scenario 2:** Sources segment header renders the chain-link glyph
> GIVEN a P4 ItemCard with at least one source row is expanded
> WHEN the expanded body is visible in the DOM
> THEN the `.item-card__sources-hd` element contains an `<svg>` whose first child is a `<path>` (not a `<rect>` placeholder)
> AND the same `<path>` `d` prefix as Scenario 1 is present.

> **Scenario 3:** No remaining placeholder-rect Mdi fallbacks in the critique surface
> GIVEN any run-detail view with at least one critique card visible
> WHEN the run-detail view finishes rendering
> THEN no `<svg>` inside any element with class beginning `item-card__` contains a child `<rect>` with attributes `x="4" y="4" width="16" height="16"` (the Mdi fallback signature from [icons.jsx:106](src/dual_research/ui/static/icons.jsx)).

## 5. Regression-prevention test

- [ ] **Test:** `tests/ui/test_icon_registry.py::test_link_variant_resolves` — parse [src/dual_research/ui/static/icons.jsx](src/dual_research/ui/static/icons.jsx) as text, assert the ICONS object literal contains a `'link-variant':` key whose value is a non-empty string. Locks in that the key exists; would have failed before this spec and passes after.

- [ ] **Test:** `tests/ui/test_icon_registry.py::test_no_call_site_uses_missing_icon` — grep `src/dual_research/ui/static/*.jsx` for `<Mdi name="..."` invocations, extract every distinct icon name, and assert each one appears as a key in the ICONS dictionary. Generalises the regression so any future caller using an un-registered name fails CI rather than reaching production as a blank square. Failure mode locked in: a developer adds `<Mdi name="some-new-icon" />` without adding the key.

Both tests live in the same new file and run under the standard `uv run pytest tests/ -q` command. No Playwright run-time render-check is added in this spec — the static analysis above catches the entire class of "missing key" bugs with zero browser cost. A DOM-level Playwright assertion is in scope for a follow-up DS-coverage spec (noted in §7).

## 6. Blast radius

The change is **additive**: one new key in a dictionary literal. No existing key is modified, removed, or renamed. The five call sites that currently render the fallback placeholder begin rendering the link-variant glyph the instant the key resolves — there is no API surface to migrate and no consumer outside `src/dual_research/ui/static/` to coordinate with.

Adjacent callers that read OTHER keys in the same dictionary are unaffected — Python-style "dict mutation while iterating" hazards don't apply to a JS object literal evaluated once at module load.

The DS SPEC at [design-system/SPEC.md:501](design-system/SPEC.md) already documents `mdi:link-variant` as the canonical sources glyph, so this fix brings the implementation into compliance with the existing DS contract rather than introducing a new contract. No DS revision required.

CSS for the affected chips (tone-info, icon-only, evidence-chip className) is already correct and reviewed; the only failure was the SVG payload missing. No CSS edits in this spec.

## 7. Out of scope

- **Renaming the existing `'link'` key.** The path data stored under `'link'` at [icons.jsx:54](src/dual_research/ui/static/icons.jsx) is actually link-variant artwork. Grep confirms no call site reads `'link'` today, but normalising the key name (or adding the proper "two interlocked rings" MDI `link` artwork) is a separate DS-cleanup concern. Deferred to a follow-up dev spec to be drafted post-merge if the duplicate-artwork ambiguity ever causes confusion.

- **Sweeping the entire `src/dual_research/ui/static/*.jsx` tree for other `<Mdi name="X" />` call sites whose `X` is missing from the registry.** The §5 regression test will surface any such case by failing CI, at which point each missing icon gets added as part of routine maintenance. No proactive audit in this spec.

- **A Playwright DOM-render-time check that the live page contains no fallback `<rect>` placeholders.** The static-analysis tests in §5 catch the class of bugs without browser overhead; a live DOM assertion would be a useful additional belt-and-braces check but is not the minimum bar to fix the reported symptom. Deferred to a follow-up dev spec to be drafted post-merge.

- **A general "all DS-mandated icons are present" audit cross-referencing every `mdi:*` mention in [design-system/SPEC.md](design-system/SPEC.md) against the registry.** Worth doing but a separate, larger refactor concern. Deferred to a follow-up dev spec to be drafted post-merge.

## 8. Risks

- **Risk: the canonical MDI link-variant path I'm copying in §3 contains a typo I introduced when retyping it.** Mitigation: the path is identical to the existing `'link'` entry at [icons.jsx:54](src/dual_research/ui/static/icons.jsx), so the implementer can copy-paste the value rather than retype it from the MDI source. The regression test in §5 also verifies the value is non-empty.

- **Risk: a future MDI library upgrade redraws `link-variant` and ours drifts.** Mitigation: low impact — the glyph is a single chain link, semantically stable; visual drift would be cosmetic at worst. No mitigation in this spec.

- **Risk: the empty rect placeholder was actually intentional in some other surface — removing it everywhere might surprise.** Mitigation: the fix does not remove the fallback. The fallback at [icons.jsx:103-108](src/dual_research/ui/static/icons.jsx) still fires for any future missing icon name. Only the specific name `link-variant` begins resolving correctly.
