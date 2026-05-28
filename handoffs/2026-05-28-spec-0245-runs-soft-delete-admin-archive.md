---
spec: "0245"
date: 2026-05-28
version: "1.59.0"
pr: "https://github.com/Lexiz/dual-research/pull/281"
kind: post-deploy
---

# Spec 0245 — Soft-delete on runs + admin hover-archive

## What landed

Soft-delete on `public.runs` with an admin-only UI affordance — hover an active row as admin, click the archive icon button, confirm in the dialog, the row disappears from the live list and a success toast appears bottom-right. A new `Active | Archived` segmented toggle (admin-only, top-right of the list header) flips the polled URL to `/api/runs?archived=true`; archived rows render at 0.65 opacity with an `archived <relTime> · by <email>` caption and an unarchive button on hover.

**Server.** `POST /api/runs/{id}/archive` + symmetric `DELETE /api/runs/{id}/archive`, admin-gated via the existing `_require_admin` helper. 204 on success, 403 non-admin, 404 unknown, 409 already-archived / not-archived. The four reader sites switched from `runs` to the new `runs_active` view: `_supabase_list_runs` ([server.py:1018](src/dual_research/ui/server.py#L1018)), `_require_run_exists` ([server.py:1146](src/dual_research/ui/server.py#L1146)), `_search_runs_supabase` ([server.py:1794](src/dual_research/ui/server.py#L1794)), and `gather_supabase_totals` ([audit/reconcile.py:474](src/dual_research/audit/reconcile.py#L474)). The writer at [`persistence/remote.py:105`](src/dual_research/persistence/remote.py#L105) is unchanged (the view is read-only).

**DB.** Migration [`supabase/migrations/0007_runs_soft_delete.sql`](supabase/migrations/0007_runs_soft_delete.sql) added `deleted_at` + `deleted_by` to `public.runs`, a partial index on `deleted_at IS NOT NULL`, the `runs_active` view (`SELECT * FROM runs WHERE deleted_at IS NULL`, `security_invoker = true`), and RLS policies as defense-in-depth (`runs_select_active_or_admin`, `runs_update_admin_only`). Applied to Supabase project `qpdsxspdwqukircrfqkm` via the supabase MCP **before** the merge so the deploy.yml run picked up the schema cleanly; verified post-apply that `runs_active` returns all 29 rows (none archived yet) and the two new columns are present.

**DS primitive.** New `<Toast>` — `<ToastHost>` singleton mounted near the app root in [`app.jsx`](src/dual_research/ui/static/app.jsx), any surface dispatches via the `useToast()` hook (which fires a `window` `app-toast` CustomEvent the host listens for). Bottom-right anchored, `--md-shape-md` corners, `--md-elev-3`, `--md-surface-container-highest` background. Two tones: `ok` (tertiary-container) and `error` (error-container); default neutral. Auto-dismiss 4 s, click anywhere to dismiss, ESC dismisses most-recent, stacks newest-at-top, honours `prefers-reduced-motion`. CSS lives in both [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) (DS canonical) AND [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) (live app) per the CLAUDE.md DS sync rule. [`design-system/SPEC.md`](design-system/SPEC.md) §3 Primitives gained a Toast row. The bespoke `.tour-skip-toast` rule + `tour-skip-fadein` keyframe were retired in the same commit; the onboarding tour's skip notification now dispatches via the canonical toast event.

**Other primitive touch.** `Button` learned a `tone` prop — `<Button variant="filled" tone="error">` paints with `--md-error` / `--md-on-error` for destructive confirm actions (the archive dialog's confirm button is the first consumer).

## Verification

- **Local tests:** `uv run pytest tests/ -q` → **2342 passed in 32 s** (5 new spec-0245 source-pattern / endpoint test files, 1 existing reconcile test updated for the `runs_active` migration).
- **Local UI preview** via Claude Preview MCP (`http://127.0.0.1:6173/`) — app loads at v1.59.0, runs list renders all 38 local runs, no console errors, toast dispatch produces the right tones in the right positions (bottom-right, stacked). Admin-only affordances (archive button, Active/Archived toggle, archived-view dim) **are not exercisable in fs/local mode** (no Supabase auth context); they're guarded by source-pattern tests and the post-deploy live verification below.
- **Migration applied:** `mcp__supabase__apply_migration` to `qpdsxspdwqukircrfqkm` returned `{"success":true}` before the PR was opened; `information_schema` shows `deleted_at` + `deleted_by` present; `SELECT count(*) FROM runs_active` matches `SELECT count(*) FROM runs` at 29 rows.
- **GH Actions deploy** ([`deploy.yml` run](https://github.com/Lexiz/dual-research/actions/runs/26588461024)) completed in 39 s — flyctl deploy + sweep-stale-blues both green.
- **Live smoke:** `https://dual-research-alex.fly.dev/version-notes.json` returns 230 entries with `1.59.0` as the leading version, confirming the deploy is serving the new build.

## Tested scenarios (source-pattern + server)

- Archive button only renders inside `hover && isAdmin && !isArchived && !archivedView` (positive + exactly-one-render-site antipodal-absence guard).
- Active/Archived toggle only renders for admins (positive on `isAdmin && (<TabGroup variant="solid" ...>` plus per-option `setArchivedView` wiring).
- `.run-row--archived` class applied only when `run.deletedAt` is non-null; inline `opacity: 0.65` is forbidden (lives in CSS, not JSX).
- `.md-toast`, `.md-toast-host`, `.md-toast--tone-ok`, `.md-toast--tone-error` all present in BOTH `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css`.
- `.tour-skip-toast` CSS class + `tour-skip-fadein` keyframe + `className="tour-skip-toast"` JSX all gone.
- Server: 204 admin-archive, 403 non-admin-archive, 404 unknown-id, 409 already-archived, 204 admin-unarchive, 409 not-archived.
- Server: `runs_active` view excludes archived; `/api/runs` excludes archived for everyone; `/api/runs?archived=true` returns only archived for admin; non-admin `?archived=true` silently returns the active list; `/api/runs/{archived_id}` 404s for admin AND non-admin (admin recovery flows through the dedicated unarchive endpoint, not the detail surface).
- Reconcile: `gather_supabase_totals` queries `runs_active` (existing test updated).

## Followups noticed during implementation

None — the spec was scoped tightly and the §5 Out-of-scope list (no `reason` field, no retention cron, no soft-delete on `approved_emails`, no non-admin restore path, no generalisation of `HIDDEN_RUN_IDS`, no Postgres RPC) all stay deferred per the spec author's reasoning. The `<Toast>` primitive's bloated-migration risk that §7 flagged is not realised yet — only the tour's skip notification was migrated this cycle.

## Backstop

- If the live archive surface misbehaves under real admin auth (the dimension I couldn't test locally), recovery is just `UPDATE public.runs SET deleted_at = NULL, deleted_by = NULL WHERE id = '<id>';` via the supabase MCP or the Studio SQL editor — the data is preserved.
- The migration is idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE VIEW`, `DROP POLICY IF EXISTS` + `CREATE POLICY`); rerunning is safe.
- `HIDDEN_RUN_IDS` (spec 0082) still works — it filters the post-view list in Python, so it composes cleanly with the new view.
