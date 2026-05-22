# Critique-card design · iteration brief

> **Paste everything below this line into the critique-iteration session.** Self-contained. Don't summarise before pasting.

---

You are continuing the critique-pane workshop at `prototypes/critique-iteration/`. The next iteration focuses on **how an individual critique card should look inside a phase view** — the card's own visual composition, in isolation. This brief tells you what's in scope, what's out of scope, and which design language to apply.

## 1. What this iteration is about

A critique pane shows items grouped by status (`Open · new` / `Open · carried` / `Resolved` / `Drift`) inside each phase (P0 / P2 / P4 / Σ Summary). Each item is one card. That card is what we're designing.

We are NOT touching anything outside the card silhouette this iteration. Specifically out of scope:

- The phase-header chip cluster on the timeline pane (Q / D / I / C category **counter** chips). Those are pane-level summary badges and not part of an individual card's view.
- The pane's Bar 1 / Bar 2 chrome (phase tabs, kind tabs, agent + status segmented filters, drift chip). Don't reopen those — earlier iters already shipped those changes.
- The status-group section headers (`Open · new`, `Resolved`, etc.).
- The Σ Summary tab body — that's a different layout entirely.

The card itself, isolated, is the only surface we're iterating on.

## 2. The badges + slots inside an individual card

In scope for this iteration:

1. **Provider chip** — who raised this item. Same primitive as the timeline `[Claude]` / `[GPT]` / `[System]` identity chip. Brand-mark SVG inside a colored 12×12 square, label "Claude" / "GPT" / "System". This is the leading slot of the card head.

2. **Round / turn badge** — when this item was raised. Equivalent to the timeline's `turn N` activity chip (mono, tone-neutral). Vocabulary: `raised in r1` / `r2` / etc. — lowercase, no abbreviation. Inside the card head, immediately after the provider chip.

3. **Status / lifecycle chip** — the item's current state. Vocabulary from spec 0119 §9.5: `raised` / `addressed` / `resolved` / `acknowledged` / `withdrawn` / `capped` / `drift`. Right-aligned in the card head. Never bare — every card carries a status chip.

4. **Optional modifier chips** — `via hard cap` / `via ghost cap` / `↻ closeout` / `⚠ unverified` / `⚠ ledger drift`. Right cluster, before the status chip when present.

5. **Body** (when expanded) — the item text. Italic serif (`var(--md-font-brand)`) for the quote / question / disagreement statement.

6. **Lifecycle timeline** (when expanded) — vertical list of transitions, one row per round. Each row is `[provider] [round N] [verb]` + reason. Same chip primitives as the head, smaller.

7. **Footer** (when terminal) — single tinted line: `✓ resolved at round 3 · 2 turns to converge` (or capped / acknowledged / withdrawn variants).

8. **SOURCES (N)** segment (when N > 0) — per spec 0144 §6.3.d / §4.7. Dashed top border, `Sources (N)` overline, vertical stack of `SourceRow` instances.

Out of scope for this iteration (explicitly):

- The card's **kind badge** (Question / Disagreement / Issue / Comment chip). The user has scoped this iteration to exclude that badge; the card's kind is conveyed by which filter / section it lives in, not by an in-card badge. Don't add or modify a kind badge.
- The pane-level Q / D / I / C **counter** chips (they're on the phase header, not on cards).

## 3. Design language to apply (lifted from the locked timeline iterations)

Read `prototypes/timeline-iteration/NOTES.md` for the per-element detail. The condensed playbook to apply to critique cards:

### Frame (collapsed state)
- Background: `var(--md-surface-container-high)` — one tier brighter than the pane surface
- Border: `1px solid var(--md-outline-variant)` — visible outline, not hair
- **2 px left stripe** in provider color via `:has()`:
  - Claude raise → `var(--p-sable)`
  - GPT raise → `var(--p-sage)`
  - System raise → `var(--p-idle)`
- Border-radius: `var(--md-shape-lg)` (16 dp, M3-Expressive)
- Padding: 0 on the card itself; head owns its own 10–12 px padding
- Transition: `background`, `box-shadow`, `border-color` — 150 ms standard easing
- Hover: surface bumps to `--md-surface-container-highest`, border to `--md-outline`, plus `var(--md-elev-1)` shadow

### Frame (expanded state)
- Background: `var(--md-surface-container-low)` (one tier darker than collapsed — same pattern as timeline expanded)
- `var(--md-elev-2)` shadow lift
- Card head gets `var(--md-surface-container-high)` background + 1 px hairline bottom border to separate from body
- Body: italic serif on `--md-on-surface-variant`
- Actions row: tonal button (`--md-primary-container` / `--md-on-primary-container`) + spacer + supporting chips (token usage, cost — see §4 on cost precision)

### Provider chip — backgrounds
The identity-chip background opacities locked in for timeline apply here too:
- `.crit2 .item-card__head .chip.tone-claude` → `color-mix(in srgb, var(--p-sable) 30%, transparent)`
- `.crit2 .item-card__head .chip.tone-gpt` → `color-mix(in srgb, var(--p-sage) 30%, transparent)`
- `.crit2 .item-card__head .chip.tone-neutral:not(.mono)` → `color-mix(in srgb, var(--p-idle) 20%, transparent)` + `color: var(--md-on-surface)`

(Scope selectors to whatever the actual critique-card head class is in your dumped DOM — likely `.item-card__head` per spec 0144. Don't touch the global `.chip.tone-X` token — that affects critique-pane summary chips and other surfaces.)

### Light-mode drift fix (still applies)
`tokens.css` is missing `--md-on-primary-container` / `--md-on-secondary-container` overrides for `body.light`, so Claude/GPT chip text inherits the dark-mode values (`#f3deca` / `#cfece6`) and reads washed-out on cream. Force the dark text explicitly inside the card head:
```css
body.light .crit2 .item-card__head .chip.tone-claude,
body.light .crit2 .item-card__head .chip.tone-claude .chip-label { color: #3b2810 !important; }
body.light .crit2 .item-card__head .chip.tone-gpt,
body.light .crit2 .item-card__head .chip.tone-gpt .chip-label { color: #0a322d !important; }
```

### Activity / round chip
The `raised in rN` chip uses `.chip.tone-neutral.mono` — same surface drift fix:
```css
.crit2 .item-card__head .chip.tone-neutral.mono {
  background: var(--md-surface-container-highest) !important;
}
```
One tier brighter than the card surface, so the chip reads as a discrete badge.

### Status chip
Same vocabulary as the timeline status chip rules in spec 0119 §9.4 — right-aligned, never bare. Existing implementation likely already does this; don't change the API, just verify it visually after the card chrome changes land.

### Sources segment (when N > 0)
Per spec 0144 §4.7:
- `Sources (N)` overline in `t-overline` style (11 px uppercase, 0.06 em letter-spacing, `--md-on-surface-variant`)
- Dashed top border separating from the lifecycle footer
- Empty-state behaviour: when N === 0, **hide the entire segment** (no label, no border)
- Card-header gets a `Sources {N}` chip when N > 0; clicking jumps to the segment in-card
- `⚠ unverified` chip lives on the offending **row**, not on the card

## 4. Cost precision (carry-over from timeline iter 10)

If the critique card has any cost or token figures in its actions row or anywhere else, use **2-decimal precision** for cost (`$0.03`, `$13.51`, `<$0.01` for sub-cent). 1-decimal lives in the consumption-row spec (SPEC.md §4.3) but reads too coarse on card-internal displays.

## 5. Per-state expectations

When you build the iteration:

- **Collapsed** — card head visible only. Head shows `[provider] [raised in rN] … [status]`. Click to expand.
- **Expanded** — head + body + lifecycle + footer + SOURCES (when present). One card per phase can be pre-expanded in your iteration view so the expanded composition is auditable without clicking.

Make both states visible in the iteration tab — either side-by-side, via toggle, or by pre-expanding one card per group.

## 6. Iteration cadence (the non-negotiables — same rules as the timeline workshop)

1. **One change per iteration.** Each change gets its own `<style id="iter-N-…">` block at the top of `proposed.html`. Banner the current iter step in `wrap__banner #iter-banner`. New row in `NOTES.md`.

2. **Verify visually after every iter.** `mcp__Claude_Preview__preview_screenshot` (light mode for legibility) + `mcp__Claude_Preview__preview_inspect` for computed styles.

3. **Recreate from rendered DOM, not from JSX or specs.** If you need to know what the live critique card looks like today, dump it from the live app via `preview_eval(document.querySelector('.item-card').outerHTML)` and inspect, don't paraphrase from `run-detail.jsx` or `SPEC.md`.

4. **Use template literals** for any JS strings containing HTML. No `\\'` escaping inside single-quoted strings.

5. **CSS specificity battles** — if a rule isn't applying, check what's winning; bump specificity (e.g. `.crit2 .item-card__head .chip` beats `.chip`); only `!important` as a last resort.

6. **Don't touch the live `tokens.css`, `components.css`, or `run-detail.jsx`.** This iteration produces a mockup + NOTES.md entries only. Real-code changes get specced separately later.

7. **Don't add a Q/D/I/C kind chip to the card head.** That's explicitly out of scope for this iteration.

## 7. Bootstrap step

Before iterating, verify the critique workshop's `proposed.html` already has the timeline-derived locks applied to its critique-pane cards. If iter 4 (M3 card chrome) and iter 7 (light text drift fix) and iter 8 (provider stripes) are already in place from earlier critique iterations, this brief is incremental polish. If they're NOT in place, you have catch-up work to do first — apply the timeline-locked playbook from §3 above to bring critique cards to parity.

Either way, dump the current state of a representative critique card in `proposed.html` and confirm:
- which design lessons are already applied
- which are missing
- which would conflict if applied

Report that to me before writing any iter blocks.

## 8. When you're done with the iteration round

Update `prototypes/critique-iteration/NOTES.md` with one row per iter using the existing four-quadrant format (Now / After / DS change / Live change). Reference this brief by file path (`prototypes/critique-iteration/CARD-DESIGN-PROMPT.md`) so future-you knows where the constraints came from.

---

*End of brief. Workshop server already running on `localhost:6174` per existing `.claude/launch.json` config `prototype-mockup` — don't restart it.*
