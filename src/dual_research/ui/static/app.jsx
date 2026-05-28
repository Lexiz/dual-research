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

// Canonical theme-persistence key (spec 0246.1). Legacy `dr.theme` is read as a
// one-time migration fallback and swept on first effect.
const THEME_KEY = 'dr-theme';

function App() {
  const { route, navigate } = useRoute();
  const [theme, setTheme] = React.useState(() => {
    try { return localStorage.getItem(THEME_KEY) || localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
  });
  React.useEffect(() => {
    document.body.classList.toggle('light', theme === 'light');
    try {
      localStorage.setItem(THEME_KEY, theme);
      localStorage.removeItem('dr.theme');
    } catch (e) {}
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
      {/* Spec 0252 — the All Runs `.ar-chrome` (60 px) is now the single app
          bar for EVERY route. The list route renders its own inside
          `ListScreen` (it owns the SSE `connected` prop + Active/Archived
          toggle); every other route mounts the same chrome here with
          `route={route.view}` driving the active-tab state. The old 44 px
          `.md-appbar` ChromeBar is gone (deleted below). */}
      {route.view !== 'list' && (
        <AllRunsChrome route={route.view} navigate={navigate}
                       me={me} isAdmin={!!(me && me.isAdmin)}
                       theme={theme}
                       onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                       client={client} session={session} />
      )}

      <div id="main" style={route.view === 'list'
            ? { height: '100vh', overflow: 'auto' }
            : { height: 'calc(100vh - 60px)', overflow: 'hidden' }}>
        {route.view === 'detail'        && <DetailScreen runId={route.runId} navigate={navigate} />}
        {route.view === 'list'          && <ListScreen navigate={navigate} theme={theme} onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} client={client} session={session} />}
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
      {/* Spec 0245 — singleton toast host. Listens on the `app-toast`
          window event; any surface can dispatch via the `useToast()` hook. */}
      <ToastHost />
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

function ListScreen({ navigate, theme, onToggleTheme, client, session }) {
  return (
    <AllRunsPage
      onSelect={(r) => navigate('detail', r.id)}
      navigate={navigate}
      theme={theme}
      onToggleTheme={onToggleTheme}
      client={client}
      session={session}
    />
  );
}

// ─────────────────── Top chrome ───────────────────
// Spec 0252 — `ChromeBar` / `ChromeTab` / `RightCluster` / `ConnectionPill`
// / `AppVersionChip` were deleted here: the universal `.ar-chrome`
// (`AllRunsChrome`, run-list.jsx) is now the single app bar for every
// route, so the old 44 px `.md-appbar` chrome and its right-cluster
// children are dead. The connected-pill behaviour ConnectionPill provided
// is folded into `AllRunsChrome`'s `window.__lastSseConnected` poll; the
// version deep-link AppVersionChip provided is the `.ar-pill__v` button.

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

// HowItWorksLink removed in spec 0056 — replaced by Tab primitive in RightCluster.
// AppVersionChip removed in spec 0252 — the `.ar-pill__v` version button in
// `AllRunsChrome` is the universal-chrome equivalent deep-link.

// ─────────────────── Avatar dropdown ───────────────────
// Spec 0248 §2.2 — `AvatarMenu` / `AvatarDisc` / `MenuItem` were lifted
// into run-list.jsx (loaded before app.jsx) so the All Runs `.ar-chrome`
// can mount the same menu. They remain global function declarations, so
// the references in `RightCluster` below resolve unchanged at render time.

// ConnectionPill removed in spec 0252 — `AllRunsChrome`'s connected pill
// polls the same `window.__lastSseConnected` flag on non-list routes.

// Spec 0024's compact dual-icon theme toggle pill (`ThemeToggle`)
// formerly lived here; spec 0176 §2.8 extracted it into
// `theme-toggle.jsx` so the login screen can mount the same primitive
// at the same X coordinate the chrome occupies post-login.
// The chrome's `RightCluster` actually uses `ThemeToggleSegmented`
// (from `shared.jsx`), so nothing in this file references the extracted
// pill — the JSX literal is gone from here on purpose.

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
