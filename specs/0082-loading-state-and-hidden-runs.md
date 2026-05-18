---
spec: 0082
title: Run-list loading state + server-side hidden-runs filter
label: bug
version-bump: PATCH
status: proposed
target-version: 0.69.6
created: 2026-05-18
pr: ""
---

# Spec 0082 — Loading state + hidden-runs filter

## Context

Two unrelated polish items rolled into one PR because they're both
small and both touch the run-list surface.

### Problem 1 — empty-state flash

Every page load briefly renders the "No runs" empty-state before the
first `/api/runs` fetch resolves. With a cold backend cache (spec
0081's first hit) plus the Amsterdam → iad round-trip the flash can
last seconds. The user reads "No runs" and assumes the page is broken
before the actual list pops in. The data-loading state needs its own
copy.

`useRunList` ([live-data.jsx:148](src/dual_research/ui/static/live-data.jsx:148))
currently exposes `{ rows, connected }`. The empty-state in
`RunListView` ([run-list.jsx:359](src/dual_research/ui/static/run-list.jsx:359))
renders "No runs" whenever `filtered.length === 0` regardless of
whether a fetch has even completed once.

### Problem 2 — too many stale runs on the list

The hosted UI currently lists a number of one-off test runs from the
spec-0019 → spec-0049 iterations (`prod-postgres-vs-sqlite`,
`live-integration-test`, `cache-multi-round`, etc.). They're no
longer useful for browsing — they were artefacts of integration
testing. The user wants them retired from the UI but kept in the
database (orchestrator artifacts, reconcile-costs history, future
diagnostics).

The user dictated 8 of these by their 4-char display id:

| Display id (sha1[:4]) | Run id                                              |
| --------------------- | --------------------------------------------------- |
| `bcd3`                | 20260516-023449-web-components-catalogue            |
| `db46`                | 20260515-171500-live-verify-webcomp-catalogue       |
| `70e3`                | 20260515-163105-live-integration-test               |
| `009f`                | 20260515-124552-cache-multi-round                   |
| `48b1`                | 20260515-122538-prod-cached-e2e                     |
| `76e1`                | 20260515-120623-prod-postgres-vs-sqlite             |
| `1ab9`                | 20260515-112634-p2-asyncio-vs-goroutines            |
| `38f9`                | 20260515-111151-asyncio-vs-goroutines               |

## Proposed change

### Change 1 — Loading state in `useRunList`

`useRunList` in [live-data.jsx](src/dual_research/ui/static/live-data.jsx)
adds a `loading` boolean. Initial `true`; flips to `false` in a
`.finally()` on the first fetch attempt (success **or** failure — once
we've heard back from the server, we know the empty state is
authoritative).

`ListScreen` in [app.jsx](src/dual_research/ui/static/app.jsx) passes
`loading` through to `RunListView` as a prop.

`RunListView` in [run-list.jsx](src/dual_research/ui/static/run-list.jsx)
accepts the prop; the empty-state branch becomes:

```jsx
{loading && !search
  ? 'Loading data…'
  : search
    ? `No runs matching "${search}"`
    : 'No runs'}
```

`search` still wins when the user has typed a query — that empty
state is informative regardless of fetch status.

### Change 2 — `HIDDEN_RUN_IDS` frozenset

`src/dual_research/ui/server.py` gains a module-level
`HIDDEN_RUN_IDS: frozenset[str]` with the 8 ids above. Three filter
points pick it up:

- **`_supabase_list_runs`** drops hidden rows immediately after the
  initial `select * from runs` and before the brief-join, so we don't
  even pay the second round-trip for filtered-out rows.
- **`_search_runs_supabase`** filters the candidate set before the
  brief-join for the same reason.
- **`_require_run_exists`** raises 404 if the id is in
  `HIDDEN_RUN_IDS`. Every per-run endpoint
  (`/api/runs/{id}`, `/stream`, `/inputs/*`, `/searches/*`,
  `/files/*`, `/attachments`, `/attachment-blobs/*`) calls
  `_require_run_exists`, so the choke-point is one function.

**Why a frozenset literal in code instead of a DB column.** The list
is small, edited by the maintainer, and changes infrequently. A
config knob is cheaper to add, review, and roll back than a schema
migration. If the list grows past ~30 entries or someone wants
non-engineers to toggle it from the UI, promote to a `runs.hidden_at`
column in a follow-up.

**fs-mode (`_make_app`) deliberately untouched.** This is a hosted-UI
concern; local dev wants to see everything in `runs/`.

### Cache-bust

`?v=0077` → `?v=0082` across `index.html` so browsers pick up the new
`live-data.jsx`, `app.jsx`, and `run-list.jsx`.

### Test plumbing

`tests/conftest.py` (new) autouse-fixture clears `HIDDEN_RUN_IDS` for
every test, since several pre-existing tests seed with run ids that
overlap the production hidden list. Tests that need to exercise the
hidden-runs behaviour monkeypatch it back to a specific set
(`tests/ui/test_server_hidden_runs.py`).

## Out of scope

- **Promoting `HIDDEN_RUN_IDS` to a database column.** Future spec
  once the maintenance cost of editing the frozenset becomes real.
- **An admin endpoint to hide/unhide runs from the UI.** Same reason.
- **Hiding hidden runs from `/api/reconcile/*`.** Cost reconciliation
  still needs to see every row that was actually pushed. The hidden
  list is a presentation filter, not a soft-delete.
- **Loading-state UX in `RunDetail` and other screens.** This spec
  targets the empty-state flash the user actually called out; other
  surfaces are a separate cleanup pass.
- **Frontend cache-busting for partial JSX edits.** We're using a
  single `?v=` query string across the bundle, same as PR #77;
  per-file content hashes would be cleaner but unrelated.

## Test plan

### Unit (shipped in this PR)

- [x] `tests/ui/test_server_hidden_runs.py::test_list_runs_excludes_hidden_ids`
- [x] `test_run_detail_returns_404_for_hidden_id`
- [x] `test_run_detail_returns_200_for_visible_id`
- [x] `test_search_excludes_hidden_ids`
- [x] `tests/conftest.py` clears `HIDDEN_RUN_IDS` for every other
      test — full suite green: **782 passed**.

### Manual (post-deploy)

- [ ] Open `https://dual-research-alex.fly.dev/` cold. Empty-state
      reads "Loading data…" until the fetch resolves. Once it
      resolves, the list either renders or shows "No runs" — but
      "No runs" never appears while data is in flight.
- [ ] The list contains the 4 expected runs (the two
      backend-language-choice rows, partner-vetting-arch-critique,
      full-e2e) and **none** of the 8 hidden ones.
- [ ] Direct navigation to
      `/#/runs/20260515-163105-live-integration-test` (a hidden id)
      404s end-to-end; the run-detail page shows "Could not load
      run · Error: HTTP 404".
- [ ] `/api/search?q=postgres` returns no results from
      `prod-postgres-vs-sqlite`.

## Risks

- **A wrong id ends up in `HIDDEN_RUN_IDS`.** Recovery is a one-line
  edit + redeploy; cost is bounded. Reviewers should double-check
  the 8 entries against the dictation list before merging.
- **Hidden-runs filter masks a bug.** A regression elsewhere that
  drops a run wouldn't be visible if the run was hidden. Acceptable
  — the hidden list is small and explicitly maintained.
- **`tests/conftest.py` accidentally suppresses production behaviour
  in a test that meant to exercise it.** Mitigated by always pairing
  the global default-empty fixture with a per-test
  `monkeypatch.setattr` in tests that *do* want the filter live.

## Open questions

- **Cache-Control on the run-list endpoint.** `/api/runs` is mutable
  (new runs land, hidden list changes), so we deliberately don't add
  an immutable header here. A short `max-age=2` could mask the cost
  of the 3s poll, but only if we're confident the list never
  surprises a viewer mid-edit. Not in this spec.
