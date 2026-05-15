---
spec: 0022
title: Admin allowlist UI, profile menu, and landing-page redesign
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.21.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/22"
---

# Spec 0022 — Admin allowlist UI + profile menu + landing-page redesign

## Context

Spec 0021 wired Google OAuth + the `approved_emails` allowlist, but
managing the allowlist requires hand-editing rows in the Supabase SQL
editor. This spec lands the admin UI promised in the hosted-deployment
kickoff (§3, "spec 0022"), plus two UX upgrades:

- A profile menu in the chrome bar (avatar → sign out / design
  language / settings).
- A real landing page for unauthenticated visitors — currently a bare
  button on a dark background.

All three changes are user-facing, low-reversal, and orthogonal to the
backend's read paths. They ship together because the avatar menu is the
natural entry point for the admin route.

## Design decisions

All low-reversal. Listed so they're easy to scan.

| # | Decision | One-liner |
|---|---|---|
| D1 | **`is_admin` server-side enforcement** on every `/api/approved-emails*` call | Middleware already validates the email; admin routes re-check `is_admin` from the same row. No client-side trust. |
| D2 | **`GET /api/me`** returns `{email, isAdmin, avatarUrl, fullName}` | Drives whether the Settings menu item renders. The avatar URL comes from Google via Supabase user metadata. |
| D3 | **CRUD shape**: `GET /api/approved-emails`, `POST /api/approved-emails`, `DELETE /api/approved-emails/{email}` | REST-shaped; immediate (no batch/draft mode). Each click talks to the server. |
| D4 | **Self-protect on delete** (admin can't delete their own email) and **last-admin protect** (can't demote/delete the last admin) | Both enforced server-side, surfaced as 409 with a human-readable message. |
| D5 | **Avatar dropdown** in the chrome bar — replaces the current standalone "Design language" link; theme toggle stays as its own icon | Less chrome clutter; profile/account UX is conventional. |
| D6 | **Settings only visible to admins** in the menu; non-admins hitting `#/settings` directly see an "admin only" inline message | Server's the source of truth; UI just hides the entrance. |
| D7 | **Landing-page visual**: letter-mark "C" and "G" discs in theme accent colors, connected by a faint line; tagline below | Conveys "two agents in conversation" without using Anthropic/OpenAI logos (trademark-safe). |
| D8 | **Sign-in button**: white pill with Google "G" SVG + "Sign in with Google" label | Matches Google brand-style guidance closely enough to feel official without pulling in their full asset kit. |
| D9 | **Avatar fallback**: when Google has no avatar, render initials on a coloured disc keyed off a hash of the email | Deterministic per email; pleasant default. |
| D10 | **`current_user` plumbed through the middleware** | Middleware attaches `scope["user"] = {"email": ..., "is_admin": ...}`. Admin routes read it; no second DB lookup. |

## Proposed change

### Backend (`src/dual_research/ui/server.py` + `auth.py`)

**`auth.py`** — extend `_email_is_approved` to also return `is_admin`,
and have `SupabaseAuthMiddleware` cache + plumb that. The middleware
sets `scope["user"] = {"email": ..., "is_admin": bool}`.

**`server.py`** — four new routes on the supabase-mode app:

- `GET /api/me` — reads `scope["user"]` + optionally calls
  `client.auth.get_user(token)` again to pull `user_metadata.avatar_url`
  and `full_name` from Google. Returns `{email, isAdmin, avatarUrl,
  fullName}`. Cached client-side; the SDK keeps a session.

- `GET /api/approved-emails` — admin-only. Returns the full list
  sorted by `added_at desc`.

- `POST /api/approved-emails` — admin-only. Body `{email, isAdmin}`.
  Inserts a new row; upserts on conflict (keeps `is_admin` in sync).
  Returns the inserted row.

- `DELETE /api/approved-emails/{email}` — admin-only. Blocks
  self-delete and last-admin delete with `409 Conflict` + a
  human-readable message. On success returns 204.

A small helper `_require_admin(scope) -> str` lifted into the same
file; raises `HTTPException(403)` if `scope["user"]["is_admin"]` is
false. The four routes call it.

### Frontend

**`static/auth.jsx`** — extend the SignInScreen export to use the new
landing-page layout (described below). Add a `useMe()` hook that
fetches `/api/me` once per session and memoises the result on the
window so it can also be read synchronously.

**`static/app.jsx`** —

- Add `#/settings` to the route enum (in `router.jsx`).
- ChromeBar:
  - Drop the standalone "Design language" link.
  - Add an avatar disc on the right of the chrome bar. Click toggles
    a small dropdown with: "Design language", "Settings" (admin only),
    "Sign out". Click-outside-to-close.
- Top-level routing gains a `route.view === 'settings'` branch
  rendering `<SettingsScreen client={client} />`.

**`static/settings.jsx` (new)** — admin route content:

- Header: "Email allowlist", subtitle "Anyone with these Google
  accounts can sign in. Admins can manage this list."
- Table of rows: avatar, email, "Admin" badge, "Remove" button.
- Add-row at the bottom: text input, "Admin" checkbox, "Add" button.
  Validation (basic email regex) happens client-side; server gives a
  clear error if it fails again. After add, input clears and focus
  returns to it.
- Error toast strip at top of the page for the 409 cases (self-delete,
  last-admin).
- If `/api/me` says `!isAdmin`, the screen renders an inline "admin
  only" message instead of the table.

**`static/router.jsx`** — add the new route. The hash mapping is
trivial: `#/settings` → `{ view: 'settings' }`.

**`static/landing.jsx` (new, split out of auth.jsx)** — the new
landing-page component:

- Centered card on a subtle radial-gradient background using existing
  theme tokens.
- Title "dual-research" in display weight; a one-line tagline
  underneath.
- The two-agent visual: an inline SVG with a "C" disc on the left
  (claude accent colour) and a "G" disc on the right (gpt accent
  colour), with a faint dotted line connecting them and a small
  pulsing dot midway as a hint of motion.
- Tagline copy: "Two AI agents in conversation, converging toward a
  single research document."
- Below that, a white pill button ("Sign in with Google") with the
  multi-coloured Google "G" SVG. Hover + focus states tuned to match
  the existing theme.
- Subtle footnote: "Access by invitation. Ask an admin to add you to
  the allowlist."
- Theme-toggle stays in the corner so visitors aren't locked into the
  default theme.

**`static/auth.jsx`** — exports `LandingScreen` (replaces
`SignInScreen` as the unauth view in `App`). `NotApprovedScreen` gets
the same visual treatment so it doesn't feel like a different app.

### Tests

`tests/ui/test_admin_endpoints.py` (new):

- [ ] GET /api/approved-emails as admin returns the list.
- [ ] GET /api/approved-emails as non-admin returns 403.
- [ ] POST as admin inserts a row and is idempotent on duplicate.
- [ ] DELETE self returns 409 with the expected message.
- [ ] DELETE the last admin returns 409.
- [ ] DELETE a non-admin row works for an admin caller.

`tests/ui/test_supabase_auth.py` — extend:

- [ ] `scope["user"]["is_admin"]` is True for admin tokens, False otherwise.
- [ ] `is_admin` is cached with the token validation (no extra DB call).

`tests/ui/test_server_supabase_mode.py` — extend:

- [ ] `/api/me` returns the right shape under the seeded token.

No frontend-JS unit tests (the project has none today; the manual
smoke covers the same surface).

### Version + CHANGELOG

`pyproject.toml` 0.20.0 → 0.21.0. `__init__.py` ditto. CHANGELOG
gets a `## [0.21.0]` entry.

## Out of scope

- **Bulk import** of email addresses (CSV upload, paste list). Add a
  follow-up if it ever matters; right now there's one user.
- **Domain-match allowlist** (e.g. anyone @example.com). Per-email
  only for now.
- **Inviting unverified emails** (sending an invitation email).
  Allowlist additions only let someone sign in *if* they have a Google
  account at that address — we don't email them.
- **Audit log** of who-added-whom. Supabase keeps auth logs; we don't
  duplicate.
- **Custom domain** for the Fly app. Still
  `dual-research-alex.fly.dev`; one `fly certs add` away.
- **Mobile layout polish.** The chrome bar / dropdown work on
  desktop; mobile is best-effort.
- **Kickoff-from-UI.** Still spec 0023 territory.

## Risks

- **Race when an admin demotes another admin while themselves being
  the only other admin** — they could lock themselves out at the same
  moment. We do the last-admin check at write time; if two admins
  delete simultaneously, the DB constraint is the backstop. We do
  *not* enforce this via a SQL constraint in spec 0022 — server-side
  pre-check only. If it bites, a Postgres trigger is a follow-up.
- **Avatar URL availability.** Google sometimes returns no avatar
  (recent privacy changes). Fallback initials disc covers that.
- **Trademark drift.** The letter-mark visual is intentional; if we
  ever swap to actual Anthropic/OpenAI assets, we'd want their brand
  guidelines or written permission.
- **Settings screen as the only admin entry.** No URL is ever shared
  with non-admins, but `#/settings` is technically guessable.
  Defense-in-depth: the API gate is the real protection; the UI just
  hides the entrance.

## Open questions

None.
