---
kind: dev
spec: "0166"
slug: timeline-pane-system-error-chips-and-live-state
title: Timeline pane — System + Error chip primitives + brief-card refactor + live-state agent-strip wiring + turn-render data-layer fix
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 2
depends_on: ["0164"]
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: timeline-iteration-2026-05-22
promoted_from_draft: "006"
---

# Spec 0166 — Timeline pane System + Error chip primitives + live-state agent strip + turn-render data-layer fix

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0164 (M3 card chrome must exist before agentless cards + live-state strip sit on the new card chrome)
> **Bump:** MINOR — adds two new chip primitives, wires an existing animation that was unreachable in production, and fixes a small data-layer bug that produces `turn [object object]` in the wild.

---

## 1. Context

Three independent threads converge in this spec:

**(A) Agentless cards have no leading identity chip.** The Phase 0 "brief" card and any render-error fallback card currently render with a `.chip.tone-neutral` containing a Material `file-document` icon + label `brief`. Agent turn cards render with a Claude or GPT identity chip immediately followed by the activity chip — the canonical `[identity] [activity]` composition documented in `design-system/SPEC.md` §9.2 / §9.4. Agentless cards break that rule by omitting the identity chip entirely. The design system has no `System` primitive.

**(B) A turn-render data-layer bug produces `turn [object object]` in the wild.** In the anchor run `20260521-010637-dvs-backend-language-choice` (Phase 4 cross-review), one turn card stringifies to `turn [object object]`. A JS template like ``turn ${turnNumber}`` is being handed the `Turn` record object instead of its numeric index. The UI has no defensive fallback — the broken string just renders as the activity-chip label. Even after the upstream stringification is fixed, the absence of a defensive render path means any future similar bug will silently corrupt the card head.

**(C) The live-state agent-strip animation isn't wired into production.** Spec 0138 §5.1 added a `.as.in-header.is-live::before` gradient sweep at `src/dual_research/ui/static/components.css:429` (the `@keyframes as-pulse-sweep` block runs through approximately L491) — a 3.2 s ease-in-out sweep over an 18 %-alpha agent-tinted gradient that fires when `.as.in-header` carries the `.is-live` class. GPT gets `animation-delay: -1.6s` so the two strips sweep out of phase. `prefers-reduced-motion: reduce` falls back to a static tint. The CSS exists and is correct, but no production JSX path currently sets `.is-live` on either strip. Concretely, the activity dot stays static grey instead of pulsing info-blue, the activity phrase shows the terminal state ("deadlocked") instead of the running phase, and there's no elevation lift signalling "this agent is doing work right now."

Three iterations + one data-layer fix, all in one MINOR release.

## 2. Proposed change

### 2.1 SystemChip primitive

**Markup target** (lands as a `SystemChip` helper component in `src/dual_research/ui/static/shared.jsx`):

```jsx
function SystemChip() {
  return (
    <span className="chip tone-neutral no-dot" aria-label="System">
      <span className="chip-leading-icon" aria-hidden="true">
        <span style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 12, height: 12, borderRadius: 3,
          background: 'var(--p-idle)', color: '#ffffff',
          flexShrink: 0, lineHeight: 1,
        }}>
          {/* Material Icons "settings" gear, 8×8 inside a 12×12 idle-colored square */}
          <svg viewBox="0 0 24 24" width="8" height="8" aria-hidden="true">
            <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z" fill="currentColor" />
          </svg>
        </span>
      </span>
      <span className="chip-label">System</span>
    </span>
  );
}
```

**CSS** (the background rule lands with spec 0165 §2.2 — when both specs are in the queue, coordinate so the rule lands exactly once; if 0165 lands first, this spec doesn't restate it. If 0166 lands first, include the rule here):

```css
.tl-card-head .chip.tone-neutral:not(.mono) {
  background: color-mix(in srgb, var(--p-idle) 20%, transparent);
  color: var(--md-on-surface);
}
```

The 12×12 idle-coloured square mirrors the Claude / GPT chip's `chip-leading-icon` anatomy exactly — same dimensions, same border-radius (3 px), same `flex-shrink: 0`, same line-height. The settings-gear glyph is the Material Icons `settings` filled path at 8×8 inside the 12×12 square, which keeps the visual weight of the System chip identical to the brand chips.

**Files to change.**
- `src/dual_research/ui/static/shared.jsx` — add the `SystemChip` helper.
- `src/dual_research/ui/static/components.css` — add the scoped `.tl-card-head .chip.tone-neutral:not(.mono)` rule (if not already added by spec 0165).
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §3 Primitives — add a new "System chip" row alongside the existing identity chips (Claude / GPT). Document the Material settings-gear glyph, the `--p-idle` colored 12×12 square, the label vocabulary ("System"), the 20 % color-mix background.
- `design-system/SPEC.md` §9.2 — extend the canonical-kinds table with a "System" identity kind alongside Claude and GPT.
- `design-system/assets/Design System v2.html` §9 + §16 — render examples.

### 2.2 ErrorChip primitive

**Markup target** (helper in `shared.jsx`):

```jsx
function ErrorChip({ label }) {
  return (
    <span className="chip tone-err no-dot" aria-label={label}>
      <span className="chip-leading-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"
             style={{ width: 12, height: 12, color: 'currentColor' }}>
          {/* Material Icons "error" filled-circle */}
          <path d="M12,2C6.48,2 2,6.48 2,12s4.48,10 10,10s10-4.48 10-10S17.52,2 12,2z M13,17h-2v-2h2V17z M13,13h-2V7h2V13z"
                fill="currentColor" />
        </svg>
      </span>
      <span className="chip-label">{label}</span>
    </span>
  );
}
```

Inherits `.chip.tone-err` styling (err-color background + text — `--p-err` + `--md-on-error-container`). No new CSS rule required; the existing `.chip.tone-err` token mapping resolves correctly.

**Label vocabulary.** Each error condition gets a canonical human-readable phrase. If the data layer carries an error code, the chip label is the human translation, NOT the raw code:

- "Could not render this turn" — turn-record stringification failure (the bug at §2.4 below)
- "Turn data missing" — event-store gap (the expected turn payload was absent)
- "Agent timed out" — the agent's HTTP request exceeded the orchestrator timeout
- "Empty turn received" — the agent returned an empty body

The vocabulary table lives in `design-system/SPEC.md` §9.5 — this spec extends that table with the new ErrorChip phrases.

**Files to change.**
- `src/dual_research/ui/static/shared.jsx` — add the `ErrorChip` helper.
- `design-system/SPEC.md` §3 — new Error chip primitive row.
- `design-system/SPEC.md` §9.5 — new row for "Error" with the canonical human-readable phrases listed above.
- `design-system/assets/Design System v2.html` — render an Error chip example.

### 2.3 Brief-card refactor — `[System] [brief]`

**Now.** The agentless brief card render at `src/dual_research/ui/static/run-detail.jsx` (search for `item.kind === 'input'` near the turn-card render around line 1223) emits a single `.chip.tone-neutral` carrying a Material `file-document` icon + label "brief". No leading identity chip.

**After.** Two chips: `<SystemChip />` + `<Chip mono tone="neutral" label="brief" />`. The activity-chip's `file-document` icon is dropped to match the canonical activity-chip anatomy (label-only, mono font, neutral tone).

The JSX condition stays the same (`!agent && item.kind === 'input'`) — only the chip composition inside the branch changes:

```jsx
{!agent && item.kind === 'input' ? (
  <>
    <SystemChip />
    <Chip mono tone="neutral" label="brief" />
  </>
) : (
  /* existing agent + activity branch unchanged */
)}
```

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx:1223` (approximate — the existing `item.kind === 'input'` branch in the turn-card render).

### 2.4 Defensive error render + `[object object]` data-layer fix

**Now.** The turn-card render derives the activity label from a template like ``turn ${turnIndex}`` (search `run-detail.jsx` for `turn ${` near the agent-turn render). In the anchor run, one Phase 4 cross-review turn passes a `Turn` object instead of a number into that template, producing the literal text `turn [object object]`. The card head renders that string verbatim — no defensive guard.

**After.** Two coordinated fixes:

**Data-layer fix (the real fix).** Locate the call site that constructs the activity label. The value being interpolated should be the turn's numeric index (likely `turn.index` or `turn.round`, not the whole turn record). Fix the field reference.

**Defensive render path (the backstop).** Wrap the activity-label derivation in a try/catch. If the derived value is non-numeric, or the derivation throws, fall back to the System + Error chip composition:

```jsx
let activityLabel;
try {
  activityLabel = `turn ${turnIndex}`;
  if (typeof turnIndex !== 'number') {
    throw new Error('turnIndex is not a number');
  }
} catch (e) {
  // Defensive: show a human-readable error instead of stringifying
  return (
    <>
      <SystemChip />
      <ErrorChip label="Could not render this turn" />
    </>
  );
}
```

The defensive path renders `[System] [Could not render this turn]` instead of `turn [object object]`. The aria-label on the ErrorChip carries the same phrase so screen readers announce the failure.

After the data-layer fix lands, the defensive path should never fire on healthy data — it's strictly a safety net for future regressions.

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — find the activity-label template + fix the field reference + wrap with the try/catch fallback.

### 2.5 Live-state agent strip — `.is-live` wiring + dot pulse

**Now.** The animation CSS exists at `src/dual_research/ui/static/components.css:429–491` (the `@keyframes as-pulse-sweep` block + the `.as.in-header.is-live::before` rule + the GPT `animation-delay: -1.6s`). No JSX path currently sets `.is-live` on `.as.in-header`. The activity dot is static grey; the activity phrase shows the terminal state.

**After.** Derive `isLive` per agent from the run state: which agent is currently doing work this round. Use the run's `liveAgent` / `currentRoundAgent` field (whatever the existing run-state model names the field — search `run-detail.jsx` for `liveAgent` or `currentRound` to locate it).

JSX:

```jsx
const isLive = liveAgent === agentKey;  // 'claude' for .is-a, 'gpt' for .is-b

<div className={`as is-${agent === 'claude' ? 'a' : 'b'} in-header${isLive ? ' is-live' : ''}`}>
  …
</div>
```

When `isLive`:
- The existing spec 0138 sweep fires automatically (no additional CSS — adding `.is-live` is sufficient).
- The activity dot's background flips from `var(--md-outline)` (neutral grey) to `var(--p-info)` (info blue).
- The dot carries a slow halo pulse via the new `@keyframes pulse-info`.
- The activity phrase shows the live phase-and-round context (e.g. `"negotiating · round 4"` / `"reviewing · round 2"` / `"drafting"`) instead of the static terminal state.

Dot pulse keyframe + rule:

```css
@keyframes pulse-info {
  0%, 100% { box-shadow: 0 0 0 0   color-mix(in srgb, var(--p-info) 60%, transparent); }
  50%      { box-shadow: 0 0 0 4px color-mix(in srgb, var(--p-info)  0%, transparent); }
}

.as.in-header.is-live .activity-dot {
  background: var(--p-info);
  animation: pulse-info 2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .as.in-header.is-live .activity-dot {
    animation: none;
    box-shadow: none;
  }
}
```

The `prefers-reduced-motion` fallback zeros out the dot animation. The strip-level sweep already has its own reduced-motion fallback in spec 0138 (the `::before` becomes a static tint).

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — derive `isLive` per agent, set `.is-live` class on the strip, switch the activity phrase to the live context when `isLive` is true.
- `src/dual_research/ui/static/components.css` — add the `pulse-info` keyframe + the `.is-live .activity-dot` rule + the reduced-motion fallback.
- `design-system/assets/styles/composed-components.css` — same.

### 2.6 Live-strip elevation lift

**Now.** `.as.in-header` carries no `box-shadow` in any state. The live state is signalled only by the sweep + dot pulse.

**After.** When the strip is `.is-live`, lift it with `--md-elev-2`:

```css
.as.in-header.is-live {
  box-shadow: var(--md-elev-2);
  transition: box-shadow var(--md-dur-short-3) var(--md-easing-standard);
}
```

`elev-2` is chosen over `elev-1` (too subtle for a sticky header strip) and `elev-3` (reads as a modal/dialog). The shadow is the fourth reinforcing live-state signal alongside the sweep, the dot pulse, and the live activity phrase.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the rule.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.4 — add: *"The live-state agent strip carries `--md-elev-2` shadow + a 2 s info-blue dot pulse + the spec 0138 §5.1 gradient sweep. Reduced-motion fallback (per spec 0138 + new dot-pulse fallback): static `--md-surface-container-high` background, no sweep, no pulse — elevation lift is retained as the static state signal."*
- `design-system/assets/Design System v2.html` §16 — render an `.is-live` example showing the lift.

## 3. UX / behaviour

After this spec lands:

- The Phase 0 "brief" card starts with `[System] [brief]` — same composition pattern as agent cards (`[Claude] [turn 1]` / `[GPT] [turn 2]` / etc.).
- Any future agentless cards (orchestrator status messages, system notifications) reuse the System chip primitive.
- When the data layer hands the activity-label template an object instead of a number, the card renders `[System] [Could not render this turn]` defensively. The upstream `[object object]` stringification is also fixed at the source.
- When an agent is currently doing work on the active round, its `.as.in-header` strip carries four reinforcing live signals:
  1. Sable / sage gradient sweep across the strip (3.2 s, 18 % peak — spec 0138)
  2. Info-blue activity dot with a 2 s soft-pulse halo
  3. Live activity phrase (`"negotiating · round 4"` / `"drafting"` / `"reviewing · round 2"`) replacing the terminal-state phrase
  4. `elev-2` shadow lifting the strip off the pane surface
- When the agent is not currently active, the strip reverts to static styling (no sweep, no pulse, no shadow, terminal-state phrase).
- `prefers-reduced-motion: reduce` zeros out the sweep, the dot pulse, and any animation. The `elev-2` lift + live activity phrase are retained as static signals so the live state still degrades gracefully.

## 4. Data / schema deltas

None for the visual changes. The data-layer fix (§2.4) is internal to `run-detail.jsx` — no event-store / run-detail JSON / run-summary changes.

## 5. Out of scope

- M3 card chrome / pane gutter / provider stripe / narrow-mode strip equalisation — delivered by spec 0164.
- Identity-chip backgrounds (Claude / GPT 30 % color-mix), activity-chip surface bump (highest), phase-chip bubble dim, cost precision, light-mode token drift — delivered by spec 0165. (Note: the `.tl-card-head .chip.tone-neutral:not(.mono)` rule is shared between 0165 §2.2 and this spec §2.1; coordinate so it lands once.)
- Critique-pane System / Error chip integration — separate critique spec (the primitives are added here; critique reuses them).
- New live-state signals beyond the four listed (sweep + dot + phrase + lift). Future polish (e.g. progress bars) is its own spec.

## 6. Design-system gate

Cited DS sections being updated:

- `design-system/SPEC.md` §3 Primitives — new SystemChip row, new ErrorChip row.
- `design-system/SPEC.md` §9.2 — canonical-kinds table extended with "System" identity.
- `design-system/SPEC.md` §9.5 — vocabulary table extended with the Error chip phrases.
- `design-system/SPEC.md` §4.4 Timeline pane — live-state agent strip styling (sweep + pulse + elev-2 + reduced-motion fallback).
- `design-system/SPEC.md` §2.11 — confirm reduced-motion contract covers the new dot-pulse.

Files that MUST land in the same commit:

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/Design System v2.html` (SystemChip + ErrorChip examples + live-strip example)
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/run-detail.jsx`
- `src/dual_research/ui/static/shared.jsx` (new SystemChip + ErrorChip helpers)
- `CHANGELOG.md`
- `pyproject.toml`
- `src/dual_research/__init__.py`

## 7. Test plan

- [ ] **Brief card composition.** Render a run with a P0 brief. The brief card head contains exactly two chips: `[System]` then `[brief]`. The System chip has `aria-label="System"`, contains a 12×12 idle-colored square with a Material settings-gear SVG at 8×8 inside. The brief chip is `.chip.tone-neutral.mono` with label "brief", no leading icon.
- [ ] **System chip — DS reference.** Open `design-system/assets/Design System v2.html` §3 + §9 + §16. The SystemChip primitive is documented with the gear glyph, the 12×12 idle square, the 20 % color-mix background. Rendered examples match the live impl.
- [ ] **Error chip — DS reference.** Same file, §3 + §9.5. The ErrorChip primitive is documented with the filled-error-circle glyph. The §9.5 vocabulary table includes "Could not render this turn", "Turn data missing", "Agent timed out", "Empty turn received".
- [ ] **Data-layer fix — healthy case.** Render the anchor run `20260521-010637-dvs-backend-language-choice` in Phase 4 cross-review. No card renders `turn [object object]`. The previously-broken card renders `turn N` with the correct numeric index.
- [ ] **Defensive render — broken case.** Inject a fixture turn where `turnIndex` is an object (or `undefined`). The card head renders `[System] [Could not render this turn]`. The ErrorChip has `aria-label="Could not render this turn"`. No `[object object]` text appears anywhere in the rendered DOM.
- [ ] **`.is-live` wiring.** Start a run via `uv run dual-research run --prompt "test" --push-while-running` and observe the run-detail page. While the orchestrator is mid-round on a Claude turn, the Claude strip has class `is-live` on `.as.is-a.in-header`. The GPT strip does NOT have `.is-live`. When the round flips to GPT, the classes flip.
- [ ] **Sweep animation fires.** With `.is-live` set, the `::before` pseudo-element of `.as.in-header.is-live` is animating `as-pulse-sweep` 3.2 s ease-in-out infinite. Visible in DevTools animations panel.
- [ ] **Dot pulse fires.** `.as.in-header.is-live .activity-dot` is animating `pulse-info 2s ease-in-out infinite`. Computed `animation` matches that string.
- [ ] **Activity phrase swaps to live context.** When `.is-live` is on, `.as-activity` text content matches the running phase + round (e.g. `"negotiating · round 4"`). When the strip is NOT live (post-completion or pre-start), the phrase shows the terminal/static state.
- [ ] **Elev-2 lift.** `.as.in-header.is-live` computed `box-shadow` matches the resolved `--md-elev-2` token. Visible visually as a lift above the pane surface.
- [ ] **Reduced-motion fallback.** Emulate `prefers-reduced-motion: reduce` via Chrome DevTools. With `.is-live` set: no sweep on `::before`, no dot pulse animation. The `elev-2` shadow is retained. The activity phrase still shows the live context (text-based signals stay).
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0.

## 8. Implementation steps (suggested order)

1. Add `SystemChip` + `ErrorChip` helpers to `src/dual_research/ui/static/shared.jsx` (§2.1, §2.2).
2. Update `design-system/SPEC.md` §3 + §9.2 + §9.5 to document the new primitives + vocabulary.
3. Render the primitives in `design-system/assets/Design System v2.html` §3 / §9 / §16 for the visual reference.
4. Fix the data-layer bug at `run-detail.jsx` (§2.4) — identify the field, swap to the correct field reference.
5. Wrap the activity-label derivation in the try/catch fallback that emits `[SystemChip] [ErrorChip]` (§2.4 defensive path).
6. Refactor the brief-card branch to `[SystemChip] [<Chip mono label="brief">]` (§2.3).
7. Derive `isLive` and add `.is-live` to the strip JSX (§2.5).
8. Add the `pulse-info` keyframe + the dot-animation rule + the reduced-motion fallback + the `.is-live` elev-2 rule to both `design-system/assets/styles/composed-components.css` and `src/dual_research/ui/static/components.css` (§2.5, §2.6).
9. Run the test plan (§7) including the live-run smoke test in step `.is-live` wiring.
10. Write the CHANGELOG entry. Bump version files.
