---
spec: 0083
title: Robust run-list loading state + spinner visual + hide 5455
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.7
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/83"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0083 — Robust loading state + spinner + hide 5455

## Context

Three small follow-ups to spec 0082, which I rushed.

### 1. "No runs" still flashed on navigation back

Spec 0082 added a `loading` boolean to `useRunList` that flipped to
`false` in a `.finally()` — meaning it flipped on **error** too. When
the user navigated detail → list, the freshly-remounted hook fired a
request; if that very first request errored or was slow enough to
race with the unmount-cancel, `loading` could turn `false` while
`rows` was still `[]`, putting the UI in the "confirmed empty" branch
that renders "No runs". This was real, even with cached JS — the
user's screenshots show the flash clearly.

### 2. The empty visual was just plain text

The user explicitly asked for "a nice, clean visual in the middle,
basically saying something like 'waiting, content is loading', maybe
with some nice visual." Spec 0082 shipped plain text. This spec
upgrades it to a centered spinner + label.

### 3. One more retired run

The user identified `5455` (display id of `20260515-114303-full-e2e`)
as another test run that should drop off the UI. Missed in the spec
0082 dictation parse.

## Proposed change

### Change 1 — `useRunList` returns `loading: !hasLoaded`

Replace the spec 0082 `loading` state with `hasLoaded`. The hook only
flips `hasLoaded` to `true` on a **successful** response. On error we
do nothing — stale rows keep showing, the loading visual keeps
showing, the indicator dims via the existing `lastOk` path. The
returned value `loading: !hasLoaded` stays semantically the same to
callers ([live-data.jsx](src/dual_research/ui/static/live-data.jsx)).

This means:

- Cold mount → fetch in flight → `loading: true` → spinner visible.
- Fetch succeeds with `[]` → `hasLoaded: true`, `rows: []` →
  `loading: false`, "No runs" message (correct — server confirmed
  empty).
- Fetch fails → `hasLoaded` stays `false` → spinner stays. Next 3 s
  poll tick tries again.
- Subsequent fetches → if any one had succeeded already, stale rows
  keep showing through errors; `loading: false` so the empty-state
  branch shows "No runs" only when `rows.length === 0` and at least
  one fetch succeeded.

### Change 2 — Spinner visual in `base.css` + `run-list.jsx`

New `dr-spin` keyframe (one-line `transform: rotate(360deg)`) plus a
`.dr-spinner` class — a 28 px round element with a 2.5 px border whose
top is the brand accent colour. The empty-state branch in
`RunListView` switches on `loading && !search`:

```jsx
loading && !search ? (
  <div style={{
    padding: '60px 18px',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: 14,
    color: 'var(--fg-3)',
  }}>
    <div className="dr-spinner" aria-hidden="true" />
    <span style={{ fontSize: 13 }}>Loading runs…</span>
  </div>
) : (
  /* "No runs" or "No runs matching ..." */
)
```

Honours `prefers-reduced-motion` automatically — the existing
universal rule in `base.css:120` already sets
`animation-duration: 0.001ms !important` for all selectors when the
media query matches, so the spinner stops spinning for users who
have the system preference set without us needing to add a per-rule
override.

### Change 3 — Add `5455` to `HIDDEN_RUN_IDS`

One-line addition to the frozenset in
[server.py](src/dual_research/ui/server.py): `"20260515-114303-full-e2e"`.

### Cache-bust

`?v=0082` → `?v=0083` across `index.html` so browsers actually pick
up the new `live-data.jsx`, `run-list.jsx`, and `base.css`.

## Out of scope

- **Cross-route data persistence.** Right now every list-screen mount
  starts from `rows: []` and spins for one network round-trip even
  if the user just came back from a detail page. A real cache would
  surface the previous list instantly. Out of scope here — separate
  spec if the spinner-on-back UX still feels off after this.
- **Loading skeletons that match the list layout.** A nice-to-have;
  the spinner is the user's requested "nice visual" and it ships
  today.
- **Spinner accessibility beyond `aria-hidden`.** No live-region
  announcement; for a 200 ms warm load that would be more noise than
  signal.

## Test plan

- [x] `uv run pytest` — existing 782 still pass; no new tests needed
      (frontend-only visual changes; logic change in `useRunList`
      isn't unit-tested today and a smoke test would require a JSX
      test harness that isn't set up).
- [ ] **`fly deploy`** from this branch.
- [ ] **Cold load:** `https://dual-research-alex.fly.dev/` shows the
      centered spinner + "Loading runs…" until the first
      `/api/runs` response, then the list.
- [ ] **Navigate-back flash:** open the site, click into a run,
      click back. The empty-state during the brief moment of remount
      shows the spinner — **not** "No runs".
- [ ] **Hidden 5455:** `full-e2e` no longer appears in the run-list.
- [ ] **Direct nav to hidden:** `/#/runs/20260515-114303-full-e2e`
      returns 404 from `/api/runs/...`.
- [ ] **Reduced motion:** with `prefers-reduced-motion: reduce`, the
      spinner doesn't visibly spin (the universal rule kills the
      animation).

## Risks

- **`hasLoaded` stays `false` forever if every fetch fails.** That's
  the desired behaviour — better than promoting to "no runs"
  spuriously. The `connected` indicator already telegraphs the
  failure state, and the user can retry by refreshing.
- **Spinner CSS interferes with reduced-motion users.** Covered by
  the existing universal rule; manual verification listed above.
- **Cache-bust query gets stale faster.** Each spec we ship bumps it,
  same pattern as 0077/0082/0083 — known cost.

## Open questions

None.
