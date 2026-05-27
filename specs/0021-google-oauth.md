---
spec: 0021
title: Google OAuth + email allowlist via Supabase Auth
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.20.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/21"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0021 — Google OAuth + email allowlist

## Context

Spec 0020 shipped the hosted UI behind an HTTP Basic auth stopgap.
Workable but not real auth: one shared password, no concept of *who* is
signed in, no way to invite collaborators without sharing that password.

This spec replaces Basic with **Supabase Auth + Google OAuth + an
`approved_emails` allowlist**. Every `/api/*` request is gated by a
valid Supabase session for an allowlisted email. Visitors who hit the
URL without a session see a minimal sign-in screen (one Google
button); after sign-in their email is checked against
`approved_emails` — present → in; missing → "not approved".

Local `dual-research serve` (RUNS_BACKEND=fs) stays ungated. The auth
middleware only activates in supabase mode.

## Design decisions

All low-reversal; called out so they're easy to scan and push back on.

| # | Decision | Why |
|---|---|---|
| D1 | **Validate tokens via `supabase-py`'s `client.auth.get_user(token)` per request**, with a 60s in-memory cache | One HTTP call to Supabase per uncached request. Avoids JWKS/RS256 plumbing. Per-user overhead is trivial at our scale. |
| D2 | **`approved_emails` table**: `email PRIMARY KEY`, `is_admin BOOLEAN`, `added_at TIMESTAMPTZ` | Spec 0022 will add CRUD on this; we seed once here. RLS not configured (service-role bypasses anyway; spec 0022 will add it). |
| D3 | **Gate `/api/*` only** (except `/api/health` + `/api/config`); static bundle stays public | The JSX/HTML bundle has no secrets; access is meaningless without API data. Keeping it public means the sign-in screen renders at the URL without a chicken-and-egg auth gate. |
| D4 | **Frontend uses Supabase JS SDK** from a CDN, talks directly to Supabase for auth | Standard pattern. The SDK handles localStorage persistence, token refresh, OAuth redirect parsing. |
| D5 | **`/api/config` endpoint** returns `{ supabaseUrl, supabaseAnonKey }` for the browser to bootstrap the SDK | Decouples the bundled HTML from per-environment config. Public endpoint (these values are browser-safe by design). |
| D6 | **Frontend switches from EventSource to polling** for the run-detail live stream | EventSource can't send `Authorization` headers and we don't want tokens in URL query strings. The kickoff doc explicitly preferred polling for hosted anyway; this just brings the frontend in line. |
| D7 | **`authedFetch()` wrapper** injects `Authorization: Bearer <access_token>` into every API call | One central seam for auth — replace every `fetch()` call to `/api/*` in `live-data.jsx`. |
| D8 | **Drop BasicAuthMiddleware entirely**; remove `UI_BASIC_AUTH_PASSWORD` Fly secret | Stopgap is over. One auth path, not two. |
| D9 | **Token cache is in-memory**, per-process, 60s TTL | Tiny dict. We run one machine; cross-machine cache invalidation is irrelevant. |
| D10 | **Seed `alex.lisitzky@gmail.com` as the first admin** | Required by spec 0022's bootstrap rule (≥1 admin row must exist). |

## Proposed change

### Schema — `supabase/migrations/0002_approved_emails.sql`

```sql
CREATE TABLE IF NOT EXISTS approved_emails (
    email      TEXT PRIMARY KEY,
    is_admin   BOOLEAN NOT NULL DEFAULT false,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO approved_emails (email, is_admin)
VALUES ('alex.lisitzky@gmail.com', true)
ON CONFLICT (email) DO UPDATE SET is_admin = EXCLUDED.is_admin;
```

Run via Supabase Dashboard → SQL Editor, same path as 0001.

### Backend — `src/dual_research/ui/auth.py` (replaced)

The whole `BasicAuthMiddleware` is removed. New
`SupabaseAuthMiddleware`:

```python
class SupabaseAuthMiddleware:
    def __init__(self, app, client, *, cache_ttl_seconds: float = 60.0): ...
    async def __call__(self, scope, receive, send):
        # 1. Skip for non-/api or for /api/health, /api/config.
        # 2. Extract Bearer token. 401 if missing.
        # 3. Validate token (cached). 401 if invalid.
        # 4. Check email is in approved_emails. 403 if not.
        # 5. Pass through.
```

Cache structure: `{ token_hash: (email, expires_at) }`. The `email` is
None for tokens that validated but whose email isn't allowlisted — we
cache the "not approved" answer too, so a hammered URL doesn't keep
re-querying.

### Server — `src/dual_research/ui/server.py`

`_make_supabase_app` swaps `BasicAuthMiddleware` for the new one and
adds a `/api/config` endpoint:

```python
@app.get("/api/config")
async def config() -> dict[str, str]:
    return {"supabaseUrl": ..., "supabaseAnonKey": ...}
```

Config values come from `load_supabase_credentials()`. Both are
browser-safe per Supabase's design.

`_make_app` (fs mode) is **untouched** — local mode stays ungated.

### Frontend

**`src/dual_research/ui/static/index.html`** — add Supabase JS SDK
script tag (CDN):

```html
<script src="https://unpkg.com/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
```

And add a new `auth.jsx` script in the load order (before
`live-data.jsx`):

```html
<script type="text/babel" src="auth.jsx"></script>
```

**`src/dual_research/ui/static/auth.jsx` (new)** — provides:

- `useSupabaseClient()` — fetches /api/config once, returns a memoized
  `supabase` client.
- `useSession()` — subscribes to `onAuthStateChange`, returns the
  current Session or null.
- `SignInScreen` — single button, calls `signInWithOAuth({ provider:
  'google', options: { redirectTo: window.location.origin } })`.
- `NotApprovedScreen` — shown when the user signed in but the server
  returned 403 on first API call (email not on the allowlist).
- `authedFetch(url, options)` — wrapper that pulls the session and
  injects `Authorization: Bearer ${access_token}`.

**`src/dual_research/ui/static/app.jsx`** — wraps the routed views in
an auth gate:

```jsx
function App() {
  const { client, ready } = useSupabaseClient();
  const session = useSession(client);
  if (!ready) return <FullPageMessage title="Loading…" />;
  if (!session) return <SignInScreen client={client} />;
  return <RoutedApp />;
}
```

When the API returns 403 after auth, the SDK throws and a top-level
ErrorBoundary in App swaps to `<NotApprovedScreen />`.

**`src/dual_research/ui/static/live-data.jsx`** — every `fetch(...)`
call swapped for `authedFetch(...)`. The `EventSource` block in
`useLiveRun` is replaced with `setInterval(authedFetch, 5000)` —
polling. The `connected` flag now means "last poll succeeded in the
last 7s".

### Fly secrets

After deploy, remove the no-longer-used basic-auth secret:

```
fly secrets unset UI_BASIC_AUTH_PASSWORD -a dual-research-alex
```

`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` stay
as-is.

### User pre-work

Before this spec can run end-to-end:

1. **Google Cloud OAuth client.** Google Cloud Console →
   "APIs & Services" → "Credentials" → "Create credentials" → "OAuth
   client ID". Type = **Web application**. Authorized JavaScript
   origins: `https://dual-research-alex.fly.dev`. Authorized
   redirect URIs: **your Supabase project's auth callback URL**
   (`https://<project-ref>.supabase.co/auth/v1/callback`). Copy the
   client ID + client secret.
2. **Configure Google in Supabase.** Supabase Dashboard →
   Authentication → Providers → Google → enable → paste the client ID
   and secret → save.

That's the only out-of-band setup. Migration is applied via the SQL
editor as in 0019/0020.

### Version + CHANGELOG

`pyproject.toml` 0.19.0 → 0.20.0. `__init__.py` ditto. CHANGELOG
gets a `## [0.20.0]` entry.

## Out of scope

- **Admin route for `approved_emails`** — spec 0022.
  No CRUD UI in this spec; rows are managed via the Supabase
  dashboard SQL editor until 0022 lands.
- **Kickoff-from-UI** — spec 0023.
- **Other OAuth providers** (GitHub, etc.). Google only for now;
  Supabase makes adding more trivial later.
- **Per-user state** (last-viewed run, saved filters, etc.). Auth
  identifies *who* but no per-user UI features are added here.
- **Audit log of sign-ins / denials**. Supabase has its own auth log;
  we don't aggregate it.
- **Rate limiting on the API.** Out of scope; revisit if abuse
  appears.
- **Custom email-allowlist domain rules** (e.g. "anyone
  @anthropic.com"). For now individual emails only. Adding a
  domain-match column to `approved_emails` is a follow-up spec.
- **CSP / strict security headers.** Useful but orthogonal.

## Test plan

### Unit

`tests/ui/test_supabase_auth.py` (new):

- [ ] Request with no `Authorization` → 401.
- [ ] Request with malformed `Authorization` → 401.
- [ ] Request with a valid token whose email is *not* in
      `approved_emails` → 403.
- [ ] Request with a valid token whose email *is* in
      `approved_emails` → 200.
- [ ] `/api/health` and `/api/config` return 200 without any token.
- [ ] Static paths (`/`, `/app.jsx`) return 200 without any token.
- [ ] Two requests in quick succession with the same valid token hit
      the cache (only one `get_user` call recorded).
- [ ] After the cache TTL expires, the token is re-validated.

The fake supabase client gets a tiny `auth.get_user(token)` stub
returning whatever the test seeded. We don't validate JWTs in unit
tests — the SDK is treated as a trusted boundary.

### Manual smoke (post-deploy)

- [ ] Visit `https://dual-research-alex.fly.dev/` without a session
      → sign-in screen renders.
- [ ] Click "Sign in with Google" → redirected to Google → back to
      app → all-runs list shows.
- [ ] Sign in as a non-allowlisted email → "not approved" screen
      shown.
- [ ] Confirm the migration ran: `SELECT * FROM approved_emails;` in
      Supabase shows `alex.lisitzky@gmail.com` as admin.
- [ ] Confirm `UI_BASIC_AUTH_PASSWORD` was unset on Fly.

Total expected: ~10 new tests; total ~270.

## Risks

- **OAuth client misconfiguration.** Easy to fumble the redirect URI
  in Google Cloud Console — gives an opaque error after the
  redirect. Mitigation: spec body lists the exact URI shape;
  Supabase's docs surface the same.
- **Token validation latency.** First request per token incurs a
  `get_user` HTTP roundtrip (~100-200ms). Within the 60s cache window,
  all further requests are dict lookups. If we ever see real users,
  switch to JWKS-based local validation. Today: invisible.
- **Race on the auth state.** During the first ~500ms after the
  OAuth redirect, the SDK is still parsing the URL fragment. Brief
  "loading" flash is fine; the app waits on `useSession` returning
  a definite null vs Session before deciding what to render.
- **Lockout if the migration isn't applied.** A user could sign in
  successfully via Google but get 403 because `approved_emails` is
  empty. Mitigation: the migration body explicitly seeds the user's
  email; user pre-work confirms before deploy.
- **Dropping BasicAuth is one-way until we redeploy with an
  intermediate state.** If something is wrong with Supabase auth on
  first deploy, the URL is wide open (nothing gates it). Mitigation:
  the deploy is gated by all unit tests passing; live test is
  immediate; rollback is `fly releases revert` if needed.

## Open questions

None outstanding for this spec. Spec 0022 will pick up: the admin
route's UX (modal? full route?), and the bootstrap rule for the
admin-of-admins.
