# Spec 0170 — critique-entry revision request

Audit by the critique session (2026-05-22) against the live
`prototypes/critique-iteration/` workshop. Four concrete divergences that
would prevent `/canvas critique` from reproducing the existing workshop
bit-for-bit. Plus one clarification.

All edits live in `specs/0170-canvas-workshop-skill-and-scaffold.md` only;
no new spec needed if these land.

---

## Revision 1 — `states[].click` selector format won't match the live DOM

**0170 §2.1, lines 94-98 currently say:**

```yaml
states:
  - { name: "P0",    click: "[data-phase-tab='P0']" }
  - { name: "P2",    click: "[data-phase-tab='P2']" }
  - { name: "P4",    click: "[data-phase-tab='P4']" }
  - { name: "sigma", click: "[data-phase-tab='sigma']" }
```

**Problem.** The live critique-pane DOM has no `data-phase-tab` attribute
anywhere. Verbatim markup from `_dump-p0.html`:

```html
<button class="phase-tab is-active">
  <span class="pcode">P0</span>
  <span class="pname">Brief</span>
</button>
<button class="phase-tab">
  <span class="pcode">P2</span>
  <span class="pname">Negotiate</span>
</button>
```

The disambiguator is the **inner-text of `.pcode`** (or `.sigma` for Σ).
The workshop's own JS confirms this — `_inline-script.js:454-457`:

```js
var pcode = tab.querySelector('.pcode');
if (pcode) return (pcode.textContent||'').trim().toLowerCase();
```

**Proposed schema change.** Replace the bare CSS selector with a structured
form that supports text-match:

```yaml
states:
  - { name: "P0",    selector: ".phase-tab", match_text: "P0",    in: ".pcode" }
  - { name: "P2",    selector: ".phase-tab", match_text: "P2",    in: ".pcode" }
  - { name: "P4",    selector: ".phase-tab", match_text: "P4",    in: ".pcode" }
  - { name: "sigma", selector: ".phase-tab", match_text: "Σ",     in: ".sigma" }
```

Then `spin-up.py` (§2.3, line 144 step 4) does
`document.querySelectorAll(state.selector)` and picks the one whose
descendant matching `state.in` has `textContent.trim() === state.match_text`.

Single-state panes (timeline, today) keep `states: []` and the dumper
skips state-switching — unchanged.

---

## Revision 2 — 2-pane shell isn't in the spec

**0170 §2.1 lines 118-131 (mockup.html.tmpl) describes a single-iframe
wrapper.** The critique workshop renders a **2-pane shell**:

`prototypes/critique-iteration/_build.sh:556-557, 576-585`:

```html
<div class="wrap__stage">
  <div class="timeline-pane">…timeline stub…</div>
  <div class="critique-host">…dumped critique pane…</div>
</div>
```

with `grid-template-columns: 1fr 1fr`, so the critique pane renders at
**half the viewport width**. That's the production-fidelity layout — the
critique pane is the right column of `.rdvc__split`, never full-width.

This isn't optional. The narrow-mode `@media (max-width: 1799px)`
behaviours that drove iters 7.2 / 7.3 (drop counts from segmented controls,
hide kind labels) only fire at the correct viewport-relative width.
Without the 2-pane shell, the critique iframe renders full-width and
those `@media` rules never activate.

**Proposed registry addition.**

```yaml
critique:
  …existing fields…
  shell: "2-pane"                # "single" (default) | "2-pane"
  shell_companion:
    side: "left"                  # which side the companion sits on
    label: "Timeline stub"
    file: "_dump-timeline-stub.html"  # placeholder dump or empty file
```

And in §2.2 (mockup.html.tmpl) add `{{shell_html}}` which expands to
either the single-iframe layout or the 2-pane grid wrapper based on
`shell:`. The companion file path resolves relative to the workshop dir.

---

## Revision 3 — `.phase-state` wrapper attribute name mismatch

**0170 §2.3 line 145 says** the dumper wraps each state as:

```html
<section class="phase-state" data-state="X">
```

**Critique workshop uses** (`_build.sh:592`):

```html
<section class="phase-state" data-phase="X">
```

The JS handlers in `_inline-script.js` key off `data-phase` (line 519:
`s.querySelectorAll('.phase-tab')` looking inside `.phase-state`
elements). Changing the attribute name in the spec would silently break
the in-iframe tab-switch handler.

**Proposed.** Change §2.3 line 145 from `data-state="X"` to
`data-phase="X"` (or settle on `data-state` everywhere and update the
critique JS — but the JS is already locked in spec 0168). `data-phase`
wins. The timeline's single-state surface doesn't use this attribute so
it's unaffected.

---

## Revision 4 — iframe scroll containment is required for critique

The critique workshop wrappers add (lines 538-543 in `_build.sh`):

```css
html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
```

This is iter 2.1's hard-won fix. Without it, expanding the "Resolved"
crit-group inside the iframe makes the **page itself** scroll vertically,
the scrollbar appears, the iframe's effective width shrinks by 5–17 px,
and bar 2 wraps to two rows — invalidating every wide-mode iter.

The spec's mockup.html.tmpl (§2.1 line 118) doesn't mention iframe-side
overflow rules. The single-iframe story works because timeline scroll is
internal to `.tl-phase__list`. But for critique, the pane has its own
`.crit2__body { overflow: auto }` from the live CSS, and that has to
become the scroll container.

**Proposed.** In §2.2 add a registry field per pane:

```yaml
critique:
  iframe_overflow: "hidden"   # forces html/body { overflow: hidden } in the iframe wrapper
```

Default `null` (no rule). Critique sets `"hidden"`. Timeline leaves it
unset.

Then the dumper emits, when set, the corresponding `<style>` block in the
generated `live.html` / `proposed.html` `<head>` so the iframe's
scroll container is the pane body, not the document.

---

## Clarification — `<script>` blocks accumulate alongside `<style>` blocks

**0170 §2.2 line 129 says** proposed.html accumulates
`<style id="iter-N-…">` blocks. The critique workshop also accumulates
**`<script>` logic** (`_inline-script.js`, 524 lines, runs inside an
IIFE at the end of `proposed.html`) — head rebuild, lifecycle injection,
source-meta chip injection, auto-expand logic. These behaviours are part
of the iter output and get folded into the dev spec (spec 0168 §2.7,
§2.8, §2.10).

**Proposed.** Reword §2.2's `proposed.html.tmpl` description to read:

> Starts as a verbatim copy of `live.html`. Iterations accumulate stacked
> `<style id="iter-N-…">` blocks at the top of `<head>` and may also add
> a bottom-of-body `<script>` block (or modify the existing one) for
> behaviour changes that can't be expressed in CSS alone. Both are part of
> the locked iter output that feeds the dev spec.

Not a behaviour change — just an honest description of what iters
produce.

---

## Severity + recommended action

Items 1-4 are correctness bugs in the critique registry entry. Item 5 is
documentation honesty. None of them are large enough to redesign 0170 —
they're surgical edits to:

- `specs/0170-canvas-workshop-skill-and-scaffold.md` lines 87-108
  (critique registry block) — add `shell`, `iframe_overflow`,
  `shell_companion`; restructure `states` to support text-match
- Line 118 (mockup.html.tmpl description) — add `{{shell_html}}` token
- Line 129 (proposed.html.tmpl description) — acknowledge `<script>`
  blocks
- Line 145 (scaffold script dump step) — `data-phase`, not `data-state`;
  honor the new selector schema

Estimated edit: ~40 lines changed, no new sections. After these edits,
`/canvas critique` should reproduce the existing workshop byte-for-byte
modulo `proposed.html` and `NOTES.md`.

Recommend: edit 0170 in the timeline session before `/dev-next` picks it
up. No addendum spec needed.
