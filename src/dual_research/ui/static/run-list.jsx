// run-list.jsx — All Runs landing page (card layout + summary stats).
// SPEC-0246: card-based rewrite. The page owns its own fetch (spec 0245
// archive toggle depends on it), renders a sticky chrome, a summary stats
// panel, status-grouped sections, and per-run cards surfacing the phase
// strip, per-agent cost split, and terminal-state note. URL state
// (?sort=/?filter=) lives in the local helpers below — router.jsx is
// hash-only. The old `?q=` inline search is removed (§5).

// ── URL state helpers (kept; ?q= is now a no-op — §2.1) ─────────────
function _readUrlParams() {
  const p = new URLSearchParams(window.location.search);
  return {
    sort: p.get('sort') || 'started:desc',
    filter: p.get('filter') || 'all',
    q: p.get('q') || '',
  };
}

function _writeUrlParams(params) {
  const p = new URLSearchParams();
  if (params.sort && params.sort !== 'started:desc') p.set('sort', params.sort);
  if (params.filter && params.filter !== 'all') p.set('filter', params.filter);
  const qs = p.toString();
  const url = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState(null, '', url);
}

// ── Sort logic (kept) ───────────────────────────────────────────
const SORT_COLUMNS = {
  id:       { get: (r) => r.displayId || r.id.slice(0, 4), type: 'string' },
  status:   { get: (r) => r.status, type: 'string' },
  topic:    { get: (r) => (r.topic || '').toLowerCase(), type: 'string' },
  phase:    { get: (r) => r.phase, type: 'number' },
  started:  { get: (r) => r.startedAtAgo, type: 'number', invert: true },
  duration: { get: (r) => r.duration, type: 'number' },
  cost:     { get: (r) => r.cost, type: 'number' },
};

function _parseSort(s) {
  const [col, dir] = (s || 'started:desc').split(':');
  if (!SORT_COLUMNS[col]) return { col: 'started', dir: 'desc' };
  return { col, dir: dir === 'asc' ? 'asc' : 'desc' };
}

function _sortRuns(runs, col, dir) {
  const cfg = SORT_COLUMNS[col];
  if (!cfg) return runs;
  const sorted = [...runs].sort((a, b) => {
    const va = cfg.get(a);
    const vb = cfg.get(b);
    if (cfg.type === 'string') {
      const cmp = String(va).localeCompare(String(vb));
      return dir === 'asc' ? cmp : -cmp;
    }
    let cmp = (va || 0) - (vb || 0);
    if (cfg.invert) cmp = -cmp;
    return dir === 'asc' ? cmp : -cmp;
  });
  return sorted;
}

// Sort affordance — cycles through the documented vocabulary (§2.5).
const SORT_ORDER = ['started:desc', 'cost:desc', 'duration:desc', 'id:asc'];
const SORT_LABELS = {
  'started:desc': 'Started, newest',
  'cost:desc': 'Cost, highest',
  'duration:desc': 'Duration, longest',
  'id:asc': 'Run id, A–Z',
};

// ── Status partitioning ─────────────────────────────────────────
// Spec 0181 — `abandoned` is a "needs-attention" status (silent death).
const ATTENTION_STATUSES = new Set(['errored', 'deadlocked', 'abandoned']);
const CONVERGED_STATUSES = new Set(['completed', 'converged']);

// ── Card class maps (literal strings so the source-pattern tests can
//    assert the post-fix anatomy; spec 0206 doctrine) ─────────────
const RC_CARD_MOD = {
  errored: 'run-card--errored',
  deadlocked: 'run-card--abandoned',
  abandoned: 'run-card--abandoned',
  completed: 'run-card--completed',
  converged: 'run-card--completed',
  running: 'run-card--running',
};
const RC_STATUS_MOD = {
  errored: 'rc-status--errored',
  deadlocked: 'rc-status--abandoned',
  abandoned: 'rc-status--abandoned',
  completed: 'rc-status--completed',
  converged: 'rc-status--completed',
  running: 'rc-status--running',
};
const RC_PHASE_LABELS = ['P1 plan', 'P2 nego', 'P3 res', 'P4 rev', 'P5 sum'];

// ── Small render helpers ────────────────────────────────────────
function Ms({ name, size }) {
  return <span className={'ms' + (size ? ' ms-' + size : '')} aria-hidden="true">{name}</span>;
}

function _money(n) { return '$' + (Number(n) || 0).toFixed(2); }

function _fmtStarted(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getMonth()];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${mon} ${d.getDate()}, ${hh}:${mm}`;
}

// Spec 0245 — local helper; mirrors `_seconds_since_iso` in server.py.
function _secondsSinceIso(iso) {
  if (!iso) return 0;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

// ── Aggregation (computed client-side over the unfiltered runs) ──
function computeStats(runs) {
  const total = runs.length;
  const num = (n) => Number(n) || 0;
  const totalSpend = runs.reduce((a, r) => a + num(r.cost), 0);
  const stalledSpend = runs.filter(r => ATTENTION_STATUSES.has(r.status)).reduce((a, r) => a + num(r.cost), 0);
  const convergedRuns = runs.filter(r => CONVERGED_STATUSES.has(r.status));
  const convergedSpend = convergedRuns.reduce((a, r) => a + num(r.cost), 0);
  const convergedCount = convergedRuns.length;
  const convergenceRate = total ? (convergedCount / total) * 100 : 0;
  const avgCost = total ? totalSpend / total : 0;
  const costs = runs.map(r => num(r.cost));
  const minCost = costs.length ? Math.min(...costs) : 0;
  const maxCost = costs.length ? Math.max(...costs) : 0;
  const durRuns = runs.filter(r => num(r.duration) > 0);
  const avgDuration = durRuns.length ? durRuns.reduce((a, r) => a + num(r.duration), 0) / durRuns.length : 0;
  const p2Abandoned = runs.filter(r => r.phase === 2 && r.status === 'abandoned').length;
  const buckets = [1, 2, 3, 4, 5].map(p => {
    const inb = runs.filter(r => r.phase === p);
    const hasErr = inb.some(r => r.status === 'errored');
    const hasWarn = inb.some(r => r.status === 'abandoned' || r.status === 'deadlocked');
    const hasOk = inb.some(r => CONVERGED_STATUSES.has(r.status));
    let kind = '';
    if (hasErr && hasWarn) kind = '--mix';
    else if (hasErr) kind = '--err';
    else if (hasOk && !hasWarn) kind = '--ok';
    return { code: 'P' + p, count: inb.length, kind };
  });
  const maxCount = Math.max(1, ...buckets.map(b => b.count));
  buckets.forEach(b => { b.pct = Math.round((b.count / maxCount) * 100); });
  return {
    total, totalSpend, stalledSpend, convergedSpend, convergedCount,
    convergenceRate, avgCost, minCost, maxCost, avgDuration, p2Abandoned, buckets,
  };
}

function statusCounts(runs) {
  const c = { all: runs.length };
  runs.forEach(r => { c[r.status] = (c[r.status] || 0) + 1; });
  return c;
}

function applyFilterAndSort(runs, filter, sortKey) {
  const filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter);
  const parsed = _parseSort(sortKey);
  return _sortRuns(filtered, parsed.col, parsed.dir);
}

function partitionByStatus(runs) {
  return {
    running: runs.filter(r => r.status === 'running'),
    attention: runs.filter(r => ATTENTION_STATUSES.has(r.status)),
    converged: runs.filter(r => CONVERGED_STATUSES.has(r.status)),
  };
}

// ─────────────────── Page ───────────────────
function AllRunsPage({ onSelect, navigate, theme, onToggleTheme }) {
  const me = useMe();
  const isAdmin = !!(me && me.isAdmin);

  // Spec 0245 — admin-only Active/Archived toggle. Owns the data fetch so
  // swapping flips the polled URL. Non-admins cannot reach this state.
  const [archivedView, setArchivedView] = React.useState(false);
  const { rows: runs, connected, loading, refresh } = useRunList({ archived: archivedView });
  React.useEffect(() => { window.__lastSseConnected = connected; }, [connected]);

  // Spec 0245 — confirmation-dialog targets.
  const [archiveTarget, setArchiveTarget] = React.useState(null);
  const [unarchiveTarget, setUnarchiveTarget] = React.useState(null);
  const toast = useToast();

  const handleArchiveConfirm = React.useCallback(async () => {
    if (!archiveTarget) return;
    const target = archiveTarget;
    setArchiveTarget(null);
    try {
      const resp = await authedFetch(`/api/runs/${encodeURIComponent(target.id)}/archive`, { method: 'POST' });
      if (resp.status === 204 || resp.status === 409) {
        toast({ tone: 'ok', text: `Run ${target.displayId || target.id.slice(0, 4)} archived.` });
        refresh();
      } else {
        let err;
        try { err = (await resp.json()).detail; } catch (_) { err = null; }
        toast({ tone: 'error', text: err || 'Could not archive run. Try again.' });
      }
    } catch (_) {
      toast({ tone: 'error', text: 'Could not archive run. Try again.' });
    }
  }, [archiveTarget, refresh, toast]);

  const handleUnarchiveConfirm = React.useCallback(async () => {
    if (!unarchiveTarget) return;
    const target = unarchiveTarget;
    setUnarchiveTarget(null);
    try {
      const resp = await authedFetch(`/api/runs/${encodeURIComponent(target.id)}/archive`, { method: 'DELETE' });
      if (resp.status === 204 || resp.status === 409) {
        toast({ tone: 'ok', text: `Run ${target.displayId || target.id.slice(0, 4)} restored.` });
        refresh();
      } else {
        let err;
        try { err = (await resp.json()).detail; } catch (_) { err = null; }
        toast({ tone: 'error', text: err || 'Could not restore run. Try again.' });
      }
    } catch (_) {
      toast({ tone: 'error', text: 'Could not restore run. Try again.' });
    }
  }, [unarchiveTarget, refresh, toast]);

  // Local URL-param state (NOT router hooks).
  const initial = React.useMemo(() => _readUrlParams(), []);
  const [filter, setFilter] = React.useState(initial.filter);
  const [sortKey, setSortKey] = React.useState(initial.sort);

  const handleFilter = (f) => { setFilter(f); _writeUrlParams({ filter: f, sort: sortKey }); };
  const handleSortCycle = () => {
    const i = SORT_ORDER.indexOf(sortKey);
    const next = SORT_ORDER[(i + 1) % SORT_ORDER.length] || SORT_ORDER[0];
    setSortKey(next);
    _writeUrlParams({ filter, sort: next });
  };

  const stats = computeStats(runs);                       // unfiltered — project-wide health
  const counts = statusCounts(runs);
  const visibleRuns = applyFilterAndSort(runs, filter, sortKey);
  const groups = partitionByStatus(visibleRuns);

  const cardProps = {
    onSelect, isAdmin, archivedView,
    onArchive: setArchiveTarget, onUnarchive: setUnarchiveTarget,
  };

  return (
    <>
      <AllRunsChrome
        me={me}
        isAdmin={isAdmin}
        archivedView={archivedView}
        onArchivedView={setArchivedView}
        connected={connected}
        navigate={navigate}
        theme={theme}
        onToggleTheme={onToggleTheme}
      />
      <main className="ar-page">
        <ProjectStrip />
        <StatsPanel stats={stats} />
        <FilterChipRow filter={filter} counts={counts} sortKey={sortKey} onFilter={handleFilter} onSortCycle={handleSortCycle} />

        {archivedView ? (
          <div className="ar-grid">
            {visibleRuns.map(r => <RunCard key={r.id} run={r} {...cardProps} />)}
          </div>
        ) : (
          <>
            {groups.running.length > 0 && (
              <RunGroup kind="running" runs={groups.running} stats={stats} {...cardProps} />
            )}
            {groups.attention.length > 0 && (
              <RunGroup kind="attention" runs={groups.attention} stats={stats} {...cardProps} />
            )}
            {groups.converged.length > 0 && (
              <RunGroup kind="converged" runs={groups.converged} stats={stats} {...cardProps} />
            )}
          </>
        )}

        {visibleRuns.length === 0 && (
          <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--md-on-surface-faint)', fontSize: 13 }}>
            {loading ? 'Loading runs…' : (archivedView ? 'No archived runs.' : 'No runs yet.')}
          </div>
        )}
      </main>

      <ConfirmArchiveDialog run={archiveTarget} onConfirm={handleArchiveConfirm} onCancel={() => setArchiveTarget(null)} />
      <ConfirmUnarchiveDialog run={unarchiveTarget} onConfirm={handleUnarchiveConfirm} onCancel={() => setUnarchiveTarget(null)} />
    </>
  );
}

// ── §2.2 / §2.12.1 — Top chrome ─────────────────────────────────
function AllRunsChrome({ me, isAdmin, archivedView, onArchivedView, connected, navigate, theme, onToggleTheme }) {
  const meta = window.useAppMeta ? window.useAppMeta() : null;
  const version = meta && meta.version;
  const avatarInitial = ((me && me.email) || 'a').slice(0, 1).toLowerCase();
  return (
    <header className="ar-chrome">
      <div className="ar-chrome__tabs">
        <button type="button" className="ar-tab" aria-current="page"><Ms name="view_agenda" />All runs</button>
        <button type="button" className="ar-tab" onClick={() => navigate && navigate('compare')}><Ms name="compare_arrows" />Compare</button>
        <button type="button" className="ar-tab" onClick={() => navigate && navigate('search')}><Ms name="search" />Search</button>
      </div>
      <div className="ar-chrome__sp" />
      {isAdmin && (
        <div className="ar-chrome__tabs" data-testid="archived-view-toggle">
          <button type="button" className={'ar-tab' + (!archivedView ? ' is-active' : '')} onClick={() => onArchivedView(false)}>Active</button>
          <button type="button" className={'ar-tab' + (archivedView ? ' is-active' : '')} onClick={() => onArchivedView(true)}>Archived</button>
        </div>
      )}
      <span className="ar-pill"><span className={'dot' + (connected ? ' dot--ok' : '')} />{connected ? 'connected' : 'offline'}</span>
      {version && (
        <button type="button" className="ar-pill" title={`dual-research v${version}`}
          onClick={() => { window.location.hash = `#/how-it-works#cl-${String(version).replace(/\./g, '')}`; }}>
          <span className="ar-pill__v">v{version}</span>
        </button>
      )}
      <button type="button" className="ar-tab" onClick={() => navigate && navigate('how-it-works')}>How it works</button>
      <button type="button" className="md-icon-btn" aria-label="Toggle light / dark theme" title="Toggle theme"
        onClick={() => onToggleTheme && onToggleTheme()}>
        <Ms name="contrast" size={20} />
      </button>
      <span className="ar-avatar" aria-hidden="true">{avatarInitial}</span>
    </header>
  );
}

// ── §2.3 — Project strip ────────────────────────────────────────
function ProjectStrip() {
  return (
    <div className="ar-project">
      <span className="ar-project__mark" aria-hidden="true" />
      <span className="ar-project__name">dual&#8209;research</span>
    </div>
  );
}

// ── §2.4 — Stats panel ──────────────────────────────────────────
function StatsPanel({ stats }) {
  const s = stats;
  return (
    <section className="ar-stats" aria-label="Summary statistics">
      <div className="ar-stat">
        <div className="ar-stat__label">Total spend</div>
        <div className="ar-stat__value">{_money(s.totalSpend)}</div>
        <div className="ar-stat__hint"><b>{_money(s.stalledSpend)}</b> on stalled runs · <b>{_money(s.convergedSpend)}</b> converged</div>
      </div>
      <div className="ar-stat">
        <div className="ar-stat__label">Convergence rate</div>
        <div className="ar-stat__value">{s.convergenceRate.toFixed(1)}%</div>
        <div className="ar-stat__hint"><b>{s.total} runs</b> · <b>{s.convergedCount} converged</b></div>
      </div>
      <div className="ar-stat">
        <div className="ar-stat__label">Avg cost / run</div>
        <div className="ar-stat__value">{_money(s.avgCost)}</div>
        <div className="ar-stat__hint">Range <b>{_money(s.minCost)}</b> – <b>{_money(s.maxCost)}</b></div>
      </div>
      <div className="ar-stat">
        <div className="ar-stat__label">Avg duration</div>
        <div className="ar-stat__value">{fmt.duration(Math.round(s.avgDuration))}</div>
        <div className="ar-stat__hint">Excludes runs abandoned at P2 ({s.p2Abandoned})</div>
      </div>
      <div className="ar-stat ar-stat--phase">
        <div className="ar-stat__label">Where runs ended</div>
        <div className="phase-dist">
          {s.buckets.map(b => (
            <React.Fragment key={b.code}>
              <div className="phase-dist__code">{b.code}</div>
              <div className="phase-dist__bar"><div className={'phase-dist__fill ' + (b.kind || '')} style={{ width: b.pct + '%' }} /></div>
              <div className="phase-dist__count">{b.count}</div>
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── §2.5 — Filter chip row ──────────────────────────────────────
const FILTER_CHIPS = [
  { key: 'all', label: 'All', swatch: null },
  { key: 'running', label: 'Running', swatch: '--running' },
  { key: 'converged', label: 'Converged', swatch: '--converged' },
  { key: 'deadlocked', label: 'Deadlocked', swatch: '--deadlocked' },
  { key: 'errored', label: 'Errored', swatch: '--errored' },
  { key: 'abandoned', label: 'Abandoned', swatch: '--abandoned' },
  { key: 'completed', label: 'Completed', swatch: '--completed' },
];

function FilterChipRow({ filter, counts, sortKey, onFilter, onSortCycle }) {
  return (
    <div className="ar-filters">
      {FILTER_CHIPS.map(chip => {
        const count = chip.key === 'all' ? counts.all : (counts[chip.key] || 0);
        return (
          <button
            key={chip.key}
            type="button"
            className="fchip"
            aria-pressed={filter === chip.key}
            onClick={() => onFilter(chip.key)}
          >
            {chip.swatch && <span className={'swatch ' + chip.swatch} />}
            {chip.label}
            <span className="ct">{count}</span>
          </button>
        );
      })}
      <span className="ar-filters__sp" />
      <button type="button" className="ar-sort" onClick={onSortCycle}>
        <Ms name="sort" />{SORT_LABELS[sortKey] || 'Started, newest'}
      </button>
    </div>
  );
}

// ── §2.6 — Section group ────────────────────────────────────────
const GROUP_META = {
  running: { title: 'Running', cls: 'ar-group', icon: 'play_circle' },
  attention: { title: 'Needs attention', cls: 'ar-group ar-group--warn', icon: 'warning_amber' },
  converged: { title: 'Converged', cls: 'ar-group', icon: 'check_circle' },
};

function _groupHint(kind, runs, stats) {
  if (kind === 'running') {
    const spend = runs.reduce((a, r) => a + (Number(r.cost) || 0), 0);
    return `${runs.length} in flight · ${_money(spend)} spent so far`;
  }
  if (kind === 'attention') {
    const spend = runs.reduce((a, r) => a + (Number(r.cost) || 0), 0);
    const p2 = runs.filter(r => r.phase === 2 && r.status === 'abandoned').length;
    return `${_money(spend)} of compute on stalled runs · ${p2} abandoned in P2 (plan negotiation)`;
  }
  const spend = runs.reduce((a, r) => a + (Number(r.cost) || 0), 0);
  const avg = runs.length ? spend / runs.length : 0;
  const durRuns = runs.filter(r => (Number(r.duration) || 0) > 0);
  const avgDur = durRuns.length ? durRuns.reduce((a, r) => a + r.duration, 0) / durRuns.length : 0;
  return `Clean P5 finish · ${_money(avg)} average · ${fmt.duration(Math.round(avgDur))} average`;
}

function RunGroup({ kind, runs, stats, ...cardProps }) {
  const meta = GROUP_META[kind] || GROUP_META.converged;
  return (
    <section className={meta.cls}>
      <div className="ar-group__head">
        <Ms name={meta.icon} />
        <span className="ar-group__title">{meta.title}</span>
        <span className="ar-group__count">{runs.length}</span>
        <span className="ar-group__hint">{_groupHint(kind, runs, stats)}</span>
      </div>
      <div className="ar-grid">
        {runs.map(r => <RunCard key={r.id} run={r} {...cardProps} />)}
      </div>
    </section>
  );
}

// ── §2.8.6 — Per-agent row ──────────────────────────────────────
function AgentRow({ side, agent }) {
  if (!agent) return null;
  return (
    <div className={'rc-agent rc-agent--' + side}>
      <span className="rc-agent__name">{agent.name}</span>
      <span className="rc-agent__cost">{_money(agent.cost)}</span>
      <span className="rc-agent__chips">
        {(agent.chips || []).map((c, i) => (
          <span key={i} className={'rc-bdg' + (c.kind ? ' rc-bdg--' + c.kind : '')}>{c.text}</span>
        ))}
      </span>
    </div>
  );
}

// ── §2.8 / §2.12 — Run card ─────────────────────────────────────
function RunCard({ run, onSelect, isAdmin, archivedView, onArchive, onUnarchive }) {
  const [hover, setHover] = React.useState(false);
  const isArchived = !!run.deletedAt;
  const cardMod = isArchived ? 'run-card--archived' : (RC_CARD_MOD[run.status] || '');
  const statusMod = RC_STATUS_MOD[run.status] || '';
  const displayId = run.displayId || run.id;
  const isRunning = run.status === 'running';

  const showArchiveBtn = hover && isAdmin && !isArchived && !archivedView;
  const showUnarchiveBtn = hover && isAdmin && isArchived;
  const archivedSecs = isArchived ? _secondsSinceIso(run.deletedAt) : null;

  return (
    <article
      className={'run-card ' + cardMod}
      data-run-id={run.id}
      onClick={() => { if (!isArchived) onSelect && onSelect(run); }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="rc-head">
        <span className={'rc-status ' + statusMod}>{run.status}</span>
        <span className="rc-topic">{run.topic || '—'}</span>
        <div className="rc-foot">
          <div className="rc-meta"><span className="rc-meta__l">Started</span><span className="rc-meta__v">{_fmtStarted(run.startedAt)}</span></div>
          <div className="rc-meta"><span className="rc-meta__l">Duration</span><span className="rc-meta__v">{fmt.duration(run.duration)}</span></div>
          <div className="rc-meta"><span className="rc-meta__l">Rounds</span><span className="rc-meta__v">{(run.roundsCompleted || 0)} / {(run.roundsMax || 6)}</span></div>
          <div className="rc-meta"><span className="rc-meta__l">Cost</span><span className="rc-meta__v">{_money(run.cost)}</span></div>
        </div>
        <span className="rc-idbdg">{displayId}</span>
      </div>

      <div className="rc-phases">
        {(run.phases || []).map((st, i) => (
          <div key={i} className={'rc-phase rc-phase--' + (st || 'pending')}>
            <div className="rc-phase__bar" />
            <div className="rc-phase__lbl">{RC_PHASE_LABELS[i]}</div>
          </div>
        ))}
      </div>

      <div className="rc-agents">
        <AgentRow side="a" agent={run.agents && run.agents.a} />
        <AgentRow side="b" agent={run.agents && run.agents.b} />
      </div>

      {isArchived ? (
        <span className="rc-archived-cap" title={`archived ${run.deletedAt} by ${run.deletedBy || 'unknown'}`}>
          {`archived ${fmt.relTime(archivedSecs || 0)}${run.deletedBy ? ` · by ${run.deletedBy}` : ''}`}
        </span>
      ) : run.note ? (
        <div className={'rc-note rc-note--' + run.note.variant}>
          <Ms name={run.note.icon} />
          <span dangerouslySetInnerHTML={{ __html: run.note.html }} />
        </div>
      ) : null}

      {/* Top-right affordances (§2.8.3 / §2.8.4 / §2.12.2). */}
      {isRunning && !isArchived && <span className="rc-live" aria-hidden="true" />}
      {!isRunning && !showArchiveBtn && !showUnarchiveBtn && (
        <span className="rc-chev" aria-hidden="true"><Ms name="chevron_right" /></span>
      )}
      {showArchiveBtn && (
        <button type="button" className="md-icon-btn rc-archive-btn"
          onClick={(e) => { e.stopPropagation(); onArchive && onArchive(run); }}
          aria-label={`Archive run ${displayId}`} title="Archive run">
          <Icon.Archive />
        </button>
      )}
      {showUnarchiveBtn && (
        <button type="button" className="md-icon-btn rc-archive-btn"
          onClick={(e) => { e.stopPropagation(); onUnarchive && onUnarchive(run); }}
          aria-label={`Restore run ${displayId}`} title="Restore run">
          <Icon.ArchiveUp />
        </button>
      )}
    </article>
  );
}

// ─────────────────── Confirm dialogs (kept — spec 0245) ───────────────────
function ConfirmArchiveDialog({ run, onConfirm, onCancel }) {
  if (!run) return null;
  const displayId = run.displayId || run.id.slice(0, 4);
  return (
    <Modal open={true} onClose={onCancel} title={`Archive run ${displayId}?`} variant="single">
      <div style={{ padding: 'var(--md-sp-2) 0', color: 'var(--md-on-surface-variant)' }}>
        It will be hidden from the runs list. An admin can restore it from the Archived view.
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--md-sp-2)', marginTop: 'var(--md-sp-4)' }}>
        <Button variant="text" onClick={onCancel}>Cancel</Button>
        <Button variant="filled" tone="error" onClick={onConfirm}>Archive</Button>
      </div>
    </Modal>
  );
}

function ConfirmUnarchiveDialog({ run, onConfirm, onCancel }) {
  if (!run) return null;
  const displayId = run.displayId || run.id.slice(0, 4);
  return (
    <Modal open={true} onClose={onCancel} title={`Restore run ${displayId}?`} variant="single">
      <div style={{ padding: 'var(--md-sp-2) 0', color: 'var(--md-on-surface-variant)' }}>
        It will reappear in the active runs list.
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--md-sp-2)', marginTop: 'var(--md-sp-4)' }}>
        <Button variant="text" onClick={onCancel}>Cancel</Button>
        <Button variant="filled" onClick={onConfirm}>Restore</Button>
      </div>
    </Modal>
  );
}

// ── PhaseMini — kept for the /#/language primitives showcase (§2.1) ──
function PhaseMini({ phase, status }) {
  const failed = status === 'errored' || status === 'deadlocked';
  return (
    <div style={{ display: 'inline-flex', gap: 2 }}>
      {PHASES.map((p) => {
        const completed = p.id < phase || (status === 'completed' && p.id <= 5);
        const current = p.id === phase && status !== 'completed';
        let bg = 'var(--md-outline-variant)';
        if (failed && current) bg = status === 'errored' ? COLORS.err : COLORS.warn;
        else if (current) bg = COLORS.info;
        else if (completed) bg = COLORS.ok;
        return (
          <span key={p.id} style={{
            display: 'inline-block', width: 6, height: 6, borderRadius: 1.5,
            background: bg,
          }} />
        );
      })}
    </div>
  );
}

Object.assign(window, { AllRunsPage });
