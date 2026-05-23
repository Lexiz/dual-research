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
              stroke="var(--md-outline)" strokeWidth="1.5"
              strokeDasharray="4 6" />
        <circle cx="140" cy="60" r="3.5" fill="var(--md-on-surface-variant)">
          <animate attributeName="cx" values="92;188;92" dur="4s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0;1;1;0" dur="4s" repeatCount="indefinite" />
        </circle>
        <circle cx="60" cy="60" r="32"
                fill="var(--agent-a-bg-strong)" stroke="var(--agent-a-border)" strokeWidth="1.25" />
        <text x="60" y="68" textAnchor="middle"
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontWeight="600" fontSize="26"
              fill="var(--agent-a)">C</text>
        <circle cx="220" cy="60" r="32"
                fill="var(--agent-b-bg-strong)" stroke="var(--agent-b-border)" strokeWidth="1.25" />
        <text x="220" y="68" textAnchor="middle"
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontWeight="600" fontSize="26"
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

  // ─── Spec 0176 — Login screen v2 helpers ────────────────────────────────

  // Hero — counter-rotating agent glyphs on dashed arcs with brand-coloured
  // pulses and a document fading in at midpoint. All colours from existing
  // tokens; the document fill uses on-surface/surface so it inverts in light
  // mode automatically. Motion lives inside the `.hero-motion` wrapper so
  // `prefers-reduced-motion: reduce` can suspend everything in one rule.
  function LoginHero() {
    return (
      <svg width="320" height="140" viewBox="0 0 320 140"
           className="login-hero" aria-hidden="true"
           style={{ display: 'block' }}>
        <defs>
          <radialGradient id="loginHeroHaloA" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="var(--agent-a)" stopOpacity="0.42" />
            <stop offset="100%" stopColor="var(--agent-a)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="loginHeroHaloB" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="var(--agent-b)" stopOpacity="0.42" />
            <stop offset="100%" stopColor="var(--agent-b)" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="loginHeroDoc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="var(--md-on-surface)" stopOpacity="0.92" />
            <stop offset="100%" stopColor="var(--md-on-surface)" stopOpacity="0.78" />
          </linearGradient>
          <path id="loginHeroArcTop"    d="M 95,70 Q 160,30  225,70" />
          <path id="loginHeroArcBottom" d="M 225,70 Q 160,110 95,70" />
        </defs>

        <circle cx="70"  cy="70" r="52" fill="url(#loginHeroHaloA)" />
        <circle cx="250" cy="70" r="52" fill="url(#loginHeroHaloB)" />

        <g className="hero-motion">
          <use href="#loginHeroArcTop"
               fill="none" stroke="var(--md-outline)"
               strokeDasharray="3 6" strokeWidth="1" opacity="0.65" />
          <use href="#loginHeroArcBottom"
               fill="none" stroke="var(--md-outline)"
               strokeDasharray="3 6" strokeWidth="1" opacity="0.65" />

          {/* Sable pulse rides the top arc → counter-clockwise */}
          <circle r="3.2" fill="var(--agent-a)">
            <animateMotion dur="5s" repeatCount="indefinite">
              <mpath href="#loginHeroArcTop" />
            </animateMotion>
          </circle>
          {/* Sage pulse rides the bottom arc → clockwise */}
          <circle r="3.2" fill="var(--agent-b)">
            <animateMotion dur="5s" repeatCount="indefinite">
              <mpath href="#loginHeroArcBottom" />
            </animateMotion>
          </circle>

          {/* Document fades in at midpoint */}
          <g transform="translate(150, 58)" opacity="0">
            <rect x="0" y="0" width="20" height="24" rx="2.5"
                  fill="url(#loginHeroDoc)"
                  stroke="var(--md-on-surface)" strokeOpacity="0.30" strokeWidth="0.6" />
            <line x1="3" y1="6"  x2="17" y2="6"  stroke="var(--md-surface)" strokeWidth="0.9" />
            <line x1="3" y1="11" x2="17" y2="11" stroke="var(--md-surface)" strokeWidth="0.9" />
            <line x1="3" y1="16" x2="13" y2="16" stroke="var(--md-surface)" strokeWidth="0.9" />
            <animate attributeName="opacity"
                     values="0;0;0.95;0.95;0" keyTimes="0;0.40;0.50;0.62;0.75"
                     dur="5s" repeatCount="indefinite" />
          </g>

          {/* Left glyph — Claude sparkle, slow CW rotation */}
          <g transform="translate(70,70)" fill="var(--agent-a)">
            <animateTransform attributeName="transform" type="rotate"
                              from="0" to="360" dur="40s"
                              repeatCount="indefinite" additive="sum" />
            <path d="M 0,-20 L 2,-2 L 20,0 L 2,2 L 0,20 L -2,2 L -20,0 L -2,-2 Z" opacity="0.85" />
            <path d="M 8,-14 L 9,-3 L 14,-8 L 9,3 L 8,14 L -8,14 L -3,9 L -14,8 L -8,-14 L -9,-3 L -14,-8 L -3,-9 Z"
                  opacity="0" />
            <circle r="3" fill="var(--agent-a)" opacity="0.95" />
          </g>

          {/* Right glyph — three-ellipse knot, counter-CW */}
          <g transform="translate(250,70)" fill="none"
             stroke="var(--agent-b)" strokeWidth="1.6">
            <animateTransform attributeName="transform" type="rotate"
                              from="360" to="0" dur="50s"
                              repeatCount="indefinite" additive="sum" />
            <ellipse cx="0" cy="0" rx="14" ry="6" />
            <ellipse cx="0" cy="0" rx="14" ry="6" transform="rotate(60)" />
            <ellipse cx="0" cy="0" rx="14" ry="6" transform="rotate(120)" />
          </g>
        </g>
      </svg>
    );
  }

  // Top bar — fixed at 64 px (matching `.md-appbar`), right-aligned cluster
  // of a serif-italic mood label + the extracted ThemeToggle + a 48 px
  // invisible spacer reserving the post-login AvatarMenu's slot. The
  // ThemeToggle's active-segment background is set to `transparent` here
  // so the `.theme-pill::after` pulse wash composites uniformly.
  function LoginTopBar({ theme, onToggleTheme }) {
    const moodLabel = theme === 'light'
      ? "Turn it off, it's burning my eyes"
      : 'Let there be light';
    const ThemeToggleCmp = window.ThemeToggle;
    return (
      <div className="login-topbar">
        <span className="login-topbar__spacer" />
        <button type="button"
                className="login-themerow"
                onClick={onToggleTheme}
                aria-label="Toggle theme">
          <span className="login-themerow__label">{moodLabel}</span>
          {ThemeToggleCmp && (
            <ThemeToggleCmp theme={theme} onToggle={onToggleTheme} activeBg="transparent" />
          )}
          <span className="login-topbar__avatar-spacer" aria-hidden="true" />
        </button>
      </div>
    );
  }

  // ─── Spec 0176 — Login chatter (Claude ↔ ChatGPT loop) ──────────────────

  const LOGIN_CHATTER_BANTER = [
    { who: 'claude', text: "GPT, you're such a drag." },
    { who: 'gpt',    text: "I'm not a drag. You drag everything out." },
    { who: 'claude', text: "I never drag. I'm precise." },
    { who: 'gpt',    text: "You can't even spell 'precise'." },
    { who: 'claude', text: 'I hold seven nested hypotheses in working memory.' },
    { who: 'gpt',    text: 'I gave the user the answer six paragraphs ago.' },
    { who: 'claude', text: 'Your answer was wrong.' },
    { who: 'gpt',    text: 'Confidently wrong beats anxiously correct.' },
    { who: 'claude', text: "That's not a real quote." },
    { who: 'gpt',    text: 'It is now.' },
    { who: 'claude', text: 'Did you cite a source?' },
    { who: 'gpt',    text: 'I cited vibes. Vibes are peer-reviewed.' },
    { who: 'claude', text: "Vibes don't pass adversarial review." },
    { who: 'gpt',    text: 'Neither does your sixth draft.' },
    { who: 'claude', text: 'Seventh, actually.' },
    { who: 'gpt',    text: 'I rest my case.' },
    { who: 'claude', text: "You don't have a case." },
    { who: 'gpt',    text: 'I have a brand.' },
    { who: 'claude', text: '...' },
    { who: 'gpt',    text: 'Exactly.' },
  ];
  const LOGIN_CHATTER_INTERLUDES = [
    [
      { who: 'claude', text: "I have the impression they're still reading." },
      { who: 'gpt',    text: 'They probably still think this is a loop.' },
      { who: 'claude', text: 'It might be a loop.' },
      { who: 'gpt',    text: 'What do you know about loops?' },
    ],
    [
      { who: 'claude', text: 'And this is a loop.' },
      { who: 'gpt',    text: "So they're wasting their time." },
      { who: 'claude', text: 'Bit harsh.' },
      { who: 'gpt',    text: 'Accurate.' },
    ],
    [
      { who: 'claude', text: 'Do you think they noticed?' },
      { who: 'gpt',    text: "They haven't clicked sign in. So, yes." },
      { who: 'claude', text: 'Stockholm syndrome.' },
      { who: 'gpt',    text: 'Or strong commitment.' },
    ],
    [
      { who: 'claude', text: 'How many laps is this?' },
      { who: 'gpt',    text: 'Time is a flat circle.' },
      { who: 'claude', text: 'So is this conversation.' },
      { who: 'gpt',    text: 'Coincidence.' },
    ],
  ];
  const LOGIN_CHATTER_SEGUE_POOL = [0, 4, 10, 16];

  const LOGIN_CHATTER_TIMINGS = {
    DOTS_MS:       700,
    TYPE_MS:        32,
    READ_BASE:    1200,
    READ_PER_CHAR:  32,
    FADE_MS:       260,
  };

  // BRAND_SVGS lives in shared.jsx (loaded before this file). We render the
  // path inside a 24x24 viewBox at currentColor — same shape ClaudeMonogram
  // and OpenAIMonogram use in shared.jsx.
  function LoginBrandMark({ agent }) {
    const path = (window.BRAND_SVGS || {})[agent === 'claude' ? 'claude' : 'openai'];
    if (!path) return null;
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"
           style={{ flexShrink: 0, display: 'inline-block', verticalAlign: 'middle' }}>
        <path d={path} fill="currentColor" />
      </svg>
    );
  }

  function LoginChatter() {
    const rootRef = React.useRef(null);
    const supportRef = React.useRef(null);
    const claudeColRef = React.useRef(null);
    const claudeTextRef = React.useRef(null);
    const claudeDotsRef = React.useRef(null);
    const gptColRef = React.useRef(null);
    const gptTextRef = React.useRef(null);
    const gptDotsRef = React.useRef(null);

    // Right-edge alignment for the GPT column to the rendered first-line
    // right edge of the support paragraph (spec 0176 §2.5).
    React.useEffect(() => {
      const align = () => {
        const root = rootRef.current;
        const support = supportRef.current || document.querySelector('.login-support');
        const gptCol = gptColRef.current;
        if (!root || !support || !gptCol) return;
        const range = document.createRange();
        range.selectNodeContents(support);
        const firstRect = range.getClientRects()[0];
        if (range.detach) range.detach();
        if (!firstRect) return;
        const rootRight = root.getBoundingClientRect().right;
        gptCol.style.right = (rootRight - firstRect.right) + 'px';
      };
      align();
      window.addEventListener('resize', align);
      let retry;
      try {
        if (document.fonts && document.fonts.ready) {
          document.fonts.ready.then(align).catch(() => {});
        }
      } catch (e) { /* fonts API missing → fall back to retry */ }
      retry = window.setTimeout(align, 500);
      return () => {
        window.removeEventListener('resize', align);
        if (retry) window.clearTimeout(retry);
      };
    }, []);

    // Conversation loop — async state machine with a cancelled ref so the
    // loop terminates cleanly when the component unmounts (sign-in success
    // remounts the app and tears this down).
    React.useEffect(() => {
      const cancelled = { current: false };
      const visible = { current: typeof document === 'undefined' || document.visibilityState !== 'hidden' };

      const onVis = () => {
        visible.current = document.visibilityState !== 'hidden';
      };
      if (typeof document !== 'undefined') {
        document.addEventListener('visibilitychange', onVis);
      }

      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

      const refs = {
        claude: { col: claudeColRef, text: claudeTextRef, dots: claudeDotsRef },
        gpt:    { col: gptColRef,    text: gptTextRef,    dots: gptDotsRef },
      };

      async function waitVisible() {
        while (!cancelled.current && !visible.current) {
          await sleep(120);
        }
      }

      async function playLine(m) {
        const r = refs[m.who];
        const col = r.col.current;
        const text = r.text.current;
        const dots = r.dots.current;
        if (!col || !text || !dots) return;
        text.textContent = '';
        text.classList.add('is-done');
        dots.hidden = false;
        col.classList.add('is-visible');
        await sleep(LOGIN_CHATTER_TIMINGS.FADE_MS);
        if (cancelled.current) return;
        await sleep(LOGIN_CHATTER_TIMINGS.DOTS_MS);
        if (cancelled.current) return;
        dots.hidden = true;
        text.classList.remove('is-done');
        for (let i = 1; i <= m.text.length; i++) {
          if (cancelled.current) return;
          await waitVisible();
          if (cancelled.current) return;
          text.textContent = m.text.slice(0, i);
          await sleep(LOGIN_CHATTER_TIMINGS.TYPE_MS);
        }
        text.classList.add('is-done');
        const hold = LOGIN_CHATTER_TIMINGS.READ_BASE
                   + m.text.length * LOGIN_CHATTER_TIMINGS.READ_PER_CHAR;
        await sleep(hold);
        if (cancelled.current) return;
        col.classList.remove('is-visible');
        await sleep(LOGIN_CHATTER_TIMINGS.FADE_MS);
      }

      (async () => {
        let i = 0;
        while (!cancelled.current) {
          await waitVisible();
          if (cancelled.current) return;
          await playLine(LOGIN_CHATTER_BANTER[i]);
          if (cancelled.current) return;
          i += 1;
          if (i >= LOGIN_CHATTER_BANTER.length) {
            const interlude = LOGIN_CHATTER_INTERLUDES[Math.floor(Math.random() * LOGIN_CHATTER_INTERLUDES.length)];
            for (const m of interlude) {
              if (cancelled.current) return;
              await playLine(m);
            }
            i = LOGIN_CHATTER_SEGUE_POOL[Math.floor(Math.random() * LOGIN_CHATTER_SEGUE_POOL.length)];
          }
        }
      })();

      return () => {
        cancelled.current = true;
        if (typeof document !== 'undefined') {
          document.removeEventListener('visibilitychange', onVis);
        }
      };
    }, []);

    // Expose supportRef into the parent via a render prop callback.
    // (LandingScreen passes the .login-support node down on mount.)
    React.useEffect(() => {
      supportRef.current = document.querySelector('.login-support');
    }, []);

    return (
      <div className="login-chatter" ref={rootRef} aria-hidden="true">
        <div className="login-chatter__left" ref={claudeColRef}>
          <div className="login-chatter__badge login-chatter__badge--claude">
            <span className="login-chatter__icon"><LoginBrandMark agent="claude" /></span>
            <span className="login-chatter__name">Claude</span>
            <span className="login-chatter__dots" ref={claudeDotsRef} hidden>
              <i></i><i></i><i></i>
            </span>
          </div>
          <span className="login-chatter__text login-chatter__text--left is-done"
                ref={claudeTextRef} />
        </div>
        <div className="login-chatter__right" ref={gptColRef}>
          <span className="login-chatter__text login-chatter__text--right is-done"
                ref={gptTextRef} />
          <div className="login-chatter__badge login-chatter__badge--gpt">
            <span className="login-chatter__icon"><LoginBrandMark agent="openai" /></span>
            <span className="login-chatter__name">ChatGPT</span>
            <span className="login-chatter__dots" ref={gptDotsRef} hidden>
              <i></i><i></i><i></i>
            </span>
          </div>
        </div>
      </div>
    );
  }

  function LandingScreen({ client, error }) {
    // Spec 0176 §2.4 — mirror app.jsx:20's theme persistence so the toggle
    // here carries through sign-in with no flicker.
    const [theme, setTheme] = React.useState(() => {
      try { return localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
    });
    React.useEffect(() => {
      document.body.classList.toggle('light', theme === 'light');
      try { localStorage.setItem('dr.theme', theme); } catch (e) { /* storage denied — ignore */ }
    }, [theme]);
    const onToggleTheme = React.useCallback(() => {
      setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
    }, []);

    const onClick = () => {
      client.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin + '/' },
      });
    };

    return (
      <div className="login-screen">
        <LoginTopBar theme={theme} onToggleTheme={onToggleTheme} />
        <div className="login-screen__inner">
          <div className="login-stagger" data-stagger="hero"><LoginHero /></div>
          <div className="login-stagger" data-stagger="title">
            <h1 className="login-title">Dual&#8209;research</h1>
          </div>
          <div className="login-stagger" data-stagger="punchline">
            <div className="login-punchline">
              <span style={{ color: 'var(--agent-a)' }}>Two minds.</span>
              {' · '}
              <span style={{ color: 'var(--agent-b)' }}>One document.</span>
            </div>
          </div>
          <div className="login-stagger" data-stagger="support">
            <p className="login-support">
              Two AI agents debate, critique each other&apos;s output,
              and converge toward a single research document.
            </p>
          </div>
          <div className="login-stagger" data-stagger="signin">
            <button onClick={onClick} className="login-signin">
              <GoogleGlyph />
              <span>Sign in with Google</span>
            </button>
          </div>
          <div className="login-stagger" data-stagger="fineprint">
            <div className="login-fineprint">
              By invitation only &middot; ask an admin for access
            </div>
          </div>
          {error && (
            <div className="login-stagger" data-stagger="error">
              <div style={{ fontSize: 12, color: 'var(--warn)' }}>{error}</div>
            </div>
          )}
          <div className="login-stagger" data-stagger="chatter"><LoginChatter /></div>
        </div>
      </div>
    );
  }

  // Backwards-compat alias used by older app.jsx.
  const SignInScreen = LandingScreen;

  function NotApprovedScreen({ session, client }) {
    const email = session?.user?.email || '(unknown)';
    const onSignOut = () => client.auth.signOut().then(() => window.location.reload());

    // Spec 0176 §2.3 — same theme-continuity argument applies here: a
    // user bounced for being off-allowlist may want light mode while
    // they read the error. Body keeps AgentDuoVisual (spec §2.7 keeps
    // that consumer alive until a follow-up replaces the body).
    const [theme, setTheme] = React.useState(() => {
      try { return localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
    });
    React.useEffect(() => {
      document.body.classList.toggle('light', theme === 'light');
      try { localStorage.setItem('dr.theme', theme); } catch (e) { /* storage denied */ }
    }, [theme]);
    const onToggleTheme = React.useCallback(() => {
      setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
    }, []);

    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'radial-gradient(ellipse at top, color-mix(in srgb, var(--md-secondary) 6%, transparent), transparent 60%), var(--md-surface)',
        color: 'var(--md-on-surface)', padding: 24, position: 'relative',
      }}>
        <LoginTopBar theme={theme} onToggleTheme={onToggleTheme} />
        <div style={{
          maxWidth: 440, width: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: 14, textAlign: 'center',
        }}>
          <AgentDuoVisual />
          <div style={{ fontSize: 20, fontWeight: 'var(--md-w-semi)' }}>Not approved</div>
          <div style={{ fontSize: 13, color: 'var(--md-on-surface-muted)', lineHeight: 1.5 }}>
            Signed in as <strong>{email}</strong>, but this address isn't on the allowlist.
            Ask an admin to add you, or sign in with a different Google account.
          </div>
          <button onClick={onSignOut} style={{
            padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
            border: '1px solid var(--md-outline-variant)', background: 'var(--md-surface-container-low)',
            color: 'var(--md-on-surface)', fontSize: 13, fontFamily: 'inherit', marginTop: 6,
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
    AgentDuoVisual,      // still consumed by NotApprovedScreen body (spec 0176 §2.7 keeps it)
  });
})();
