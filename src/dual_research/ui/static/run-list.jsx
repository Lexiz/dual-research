// run-list.jsx — list of recent runs
// SPEC-0055: sortable columns, URL state, attention promotion,
// /-bound search, errored/deadlocked left border.

// ── URL state helpers ───────────────────────────────────────────
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
  if (params.q) p.set('q', params.q);
  const qs = p.toString();
  const url = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState(null, '', url);
}

// ── Sort logic ──────────────────────────────────────────────────
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
    // For 'started', higher startedAtAgo = older, so default desc should show newest first.
    // startedAtAgo is seconds ago — lower number = more recent.
    // invert flag means: for 'asc' display order we actually want descending numeric order.
    let cmp = (va || 0) - (vb || 0);
    if (cfg.invert) cmp = -cmp;
    return dir === 'asc' ? cmp : -cmp;
  });
  return sorted;
}

// ── Search filter ───────────────────────────────────────────────
function _matchesSearch(run, q) {
  if (!q) return true;
  const needle = q.toLowerCase();
  const haystack = [
    run.id, run.displayId, run.topic, run.status,
    'P' + run.phase,
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(needle);
}

// ── Attention classification ────────────────────────────────────
const ATTENTION_STATUSES = new Set(['errored', 'deadlocked']);

function _attentionSummary(run) {
  const parts = [];
  parts.push('P' + run.phase);
  if (run.rounds) parts.push(run.rounds + ' rounds');
  parts.push(run.status);
  return parts.join(' \u00b7 ');
}

// ── Column header labels + keys ─────────────────────────────────
const COLUMNS = [
  { key: 'id',       label: 'run id',   align: 'left' },
  { key: 'status',   label: 'status',   align: 'left' },
  { key: 'topic',    label: 'topic',    align: 'left' },
  { key: 'phase',    label: 'phase',    align: 'left' },
  { key: 'started',  label: 'started',  align: 'left' },
  { key: 'duration', label: 'duration', align: 'left' },
  { key: 'cost',     label: 'cost',     align: 'right' },
];

function RunListView({ runs, loading, onSelect }) {
  // Read URL state on mount
  const initial = React.useMemo(() => _readUrlParams(), []);
  const [filter, setFilter] = React.useState(initial.filter);
  const [sortKey, setSortKey] = React.useState(initial.sort);
  const [search, setSearch] = React.useState(initial.q);
  const searchRef = React.useRef(null);
  const debounceRef = React.useRef(null);

  // URL sync
  const syncUrl = React.useCallback((f, s, q) => {
    _writeUrlParams({ filter: f, sort: s, q });
  }, []);

  // Filter change
  const handleFilter = (f) => {
    setFilter(f);
    syncUrl(f, sortKey, search);
  };

  // Sort change
  const handleSort = (col) => {
    const parsed = _parseSort(sortKey);
    let newDir = 'asc';
    if (parsed.col === col) {
      newDir = parsed.dir === 'asc' ? 'desc' : 'asc';
    } else {
      // Default direction per column type
      newDir = col === 'topic' || col === 'id' || col === 'status' ? 'asc' : 'desc';
    }
    const newKey = col + ':' + newDir;
    setSortKey(newKey);
    syncUrl(filter, newKey, search);
  };

  // Search change with debounced URL write
  const handleSearch = (val) => {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      syncUrl(filter, sortKey, val);
    }, 250);
  };

  // `/` key to focus search
  React.useEffect(() => {
    const onKey = (e) => {
      if (e.key !== '/') return;
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) return;
      // Don't steal focus if a modal is open
      if (document.querySelector('[role="dialog"]')) return;
      e.preventDefault();
      if (searchRef.current) searchRef.current.focus();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const counts = runs.reduce((a, r) => ({ ...a, [r.status]: (a[r.status] || 0) + 1 }), {});
  const totalCost = runs.reduce((a, r) => a + r.cost, 0);
  const runningCount = runs.filter(r => r.status === 'running').length;

  // Apply filter + search
  let filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter);
  if (search) filtered = filtered.filter(r => _matchesSearch(r, search));

  // Sort
  const parsed = _parseSort(sortKey);

  // Split attention vs normal
  const attentionRuns = filtered.filter(r => ATTENTION_STATUSES.has(r.status));
  const normalRuns = filtered.filter(r => !ATTENTION_STATUSES.has(r.status));

  const sortedAttention = _sortRuns(attentionRuns, parsed.col, parsed.dir);
  const sortedNormal = _sortRuns(normalRuns, parsed.col, parsed.dir);

  const hasAttention = sortedAttention.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Top bar */}
      <header style={{
        display: 'grid',
        gridTemplateColumns: 'auto 1fr auto',
        gap: 18,
        alignItems: 'center',
        padding: '10px 18px',
        borderBottom: '1px solid var(--border-1)',
        background: 'var(--bg-1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, whiteSpace: 'nowrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{
              width: 16, height: 16, borderRadius: 4,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative', overflow: 'hidden',
              background: 'var(--bg-3)',
              flexShrink: 0,
            }}>
              <BrandMark name="claude" size={9} variant="solid" aria-hidden="true" style={{ position: 'absolute', top: 1, left: 1 }} />
              <BrandMark name="openai" size={9} variant="solid" aria-hidden="true" style={{ position: 'absolute', bottom: 1, right: 1 }} />
            </div>
            <span className="mono" style={{ fontSize: 12, color: 'var(--fg-1)', letterSpacing: '0.02em' }}>
              dual&#8209;research
            </span>
          </div>
          <span style={{ color: 'var(--fg-4)' }}>&middot;</span>
          <span style={{ color: 'var(--fg-1)', fontSize: 12 }}>runs</span>
        </div>

        <div style={{ minWidth: 0, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip icon="format-list-bulleted">{runs.length} run{runs.length === 1 ? '' : 's'}</Chip>
          {runningCount > 0 && <Chip tone="info" icon="circle-medium">{runningCount} running</Chip>}
          <Chip icon="currency-usd">{fmt.costShort(totalCost)} spent</Chip>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', whiteSpace: 'nowrap' }}>
          {/* Search input */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="search runs..."
              aria-label="Search runs"
              style={{
                width: 160,
                height: 26,
                padding: '0 8px 0 26px',
                fontSize: 11,
                fontFamily: 'var(--mono)',
                color: 'var(--fg-1)',
                background: 'var(--bg-0)',
                border: '1px solid var(--border-1)',
                borderRadius: 'var(--r-2)',
                outline: 'none',
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--border-2)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--border-1)'}
            />
            <Mdi name="magnify" size={12} style={{ position: 'absolute', left: 8, color: 'var(--fg-3)', pointerEvents: 'none' }} />
            {search && (
              <button
                onClick={() => { handleSearch(''); if (searchRef.current) searchRef.current.focus(); }}
                style={{
                  position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--fg-3)', padding: 2, display: 'flex',
                }}
                aria-label="Clear search"
              >
                <Mdi name="close" size={10} />
              </button>
            )}
          </div>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-4)' }}>live</span>
          <Dot color={COLORS.info} pulse="pulse-a" size={6} />
        </div>
      </header>

      {/* Filter strip -- SPEC-0053 D6: Tab primitives in TabGroup */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 18px',
        background: 'var(--bg-1)',
        borderBottom: '1px solid var(--border-1)',
      }}>
        <TabGroup>
          <Tab active={filter === 'all'} onClick={() => handleFilter('all')} count={runs.length} size="sm">all</Tab>
          <Tab active={filter === 'running'} onClick={() => handleFilter('running')} dot filterTone="running" count={counts.running||0} size="sm">running</Tab>
          <Tab active={filter === 'converged'} onClick={() => handleFilter('converged')} dot filterTone="converged" count={counts.converged||0} size="sm">converged</Tab>
          <Tab active={filter === 'deadlocked'} onClick={() => handleFilter('deadlocked')} dot filterTone="deadlocked" count={counts.deadlocked||0} size="sm">deadlocked</Tab>
          <Tab active={filter === 'errored'} onClick={() => handleFilter('errored')} dot filterTone="errored" count={counts.errored||0} size="sm">errored</Tab>
          <Tab active={filter === 'completed'} onClick={() => handleFilter('completed')} dot filterTone="completed" count={counts.completed||0} size="sm">completed</Tab>
        </TabGroup>
      </div>

      {/* Column headers -- sortable */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '80px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px',
        padding: '8px 18px',
        background: 'var(--bg-2)',
        borderBottom: '1px solid var(--border-2)',
        fontSize: 10, color: 'var(--fg-2)',
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}>
        {COLUMNS.map((c) => {
          const active = parsed.col === c.key;
          const isAsc = parsed.dir === 'asc';
          return (
            <div
              key={c.key}
              onClick={() => handleSort(c.key)}
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                justifyContent: c.align === 'right' ? 'flex-end' : 'flex-start',
                userSelect: 'none',
                color: active ? 'var(--fg-0)' : undefined,
              }}
              title={`Sort by ${c.label}`}
            >
              <span>{c.label}</span>
              {active && <Mdi name={isAsc ? 'sort-ascending' : 'sort-descending'} size={10} />}
            </div>
          );
        })}
        <div></div>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-0)' }}>
        {/* Attention section */}
        {hasAttention && (
          <>
            <div style={{
              padding: '6px 18px',
              background: 'var(--bg-1)',
              borderBottom: '1px solid var(--border-1)',
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--fg-2)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <Mdi name="alert" size={12} style={{ color: 'var(--warn)' }} />
              <span>Needs attention</span>
              <span className="mono" style={{
                fontSize: 10,
                padding: '1px 6px',
                background: 'var(--warn-bg)',
                border: '1px solid var(--warn-border)',
                borderRadius: 'var(--r-pill)',
                color: 'var(--warn)',
              }}>{sortedAttention.length}</span>
            </div>
            {sortedAttention.map((r) => (
              <RunRow key={r.id} run={r} onSelect={onSelect} attentionSummary={_attentionSummary(r)} />
            ))}
            {sortedNormal.length > 0 && (
              <div style={{
                padding: '6px 18px',
                background: 'var(--bg-1)',
                borderBottom: '1px solid var(--border-1)',
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--fg-3)',
              }}>
                Other runs
              </div>
            )}
          </>
        )}
        {sortedNormal.map((r) => (
          <RunRow key={r.id} run={r} onSelect={onSelect} />
        ))}
        {filtered.length === 0 && (
          <div style={{
            padding: '40px 18px',
            textAlign: 'center',
            color: 'var(--fg-3)',
            fontSize: 12,
          }}>
            {/* Spec 0082 — distinguish first-load-still-pending from
                confirmed-empty so the page doesn't flash "No runs"
                before the fetch has resolved. */}
            {loading && !search
              ? 'Loading data…'
              : search
                ? `No runs matching "${search}"`
                : 'No runs'}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-1)',
        background: 'var(--bg-1)',
        padding: '8px 18px',
        display: 'flex', gap: 18, alignItems: 'center',
        fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
      }}>
        <span>showing {filtered.length} of {runs.length}</span>
        <span style={{ flex: 1 }} />
        <span><kbd style={{ padding: '1px 4px', background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 3, fontSize: 10 }}>/</kbd> search &middot; click header to sort</span>
      </footer>
    </div>
  );
}

function RunRow({ run, onSelect, attentionSummary }) {
  const phaseLabel = PHASES[run.phase]?.label || 'done';
  const [hover, setHover] = React.useState(false);
  const idParts = window.splitRunId(run.id);
  const shortTopic = window.formatTopic(run.topic, { maxChars: 110 });
  const idTooltip = `${run.id}${idParts.time ? ` \u00b7 started ${idParts.time}` : ''}${idParts.slug ? ` \u00b7 ${idParts.slug}` : ''}`;
  const displayId = run.displayId || run.id.slice(0, 4);

  const isErrored = run.status === 'errored';
  const isDeadlocked = run.status === 'deadlocked';
  const needsAttention = isErrored || isDeadlocked;
  const borderColor = isErrored ? 'var(--err)' : isDeadlocked ? 'var(--warn)' : null;

  return (
    <div
      onClick={() => onSelect?.(run)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={run.id}
      style={{
        display: 'grid',
        gridTemplateColumns: '80px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px',
        alignItems: 'center',
        padding: '10px 18px',
        borderBottom: '1px solid var(--border-1)',
        background: hover ? 'var(--bg-1)' : run.selected ? 'var(--bg-1)' : 'transparent',
        cursor: 'pointer',
        position: 'relative',
        borderLeft: borderColor ? `2px solid ${borderColor}` : '2px solid transparent',
      }}>
      {/* Run id pill */}
      <span className="mono" title={idTooltip} style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        padding: '3px 10px',
        background: 'var(--bg-2)',
        border: '1px solid var(--border-1)',
        borderRadius: 999,
        fontSize: 11.5,
        color: 'var(--fg-1)',
        letterSpacing: '0.04em',
        width: 'fit-content',
      }}>{displayId}</span>
      <StatusBadge status={run.status} />
      <div style={{ minWidth: 0, paddingLeft: 8, paddingRight: 16 }} title={run.topic}>
        <div style={{
          color: 'var(--fg-0)', fontSize: 12.5,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{shortTopic}</div>
        {attentionSummary && (
          <div className="mono" style={{
            fontSize: 10, color: 'var(--fg-3)', marginTop: 2,
          }}>{attentionSummary}</div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <PhaseMini phase={run.phase} status={run.status} />
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>P{run.phase}</span>
        {run.rounds && (run.phase === 2 || run.phase === 4) && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>&middot; {run.rounds}</span>
        )}
      </div>
      <span className="mono" style={{ fontSize: 11.5, color: 'var(--fg-2)' }}>{fmt.relTime(run.startedAtAgo)}</span>
      <span className="mono num" style={{ fontSize: 11.5, color: 'var(--fg-2)' }}>{fmt.duration(run.duration)}</span>
      <span className="mono num" style={{ fontSize: 12, color: 'var(--fg-0)', textAlign: 'right' }}>{fmt.cost(run.cost)}</span>
      <Icon.Chevron style={{ color: hover ? 'var(--fg-1)' : 'var(--fg-4)' }} />
    </div>
  );
}

// 6-dot phase mini-strip
function PhaseMini({ phase, status }) {
  const failed = status === 'errored' || status === 'deadlocked';
  return (
    <div style={{ display: 'inline-flex', gap: 2 }}>
      {PHASES.map((p) => {
        const completed = p.id < phase || (status === 'completed' && p.id <= 5);
        const current = p.id === phase && status !== 'completed';
        let bg = 'var(--border-2)';
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

Object.assign(window, { RunListView });
