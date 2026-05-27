---
spec: 0084
title: Unified LoadingState primitive — one delightful loading visual everywhere
label: new-feature
version-bump: PATCH
status: merged
target-version: 0.69.8
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/84"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0084 — Unified `LoadingState` primitive

## Context

Spec 0083 introduced a centred spinner + "Loading runs…" copy as the
empty state for the run list. The user liked it but pointed out two
things:

1. **The visual should feel more delightful.** A spinner with no
   secondary text is functional but cold. A friendly "please" line
   below would warm it up and match the rest of the app's voice.
2. **Other loading screens are inconsistent.** The run-detail wait
   uses `FullPageMessage` with a plain mono `<pre>` showing the run
   id. The lazy markdown / input bundle / search audit cards each
   render their own bare-text `"loading…"` div in mono. The compare
   page has a `PanelLoading` component that's just a centred string.
   None of them speak to each other.

We want **one** loading visual, sized appropriately per surface,
shared across every place the UI is waiting on a first useful
payload.

## Proposed change

### A new design-system primitive

A `LoadingState` function-component lives in `shared.jsx` next to the
other primitives. Three sizes; all three render the same elements
(spinner + label + optional hint) at different scales:

| `size`     | Spinner | Border | Layout      | Default hint              |
| ---------- | ------- | ------ | ----------- | -------------------------- |
| `inline`   | 14 px   | 2 px   | row-flex    | _none_                    |
| `panel`    | 28 px   | 2.5 px | column-flex | "Just a moment, please."  |
| `page`     | 44 px   | 3 px   | column-flex | "Just a moment, please."  |

Props:

- `size: 'inline' | 'panel' | 'page'` — default `'panel'`.
- `label: string` — primary copy, e.g. "Loading runs" or "Loading
  input bundle…".
- `hint: string | null` — secondary copy. Omit / pass `null` to
  suppress; pass a string to override the default ("please" line for
  panel/page; nothing for inline).
- `className`, `style` — passthroughs for the wrapper.

`role="status"` + `aria-live="polite"` so assistive tech announces
the loading state.

The base CSS class `.dr-spinner` (added in spec 0083) is now
size-agnostic — `width`, `height`, and `border-width` are driven by
inline style in the component so one class scales to every size.

### Surfaces that adopt `LoadingState`

| Surface                                  | Before                                             | After                                                                |
| ---------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------- |
| Run list empty state (`run-list.jsx`)    | Inline spinner + "Loading runs…" (spec 0083)       | `<LoadingState size="panel" label="Loading runs" />`                 |
| App boot (`app.jsx`)                     | `<FullPageMessage title="Loading…" body="Connecting to the server." />` | `<LoadingState size="page" label="Connecting to the server" />`      |
| Run detail wait (`app.jsx`)              | `<FullPageMessage title="Loading run…" body={runId} />` | `<LoadingState size="page" label="Loading run" hint={runId} />`      |
| Lazy markdown body (`run-detail.jsx`)    | `<div className="mono">loading…</div>`             | `<LoadingState size="inline" label="Loading…" />`                    |
| Draft body fallback (`run-detail.jsx`)   | `<div className="mono">loading…</div>`             | `<LoadingState size="inline" label="Loading…" />`                    |
| Input-bundle modal (`run-detail.jsx`)    | `<div className="mono">loading input bundle…</div>`| `<LoadingState size="inline" label="Loading input bundle…" />`       |
| Search-audit modal (`run-detail.jsx`)    | `<div className="mono">loading search audit…</div>`| `<LoadingState size="inline" label="Loading search audit…" />`       |
| Compare panel loader (`compare.jsx`)     | `PanelLoading` with bare text                       | `PanelLoading` now delegates to `<LoadingState size="panel" />`      |

`FullPageMessage` (`app.jsx`) is kept for **error** screens —
title + body + back button — which is a different concern. Only its
loading-flavoured call sites move to `LoadingState`.

### Design-language manifesto reconciliation

`design-language.jsx` previously asserted "**No spinners** (the live
caret and pulsing dot do that job)". That was scoped to streaming
**inside** the run document. We add an explicit exception there:
`LoadingState` is the canonical page/panel-level loading visual, and
the streaming-internal "no spinners" rule still applies inside the
run document.

### Cache-bust

`?v=0083` → `?v=0084` across `index.html` so browsers pick up the
new `shared.jsx`, `run-list.jsx`, `app.jsx`, `run-detail.jsx`,
`compare.jsx`, and `design-language.jsx`.

## Out of scope

- **Skeleton screens** that mirror each surface's actual layout.
  Visually richer than a spinner but expensive to maintain. Future
  spec if needed.
- **A pulsing brand-mark variant** for very long loads. The friendly
  hint already telegraphs "we know this is slow, hang on"; the brand
  mark would be a different idea entirely.
- **Internationalising the "Just a moment, please." copy.** The app
  ships English-only today.
- **Server-side changes.** Pure frontend; spec 0081's snapshot cache
  is what actually shortens loads.

## Test plan

- [x] `uv run pytest` — 782 still pass (frontend-only changes; no
      backend touched).
- [ ] **`fly deploy`** from this branch.
- [ ] **Hard refresh.** Run list shows the new spinner + "Loading
      runs" + "Just a moment, please." while waiting; the same visual
      with "Loading run" + the run id appears on the run-detail
      page; the same visual with "Connecting to the server" appears
      at app boot if the auth handshake is slow.
- [ ] **Navigate detail → back to list**: the visual is the same as
      a cold mount (no inconsistency).
- [ ] **Modal-open inside a run**: clicking a timeline card shows
      the new inline-size spinner + "Loading input bundle…" instead
      of the old mono text.
- [ ] **Reduced motion**: with `prefers-reduced-motion: reduce`, the
      spinner is a static ring (no rotation) — covered by the
      existing universal rule in `base.css`.

## Risks

- **The "Just a moment, please." copy is heavy if loads are
  instant.** With spec 0081's snapshot cache and spec 0080's warm
  machines, hot loads finish in < 200 ms — the hint flashes
  unhelpfully. Acceptable: the hint matters most when the load is
  slow, which is exactly when the user is reading text. A short fade
  delay (hint hidden for the first 150 ms) is a future polish.
- **Touching `FullPageMessage` call sites means the error path is
  intentionally untouched**, so the error screens still have a back
  button. Reviewers should sanity-check that no error path
  accidentally renders `LoadingState`.
- **Rollback** is single-revert; the previous spinner from spec 0083
  remains intact under the hood, just unwrapped.

## Open questions

None.
