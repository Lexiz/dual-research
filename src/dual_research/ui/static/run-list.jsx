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
// Spec 0181 — `abandoned` is the "needs-attention" bucket too: the
// orchestrator died silently and the user almost certainly wants to
// investigate or retry.
const ATTENTION_STATUSES = new Set(['errored', 'deadlocked', 'abandoned']);

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

function RunListView({ onSelect }) {
  const me = useMe();
  const isAdmin = !!(me && me.isAdmin);

  // Spec 0245 — admin-only Active/Archived toggle. Owns the data fetch
  // so swapping flips the polled URL. Non-admins cannot reach this
  // state (the toggle is hidden); even if they could, the server
  // silently ignores `?archived=true` for non-admin callers.
  const [archivedView, setArchivedView] = React.useState(false);
  const { rows: runs, connected, loading, refresh } = useRunList({ archived: archivedView });
  React.useEffect(() => {
    window.__lastSseConnected = connected;
  }, [connected]);

  // Spec 0245 — confirmation-dialog targets. `archiveTarget` opens the
  // archive dialog; `unarchiveTarget` opens the symmetric unarchive
  // dialog. Both are run objects from the current list.
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
        // 409 = already archived from another tab; treat as success since
        // the resulting state matches the user's intent (row goes away).
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

  // Spec 0245 — archive is "I dealt with it"; don't bucket archived
  // rows back into the "Needs attention" cluster even if their last
  // recorded status was errored / deadlocked / abandoned.
  const attentionRuns = archivedView
    ? []
    : filtered.filter(r => ATTENTION_STATUSES.has(r.status));
  const normalRuns = archivedView
    ? filtered
    : filtered.filter(r => !ATTENTION_STATUSES.has(r.status));

  const sortedAttention = _sortRuns(attentionRuns, parsed.col, parsed.dir);
  const sortedNormal = _sortRuns(normalRuns, parsed.col, parsed.dir);

  const hasAttention = sortedAttention.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Header 1 — top app bar: brand mark + title | spacer | chips + search */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '0 18px',
        height: 44,
        borderBottom: '1px solid var(--md-outline-hair)',
        background: 'var(--md-surface-container-low)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0 }}>
          <div style={{
            width: 16, height: 16, borderRadius: 4,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative', overflow: 'hidden',
            background: 'var(--md-surface-container-highest)',
            flexShrink: 0,
          }}>
            <BrandMark name="claude" size={9} variant="solid" aria-hidden="true" style={{ position: 'absolute', top: 1, left: 1 }} />
            <BrandMark name="openai" size={9} variant="solid" aria-hidden="true" style={{ position: 'absolute', bottom: 1, right: 1 }} />
          </div>
          <span className="mono" style={{ fontSize: 12, color: 'var(--md-on-surface-variant)', letterSpacing: '0.02em' }}>
            dual&#8209;research
          </span>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
          <Chip icon="format-list-bulleted" title="Total runs in the current filter">{runs.length} run{runs.length === 1 ? '' : 's'}</Chip>
          {runningCount > 0 && <Chip tone="info" icon="circle-medium" title="Runs currently in progress">{runningCount} running</Chip>}
          <Chip icon="currency-usd" title="Aggregate cost across the visible runs">{fmt.costShort(totalCost)} spent</Chip>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
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
                fontFamily: 'var(--md-font-data)',
                color: 'var(--md-on-surface-variant)',
                background: 'var(--md-surface)',
                border: '1px solid var(--md-outline-hair)',
                borderRadius: 'var(--md-shape-sm)',
                outline: 'none',
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--md-outline-variant)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--md-outline-hair)'}
            />
            <Mdi name="magnify" size={12} style={{ position: 'absolute', left: 8, color: 'var(--md-on-surface-faint)', pointerEvents: 'none' }} />
            {search && (
              <button
                onClick={() => { handleSearch(''); if (searchRef.current) searchRef.current.focus(); }}
                style={{
                  position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--md-on-surface-faint)', padding: 2, display: 'flex',
                }}
                aria-label="Clear search"
              >
                <Mdi name="close" size={10} />
              </button>
            )}
          </div>
          <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-decor)' }}>live</span>
          <Dot color={COLORS.info} pulse="pulse-a" size={6} />
        </div>
      </header>

      {/* Header 2 — filter-tab strip (was header 3; header 2's brand row deleted) */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 18px',
        background: 'var(--md-surface-container-low)',
        borderBottom: '1px solid var(--md-outline-hair)',
      }}>
        <TabGroup>
          <Tab active={filter === 'all'} onClick={() => handleFilter('all')} count={runs.length} size="sm">all</Tab>
          <Tab active={filter === 'running'} onClick={() => handleFilter('running')} dot filterTone="running" count={counts.running||0} size="sm">running</Tab>
          <Tab active={filter === 'converged'} onClick={() => handleFilter('converged')} dot filterTone="converged" count={counts.converged||0} size="sm">converged</Tab>
          <Tab active={filter === 'deadlocked'} onClick={() => handleFilter('deadlocked')} dot filterTone="deadlocked" count={counts.deadlocked||0} size="sm">deadlocked</Tab>
          <Tab active={filter === 'errored'} onClick={() => handleFilter('errored')} dot filterTone="errored" count={counts.errored||0} size="sm">errored</Tab>
          {/* Spec 0181 — abandoned filter chip. Reuses the drift tone so
              it visually clusters with deadlocked (both warn-amber). */}
          <Tab active={filter === 'abandoned'} onClick={() => handleFilter('abandoned')} dot filterTone="deadlocked" count={counts.abandoned||0} size="sm">abandoned</Tab>
          <Tab active={filter === 'completed'} onClick={() => handleFilter('completed')} dot filterTone="completed" count={counts.completed||0} size="sm">completed</Tab>
        </TabGroup>
        <div style={{ flex: 1 }} />
        {/* Spec 0245 — admin-only Active/Archived toggle. Lives at the
            right edge of the filter strip; flips `useRunList`'s polled
            URL between `/api/runs` and `/api/runs?archived=true`. */}
        {isAdmin && (
          <TabGroup variant="solid" data-testid="archived-view-toggle">
            <Tab
              variant="solid"
              active={!archivedView}
              onClick={() => setArchivedView(false)}
              size="sm"
            >
              Active
            </Tab>
            <Tab
              variant="solid"
              active={archivedView}
              onClick={() => setArchivedView(true)}
              size="sm"
            >
              Archived
            </Tab>
          </TabGroup>
        )}
      </div>

      {/* Column headers -- sortable */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '80px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px 32px',
        padding: '8px 18px',
        background: 'var(--md-surface-container-high)',
        borderBottom: '1px solid var(--md-outline-variant)',
        fontSize: 10, color: 'var(--md-on-surface-muted)',
        fontWeight: 'var(--md-w-semi)',
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
                color: active ? 'var(--md-on-surface)' : undefined,
              }}
              title={`Sort by ${c.label}`}
            >
              <span>{c.label}</span>
              {active && <Mdi name={isAsc ? 'sort-ascending' : 'sort-descending'} size={10} />}
            </div>
          );
        })}
        {/* Spec 0245 — 2 trailing empty cells: archive-button slot + chevron. */}
        <div></div>
        <div></div>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflow: 'auto', background: 'var(--md-surface)' }}>
        {/* Attention section */}
        {hasAttention && (
          <>
            <div style={{
              padding: '6px 18px',
              background: 'var(--md-surface-container-low)',
              borderBottom: '1px solid var(--md-outline-hair)',
              fontSize: 11,
              fontWeight: 'var(--md-w-semi)',
              color: 'var(--md-on-surface-muted)',
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
                borderRadius: 'var(--md-shape-full)',
                color: 'var(--warn)',
              }}>{sortedAttention.length}</span>
            </div>
            {sortedAttention.map((r, idx) => (
              <RunRow key={r.id} run={r} onSelect={onSelect} attentionSummary={_attentionSummary(r)}
                      tourAnchor={idx === 0}
                      isAdmin={isAdmin}
                      archivedView={archivedView}
                      onArchive={setArchiveTarget}
                      onUnarchive={setUnarchiveTarget} />
            ))}
            {sortedNormal.length > 0 && (
              <div style={{
                padding: '6px 18px',
                background: 'var(--md-surface-container-low)',
                borderBottom: '1px solid var(--md-outline-hair)',
                fontSize: 11,
                fontWeight: 'var(--md-w-semi)',
                color: 'var(--md-on-surface-faint)',
              }}>
                Other runs
              </div>
            )}
          </>
        )}
        {sortedNormal.map((r, idx) => (
          <RunRow key={r.id} run={r} onSelect={onSelect}
                  tourAnchor={idx === 0 && !hasAttention}
                  isAdmin={isAdmin}
                  archivedView={archivedView}
                  onArchive={setArchiveTarget}
                  onUnarchive={setUnarchiveTarget} />
        ))}
        {filtered.length === 0 && (
          loading && !search ? (
            <div className="load-card" role="status" aria-label="Loading runs" style={{ padding: '18px' }}>
              {[0,1,2,3,4].map(i => (
                <div key={i} style={{
                  display: 'grid',
                  gridTemplateColumns: '80px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px 32px',
                  alignItems: 'center',
                  padding: '10px 0',
                  borderBottom: '1px solid var(--md-outline-hair)',
                  gap: 8,
                }}>
                  <div className="skel" style={{ width: 52, height: 22, borderRadius: 999 }} />
                  <div className="skel" style={{ width: 80, height: 18 }} />
                  <div className="skel" style={{ width: '80%', height: 14 }} />
                  <div className="skel" style={{ width: 60, height: 14 }} />
                  <div className="skel" style={{ width: 50, height: 14 }} />
                  <div className="skel" style={{ width: 50, height: 14 }} />
                  <div className="skel" style={{ width: 60, height: 14 }} />
                  <div style={{ width: 12 }} />
                  <div style={{ width: 12 }} />
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              padding: '40px 18px',
              textAlign: 'center',
              color: 'var(--md-on-surface-faint)',
              fontSize: 12,
            }}>
              {search ? `No runs matching "${search}"` : 'No runs'}
            </div>
          )
        )}
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--md-outline-hair)',
        background: 'var(--md-surface-container-low)',
        padding: '8px 18px',
        display: 'flex', gap: 18, alignItems: 'center',
        fontSize: 11, color: 'var(--md-on-surface-faint)', fontFamily: 'var(--md-font-data)',
      }}>
        <span>showing {filtered.length} of {runs.length}</span>
        <span style={{ flex: 1 }} />
        <span><kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)', borderRadius: 3, fontSize: 10 }}>/</kbd> search &middot; click header to sort</span>
      </footer>

      {/* Spec 0245 — archive / unarchive confirmation dialogs. Use the
          canonical ModalDialog (Basic variant, max-width 560 px, scrim,
          focus trap, ESC close per DS SPEC.md §4.6). */}
      <ConfirmArchiveDialog
        run={archiveTarget}
        onConfirm={handleArchiveConfirm}
        onCancel={() => setArchiveTarget(null)}
      />
      <ConfirmUnarchiveDialog
        run={unarchiveTarget}
        onConfirm={handleUnarchiveConfirm}
        onCancel={() => setUnarchiveTarget(null)}
      />
    </div>
  );
}

// Spec 0245 — confirmation dialogs. Both use Modal with `variant="single"`
// (== basic), matching the existing allowlist admin destructive-action
// pattern. Error tone on the confirm button signals destructive intent.
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

function RunRow({ run, onSelect, attentionSummary, tourAnchor, isAdmin, archivedView, onArchive, onUnarchive }) {
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

  // Spec 0245 \u2014 soft-delete affordances. Row click is suppressed on
  // archived rows because the detail endpoint 404s on `deleted_at IS
  // NOT NULL` ids (canonical reader is `runs_active`).
  const isArchived = !!run.deletedAt;
  const archivedSecs = isArchived ? _secondsSinceIso(run.deletedAt) : null;

  const showArchiveBtn = hover && isAdmin && !isArchived && !archivedView;
  const showUnarchiveBtn = hover && isAdmin && isArchived;

  return (
    <div
      className={isArchived ? 'run-row--archived' : undefined}
      onClick={() => { if (!isArchived) onSelect?.(run); }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={run.id}
      data-tour-anchor={tourAnchor ? 'run-row' : undefined}
      data-run-id={run.id}
      style={{
        display: 'grid',
        gridTemplateColumns: '80px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px 32px',
        alignItems: 'center',
        padding: '10px 18px',
        borderBottom: '1px solid var(--md-outline-hair)',
        background: hover ? 'var(--md-surface-container-low)' : run.selected ? 'var(--md-surface-container-low)' : 'transparent',
        cursor: isArchived ? 'default' : 'pointer',
        position: 'relative',
        borderLeft: borderColor ? `2px solid ${borderColor}` : '2px solid transparent',
      }}>
      {/* Run id pill */}
      <span className="mono" title={idTooltip} style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        padding: '3px 10px',
        background: 'var(--md-surface-container-high)',
        border: '1px solid var(--md-outline-hair)',
        borderRadius: 999,
        fontSize: 11.5,
        color: 'var(--md-on-surface-variant)',
        letterSpacing: '0.04em',
        width: 'fit-content',
      }}>{displayId}</span>
      <StatusBadge status={run.status} />
      {/* SPEC-0087 § A — column-gap between STATUS pill and TOPIC bumped
          from 8 to 20 px per the user's 12.52 + 13.22 complaint. The
          tighter spacing pre-spec made the topic text read crammed
          against the pill. */}
      <div style={{ minWidth: 0, paddingLeft: 20, paddingRight: 16 }} title={run.topic}>
        <div style={{
          color: 'var(--md-on-surface)', fontSize: 12.5,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{shortTopic}</div>
        {attentionSummary && (
          <div className="mono" style={{
            fontSize: 10, color: 'var(--md-on-surface-faint)', marginTop: 2,
          }}>{attentionSummary}</div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <PhaseMini phase={run.phase} status={run.status} />
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-muted)' }}>P{run.phase}</span>
        {run.rounds && (run.phase === 2 || run.phase === 4) && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>&middot; {run.rounds}</span>
        )}
      </div>
      <span className="mono" style={{ fontSize: 11.5, color: 'var(--md-on-surface-muted)' }}>{run.startedAt || run.startedAtAgo > 0 ? fmt.relTime(run.startedAtAgo) : '—'}</span>
      <span className="mono num" style={{ fontSize: 11.5, color: 'var(--md-on-surface-muted)' }}>{fmt.duration(run.duration)}</span>
      <span className="mono num" style={{ fontSize: 12, color: 'var(--md-on-surface)', textAlign: 'right' }}>{fmt.cost(run.cost)}</span>
      {/* Spec 0245 — archive-slot column. Visible only on hover for
          admins on non-archived rows; unarchive replaces it on archived
          rows. Stays mounted (empty span) at other times so row grid
          columns don't reflow. */}
      <span style={{ display: 'inline-flex', justifyContent: 'center' }}>
        {showArchiveBtn && (
          <button
            type="button"
            className="md-icon-btn"
            onClick={(e) => { e.stopPropagation(); onArchive?.(run); }}
            aria-label={`Archive run ${displayId}`}
            title="Archive run"
            style={{ width: 28, height: 28 }}
          >
            <Icon.Archive />
          </button>
        )}
        {showUnarchiveBtn && (
          <button
            type="button"
            className="md-icon-btn"
            onClick={(e) => { e.stopPropagation(); onUnarchive?.(run); }}
            aria-label={`Restore run ${displayId}`}
            title="Restore run"
            style={{ width: 28, height: 28 }}
          >
            <Icon.ArchiveUp />
          </button>
        )}
      </span>
      {/* Spec 0245 — chevron column replaced by `archived <relTime> ·
          by <email>` caption when the row is archived. */}
      {isArchived ? (
        <span
          className="mono"
          title={`archived ${run.deletedAt} by ${run.deletedBy || 'unknown'}`}
          style={{
            fontSize: 10,
            color: 'var(--md-on-surface-faint)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            textAlign: 'right',
          }}
        >
          {`archived ${fmt.relTime(archivedSecs || 0)}${run.deletedBy ? ` · by ${run.deletedBy}` : ''}`}
        </span>
      ) : (
        <Icon.Chevron style={{ color: hover ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-decor)' }} />
      )}
    </div>
  );
}

// Spec 0245 — local helper; mirrors `_seconds_since_iso` in server.py
// so the archived-caption `archived <relTime>` reads consistently.
function _secondsSinceIso(iso) {
  if (!iso) return 0;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

// 6-dot phase mini-strip
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

Object.assign(window, { RunListView });
