---
kind: dev
spec: "0190"
slug: timeline-tabs-data-active-migration
title: "Refactor: TimelineTabs `Tab variant=solid` branch from `.is-active` to `data-active=true`, drop the dual CSS selector"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 8
depends_on: ["0173"]
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0173
promoted_from_draft: ""
---

# Spec 0190 — Refactor: TimelineTabs migration to `data-active` attribute

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0173
> **Bump:** PATCH — finish the `[data-active]` migration spec 0173 §2.3 started. No behavior change — the dual CSS selector currently accepts both forms; this spec collapses to the single canonical form.
> **Evidence:** Spec 0173 handoff `## Deferred during implementation` fourth bullet — [handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:47](handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:47): *"spec §2.3 says the `.is-active` modifier becomes a `[data-active="true"]` attribute selector. The bar-2 segments migrated; `TimelineTabs` (the only other in-tree user of `<TabGroup variant="solid">` / `.tab-solid`) still uses `.is-active` via the legacy `<Tab variant="solid" active={...} />` branch in `shared.jsx`. The DS canonical and live `.tab-solid.is-active, .tab-solid[data-active="true"]` selectors both accept either form so this is non-blocking, but the migration is incomplete."*

---

## 1. Current state

Spec 0173 §2.3 renamed `.fgroup` → `.tab-group-solid` and migrated the bar-2 agent + status segments from `.is-active` className to `data-active="true"` attribute selector. The CSS in both files was updated to a dual selector that accepts either form during the transition:

- [src/dual_research/ui/static/components.css:2211–2212](src/dual_research/ui/static/components.css):
  ```css
  .tab-solid.is-active,
  .tab-solid[data-active="true"] { background: var(--md-surface); ... }
  ```
- [src/dual_research/ui/static/components.css:2227](src/dual_research/ui/static/components.css):
  ```css
  .tab-solid[data-active="true"] .chip-value { color: var(--md-on-surface); }
  ```
- [design-system/assets/styles/composed-components.css:797–798, 813](design-system/assets/styles/composed-components.css) — mirror of the above.

The bar-2 segments in run-detail.jsx emit `data-active="true"` directly on the `<button class="tab-solid">` elements (per spec 0173 §2.3's bar-2 rebuild around [src/dual_research/ui/static/run-detail.jsx:7236–7311](src/dual_research/ui/static/run-detail.jsx) in the spec 0173 handoff anchor). The dual CSS selector covers them.

But there is **one remaining in-tree consumer of `<TabGroup variant="solid">`** that did not migrate: `TimelineTabs` at [src/dual_research/ui/static/run-detail.jsx:2030–2050](src/dual_research/ui/static/run-detail.jsx) renders its tabs via the `<Tab variant="solid" active={...} />` API. The `Tab` component's `variant === 'solid'` branch at [src/dual_research/ui/static/shared.jsx:1072–1081](src/dual_research/ui/static/shared.jsx) still emits the legacy `is-active` className:

```jsx
if (variant === 'solid') {
  return (
    <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
            onClick={onClick} disabled={disabled}
            className={_cn('tab-solid', active && 'is-active', className)}>
      …
    </button>
  );
}
```

The pain:

- **Two attribute conventions on the same primitive.** `tab-solid` buttons appear in the DOM with `class="… is-active"` (from `TimelineTabs`) AND with `data-active="true"` (from bar-2 segments). A reader inspecting the DOM has to know that both mean the same thing and that the CSS treats them equivalently. That's exactly the cost spec 0173 §2.3's rename was supposed to eliminate.
- **The dual CSS selector is doc debt.** Every CSS file that targets `.tab-solid` active state has to keep both selectors in sync. Future maintainers may forget to keep the comma-separated pair aligned (one cell drifts, the other stays), introducing a subtle bug that only triggers in one of the two call sites.
- **The DS canonical position is `data-active`.** The DS reference at [design-system/SPEC.md](design-system/SPEC.md) and spec 0173's §2.3 commit codify `data-active` as the new convention. Live should match the canonical naming.

Non-blocking — the dual selector currently makes both forms work — but the migration is incomplete.

## 2. Target state

`TimelineTabs` callers and the `Tab variant="solid"` branch both emit `data-active="true"`. The dual CSS selector collapses to the single `data-active` form. End state:

- [src/dual_research/ui/static/shared.jsx:1072–1081](src/dual_research/ui/static/shared.jsx) `Tab variant="solid"` branch:
  ```jsx
  if (variant === 'solid') {
    return (
      <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
              onClick={onClick} disabled={disabled}
              data-active={active ? 'true' : undefined}
              className={_cn('tab-solid', className)}>
        …
      </button>
    );
  }
  ```
  Note: `data-active={active ? 'true' : undefined}` — when `active` is false the attribute is omitted entirely (cleaner than `data-active="false"`, matches how bar-2 emits it post-0173).

- [src/dual_research/ui/static/components.css:2211–2212](src/dual_research/ui/static/components.css):
  ```css
  /* drop the .is-active branch */
  .tab-solid[data-active="true"] { background: var(--md-surface); color: var(--md-on-surface); box-shadow: var(--md-elev-1); }
  ```

- [design-system/assets/styles/composed-components.css:797–798](design-system/assets/styles/composed-components.css): mirror the same drop.

- The `[src/dual_research/ui/static/components.css:2227](src/dual_research/ui/static/components.css)` `.tab-solid[data-active="true"] .chip-value` rule is already in the canonical form and does not need changes.

`TimelineTabs` ([src/dual_research/ui/static/run-detail.jsx:2030–2050](src/dual_research/ui/static/run-detail.jsx)) does not need direct edits — it passes `active={t.id === active}` to `Tab` and the `Tab` component does the rest. The migration is entirely contained in `shared.jsx` + the two CSS files.

## 3. Stepwise migration

Each step independently shippable / revertable. Ordering matters: emit `data-active` from JSX **before** dropping the `.is-active` CSS selector, otherwise the active state would briefly render unstyled during a partial deploy.

- **Step 1 — JSX emits both forms.** Edit [src/dual_research/ui/static/shared.jsx:1072–1081](src/dual_research/ui/static/shared.jsx) to add `data-active={active ? 'true' : undefined}` while keeping the `active && 'is-active'` className. Both the dual CSS selector (which still exists) and the canonical `data-active` selector now match. Manual DOM inspection of the Timeline / Consumption tab pair confirms both attributes appear on the active button. *Verifies:* visual state matches today's exactly; pytest still green.

- **Step 2 — JSX drops the className.** Edit [src/dual_research/ui/static/shared.jsx:1076](src/dual_research/ui/static/shared.jsx) to remove `active && 'is-active'` from the `_cn(…)` call. The button now carries only `data-active`. The CSS still has the dual selector, so visual state is preserved by the `data-active` branch alone. *Verifies:* DOM inspect shows `.tab-solid` button with no `is-active` className but with `data-active="true"` when active; visual rendering unchanged.

- **Step 3 — CSS drops the `.is-active` branch.** Edit both [src/dual_research/ui/static/components.css:2211–2212](src/dual_research/ui/static/components.css) and [design-system/assets/styles/composed-components.css:797–798](design-system/assets/styles/composed-components.css) — drop the `.tab-solid.is-active,` line, leaving only `.tab-solid[data-active="true"]`. *Verifies:* visual state preserved; CSS lint / linter (if any) passes; manual diff between the two files confirms they stay in sync per the `CLAUDE.md` two-files rule.

- **Step 4 — DS HTML reference grep.** Grep [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) for `tab-solid.*is-active` or `class="tab-solid.*is-active"`. If found, update those static example HTML snippets to use `data-active="true"` instead. *Verifies:* no remaining `is-active` references on `tab-solid` in the DS HTML reference page.

## 4. Behavior preservation

- [ ] Existing test `uv run pytest tests/ -q` still green — pytest does not exercise JSX runtime but the structural fixtures around shared.jsx import paths must still resolve.
- [ ] Manual visual check: open the run-detail page on the anchor run `20260521-010637-dvs-backend-language-choice`, switch between the Timeline / Consumption tabs. The active tab visual style (lifted background + elevation + on-surface text color) is identical before and after.
- [ ] Manual DOM check: inspect the `TimelineTabs` button group in DevTools. Active button has `data-active="true"` and no `is-active` className. Inactive button has neither attribute / className.
- [ ] New parity test under [tests/spec0190/](tests/spec0190/): structural regex test over [src/dual_research/ui/static/shared.jsx](src/dual_research/ui/static/shared.jsx) — assert the `variant === 'solid'` branch contains `data-active=` and does NOT contain `'is-active'`. (Pattern mirror of `tests/spec0173/test_item_round_shape.py`.)
- [ ] Bar-2 unaffected: the bar-2 status + agent segments at [src/dual_research/ui/static/run-detail.jsx:7236–7311 region](src/dual_research/ui/static/run-detail.jsx) already emit `data-active` directly, not via the `Tab` component. They are unchanged by this spec.

## 5. Out of scope

**Explicit: no new feature ships here.** This is purely a rename / convention-completion that closes out spec 0173 §2.3's incomplete migration. Any feature work that depends on the cleaner convention lives in a follow-up spec.

- **Other variants of the `Tab` component.** The `variant === 'kind'` ([src/dual_research/ui/static/shared.jsx:1087](src/dual_research/ui/static/shared.jsx)), `variant === 'phase'` ([src/dual_research/ui/static/shared.jsx:1098](src/dual_research/ui/static/shared.jsx)), and `md-btn--text` ([src/dual_research/ui/static/shared.jsx:1106](src/dual_research/ui/static/shared.jsx)) branches all still use `active && 'is-active'`. None of them are `tab-solid`; their `.is-active` rules are separate CSS selectors targeting `.kind-tab`, `.phase-tab`, and `.md-btn` respectively. Migrating those is a separate (potentially larger) refactor — out of scope for this spec.
- **The unrelated `.tab` default-variant branch** at [src/dual_research/ui/static/shared.jsx:1120](src/dual_research/ui/static/shared.jsx) and its `.is-active` CSS rule — same story: separate selector, separate convention, separate spec if desired.
- **`tt-cell` theme tabs** at [src/dual_research/ui/static/shared.jsx:1142–1150](src/dual_research/ui/static/shared.jsx) (`is-active` for the theme picker) — not `tab-solid`, not in scope.
- **CSS migration to attribute selectors more broadly.** Spec 0173 §2.3 only mandated the `tab-solid` migration. Other `.is-active` selectors in the CSS files remain on the className convention and are not touched here.
- **`Tab` component API change.** The `active` boolean prop stays on the `Tab` component API. Internally the `variant === 'solid'` branch now maps it to `data-active` instead of a className, but the caller-facing contract is unchanged. `TimelineTabs` doesn't need any edit.

## 6. Risks

- **Hidden behavior depending on internals.** Other CSS files (or inline styles, or third-party stylesheets) targeting `.tab-solid.is-active` would silently lose their styling. Mitigation: grep both CSS files plus [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) for `tab-solid.is-active` and `tab-solid\\.is-active` before merging. If any other rule references the dropped selector, the implementer must reconcile (either update the rule to `data-active` or, if the rule is intentional doc preservation, leave the dual selector in place and document the exception).
- **Performance regression.** N/A — attribute selectors and class selectors have effectively equivalent specificity and matching cost in modern browsers. No measurable delta.
- **Missed call site.** Any other place in the codebase that constructs a `<button class="tab-solid is-active">` directly (without going through the `<Tab>` component) would still emit the legacy className and lose its active styling after step 3. Mitigation: grep [src/dual_research/](src/dual_research/) for `tab-solid` to enumerate all call sites. If any direct emission exists outside `Tab`, either route it through the component or update the literal to `data-active`. Spec 0173 §2.3 already did this audit for the bar-2 segments; verify no new direct callers have appeared in the meantime.
- **DS HTML reference drift.** If [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) shows `.tab-solid.is-active` examples in any of its component galleries, the rendered example would lose its active-state highlight after step 3. Mitigation: step 4 above explicitly greps and reconciles. The DS HTML is hand-authored; the implementer must read what's there and update it.
- **`active && 'is-active'` `_cn` semantics.** The current shared.jsx uses `_cn(…, active && 'is-active', …)` which evaluates to either `'is-active'` (truthy) or `false` (falsy). Replacing with `data-active={active ? 'true' : undefined}` matches the React idiom for "emit attribute conditionally" but the implementer must confirm `_cn` is being used elsewhere with the same pattern and remains intact for the className list. The change is mechanical — drop one element from `_cn`, add one prop attribute.
- **Race with active deploys.** A partial deploy where the JSX has been updated but the CSS has not (or vice versa) would lose the active-state highlight for the few seconds of the deploy window. Mitigation: the stepwise migration in §3 explicitly handles this — step 1 emits both attributes, step 2 drops the className from JSX (CSS still accepts via dual selector), step 3 drops the legacy CSS branch. Each step is independently revertable and visually neutral. Even if the three steps land in three separate PRs, the migration is safe at every intermediate state.
