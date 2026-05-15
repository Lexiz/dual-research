// errors.jsx — chronological error log view

// Sample errors. Wire this to the orchestrator's error stream later.
const ERRORS_LOG = [
  {
    id: 'e-008',
    timestamp: '2026-05-15 08:22:14',
    relAgo: 6 * 60 + 4,
    code: 'STREAM_DISCONNECTED',
    severity: 'error',
    runId: '7eed',
    agent: 'gpt',
    phase: 2,
    where: 'phase-2 / round-3 / gpt',
    summary: 'Upstream provider closed SSE connection mid-token.',
    detail:
`Last byte: "…the regressivity claim should be subordina"
Retry policy: max=2  attempts=2  next=halt
Orchestrator state preserved at .dr/runs/7eed/checkpoint.json`,
    retried: 2,
    resolved: 'halted',
  },
  {
    id: 'e-007',
    timestamp: '2026-05-15 06:01:38',
    relAgo: 2 * 3600 + 26 * 60,
    code: 'RATE_LIMIT_EXCEEDED',
    severity: 'warning',
    runId: '7f29',
    agent: 'claude',
    phase: 3,
    where: 'phase-3 / drafter (claude)',
    summary: 'Provider returned 429; cooldown 24s before retry.',
    detail:
`HTTP 429 from upstream. Retry-After header: 24 seconds.
Backoff applied. Resumed at 06:02:02 (turn continued from same offset).`,
    retried: 1,
    resolved: 'recovered',
  },
  {
    id: 'e-006',
    timestamp: '2026-05-14 16:08:42',
    relAgo: 1 * 86400 + 16 * 3600,
    code: 'CONTEXT_OVERFLOW',
    severity: 'error',
    runId: '7e7c',
    agent: 'claude',
    phase: 2,
    where: 'phase-2 / round-9 / claude',
    summary: 'Context window exceeded provider maximum after 9 rounds.',
    detail:
`Cumulative input tokens: 204,118. Provider limit: 200,000.
Compression failed: no summarization checkpoint available for round 1-4.
Forced phase advance to P3 with degraded context — recorded as quality warning on the final document.`,
    retried: 0,
    resolved: 'degraded',
  },
  {
    id: 'e-005',
    timestamp: '2026-05-14 11:44:21',
    relAgo: 1 * 86400 + 20 * 3600,
    code: 'TIMEOUT_EXCEEDED',
    severity: 'warning',
    runId: '7e7c',
    agent: 'gpt',
    phase: 2,
    where: 'phase-2 / round-5 / gpt',
    summary: 'Turn exceeded 180s soft timeout; allowed to continue.',
    detail:
`GPT turn took 214 seconds (soft cap 180s, hard cap 300s).
Soft cap is informational; no action taken. Turn completed normally at 214s.`,
    retried: 0,
    resolved: 'recovered',
  },
  {
    id: 'e-004',
    timestamp: '2026-05-13 23:11:09',
    relAgo: 2 * 86400 + 9 * 3600,
    code: 'INVALID_TURN_FORMAT',
    severity: 'error',
    runId: '7d10',
    agent: 'claude',
    phase: 4,
    where: 'phase-4 / round-2 / claude',
    summary: 'Model returned a review without the required structured-review wrapper.',
    detail:
`Expected: { accept: [...], reject: [...], partial: [...] }
Received: free-form prose without JSON wrapper.
Reprompted with format reminder. Second attempt succeeded.`,
    retried: 1,
    resolved: 'recovered',
  },
  {
    id: 'e-003',
    timestamp: '2026-05-13 08:30:02',
    relAgo: 2 * 86400 + 23 * 3600,
    code: 'CHECKPOINT_WRITE_FAILED',
    severity: 'warning',
    runId: '7cf1',
    agent: null,
    phase: 2,
    where: 'orchestrator',
    summary: 'Could not write round-3 checkpoint to disk.',
    detail:
`fs.writeFile to .dr/runs/7cf1/checkpoint-3.json failed with ENOSPC.
Run continued in memory; final checkpoint succeeded at run completion (disk had freed up).`,
    retried: 0,
    resolved: 'recovered',
  },
  {
    id: 'e-002',
    timestamp: '2026-05-12 22:19:53',
    relAgo: 3 * 86400 + 9 * 3600,
    code: 'ORCHESTRATOR_PANIC',
    severity: 'critical',
    runId: '7c84',
    agent: null,
    phase: 3,
    where: 'orchestrator / drafter-handoff',
    summary: 'Drafter assignment race: both agents marked as drafter for ~40ms.',
    detail:
`State store transitioned through an inconsistent intermediate where both agents
held the drafter role. No tokens were produced during the window (both blocked
on lock acquisition). Recovery deterministically picked Claude as drafter
(lower agent id). Run continued without observable corruption.`,
    retried: 0,
    resolved: 'recovered',
  },
  {
    id: 'e-001',
    timestamp: '2026-05-11 14:02:11',
    relAgo: 4 * 86400 + 18 * 3600,
    code: 'STREAM_DISCONNECTED',
    severity: 'error',
    runId: '7b22',
    agent: 'claude',
    phase: 1,
    where: 'phase-1 / claude / plan-draft',
    summary: 'Mid-draft disconnect; reconnected and resumed from token offset.',
    detail:
`Connection dropped at byte offset 4,182. Reconnect at 14:02:18 (delay 7s).
Provider returned with continuation prompt; output rejoined cleanly.`,
    retried: 1,
    resolved: 'recovered',
  },
];

const SEVERITY_META = {
  critical: { color: COLORS.err,  label: 'critical' },
  error:    { color: COLORS.err,  label: 'error' },
  warning:  { color: COLORS.warn, label: 'warning' },
  info:     { color: COLORS.info, label: 'info' },
};

const RESOLUTION_META = {
  halted:    { color: COLORS.err,  label: 'halted' },
  degraded:  { color: COLORS.warn, label: 'degraded' },
  recovered: { color: COLORS.ok,   label: 'recovered' },
};

function ErrorsView() {
  const [filter, setFilter] = React.useState('all');
  const [openId, setOpenId] = React.useState(null);

  const counts = ERRORS_LOG.reduce((a, e) => {
    a[e.severity] = (a[e.severity] || 0) + 1;
    return a;
  }, {});

  const visible = filter === 'all'
    ? ERRORS_LOG
    : ERRORS_LOG.filter(e => e.severity === filter);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--bg-0)' }}>
      {/* Header */}
      <header style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, auto) minmax(0, 1fr) minmax(0, auto)',
        alignItems: 'center',
        gap: 24,
        padding: '14px 24px',
        borderBottom: '1px solid var(--border-1)',
        background: 'var(--bg-0)',
        flexShrink: 0,
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0,
          height: 2, background: COLORS.err,
        }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
          <span style={{ color: COLORS.err }}><Icon.Warn /></span>
          <span style={{ fontSize: 14, color: 'var(--fg-0)', fontWeight: 600 }}>Errors</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
            {ERRORS_LOG.length} total · last 7 days
          </span>
        </div>
        <div style={{ minWidth: 0 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, whiteSpace: 'nowrap' }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
            ingesting from orchestrator
          </span>
          <Dot color={COLORS.info} pulse="pulse-a" size={6} />
        </div>
      </header>

      {/* Filter strip */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '12px 24px',
        borderBottom: '1px solid var(--border-1)',
        background: 'var(--bg-1)',
        flexShrink: 0,
      }}>
        <FilterChip label="all" count={ERRORS_LOG.length} active={filter === 'all'} onClick={() => setFilter('all')} />
        <FilterChip label="critical" count={counts.critical || 0} color={COLORS.err}  active={filter === 'critical'} onClick={() => setFilter('critical')} />
        <FilterChip label="error"    count={counts.error || 0}    color={COLORS.err}  active={filter === 'error'}    onClick={() => setFilter('error')} />
        <FilterChip label="warning"  count={counts.warning || 0}  color={COLORS.warn} active={filter === 'warning'}  onClick={() => setFilter('warning')} />
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
          newest first · click row to expand
        </span>
      </div>

      {/* List */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <div style={{ padding: '14px 24px 28px', maxWidth: 1280, margin: '0 auto' }}>
          {visible.map((e) => (
            <ErrorCard
              key={e.id}
              error={e}
              open={openId === e.id}
              onToggle={() => setOpenId(openId === e.id ? null : e.id)}
            />
          ))}
          {visible.length === 0 && (
            <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)' }}>
              <div className="mono" style={{ fontSize: 12 }}>no errors matching this filter</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterChip({ label, count, color, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      height: 28, padding: '0 12px',
      background: active ? 'var(--bg-3)' : 'var(--bg-2)',
      border: `1px solid ${active ? 'var(--border-3)' : 'var(--border-1)'}`,
      borderRadius: 'var(--r-2)',
      whiteSpace: 'nowrap',
    }}>
      {color && <Dot color={color} size={6} />}
      <span style={{
        fontSize: 12, color: active ? 'var(--fg-0)' : 'var(--fg-2)',
        fontWeight: active ? 500 : 400,
        textTransform: 'lowercase',
      }}>{label}</span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{count}</span>
    </button>
  );
}

function ErrorCard({ error, open, onToggle }) {
  const [hover, setHover] = React.useState(false);
  const sev = SEVERITY_META[error.severity];
  const res = RESOLUTION_META[error.resolved];

  return (
    <article
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        marginBottom: 8,
        background: 'var(--bg-1)',
        border: `1px solid ${open ? 'var(--border-2)' : 'var(--border-1)'}`,
        borderLeft: `3px solid ${sev.color}`,
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
        transition: 'border-color 120ms',
      }}>
      <button onClick={onToggle} style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '12px 14px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          {/* Left side: timestamp + code */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 200, flexShrink: 0 }}>
            <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', whiteSpace: 'nowrap' }}>
              {error.timestamp}
              <span style={{ color: 'var(--fg-4)', marginLeft: 8 }}>· {fmt.relTime(error.relAgo)}</span>
            </span>
            <span className="mono" style={{
              fontSize: 12.5, color: sev.color, fontWeight: 600, letterSpacing: '0.02em',
              whiteSpace: 'nowrap',
            }}>{error.code}</span>
          </div>

          {/* Middle: summary */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, color: 'var(--fg-0)', lineHeight: 1.45, marginBottom: 4 }}>
              {error.summary}
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12,
              fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
              whiteSpace: 'nowrap',
            }}>
              {error.agent && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                  <AgentIcon agent={error.agent} size={12} variant="ghost" />
                  <span style={{ color: 'var(--fg-1)' }}>{AGENT_META[error.agent].name}</span>
                </span>
              )}
              {!error.agent && <span style={{ color: 'var(--fg-2)' }}>orchestrator</span>}
              <span style={{ color: 'var(--fg-4)' }}>·</span>
              <span>P{error.phase}</span>
              <span style={{ color: 'var(--fg-4)' }}>·</span>
              <span>run <span style={{ color: 'var(--fg-1)' }}>{error.runId}</span></span>
              {error.retried > 0 && (
                <>
                  <span style={{ color: 'var(--fg-4)' }}>·</span>
                  <span>retried {error.retried}×</span>
                </>
              )}
            </div>
          </div>

          {/* Right: resolution + chevron */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <span className="mono" style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '2px 8px',
              fontSize: 10.5, color: res.color,
              background: res.color + '14',
              border: `1px solid ${res.color}44`,
              borderRadius: 999,
              whiteSpace: 'nowrap', letterSpacing: '0.02em',
            }}>{res.label}</span>
            <span style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: 18, height: 18,
              opacity: open ? 0.6 : hover ? 0.6 : 0.25,
              transition: 'opacity 120ms',
              color: 'var(--fg-2)',
              transform: open ? 'rotate(90deg)' : 'none',
            }}>
              <Icon.Chevron />
            </span>
          </div>
        </div>
      </button>

      {open && (
        <div style={{
          padding: '14px',
          borderTop: '1px dashed var(--border-1)',
          background: 'var(--bg-0)',
        }}>
          <div style={{ marginBottom: 14 }}>
            <div style={{
              fontSize: 10, color: 'var(--fg-3)',
              letterSpacing: '0.08em', textTransform: 'uppercase',
              fontWeight: 500, marginBottom: 6,
            }}>Location</div>
            <div className="mono" style={{ fontSize: 12, color: 'var(--fg-1)' }}>{error.where}</div>
          </div>
          <div>
            <div style={{
              fontSize: 10, color: 'var(--fg-3)',
              letterSpacing: '0.08em', textTransform: 'uppercase',
              fontWeight: 500, marginBottom: 6,
            }}>Detail</div>
            <pre className="mono" style={{
              margin: 0, padding: '10px 12px',
              fontSize: 11.5, color: 'var(--fg-1)',
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-2)',
              whiteSpace: 'pre-wrap', lineHeight: 1.6,
            }}>{error.detail}</pre>
          </div>
        </div>
      )}
    </article>
  );
}

Object.assign(window, { ErrorsView, ErrorCard, ERRORS_LOG, SEVERITY_META, RESOLUTION_META });
