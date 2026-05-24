---
kind: dev
spec: "0209"
slug: cs-body-hidden-when-open
title: "Fix: CollapsibleSection bodies stay hidden when open due to legacy how-it-works CSS bleed"
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

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0209 — Fix: CollapsibleSection bodies stay hidden when open due to legacy how-it-works CSS bleed

> **Type:** bug  |  **Severity:** P1  |  **Affects:** every consumer of the modern `<CollapsibleSection>` primitive — Input Brief modal (System / User / Derived sections), critique pane section headers, timeline phase groups, agent-input entry rows, and other call sites listed in [design-system/SPEC.md:347](design-system/SPEC.md).
> **Bump:** PATCH — bug fix
> **Evidence:** User screenshot of the Input Brief modal "User prompt" tab — `USER PROMPT` section chevron rotated open (`▼`, `aria-expanded="true"`), `DERIVED INPUTS` shows `6 pieces` next to a chevron that toggles but reveals no body. Spec [0178 (2e23fa2)](specs/0178-input-section-default-open-on-outer-expand.md) was a prior failed attempt — it diagnosed the symptom as a JSX nesting/default-open issue and patched JSX `defaultOpen` props, which did not address the actual cause (CSS cascade).

---

## 1. Reproduction

**Environment:** Production at `https://dual-research-alex.fly.dev/` and local dev. All browsers. Reproduces on every run that has a populated agent-input bundle.

**Steps:**
1. Open any run detail page that exposes the Input Brief modal (any completed turn).
2. Open the modal and switch to the `User prompt` tab — see three collapsible sections: `SYSTEM PROMPT`, `USER PROMPT`, `DERIVED INPUTS`, each with a right-aligned `N piece(s)` counter.
3. Click the `DERIVED INPUTS` header (or `SYSTEM PROMPT`). The chevron rotates from `▶` to `▼`.

**Expected:** Body of the clicked section appears below the header, showing the per-piece rows from `PromptPiecesThreeSectionView` ([run-detail.jsx:6300-6380](src/dual_research/ui/static/run-detail.jsx:6300)).

**Actual:** Body stays invisible. Chevron rotates and `aria-expanded` toggles to `true`, but no content appears. The `USER PROMPT` section is `defaultOpen: true` ([run-detail.jsx:6342](src/dual_research/ui/static/run-detail.jsx:6342)) and shows the same emptiness on first paint — proving the bug is not state-flip-related but renders-empty-when-open.

## 2. Root cause hypothesis

`src/dual_research/ui/static/components.css` defines two unrelated `.cs-*` rule blocks under the same class names:

| Block | Lines | Consumer |
| --- | --- | --- |
| Modern primitive (SPEC-0071 D9 — the canonical DS disclosure per [design-system/SPEC.md:347](design-system/SPEC.md)) | [components.css:1410-1454](src/dual_research/ui/static/components.css:1410) | `<CollapsibleSection>` at [shared.jsx:1620](src/dual_research/ui/static/shared.jsx:1620) — wraps DOM as `<div class="cs"> … <div class="cs-body cs-open">…</div></div>` |
| Legacy "how-it-works" CSS-only sections | [components.css:3721-3746](src/dual_research/ui/static/components.css:3721) | exactly one JSX site: [how-it-works.jsx:614](src/dual_research/ui/static/how-it-works.jsx:614) — wraps DOM as `<section class="hiw-sec cs-section is-open"> … <div class="cs-body">…</div></section>` |

The legacy block at [components.css:3745](src/dual_research/ui/static/components.css:3745) declares an **unscoped** rule:

```css
.cs-body { padding: var(--s-3) 0 var(--s-5) 28px; display: none; }
.cs-section.is-open .cs-body { display: block; }
```

The modern open-state rule at [components.css:1446](src/dual_research/ui/static/components.css:1446) sets only `transition: none` — it never declares `display`:

```css
.cs-body.cs-open { transition: none; }
.cs-body.cs-closed { display: none; }
```

CSS cascade resolution for the modern primitive when `open=true`:

- `.cs-body { display: none }` (legacy, line 3745, specificity 0,1,0) — **wins** for the `display` property.
- `.cs-body.cs-open { transition: none }` (modern, line 1446, specificity 0,2,0) — higher specificity but does NOT touch `display`.
- `.cs-section.is-open .cs-body { display: block }` (legacy override, line 3746) — does NOT fire because the modern primitive's wrapper is `<div class="cs">`, not `<div class="cs-section">`.

Final computed `display` on every modern `<div class="cs-body cs-open">` element: **`none`**. The children render to the DOM (the React tree at [shared.jsx:1645](src/dual_research/ui/static/shared.jsx:1645) conditionally mounts `{open && children}`), but the parent is `display: none`, so nothing is visible. The chevron rotates via the inline `transform` at [shared.jsx:1638](src/dual_research/ui/static/shared.jsx:1638) — a different selector, unaffected by the cascade collision.

Spec 0178 missed this because the cause is in CSS, not React state. The patch flattened JSX `defaultOpen` props ([run-detail.jsx:6342](src/dual_research/ui/static/run-detail.jsx:6342)) and re-shipped, but the CSS conflict survives any state change.

Bleed-through is not limited to `.cs-body`. The two blocks also collide on `.cs-header` ([1414](src/dual_research/ui/static/components.css:1414) vs [3727](src/dual_research/ui/static/components.css:3727)), `.cs-chevron` ([1429](src/dual_research/ui/static/components.css:1429) vs [3732](src/dual_research/ui/static/components.css:3732)), and `.cs-title` ([1435](src/dual_research/ui/static/components.css:1435) vs [3739](src/dual_research/ui/static/components.css:3739)) — with different padding, font-sizes, and transitions. The current visible bug is the most painful symptom; the structural problem is broader.

## 3. Fix

**Rename the legacy how-it-works classes** so they stop sharing the `.cs-*` namespace with the canonical DS primitive.

Touchpoints (two files, one commit):

1. **`src/dual_research/ui/static/components.css`** — rename inside the legacy block at lines [3721-3746](src/dual_research/ui/static/components.css:3721):
   - `.cs-section` → `.hiw-cs-section`
   - `.cs-section:first-child` → `.hiw-cs-section:first-child`
   - `.cs-header` (line 3727) → `.hiw-cs-header`
   - `.cs-chevron` (line 3732) → `.hiw-cs-chevron`
   - `.cs-section.is-open .cs-chevron` → `.hiw-cs-section.is-open .hiw-cs-chevron`
   - `.cs-title` (line 3739) → `.hiw-cs-title`
   - `.cs-body` (line 3745) → `.hiw-cs-body`
   - `.cs-section.is-open .cs-body` → `.hiw-cs-section.is-open .hiw-cs-body`
   - Leave the modern block at lines [1410-1454](src/dual_research/ui/static/components.css:1410) untouched — it is the canonical DS primitive and its class names must NOT change.

2. **`src/dual_research/ui/static/how-it-works.jsx:614`** — the only consumer of the legacy classes per `grep -rn "cs-section" src/dual_research/ui/static/*.jsx`. Update the JSX `className` strings in the same component (renderer at [how-it-works.jsx:595-637](src/dual_research/ui/static/how-it-works.jsx:595)) to emit the renamed classes:
   - `'hiw-sec cs-section' + (open ? ' is-open' : '')` → `'hiw-sec hiw-cs-section' + (open ? ' is-open' : '')`
   - Any inner `cs-header` / `cs-chevron` / `cs-title` / `cs-body` references in the same component (within the [how-it-works.jsx:595-637](src/dual_research/ui/static/how-it-works.jsx:595) render block) → `hiw-cs-*` counterparts.

3. **`how-it-works.jsx:76`** — prose string lists structural classes including `.cs-section`. Update the documentation string to reference `.hiw-cs-section`.

**Not touched (verified):**

- `design-system/assets/styles/composed-components.css` — `grep -nE "cs-section|cs-body|cs-header|cs-chevron|cs-title"` on the DS mirror returns zero hits. The legacy block was never mirrored, so the CLAUDE.md dual-write rule (`design-system/` ↔ `src/dual_research/ui/static/components.css`) does not require a same-commit DS-side change. The modern `.cs-*` primitive's mirror status is unchanged by this spec — if it is currently un-mirrored, that is a separate (pre-existing) DS hygiene issue; see §7 Out of scope.

- The modern `<CollapsibleSection>` JSX at [shared.jsx:1620-1649](src/dual_research/ui/static/shared.jsx:1620) — no change. The component is correctly implemented (toggles state, conditionally renders children, sets `aria-expanded`). The fix is CSS-only on the legacy side.

- Spec 0178's JSX `defaultOpen` props at [run-detail.jsx:6336-6348](src/dual_research/ui/static/run-detail.jsx:6336) — leave as-is. With the CSS bleed gone, the existing `false / true / false` defaults render correctly (System closed, User open, Derived closed) on first paint.

## 4. User stories & acceptance criteria

UI bug — both required.

### 4.1 — User stories

> As a `researcher`, I want the `User prompt` tab of the Input Brief modal to actually show me the prompt content when I click a section header, so that I can inspect what the agent saw on that turn.

> As a `dev`, I want every `<CollapsibleSection>` in the app (critique pane, timeline phase groups, agent-input entry rows, How-It-Works page) to reveal its body when I expand it, so that I can trust the disclosure primitive across surfaces.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Input Brief modal — User prompt section renders body on first paint
> GIVEN the Input Brief modal is open on a turn that has populated `pieces` for the `user_prompt` group
> WHEN the `User prompt` tab is the active tab and the `USER PROMPT` section's chevron is rotated (`▼`, `aria-expanded="true"`)
> THEN the per-piece rows for the user-prompt group are visible below the header — `getComputedStyle(div.cs-body.cs-open).display === 'block'` and at least one `.agent-input-entry` is present in the DOM below the `USER PROMPT` header.

> **Scenario 2:** Input Brief modal — Derived inputs section reveals body on click
> GIVEN the Input Brief modal is open on a turn that has six `derived` pieces and the `DERIVED INPUTS` header is collapsed (chevron `▶`)
> WHEN the user clicks the `DERIVED INPUTS` header
> THEN the chevron rotates to `▼`, `aria-expanded` becomes `"true"`, and six per-piece `.agent-input-entry` rows become visible below the header.

> **Scenario 3:** How-It-Works page regression check
> GIVEN the user navigates to `/#/how-it-works` (which renders the legacy `<CollapsibleSection>` from [how-it-works.jsx:595-637](src/dual_research/ui/static/how-it-works.jsx:595) with the renamed `.hiw-cs-*` classes)
> WHEN the user clicks a legacy section header
> THEN the section's body becomes visible and the chevron rotates — i.e. the rename did not break the legacy consumer.

## 5. Regression-prevention test

- [ ] **Playwright (or equivalent DOM smoke) test:** open the Input Brief modal on a fixture run with at least one `derived.*` piece. Assert `getComputedStyle(document.querySelector('div.cs-body.cs-open')).display === 'block'`. Without this fix the test fails (computed display is `none`); with the fix it passes. Locks in the CSS-cascade contract for the modern primitive.

- [ ] **CSS-grep guard (lightweight, in `tests/`):** assert that the file `src/dual_research/ui/static/components.css` contains exactly **one** unscoped `.cs-body` rule and that rule is `.cs-body.cs-closed { display: none }` (from the modern block). Any future `.cs-body { display: none }` selector that resurrects the legacy bleed fails the test. Same guard for `.cs-section { … }` (must not exist in components.css after this spec).

## 6. Blast radius

**Consumers of the modern `.cs-*` primitive (unchanged class names — should now actually work):**

- Input Brief modal — `<InputSectionGroup>` and `<InputSection>` at [run-detail.jsx:6401](src/dual_research/ui/static/run-detail.jsx:6401), [run-detail.jsx:6439](src/dual_research/ui/static/run-detail.jsx:6439).
- Critique pane section headers — per [design-system/SPEC.md:347](design-system/SPEC.md).
- Timeline phase group headers — per [design-system/SPEC.md:347](design-system/SPEC.md).
- Any other `<CollapsibleSection>` call site discoverable via `grep -rn "CollapsibleSection" src/dual_research/ui/static/`.

**Consumers of the renamed legacy classes (only one):**

- [how-it-works.jsx:614](src/dual_research/ui/static/how-it-works.jsx:614) — single call site, updated in the same commit. No other JSX file references `.cs-section` (verified by `grep -rn "cs-section" src/dual_research/ui/static/*.jsx`).

**Why this doesn't break adjacent callers:**

- The modern primitive's class names are preserved exactly. Existing CSS that targets `.cs`, `.cs-header`, `.cs-body.cs-open`, etc. continues to apply.
- The legacy renderer at [how-it-works.jsx:595-637](src/dual_research/ui/static/how-it-works.jsx:595) is updated in lockstep with the CSS — no orphan class references in either direction.
- No external (DS-mirror) duplication exists, so no second-file edit is required.

## 7. Out of scope

- **Mirroring the modern `.cs-*` primitive into `design-system/assets/styles/composed-components.css`.** The DS mirror currently has zero `.cs-*` rules. Whether to backfill the modern primitive into the DS mirror per the CLAUDE.md dual-write rule is a separate DS-hygiene issue, **deferred to a follow-up dev spec to be drafted post-merge** if the user wants the dual-write invariant restored for this primitive.
- **Visual redesign of the legacy how-it-works disclosure.** The renamed `.hiw-cs-*` rules keep their current visual output. Any Material-3 unification of the How-It-Works page disclosure with the canonical primitive is **deferred to a follow-up dev spec to be drafted post-merge**.
- **Re-litigating spec 0178's JSX `defaultOpen` defaults.** Spec 0178 was a wrong-cause patch but the per-section defaults (System closed / User open / Derived closed) are still the desired UX. Leave them untouched.
- **Token-only-for-color audit on the renamed block.** The legacy block already reads from `--md-*` / `--s-*` tokens; no token rework is in scope.

## 8. Risks

- **Cached browser stylesheets** — users who keep an old `components.css` cached for a session will still see the legacy bleed until reload. Mitigated by the existing cache-busting URL parameter on the static assets (no spec-level action required).
- **Other call sites of `.cs-section` discovered post-grep.** Mitigated by an explicit grep at implementation time across the full repo (`grep -rn "cs-section\b\|cs-chevron\b\|cs-title\b\|cs-body\b\|cs-header\b" src/ design-system/`) before commit, and by the §5 CSS-grep guard test.
- **HMR / static-file resolver in `dual_research.ui.static`** — confirm in implementation that `components.css` is served at the same URL after edit (no path-rewriting middleware that caches old contents in memory).
