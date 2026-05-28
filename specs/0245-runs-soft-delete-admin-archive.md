---
kind: dev
spec: "0245"
slug: runs-soft-delete-admin-archive
title: Soft-delete on runs + admin hover-archive on the runs list
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-28
queued_at: "2026-05-28T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Primary spec, not a carve-out — disposition required by template but ship is the only sensible value."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0245 — Soft-delete on runs + admin hover-archive on the runs list

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds a new admin-only action, a new DB column, a new server endpoint, and a new DS primitive (Toast). No contract regressions.
> **Evidence:** Supabase project `qpdsxspdwqukircrfqkm` (Postgres 17), `public.runs` row count 29 (verified 2026-05-28); `public.approved_emails.is_admin` already gates admin actions (see [server.py:401](src/dual_research/ui/server.py#L401)).

---

## 1. Context

Hard `DELETE` on `public.runs` cascades through `events`, `session_files`, `turn_prompt_pieces`, `attachment_blobs` and removes turn data irreversibly. There is no way to hide a single mis-recorded or noisy run from the live list at [`https://dual-research-alex.fly.dev/`](https://dual-research-alex.fly.dev/) short of dropping the row outright, and the existing escape valve — `HIDDEN_RUN_IDS` frozenset, edited in `server.py` — requires a code deploy per hidden id. Every other admin action on this surface (allowlist add / remove / promote-to-admin) routes through a server-side endpoint gated on `approved_emails.is_admin`; archiving is the only one of comparable destructive weight that has no UI affordance.

The list itself is rendered by `RunRow` in [run-list.jsx:413](src/dual_research/ui/static/run-list.jsx#L413), which already tracks per-row `hover` state via React `useState` (line 415) — the hover-reveal pattern slots in without a structural rewrite. The grid template (line 436) reserves a 32 px right-edge column for the chevron, and an archive-icon button sits naturally alongside it as a 9th column gated on `hover && isAdmin`. There is no canonical `<Toast>` primitive in the DS today — only the bespoke `.tour-skip-toast` at [components.css:4149](src/dual_research/ui/static/components.css#L4149) — so this spec formalises one, since post-archive feedback is the first transactional-toast use case the app has had.

## 2. Proposed change

### 2.1 — DB layer (one migration: `supabase/migrations/0007_runs_soft_delete.sql`)

```sql
ALTER TABLE public.runs
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS deleted_by TEXT NULL;

CREATE INDEX IF NOT EXISTS runs_deleted_at_idx
    ON public.runs (deleted_at)
    WHERE deleted_at IS NOT NULL;

CREATE OR REPLACE VIEW public.runs_active
    WITH (security_invoker = true)
AS SELECT * FROM public.runs WHERE deleted_at IS NULL;

-- RLS safety net (defense in depth — the server-side endpoint is the
-- canonical write path; RLS catches anyone who bypasses it).
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY runs_select_active_or_admin ON public.runs
    FOR SELECT
    USING (
        deleted_at IS NULL
        OR EXISTS (
            SELECT 1 FROM public.approved_emails
            WHERE email = auth.email() AND is_admin = true
        )
    );

CREATE POLICY runs_update_admin_only ON public.runs
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.approved_emails
            WHERE email = auth.email() AND is_admin = true
        )
    );
```

The view uses `security_invoker = true` (Postgres 15+) so RLS evaluates against the calling user, not the view definer. The partial index on `deleted_at IS NOT NULL` keeps the archived-list query fast even as archived count grows.

**No Postgres RPC** (`archive_run`) is added. The server-side endpoint in §2.2 is the canonical write path — it already runs with the service-role key, which bypasses RLS, so the RLS UPDATE policy exists purely as the safety net for any future caller that bypasses the server. Considered and rejected: an RPC adds a second admin-gate code path (Postgres function + server endpoint) that must stay in sync. Server-only is simpler.

### 2.2 — Server layer (`src/dual_research/ui/server.py`)

**New endpoint** `POST /api/runs/{run_id}/archive`. Mirrors the existing admin-gated endpoints (`list_approved_emails` at [server.py:414](src/dual_research/ui/server.py#L414), `add_approved_email` at [server.py:429](src/dual_research/ui/server.py#L429)): re-uses the same `require_admin(request)` helper, returns `403` for non-admins, `404` for unknown `run_id`, `409` if `deleted_at` is already non-null. On success: sets `deleted_at = now()`, `deleted_by = <email-from-jwt>`, returns `204`.

**Optional `DELETE /api/runs/{run_id}/archive`** for the same admin to unarchive — sets both columns back to NULL. Symmetric with the archive route, useful for "I clicked the wrong row" recovery without dropping to SQL.

**Reader migration — switch all four reader sites from `runs` to `runs_active`:**

- [server.py:1018](src/dual_research/ui/server.py#L1018) — `_supabase_list_runs` (the `/api/runs` list endpoint).
- [server.py:1146](src/dual_research/ui/server.py#L1146) — the existence check before `/api/runs/{id}` detail reads.
- [server.py:1794](src/dual_research/ui/server.py#L1794) — second list-reader path (search/index surface).
- [audit/reconcile.py:474](src/dual_research/audit/reconcile.py#L474) — daily reconcile job. Archived runs are excluded from reconcile by default since reconciling against an archived row is incorrect signal; if a future reconcile use case wants archived rows, pass an explicit flag.

**Writer untouched:** [persistence/remote.py:105](src/dual_research/persistence/remote.py#L105) (run upsert) continues to write `runs` directly — the view is read-only by definition.

**Admin toggle on the list endpoint.** `/api/runs` learns one optional query parameter, `archived` (default `false`). When `archived=true` AND the caller is admin, the endpoint queries `runs` with `WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC` instead of `runs_active`. Non-admin callers passing `archived=true` get the same default-active list as if they hadn't passed it (no error, no leak).

### 2.3 — UI layer (`src/dual_research/ui/static/run-list.jsx`)

**Archive icon button on `RunRow`.** Extend the grid template at [run-list.jsx:436](src/dual_research/ui/static/run-list.jsx#L436) from 8 columns to 9 by inserting `32px` immediately before the chevron column. Render an `.md-icon-btn` instance carrying an `<Icon.Archive />` glyph in that slot, with `aria-label="Archive run {displayId}"`. Visibility is gated on `hover && isAdmin && !run.deleted_at`:

```jsx
{hover && isAdmin && !run.deleted_at && (
  <button
    className="md-icon-btn"
    onClick={(e) => { e.stopPropagation(); setArchiveTarget(run); }}
    aria-label={`Archive run ${displayId}`}
  >
    <Icon.Archive />
  </button>
)}
```

Per DS SPEC.md §3 Primitives — "Icon button" — `.md-icon-btn` is the 40 × 40 dp circular icon-only action with state-layer overlay. The DS already governs hover-reveal: every card gains elevation-2 on hover (§4.1 — Critique pane). Reusing the row's existing `useState(hover)` keeps the JS path single-source.

**New `<Icon.Archive />` glyph** in [icons.jsx](src/dual_research/ui/static/icons.jsx) — Material `mdi:archive-outline` (24 × 24 dp, currentColor stroke). Lives next to the other Material glyphs in the same file.

**Confirmation dialog (`<ConfirmArchiveDialog>`).** Mounts when `archiveTarget` is non-null. Uses `<ModalDialog>` in Basic variant per DS SPEC.md §4.6 — `max-width: 560 px`, `--md-shape-xl` corners, elevation-3, ESC + scrim-click close, focus trap, body overflow lock. Anatomy:

- Title (`<h2>`): `Archive this run?`
- Body: `It will be hidden from the runs list. An admin can restore it via SQL.`
- Actions: `<Button variant="text">Cancel</Button>` + `<Button variant="filled" tone="error">Archive</Button>`. The error-toned filled button uses `--md-error` / `--md-on-error` per DS SPEC.md §2 Foundations colour tokens, matching the existing destructive-action pattern in the allowlist admin page.

On `Archive` click: POST to `/api/runs/{id}/archive`, on `204` close the dialog, remove the row from the local runs list (optimistic), show a success toast. On any non-204: show an error toast with the response body's `error` field if present, otherwise `"Could not archive run. Try again."`, and leave the row in place.

**Admin toggle in list header (`<RunListView>` header chrome).** A `<Tab variant="solid">`-style segmented control with two options — `Active` (default) and `Archived` — rendered admin-only, top-right of the list header. Selected state via `data-active="true"` per DS SPEC.md §4.1 lifted-tile contract. Selecting `Archived` re-fetches `/api/runs?archived=true`. Archived rows render with `opacity: 0.65` (CSS class `.run-row--archived`) and replace the chevron column with a small caption: `archived <relTime> · by {email}`. The archive icon button is not rendered on archived rows; an unarchive button (`<Icon.ArchiveUp />` — `mdi:archive-arrow-up-outline`) takes its place, opening the symmetric `<ConfirmUnarchiveDialog>`.

### 2.4 — New DS primitive: `<Toast>`

Lives in `src/dual_research/ui/static/shared.jsx` as `<ToastHost>` (singleton, mounted near app root) + `<Toast>` (one-shot, dispatched via a `useToast()` hook). CSS authoritative class `.md-toast` lands in **both** `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css` in the same commit, per CLAUDE.md DS sync rule.

Anatomy:
- Bottom-right anchored, 16 px gutter from viewport edges.
- `--md-shape-md` (12 dp) corners, `--md-elev-3`, `--md-surface-container-highest` background, `--md-on-surface` text.
- Two variants: `tone="ok"` (uses `--md-tertiary-container` background + `--md-on-tertiary-container`) and `tone="error"` (uses `--md-error-container` + `--md-on-error-container`). Default tone is neutral.
- Auto-dismiss after 4 s. Click anywhere on the toast to dismiss immediately. Keyboard ESC dismisses the most-recent toast.
- Stacks vertically when multiple toasts coexist (newest at top).
- Reduced-motion: skips the slide-in transform.

Replaces the bespoke `.tour-skip-toast` at [components.css:4149](src/dual_research/ui/static/components.css#L4149) — the tour rewrites its skip notification to use `useToast({ tone: 'ok', text: 'Skipped — element not found' })`. The legacy CSS class is removed in the same commit.

This is a deliberate DS extension; SPEC.md §3 Primitives gains a new row (`Toast`), and §4 Composed components gains nothing (Toast is atomic, not composed).

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As an `admin`, I want to archive a run that I know is noise (test run, mis-pushed, abandoned), so that it stops cluttering the runs list for myself and other viewers without me having to drop the DB row.

> As an `admin`, I want to toggle to an archived-only view of the runs list, so that I can verify what I've archived and recover from a mis-click without dropping to SQL.

> As a `viewer` (non-admin signed-in user), I want archived runs to be invisible by default, so that the list shows me only live, relevant runs.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** admin archives a run via hover
> GIVEN I am signed in as an admin AND I am viewing the runs list at `/#/` with the `Active` toggle selected
> WHEN I hover over a row whose `deleted_at` is null AND I click the archive icon button that appears in the row's right edge AND I click `Archive` in the confirmation dialog
> THEN the row disappears from the visible list AND a bottom-right toast appears reading `Run archived.` AND a subsequent reload of `/api/runs` does not return that run id

> **Scenario 2:** non-admin sees no archive affordance
> GIVEN I am signed in as a non-admin AND I am viewing the runs list
> WHEN I hover over any row
> THEN no archive icon button is rendered (verify by DOM: no `button.md-icon-btn[aria-label^="Archive run "]` exists inside any `[data-tour-anchor="run-row"]`)

> **Scenario 3:** admin toggles to archived view
> GIVEN I am signed in as an admin AND I have previously archived at least one run
> WHEN I click the `Archived` segment in the list header
> THEN the list re-fetches `/api/runs?archived=true` AND each visible row renders with `opacity: 0.65` AND the chevron is replaced by a `archived <time> · by <email>` caption AND a `mdi:archive-arrow-up-outline` button is reachable on hover

### 3.3 — Hover-reveal accessibility

The archive icon button must be reachable by keyboard for admins: pressing Tab while focus is on the row reveals the button (via `:focus-within` on the row) AND moves focus to the button. This mirrors the spec 0204 §2.2 keyboard-parity contract for inline-expand vs. modal-open. Screen readers announce the button as `Archive run <displayId>`; the row label remains unchanged.

## 4. Data / Schema deltas

| Object | Change | Reason |
|---|---|---|
| `public.runs` | `+ deleted_at TIMESTAMPTZ NULL`, `+ deleted_by TEXT NULL` | Soft-delete marker + audit trail. |
| `public.runs` | Partial index on `deleted_at IS NOT NULL` | Keep archived-list query cheap as archived count grows. |
| `public.runs_active` | NEW view: `SELECT * FROM runs WHERE deleted_at IS NULL`, `security_invoker = true` | Default reader surface — drops the WHERE clause from every caller. |
| `public.runs` | RLS enabled, `runs_select_active_or_admin` policy, `runs_update_admin_only` policy | Defense in depth — the server-side endpoint is canonical, RLS catches bypass. |
| `events` / `session_files` / `turn_prompt_pieces` / `attachment_blobs` | No schema change | Children remain reachable via direct `run_id` query; UI surfaces them only after first hitting `runs_active` to resolve the parent, so soft-deleting a run hides its children transitively. |

**No backfill required:** existing 29 rows get NULL `deleted_at` (the default), which is the "active" state. Migration is idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE VIEW`).

## 5. Out of scope

- **`reason` free-text field on archive.** Deferred — no caller has asked for an audit reason; adding the column now means committing to "we audit archive reasons" with half-populated data we can't trust. Deferred to a follow-up spec to be drafted when the first "why was this archived?" question arrives in practice.
- **Hard-delete retention cron** (e.g. `delete runs where deleted_at < now() - interval '90 days'`). Deferred — the immediate need is to hide noise, not to free storage. Trigger condition for landing the follow-up: Supabase `attachment_blobs` storage exceeds 10 GB OR a compliance ask names a retention ceiling. Will spec separately.
- **Soft-delete on other tables.** `approved_emails` is the obvious next candidate but the semantic is "revoke access" not "archive history" — different invariants (a revoked admin must immediately lose the ability to archive, which a `deleted_at` column doesn't model cleanly). Deferred indefinitely; revisit only if a concrete need emerges.
- **Restore-via-UI on a non-admin path.** Recovery from a mis-click is handled by the symmetric `DELETE /api/runs/{id}/archive` admin endpoint plus the archived-view toggle. Non-admins have no restore path; this is intentional — archive is reversible-by-admin, not reversible-by-anyone.
- **Generalising `HIDDEN_RUN_IDS` into the soft-delete mechanism.** The existing frozenset stays as-is for now; folding it into `deleted_at` would require a one-time backfill commit by an admin and changes the audit semantics (those runs were never "deleted_by" anyone). Deferred carve-out, low priority.
- **A Postgres RPC `archive_run()`.** Considered (it would be the canonical write path if the UI talked directly to Supabase via JS client), rejected: the UI talks to `/api/runs/*` Python endpoints today, so the admin gate lives there, and RLS on UPDATE is the defense-in-depth layer. Adding the RPC would create two admin-gate code paths to keep in sync.

## 6. Test plan

DB / server layer (pytest):

- [ ] `tests/test_spec_0245_archive_endpoint.py::test_archive_run_admin_204` — admin POST to `/api/runs/{id}/archive` returns 204 and sets `deleted_at` / `deleted_by` on the row.
- [ ] `tests/test_spec_0245_archive_endpoint.py::test_archive_run_non_admin_403` — non-admin POST returns 403 and row is unchanged.
- [ ] `tests/test_spec_0245_archive_endpoint.py::test_archive_run_unknown_id_404` — unknown `run_id` returns 404.
- [ ] `tests/test_spec_0245_archive_endpoint.py::test_archive_run_already_archived_409` — second archive on the same row returns 409.
- [ ] `tests/test_spec_0245_archive_endpoint.py::test_unarchive_run_admin_204` — admin DELETE clears `deleted_at` / `deleted_by`.
- [ ] `tests/test_spec_0245_runs_active_view.py::test_runs_active_view_excludes_archived` — soft-deleting a row removes it from `runs_active` SELECT.
- [ ] `tests/test_spec_0245_runs_active_view.py::test_list_runs_endpoint_uses_view` — `/api/runs` (default) does not return archived ids; `/api/runs?archived=true` as admin does.
- [ ] `tests/test_spec_0245_runs_active_view.py::test_archived_query_param_non_admin_ignored` — non-admin calling `/api/runs?archived=true` still gets the active list (no leak, no error).
- [ ] `tests/test_spec_0245_runs_active_view.py::test_run_detail_404_on_archived` — `/api/runs/{archived_id}` returns 404 for non-admin.

UI source-pattern tests (per spec 0206 doctrine, via `tests/_ui_pattern_helpers.py`):

- [ ] `tests/test_spec_0245_run_row_archive_button.py::test_archive_button_renders_inside_run_row` — positive regex match for the `.md-icon-btn` JSX inside `RunRow` gated on `hover && isAdmin && !run.deleted_at`.
- [ ] `tests/test_spec_0245_run_row_archive_button.py::test_pre_fix_anatomy_absent` — antipodal-absence regex: no archive button rendered ungated.
- [ ] `tests/test_spec_0245_archived_view.py::test_archived_view_toggle_renders_admin_only` — positive regex for the `Active | Archived` segmented control gated on `isAdmin`.
- [ ] `tests/test_spec_0245_archived_view.py::test_archived_row_has_dimmed_opacity_class` — positive regex for `.run-row--archived` CSS class application.
- [ ] `tests/test_spec_0245_toast_primitive.py::test_toast_class_in_both_css_files` — `.md-toast` definition present in both `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css` (CLAUDE.md sync rule).
- [ ] `tests/test_spec_0245_toast_primitive.py::test_legacy_tour_skip_toast_removed` — antipodal-absence: `.tour-skip-toast` CSS class is gone; `useToast` is the only path.

PR-description verification proof (Claude Preview MCP screenshots, plus reduced-motion check):

- [ ] (a) Active runs list, no row hovered — admin signed in. Archive button NOT visible.
- [ ] (b) Active runs list, one row hovered. Archive button visible in right edge.
- [ ] (c) Confirmation dialog open after clicking archive button.
- [ ] (d) Post-archive: row removed from list + success toast visible bottom-right.
- [ ] (e) Archived-view toggle clicked: list re-rendered with dimmed rows + captions.
- [ ] (f) Same row in (b) as a non-admin sign-in — archive button NOT visible.
- [ ] (g) Reduced-motion: toast appears without slide transform (verified by emulating `prefers-reduced-motion: reduce` in DevTools).
- [ ] (h) Error path: archive endpoint returns 500 once → error toast appears, row stays in list.

Per spec 0179, the spec 0245 surface (`RunRow`) is NOT an `ItemCard` instance, so the 8-capture parity grid does not apply. This is called out explicitly so the reviewer doesn't expect it.

## 7. Risks

- **RLS misconfiguration leaking archived rows.** The view uses `security_invoker = true`; the SELECT policy makes admins see archived. The risk is a missed reader site that bypasses the view and queries `runs` directly without the admin check — RLS catches non-admin browsers but the service-role server endpoints bypass RLS by design. Mitigation: the test plan asserts `/api/runs` returns no archived ids for non-admin; reviewer is asked to grep for `table("runs")` in the same PR to confirm migration completeness.
- **Optimistic UI race.** If archive succeeds server-side but the response is lost, the row is removed from the local list and the next refresh would show it still active. Mitigation: on toast click or on next interval refresh, re-fetch `/api/runs` and reconcile; an archived row reappearing is recoverable (admin clicks archive again, idempotent at the row level because we 409 on double-archive — adjust the optimistic path to also tolerate 409 as "already archived, ok").
- **Toast primitive scope creep.** Introducing `<Toast>` invites every existing inline-error path to migrate. The spec is scoped to the archive surface plus the tour-skip migration; other surfaces stay as-is and migrate piecemeal. If reviewer flags toast surface bloat, the migration scope is the line.
- **DS reference baseline.** This spec does NOT touch ItemCard, but it does touch `run-list.jsx` (which is NOT in the spec 0179 / 0205.1 baseline). No PNG refresh required. The `run-row--archived` class and new toast primitive are net-new DS surfaces — if a future spec changes their anatomy, that spec will own the parity proof.
- **Migration ordering.** The migration file (`0007_runs_soft_delete.sql`) MUST apply before the server-code change deploys — the new endpoint references columns and the view that don't exist yet. Fly deploy serializes through GH Actions, but the migration is run by Supabase apply, not by the deploy itself. Mitigation: spec the PR description to include the explicit `mcp__supabase__apply_migration` call as a pre-merge step, with the migration text inline.
