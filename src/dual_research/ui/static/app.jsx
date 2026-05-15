// app.jsx — top-level router + theme toggle, wired to the live API.
//
// View selection follows the URL hash (router.jsx):
//   #/                   list view
//   #/runs/<run_id>      detail view for one run
//   #/language           design language reference
//
// Tweaks panel is retained for cosmetic-only knobs (stream speed). The
// "scenario" tweak from the prototype is gone — we have real data now.

function App() {
  const { route, navigate } = useRoute();
  const [theme, setTheme] = React.useState(() => {
    try { return localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
  });
  React.useEffect(() => {
    document.body.classList.toggle('light', theme === 'light');
    try { localStorage.setItem('dr.theme', theme); } catch (e) {}
  }, [theme]);

  return (
    <div style={{ height: '100vh', overflow: 'hidden', background: 'var(--bg-0)' }}>
      <ViewSwitcher route={route} navigate={navigate}
                    theme={theme}
                    onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} />

      <div style={{ height: 'calc(100vh - 36px)', overflow: 'hidden' }}>
        {route.view === 'detail' && <DetailScreen runId={route.runId} navigate={navigate} />}
        {route.view === 'list'   && <ListScreen navigate={navigate} />}
        {route.view === 'language' && <DesignLanguageView />}
      </div>
    </div>
  );
}

// ─────────────────── Detail screen ───────────────────

function DetailScreen({ runId, navigate }) {
  // Stash runId on the module-level so deep components without context access
  // can fetch files. RunContext is the preferred path; this is a fallback.
  React.useEffect(() => { setActiveRunId(runId); }, [runId]);

  const { run, connected, error } = useLiveRun(runId);

  // Bridge SSE connection state to the indicator in the top chrome.
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
    return <FullPageMessage title="Loading run…" body={runId} />;
  }

  return (
    <RunContext.Provider value={{ runId, connected }}>
      <RunDetail run={run} />
    </RunContext.Provider>
  );
}

// ─────────────────── List screen ───────────────────

function ListScreen({ navigate }) {
  const { rows } = useRunList();
  return (
    <RunListView
      runs={rows}
      onSelect={(r) => navigate('detail', r.id)}
    />
  );
}

// ─────────────────── Top chrome ───────────────────

function ViewSwitcher({ route, navigate, theme, onToggleTheme }) {
  const tabs = [
    { id: 'detail',   label: 'Run detail',      icon: Icon.Activity, disabled: !route.runId && route.view !== 'detail' },
    { id: 'list',     label: 'All runs',        icon: Icon.List },
    { id: 'language', label: 'Design language', icon: Icon.Palette },
  ];

  // Detail tab is "active" only when a run is selected; clicking it with
  // no current run sends you to the list.
  return (
    <div style={{
      height: 36, background: 'var(--bg-0)',
      borderBottom: '1px solid var(--border-1)',
      display: 'flex', alignItems: 'stretch', paddingLeft: 8,
    }}>
      {tabs.map(t => {
        const active = route.view === t.id;
        const IconEl = t.icon;
        const onClick = () => {
          if (t.id === 'detail' && !route.runId) {
            // No run selected — go to list (where you can pick one).
            navigate('list');
            return;
          }
          if (t.id === 'detail' && route.runId) {
            navigate('detail', route.runId);
            return;
          }
          navigate(t.id);
        };
        return (
          <button key={t.id} onClick={onClick} style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '0 14px',
            background: active ? 'var(--bg-1)' : 'transparent',
            color: active ? 'var(--fg-0)' : 'var(--fg-2)',
            fontSize: 12,
            borderRight: '1px solid var(--border-1)',
            borderTop: active ? '1px solid var(--border-1)' : '1px solid transparent',
            borderLeft: active ? '1px solid var(--border-1)' : '1px solid transparent',
            position: 'relative',
            opacity: t.disabled ? 0.5 : 1,
          }}>
            <IconEl style={{ color: active ? 'var(--fg-1)' : 'var(--fg-3)' }} />
            <span>{t.label}</span>
            {active && (
              <span style={{
                position: 'absolute', bottom: -1, left: 0, right: 0,
                height: 1, background: 'var(--bg-1)',
              }} />
            )}
          </button>
        );
      })}
      <div style={{ flex: 1 }} />
      <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      <ConnectedIndicator />
    </div>
  );
}

function ConnectedIndicator() {
  // The active run's SSE state is in RunContext; we read it via a small
  // bridge. When the list view is showing, fall back to "—".
  const [connected, setConnected] = React.useState(false);
  React.useEffect(() => {
    // Poll a tiny window flag that DetailScreen / RunContext updates.
    const id = setInterval(() => {
      setConnected(!!window.__lastSseConnected);
    }, 500);
    return () => clearInterval(id);
  }, []);
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      paddingRight: 14, paddingLeft: 14,
      color: 'var(--fg-3)',
      borderLeft: '1px solid var(--border-1)',
    }}>
      <Dot color={connected ? COLORS.info : COLORS.idle}
           pulse={connected ? 'pulse-a' : null} size={6} />
      <span className="mono" style={{ fontSize: 10.5 }}>
        {connected ? 'connected · localhost' : 'idle'}
      </span>
    </div>
  );
}

function ThemeToggle({ theme, onToggle }) {
  const [hover, setHover] = React.useState(false);
  const isDark = theme === 'dark';
  return (
    <button
      onClick={onToggle}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 24, padding: '0 10px', marginRight: 10,
        background: hover ? 'var(--bg-2)' : 'transparent',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-2)',
        color: 'var(--fg-2)',
        transition: 'background 120ms',
      }}>
      {isDark
        ? <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13.5 9.5A6 6 0 1 1 6.5 2.5 5 5 0 0 0 13.5 9.5Z"/></svg>
        : <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="8" r="2.8"/><path d="M8 1.5v1.4M8 13.1v1.4M1.5 8h1.4M13.1 8h1.4M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/></svg>
      }
      <span className="mono" style={{ fontSize: 10.5 }}>{isDark ? 'dark' : 'light'}</span>
    </button>
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
