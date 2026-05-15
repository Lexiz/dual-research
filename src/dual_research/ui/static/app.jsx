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
      <ChromeBar route={route} navigate={navigate}
                 theme={theme}
                 onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} />

      <div style={{ height: 'calc(100vh - 44px)', overflow: 'hidden' }}>
        {route.view === 'detail'   && <DetailScreen runId={route.runId} navigate={navigate} />}
        {route.view === 'list'     && <ListScreen navigate={navigate} />}
        {route.view === 'language' && <DesignLanguageView />}
      </div>
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
    return <FullPageMessage title="Loading run…" body={runId} />;
  }
  return (
    <RunContext.Provider value={{ runId, connected, navigate }}>
      <RunDetail run={run} />
    </RunContext.Provider>
  );
}

// ─────────────────── List screen ───────────────────

function ListScreen({ navigate }) {
  const { rows, connected } = useRunList();
  React.useEffect(() => {
    window.__lastSseConnected = connected;
  }, [connected]);
  return (
    <RunListView
      runs={rows}
      onSelect={(r) => navigate('detail', r.id)}
    />
  );
}

// ─────────────────── Top chrome ───────────────────

function ChromeBar({ route, navigate, theme, onToggleTheme }) {
  const onList = route.view === 'list';
  return (
    <div style={{
      height: 44,
      background: 'var(--bg-0)',
      borderBottom: '1px solid var(--border-1)',
      display: 'flex', alignItems: 'stretch',
      paddingLeft: 8,
    }}>
      <ChromeTab
        label="All runs"
        icon={Icon.List}
        active={onList}
        onClick={() => navigate('list')}
      />
      <div style={{ flex: 1 }} />
      <RightCluster
        theme={theme}
        onToggleTheme={onToggleTheme}
        onOpenLanguage={() => navigate('language')}
        languageActive={route.view === 'language'}
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

// ─────────────────── Right cluster — three sibling controls ───────────────────

function RightCluster({ theme, onToggleTheme, onOpenLanguage, languageActive }) {
  return (
    <div style={{ display: 'flex', alignItems: 'stretch' }}>
      <ConnectionPill />
      <ThemeSegmentedToggle theme={theme} onToggle={onToggleTheme} />
      <DesignLanguageButton onClick={onOpenLanguage} active={languageActive} />
    </div>
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
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '0 14px',
      borderLeft: '1px solid var(--border-1)',
      color: 'var(--fg-2)',
      minWidth: 132,
    }}>
      <Dot color={connected ? COLORS.info : COLORS.idle}
           pulse={connected ? 'pulse-a' : null} size={7} />
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
        <span style={{ fontSize: 11.5, color: connected ? 'var(--fg-1)' : 'var(--fg-2)' }}>
          {connected ? 'connected' : 'idle'}
        </span>
        <span className="mono" style={{ fontSize: 9.5, color: 'var(--fg-3)' }}>
          {connected ? 'localhost · 6173' : '—'}
        </span>
      </div>
    </div>
  );
}

function ThemeSegmentedToggle({ theme, onToggle }) {
  const isDark = theme === 'dark';
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      borderLeft: '1px solid var(--border-1)',
      padding: '0 12px',
    }}>
      <div role="group" aria-label="Theme"
           style={{
        display: 'inline-flex',
        background: 'var(--bg-2)',
        border: '1px solid var(--border-1)',
        borderRadius: 999,
        padding: 2,
        height: 28,
      }}>
        <ThemeSeg active={!isDark} onClick={() => isDark && onToggle()} label="light"
                  icon={
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
                         stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="8" cy="8" r="2.8"/>
                      <path d="M8 1.5v1.4M8 13.1v1.4M1.5 8h1.4M13.1 8h1.4M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/>
                    </svg>
                  } />
        <ThemeSeg active={isDark} onClick={() => !isDark && onToggle()} label="dark"
                  icon={
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
                         stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13.5 9.5A6 6 0 1 1 6.5 2.5 5 5 0 0 0 13.5 9.5Z"/>
                    </svg>
                  } />
      </div>
    </div>
  );
}

function ThemeSeg({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      title={label}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '0 10px',
        background: active ? 'var(--bg-0)' : 'transparent',
        color: active ? 'var(--fg-0)' : 'var(--fg-3)',
        border: active ? '1px solid var(--border-1)' : '1px solid transparent',
        borderRadius: 999,
        cursor: active ? 'default' : 'pointer',
        height: 22,
      }}>
      {icon}
      <span className="mono" style={{ fontSize: 10.5 }}>{label}</span>
    </button>
  );
}

function DesignLanguageButton({ onClick, active }) {
  return (
    <button
      onClick={onClick}
      title="Design language"
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        padding: '0 14px',
        borderLeft: '1px solid var(--border-1)',
        background: active ? 'var(--bg-1)' : 'transparent',
        color: active ? 'var(--fg-0)' : 'var(--fg-2)',
        fontSize: 12,
        cursor: 'pointer',
      }}>
      <Icon.Palette style={{ color: active ? 'var(--fg-1)' : 'var(--fg-3)' }} />
      <span>Design</span>
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
