---
kind: dev
spec: "0208"
slug: provider-chip-dim-in-critique-promote-tone-to-base
title: "Fix: provider chip dim in critique — promote tone-claude/gpt override into the base Chip primitive"
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
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0208 — Fix: provider chip dim in critique — promote tone-claude/gpt override into the base Chip primitive

> **Type:** bug  |  **Severity:** P2 (visual / readability)  |  **Affects:** Critique pane item-card heads on every run-detail view; structural debt across the DS.
> **Bump:** PATCH — bug fix.
> **Evidence:** User reported the `Claude` / `GPT` provider chips on critique cards look dim and hard to read versus the same chip on Timeline cards. Confirmed in source: timeline + lifecycle rows scope an override; critique card-head + DS gallery + how-it-works callsite all fall through to the unreadable defaults.

---

## 1. Reproduction

**Environment:** dual-research dashboard at any run-detail view, dark and light modes, current `main` (`52f7c88`).

**Steps:**
1. Open any run-detail view that has at least one critique item (e.g. `/r/<run-id>` with the Critique pane open).
2. Open the Timeline pane in the adjacent column.
3. Compare the provider chip (`Claude` / `GPT`) at the start of any Critique card's header against the same chip on any Timeline card's header.

**Expected:** the two chips render identically — same background tint, same text colour, same legibility — because they are the same `<Chip tone="claude" />` / `<Chip tone="gpt" />` design-system primitive.

**Actual:** the Timeline chip carries a noticeably brighter background (30% sable/sage tint) and a dark, high-contrast text colour in light mode. The Critique chip falls through to the base rule's 8%-rgba background, which nearly vanishes on the M3 card surface; its text remains the bright brand hue, which reads as faint and muddy.

## 1.1 Context

The provider chip (`<Chip tone="claude">` / `<Chip tone="gpt">` from `design-system/SPEC.md` §6 Primitives) is supposed to be a single design-system component that renders identically wherever it appears. In practice it currently renders **differently in different containers** because the readable treatment (30% brand-tint background, dark text in light mode) lives as a **scoped CSS override** on `.tl-card-head` rather than in the base chip rule.

The base rule itself encodes a near-invisible 8% rgba tint ([components.css:144-145](src/dual_research/ui/static/components.css:144)). Every consumer that wanted the chip to actually read had to re-discover the fix and patch it in their own container scope:

| Container | Scoped override? | File:line |
|---|---|---|
| Timeline card head (`.tl-card-head`) | yes — 30% tint, light-mode hex backstop | [components.css:509-514](src/dual_research/ui/static/components.css:509), [components.css:541-549](src/dual_research/ui/static/components.css:541) (light backstop) |
| Critique lifecycle rows (`.item-card__lifecycle-section .lc-row-chips`) | yes — 30% tint | [composed-components.css:2308-2313](design-system/assets/styles/composed-components.css:2308) |
| **Critique card head (`.item-card__head`)** | **no** — falls through to 8% defaults | [components.css:144-145](src/dual_research/ui/static/components.css:144), [run-detail.jsx:1956-1963](src/dual_research/ui/static/run-detail.jsx:1956) (callsite) |
| Design-system gallery (`/#/language` route) | no — falls through to 8% defaults | [design-language.jsx:108-109](src/dual_research/ui/static/design-language.jsx:108) |
| How-it-works pane | no — falls through to 8% defaults | [how-it-works.jsx:663](src/dual_research/ui/static/how-it-works.jsx:663) |

Three of five callsites silently disagree with the base rule. That isn't drift — it's the base rule being wrong and every well-rendered surface paying the cost of working around it.

This is a structural design-system failure: the DS exposes the *worse* treatment as canonical, every consumer re-implements the fix, and any new consumer ships broken until someone notices. Spec 0165 §2.2 + §2.6 explicitly *scoped* the readable treatment to `.tl-card-head` only, with a comment that "the critique pane stays unchanged" — but that decision predates the critique pane being rebuilt on a card surface where the dim treatment is unreadable.

**Source-artefact traceability**

| Source item | Source quote/ref | Spec section |
|---|---|---|
| Critique card-head provider chip dim vs. Timeline | User screenshot comparison; verified in [run-detail.jsx:1956-1963](src/dual_research/ui/static/run-detail.jsx:1956) (Critique `<Chip>` callsite) and [run-detail.jsx:1253-1260](src/dual_research/ui/static/run-detail.jsx:1253) (Timeline `<Chip>` callsite) | §2.1 |
| Base chip rule encodes the dim treatment | [components.css:144-145](src/dual_research/ui/static/components.css:144) `background: var(--claude-bg)` resolves to `rgba(212,165,116,0.08)` per [tokens.css:12](src/dual_research/ui/static/tokens.css:12) | §2.2 |
| Timeline scoped override is the canonical readable treatment | [components.css:509-514](src/dual_research/ui/static/components.css:509) + DS-side mirror [composed-components.css:1856-1861](design-system/assets/styles/composed-components.css:1856), documented at [SPEC.md:458-467](design-system/SPEC.md:458) | §2.2, §2.3 |
| Light-mode text backstop on `.tl-card-head` (spec 0165 §2.6) | [composed-components.css:1897-1904](design-system/assets/styles/composed-components.css:1897), hexes `#3b2810` / `#0a322d` mirror `--md-on-primary-container` / `--md-on-secondary-container` at [tokens-and-primitives.css:231,234](design-system/assets/styles/tokens-and-primitives.css:231) | §2.3 |
| Critique lifecycle rows already re-implement the override | [composed-components.css:2308-2313](design-system/assets/styles/composed-components.css:2308) | §2.4 |

## 2. Root cause

### 2.1 The visible bug

`.item-card__head` in the Critique pane contains an `<AgentIcon /> + label` provider chip ([run-detail.jsx:1956-1963](src/dual_research/ui/static/run-detail.jsx:1956)). The chip's tone class (`.chip.tone-claude` / `.chip.tone-gpt`) resolves to the base rule at [components.css:144-145](src/dual_research/ui/static/components.css:144), which sets `background: var(--claude-bg)` = `rgba(212,165,116,0.08)` — an 8% tint that almost vanishes on the card surface (`--md-surface-container-high`). The text colour stays at the bright brand hue `var(--claude)` = `#d4a574`, which is hard to read on a near-transparent background.

The Timeline card head ([run-detail.jsx:1253-1260](src/dual_research/ui/static/run-detail.jsx:1253)) renders the *same* `<Chip>` component but its container scope (`.tl-card-head`) carries a stronger override ([components.css:509-514](src/dual_research/ui/static/components.css:509)) — `background: color-mix(in srgb, var(--p-sable) 30%, transparent)` — plus a light-mode text backstop ([composed-components.css:1897-1904](design-system/assets/styles/composed-components.css:1897)) that forces `color: #3b2810` so the chip stays readable on light surfaces.

### 2.2 The structural cause

The base rule at [components.css:144-145](src/dual_research/ui/static/components.css:144) (and its DS-side mirror) encodes the wrong default. The 8%-tint treatment was inherited from an earlier surface context and was never revisited when:
- spec 0164 swapped the timeline card to `--md-surface-container-high` (where 8% disappears),
- spec 0165 patched timeline only,
- the critique pane was rebuilt to use the same M3 card surface.

Adjacent surfaces independently rediscovered the fix:
- Timeline: `.tl-card-head .chip.tone-{claude,gpt}` → 30% tint ([components.css:509-514](src/dual_research/ui/static/components.css:509))
- Critique lifecycle rows: `.item-card__lifecycle-section .lc-row-chips .chip.tone-{claude,gpt}` → 30% tint ([composed-components.css:2308-2313](design-system/assets/styles/composed-components.css:2308))

Critique card head and two other callsites (design-language gallery, how-it-works pane) did not.

### 2.3 Why the user's framing is correct

The user invoked this spec asking whether the design system is "real" or "vanity". Diagnosis: the component IS being imported correctly everywhere — `<Chip tone="claude">` from `shared.jsx` — but the **visual contract** the design system encodes in CSS is the broken one. Three of five consumers override it inline; two don't. The DS owns the wrong default, so consumers' adherence to "import the DS component" produces visually-inconsistent results.

## 3. Fix

Promote the 30%-tint background and light-mode text backstop from the `.tl-card-head` / lifecycle-row scopes into the **base** `.chip.tone-claude` / `.chip.tone-gpt` rules. Delete the redundant scoped overrides for the provider tones in `.tl-card-head` and `.item-card__lifecycle-section .lc-row-chips`. Keep the System / activity-mono Timeline overrides untouched — those govern different chip tones.

### 3.1 Base chip rule (live-app + DS-side, lockstep per CLAUDE.md two-file rule)

Edit [src/dual_research/ui/static/components.css:144-145](src/dual_research/ui/static/components.css:144) and the DS-side mirror in [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) (find the matching block):

```css
/* before */
.chip.tone-claude { color: var(--claude); background: var(--claude-bg); border-color: transparent; }
.chip.tone-gpt    { color: var(--gpt);    background: var(--gpt-bg);    border-color: transparent; }

/* after */
.chip.tone-claude { color: var(--claude); background: color-mix(in srgb, var(--p-sable) 30%, transparent); border-color: transparent; }
.chip.tone-gpt    { color: var(--gpt);    background: color-mix(in srgb, var(--p-sage)  30%, transparent); border-color: transparent; }
```

Rationale: aligns provider chips with the established pattern used by every other tone at [components.css:137-142](src/dual_research/ui/static/components.css:137) (info / ok / warn / err / idle), which all use `color-mix(... N%, transparent)` over the brand hue. The 8%-rgba alias tokens (`--claude-bg` / `--gpt-bg`) remain in tokens.css — they are still used by [compare.jsx:220](src/dual_research/ui/static/compare.jsx:220), [shared.jsx:16-17](src/dual_research/ui/static/shared.jsx:16) (AGENT_META metadata), and [components.css:1322-1323](src/dual_research/ui/static/components.css:1322) (`.sci__msg` chat bubbles) for non-chip surfaces. We are not removing the tokens; we are detaching the chip rule from them.

### 3.2 Light-mode text backstop, promoted globally

Add to both files (replacing the `.tl-card-head`-scoped backstop at [composed-components.css:1897-1904](design-system/assets/styles/composed-components.css:1897)):

```css
body.light .chip.tone-claude,
body.light .chip.tone-claude .chip-label { color: var(--md-on-primary-container); }
body.light .chip.tone-gpt,
body.light .chip.tone-gpt .chip-label    { color: var(--md-on-secondary-container); }
```

Use the canonical tokens (`--md-on-primary-container` = `#3b2810`, `--md-on-secondary-container` = `#0a322d` per [tokens-and-primitives.css:231,234](design-system/assets/styles/tokens-and-primitives.css:231)) rather than re-inlining hex codes. Per CLAUDE.md: "No hex codes inside `src/dual_research/ui/static/components.css` or `design-system/assets/styles/composed-components.css`." Spec 0165's defensive hex backstop is no longer warranted now that the rule is the canonical one — if `--md-on-primary-container` ever drifts in light mode, the whole DS breaks, not just chips.

### 3.3 Delete redundant scoped overrides

Remove these rules from both files (they now do nothing — the base rule already provides the same treatment):

- `.tl-card-head .chip.tone-claude { ... }` at [components.css:509-511](src/dual_research/ui/static/components.css:509) and [composed-components.css:1856-1858](design-system/assets/styles/composed-components.css:1856)
- `.tl-card-head .chip.tone-gpt { ... }` at [components.css:512-514](src/dual_research/ui/static/components.css:512) and [composed-components.css:1859-1861](design-system/assets/styles/composed-components.css:1859)
- `body.light .tl-card-head .chip.tone-claude, ... { color: #3b2810; }` at [composed-components.css:1897-1900](design-system/assets/styles/composed-components.css:1897) and its live-app mirror
- `body.light .tl-card-head .chip.tone-gpt, ... { color: #0a322d; }` at [composed-components.css:1901-1904](design-system/assets/styles/composed-components.css:1901) and its live-app mirror
- `.item-card__lifecycle-section .lc-row-chips .chip.tone-claude { ... }` at [composed-components.css:2308-2310](design-system/assets/styles/composed-components.css:2308) and its live-app mirror
- `.item-card__lifecycle-section .lc-row-chips .chip.tone-gpt { ... }` at [composed-components.css:2311-2313](design-system/assets/styles/composed-components.css:2311) and its live-app mirror

**Keep** the following — they govern different tones (`tone-neutral` for System identity and the mono activity chip), which are still surface-scoped:
- `.tl-card-head .chip.tone-neutral:not(.mono)` ([composed-components.css:1862-1865](design-system/assets/styles/composed-components.css:1862))
- `.tl-card-head .chip.tone-neutral.mono` ([composed-components.css:1866-1868](design-system/assets/styles/composed-components.css:1866))

### 3.4 Update design-system/SPEC.md §4.4

The "Chip polish inside `.tl-card-head`" table at [SPEC.md:458-467](design-system/SPEC.md:458) currently documents the scoped override pattern. Rewrite to:
- Move the `tone-claude` / `tone-gpt` rows to §6 (Primitives — Chip) as the **base** rendering for identity tones.
- Shrink the §4.4 table to the two surviving rows (`tone-neutral:not(.mono)` and `tone-neutral.mono`) — still timeline-scoped because System / activity-mono chips don't appear elsewhere on the surface mix that needs the override.
- Add a short note in §6 (Chip primitive) recording the structural rule: **identity chips render the same on every surface; per-container overrides for identity tones are forbidden going forward.**
- Drop the §2.6 light-mode backstop paragraph at [SPEC.md:467](design-system/SPEC.md:467) and replace with a one-line note that identity-chip text colour uses `--md-on-{primary,secondary}-container` in light mode globally.

## 4. User stories & acceptance criteria

### 4.1 — User stories

> As a **researcher viewing a run**, I want the provider badge on Critique cards to be as readable as on Timeline cards, so that I can scan which agent raised an item without squinting.

> As a **dev working on the design system**, I want `<Chip tone="claude">` to render identically wherever it appears, so that I don't have to add a scoped CSS override every time a chip lands in a new container.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Critique provider chip is readable
> GIVEN a run-detail view with the Critique pane open and at least one item raised by `claude`
> WHEN the user inspects the `<Chip>` inside `.item-card__head` rendered at [run-detail.jsx:1956-1963](src/dual_research/ui/static/run-detail.jsx:1956)
> THEN the computed background is `color-mix(in srgb, var(--p-sable) 30%, transparent)` (not `rgba(212,165,116,0.08)`) and the chip is visually indistinguishable from the same chip rendered in `.tl-card-head` in the Timeline pane.

> **Scenario 2:** Cross-surface parity for the GPT provider chip
> GIVEN the same run-detail view in light mode
> WHEN the user compares the GPT provider chip in Timeline (`.tl-card-head`), Critique card head (`.item-card__head`), Critique lifecycle rows (`.lc-row-chips`), and the DS gallery at `/#/language`
> THEN all four chips share the same background tint (30% sage), the same text colour (`var(--md-on-secondary-container)` resolving to `#0a322d`), and the same border treatment — pixel-equivalent up to surrounding container differences.

> **Scenario 3:** Removed overrides do not leave the System / activity chips behind
> GIVEN the Timeline pane with the activity-mono chip (`turn 2` / `brief` / `plan`) and the System identity chip visible
> WHEN the user inspects them after this fix lands
> THEN the activity-mono chip still renders on `var(--md-surface-container-highest)` and the System chip still renders on the 20% idle tint with `var(--md-on-surface)` text — these two overrides are explicitly *kept* per §3.3.

## 5. Regression-prevention test

- [ ] **Visual parity Playwright test** (`tests/test_ui_provider_chip_parity.py` or extend the nearest existing visual-regression test under `tests/`): load `/#/language` (the DS gallery) and at least one cached run-detail view; assert that the computed `background-color` of `.chip.tone-claude` is identical across `.tl-card-head`, `.item-card__head`, `.lc-row-chips`, and the gallery surface; ditto for `.chip.tone-gpt`. Fails before this fix (critique card head + gallery diverge), passes after.

- [ ] **CSS lint/grep guard** (extend `scripts/spec_lifecycle/validator.py` or a new lightweight check under `scripts/`): grep both stylesheets for any rule matching `.<container>.*\.chip\.tone-(claude|gpt)\s*{` and fail CI if more than one such rule exists outside the base `.chip.tone-{claude,gpt}` declarations. Prevents the regression where a future consumer adds a scoped override again.

## 6. Blast radius

`<Chip tone="claude">` / `<Chip tone="gpt">` callsites in the live app:

| File:line | Container | Today | After |
|---|---|---|---|
| [run-detail.jsx:1253-1260](src/dual_research/ui/static/run-detail.jsx:1253) | `.tl-card-head` (Timeline) | 30% via scoped override | 30% via base rule (override deleted, visually identical) |
| [run-detail.jsx:1431](src/dual_research/ui/static/run-detail.jsx:1431) | (verify in implementation) | 8% if no scope override | 30% — readable improvement |
| [run-detail.jsx:1621](src/dual_research/ui/static/run-detail.jsx:1621) | (verify in implementation) | 8% if no scope override | 30% — readable improvement |
| [run-detail.jsx:1956-1963](src/dual_research/ui/static/run-detail.jsx:1956) | `.item-card__head` (Critique) | **8% — the bug** | 30% — fixes the bug |
| [shared.jsx:1330](src/dual_research/ui/static/shared.jsx:1330), [shared.jsx:1411](src/dual_research/ui/static/shared.jsx:1411) | (verify in implementation) | 8% if no scope override | 30% — readable improvement |
| [design-language.jsx:108-109](src/dual_research/ui/static/design-language.jsx:108) | DS gallery `/#/language` | 8% | 30% — gallery now reflects the canonical rendering |
| [how-it-works.jsx:663](src/dual_research/ui/static/how-it-works.jsx:663) | how-it-works pane | 8% | 30% — readable improvement |

Lifecycle rows (`.lc-row-chips`) already rendered at 30% via their scoped override; deleting that override moves them to render at 30% via the base rule — same visual result.

Non-chip consumers of `--claude-bg` / `--gpt-bg` (the 8%-rgba alias tokens) are untouched:
- [compare.jsx:220](src/dual_research/ui/static/compare.jsx:220) — inline style on a draft panel, still 8%.
- [components.css:1322-1323](src/dual_research/ui/static/components.css:1322) — `.sci__msg` chat bubble background, still 8%.
- [shared.jsx:16-17](src/dual_research/ui/static/shared.jsx:16) — AGENT_META.bg metadata, still resolves to 8%.

The 8%-rgba tokens stay; only the chip rule decouples from them.

## 7. Out of scope

- **Other tones** (info / ok / warn / err / idle / muted). Their base-rule treatment at [components.css:137-142](src/dual_research/ui/static/components.css:137) already uses the `color-mix(... N%, transparent)` pattern at 18–28%. Whether 18% is the right value on the current M3 card surface is a separate readability audit — not part of this spec.
- **`.tl-card-head .chip.tone-neutral:not(.mono)` and `.tl-card-head .chip.tone-neutral.mono`** overrides. These govern System identity and the mono activity chip respectively, which are timeline-specific affordances per [SPEC.md:464-465](design-system/SPEC.md:464). They stay scoped. If the critique pane ever needs a System chip in its head (it does not today per spec 0205 Bug 5), that's a separate spec.
- **Token cleanup.** The `--claude-bg` / `--gpt-bg` 8%-rgba aliases stay defined and stay in use by non-chip callsites. Renaming or removing them is not part of this spec.
- **Refactoring `.tl-card-head` / `.item-card__head` markup**. We are touching CSS rules and the SPEC.md doc only; JSX is untouched.
- **DS gallery audit.** This spec will incidentally improve the `/#/language` gallery rendering (since the gallery is one of the broken consumers). A broader gallery audit / cross-surface visual review is deferred to a follow-up dev spec to be drafted post-merge if needed.

## 8. Risks

- **A latent caller actually wanted the 8% dim treatment.** Mitigation: the blast-radius scan above enumerates every `tone="claude"` / `tone="gpt"` callsite; none of them are surface-darkening their container, so 30% is uniformly the better rendering. If a future caller wants dim, they should use `tone-muted` (already 8%-style via `--md-surface-container`) rather than overriding identity tones.
- **Light-mode token drift.** We are replacing the defensive hex backstop with a token reference (`--md-on-primary-container`). If a future spec changes the light-mode value of that token, identity-chip text colour follows it. That is the correct behaviour for a token-driven DS — spec 0165's defensive hex was a one-off concession for a scoped fix that is now obsolete.
- **Two-file drift.** The live-app `components.css` and the DS-side `composed-components.css` must move in lockstep (CLAUDE.md rule). Implementation must verify byte-for-byte equivalence of the new `.chip.tone-claude` / `.chip.tone-gpt` rules in both files in the same commit.
- **SPEC.md staleness.** §4.4's chip-polish table and §6 Chip primitive both need touching in the same PR or the docs misrepresent the code. Implementation must include the SPEC.md edits described in §3.4 — not as a follow-up.
