// run-detail.jsx — v4: card-based timeline + phase-tabbed disagreement explorer
//
//   ┌─ top bar
//   ├─ phase strip
//   ├─ left: artifact cards (collapsible)   │  right: disagreements by phase (tabbed)
//   └─ footer

// ─────────────────── Top bar — two stacked rows ───────────────────
function TopBar({ run }) {
  const ctx = React.useContext(window.RunContext) || {};
  const onBack = () => ctx.navigate ? ctx.navigate('list') : (window.location.hash = '#/');
  const total = run.agents.claude.cost + run.agents.gpt.cost;
  const idParts = window.splitRunId(run.id);
  const startedClock = idParts.time || '—';
  const elapsedTotal = Object.values(run.phaseTimings || {}).filter(Boolean).reduce((a, b) => a + b, 0);
  const elapsedLabel = elapsedTotal > 0 ? fmt.duration(elapsedTotal) : '—';
  const drafterLabel = run.drafter ? (AGENT_META[run.drafter]?.name || run.drafter) : '—';

  return (
    <header style={{
      display: 'flex', flexDirection: 'column',
      padding: '10px 24px 12px',
      borderBottom: '1px solid var(--border-1)',
      background: 'var(--bg-0)',
      flexShrink: 0,
      gap: 6,
    }}>
      {/* Row 1: back · brand · id chip · spacer · cost · status */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14, whiteSpace: 'nowrap',
      }}>
        <BackChip onClick={onBack} />
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 14, height: 14, borderRadius: 3,
            background: 'linear-gradient(135deg, var(--agent-a) 0 50%, var(--agent-b) 50% 100%)',
          }} />
          <span style={{ fontSize: 13, color: 'var(--fg-1)' }}>dual&#8209;research</span>
        </span>
        <RunIdChip runId={run.id} displayId={run.displayId} />
        <div style={{ flex: 1 }} />
        <span className="mono num" style={{ fontSize: 13, color: 'var(--fg-1)' }}>
          {fmt.cost(total)}
          {run.budget?.limit != null && (
            <span style={{ color: 'var(--fg-3)' }}> / ${run.budget.limit.toFixed(2)}</span>
          )}
        </span>
        <StatusBadge status={run.status} />
      </div>

      {/* Row 2: topic (clamped to 2 lines) + meta line */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingLeft: 92 }}>
        <div title={run.topic} style={{
          color: 'var(--fg-0)', fontSize: 14, lineHeight: 1.35,
          display: '-webkit-box',
          WebkitBoxOrient: 'vertical',
          WebkitLineClamp: 2,
          overflow: 'hidden',
        }}>{run.topic || '— no topic —'}</div>
        <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
          started <span style={{ color: 'var(--fg-1)' }}>{startedClock}</span>
          {' · '}drafter <span style={{ color: 'var(--fg-1)' }}>{drafterLabel}</span>
          {' · '}<span style={{ color: 'var(--fg-1)' }}>{elapsedLabel}</span> elapsed
        </div>
      </div>
    </header>
  );
}

function BackChip({ onClick }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title="Back to All runs"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 26, padding: '0 10px',
        background: hover ? 'var(--bg-2)' : 'var(--bg-1)',
        border: '1px solid var(--border-2)',
        borderRadius: 'var(--r-2)',
        color: 'var(--fg-1)',
        fontSize: 11.5,
        cursor: 'pointer',
        transition: 'background 120ms',
      }}>
      <span style={{ fontSize: 12, lineHeight: 1 }}>←</span>
      <span>All runs</span>
    </button>
  );
}

function RunIdChip({ runId, displayId }) {
  const [hover, setHover] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const onClick = async () => {
    try {
      await navigator.clipboard?.writeText(runId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (e) { /* clipboard blocked — silent */ }
  };
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={copied ? 'Copied!' : `Click to copy ${runId}`}
      className="mono"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 12px',
        background: hover ? 'var(--bg-3)' : 'var(--bg-2)',
        border: '1px solid var(--border-1)',
        borderRadius: 999,
        color: 'var(--fg-1)',
        fontSize: 11.5,
        fontWeight: 500,
        letterSpacing: '0.04em',
        cursor: 'pointer',
        transition: 'background 120ms',
      }}>
      <span>{displayId || runId.slice(0, 4)}</span>
      {copied && <span style={{ fontSize: 9.5, color: 'var(--ok)' }}>copied</span>}
    </button>
  );
}

function PhaseStrip({ run, errorCount, showErrors, onToggleErrors }) {
  const { phase, status, phaseTimings, round } = run;
  const totalElapsed = Object.values(phaseTimings).filter(Boolean).reduce((a, b) => a + b, 0);
  const phaseLabel = PHASES[phase]?.label || 'Done';
  const inCapPhase = phase === 2 || phase === 4;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 20,
      padding: '12px 24px',
      borderBottom: '1px solid var(--border-1)',
      background: 'var(--bg-0)',
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {PHASES.map((p, i) => {
          const completed = p.id < phase || (status === 'completed' && p.id <= 5);
          const current = p.id === phase && status !== 'completed';
          const failed = (status === 'errored' || status === 'deadlocked') && p.id === phase;
          const color = failed
            ? (status === 'errored' ? COLORS.err : COLORS.warn)
            : current ? COLORS.info
            : completed ? COLORS.ok
            : 'var(--border-3)';
          const isLast = i === PHASES.length - 1;
          return (
            <React.Fragment key={p.id}>
              <span style={{
                position: 'relative',
                width: 8, height: 8, borderRadius: '50%',
                background: completed || current || failed ? color : 'transparent',
                border: completed || current || failed ? 'none' : `1px solid ${color}`,
                flexShrink: 0,
              }}>
                {current && <span className="pulse-a" style={{ position: 'absolute', inset: -3, borderRadius: '50%' }} />}
              </span>
              {!isLast && (
                <span style={{
                  width: 22, height: 1,
                  background: completed ? COLORS.ok : 'var(--border-2)',
                  opacity: completed ? 0.5 : 1,
                }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, whiteSpace: 'nowrap' }}>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', letterSpacing: '0.04em' }}>
          PHASE&nbsp;{phase}
        </span>
        <span style={{ fontSize: 13.5, color: 'var(--fg-0)', fontWeight: 500 }}>{phaseLabel}</span>
      </div>
      <div style={{ flex: 1 }} />
      {inCapPhase && status === 'running' && <RoundIndicator round={round} />}
      {status === 'deadlocked' && (
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.warn }}>
          hard cap reached · {round.current}/{round.hard}
        </span>
      )}
      {status === 'errored' && (
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.err }}>
          halted · {run.error?.code}
        </span>
      )}
      {status === 'completed' && (
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.ok }}>
          converged in {fmt.duration(totalElapsed)}
        </span>
      )}
      <ErrorsToggleButton count={errorCount} active={showErrors} onClick={onToggleErrors} />
    </div>
  );
}

function ErrorsToggleButton({ count, active, onClick }) {
  const [hover, setHover] = React.useState(false);
  const hasErrors = count > 0;
  const color = hasErrors ? COLORS.err : 'var(--fg-3)';
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 26, padding: '0 10px',
        background: active ? (hasErrors ? color + '1c' : 'var(--bg-3)')
                  : hover  ? 'var(--bg-2)'
                  : 'var(--bg-1)',
        border: `1px solid ${active ? (hasErrors ? color + '66' : 'var(--border-3)') : 'var(--border-1)'}`,
        borderRadius: 'var(--r-2)',
        whiteSpace: 'nowrap',
        color: hasErrors ? color : 'var(--fg-2)',
        transition: 'background 120ms, border-color 120ms',
      }}>
      {active ? (
        <>
          <span style={{ display: 'inline-block', transform: 'rotate(180deg)' }}>
            <Icon.Arrow />
          </span>
          <span style={{ fontSize: 11.5, color: 'var(--fg-1)' }}>Back to timeline</span>
        </>
      ) : (
        <>
          <Icon.Warn />
          <span style={{ fontSize: 11.5 }}>
            {count === 0 ? 'No errors' : `${count} error${count === 1 ? '' : 's'}`}
          </span>
        </>
      )}
    </button>
  );
}

function RoundIndicator({ round }) {
  const pct = (round.current / round.hard) * 100;
  const softPct = (round.soft / round.hard) * 100;
  const overSoft = round.current >= round.soft;
  const overHard = round.current >= round.hard;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
      <span style={{ fontSize: 12, color: 'var(--fg-2)' }}>round</span>
      <span className="mono num" style={{ fontSize: 13, color: 'var(--fg-0)' }}>
        {round.current}<span style={{ color: 'var(--fg-3)' }}>&nbsp;/&nbsp;{round.soft}</span>
      </span>
      <div style={{ position: 'relative', width: 100, height: 3, background: 'var(--bg-3)', borderRadius: 999 }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct}%`,
          background: overHard ? COLORS.err : overSoft ? COLORS.warn : COLORS.info,
          borderRadius: 999,
          transition: 'width 300ms ease',
        }} />
        <span style={{ position: 'absolute', top: -2, bottom: -2, left: `${softPct}%`, width: 1, background: 'var(--border-3)' }} />
      </div>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        hard&nbsp;{round.hard}
      </span>
    </div>
  );
}

// ─────────────────── Timeline ───────────────────
function Timeline({ run }) {
  const items = React.useMemo(() => buildTimeline(run), [run]);
  // expansion state — live items default expanded
  const defaultExpanded = new Set(items.filter(i => i.live).map(i => i.id));
  const [expanded, setExpanded] = React.useState(defaultExpanded);
  React.useEffect(() => {
    setExpanded(new Set(items.filter(i => i.live).map(i => i.id)));
    // eslint-disable-next-line
  }, [run.id, run.phase, run.status]);

  const toggle = (id) => setExpanded(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const artifactCount = items.filter(i => i.kind !== 'phase-divider' && i.kind !== 'error' && i.kind !== 'deadlock').length;
  const liveCount = items.filter(i => i.live).length;
  const claudeTotal = run.agents.claude;
  const gptTotal = run.agents.gpt;

  return (
    <section style={{
      display: 'flex', flexDirection: 'column',
      borderRight: '1px solid var(--border-1)',
      minWidth: 0, minHeight: 0,
    }}>
      <PaneHeader
        title="Timeline"
        count={`${artifactCount} artifacts`}
        accentGradient="linear-gradient(to right, var(--agent-a) 0%, var(--agent-a) 48%, var(--agent-b) 52%, var(--agent-b) 100%)"
      />
      <PaneToolbar>
        <AgentLegendChip agent="claude" tokens={claudeTotal.tokens.in + claudeTotal.tokens.out} cost={claudeTotal.cost} />
        <AgentLegendChip agent="gpt"    tokens={gptTotal.tokens.in + gptTotal.tokens.out} cost={gptTotal.cost} />
        <span style={{ flex: 1 }} />
        {liveCount > 0 && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '3px 8px',
            background: 'rgba(107,156,240,0.10)',
            border: '1px solid rgba(107,156,240,0.30)',
            borderRadius: 999,
            fontSize: 11, color: COLORS.info,
            fontFamily: 'var(--mono)',
            whiteSpace: 'nowrap',
          }}>
            <span className="pulse-a" style={{ width: 6, height: 6, borderRadius: '50%', background: COLORS.info }} />
            {liveCount} live
          </span>
        )}
      </PaneToolbar>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '8px 16px 24px', background: 'var(--bg-0)' }}>
        {items.map((item) => (
          <TimelineItem
            key={item.id}
            item={item}
            run={run}
            expanded={expanded.has(item.id)}
            onToggle={() => toggle(item.id)}
          />
        ))}
      </div>
    </section>
  );
}

function AgentLegendChip({ agent, tokens, cost }) {
  const meta = AGENT_META[agent];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 8px 3px 6px',
      background: 'var(--bg-2)',
      border: `1px solid ${meta.border}`,
      borderRadius: 999,
      whiteSpace: 'nowrap',
    }}>
      <AgentIcon agent={agent} size={14} />
      <span style={{ fontSize: 11.5, color: 'var(--fg-1)' }}>{meta.name}</span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        {fmt.tokens(tokens)}t · {fmt.cost(cost)}
      </span>
    </span>
  );
}

// ─────────────────── Pane shell components ───────────────────

// Pane header — fixed 52px, with a colored accent bar at top.
// `accentGradient` for multi-color, `accentColor` for solid.
function PaneHeader({ title, count, right, accentGradient, accentColor }) {
  const accent = accentGradient
    ? { background: accentGradient }
    : { background: accentColor || COLORS.info };
  return (
    <div style={{
      height: 52,
      flexShrink: 0,
      position: 'relative',
      display: 'flex', alignItems: 'center',
      padding: '0 24px',
      background: 'var(--bg-1)',
      borderBottom: '1px solid var(--border-1)',
    }}>
      {/* 2px accent at top */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 2, ...accent,
      }} />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flex: 1, minWidth: 0, whiteSpace: 'nowrap' }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-0)', letterSpacing: '-0.005em' }}>
          {title}
        </span>
        {count != null && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
            {count}
          </span>
        )}
      </div>
      {right}
    </div>
  );
}

// Pane toolbar — fixed 44px, subtle bg to differentiate from content.
function PaneToolbar({ children }) {
  return (
    <div style={{
      height: 44,
      flexShrink: 0,
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '0 24px',
      background: 'var(--bg-1)',
      borderBottom: '1px solid var(--border-1)',
    }}>{children}</div>
  );
}

// Group header — tinted full-row bar with label + count. Used for OPEN /
// RESOLVED / ERRORS sections. The same shape as phase dividers in the
// timeline, just with status-keyed colors instead of neutral grey.
function GroupHeader({ label, color, count, style, tone = 'tinted' }) {
  const bg = tone === 'neutral'
    ? 'var(--bg-2)'
    : color + '14';
  const border = tone === 'neutral'
    ? 'var(--border-1)'
    : color + '44';
  const labelColor = tone === 'neutral' ? 'var(--fg-2)' : color;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px',
      marginTop: 16, marginBottom: 8,
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 'var(--r-2)',
      whiteSpace: 'nowrap',
      ...style,
    }}>
      <span style={{
        fontSize: 11, fontWeight: 700, color: labelColor,
        letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>{label}</span>
      <span style={{ flex: 1 }} />
      {count != null && (
        <span className="mono num" style={{
          fontSize: 11.5, color: labelColor, fontWeight: 600,
        }}>{count}</span>
      )}
    </div>
  );
}

// Build flat ordered list — delegates to live-data.jsx's buildLiveTimeline
// which knows how to derive items from a live Run + on-disk filename
// conventions.
function buildTimeline(run) {
  return window.buildLiveTimeline(run);
}

// ─────────────────── Timeline items ───────────────────
function TimelineItem({ item, run, expanded, onToggle }) {
  if (item.kind === 'phase-divider') return <PhaseDivider item={item} run={run} />;
  if (item.kind === 'error')         return <ErrorCard item={item} />;
  if (item.kind === 'deadlock')      return <DeadlockCard item={item} />;
  return <ArtifactCard item={item} expanded={expanded} onToggle={onToggle} />;
}

function PhaseDivider({ item, run }) {
  const p = PHASES[item.phaseId];
  const current = item.phaseId === run.phase && run.status !== 'completed';
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px',
      marginTop: 16, marginBottom: 8,
      background: 'var(--bg-2)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      whiteSpace: 'nowrap',
    }}>
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-2)',
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600,
      }}>
        Phase&nbsp;{item.phaseId}
      </span>
      <span style={{ color: 'var(--fg-4)' }}>·</span>
      <span style={{ fontSize: 12.5, color: 'var(--fg-1)', fontWeight: current ? 600 : 500 }}>
        {p.label}
      </span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        {item.duration ? fmt.duration(item.duration) : '—'}
        {item.extra ? ` · ${item.extra}` : ''}
      </span>
    </div>
  );
}

// The unified card
function ArtifactCard({ item, expanded, onToggle }) {
  const meta = item.agent ? AGENT_META[item.agent] : null;
  const [hover, setHover] = React.useState(false);

  // Header content varies by kind
  const header = (
    <ArtifactHeader item={item} meta={meta} expanded={expanded} hover={hover} />
  );

  const accentColor = meta?.color || 'var(--fg-2)';
  const isLive = item.live;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        marginBottom: 6,
        background: 'var(--bg-1)',
        border: `1px solid ${expanded ? 'var(--border-2)' : 'var(--border-1)'}`,
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
        transition: 'border-color 120ms, background 120ms',
        ...(isLive ? {
          borderLeft: `2px solid ${accentColor}`,
        } : {}),
      }}
    >
      <button onClick={onToggle} style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '10px 12px',
        background: hover && !expanded ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        {header}
      </button>
      {expanded && <ArtifactBody item={item} />}
    </div>
  );
}

// Small mono chips surfacing parsed protocol stats on a turn/plan row.
// Stays out of the way: nothing rendered when stats are absent.
function StatsChips({ stats, phase }) {
  if (!stats) return null;
  const chips = [];
  // Phase 4 surfaces OPEN_ISSUES; Phases 1/2 surface OPEN_QUESTIONS + BLOCKING.
  // Labels are full words so they read naturally and match the right-pane
  // Disagreement explorer's vocabulary (spec 0014).
  if (phase === 4) {
    if (stats.openIssues != null) {
      chips.push({
        value: stats.openIssues,
        label: stats.openIssues === 1 ? 'issue' : 'issues',
        tint: stats.openIssues > 0 ? 'warn' : 'ok',
      });
    }
  } else {
    if (stats.openQuestions != null) {
      chips.push({
        value: stats.openQuestions,
        label: stats.openQuestions === 1 ? 'question' : 'questions',
        tint: stats.openQuestions > 0 ? 'info' : 'ok',
      });
    }
    if (stats.blocking != null && stats.blocking > 0) {
      chips.push({
        value: stats.blocking,
        label: stats.blocking === 1 ? 'disagreement' : 'disagreements',
        tint: 'warn',
      });
    }
  }
  const statusPill = stats.status && (stats.status === 'AGREED' || stats.status === 'APPROVED' || stats.status === 'NOT_APPROVED');
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
      {chips.map((c, i) => <StatChip key={i} {...c} />)}
      {statusPill && <StatusInline label={stats.status} />}
    </span>
  );
}

function StatChip({ label, value, tint }) {
  const colorMap = { ok: COLORS.ok, info: COLORS.info, warn: COLORS.warn, err: COLORS.err };
  const c = colorMap[tint] || 'var(--fg-3)';
  return (
    <span className="mono" style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '1px 7px',
      background: 'transparent',
      border: `1px solid ${c}33`,
      borderRadius: 4,
      fontSize: 10.5, color: c,
      letterSpacing: '0.02em',
    }}>
      <span className="num" style={{ color: c, fontWeight: 500 }}>{value}</span>
      <span style={{ color: 'var(--fg-3)' }}>{label}</span>
    </span>
  );
}

function StatusInline({ label }) {
  const map = {
    AGREED:       { color: COLORS.ok,   text: 'agreed' },
    APPROVED:     { color: COLORS.ok,   text: 'approved' },
    NOT_APPROVED: { color: COLORS.warn, text: 'not approved' },
  };
  const m = map[label] || { color: 'var(--fg-3)', text: String(label).toLowerCase() };
  return (
    <span className="mono" style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '1px 6px',
      background: m.color + '14',
      border: `1px solid ${m.color}55`,
      borderRadius: 4,
      fontSize: 10, color: m.color,
      letterSpacing: '0.04em',
    }}>{m.text}</span>
  );
}

// Phase 0 preflight chip — distinct from the Phase 2/4 stats because the
// preflight protocol uses BRIEF_OK + BRIEF_ISSUES, not the negotiation fields.
function PreflightChip({ stats }) {
  if (!stats) return null;
  if (stats.state === 'ok') return <StatusInline label="OK" />;
  if (stats.state === 'issues') {
    return (
      <span className="mono" style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '1px 6px',
        background: COLORS.warn + '14',
        border: `1px solid ${COLORS.warn}55`,
        borderRadius: 4,
        fontSize: 10, color: COLORS.warn,
        letterSpacing: '0.04em',
      }}>
        <span>needs input</span>
        <span className="num" style={{ fontWeight: 500 }}>· {stats.count}</span>
      </span>
    );
  }
  return null;
}

function ArtifactHeader({ item, meta, expanded, hover }) {
  if (item.kind === 'input') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
        <span style={{ color: 'var(--fg-3)', fontSize: 12 }}>◆</span>
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500 }}>Input</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>brief · shared</span>
        <span style={{
          flex: 1, minWidth: 0, fontSize: 12, color: 'var(--fg-2)',
          overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{item.topic || ''}</span>
        <PreflightChip stats={item.stats} />
        <ExpandChevron expanded={expanded} hover={hover} />
      </div>
    );
  }
  if (item.kind === 'doc') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
        <Icon.Check style={{ color: COLORS.ok }} />
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500 }}>
          {item.completed ? 'Final document' : 'Converged document'}
        </span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>by {meta.name}</span>
        <span style={{ flex: 1, minWidth: 0, fontSize: 12, color: 'var(--fg-2)',
                       overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.summary}</span>
        <ExpandChevron expanded={expanded} hover={hover} />
      </div>
    );
  }
  if (item.kind === 'doc-live') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
        <AgentIcon agent={item.agent} size={14} />
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500 }}>{meta.name}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>drafting converged document</span>
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 10, color: meta.color, letterSpacing: '0.06em' }}>DRAFTER</span>
      </div>
    );
  }
  if (item.kind === 'plan' || item.kind === 'plan-live' || item.kind === 'turn' || item.kind === 'turn-live') {
    const isLive = item.live;
    const kindLabel =
      item.kind === 'plan' || item.kind === 'plan-live' ? 'plan draft' :
      typeof item.index === 'string' ? `turn ${item.index}` :
      `turn ${item.index ?? item.id.slice(1)}`;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
        <AgentIcon agent={item.agent} size={14} />
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, minWidth: 52 }}>{meta.name}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', minWidth: 76 }}>{kindLabel}</span>
        {!isLive && (
          <span style={{
            flex: 1, minWidth: 0, fontSize: 12, color: 'var(--fg-2)',
            overflow: 'hidden', textOverflow: 'ellipsis',
          }}>{item.summary}</span>
        )}
        {isLive && (
          <span style={{ flex: 1 }} />
        )}
        <StatsChips stats={item.stats} phase={item.statsPhase} />
        {isLive ? (
          <AgentStatusInline status={item.status} />
        ) : item.tokens != null || item.cost != null ? (
          <span className="mono num" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
            {fmt.tokens(item.tokens || 0)}t&nbsp;·&nbsp;{fmt.cost(item.cost || 0)}
          </span>
        ) : item.round != null ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
            r{item.round}
          </span>
        ) : null}
        {!isLive && <ExpandChevron expanded={expanded} hover={hover} />}
      </div>
    );
  }
  return null;
}

function ExpandChevron({ expanded, hover }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: 18, height: 18,
      opacity: expanded ? 0.6 : hover ? 0.6 : 0,
      transition: 'opacity 120ms',
      color: 'var(--fg-2)',
      transform: expanded ? 'rotate(90deg)' : 'none',
      transformOrigin: 'center',
      flexShrink: 0,
    }}>
      <Icon.Chevron />
    </span>
  );
}

function ArtifactBody({ item }) {
  // Live (streaming) bodies
  if (item.live) {
    return (
      <div style={{
        padding: '0 14px 14px',
        borderTop: '1px dashed var(--border-1)',
        maxHeight: 280,
        overflow: 'auto',
      }}>
        <div style={{ paddingTop: 12 }}>
          <StreamingText key={`${item.id}-${(item.body || '').length}`} content={item.body || ''} speed={70} />
        </div>
      </div>
    );
  }

  // Static bodies — input, plan, turn, doc — body fetched lazily from the
  // file endpoint (spec 0010). The filePath is set per-item by buildLiveTimeline.
  if (item.kind === 'input' || item.kind === 'plan' || item.kind === 'turn' || item.kind === 'doc') {
    return (
      <Body>
        <LazyMarkdownBody filePath={item.filePath} />
      </Body>
    );
  }
  return null;
}

function LazyMarkdownBody({ filePath }) {
  const { body, loading } = window.useFileBody(filePath);
  if (loading) {
    return <div style={{ color: 'var(--fg-3)', fontSize: 12 }} className="mono">loading…</div>;
  }
  return <Markdown text={body || '— body unavailable —'} />;
}

function Body({ children }) {
  return (
    <div style={{
      padding: '12px 14px 14px',
      borderTop: '1px dashed var(--border-1)',
      maxHeight: 320,
      overflow: 'auto',
    }}>{children}</div>
  );
}

function FinalDocPreview() {
  return (
    <div>
      <h2 style={{ margin: '0 0 10px', fontSize: 15, color: 'var(--fg-0)', fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.35 }}>
        Effects of urban density on residential heat-pump retrofit economics in temperate climates
      </h2>
      <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.6 }}>
        We assess the relationship between residential density and heat-pump retrofit economics across a cohort of 4,218 single-family households in IPCC Köppen-Geiger Cfa and (separately) Cfb climates between 2015 and 2024…
      </p>
      <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', lineHeight: 1.6 }}>
        §1 framing · §2 vintage taxonomy (5 buckets) · §3 heat-pump baseline · §4 financing (unified, with regressivity callout) · §5 cohort outcomes · §6 limitations · 12pp
      </div>
    </div>
  );
}

function AgentStatusInline({ status }) {
  const map = {
    idle:       { color: COLORS.idle, pulse: null,       label: 'idle' },
    thinking:   { color: COLORS.info, pulse: 'pulse-a',  label: 'thinking' },
    drafting:   { color: COLORS.info, pulse: 'pulse-a',  label: 'drafting' },
    responding: { color: COLORS.info, pulse: 'pulse-a',  label: 'responding' },
    reviewing:  { color: COLORS.info, pulse: 'pulse-a',  label: 'reviewing' },
    waiting:    { color: COLORS.idle, pulse: null,       label: 'waiting' },
  };
  const m = map[status] || map.idle;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
      <span className={m.pulse || ''} style={{ width: 6, height: 6, borderRadius: '50%', background: m.color }} />
      <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>{m.label}</span>
    </span>
  );
}

function ErrorCard({ item }) {
  return (
    <div style={{
      marginBottom: 6,
      padding: '12px 14px',
      background: 'rgba(217,106,106,0.04)',
      border: '1px solid rgba(217,106,106,0.30)',
      borderRadius: 'var(--r-3)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <Icon.Warn style={{ color: COLORS.err }} />
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.err, letterSpacing: '0.04em' }}>{item.error.code}</span>
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>at {item.error.where}</span>
      </div>
      <pre className="mono" style={{ margin: 0, fontSize: 11.5, color: 'var(--fg-1)', whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{item.error.detail}</pre>
    </div>
  );
}

function DeadlockCard({ item }) {
  return (
    <div style={{
      marginBottom: 6,
      padding: '12px 14px',
      background: 'rgba(212,160,86,0.04)',
      border: '1px solid rgba(212,160,86,0.30)',
      borderRadius: 'var(--r-3)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <Icon.Warn style={{ color: COLORS.warn }} />
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.warn, letterSpacing: '0.04em' }}>HARD_CAP_REACHED</span>
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.55 }}>
        {item.round.current} of {item.round.hard} negotiation rounds consumed.{' '}
        {item.open} disagreement{item.open === 1 ? '' : 's'} unresolved. Phase 3 not entered.
      </div>
    </div>
  );
}

// ─────────────────── Disagreement explorer (right panel) ───────────────────
function DisagreementExplorer({ run }) {
  const phasesWithDisagreements = [];
  if (run.phase >= 2 || run.disagreements.some(d => d.phase === 2)) phasesWithDisagreements.push(2);
  if (run.phase >= 4 || run.disagreements.some(d => d.phase === 4)) phasesWithDisagreements.push(4);
  if (phasesWithDisagreements.length === 0) phasesWithDisagreements.push(2);

  const initial = (run.phase === 4 || run.phase === 2) ? run.phase :
                  phasesWithDisagreements.includes(4) ? 4 : 2;
  const [selectedPhase, setSelectedPhase] = React.useState(initial);
  React.useEffect(() => { setSelectedPhase(initial); }, [run.id, initial]);

  const allInPhase = run.disagreements.filter(d => d.phase === selectedPhase);
  const open = allInPhase.filter(d => d.status === 'open');
  const resolved = allInPhase.filter(d => d.status.startsWith('resolved'));
  const introduced = allInPhase.length;

  const phaseInfo = (pid) => {
    const inPhase = run.disagreements.filter(d => d.phase === pid);
    const pending = run.phase < pid || (pid === 4 && run.phase < 3);
    return {
      pid,
      label: pid === 2 ? 'Negotiate' : 'Review',
      total: inPhase.length,
      open: inPhase.filter(d => d.status === 'open').length,
      resolved: inPhase.filter(d => d.status.startsWith('resolved')).length,
      pending,
      active: (run.phase === pid && run.status === 'running'),
    };
  };
  const tabs = [phaseInfo(2), phaseInfo(4)];

  const totalIntroduced = run.disagreements.length;

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
      <PaneHeader
        title="Disagreements"
        count={`${totalIntroduced} introduced`}
        accentColor={COLORS.info}
        right={
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <SmallStat label="open"     value={open.length} color={open.length > 0 ? COLORS.warn : 'var(--fg-3)'} />
            <SmallStat label="resolved" value={resolved.length} color={resolved.length > 0 ? COLORS.ok : 'var(--fg-3)'} />
          </span>
        }
      />
      <PaneToolbar>
        {tabs.map((t) => (
          <PhaseTab
            key={t.pid}
            tab={t}
            active={selectedPhase === t.pid}
            onSelect={() => setSelectedPhase(t.pid)}
          />
        ))}
      </PaneToolbar>
      <PhaseContent run={run} phaseId={selectedPhase} open={open} resolved={resolved} introduced={introduced} />
    </section>
  );
}

function SmallStat({ label, value, color }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'baseline', gap: 6, whiteSpace: 'nowrap',
    }}>
      <span className="mono num" style={{ fontSize: 13, color, fontWeight: 600 }}>{value}</span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{label}</span>
    </span>
  );
}

function PhaseTab({ tab, active, onSelect }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        height: 28,
        padding: '0 12px',
        background: active ? 'var(--bg-3)' : hover ? 'var(--bg-2)' : 'var(--bg-1)',
        border: `1px solid ${active ? 'var(--border-3)' : 'var(--border-1)'}`,
        borderRadius: 'var(--r-2)',
        transition: 'background 120ms, border-color 120ms',
        whiteSpace: 'nowrap',
        position: 'relative',
        boxShadow: active ? `inset 0 -2px 0 ${COLORS.info}` : 'none',
      }}>
      {tab.active && <Dot color={COLORS.info} pulse="pulse-a" size={6} />}
      <span className="mono" style={{
        fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase',
        color: active ? 'var(--fg-2)' : 'var(--fg-3)',
      }}>
        Phase&nbsp;{tab.pid}
      </span>
      <span style={{
        fontSize: 12.5,
        color: active ? 'var(--fg-0)' : 'var(--fg-2)',
        fontWeight: active ? 600 : 400,
      }}>
        {tab.label}
      </span>
      <span style={{ color: 'var(--fg-4)' }}>·</span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        {tab.pending ? 'pending'
          : tab.total === 0 ? 'no items'
          : <>
              <span style={{ color: tab.open > 0 ? COLORS.warn : 'var(--fg-3)' }}>{tab.open} open</span>
              <span style={{ color: 'var(--fg-4)' }}> · </span>
              <span style={{ color: tab.resolved > 0 ? COLORS.ok : 'var(--fg-3)' }}>{tab.resolved} resolved</span>
            </>
        }
      </span>
    </button>
  );
}

function PhaseContent({ run, phaseId, open, resolved, introduced }) {
  const pending = run.phase < phaseId || (phaseId === 4 && run.phase < 3);
  if (pending) {
    return (
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--fg-3)', background: 'var(--bg-0)' }}>
        <div style={{ textAlign: 'center', maxWidth: 280, lineHeight: 1.6, fontSize: 12.5 }}>
          {phaseId === 2 ? (
            <>
              <div style={{ marginBottom: 10, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <AgentIcon agent="claude" size={16} />
                <span className="mono" style={{ color: 'var(--fg-4)' }}>↔</span>
                <AgentIcon agent="gpt" size={16} />
              </div>
              Negotiation hasn't started yet. Both agents are still drafting independent plans.
            </>
          ) : (
            <>Cross-review begins after Phase 3 produces a converged draft.</>
          )}
        </div>
      </div>
    );
  }

  if (introduced === 0) {
    return (
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--fg-3)', background: 'var(--bg-0)' }}>
        <div className="mono" style={{ fontSize: 12 }}>no disagreements in this phase</div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--bg-0)' }}>
      <div style={{ padding: '6px 24px 28px' }}>
        {open.length > 0 && <GroupHeader label="Open" color={COLORS.warn} count={open.length} />}
        {open.map(d => <DisagreementCard key={d.id} d={d} />)}
        {resolved.length > 0 && (
          <GroupHeader label="Resolved" color={COLORS.ok} count={resolved.length}
                       style={{ marginTop: open.length ? 20 : 0 }} />
        )}
        {resolved.map(d => <DisagreementCard key={d.id} d={d} />)}
      </div>
    </div>
  );
}

function DisagreementCard({ d }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);

  const isResolved = d.status.startsWith('resolved');
  const which = isResolved ? d.status.split('-')[1] : null;
  const exchanges = d.progression?.length || 0;
  const raisedMeta = d.raisedBy && d.raisedBy !== 'both' ? AGENT_META[d.raisedBy] : null;

  // Card accent (left edge) color by status
  let accentColor;
  if (d.status === 'open' && d.deadlocked) accentColor = COLORS.warn;
  else if (d.status === 'open')            accentColor = COLORS.warn;
  else if (which === 'claude')             accentColor = COLORS.agentA;
  else if (which === 'gpt')                accentColor = COLORS.agentB;
  else if (which === 'both')               accentColor = COLORS.ok;

  let statusPill;
  if (d.status === 'open' && d.deadlocked) statusPill = <StatusPill color={COLORS.warn} label="deadlocked" />;
  else if (d.status === 'open')            statusPill = <StatusPill color={COLORS.warn} label="open" />;
  else if (which === 'claude')             statusPill = <StatusPill color={COLORS.agentA} label="→ claude" />;
  else if (which === 'gpt')                statusPill = <StatusPill color={COLORS.agentB} label="→ gpt" />;
  else if (which === 'both')               statusPill = <StatusPill color={COLORS.ok} label="aligned" />;

  const roundRange = d.closedRound
    ? `R${d.openedRound} → R${d.closedRound}`
    : `R${d.openedRound ?? d.round} · still open`;

  return (
    <article
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        marginBottom: 8,
        background: 'var(--bg-1)',
        border: `1px solid ${open ? 'var(--border-2)' : 'var(--border-1)'}`,
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
        transition: 'border-color 120ms',
      }}
    >
      <button onClick={() => setOpen(!open)} style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '12px 14px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        {/* Top row: label + status */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
          <span style={{ flex: 1, fontSize: 13, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.35 }}>
            {d.shortLabel || d.point}
          </span>
          {statusPill}
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 18, height: 18,
            opacity: open ? 0.6 : hover ? 0.6 : 0.25,
            transition: 'opacity 120ms',
            color: 'var(--fg-2)',
            transform: open ? 'rotate(90deg)' : 'none',
            flexShrink: 0,
          }}>
            <Icon.Chevron />
          </span>
        </div>
        {/* Stats row */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 14,
          fontSize: 11, color: 'var(--fg-3)',
          fontFamily: 'var(--mono)',
          whiteSpace: 'nowrap',
        }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color: 'var(--fg-4)' }}>raised by</span>
            {raisedMeta ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                <AgentIcon agent={d.raisedBy} size={12} variant="ghost" />
                <span style={{ color: 'var(--fg-1)' }}>{raisedMeta.name.toLowerCase()}</span>
              </span>
            ) : (
              <span style={{ color: 'var(--fg-1)' }}>both</span>
            )}
          </span>
          <span style={{ color: 'var(--fg-4)' }}>·</span>
          <span style={{ color: isResolved ? 'var(--fg-2)' : COLORS.warn }}>{roundRange}</span>
          <span style={{ color: 'var(--fg-4)' }}>·</span>
          <span>
            <span style={{ color: 'var(--fg-1)' }}>{exchanges}</span>
            {' '}exchange{exchanges === 1 ? '' : 's'}
          </span>
        </div>
      </button>

      {open && (
        <div style={{
          padding: '14px',
          borderTop: '1px dashed var(--border-1)',
          background: 'var(--bg-0)',
        }}>
          {/* Full point statement */}
          <div style={{ marginBottom: 16 }}>
            <SmallLabel>Contested point</SmallLabel>
            <div style={{ fontSize: 12.5, color: 'var(--fg-0)', lineHeight: 1.5 }}>{d.point}</div>
          </div>

          {/* Progression */}
          {d.progression && d.progression.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <SmallLabel>Progression</SmallLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                {d.progression.map((step, i) => (
                  <ProgressionStep key={i} step={step} last={i === d.progression.length - 1} />
                ))}
                {!isResolved && (
                  <ProgressionStep step={{ round: null, agent: null, action: 'open', note: 'No movement yet from either agent.' }} last pending />
                )}
              </div>
            </div>
          )}

          {/* Current positions (only if not aligned/single-exchange) */}
          {d.progression && d.progression.length > 1 && d.raisedBy !== 'both' && (
            <div style={{ marginBottom: isResolved ? 16 : 0 }}>
              <SmallLabel>Current positions</SmallLabel>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Position agent="claude" text={d.claude} />
                <Position agent="gpt" text={d.gpt} />
              </div>
            </div>
          )}

          {/* Resolution */}
          {d.resolution && (
            <div>
              <SmallLabel color={COLORS.ok}>Resolution</SmallLabel>
              <div style={{
                paddingLeft: 10,
                borderLeft: `2px solid ${COLORS.ok}55`,
                fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.55,
              }}>{d.resolution}</div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function StatusPill({ color, label }) {
  return (
    <span className="mono" style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '2px 7px',
      fontSize: 10.5, color,
      background: color + '14',
      border: `1px solid ${color}44`,
      borderRadius: 999,
      whiteSpace: 'nowrap',
      letterSpacing: '0.02em',
      flexShrink: 0,
    }}>{label}</span>
  );
}

function SmallLabel({ children, color, style }) {
  return (
    <div style={{
      fontSize: 10, color: color || 'var(--fg-3)',
      letterSpacing: '0.08em', textTransform: 'uppercase',
      fontWeight: 500,
      marginBottom: 8,
      ...style,
    }}>{children}</div>
  );
}

function ProgressionStep({ step, last, pending }) {
  const meta = step.agent && step.agent !== 'both' ? AGENT_META[step.agent] : null;
  const actionTones = {
    raised:       COLORS.info,
    rejected:     COLORS.warn,
    'pushed back': COLORS.warn,
    restated:     'var(--fg-2)',
    conceded:     COLORS.ok,
    aligned:      COLORS.ok,
    open:         COLORS.warn,
  };
  const actionColor = actionTones[step.action] || 'var(--fg-2)';

  return (
    <div style={{ display: 'flex', gap: 10, position: 'relative', paddingBottom: last ? 0 : 14 }}>
      {/* Rail */}
      <div style={{
        position: 'absolute',
        left: 7, top: 16,
        bottom: last ? 'auto' : 0, height: last ? 0 : undefined,
        width: 1, background: 'var(--border-2)',
      }} />
      {/* Icon — agent monogram, "both" pip, or pending grey */}
      <div style={{
        position: 'relative',
        marginTop: 1,
        flexShrink: 0,
        zIndex: 1,
      }}>
        {meta ? (
          <AgentIcon agent={step.agent} size={15} />
        ) : step.agent === 'both' ? (
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 15, height: 15, borderRadius: 4,
            background: COLORS.ok, color: 'var(--bg-0)',
            fontSize: 9, fontWeight: 700, fontFamily: 'var(--mono)',
            lineHeight: 1,
          }}>✓</span>
        ) : (
          <span style={{
            display: 'inline-block', width: 9, height: 9, borderRadius: '50%',
            background: pending ? 'var(--fg-4)' : COLORS.warn,
            margin: 3,
            opacity: pending ? 0.6 : 1,
          }} />
        )}
      </div>
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 3 }}>
          {step.round != null && (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>R{step.round}</span>
          )}
          {meta && (
            <span style={{ fontSize: 11.5, color: 'var(--fg-1)', fontWeight: 500 }}>{meta.name}</span>
          )}
          {step.agent === 'both' && (
            <span style={{ fontSize: 11.5, color: 'var(--fg-1)', fontWeight: 500 }}>Both agents</span>
          )}
          <span className="mono" style={{
            fontSize: 10.5, color: actionColor, letterSpacing: '0.02em',
            textTransform: 'lowercase',
          }}>{step.action}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.5 }}>
          {step.note}
        </div>
      </div>
    </div>
  );
}

function Position({ agent, text }) {
  const meta = AGENT_META[agent];
  return (
    <div style={{ paddingLeft: 10, borderLeft: `2px solid ${meta.color}` }}>
      <div className="mono" style={{ fontSize: 10, color: meta.color, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>{meta.name}</div>
      <div style={{ fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.55 }}>{text}</div>
    </div>
  );
}

// ─────────────────── Footer ───────────────────
function Footer({ run }) {
  const a = run.agents.claude.cost;
  const b = run.agents.gpt.cost;
  const total = a + b;
  const hasBudget = run.budget?.limit != null && run.budget.limit > 0;
  const budget = hasBudget ? run.budget.limit : 0;
  const pct = hasBudget ? (total / budget) * 100 : 0;
  const warnPct = (run.budget?.warnAt || 0.75) * 100;
  const over = hasBudget && pct >= warnPct;
  const aPct = hasBudget ? (a / budget) * 100 : 0;
  const bPct = hasBudget ? (b / budget) * 100 : 0;
  return (
    <footer style={{
      display: 'flex', alignItems: 'center', gap: 18,
      padding: '10px 24px',
      borderTop: '1px solid var(--border-1)',
      background: 'var(--bg-0)',
      flexShrink: 0,
      fontSize: 11.5,
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <AgentIcon agent="claude" size={12} variant="ghost" />
        <span className="mono num" style={{ color: 'var(--fg-1)' }}>{fmt.cost(a)}</span>
        <span style={{ color: 'var(--fg-4)' }}>+</span>
        <AgentIcon agent="gpt" size={12} variant="ghost" />
        <span className="mono num" style={{ color: 'var(--fg-1)' }}>{fmt.cost(b)}</span>
        <span style={{ color: 'var(--fg-4)' }}>=</span>
        <span className="mono num" style={{ color: 'var(--fg-0)' }}>{fmt.cost(total)}</span>
      </span>
      {hasBudget && (
        <>
          <div style={{ flex: 1, position: 'relative', height: 4, background: 'var(--bg-3)', borderRadius: 999, maxWidth: 380 }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${Math.min(100, aPct)}%`, background: COLORS.agentA, borderRadius: '999px 0 0 999px' }} />
            <div style={{ position: 'absolute', left: `${Math.min(100, aPct)}%`, top: 0, bottom: 0, width: `${Math.min(100 - aPct, bPct)}%`, background: COLORS.agentB }} />
            <span style={{ position: 'absolute', top: -2, bottom: -2, left: `${warnPct}%`, width: 1, background: over ? COLORS.warn : 'var(--border-3)' }} />
          </div>
          <span className="mono num" style={{ color: over ? COLORS.warn : 'var(--fg-2)' }}>
            {pct.toFixed(0)}% of ${budget.toFixed(2)}
          </span>
          {over && (
            <span className="mono" style={{ color: COLORS.warn, fontSize: 11 }}>above 75% threshold</span>
          )}
        </>
      )}
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 11 }}>SSE · /runs/{run.id}/stream</span>
    </footer>
  );
}

// ─────────────────── Run-scoped errors view (replaces main area) ───────────
function RunErrorsView({ run }) {
  const errors = run.errors || [];
  const counts = errors.reduce((a, e) => { a[e.severity] = (a[e.severity] || 0) + 1; return a; }, {});
  const [openId, setOpenId] = React.useState(null);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      minWidth: 0, minHeight: 0,
      gridColumn: '1 / -1',
      background: 'var(--bg-0)',
      overflow: 'hidden',
    }}>
      <PaneHeader
        title="Errors"
        count={`${errors.length} logged for run ${run.id}`}
        accentColor={COLORS.err}
        right={
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <SmallStat label="critical" value={counts.critical || 0} color={(counts.critical || 0) > 0 ? COLORS.err : 'var(--fg-3)'} />
            <SmallStat label="error"    value={counts.error || 0}    color={(counts.error || 0) > 0 ? COLORS.err : 'var(--fg-3)'} />
            <SmallStat label="warning"  value={counts.warning || 0}  color={(counts.warning || 0) > 0 ? COLORS.warn : 'var(--fg-3)'} />
          </span>
        }
      />
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '14px 24px 28px' }}>
        <GroupHeader label="Errors" color={COLORS.err} count={errors.length} />
        {errors.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--fg-3)', fontSize: 12.5 }}>
            no errors logged for this run
          </div>
        ) : (
          errors.map((e) => (
            <ErrorCard
              key={e.id}
              error={{ ...e, runId: run.id }}
              open={openId === e.id}
              onToggle={() => setOpenId(openId === e.id ? null : e.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ─────────────────── Top-level ───────────────────
function RunDetail({ run }) {
  const [showErrors, setShowErrors] = React.useState(false);
  React.useEffect(() => { setShowErrors(false); }, [run.id, run.phase, run.status]);

  const errorCount = (run.errors || []).length;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%',
      background: 'var(--bg-0)',
      overflow: 'hidden',
    }}>
      <TopBar run={run} />
      <PhaseStrip
        run={run}
        errorCount={errorCount}
        showErrors={showErrors}
        onToggleErrors={() => setShowErrors(s => !s)}
      />
      <main style={{
        flex: 1, minHeight: 0,
        display: 'grid',
        gridTemplateColumns: showErrors ? '1fr' : '1fr 1fr',
      }}>
        {showErrors ? (
          <RunErrorsView run={run} />
        ) : (
          <>
            <Timeline run={run} />
            <DisagreementExplorer run={run} />
          </>
        )}
      </main>
      <Footer run={run} />
    </div>
  );
}

Object.assign(window, { RunDetail });
