---
spec: 0124
title: Onboarding tour visual rewrite + unified Admin/Settings + server-persisted onboarding state
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.6.0
created: 2026-05-20
pr: ""
---

# Spec 0124 — Onboarding tour visual rewrite + unified Admin/Settings + server-persisted onboarding state

> Ship bucket: **Auth/admin + onboarding overhaul — full-stack.**
> Depends on: **0020** (Google OAuth), **0021/0022** (admin allowlist + Settings UI), **0103** (onboarding tour + ProgressSegs admin).
> Complexity: **L** — full-stack (Supabase schema + new endpoints + admin UI rewrite + onboarding visual rewrite). Three deliverables in one PR.
> Targeted version bump: **MINOR (1.5.x → 1.6.0)** — significant new admin functionality + persisted onboarding state + onboarding UX overhaul.

---

## 1. Context

A live audit on **v1.5.2** (https://dual-research-alex.fly.dev/, signed in as `alex.lisitzky@gmail.com` admin, zero runs in the list) found three large, related problems:

### 1.1 — The onboarding tour visuals don't match what a "guided tour" should look like

Walking all 8 steps revealed:

- **No spotlight or mask cutout.** The `.tour-overlay__mask` (`components.css:2664-2731`) renders as a uniform 55%-opacity black overlay across the entire viewport on every step. On spotlight steps (2, 3, 5, 6, 7) the design intends a `clip-path: polygon(…)` cutout around the anchor rect; the cutout layer (`.tour-overlay__cutout`) renders only when `anchorRect` is non-null, but the underlying mask never gets the cutout applied — so even when the spotlight code runs correctly the user sees a fully-dimmed page with no visual focus on any element. **There's no gradient, no halo, no leader line.** The card is just dropped on top of a uniform dim.
- **No visual hierarchy on the callout.** Card has a soft shadow but no elevation lift, no agent-tinted border, no arrow pointing at the anchor.
- **Cards don't position relative to anchors.** When the run-list has zero rows (the universal new-user state), `[data-tour-anchor="run-row"]` does not exist, the 500 ms retry in `onboarding.jsx:68-77` times out, `anchorRect` stays `null`, the callout falls back to viewport-centre. The user is shown a card saying *"Each row carries the run ID, topic, current phase…"* with **nothing to point at**.
- **The tour doesn't navigate between routes.** Step 3 ("the run header") and step 5 ("the timeline rail") describe surfaces that only exist at `/runs/<id>`. The tour stays on `/` the whole time. The user reads the text against a dimmed-out empty run list.
- **5 of 8 steps are useless for new users.** Steps 2, 3, 5, 6, 7 all depend on either a run-row or a run-detail page being mounted. Brand-new users (the exact people the tour is for) cannot satisfy either condition. The remaining 3 steps (1, 4, 8) are modal-shape and work, but on their own they're three blocks of prose — not a tour.
- **Stale phase vocabulary.** Step 4's `PHASES_SVG` and step 5's body text still call the phases `Preflight / Independent Research / Plan Negotiation / Drafting / Review Loop` — pre-0114 wording. Same vocabulary I fixed in the How-It-Works overlay in spec 0121.

### 1.2 — Two separate admin items in the avatar menu that should be one

The avatar menu (`app.jsx:441-457`) renders for admins:

- **Admin: users** → `/admin/users` → `AdminUsers` component
- **Settings** → `/settings` → `SettingsScreen` component

These are **two routes, two pages, two component files** (`admin-users.jsx` + `settings.jsx`) that overlap conceptually. Both surfaces are admin-only. Both describe state belonging to "users in the allowlist." They should be one Settings surface with sub-views, the same way Compare and Search are two views inside one chrome bar.

### 1.3 — The admin Users page is a permanent stub

`/admin/users` (the `AdminUsers` component, `admin-users.jsx:10-55`) renders **the current user only**, with their `dr_onboarded` / `dr_tour_step` derived from **their own browser's `localStorage`**. The page itself notes the limitation: *"Showing current user only. Multi-user admin list requires a backend endpoint."* (admin-users.jsx:51)

The required backend doesn't exist:

- No `/api/users` (no list endpoint).
- No `/api/users/<email>/reset-onboarding`.
- No `/api/onboarding/*`.
- The `approved_emails` Supabase table has `{email, is_admin, added_at}` — no onboarding state column.
- Onboarding state lives in **per-browser localStorage only**. An admin has no way to see who completed onboarding, who's stuck, who hasn't started.

**Admin requirements from the user (verbatim):**

> *"There should be a table. You should be able to: select users, see who did the onboarding, re-trigger the onboarding for them, allow the onboarding to be across the whole website or just for specific users. There's a lot of functionality in there."*

This needs the onboarding state moved to the server.

---

## 2. Goals

1. **Onboarding tour visual rewrite.** Add a real spotlight cutout (clip-path on the mask), a soft gradient halo around the cutout, a card elevation lift with an arrow pointing at the anchor, and proper anchor-aware positioning (reuses the overflow-aware positioner from spec 0121 § 20).
2. **Anchor-robust tour flow.** When an anchor doesn't exist after the retry window, the step is **skipped** with a small toast in the corner (`"step N skipped: no <anchor> on this page"`), not silently centered. Cross-route steps (3, 5, 6, 7) navigate to a fixture/demo run on entry, then back to `/` at the end.
3. **Tour vocabulary refresh.** Step 4 `PHASES_SVG` and step 5 body text replaced with the spec-0114 phase model (Phase 0 Input / Phase 1 Research plan / Phase 2 Negotiate plan / Phase 3 Draft / Phase 4 Review draft / Finalize). Possibly reuse the spec-0121 `01-pipeline.{light,dark}.svg` instead of the inline `PHASES_SVG`.
4. **Unified Admin/Settings.** Single route at `/settings` with two sub-tabs: **Allowlist** (current Settings) + **Users** (rebuilt from the Admin: users stub into a real multi-user table). `/admin/users` redirects to `/settings#users`. The avatar menu drops the "Admin: users" item; only "Settings" remains.
5. **Server-persisted onboarding state.** Each row in `approved_emails` gains `onboarded_at TIMESTAMPTZ NULL`, `tour_step SMALLINT NOT NULL DEFAULT 1`, `tour_force_reset_at TIMESTAMPTZ NULL`. New endpoints: `GET /api/users`, `POST /api/users/<email>/reset-onboarding`, `POST /api/onboarding/broadcast-reset`, `GET /api/onboarding/state`, `PUT /api/onboarding/state`. Client reads/writes through these instead of localStorage.
6. **Per-user + global re-trigger.** Admins can re-trigger onboarding for one user or for everyone. The next time that user loads the app, the tour auto-opens.
7. **Backward-compat for localStorage.** Existing `dr_onboarded` / `dr_tour_step` are read once at first load and migrated to the server. After migration, the server is the source of truth.

## 3. Non-goals

- **No new onboarding content.** Same 8 conceptual steps, same titles. The phase-vocabulary refresh in step 4/5 is a fix, not a rewrite.
- **No demo-run authoring.** The fixture/demo run that the tour navigates to is the most-recent end-to-end fixture in `runs/`. If none exists, the cross-route steps skip with a toast.
- **No admin role hierarchy.** Same flat "admin / member" model from spec 0021.
- **No invite emails.** Adding a user to the allowlist is unchanged: admin enters an email, user must sign in with that Google account.
- **No `/api/admin/*` namespace.** New endpoints live under `/api/users` and `/api/onboarding` to stay flat with existing conventions (`/api/me`, `/api/approved-emails`, `/api/runs`).
- **No analytics dashboard.** Onboarding completion is shown per user in the table, not aggregated.
- **No onboarding for non-tour surfaces** (no tour anchors on Settings, Admin, How-It-Works, Compare, Search).

---

## 4. Current-state audit (verbatim from the live site, v1.5.2)

### 4.1 — Avatar menu (admin user)

```
Alex Lisitzky · alex.lisitzky@gmail.com [admin]
─────────────────────────────────────
🎨 Design language
❓ Replay tour
≡  Admin: users
⚙  Settings
─────────────────────────────────────
↩  Sign out
```

### 4.2 — `/admin/users` (the `AdminUsers` stub)

Renders a heading `Users`, then **one row** with the current user's email + an 8-segment progress track + a `COMPLETED` badge. Below: italic note *"Showing current user only. Multi-user admin list requires a backend endpoint."*

No selection, no actions, no filters, no other users visible.

### 4.3 — `/settings` (the `SettingsScreen`)

Renders `Email allowlist` heading + a 6-row table (5 members + 1 admin = `you`) + a row at the bottom to add a new email with an Admin checkbox. Each row has a `Remove` button (or `(you)` for the current admin). Functional CRUD.

### 4.4 — Onboarding tour, walked end-to-end with zero runs

| Step | Type | Shipped behaviour | Issue |
|---|---|---|---|
| 1 | Modal | Centered card "Welcome to dual-research". Flat dim. | No card elevation, no visual polish. |
| 2 | Spotlight on `run-row` | `anchorRect = null` (no runs). Card centered. Flat dim. | No spotlight, no skip, no acknowledgement that the anchor's missing. Card describes a row that isn't visible. |
| 3 | Spotlight on `run-detail-header` (route `/runs/<id>`) | Card centered. Page still on `/`. | Tour didn't navigate; describes a surface the user can't see. |
| 4 | Modal "How the five phases work" with inline `PHASES_SVG` | Wider centered card with the SVG. Functional. | **Stale phase vocabulary** (pre-0114 names: Preflight / Independent Research / Plan Negotiation / Drafting / Review Loop). |
| 5 | Spotlight on `timeline-phase-rail` | Card centered. | Same as step 3 — no navigation, no anchor, no spotlight. Body text uses stale phase vocab. |
| 6 | Spotlight on `critique-pane` | Card centered. | Same. |
| 7 | Spotlight on `consumption-card` | Card centered. | Same. |
| 8 | Modal "You're all set" | Centered card with the closing message + `?reset_onboarding=1` hint. | Functional. Mentions a query param the average user will never type. |

**Effective tour quality for a new user with zero runs: 3 of 8 steps render meaningfully (1, 4, 8).** The other 5 are floating cards describing things that aren't on screen.

---

## 5. Proposed change — the onboarding tour

### 5.1 — Real spotlight + halo + card lift

Replace the flat `.tour-overlay__mask` with a stacked SVG-based spotlight:

```jsx
function TourSpotlight({ rect, padding = 12 }) {
  // rect = { top, left, width, height } from anchor element's getBoundingClientRect()
  // padding adds a small breathing space around the anchor.
  const x = rect.left - padding;
  const y = rect.top - padding;
  const w = rect.width + padding * 2;
  const h = rect.height + padding * 2;
  return (
    <svg className="tour-spotlight" aria-hidden="true">
      <defs>
        <mask id="tour-cutout">
          <rect width="100%" height="100%" fill="white" />
          <rect x={x} y={y} width={w} height={h} rx="12" fill="black" />
        </mask>
        <radialGradient id="tour-halo" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="var(--info)" stopOpacity="0.0" />
          <stop offset="80%"  stopColor="var(--info)" stopOpacity="0.0" />
          <stop offset="100%" stopColor="var(--info)" stopOpacity="0.35" />
        </radialGradient>
      </defs>
      {/* Dim layer with cutout */}
      <rect width="100%" height="100%" fill="var(--bg-0)" fillOpacity="0.72" mask="url(#tour-cutout)" />
      {/* Halo ring around the spotlight */}
      <rect x={x - 6} y={y - 6} width={w + 12} height={h + 12} rx="14"
            fill="none" stroke="url(#tour-halo)" strokeWidth="3" />
      {/* Outline ring at the cutout edge for crisp definition */}
      <rect x={x} y={y} width={w} height={h} rx="12"
            fill="none" stroke="var(--info)" strokeWidth="1.5" opacity="0.6" />
    </svg>
  );
}
```

Notes:
- One SVG, fixed-positioned, covers the whole viewport (`position: fixed; inset: 0; pointer-events: none;`).
- The mask cuts a rounded-rectangle hole around the anchor.
- The halo is a thin gradient ring at the cutout's outer edge — gives the spotlight a "glow" rather than a hard edge.
- Theme-aware: `var(--bg-0)` for the dim color + `var(--info)` for the highlight.
- For modal-shape steps (no anchor), `<TourSpotlight>` is not rendered — just a plain `.tour-modal-scrim` overlay (no cutout).

### 5.2 — Card elevation + arrow pointing at the anchor

`.tour-callout` gains:

- `box-shadow: var(--e-2)` (M3 elevation level 2 — significantly higher than current).
- `border: 1px solid var(--info-border)` to tie back to the halo color.
- A `::before` triangle arrow pointing at the anchor (CSS triangle via `border` trick). Direction (top/right/bottom/left) computed from card placement vs anchor; the arrow shares the card's background + border color.

Card placement uses the overflow-aware positioner from spec 0121 § 20 (already shipped in `onboarding.jsx`).

### 5.3 — Skip-on-missing-anchor + on-screen toast

In `onboarding.jsx:68-77`, after the 500 ms retry fails, the current behaviour is "leave `anchorRect=null` and render the card centered." Replace with:

```js
if (!anchorRect && stepDef.type === 'spotlight') {
  // No anchor on this page → skip the step.
  setSkipToast({
    text: `Step ${stepDef.id} skipped — no "${stepDef.anchor}" on this page.`,
    detail: stepDef.title,
  });
  setTimeout(() => onAdvance(), 600);  // brief flash so user sees the toast
  return;
}
```

`SkipToast` is a small bottom-right corner toast (`.tour-skip-toast`) with auto-fade after 2 s.

### 5.4 — Cross-route navigation for steps 3, 5, 6, 7

Step entries get an optional `route` field with destination + arrival hook:

```js
{
  id: 3, type: 'spotlight', anchor: 'run-detail-header',
  route: { view: 'detail', resolve: (run) => `/runs/${run.id}` },
  // …
}
```

On step enter, the tour:

1. Picks the **most-recent end-to-end run** from `/api/runs?limit=1` (or the demo-run fixture if no real runs exist).
2. If a run is found, calls `navigate('detail', run.id)` and waits for the route to mount (max 2 s).
3. Re-queries the anchor selector.

If no run exists at all (the universal new-user case), the cross-route steps **collapse into a single placeholder step** between step 4 and step 8:

> **Step 5 (collapsed) — Start your first run to see the rest.**
> *"Three more screens — the timeline, the critique pane, the consumption card — only exist inside a run. Start a run from the CLI (`dual-research --brief "your topic"`) and replay this tour from the avatar menu to see them."*

For users who do have runs, the 8-step flow runs as designed.

### 5.5 — Phase vocabulary refresh (step 4 + step 5)

- Step 4's `PHASES_SVG`: regenerate using the spec-0114 vocabulary, **or** reuse `/diagrams/how-it-works/01-pipeline.{light,dark}.svg` from spec 0121 with theme-aware swap (simpler, already shipped).
- Step 5's body text: rewrite to use the new phase names. *"Segments light up as the run progresses through input, research plan, negotiation, drafting, and review."*

### 5.6 — Replace `?reset_onboarding=1` reference

Step 8's body mentions `?reset_onboarding=1` — change to *"You can re-open this tour any time from the avatar menu → Replay tour."* (The URL flag stays as a dev escape hatch but isn't mentioned in user-facing copy.)

---

## 6. Proposed change — unified Admin/Settings surface

### 6.1 — Route consolidation

- `/admin/users` → **removed**. Server-side / client-side redirect to `/settings#users`.
- `/settings` becomes the canonical surface with two sub-tabs:

```
Settings
─────────────────────────────
[Allowlist]   [Users]
─────────────────────────────
<table or content for the active tab>
```

Sub-tab state lives in URL hash (`#allowlist` / `#users`). Default is `#allowlist`.

### 6.2 — Avatar menu cleanup

Drop the "Admin: users" item. Admin menu becomes:

```
Design language
Replay tour
─────────────
Settings           ← the only admin entry point
─────────────
Sign out
```

The "admin" pill stays next to the email; "Settings" is the entry to all admin functionality.

### 6.3 — Allowlist sub-tab (existing Settings content)

Unchanged from current `SettingsScreen`'s allowlist table. Just moved inside the sub-tab.

### 6.4 — Users sub-tab (new — replaces `AdminUsers` stub entirely)

New table layout:

| ☐ | Email | Role | Onboarding | Last seen | Actions |
|---|---|---|---|---|---|
| ☐ | `alice@trimble.com` | member | ✓ completed · v1.5.2 · 3d ago | 2026-05-18 14:32 | [Reset onboarding] [Remove] |
| ☐ | `bob@trimble.com` | member | in progress · step 5 / 8 | 2026-05-19 09:01 | [Reset onboarding] [Remove] |
| ☐ | `carol@trimble.com` | member | ⊘ not started | 2026-05-20 08:15 | [Reset onboarding] [Remove] |
| ☐ | `alex.lisitzky@gmail.com` | **admin** | ✓ completed · v1.5.0 · 5d ago | now | [Reset onboarding] *(you)* |

**Columns:**

- **Checkbox** — multi-select for bulk actions.
- **Email** — same as Allowlist tab.
- **Role** — same.
- **Onboarding** — derived from server state (see § 7.3):
  - `not started` — `onboarded_at IS NULL AND tour_step = 1`
  - `in progress · step N / 8` — `onboarded_at IS NULL AND tour_step > 1`
  - `✓ completed · v<version> · <relative>` — `onboarded_at IS NOT NULL`
  - For completed: also show the app version at which they finished (so you can see who completed before a major UX change).
- **Last seen** — `users.last_seen_at` updated on every `/api/me` call. Relative if < 7 days, absolute date otherwise.
- **Actions** — per-row buttons:
  - **Reset onboarding** — calls `POST /api/users/<email>/reset-onboarding`. Server sets `tour_force_reset_at = now()`. Confirm dialog: *"Re-trigger onboarding for <email>? They'll see step 1 on next page load."*
  - **Remove** — same as Allowlist tab's Remove button. (Self-remove and last-admin-remove are blocked server-side per spec 0021.)

**Bulk actions** (above the table, when ≥ 1 row checked):

- **Reset onboarding (N)** — bulk reset.
- **Remove (N)** — bulk remove. Confirm dialog.

**Global controls** (above the table, always visible):

```
Global onboarding
  [✓] Required for all new sign-ins  ← toggle: persist as a system flag
  [ Reset for everyone ]              ← button: confirm, then POST /api/onboarding/broadcast-reset
```

The "Required for all new sign-ins" toggle is a system-wide flag (`system_settings.onboarding_required`). When off, users can dismiss the tour and never see it again (current behaviour). When on, even users who completed it once will see it again if `tour_force_reset_at > onboarded_at`.

**Empty state:** if no users beyond yourself, the table shows a single row + an info note. No fake "Multi-user requires a backend endpoint" — by spec 0124 the backend exists.

### 6.5 — Filter + search above the table

A single search input filters across email + role + onboarding status. Filter chips for `[All N]` `[Admins N]` `[Pending N]` `[Completed N]`.

---

## 7. Proposed change — server-persisted onboarding state

### 7.1 — Supabase schema migration

```sql
-- Migration: add onboarding state to approved_emails
ALTER TABLE approved_emails
  ADD COLUMN onboarded_at        TIMESTAMPTZ NULL,
  ADD COLUMN onboarded_at_version TEXT NULL,
  ADD COLUMN tour_step            SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN tour_force_reset_at  TIMESTAMPTZ NULL,
  ADD COLUMN last_seen_at         TIMESTAMPTZ NULL;

-- System-wide settings (key/value store, single-row enforced via constraint)
CREATE TABLE IF NOT EXISTS system_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  onboarding_required BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NULL
);
INSERT INTO system_settings (id, onboarding_required) VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;
```

`onboarded_at_version` captures the app version at completion time so the admin table can show "completed on v1.5.0" — useful for spotting users who'd benefit from a re-trigger after a UX-changing release.

### 7.2 — Endpoints (new)

| Method | Path | Body / params | Auth | Returns |
|---|---|---|---|---|
| `GET` | `/api/users` | — | admin | `[{ email, isAdmin, onboardedAt, onboardedAtVersion, tourStep, tourForceResetAt, lastSeenAt, addedAt }]` |
| `POST` | `/api/users/<email>/reset-onboarding` | — | admin | `{ ok: true, tourForceResetAt }` |
| `POST` | `/api/users/bulk-reset-onboarding` | `{ emails: [...] }` | admin | `{ ok: true, reset: N }` |
| `GET` | `/api/onboarding/state` | — | authed | `{ tourStep, onboardedAt, mustRestart: bool }` |
| `PUT` | `/api/onboarding/state` | `{ tourStep, onboardedAt? }` | authed (own only) | `{ ok: true }` |
| `POST` | `/api/onboarding/broadcast-reset` | — | admin | `{ ok: true, reset: N }` |
| `GET` | `/api/system-settings` | — | authed | `{ onboardingRequired: bool }` |
| `PUT` | `/api/system-settings` | `{ onboardingRequired: bool }` | admin | `{ ok: true }` |

`mustRestart` is computed server-side: `tour_force_reset_at IS NOT NULL AND (onboarded_at IS NULL OR tour_force_reset_at > onboarded_at)`.

### 7.3 — Client integration

`onboarding.jsx`:

- On boot, call `GET /api/onboarding/state`. If `mustRestart === true`, force-open the tour at step 1. Otherwise honor server state.
- On every step advance, call `PUT /api/onboarding/state` with `{ tourStep }`. Debounced 300 ms.
- On Done / Skip, call `PUT /api/onboarding/state` with `{ tourStep, onboardedAt: new Date().toISOString() }`.
- On first boot (server response shows `tourStep = 1, onboardedAt = null`), check legacy localStorage flags. If `dr_onboarded === 'true'`, immediately PUT `onboardedAt = now()` to migrate. Then clear localStorage. Migration runs once per user.

`app.jsx`:

- Existing `useMe()` hook gains a parallel `useOnboardingState()` hook.
- `useMe()` itself triggers a server-side `UPDATE approved_emails SET last_seen_at = now()` on every `GET /api/me` (cheap).

### 7.4 — Backward-compatibility window

The migration of `dr_onboarded` → server is best-effort and happens on first authenticated page-load. If a user signs in on a brand-new browser, their server state wins (they were never onboarded → tour shows). If a user has the legacy localStorage flag on an old browser, the server takes it on first boot.

After two release cycles, the legacy localStorage read path can be deleted (separate cleanup spec).

---

## 8. Files touched (exhaustive)

### 8.1 — Frontend

| Path | Change |
|---|---|
| `src/dual_research/ui/static/onboarding.jsx` | Rewrite: TourSpotlight SVG component, skip-on-missing-anchor with toast, cross-route navigation for steps 3/5/6/7, server-state hooks (`useOnboardingState`), phase vocabulary refresh in step 4 SVG + step 5 body. |
| `src/dual_research/ui/static/settings.jsx` | Wrap existing `AllowlistManager` in a sub-tabbed `SettingsScreen` with `[Allowlist]` (current content) + `[Users]` (new — see below). Add the global onboarding controls panel. |
| `src/dual_research/ui/static/admin-users.jsx` | **Delete**. The component is folded into `settings.jsx`'s Users sub-tab. |
| `src/dual_research/ui/static/app.jsx` | Drop the `admin-users` route. Drop the avatar-menu "Admin: users" item. Add hash-based sub-tab handling to `/settings`. Update `useMe()` to also fetch `/api/onboarding/state`. |
| `src/dual_research/ui/static/components.css` | New `SPEC-0124` block: `.tour-spotlight`, `.tour-callout` (refresh), `.tour-skip-toast`, `.settings-tabs`, `.users-table`, `.users-table__bulk-bar`, `.global-onboarding-panel`. ~200 lines. |
| `src/dual_research/ui/static/index.html` | Cache-bust bump. |
| `src/dual_research/__init__.py` | Version bump to 1.6.0 at PR merge. |
| `CHANGELOG.md` | New entry. |

### 8.2 — Backend

| Path | Change |
|---|---|
| `supabase/migrations/<date>_add_onboarding_state.sql` | The schema migration in § 7.1. |
| `src/dual_research/server.py` | New routes: `/api/users` (GET), `/api/users/<email>/reset-onboarding` (POST), `/api/users/bulk-reset-onboarding` (POST), `/api/onboarding/state` (GET, PUT), `/api/onboarding/broadcast-reset` (POST), `/api/system-settings` (GET, PUT). Update `/api/me` to also update `last_seen_at`. |
| `tests/server/test_users_api.py` | New — covers all the new endpoints + admin gating + self-protections (can't reset onboarding for self? OK to allow). |
| `tests/server/test_onboarding_state.py` | New — server-side onboarding state lifecycle. |

### 8.3 — Spec docs

| Path | Change |
|---|---|
| `specs/0124-onboarding-rewrite-and-unified-admin-settings.md` | This spec. |

---

## 9. Acceptance criteria

### 9.1 — Onboarding tour (visual + flow)

- [ ] Spotlight steps render with a real cutout in the dim layer (`<TourSpotlight>` SVG present in DOM; the cutout shape matches the anchor's bounding rect ± padding).
- [ ] A blue (`var(--info)`) halo gradient ring surrounds the cutout.
- [ ] The callout card has `box-shadow: var(--e-2)` and an `--info-border` outline.
- [ ] An arrow on the card points at the anchor (CSS triangle on `::before`).
- [ ] Card position respects the overflow-aware positioner: tries [right, below, left, above] and clamps inside the viewport.
- [ ] When an anchor is missing, the step is **skipped automatically** within ~600 ms with a bottom-right toast `"Step N skipped — no <anchor> on this page."` Tour advances to next step.
- [ ] Cross-route steps (3, 5, 6, 7) navigate to `/runs/<latest-run-id>` on enter. If no run exists, they're collapsed into a single placeholder step explaining "start a run from the CLI."
- [ ] Step 4 + step 5 use spec-0114 phase vocabulary (no "Preflight / Independent Research / Plan Negotiation / Drafting / Review Loop").
- [ ] Step 8 body no longer mentions `?reset_onboarding=1`.

### 9.2 — Unified Admin/Settings

- [ ] `/admin/users` returns a client-side redirect to `/settings#users` (or the route is removed entirely and the menu item is gone).
- [ ] Avatar menu (admin) shows: Design language · Replay tour · — · Settings · — · Sign out. No "Admin: users".
- [ ] `/settings` renders a sub-tab row `[Allowlist] [Users]`; default tab `Allowlist`.
- [ ] Sub-tab state persists in URL hash (`#allowlist` / `#users`).
- [ ] `Allowlist` sub-tab renders the existing allowlist table unchanged.
- [ ] `Users` sub-tab renders a multi-user table with checkbox column + email + role + onboarding status + last seen + actions.
- [ ] Per-row "Reset onboarding" button triggers a confirmation dialog and POSTs to `/api/users/<email>/reset-onboarding`. Table refreshes.
- [ ] Per-row "Remove" button triggers same confirmation as the Allowlist tab.
- [ ] Bulk-action bar appears above the table when ≥ 1 row is checked: "Reset onboarding (N)" and "Remove (N)".
- [ ] Global onboarding controls panel shows above the table: `[✓] Required for all new sign-ins` toggle + `[ Reset for everyone ]` button.
- [ ] Reset-for-everyone confirms `"This will re-trigger onboarding for all N users. Continue?"` before firing.
- [ ] Search input + filter chips (`[All] [Admins] [Pending] [Completed]`) filter the table client-side.

### 9.3 — Server-persisted onboarding

- [ ] `approved_emails` has the four new columns (`onboarded_at`, `onboarded_at_version`, `tour_step`, `tour_force_reset_at`, `last_seen_at`).
- [ ] `system_settings` table exists with a single row + `onboarding_required` boolean.
- [ ] All 8 new endpoints respond with correct status codes (401 if unauthed, 403 if non-admin on admin-only endpoints, 200 + JSON on success).
- [ ] Server-side rule: `mustRestart` = `tour_force_reset_at IS NOT NULL AND (onboarded_at IS NULL OR tour_force_reset_at > onboarded_at)` — verified by a test that flips both ordering cases.
- [ ] Admin can reset onboarding for one user → that user's next page load opens the tour at step 1 (verified by a manual test with two browser sessions).
- [ ] Admin can broadcast-reset → all users' next page load opens the tour.
- [ ] Bulk reset works for ≥ 2 emails in one call.
- [ ] `GET /api/onboarding/state` returns `tourStep` from the server. `PUT` updates it.
- [ ] First boot with `dr_onboarded === 'true'` in localStorage migrates to `onboarded_at = now()` server-side, then clears localStorage.
- [ ] `last_seen_at` is updated on every `/api/me` call (visible by querying the table after a sign-in).

### 9.4 — Build / no regressions

- [ ] `uv run pytest tests/ -q` → green.
- [ ] No browser-console errors on `/settings`, `/settings#users`, during the tour, or after a force-reset round-trip.
- [ ] Sign-in flow unchanged.
- [ ] Existing localStorage-only users (pre-migration) hit a one-shot migration on first boot; no infinite tour-loop.

---

## 10. Test plan

### 10.1 — Manual (live verification)

- [ ] Sign in as admin. Avatar menu shows the new shape. `/admin/users` redirects to `/settings#users`.
- [ ] On `/settings`, click `Users` tab. See the table.
- [ ] Click "Reset onboarding" on another user. Sign out, sign in as that user (or use an incognito window). Tour auto-opens at step 1.
- [ ] Toggle "Required for all new sign-ins" on. Sign in as a fresh user (or fresh browser) — tour fires.
- [ ] Click "Reset for everyone". Re-load every other open browser session — tour fires for all of them.
- [ ] Walk the tour: each spotlight step shows a real cutout + halo + card with arrow.
- [ ] On `/` with zero runs, the cross-route steps collapse into the placeholder step.
- [ ] Force a missing-anchor situation (e.g. remove the `data-tour-anchor` attribute via devtools). Step skips with toast.
- [ ] Theme toggle while tour is open swaps the spotlight + card colors.

### 10.2 — Automated

- [ ] Server: `/api/users` returns 403 for non-admin.
- [ ] Server: `/api/users/<email>/reset-onboarding` updates `tour_force_reset_at`.
- [ ] Server: `mustRestart` flips correctly across the ordering cases.
- [ ] Server: bulk reset works for empty / single / many arrays.
- [ ] Server: `/api/onboarding/state` GET/PUT round-trips.
- [ ] Client: `useOnboardingState` migrates localStorage on first boot.

---

## 11. Risks

- **Migration of existing users.** Some users have `dr_onboarded === 'true'` on multiple browsers. On the FIRST authenticated boot per browser, the localStorage flag is consulted and may migrate. If users have different localStorage states on different browsers (unlikely but possible), the first browser to boot wins. Mitigation: this is acceptable — once `onboarded_at` is set server-side, subsequent browsers see "already onboarded" and skip.
- **Toast flash on missing anchor.** A 600 ms toast then auto-advance could feel jumpy. Mitigation: tune timing during impl; consider a 1 s minimum so the user can read the toast.
- **Cross-route navigation race.** Tour navigates to `/runs/<id>`, the page mounts asynchronously, the anchor might not exist after 2 s. Mitigation: same skip-on-missing-anchor path; the user sees the toast and the tour moves on.
- **Global "Required for all" toggle could surprise users.** If an admin toggles it on, existing-onboarded users with `tour_force_reset_at > onboarded_at` see the tour again. Mitigation: the toggle on its own does NOT set `tour_force_reset_at` — only the explicit "Reset for everyone" button does. The toggle only affects who's gated.
- **`last_seen_at` update on every `/api/me` call.** Cheap update but adds a write on every page load. Mitigation: debounce to once per minute server-side.
- **Demo-run dependency.** If no end-to-end fixture exists in `runs/` on the live server, cross-route steps collapse. Acceptable — the collapsed step explicitly tells the user to start a run.

---

## 12. Out of scope (explicit)

- **No new tour content.** Same 8 conceptual steps. Step 4 SVG can be regenerated using the spec-0121 pipeline diagram, but the prose is unchanged in tone.
- **No analytics / completion-rate dashboards.** The per-user state is enough for v1.
- **No reset for individual steps.** Admins can reset the whole tour for a user, not jump them to step N.
- **No tour for admin pages.** The Settings/Users surface itself has no `data-tour-anchor` attributes.
- **No mobile-specific tour layout.** Desktop-only assumption matches current product.

---

## 13. Open questions

- **OQ-1.** Should "Reset for everyone" send an email notification to users about the upcoming re-tour? *Default: no — silent re-trigger; users see the tour on next page load.*
- **OQ-2.** Should "Required for all new sign-ins" be on by default or off? *Default: off (preserves current behaviour); admins flip on if they want stricter onboarding.*
- **OQ-3.** Should the user's "Reset onboarding for myself" action live on the avatar menu (right next to "Replay tour")? *Default: keep "Replay tour" as-is — it's a local-only re-trigger that doesn't go through the server.*
- **OQ-4.** Should the Users tab show users who have *signed in* but aren't in the allowlist (would imply they hit a 403)? *Default: no — the allowlist is the canonical list.*
- **OQ-5.** Should the `tour_step` server-state persist across browsers (cross-device handoff) or stay per-browser? *Default: cross-browser (one canonical step per user). If user A starts tour on laptop and continues on desktop, they pick up at the same step.*

---

## 14. Backend touched?

**yes** — Supabase migration + `~8 new endpoints in server.py`.
