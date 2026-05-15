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

  // ─── Landing visual ─────────────────────────────────────────────────────

  function AgentDuoVisual() {
    return (
      <svg width="280" height="120" viewBox="0 0 280 120" style={{ display: 'block' }}>
        <defs>
          <radialGradient id="claudeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="var(--agent-a)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--agent-a)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="gptGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="var(--agent-b)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--agent-b)" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="60" cy="60" r="56" fill="url(#claudeGlow)" />
        <circle cx="220" cy="60" r="56" fill="url(#gptGlow)" />
        <line x1="92" y1="60" x2="188" y2="60"
              stroke="var(--border-3)" strokeWidth="1.5"
              strokeDasharray="4 6" />
        <circle cx="140" cy="60" r="3.5" fill="var(--fg-1)">
          <animate attributeName="cx" values="92;188;92" dur="4s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0;1;1;0" dur="4s" repeatCount="indefinite" />
        </circle>
        <circle cx="60" cy="60" r="32"
                fill="var(--agent-a-bg-strong)" stroke="var(--agent-a-border)" strokeWidth="1.25" />
        <text x="60" y="68" textAnchor="middle"
              fontFamily="Geist, system-ui, sans-serif" fontWeight="600" fontSize="26"
              fill="var(--agent-a)">C</text>
        <circle cx="220" cy="60" r="32"
                fill="var(--agent-b-bg-strong)" stroke="var(--agent-b-border)" strokeWidth="1.25" />
        <text x="220" y="68" textAnchor="middle"
              fontFamily="Geist, system-ui, sans-serif" fontWeight="600" fontSize="26"
              fill="var(--agent-b)">G</text>
      </svg>
    );
  }

  // The standard Google "G" icon for the sign-in button.
  function GoogleGlyph() {
    return (
      <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
      </svg>
    );
  }

  function LandingScreen({ client, error }) {
    const onClick = () => {
      client.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin + '/' },
      });
    };
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: 'radial-gradient(ellipse at top, rgba(124, 196, 184, 0.06), transparent 60%), radial-gradient(ellipse at bottom, rgba(212, 165, 116, 0.06), transparent 60%), var(--bg-0)',
        color: 'var(--fg-0)', padding: 24,
      }}>
        <div style={{
          maxWidth: 460, width: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: 24, textAlign: 'center',
        }}>
          <AgentDuoVisual />
          <div>
            <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-0.02em' }}>dual-research</div>
            <div style={{ fontSize: 14, color: 'var(--fg-2)', marginTop: 6, maxWidth: 380, lineHeight: 1.5 }}>
              Two AI agents in conversation, converging toward a single research document.
            </div>
          </div>
          <button onClick={onClick} style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            padding: '10px 18px', borderRadius: 999, cursor: 'pointer',
            border: '1px solid #dadce0', background: '#fff',
            color: '#3c4043', fontFamily: 'inherit', fontSize: 14, fontWeight: 500,
            boxShadow: '0 1px 2px rgba(0,0,0,0.10)',
          }}>
            <GoogleGlyph />
            <span>Sign in with Google</span>
          </button>
          <div style={{ fontSize: 11, color: 'var(--fg-2)', maxWidth: 360, lineHeight: 1.5 }}>
            Access by invitation. Ask an admin to add your Google account to the allowlist.
          </div>
          {error && (
            <div style={{ fontSize: 12, color: 'var(--warn)' }}>{error}</div>
          )}
        </div>
      </div>
    );
  }

  // Backwards-compat alias used by older app.jsx.
  const SignInScreen = LandingScreen;

  function NotApprovedScreen({ session, client }) {
    const email = session?.user?.email || '(unknown)';
    const onSignOut = () => client.auth.signOut().then(() => window.location.reload());
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'radial-gradient(ellipse at top, rgba(124, 196, 184, 0.06), transparent 60%), var(--bg-0)',
        color: 'var(--fg-0)', padding: 24,
      }}>
        <div style={{
          maxWidth: 440, width: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: 14, textAlign: 'center',
        }}>
          <AgentDuoVisual />
          <div style={{ fontSize: 20, fontWeight: 600 }}>Not approved</div>
          <div style={{ fontSize: 13, color: 'var(--fg-2)', lineHeight: 1.5 }}>
            Signed in as <strong>{email}</strong>, but this address isn't on the allowlist.
            Ask an admin to add you, or sign in with a different Google account.
          </div>
          <button onClick={onSignOut} style={{
            padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
            border: '1px solid var(--border-2)', background: 'var(--bg-1)',
            color: 'var(--fg-0)', fontSize: 13, fontFamily: 'inherit', marginTop: 6,
          }}>
            Sign out
          </button>
        </div>
      </div>
    );
  }

  // ─── useMe ──────────────────────────────────────────────────────────────

  function useMe() {
    const [me, setMe] = React.useState(null);
    React.useEffect(() => {
      let cancelled = false;
      authedFetch('/api/me')
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (!cancelled) setMe(data); })
        .catch(() => { if (!cancelled) setMe(null); });
      return () => { cancelled = true; };
    }, []);
    return me;
  }

  // ─── Window exports ─────────────────────────────────────────────────────
  Object.assign(window, {
    useSupabaseClient,
    useSession,
    useMe,
    authedFetch,
    SignInScreen,        // alias of LandingScreen for backwards-compat
    LandingScreen,
    NotApprovedScreen,
  });
})();
