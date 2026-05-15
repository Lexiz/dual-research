// auth.jsx — Supabase Auth wiring for the hosted UI (spec 0021).
//
// Exposes three globals on `window`:
//   - useSupabaseClient()  → { client, ready, error, hostedMode }
//   - useSession(client)   → { session, ready }
//   - SignInScreen({ client })
//   - NotApprovedScreen({ session, client })
//   - authedFetch(url, opts)
//
// The browser bootstraps by fetching /api/config. If the response has empty
// supabaseUrl / supabaseAnonKey, we're running against a local fs-mode
// server — auth is disabled, hooks return ready=true / session=null and
// authedFetch falls back to plain fetch.

(function () {
  let _bootstrap = null;

  function bootstrap() {
    if (_bootstrap) return _bootstrap;
    _bootstrap = fetch('/api/config')
      .then(r => r.ok ? r.json() : { supabaseUrl: '', supabaseAnonKey: '' })
      .catch(() => ({ supabaseUrl: '', supabaseAnonKey: '' }))
      .then(cfg => {
        const hosted = !!(cfg.supabaseUrl && cfg.supabaseAnonKey);
        if (!hosted) return { client: null, hostedMode: false };
        // window.supabase comes from the UMD bundle loaded in index.html.
        const client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey, {
          auth: {
            detectSessionInUrl: true,
            persistSession: true,
            flowType: 'implicit',
          },
        });
        return { client, hostedMode: true };
      });
    return _bootstrap;
  }

  function useSupabaseClient() {
    const [state, setState] = React.useState({ client: null, ready: false, hostedMode: false, error: null });
    React.useEffect(() => {
      let cancelled = false;
      bootstrap()
        .then(({ client, hostedMode }) => {
          if (!cancelled) setState({ client, ready: true, hostedMode, error: null });
        })
        .catch(e => { if (!cancelled) setState({ client: null, ready: true, hostedMode: false, error: String(e) }); });
      return () => { cancelled = true; };
    }, []);
    return state;
  }

  function useSession(client) {
    const [state, setState] = React.useState({ session: null, ready: false });
    React.useEffect(() => {
      if (!client) {
        // fs-mode: there's no client, treat as "ready, no session needed".
        setState({ session: null, ready: true });
        return;
      }
      let cancelled = false;
      client.auth.getSession().then(({ data }) => {
        if (!cancelled) setState({ session: data?.session || null, ready: true });
      });
      const { data: sub } = client.auth.onAuthStateChange((_event, session) => {
        if (!cancelled) setState({ session: session || null, ready: true });
      });
      return () => {
        cancelled = true;
        try { sub?.subscription?.unsubscribe?.(); } catch (e) { /* noop */ }
      };
    }, [client]);
    return state;
  }

  // Pull the latest session synchronously from Supabase storage so authedFetch
  // can inject the bearer header without re-running the async getSession() call.
  async function currentAccessToken(client) {
    if (!client) return null;
    try {
      const { data } = await client.auth.getSession();
      return data?.session?.access_token || null;
    } catch (e) {
      return null;
    }
  }

  // Module-level fetch wrapper. Resolves the client through bootstrap() so
  // callers don't have to thread it through React context.
  async function authedFetch(url, opts) {
    const { client } = await bootstrap();
    const token = await currentAccessToken(client);
    const headers = new Headers(opts?.headers || {});
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const res = await fetch(url, { ...(opts || {}), headers });
    if (res.status === 403) {
      try { window.dispatchEvent(new Event('dr-not-approved')); } catch (e) { /* noop */ }
    }
    return res;
  }

  function SignInScreen({ client, error }) {
    const onClick = () => {
      client.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin + '/' },
      });
    };
    return (
      <div style={{
        height: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg-0)', color: 'var(--fg-0)', gap: 16,
      }}>
        <div style={{ fontSize: 20, fontWeight: 600 }}>dual-research · monitor</div>
        <div style={{ fontSize: 13, color: 'var(--fg-2)', marginBottom: 12 }}>
          Sign in to view pushed runs.
        </div>
        <button onClick={onClick} style={{
          padding: '10px 18px', borderRadius: 6, cursor: 'pointer',
          border: '1px solid var(--border-1)', background: 'var(--bg-1)',
          color: 'var(--fg-0)', fontSize: 14, fontFamily: 'inherit',
        }}>
          Sign in with Google
        </button>
        {error && (
          <div style={{ fontSize: 12, color: 'var(--warn)', marginTop: 8 }}>
            {error}
          </div>
        )}
      </div>
    );
  }

  function NotApprovedScreen({ session, client }) {
    const email = session?.user?.email || '(unknown)';
    const onSignOut = () => client.auth.signOut().then(() => window.location.reload());
    return (
      <div style={{
        height: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg-0)', color: 'var(--fg-0)', gap: 12,
        padding: 24, textAlign: 'center',
      }}>
        <div style={{ fontSize: 18, fontWeight: 600 }}>Not approved</div>
        <div style={{ fontSize: 13, color: 'var(--fg-2)', maxWidth: 460 }}>
          Signed in as <strong>{email}</strong>, but this email isn't on the
          allowlist. Ask the admin to add you, or sign in with a different
          Google account.
        </div>
        <button onClick={onSignOut} style={{
          padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
          border: '1px solid var(--border-1)', background: 'var(--bg-1)',
          color: 'var(--fg-0)', fontSize: 13, marginTop: 8,
        }}>
          Sign out
        </button>
      </div>
    );
  }

  // ─── Window exports ─────────────────────────────────────────────────────
  Object.assign(window, {
    useSupabaseClient,
    useSession,
    authedFetch,
    SignInScreen,
    NotApprovedScreen,
  });
})();
