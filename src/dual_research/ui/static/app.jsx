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

  // SPEC-0103: 8-step tour overlay (replaces SPEC-0061 3-screen modal).
  const [tourOpen, setTourOpen] = React.useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('reset_onboarding') === '1') {
        localStorage.removeItem('dr_onboarded');
        localStorage.removeItem('dr_tour_step');
        const url = new URL(window.location);
        url.searchParams.delete('reset_onboarding');
        window.history.replaceState({}, '', url.toString());
        return true;
      }
    } catch (e) {}
    try { return localStorage.getItem('dr_onboarded') !== 'true'; } catch (e) { return false; }
  });
  const [tourStep, setTourStep] = React.useState(() => {
    try {
      const saved = parseInt(localStorage.getItem('dr_tour_step'), 10);
      return (saved > 0 && saved <= 8) ? saved : 1;
    } catch (e) { return 1; }
  });
  const tourAdvance = React.useCallback(() => {
    const next = tourStep + 1;
    setTourStep(next);
    try { localStorage.setItem('dr_tour_step', String(next)); } catch (e) {}
  }, [tourStep]);
  const tourBack = React.useCallback(() => {
    const prev = Math.max(1, tourStep - 1);
    setTourStep(prev);
    try { localStorage.setItem('dr_tour_step', String(prev)); } catch (e) {}
  }, [tourStep]);
  const tourClose = React.useCallback(() => {
    setTourOpen(false);
    try {
      localStorage.setItem('dr_onboarded', 'true');
      localStorage.removeItem('dr_tour_step');
    } catch (e) {}
  }, []);

  // SPEC-0059: overlay state for keyboard-accessible chrome surfaces.
  const [shortcutsOpen, setShortcutsOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);

  // SPEC-0123: How-It-Works is now a full-page route (#/how-it-works),
  // not a modal. The pre-0123 howOpen / openHow / closeHow state +
  // the ?how=1 deep-link query param were retired here.

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

  // Replay the SPEC-0103 onboarding tour on demand (avatar menu → "Replay tour").
  // Mirrors the ?reset_onboarding=1 path but without a page reload.
  React.useEffect(() => {
    function onReplay() {
      try {
        localStorage.removeItem('dr_onboarded');
        localStorage.removeItem('dr_tour_step');
      } catch (e) {}
      setTourStep(1);
      setTourOpen(true);
    }
    window.addEventListener('dr-replay-tour', onReplay);
    return () => window.removeEventListener('dr-replay-tour', onReplay);
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

  // SPEC-0103: tour opens for first-time users but does NOT replace the app shell.
  // The overlay is mounted as a sibling below, not as a gate.

  return (
    <div style={{ height: '100vh', overflow: 'hidden', background: 'var(--md-surface)' }}>
      <a className="skip-link" href="#main">Skip to main content</a>
      <ChromeBar route={route} navigate={navigate}
                 theme={theme}
                 onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                 client={client} session={session} me={me} />

      <div id="main" style={{ height: 'calc(100vh - 44px)', overflow: 'hidden' }}>
        {route.view === 'detail'        && <DetailScreen runId={route.runId} navigate={navigate} />}
        {route.view === 'list'          && <ListScreen navigate={navigate} />}
        {route.view === 'language'      && <DesignLanguageView />}
        {route.view === 'settings'      && <SettingsScreen me={me} />}
        {route.view === 'how-it-works'  && <HowItWorksPage />}
        {route.view === 'compare'       && <CompareScreen navigate={navigate} />}
        {route.view === 'search'        && <CrossRunSearchScreen navigate={navigate} />}
        {/* Spec 0125: 'admin-users' route folded into '/settings' (Users sub-tab). */}
      </div>

      {/* SPEC-0059: keyboard-accessible overlays */}
      <ShortcutsOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <SearchPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {/* SPEC-0123: How It Works is now a full-page route mounted above. */}
      {/* SPEC-0103: 8-step onboarding tour overlay */}
      {tourOpen && (
        <TourOverlay
          open={tourOpen}
          step={tourStep}
          onClose={tourClose}
          onAdvance={tourAdvance}
          onBack={tourBack}
          navigate={navigate}
        />
      )}
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

function ChromeBar({ route, navigate, theme, onToggleTheme, client, session, me }) {
  const onList = route.view === 'list';
  return (
    <header className="md-appbar">
      <Tab
        active={onList}
        onClick={() => navigate('list')}
        icon={route.view === 'detail' ? 'arrow-left' : 'menu'}
        variant="chrome"
      >
        All runs
      </Tab>
      <Tab
        active={route.view === 'compare'}
        onClick={() => navigate('compare')}
        icon="compare"
        variant="chrome"
      >
        Compare
      </Tab>
      <Tab
        active={route.view === 'search'}
        onClick={() => navigate('search')}
        icon="magnify"
        variant="chrome"
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
      />
    </header>
  );
}

function ChromeTab({ label, icon, active, onClick }) {
  const Ico = icon;
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '0 16px',
      background: active ? 'var(--md-surface-container-low)' : 'transparent',
      color: active ? 'var(--md-on-surface)' : 'var(--md-on-surface-muted)',
      fontSize: 12.5,
      borderRight: '1px solid var(--md-outline-hair)',
      borderTop: active ? '1px solid var(--md-outline-hair)' : '1px solid transparent',
      borderLeft: active ? '1px solid var(--md-outline-hair)' : '1px solid transparent',
      position: 'relative',
    }}>
      <Ico style={{ color: active ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-faint)' }} />
      <span>{label}</span>
      {active && (
        <span style={{
          position: 'absolute', bottom: -1, left: 0, right: 0,
          height: 1, background: 'var(--md-surface-container-low)',
        }} />
      )}
    </button>
  );
}

// ─────────────────── Right cluster — unified chrome controls ───────────────────
// Spec 0056 SUR-05: unified visual styling across all chrome-right controls.
// SUR-06: ActiveRunChip — shows short run ID when viewing a run detail.

function RightCluster({ theme, onToggleTheme, navigate, route, client, session, me }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', height: 40 }}>
      <ConnectionPill />
      <AppVersionChip />
      <span className="vbar" style={{ margin: '0 4px' }} />
      <button
        type="button"
        className={'md-btn md-btn--text md-btn--sm' + (route.view === 'how-it-works' ? ' is-active' : '')}
        onClick={() => navigate('how-it-works')}
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
        borderLeft: '1px solid var(--md-outline-hair)',
        background: 'transparent',
        cursor: 'pointer',
        border: 'none', borderLeftWidth: 1, borderLeftStyle: 'solid',
        borderLeftColor: 'var(--md-outline-hair)',
        fontFamily: 'var(--md-font-data)', fontSize: 11,
        color: 'var(--md-on-surface-variant)',
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
            style={{ fontFamily: 'var(--md-font-data)', fontSize: 10 }}>
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
                                 borderLeft: '1px solid var(--md-outline-hair)', padding: '0 10px' }}>
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
          background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-variant)',
          borderRadius: 8, padding: 6, zIndex: 50,
          boxShadow: '0 8px 28px rgba(0,0,0,0.45)',
        }}>
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--md-outline-hair)', marginBottom: 4 }}>
            <div style={{ fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 500, lineHeight: 1.2 }}>
              {fullName}
            </div>
            <div style={{ fontSize: 11, color: 'var(--md-on-surface-muted)', marginTop: 2 }}>
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
          <MenuItem onClick={() => {
                      setOpen(false);
                      try { window.dispatchEvent(new Event('dr-replay-tour')); } catch (e) {}
                    }}
                    icon={Icon.Help} label="Replay tour" />
          {me?.isAdmin && (
            <MenuItem onClick={() => { setOpen(false); navigate('settings'); }}
                      icon={Icon.Gear} label="Settings" active={route.view === 'settings'} />
          )}
          <div style={{ height: 1, background: 'var(--md-outline-hair)', margin: '4px 0' }} />
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
      border: 'none', background: active ? 'var(--md-surface-container)' : 'transparent',
      color: 'var(--md-on-surface)', fontFamily: 'inherit', fontSize: 13,
      textAlign: 'left',
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--md-surface-container)'; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}>
      {Ico && <Ico style={{ color: 'var(--md-on-surface-muted)' }} />}
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
             border: '1px solid var(--md-outline-variant)', objectFit: 'cover',
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
      fontSize: Math.round(size * 0.42), fontWeight: 'var(--md-w-semi)',
      border: '1px solid var(--md-outline-variant)',
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
      borderLeft: '1px solid var(--md-outline-hair)',
    }}>
      <Dot color={connected ? COLORS.info : COLORS.idle}
           pulse={connected ? 'pulse-a' : null} size={6} />
      <span style={{ fontSize: 11, color: connected ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-faint)', fontFamily: 'var(--md-font-data)' }}>
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
      borderLeft: '1px solid var(--md-outline-hair)',
      padding: '0 10px',
    }}>
      <div role="group" aria-label="Theme"
           style={{
             display: 'inline-flex', alignItems: 'center',
             background: 'var(--md-surface-container)',
             border: '1px solid var(--md-outline-hair)',
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
        background: active ? 'var(--md-surface)' : 'transparent',
        color: active ? 'var(--md-on-surface)' : 'var(--md-on-surface-faint)',
        border: active ? '1px solid var(--md-outline-hair)' : '1px solid transparent',
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
    <div style={{ display: 'flex', alignItems: 'center', borderLeft: '1px solid var(--md-outline-hair)', padding: '0 4px' }}>
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
      color: 'var(--md-on-surface-muted)', background: 'var(--md-surface)',
    }}>
      <div style={{ fontSize: 16, color: 'var(--md-on-surface)' }}>{title}</div>
      <pre className="mono" style={{
        fontSize: 11, color: 'var(--md-on-surface-faint)',
        background: 'var(--md-surface-container-low)', padding: '8px 12px',
        border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)',
        whiteSpace: 'pre-wrap', maxWidth: 600,
      }}>{body}</pre>
      {onBack && (
        <button onClick={onBack} style={{
          padding: '6px 14px', fontSize: 12,
          background: 'var(--md-surface-container)', color: 'var(--md-on-surface-variant)',
          border: '1px solid var(--md-outline-variant)',
          borderRadius: 'var(--md-shape-sm)',
        }}>← Back to runs</button>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
