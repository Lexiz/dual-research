// run-detail.jsx — v4: card-based timeline + phase-tabbed disagreement explorer
//
//   ┌─ top bar
//   ├─ phase strip
//   ├─ left: artifact cards (collapsible)   │  right: disagreements by phase (tabbed)
//   └─ footer

// ─────────────────── Compact run-detail header (spec 0024 pass 3) ────────────
// Back action now lives in the chrome bar's "All runs" tab (icon swaps to a
// back-arrow on detail views), so the header has neither a back chip nor a
// TOPIC tag — just topic + right-side badges.
function RunDetailHeader({ run, errorCount, showErrors, onToggleErrors }) {
  const total = run.agents.claude.cost + run.agents.gpt.cost;
  const idParts = window.splitRunId(run.id);
  const startedClock = idParts.time || '—';
  const elapsedTotal = Object.values(run.phaseTimings || {}).filter(Boolean).reduce((a, b) => a + b, 0);
  const elapsedLabel = elapsedTotal > 0 ? fmt.duration(elapsedTotal) : '—';
  const drafterLabel = run.drafter ? (AGENT_META[run.drafter]?.name || run.drafter) : '—';
  const totalTokens =
    (run.agents.claude.tokens?.in || 0) + (run.agents.claude.tokens?.out || 0) +
    (run.agents.gpt.tokens?.in || 0) + (run.agents.gpt.tokens?.out || 0);

  return (
    <header style={{
      display: 'flex', flexDirection: 'column',
      padding: '8px 20px',
      borderBottom: '1px solid var(--border-1)',
      background: 'var(--bg-0)',
      flexShrink: 0,
      gap: 4,
    }}>
      {/* Row 1: topic + cost + status/errors */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <Topic text={run.topic} />
        <CostBadge cost={total} tokens={totalTokens} />
        <StatusErrorsBadge
          status={run.status}
          errorCount={errorCount}
          showErrors={showErrors}
          onToggleErrors={onToggleErrors}
        />
      </div>
      {/* Row 2: meta line on left, phase dots on right */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--fg-3)',
          display: 'flex', flexWrap: 'wrap', flex: 1, minWidth: 0,
        }}>
          <span>started <span style={{ color: 'var(--fg-1)' }}>{startedClock}</span></span>
          <span>&nbsp;·&nbsp;drafter <span style={{ color: 'var(--fg-1)' }}>{drafterLabel}</span></span>
          <span>&nbsp;·&nbsp;<span style={{ color: 'var(--fg-1)' }}>{elapsedLabel}</span> elapsed</span>
          {run.status === 'running' && (run.phase === 2 || run.phase === 4) && run.round && (
            <span>&nbsp;·&nbsp;round&nbsp;
              <span style={{ color: 'var(--fg-1)' }}>{run.round.current}/{run.round.soft}</span>
              <span style={{ color: 'var(--fg-3)' }}>&nbsp;(hard {run.round.hard})</span>
            </span>
          )}
        </div>
        <PhaseDots run={run} />
      </div>
    </header>
  );
}

function Topic({ text }) {
  return (
    <div title={text}
         style={{
           color: 'var(--fg-0)', fontSize: 14, lineHeight: 1.35, fontWeight: 500,
           flex: 1, minWidth: 0,
           overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
         }}>
      {text || '— no topic —'}
    </div>
  );
}

function CostBadge({ cost, tokens }) {
  return (
    <span title={`${cost.toFixed(4)} USD · ${tokens.toLocaleString()} tokens`}
          className="mono"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '3px 9px', borderRadius: 999,
            background: 'var(--bg-2)', border: '1px solid var(--border-1)',
            fontSize: 11, color: 'var(--fg-1)', flexShrink: 0,
            whiteSpace: 'nowrap',
          }}>
      <span className="num">{fmt.cost(cost)}</span>
      <span style={{ color: 'var(--fg-3)' }}>·</span>
      <span className="num" style={{ color: 'var(--fg-2)' }}>{fmt.tokens(tokens)}t</span>
    </span>
  );
}

function StatusErrorsBadge({ status, errorCount, showErrors, onToggleErrors }) {
  const map = {
    running:    { label: 'running',    color: COLORS.info, pulse: 'pulse-a' },
    completed:  { label: 'completed',  color: COLORS.ok,   pulse: null },
    deadlocked: { label: 'deadlocked', color: COLORS.warn, pulse: 'pulse-warn' },
    errored:    { label: 'errored',    color: COLORS.err,  pulse: 'pulse-err' },
  };
  const m = map[status] || { label: status || 'idle', color: COLORS.idle, pulse: null };
  const hasErrors = errorCount > 0;

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'stretch',
      borderRadius: 999, overflow: 'hidden',
      border: '1px solid var(--border-1)',
      background: 'var(--bg-2)',
      flexShrink: 0,
      fontFamily: 'var(--mono)',
    }}>
      {/* Status half */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 10px 3px 9px',
        fontSize: 11, color: 'var(--fg-1)', letterSpacing: '0.01em',
      }}>
        <Dot color={m.color} pulse={m.pulse} size={6} />
        {m.label}
      </span>

      {/* Errors half (only when count > 0). Toggle on click. */}
      {hasErrors && (
        <button
          onClick={onToggleErrors}
          title={showErrors ? 'Back to timeline' : `View ${errorCount} error${errorCount === 1 ? '' : 's'}`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '3px 10px',
            background: showErrors ? COLORS.err + '20' : 'transparent',
            border: 'none', borderLeft: '1px solid var(--border-1)',
            color: COLORS.err, fontSize: 11, cursor: 'pointer',
            fontFamily: 'inherit',
          }}
          onMouseEnter={e => { if (!showErrors) e.currentTarget.style.background = COLORS.err + '14'; }}
          onMouseLeave={e => { if (!showErrors) e.currentTarget.style.background = 'transparent'; }}>
          <Icon.Warn />
          <span className="num">{errorCount}</span>
          <span style={{ color: COLORS.err, opacity: 0.85 }}>error{errorCount === 1 ? '' : 's'}</span>
          {showErrors && (
            <span style={{ marginLeft: 4, transform: 'rotate(180deg)', display: 'inline-block', color: 'var(--fg-1)' }}>
              <Icon.Arrow />
            </span>
          )}
        </button>
      )}
    </span>
  );
}

function PhaseDots({ run }) {
  const { phase, status } = run;
  return (
    <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
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
              width: 6, height: 6, borderRadius: '50%',
              background: completed || current || failed ? color : 'transparent',
              border: completed || current || failed ? 'none' : `1px solid ${color}`,
              flexShrink: 0,
            }}>
              {current && <span className="pulse-a" style={{ position: 'absolute', inset: -2, borderRadius: '50%' }} />}
            </span>
            {!isLast && (
              <span style={{
                width: 12, height: 1,
                background: completed ? COLORS.ok : 'var(--border-2)',
                opacity: completed ? 0.5 : 1,
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// BackChip / RunIdChip removed in spec 0024; replaced by BackArrow + topic.
// PhaseStrip / ErrorsToggleButton / RoundIndicator (spec 0017) folded into
// RunDetailHeader above in spec 0023; RoundIndicator removed entirely in 0024.

// ─────────────────── Timeline ───────────────────
// Spec 0025: cards no longer expand inline. The Timeline owns a single
// `openId` and renders a Modal for the active artifact. Live items
// remain inline-streaming.
function Timeline({ run }) {
  const items = React.useMemo(() => buildTimeline(run), [run]);
  const [openId, setOpenId] = React.useState(null);

  // Reset open modal when navigating between runs / phases.
  React.useEffect(() => { setOpenId(null); }, [run.id]);

  const openItem = items.find((i) => i.id === openId) || null;

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
            onOpen={() => setOpenId(item.id)}
          />
        ))}
      </div>
      {openItem && (
        <ArtifactModal
          item={openItem}
          run={run}
          onClose={() => setOpenId(null)}
        />
      )}
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
function TimelineItem({ item, run, onOpen }) {
  if (item.kind === 'phase-divider') return <PhaseDivider item={item} run={run} />;
  if (item.kind === 'error')         return <ErrorCard item={item} />;
  if (item.kind === 'deadlock')      return <DeadlockCard item={item} />;
  return <ArtifactCard item={item} onOpen={onOpen} />;
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

// The unified card (spec 0025: summary + view-full button).
//
// Layout is now two rows when a summary is present:
//   ┌───────────────────────────────────────────────────────────┐
//   │ [icon] AGENT  turn 3      5 questions · 2 disagreements   │
//   │  Summary line clamped to 2 lines …       [View full →]    │
//   └───────────────────────────────────────────────────────────┘
//
// Clicking anywhere on the card opens the modal. Live items continue
// to stream inline (no modal — the summary isn't available yet).
function ArtifactCard({ item, onOpen }) {
  const meta = item.agent ? AGENT_META[item.agent] : null;
  const [hover, setHover] = React.useState(false);

  const accentColor = meta?.color || 'var(--fg-2)';
  const isLive = item.live;
  const hasSummary = !isLive && !!(item.summary && String(item.summary).trim());

  // The header row content (same as before, minus the chevron).
  const header = <ArtifactHeader item={item} meta={meta} hover={hover} />;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        marginBottom: 6,
        background: 'var(--bg-1)',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
        transition: 'border-color 120ms, background 120ms',
        ...(isLive ? {
          borderLeft: `2px solid ${accentColor}`,
        } : {}),
      }}
    >
      <button
        onClick={isLive ? undefined : onOpen}
        disabled={isLive}
        style={{
          display: 'block', width: '100%', textAlign: 'left',
          padding: hasSummary ? '10px 12px 8px' : '10px 12px',
          background: hover && !isLive ? 'var(--bg-2)' : 'transparent',
          transition: 'background 120ms',
          cursor: isLive ? 'default' : 'pointer',
        }}>
        {header}
        {hasSummary && (
          <SummaryRow
            summary={item.summary}
            onOpen={onOpen}
          />
        )}
      </button>
      {isLive && <ArtifactLiveBody item={item} />}
    </div>
  );
}

// One-line "TL;DR + View full" row under the card header.
function SummaryRow({ summary, onOpen }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: 10,
      marginTop: 6,
    }}>
      <p style={{
        flex: 1, minWidth: 0,
        margin: 0,
        fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.5,
        // Clamp at two lines.
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        whiteSpace: 'normal',
      }}>
        {summary}
      </p>
      <span
        onClick={(e) => { e.stopPropagation(); onOpen && onOpen(); }}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px',
          fontSize: 10.5,
          color: 'var(--fg-1)',
          background: 'var(--bg-2)',
          border: '1px solid var(--border-2)',
          borderRadius: 999,
          fontFamily: 'var(--mono)',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          cursor: 'pointer',
        }}>
        View full
        <Icon.Arrow style={{ width: 10, height: 10 }} />
      </span>
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
  // Render a pill for every protocol-defined turn status, not just the
  // terminal-agreed ones. Mid-state values (NEGOTIATING / REVIEWING /
  // DISAGREED) used to be silently dropped, leaving the user unable to
  // tell at a glance whether a round agreed.
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
      {chips.map((c, i) => <StatChip key={i} {...c} />)}
      {stats.status && <StatusInline label={stats.status} />}
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
    DISAGREED:    { color: COLORS.warn, text: 'disagreed' },
    NEGOTIATING:  { color: COLORS.idle, text: 'negotiating' },
    REVIEWING:    { color: COLORS.idle, text: 'reviewing' },
  };
  const m = map[label] || { color: COLORS.idle, text: String(label).toLowerCase().replace(/_/g, ' ') };
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

function ArtifactHeader({ item, meta, hover }) {
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
        <span style={{ flex: 1 }} />
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
        <span style={{ flex: 1 }} />
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
      </div>
    );
  }
  return null;
}

// Live (streaming) body — same UX as before but with a stable container.
function ArtifactLiveBody({ item }) {
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

function LazyMarkdownBody({ filePath }) {
  const { body, loading } = window.useFileBody(filePath);
  if (loading) {
    return <div style={{ color: 'var(--fg-3)', fontSize: 12 }} className="mono">loading…</div>;
  }
  return <Markdown text={body || '— body unavailable —'} />;
}

// ─────────────────── Modal dispatch ───────────────────
// Spec 0025. Owns title + accent + body shape per artifact kind.
function ArtifactModal({ item, run, onClose }) {
  const meta = item.agent ? AGENT_META[item.agent] : null;
  const accent = meta?.color || COLORS.info;

  if (item.kind === 'input') {
    return <PreflightModal item={item} run={run} onClose={onClose} accent={accent} />;
  }
  return <DocumentModal item={item} meta={meta} onClose={onClose} accent={accent} />;
}

function DocumentModal({ item, meta, onClose, accent }) {
  let title = 'Document';
  let subtitle = null;
  if (item.kind === 'doc') {
    title = item.completed ? 'Final document' : 'Converged document';
    subtitle = meta ? `by ${meta.name}` : null;
  } else if (item.kind === 'plan' || item.kind === 'plan-live') {
    title = `${meta?.name || 'Agent'} — plan draft`;
  } else if (item.kind === 'turn' || item.kind === 'turn-live') {
    const lbl = typeof item.index === 'string' ? `turn ${item.index}` : `turn ${item.index || ''}`;
    title = `${meta?.name || 'Agent'} — ${lbl}`;
    subtitle = `round ${item.round}`;
  }
  return (
    <Modal open={true} onClose={onClose} title={title} subtitle={subtitle} accent={accent}>
      <LazyMarkdownBody filePath={item.filePath} />
    </Modal>
  );
}

function PreflightModal({ item, run, onClose, accent }) {
  const { attachments, loading } = window.useAttachments(run.id);

  // Split attachments into Sources (links) vs Files (image/pdf/file).
  const fileKinds = new Set(['image', 'pdf', 'file']);
  const sources = (attachments || []).filter((a) => a.kind === 'link');
  const files = (attachments || []).filter((a) => fileKinds.has(a.kind));

  const tabs = [
    {
      id: 'content',
      label: 'Content',
      content: <PreflightContentTab item={item} />,
    },
    {
      id: 'sources',
      label: 'Sources',
      count: sources.length,
      content: <PreflightSourcesTab sources={sources} loading={loading} />,
    },
    {
      id: 'files',
      label: 'Files',
      count: files.length,
      content: <PreflightFilesTab files={files} loading={loading} runId={run.id} />,
    },
  ];

  return (
    <Modal
      open={true}
      onClose={onClose}
      title="Input — brief"
      subtitle={item.topic || ''}
      accent={accent}
      tabs={tabs}
    />
  );
}

function PreflightContentTab({ item }) {
  return <LazyMarkdownBody filePath={item.filePath} />;
}

function PreflightSourcesTab({ sources, loading }) {
  if (loading) {
    return <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading…</div>;
  }
  if (sources.length === 0) {
    return <AttachmentsEmpty label="No external links were extracted from this brief." />;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {sources.map((s, i) => (
        <SourceRow key={i} attachment={s} />
      ))}
    </div>
  );
}

function PreflightFilesTab({ files, loading, runId }) {
  if (loading) {
    return <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading…</div>;
  }
  if (files.length === 0) {
    return <AttachmentsEmpty label="No images, PDFs, or files were attached to this brief." />;
  }
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
      gap: 14,
    }}>
      {files.map((f, i) => (
        <FileCard key={i} attachment={f} runId={runId} />
      ))}
    </div>
  );
}

function AttachmentsEmpty({ label }) {
  return (
    <div style={{
      padding: '32px 16px',
      textAlign: 'center',
      color: 'var(--fg-3)',
      fontSize: 12.5,
      lineHeight: 1.6,
      border: '1px dashed var(--border-2)',
      borderRadius: 'var(--r-2)',
      background: 'var(--bg-2)',
    }}>
      {label}
    </div>
  );
}

function SourceRow({ attachment }) {
  const { title, url, caption, source } = attachment;
  let host = '';
  try { host = url ? new URL(url).host : ''; } catch (_) { host = ''; }
  const displayTitle = title && title.trim() ? title : (url || source);
  return (
    <a
      href={url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'block',
        padding: '10px 12px',
        background: 'var(--bg-1)',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-2)',
        textDecoration: 'none',
        color: 'var(--fg-0)',
      }}>
      <div style={{
        fontSize: 13, color: 'var(--fg-0)', fontWeight: 500,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>{displayTitle}</div>
      <div className="mono" style={{
        fontSize: 11, color: 'var(--fg-3)', marginTop: 3,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {host || url || '—'}
      </div>
      {caption && (
        <div style={{ fontSize: 12, color: 'var(--fg-2)', marginTop: 6, lineHeight: 1.55 }}>
          {caption}
        </div>
      )}
    </a>
  );
}

function FileCard({ attachment, runId }) {
  const { kind, title, caption, url, rel_path, size_bytes, mime } = attachment;
  // Prefer the served blob URL when we have one; fall back to the
  // external `url`. The blob endpoint is path-traversal-guarded server-
  // side and works for both fs and supabase backends.
  const localBlobUrl = rel_path ? window.attachmentBlobUrl(runId, rel_path) : null;
  const renderUrl = localBlobUrl || url || null;

  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        flex: 1, minHeight: 140,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg-0)',
        overflow: 'hidden',
      }}>
        {kind === 'image' && renderUrl ? (
          <a href={renderUrl} target="_blank" rel="noopener noreferrer"
             style={{ display: 'block', width: '100%', height: '100%' }}>
            <img src={renderUrl} alt={title || ''}
                 style={{ display: 'block', width: '100%', height: '100%',
                          objectFit: 'cover', maxHeight: 220 }}
                 onError={(e) => { e.target.style.display = 'none'; }} />
          </a>
        ) : (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
            color: 'var(--fg-3)', padding: 12, textAlign: 'center',
          }}>
            <span style={{ fontSize: 28 }}>{kind === 'pdf' ? '📄' : '📎'}</span>
            <span className="mono" style={{
              fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase',
            }}>{kind}</span>
          </div>
        )}
      </div>
      <div style={{ padding: '10px 12px' }}>
        <div title={title || ''} style={{
          fontSize: 13, color: 'var(--fg-0)', fontWeight: 500,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{title || '(unnamed)'}</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--fg-3)', marginTop: 4,
        }}>
          {[mime, size_bytes ? formatBytes(size_bytes) : null].filter(Boolean).join(' · ') || '—'}
        </div>
        {caption && (
          <div style={{ fontSize: 12, color: 'var(--fg-2)', marginTop: 6, lineHeight: 1.5 }}>
            {caption}
          </div>
        )}
        {renderUrl && (
          <a href={renderUrl} target="_blank" rel="noopener noreferrer"
             style={{
               display: 'inline-flex', alignItems: 'center', gap: 5,
               marginTop: 8,
               fontSize: 11.5, color: COLORS.info,
               textDecoration: 'none',
             }}>
            {localBlobUrl ? 'Download' : 'Open'}
            <Icon.Arrow style={{ width: 10, height: 10 }} />
          </a>
        )}
      </div>
    </div>
  );
}

function formatBytes(n) {
  if (n == null) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
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
    const suspectedMiss = run.disagreementsParseSuspectedMiss && phaseId === 2;
    return (
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--fg-3)', background: 'var(--bg-0)' }}>
        <div style={{ textAlign: 'center', maxWidth: 320, lineHeight: 1.6 }}>
          <div className="mono" style={{ fontSize: 12 }}>no disagreements in this phase</div>
          {suspectedMiss && (
            <div className="mono" style={{ fontSize: 11, marginTop: 10, color: COLORS.warn, opacity: 0.85 }}>
              ⚠ couldn't reconstruct disagreements from this run — open the round files directly
            </div>
          )}
        </div>
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
      <RunDetailHeader
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
