// app.jsx — top-level router + theme toggle, wired to the live API.
//
// View selection follows the URL hash (router.jsx):
//   #/                   list view (default)
//   #/runs/<run_id>      detail view for one run
//   #/language           design language reference
//
// The top chrome has one primary tab (All runs) and three sibling controls
// on the right (connection state, theme toggle, design-language button).
// The Run-detail view is reachable only by clicking a row; the detail
// view has its own `← All runs` back chip (rendered by run-detail.jsx).
//
// SPEC-0059: Global keyboard contract (A11Y-03/04).
// `?` → shortcuts overlay, `Cmd+K` → search palette, `/` → run-list search.
// Input/textarea/contentEditable exempt from single-key bindings.

function App() {
  const { route, navigate } = useRoute();
  const [theme, setTheme] = React.useState(() => {
    try { return localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
  });
  React.useEffect(() => {
    document.body.classList.toggle('light', theme === 'light');
    try { localStorage.setItem('dr.theme', theme); } catch (e) {}
  }, [theme]);

  // Auth gate (spec 0021). In fs mode (`hostedMode === false`) the client is
  // null, useSession resolves immediately, and we skip both screens.
  const { client, ready: clientReady, hostedMode } = useSupabaseClient();
  const { session, ready: sessionReady } = useSession(client);
  const [notApproved, setNotApproved] = React.useState(false);
  const me = useMe();  // null until first /api/me resolves

  // SPEC-0061: onboarding gate for first-time users.
  const [showOnboarding, setShowOnboarding] = React.useState(() => {
    // Check for reset param.
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('reset_onboarding') === '1') {
        localStorage.removeItem('dr_onboarded');
        // Clean the URL.
        const url = new URL(window.location);
        url.searchParams.delete('reset_onboarding');
        window.history.replaceState({}, '', url.toString());
      }
    } catch (e) {}
    try { return localStorage.getItem('dr_onboarded') !== 'true'; } catch (e) { return false; }
  });

  // SPEC-0059: overlay state for keyboard-accessible chrome surfaces.
  const [shortcutsOpen, setShortcutsOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);

  // SPEC-0102: How It Works overlay state. Deep link via ?how=1.
  const [howOpen, setHowOpen] = React.useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get('how') === '1';
    } catch (e) { return false; }
  });
  const closeHow = React.useCallback(() => {
    setHowOpen(false);
    try {
      const url = new URL(window.location);
      url.searchParams.delete('how');
      window.history.replaceState({}, '', url.toString());
    } catch (e) {}
  }, []);
  const openHow = React.useCallback(() => {
    setHowOpen(true);
  }, []);

  // SPEC-0059: Global keyboard contract (A11Y-03/04).
  React.useEffect(() => {
    const onKey = (e) => {
      const tag = (e.target.tagName || '').toUpperCase();
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;

      // Cmd+K / Ctrl+K — always fires, even when typing.
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
        return;
      }

      // All other single-key bindings are exempt when typing.
      if (isTyping) return;

      // Don't intercept when a modal/dialog is open (let per-modal handlers work).
      if (document.querySelector('[role="dialog"]')) return;

      if (e.key === '?') {
        e.preventDefault();
        setShortcutsOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Listen for the global "not-approved" event that authedFetch raises when
  // the server returns 403. Any /api call can trigger this; we swap to the
  // not-approved screen until the user signs out.
  React.useEffect(() => {
    function onForbid() { setNotApproved(true); }
    window.addEventListener('dr-not-approved', onForbid);
    return () => window.removeEventListener('dr-not-approved', onForbid);
  }, []);

  if (hostedMode && (!clientReady || !sessionReady)) {
    // Spec 0084 — unified loading visual at app boot.
    return <LoadingState size="page" label="Connecting to the server" />;
  }
  if (hostedMode && !session) {
    return <LandingScreen client={client} />;
  }
  if (hostedMode && notApproved) {
    return <NotApprovedScreen session={session} client={client} />;
  }

  // SPEC-0061: show onboarding for first-time users (after auth resolves).
  if (showOnboarding && hostedMode && session) {
    return <OnboardingScreen onComplete={() => setShowOnboarding(false)} />;
  }

  return (
    <div style={{ height: '100vh', overflow: 'hidden', background: 'var(--bg-0)' }}>
      <ChromeBar route={route} navigate={navigate}
                 theme={theme}
                 onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                 client={client} session={session} me={me}
                 onOpenHow={openHow} />

      <div style={{ height: 'calc(100vh - 44px)', overflow: 'hidden' }}>
        {route.view === 'detail'        && <DetailScreen runId={route.runId} navigate={navigate} />}
        {route.view === 'list'          && <ListScreen navigate={navigate} />}
        {route.view === 'language'      && <DesignLanguageView />}
        {route.view === 'settings'      && <SettingsScreen me={me} />}
        {route.view === 'how-it-works'  && <HowItWorksPage />}
        {route.view === 'compare'       && <CompareScreen navigate={navigate} />}
        {route.view === 'search'        && <CrossRunSearchScreen navigate={navigate} />}
      </div>

      {/* SPEC-0059: keyboard-accessible overlays */}
      <ShortcutsOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <SearchPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {/* SPEC-0102: How It Works overlay */}
      <HowItWorks open={howOpen} onClose={closeHow} />
    </div>
  );
}

// ─────────────────── Detail screen ───────────────────

function DetailScreen({ runId, navigate }) {
  React.useEffect(() => { setActiveRunId(runId); }, [runId]);
  const { run, connected, error } = useLiveRun(runId);

  React.useEffect(() => {
    window.__lastSseConnected = connected;
    return () => { window.__lastSseConnected = false; };
  }, [connected]);

  if (error) {
    return (
      <FullPageMessage
        title="Could not load run"
        body={`runId=${runId}\n${error}`}
        onBack={() => navigate('list')}
      />
    );
  }
  if (!run) {
    // Spec 0084 — the run-detail page-level loading state. Hint shows
    // the run id so the user can still confirm which run is loading.
    return <LoadingState size="page" label="Loading run" hint={runId} />;
  }
  return (
    <RunContext.Provider value={{ runId, connected, navigate }}>
      <RunDetail run={run} />
    </RunContext.Provider>
  );
}

// ─────────────────── List screen ───────────────────

function ListScreen({ navigate }) {
  const { rows, connected, loading } = useRunList();
  React.useEffect(() => {
    window.__lastSseConnected = connected;
  }, [connected]);
  return (
    <RunListView
      runs={rows}
      loading={loading}
      onSelect={(r) => navigate('detail', r.id)}
    />
  );
}

// ─────────────────── Top chrome ───────────────────

function ChromeBar({ route, navigate, theme, onToggleTheme, client, session, me, onOpenHow }) {
  const onList = route.view === 'list';
  return (
    <div style={{
      // SPEC-0087 § B — chrome strip kept at 44px tall but tabs now
      // sit centered (no longer flush against the top edge of the
      // viewport). Adds the breathing-room the user flagged at 13.07.
      height: 44,
      background: 'var(--bg-0)',
      borderBottom: '1px solid var(--border-1)',
      display: 'flex', alignItems: 'center',
      paddingLeft: 8,
      gap: 4,
    }}>
      <Tab
        active={onList}
        onClick={() => navigate('list')}
        icon={route.view === 'detail' ? 'arrow-left' : 'menu'}
        size="sm"
        className="tab-chrome"
      >
        All runs
      </Tab>
      <Tab
        active={route.view === 'compare'}
        onClick={() => navigate('compare')}
        icon="compare"
        size="sm"
        className="tab-chrome"
      >
        Compare
      </Tab>
      <Tab
        active={route.view === 'search'}
        onClick={() => navigate('search')}
        icon="magnify"
        size="sm"
        className="tab-chrome"
      >
        Search
      </Tab>
      <div style={{ flex: 1 }} />
      <RightCluster
        theme={theme}
        onToggleTheme={onToggleTheme}
        navigate={navigate}
        route={route}
        client={client}
        session={session}
        me={me}
        onOpenHow={onOpenHow}
      />
    </div>
  );
}

function ChromeTab({ label, icon, active, onClick }) {
  const Ico = icon;
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '0 16px',
      background: active ? 'var(--bg-1)' : 'transparent',
      color: active ? 'var(--fg-0)' : 'var(--fg-2)',
      fontSize: 12.5,
      borderRight: '1px solid var(--border-1)',
      borderTop: active ? '1px solid var(--border-1)' : '1px solid transparent',
      borderLeft: active ? '1px solid var(--border-1)' : '1px solid transparent',
      position: 'relative',
    }}>
      <Ico style={{ color: active ? 'var(--fg-1)' : 'var(--fg-3)' }} />
      <span>{label}</span>
      {active && (
        <span style={{
          position: 'absolute', bottom: -1, left: 0, right: 0,
          height: 1, background: 'var(--bg-1)',
        }} />
      )}
    </button>
  );
}

// ─────────────────── Right cluster — unified chrome controls ───────────────────
// Spec 0056 SUR-05: unified visual styling across all chrome-right controls.
// SUR-06: ActiveRunChip — shows short run ID when viewing a run detail.

function RightCluster({ theme, onToggleTheme, navigate, route, client, session, me, onOpenHow }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', height: 40 }}>
      <ConnectionPill />
      <AppVersionChip />
      <span className="vbar" style={{ margin: '0 4px' }} />
      <button
        type="button"
        className="md-btn md-btn--text md-btn--sm"
        onClick={onOpenHow}
      >
        How it works
      </button>
      <span className="vbar" style={{ margin: '0 4px' }} />
      <div style={{ display: 'flex', alignItems: 'center', padding: '0 10px' }}>
        <ThemeToggleSegmented theme={theme} onToggle={onToggleTheme} />
      </div>
      {session
        ? <AvatarMenu navigate={navigate} route={route}
                      client={client} session={session} me={me} />
        : <DesignLanguageButton onClick={() => navigate('language')}
                                active={route.view === 'language'} />}
    </div>
  );
}

// Spec 0056 SUR-06: ActiveRunChip — pill showing the short run ID in the
// chrome bar when viewing a run detail. Click navigates back to run list.
function ActiveRunChip({ runId, onClick }) {
  const shortId = window.splitRunId ? window.splitRunId(runId).id : runId.slice(0, 4);
  return (
    <button
      type="button"
      onClick={onClick}
      title={`Back to run list (viewing ${shortId})`}
      className="rid rid-sm"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '0 12px',
        borderLeft: '1px solid var(--border-1)',
        background: 'transparent',
        cursor: 'pointer',
        border: 'none', borderLeftWidth: 1, borderLeftStyle: 'solid',
        borderLeftColor: 'var(--border-1)',
        fontFamily: 'var(--mono)', fontSize: 11,
        color: 'var(--fg-1)',
      }}
    >
      <Mdi name="arrow-left" size={12} />
      <span>{shortId}</span>
    </button>
  );
}

// Spec 0035: tiny pill in the chrome's right cluster showing the deployed
// version. Click -> how-it-works page (where the VERSION_NOTES live).
// SPEC-0069: restyled to use the Chip primitive for design-system cohesion.
function AppVersionChip() {
  const meta = window.useAppMeta ? window.useAppMeta() : null;
  if (!meta?.version) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', height: 40, padding: '0 8px' }}>
      <Chip title={`dual-research v${meta.version}`}
            style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>
        v{meta.version}
      </Chip>
    </div>
  );
}

// HowItWorksLink removed in spec 0056 — replaced by Tab primitive in RightCluster.

// ─────────────────── Avatar dropdown ───────────────────

function AvatarMenu({ navigate, route, client, session, me }) {
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef(null);
  const email = me?.email || session?.user?.email || '';
  const avatarUrl = me?.avatarUrl || session?.user?.user_metadata?.avatar_url || null;
  const fullName = me?.fullName || session?.user?.user_metadata?.full_name || email;

  React.useEffect(() => {
    if (!open) return;
    function onDown(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false);
    }
    function onEsc(e) { if (e.key === 'Escape') setOpen(false); }
    window.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onEsc);
    return () => {
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const onSignOut = async () => {
    setOpen(false);
    try { await client.auth.signOut(); } catch (e) { /* noop */ }
    window.location.replace('/');
  };

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'flex', alignItems: 'center',
                                 borderLeft: '1px solid var(--border-1)', padding: '0 10px' }}>
      <button onClick={() => setOpen(v => !v)}
              title={email}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 0,
                background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
              }}>
        <AvatarDisc email={email} url={avatarUrl} size={28} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 42, right: 8, minWidth: 220,
          background: 'var(--bg-1)', border: '1px solid var(--border-2)',
          borderRadius: 8, padding: 6, zIndex: 50,
          boxShadow: '0 8px 28px rgba(0,0,0,0.45)',
        }}>
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-1)', marginBottom: 4 }}>
            <div style={{ fontSize: 13, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.2 }}>
              {fullName}
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-2)', marginTop: 2 }}>
              {email}
              {me?.isAdmin && (
                <span style={{
                  marginLeft: 6, padding: '0 6px', borderRadius: 999,
                  background: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)',
                  fontSize: 10, border: '1px solid var(--agent-b-border)',
                }}>admin</span>
              )}
            </div>
          </div>
          <MenuItem onClick={() => { setOpen(false); navigate('language'); }}
                    icon={Icon.Palette} label="Design language" active={route.view === 'language'} />
          {me?.isAdmin && (
            <MenuItem onClick={() => { setOpen(false); navigate('settings'); }}
                      icon={Icon.Gear} label="Settings" active={route.view === 'settings'} />
          )}
          <div style={{ height: 1, background: 'var(--border-1)', margin: '4px 0' }} />
          <MenuItem onClick={onSignOut} icon={Icon.SignOut} label="Sign out" />
        </div>
      )}
    </div>
  );
}

function MenuItem({ onClick, icon, label, active }) {
  const Ico = icon;
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 10, width: '100%',
      padding: '8px 10px', borderRadius: 6, cursor: 'pointer',
      border: 'none', background: active ? 'var(--bg-2)' : 'transparent',
      color: 'var(--fg-0)', fontFamily: 'inherit', fontSize: 13,
      textAlign: 'left',
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--bg-2)'; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}>
      {Ico && <Ico style={{ color: 'var(--fg-2)' }} />}
      <span>{label}</span>
    </button>
  );
}

function AvatarDisc({ email, url, size = 28 }) {
  const initials = (email || '?').slice(0, 1).toUpperCase();
  // Deterministic hue from email so the fallback feels intentional.
  let hash = 0;
  for (const c of email || '') hash = (hash * 31 + c.charCodeAt(0)) & 0xffffffff;
  const hue = Math.abs(hash) % 360;
  if (url) {
    return (
      <img src={url} alt={email}
           referrerPolicy="no-referrer"
           style={{
             width: size, height: size, borderRadius: '50%',
             border: '1px solid var(--border-2)', objectFit: 'cover',
             display: 'block',
           }} />
    );
  }
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `hsl(${hue}, 55%, 38%)`,
      color: 'white', display: 'inline-flex',
      alignItems: 'center', justifyContent: 'center',
      fontSize: Math.round(size * 0.42), fontWeight: 600,
      border: '1px solid var(--border-2)',
    }}>{initials}</div>
  );
}

function ConnectionPill() {
  const [connected, setConnected] = React.useState(false);
  React.useEffect(() => {
    const id = setInterval(() => setConnected(!!window.__lastSseConnected), 500);
    return () => clearInterval(id);
  }, []);
  return (
    <div title={connected ? 'Connected to /api stream' : 'Idle — no active stream'}
         style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '0 12px',
      borderLeft: '1px solid var(--border-1)',
    }}>
      <Dot color={connected ? COLORS.info : COLORS.idle}
           pulse={connected ? 'pulse-a' : null} size={6} />
      <span style={{ fontSize: 11, color: connected ? 'var(--fg-1)' : 'var(--fg-3)', fontFamily: 'var(--mono)' }}>
        {connected ? 'connected' : 'idle'}
      </span>
    </div>
  );
}

// Compact single-pill theme toggle (spec 0024). One container, two icon
// buttons side by side; the active one is highlighted, clicking the inactive
// one flips the theme. Half the horizontal space of the previous segmented
// toggle.
function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark';
  const goLight = () => { if (isDark) onToggle(); };
  const goDark  = () => { if (!isDark) onToggle(); };
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      borderLeft: '1px solid var(--border-1)',
      padding: '0 10px',
    }}>
      <div role="group" aria-label="Theme"
           style={{
             display: 'inline-flex', alignItems: 'center',
             background: 'var(--bg-2)',
             border: '1px solid var(--border-1)',
             borderRadius: 999,
             padding: 2,
             height: 26,
           }}>
        <ThemeIconBtn active={!isDark} onClick={goLight} label="Switch to light theme">
          <SunIcon />
        </ThemeIconBtn>
        <ThemeIconBtn active={isDark} onClick={goDark} label="Switch to dark theme">
          <MoonIcon />
        </ThemeIconBtn>
      </div>
    </div>
  );
}

function ThemeIconBtn({ active, onClick, label, children }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      title={label}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 24, height: 22,
        background: active ? 'var(--bg-0)' : 'transparent',
        color: active ? 'var(--fg-0)' : 'var(--fg-3)',
        border: active ? '1px solid var(--border-1)' : '1px solid transparent',
        borderRadius: 999,
        cursor: active ? 'default' : 'pointer',
        padding: 0, fontFamily: 'inherit',
      }}>
      {children}
    </button>
  );
}

function SunIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
         stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="2.8"/>
      <path d="M8 1.5v1.4M8 13.1v1.4M1.5 8h1.4M13.1 8h1.4M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
         stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.5 9.5A6 6 0 1 1 6.5 2.5 5 5 0 0 0 13.5 9.5Z"/>
    </svg>
  );
}

function DesignLanguageButton({ onClick, active }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', borderLeft: '1px solid var(--border-1)', padding: '0 4px' }}>
      <Tab active={active} onClick={onClick} icon="palette" size="sm">Design</Tab>
    </div>
  );
}

// ─────────────────── Full-page message helper ───────────────────

function FullPageMessage({ title, body, onBack }) {
  return (
    <div style={{
      height: '100%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexDirection: 'column', gap: 16,
      color: 'var(--fg-2)', background: 'var(--bg-0)',
    }}>
      <div style={{ fontSize: 16, color: 'var(--fg-0)' }}>{title}</div>
      <pre className="mono" style={{
        fontSize: 11, color: 'var(--fg-3)',
        background: 'var(--bg-1)', padding: '8px 12px',
        border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)',
        whiteSpace: 'pre-wrap', maxWidth: 600,
      }}>{body}</pre>
      {onBack && (
        <button onClick={onBack} style={{
          padding: '6px 14px', fontSize: 12,
          background: 'var(--bg-2)', color: 'var(--fg-1)',
          border: '1px solid var(--border-2)',
          borderRadius: 'var(--r-2)',
        }}>← Back to runs</button>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
