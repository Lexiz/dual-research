// run-list.jsx — list of recent runs

function RunListView({ runs, onSelect }) {
  const [filter, setFilter] = React.useState('all');
  const counts = runs.reduce((a, r) => ({ ...a, [r.status]: (a[r.status] || 0) + 1 }), {});

  const visible = filter === 'all' ? runs : runs.filter(r => r.status === filter);

  const totalCost = runs.reduce((a, r) => a + r.cost, 0);
  const running = runs.filter(r => r.status === 'running').length;

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
              background: 'linear-gradient(135deg, var(--agent-a) 0%, var(--agent-a) 50%, var(--agent-b) 50%, var(--agent-b) 100%)',
              flexShrink: 0,
            }} />
            <span className="mono" style={{ fontSize: 12, color: 'var(--fg-1)', letterSpacing: '0.02em' }}>
              dual&#8209;research
            </span>
          </div>
          <span style={{ color: 'var(--fg-4)' }}>·</span>
          <span style={{ color: 'var(--fg-1)', fontSize: 12 }}>runs</span>
        </div>

        <div style={{ minWidth: 0 }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
            {runs.length} run{runs.length === 1 ? '' : 's'} · {running} running · ∑ cost {fmt.cost(totalCost)}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', whiteSpace: 'nowrap' }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>SSE&nbsp;live</span>
          <Dot color={COLORS.info} pulse="pulse-a" size={7} />
        </div>
      </header>

      {/* Filter strip */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 18px',
        background: 'var(--bg-1)',
        borderBottom: '1px solid var(--border-1)',
      }}>
        {[
          ['all',        'all',        runs.length,        null],
          ['running',    'running',    counts.running||0,  COLORS.info],
          ['converged',  'converged',  counts.converged||0,COLORS.ok],
          ['deadlocked', 'deadlocked', counts.deadlocked||0, COLORS.warn],
          ['errored',    'errored',    counts.errored||0,  COLORS.err],
          ['completed',  'completed',  counts.completed||0,COLORS.ok],
        ].map(([k, label, n, color]) => (
          <button key={k} onClick={() => setFilter(k)} style={{
            padding: '4px 10px',
            background: filter === k ? 'var(--bg-3)' : 'var(--bg-2)',
            color: filter === k ? 'var(--fg-0)' : 'var(--fg-2)',
            border: '1px solid var(--border-1)',
            borderRadius: 4,
            fontSize: 11,
            fontFamily: 'var(--mono)',
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            {color && <Dot color={color} size={5} />}
            <span>{label}</span>
            <span style={{ color: 'var(--fg-4)' }}>{n}</span>
          </button>
        ))}
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '110px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px',
        padding: '8px 18px',
        background: 'var(--bg-1)',
        borderBottom: '1px solid var(--border-1)',
        fontSize: 10, color: 'var(--fg-3)',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}>
        <div>run id</div>
        <div>status</div>
        <div>topic</div>
        <div>phase</div>
        <div>started</div>
        <div>duration</div>
        <div style={{ textAlign: 'right' }}>cost</div>
        <div></div>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-0)' }}>
        {visible.map((r) => (
          <RunRow key={r.id} run={r} onSelect={onSelect} />
        ))}
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-1)',
        background: 'var(--bg-1)',
        padding: '8px 18px',
        display: 'flex', gap: 18, alignItems: 'center',
        fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
      }}>
        <span>showing {visible.length} of {runs.length}</span>
        <span style={{ flex: 1 }} />
        <span>↑↓ navigate · ⏎ open · / filter</span>
      </footer>
    </div>
  );
}

function RunRow({ run, onSelect }) {
  const phaseLabel = PHASES[run.phase]?.label || 'done';
  const [hover, setHover] = React.useState(false);
  const phasePct = run.phase / 5;
  const idParts = window.splitRunId(run.id);
  const shortTopic = window.formatTopic(run.topic, { maxChars: 110 });

  return (
    <div
      onClick={() => onSelect?.(run)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={run.id}
      style={{
        display: 'grid',
        gridTemplateColumns: '110px 110px minmax(0, 1fr) 110px 110px 90px 100px 32px',
        alignItems: 'center',
        padding: '10px 18px',
        borderBottom: '1px solid var(--border-1)',
        background: hover ? 'var(--bg-1)' : run.selected ? 'var(--bg-1)' : 'transparent',
        cursor: 'pointer',
        position: 'relative',
      }}>
      {run.selected && (
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 2, background: COLORS.info }} />
      )}
      {/* Run id cell: 4-char display id on top, time + slug suffix below. */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <span className="mono" style={{
          fontSize: 13, color: 'var(--fg-0)', fontWeight: 500,
          letterSpacing: '0.02em',
        }}>{run.displayId || run.id.slice(0, 4)}</span>
        <span className="mono" style={{
          fontSize: 10, color: 'var(--fg-3)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{idParts.time}{idParts.slug ? ` · ${idParts.slug}` : ''}</span>
      </div>
      <StatusBadge status={run.status} />
      <div style={{ minWidth: 0, paddingRight: 16 }} title={run.topic}>
        <div style={{
          color: 'var(--fg-0)', fontSize: 12.5,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{shortTopic}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <PhaseMini phase={run.phase} status={run.status} />
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>P{run.phase}</span>
        {run.rounds && (run.phase === 2 || run.phase === 4) && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>· {run.rounds}</span>
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
