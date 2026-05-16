// run-detail.jsx — v4: card-based timeline + phase-tabbed disagreement explorer
//
//   ┌─ top bar
//   ├─ phase strip
//   ├─ left: artifact cards (collapsible)   │  right: disagreements by phase (tabbed)
//   └─ footer

// ─────────────────── Spec 0033 — agent activity composer ────────────────────
//
// Maps (agent.status × run.phase × run.round) → a 3–6-word activity phrase
// + live/idle flag. The two per-agent header strips render this as
//   `● drafting parallel plan`
// — pulse on `live === true`, grey static dot otherwise. No LLM; pure switch.
function composeAgentActivity(agent, run) {
  const ag = run.agents?.[agent];
  const other = agent === 'claude' ? 'gpt' : 'claude';
  const otherAg = run.agents?.[other];
  const otherName = AGENT_META[other]?.name || other;
  const status = ag?.status || 'idle';
  const otherStatus = otherAg?.status || 'idle';

  // Terminal phrasing — run is done.
  if (run.status === 'completed') return { live: false, phrase: 'done' };
  if (run.status === 'errored')   return { live: false, phrase: 'errored' };
  if (run.status === 'deadlocked')return { live: false, phrase: 'deadlocked' };

  const livelyStatuses = new Set(['thinking', 'drafting', 'responding', 'reviewing']);
  const isLive = livelyStatuses.has(status);
  const otherIsLive = livelyStatuses.has(otherStatus);

  // Idle / waiting → grey strip + a sentence about what they're waiting for.
  if (!isLive) {
    if (otherIsLive) {
      return { live: false, phrase: `waiting for ${otherName}` };
    }
    if (run.phase != null && run.phase >= 0) {
      return { live: false, phrase: `waiting · phase ${run.phase}` };
    }
    return { live: false, phrase: 'idle' };
  }

  // Live phrases keyed on (phase, status).
  const round = run.round?.current;
  switch (run.phase) {
    case 0: return { live: true, phrase: 'critiquing the brief' };
    case 1: return { live: true, phrase: 'drafting parallel plan' };
    case 2: return { live: true, phrase: round ? `negotiating · round ${round}` : 'negotiating' };
    case 3: return { live: true, phrase: 'drafting converged doc' };
    case 4: return { live: true, phrase: round ? `reviewing · round ${round}` : 'reviewing' };
    case 5: return { live: true, phrase: 'finalising' };
    default: return { live: true, phrase: status };
  }
}

// ─────────────────── Compact run-detail header (spec 0024 pass 3 + 0033) ─────
// Spec 0033 expands this from 2 to 4 rows:
//   row 1: topic · cost · status · [Conversation/Consumption tabs]
//   row 2: Claude agent strip — icon · model · tokens·cost · status sentence
//   row 3: GPT    agent strip — same shape
//   row 4: phase dots + dot labels + run metadata (started · elapsed · round)
// The 4 rows collapse to 3 on narrow widths (the per-agent strips reduce
// font and the metadata wraps under the dots row).
function RunDetailHeader({ run, errorCount, showErrors, onToggleErrors, tab, onTabChange }) {
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
      gap: 6,
    }}>
      {/* Row 1: topic + cost + status/errors + Conversation/Consumption tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <Topic text={run.topic} />
        <CostBadge cost={total} tokens={totalTokens} />
        <StatusErrorsBadge
          status={run.status}
          errorCount={errorCount}
          showErrors={showErrors}
          onToggleErrors={onToggleErrors}
        />
        {onTabChange && (
          <TimelineTabs active={tab} onChange={onTabChange} prominent />
        )}
      </div>
      {/* Row 2: Claude agent strip (spec 0033). */}
      <AgentStrip agent="claude" run={run} />
      {/* Row 3: GPT agent strip. */}
      <AgentStrip agent="gpt" run={run} />
      {/* Row 4: phase dots + dot labels + run metadata. */}
      <PhaseDotsRow
        run={run}
        startedClock={startedClock}
        elapsedLabel={elapsedLabel}
        drafterLabel={drafterLabel}
      />
    </header>
  );
}

// ─────────────────── Spec 0033 — per-agent header strip ─────────────────────
function AgentStrip({ agent, run }) {
  const meta = AGENT_META[agent];
  const ag = run.agents?.[agent] || {};
  const tokensIn = ag.tokens?.in || 0;
  const tokensOut = ag.tokens?.out || 0;
  const totalTokens = tokensIn + tokensOut;
  const cost = ag.cost || 0;
  const modelId = ag.modelId || ag.model_id || meta?.name || agent;
  const { live, phrase } = composeAgentActivity(agent, run);
  const dotColor = live ? meta.color : 'var(--border-3)';
  const phraseColor = live ? 'var(--fg-1)' : 'var(--fg-3)';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      minWidth: 0,
      // Subtle agent-tinted left rail so the two strips read as paired.
      borderLeft: `2px solid ${meta.color}`,
      paddingLeft: 8,
    }}>
      <AgentIcon agent={agent} size={14} />
      <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, minWidth: 56 }}>
        {meta.name}
      </span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        {modelId}
      </span>
      {/* token + cost badge — same shape as CostBadge but agent-scoped */}
      <span className="mono" title={`${cost.toFixed(4)} USD · ${totalTokens.toLocaleString()} tokens`}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '2px 8px', borderRadius: 999,
              background: 'var(--bg-2)', border: '1px solid var(--border-1)',
              fontSize: 10.5, color: 'var(--fg-1)',
              whiteSpace: 'nowrap',
            }}>
        <span className="num">{fmt.tokens(totalTokens)}t</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span className="num" style={{ color: 'var(--fg-2)' }}>{fmt.cost(cost)}</span>
      </span>
      {/* pipe separator */}
      <span style={{ color: 'var(--border-2)', fontSize: 12 }}>│</span>
      {/* status dot + activity sentence */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
        <Dot color={dotColor} pulse={live ? 'pulse-a' : null} size={6} />
        <span style={{
          fontSize: 11.5, color: phraseColor,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {phrase}
        </span>
      </span>
      <span style={{ flex: 1 }} />
    </div>
  );
}

// ─────────────────── Spec 0033 — phase dots row with labels ─────────────────
function PhaseDotsRow({ run, startedClock, elapsedLabel, drafterLabel }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      paddingTop: 2,
    }}>
      <PhaseDots run={run} />
      <span className="mono" style={{
        fontSize: 9.5, color: 'var(--fg-3)', letterSpacing: '0.03em',
      }}>
        preflight · drafts · negotiate · drafting · review
      </span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-3)',
        whiteSpace: 'nowrap',
      }}>
        started <span style={{ color: 'var(--fg-1)' }}>{startedClock}</span>
        &nbsp;·&nbsp;drafter <span style={{ color: 'var(--fg-1)' }}>{drafterLabel}</span>
        &nbsp;·&nbsp;<span style={{ color: 'var(--fg-1)' }}>{elapsedLabel}</span> elapsed
        {run.status === 'running' && (run.phase === 2 || run.phase === 4) && run.round && (
          <>&nbsp;·&nbsp;round <span style={{ color: 'var(--fg-1)' }}>
            {run.round.current}/{run.round.soft}
          </span><span style={{ color: 'var(--fg-3)' }}>&nbsp;(hard {run.round.hard})</span></>
        )}
      </span>
    </div>
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
//
// Spec 0029: two tabs — `Conversation` (existing card view) and
// `Consumption` (per-turn context-window bars). Tabs sit on the left of
// the pane toolbar; the two `AgentLegendChip`s move to the right end.
function Timeline({ run, tab = 'conversation', highlightedTurnKeys }) {
  const items = React.useMemo(() => buildTimeline(run), [run]);
  const [openId, setOpenId] = React.useState(null);

  // Reset open modal when navigating between runs. Tab state is owned by
  // RunDetail (spec 0033 lifted it so the header can render the pill).
  React.useEffect(() => {
    setOpenId(null);
  }, [run.id]);

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
        {/* Tabs moved to the run header (spec 0033). The toolbar now
            keeps the per-agent legend chips + the live-count chip. */}
        <span style={{ flex: 1 }} />
        <AgentLegendChip agent="claude" tokens={claudeTotal.tokens.in + claudeTotal.tokens.out} cost={claudeTotal.cost} />
        <AgentLegendChip agent="gpt"    tokens={gptTotal.tokens.in + gptTotal.tokens.out} cost={gptTotal.cost} />
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
      {tab === 'conversation' ? (
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '8px 16px 24px', background: 'var(--bg-0)' }}>
          {items.map((item) => (
            <TimelineItem
              key={item.id}
              item={item}
              run={run}
              onOpen={() => setOpenId(item.id)}
              highlightedTurnKeys={highlightedTurnKeys}
            />
          ))}
        </div>
      ) : (
        <ConsumptionView run={run} />
      )}
      {tab === 'conversation' && openItem && (
        <ArtifactModal
          item={openItem}
          run={run}
          onClose={() => setOpenId(null)}
        />
      )}
    </section>
  );
}

// Segmented control of two pills — matches the AgentLegendChip aesthetic
// (rounded pill, var(--bg-2) background, agent-style accent on active).
// Spec 0033: when ``prominent`` is set (in the run header), bump font +
// padding and add a 1px accent underline on the active tab so the
// control reads as primary chrome.
function TimelineTabs({ active, onChange, prominent = false }) {
  const tabs = [
    { id: 'conversation', label: 'Conversation' },
    { id: 'consumption',  label: 'Consumption'  },
  ];
  const fontSize = prominent ? 12.5 : 11.5;
  const padV = prominent ? 4 : 3;
  const padH = prominent ? 14 : 12;
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'stretch',
      borderRadius: 999, overflow: 'hidden',
      border: '1px solid var(--border-1)',
      background: 'var(--bg-2)',
      flexShrink: 0,
    }}>
      {tabs.map((t, i) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            style={{
              appearance: 'none',
              border: 'none',
              borderLeft: i === 0 ? 'none' : '1px solid var(--border-1)',
              borderBottom: prominent && isActive ? `2px solid ${COLORS.info}` : 'none',
              background: isActive ? 'var(--bg-3)' : 'transparent',
              color: isActive ? 'var(--fg-0)' : 'var(--fg-2)',
              fontSize,
              fontWeight: isActive ? 600 : 500,
              padding: `${padV}px ${padH}px`,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontFamily: 'inherit',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
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

// ─────────────────── Consumption tab (spec 0029) ───────────────────
//
// Per-turn context-window visualisation. Each row is one API call (one
// turn per round per agent); each bar shows that call's input fill +
// output trailing segment against the model's actual context window.
// Layout borrows the 3-col grid from `how-it-works.jsx::LifecycleRow`
// (phase label · Claude lane · OpenAI lane) so the conceptual map and
// the actual numbers share a visual idiom.
//
// IMPORTANT: the wire format camelizes inner dict keys, so the per-turn
// dict comes through as e.g. `phase2Round1Claude` — NOT the snake-case
// form `phase2_round1_claude` we use on the Python side. The
// `consumptionKey` helper below mirrors the server's `_snake_to_camel`
// rewrite of those keys.

// Spec 0030: context windows now flow through the wire — every
// `phaseTokenUsage` entry carries its `contextWindow`, and the agent
// state carries a per-agent fallback. The JS registry that spec 0029
// hand-rolled is gone (the values were wrong — see spec 0030).
const DEFAULT_CONTEXT_WINDOW = 128_000;

function contextWindowFor(usage, run, agent) {
  if (usage && usage.contextWindow) return usage.contextWindow;
  const fallback = run?.agents?.[agent]?.contextWindow;
  if (fallback) return fallback;
  return DEFAULT_CONTEXT_WINDOW;
}

// Spec 0030: per-piece segment colours mirror the Tk palette in
// `how-it-works.jsx::ChatLifecycle`. The Consumption tab fills the bar
// with one segment per prompt-piece kind so the live numbers read as a
// direct continuation of the conceptual diagram.
//
// `bg` is the segment fill (solid, ~55% alpha). `fg` is the legend swatch
// + tooltip-line accent.
const KIND_COLORS = {
  brief: { bg: 'rgba(107,156,240,0.65)', fg: '#9ab6e8',         label: 'brief' },
  d1:    { bg: 'rgba(212,165,116,0.70)', fg: 'var(--agent-a)',  label: 'Claude P1 draft' },
  d2:    { bg: 'rgba(124,196,184,0.70)', fg: 'var(--agent-b)',  label: 'GPT P1 draft' },
  plan:  { bg: 'rgba(111,179,128,0.65)', fg: 'var(--ok)',       label: 'agreed plan' },
  hist:  { bg: 'rgba(212,160,86,0.55)',  fg: 'var(--warn)',     label: 'P2 history' },
  draft: { bg: 'rgba(217,106,106,0.55)', fg: 'var(--err)',      label: 'current draft' },
  histp: { bg: 'rgba(212,160,86,0.40)',  fg: 'var(--warn)',     label: 'P4 history' },
};

// Canonical render order for segments inside a bar (left → right). Mirrors
// the order content appears in the prompt; keeps the bars visually stable
// even when keys arrive in a different order from the wire.
const KIND_ORDER = ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'];

// Build the wire-format inner key for a given (phase, round, agent).
// Examples:
//   (0, null, 'claude') → 'phase0Claude'
//   (2, 3,    'gpt')    → 'phase2Round3Gpt'
function consumptionKey(phase, round, agent) {
  const Ag = agent === 'gpt' ? 'Gpt' : 'Claude';
  if (round && round > 0) return `phase${phase}Round${round}${Ag}`;
  return `phase${phase}${Ag}`;
}

// Walk the per-turn usage dict and produce ordered rows for rendering.
// Each row: { id, phase, round, label, claude, gpt }. `claude`/`gpt`
// is the `TurnTokenUsage`-shaped value or `null` (silent lane).
function buildConsumptionRows(run) {
  const usage = run.phaseTokenUsage || {};
  // Parse the camelized keys back into (phase, round, agent).
  const parsed = [];
  for (const k of Object.keys(usage)) {
    const m = /^phase(\d+)(?:Round(\d+))?(Claude|Gpt)$/.exec(k);
    if (!m) continue;
    parsed.push({
      key: k,
      phase: Number(m[1]),
      round: m[2] ? Number(m[2]) : 0,
      agent: m[3] === 'Gpt' ? 'gpt' : 'claude',
    });
  }
  // Group by (phase, round). Use a Map keyed `${phase}:${round}` to
  // preserve insertion-order; we'll re-sort below.
  const grouped = new Map();
  for (const p of parsed) {
    const k = `${p.phase}:${p.round}`;
    if (!grouped.has(k)) grouped.set(k, { phase: p.phase, round: p.round, claude: null, gpt: null });
    grouped.get(k)[p.agent] = usage[p.key];
  }
  // Sort by phase then round.
  const rows = Array.from(grouped.values()).sort((a, b) => {
    if (a.phase !== b.phase) return a.phase - b.phase;
    return a.round - b.round;
  });
  // Attach human labels.
  for (const r of rows) {
    r.id = `${r.phase}:${r.round}`;
    if (r.round > 0) {
      r.label = `Round ${r.round}`;
    } else {
      r.label = ''; // phase-only rows get a blank sub-label
    }
  }
  return rows;
}

const PHASE_NAMES = {
  0: 'P0 Preflight',
  1: 'P1 Research',
  2: 'P2 Negotiate',
  3: 'P3 Drafting',
  4: 'P4 Review',
};

function ConsumptionView({ run }) {
  const rows = React.useMemo(() => buildConsumptionRows(run), [run.phaseTokenUsage]);
  // Spec 0031: per-row click-to-expand. Set of row ids currently open.
  // Resets implicitly when navigating runs (Timeline component remounts
  // ConsumptionView via the tab toggle).
  const [expanded, setExpanded] = React.useState(() => new Set());
  const toggleRow = React.useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  if (rows.length === 0) {
    return <ConsumptionEmptyState />;
  }
  // Pass `run` down so TokenBar can fall back to AgentState.contextWindow
  // when a per-turn entry lacks its own (pre-0030 transcripts).

  return (
    <div style={{
      flex: 1, minHeight: 0, overflow: 'auto',
      padding: '16px 16px 32px', background: 'var(--bg-0)',
    }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '120px 1fr 1fr',
        gap: 10, alignItems: 'stretch',
        padding: 14, background: 'var(--bg-1)',
        border: '1px solid var(--border-1)', borderRadius: 8,
      }}>
        {/* Header strip — phase / Claude / OpenAI labels. Matches the
            how-it-works ChatLifecycle visual exactly. */}
        <div className="mono" style={{
          fontSize: 10.5, color: 'transparent', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>phase</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--agent-a)', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>Claude lane</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--agent-b)', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>OpenAI lane</div>

        {rows.map((row, i) => {
          // Group rounds of the same phase under a single phase label —
          // only print the phase title on the first row of each phase
          // block. Sub-rows show their round label inside the same cell.
          const isFirstOfPhase = i === 0 || rows[i - 1].phase !== row.phase;
          return (
            <ConsumptionRow
              key={row.id}
              row={row}
              run={run}
              showPhaseTitle={isFirstOfPhase}
              expanded={expanded.has(row.id)}
              onToggle={() => toggleRow(row.id)}
            />
          );
        })}
      </div>

      <ConsumptionLegend />
    </div>
  );
}

function ConsumptionRow({ row, run, showPhaseTitle, expanded, onToggle }) {
  // Spec 0031: whole row is clickable to toggle the expanded body. The
  // expanded body sits below as a 4th grid row spanning all 3 columns
  // (so the 3-col rhythm of the grid keeps working).
  return (
    <React.Fragment>
      {/* Phase / round label cell */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          padding: '10px',
          background: showPhaseTitle ? 'var(--bg-2)' : 'transparent',
          border: showPhaseTitle ? '1px solid var(--border-2)' : '1px solid transparent',
          borderRadius: 6,
          minHeight: 56,
          cursor: 'pointer',
        }}>
        {showPhaseTitle && (
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--fg-0)' }}>
            {PHASE_NAMES[row.phase] || `Phase ${row.phase}`}
          </div>
        )}
        {row.label && (
          <div className="mono" style={{
            fontSize: 9.5, color: 'var(--fg-3)', letterSpacing: '0.06em',
            textTransform: 'uppercase', marginTop: showPhaseTitle ? 3 : 0,
          }}>{row.label}</div>
        )}
        <div className="mono" style={{
          fontSize: 9, color: 'var(--fg-4)', marginTop: 4,
          letterSpacing: '0.04em',
        }}>{expanded ? '▾ click to collapse' : '▸ click to expand'}</div>
      </div>
      {/* Claude lane */}
      <div onClick={onToggle} style={{ cursor: 'pointer' }}>
        <TokenLaneCell usage={row.claude} agent="claude" run={run} />
      </div>
      {/* OpenAI lane */}
      <div onClick={onToggle} style={{ cursor: 'pointer' }}>
        <TokenLaneCell usage={row.gpt} agent="gpt" run={run} />
      </div>
      {expanded && (
        <ConsumptionRowExpanded row={row} run={run} />
      )}
    </React.Fragment>
  );
}

// Per-row expanded body — a per-piece breakdown table laid out side-by-
// side for both lanes. Spans all 3 columns of the parent grid.
function ConsumptionRowExpanded({ row, run }) {
  // Collect the union of kinds present on either lane, in canonical
  // KIND_ORDER. Skip kinds that are zero on both sides.
  const cPieces = (row.claude && row.claude.promptPieces) || {};
  const gPieces = (row.gpt && row.gpt.promptPieces) || {};
  const kindsShown = KIND_ORDER.filter(
    (k) => (Number(cPieces[k]) || 0) > 0 || (Number(gPieces[k]) || 0) > 0
  );

  // Renormalise each lane's piece counts to the provider's `input`
  // token total, so the numbers in the table match what the bar shows.
  const renormLane = (usage) => {
    if (!usage) return {};
    const pieces = usage.promptPieces || {};
    const tokensIn = Number(usage.in) || 0;
    const present = KIND_ORDER.filter((k) => Number(pieces[k]) > 0);
    if (present.length === 0 || tokensIn <= 0) return {};
    const rawSum = present.reduce((acc, k) => acc + Number(pieces[k] || 0), 0);
    if (rawSum <= 0) return {};
    const scale = tokensIn / rawSum;
    const out = {};
    for (const k of present) {
      out[k] = Math.max(0, Math.round(Number(pieces[k] || 0) * scale));
    }
    return out;
  };
  const cAdj = renormLane(row.claude);
  const gAdj = renormLane(row.gpt);

  const numCell = (n, opts = {}) => (
    <span className="mono num" style={{
      fontSize: 11, color: 'var(--fg-1)',
      ...(opts.muted ? { color: 'var(--fg-3)' } : {}),
      ...(opts.bold ? { fontWeight: 600 } : {}),
    }}>{n != null ? `${fmt.tokens(n)}t` : '—'}</span>
  );

  return (
    <div style={{
      gridColumn: '1 / 4',
      padding: '12px 14px',
      background: 'var(--bg-2)',
      border: '1px solid var(--border-2)', borderRadius: 6,
      marginTop: -4,  // hug the row above
    }}>
      <div className="mono" style={{
        fontSize: 10, color: 'var(--fg-3)',
        textTransform: 'uppercase', letterSpacing: '0.06em',
        marginBottom: 8,
      }}>
        per-input breakdown · {PHASE_NAMES[row.phase] || `Phase ${row.phase}`}
        {row.label && ` · ${row.label}`}
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: '4px 16px',
        alignItems: 'baseline',
        fontSize: 11,
      }}>
        {/* Header row */}
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--fg-4)', textTransform: 'uppercase' }}>input</div>
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--agent-a)', textTransform: 'uppercase' }}>Claude</div>
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--agent-b)', textTransform: 'uppercase' }}>GPT</div>

        {/* Per-kind rows */}
        {kindsShown.map((k) => (
          <React.Fragment key={k}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              color: 'var(--fg-1)',
            }}>
              <span style={{
                display: 'inline-block', width: 10, height: 10,
                background: KIND_COLORS[k].bg, borderRadius: 2,
              }} />
              {KIND_COLORS[k].label}
            </div>
            <div>{numCell(cAdj[k])}</div>
            <div>{numCell(gAdj[k])}</div>
          </React.Fragment>
        ))}

        {/* Divider */}
        <div style={{ gridColumn: '1 / 4', height: 1, background: 'var(--border-2)', margin: '6px 0' }} />

        {/* Totals row */}
        <div style={{ color: 'var(--fg-0)', fontWeight: 500 }}>Input total</div>
        <div>{numCell(row.claude ? Number(row.claude.in) || 0 : null, { bold: true })}</div>
        <div>{numCell(row.gpt ? Number(row.gpt.in) || 0 : null, { bold: true })}</div>

        <div style={{ color: 'var(--fg-1)' }}>Output</div>
        <div>{numCell(row.claude ? Number(row.claude.out) || 0 : null)}</div>
        <div>{numCell(row.gpt ? Number(row.gpt.out) || 0 : null)}</div>

        {/* Web-search row — count + cost (spec 0031). Only show when
            at least one lane had a search this turn. */}
        {((row.claude && Number(row.claude.searches) > 0)
          || (row.gpt && Number(row.gpt.searches) > 0)) && (
          <React.Fragment>
            <div style={{ color: 'var(--fg-1)' }}>Web searches</div>
            <div>{searchCell(row.claude)}</div>
            <div>{searchCell(row.gpt)}</div>
            <div style={{ color: 'var(--fg-3)', fontSize: 10 }}>Tool cost</div>
            <div className="mono num" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>
              {row.claude ? fmt.cost(Number(row.claude.searchCost) || 0) : '—'}
            </div>
            <div className="mono num" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>
              {row.gpt ? fmt.cost(Number(row.gpt.searchCost) || 0) : '—'}
            </div>
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

function searchCell(usage) {
  if (!usage) return <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>—</span>;
  const n = Number(usage.searches) || 0;
  return (
    <span className="mono num" style={{ fontSize: 11, color: 'var(--fg-1)' }}>
      {n.toLocaleString()}
    </span>
  );
}

// One cell of a row — either a populated TokenBar or a silent placeholder.
function TokenLaneCell({ usage, agent, run }) {
  if (!usage) {
    return (
      <div className="mono" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '10px', minHeight: 56,
        background: 'var(--bg-1)',
        border: '1px dashed var(--border-2)', borderRadius: 6,
        fontSize: 10, color: 'var(--fg-4)', letterSpacing: '0.04em',
      }}>silent</div>
    );
  }
  return <TokenBar usage={usage} agent={agent} run={run} />;
}

// Spec 0030: the bar now renders one segment per prompt-piece kind
// from `usage.promptPieces` (Tk palette), renormalised against
// `usage.in` so heuristic-vs-provider-token mismatches don't distort
// segment widths. An output tail still trails the input region (darker
// shade, thinner band). When `promptPieces` is missing (pre-0030
// transcripts) we fall back to the spec-0029 single-fill rendering.
function TokenBar({ usage, agent, run }) {
  const meta = AGENT_META[agent];
  const tokensIn  = Number(usage.in)  || 0;
  const tokensOut = Number(usage.out) || 0;
  const cacheRead = Number(usage.cacheRead) || 0;
  const cacheWrite = Number(usage.cacheWrite) || 0;
  const modelId   = usage.modelId || null;
  const cost      = Number(usage.cost) || 0;
  const ctxWindow = contextWindowFor(usage, run, agent);
  const piecesRaw = usage.promptPieces || {};

  // Renormalise heuristic piece counts so they sum to the provider's
  // input_tokens. Skip zero-valued entries; preserve KIND_ORDER for
  // visual stability.
  const renormalised = (() => {
    const present = KIND_ORDER.filter((k) => Number(piecesRaw[k]) > 0);
    if (present.length === 0 || tokensIn <= 0) return [];
    const rawSum = present.reduce((acc, k) => acc + Number(piecesRaw[k] || 0), 0);
    if (rawSum <= 0) return [];
    const scale = tokensIn / rawSum;
    return present.map((k) => ({
      kind: k,
      raw: Number(piecesRaw[k] || 0),
      tokens: Math.max(0, Math.round(Number(piecesRaw[k] || 0) * scale)),
    }));
  })();
  const hasPieces = renormalised.length > 0;

  const inputPct  = Math.min(100, (tokensIn  / ctxWindow) * 100);
  const outputPct = Math.min(100 - inputPct, (tokensOut / ctxWindow) * 100);

  // Build tooltip — lead with model + window, then per-kind sizes if any.
  const tooltipLines = [
    `${meta.name} · ${modelId || 'unknown model'}`,
    `input:  ${tokensIn.toLocaleString()}t  (cache read ${cacheRead.toLocaleString()}t)`,
    `output: ${tokensOut.toLocaleString()}t`,
    cacheWrite ? `cache write: ${cacheWrite.toLocaleString()}t` : null,
    `cost:   ${fmt.cost(cost)}`,
    `window: ${ctxWindow.toLocaleString()}t (${inputPct.toFixed(1)}% used)`,
  ];
  if (hasPieces) {
    tooltipLines.push('', 'inputs:');
    for (const p of renormalised) {
      const lbl = KIND_COLORS[p.kind]?.label || p.kind;
      tooltipLines.push(`  ${lbl.padEnd(18, ' ')} ${p.tokens.toLocaleString()}t`);
    }
  }
  const tooltip = tooltipLines.filter((l) => l !== null).join('\n');

  return (
    <div title={tooltip} style={{
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      padding: '8px 10px', minHeight: 56,
      background: 'var(--bg-2)',
      border: `1px solid ${meta.border}`, borderRadius: 6,
    }}>
      {/* Bar */}
      <div style={{
        position: 'relative',
        width: '100%', height: 14,
        background: 'var(--bg-3)',
        borderRadius: 4, overflow: 'hidden',
      }}>
        {hasPieces ? (
          // Per-piece segments (spec 0030). Each segment's width is its
          // share of the context window. Cache-read shading is dropped
          // here — the prompt-piece breakdown supersedes it for the visual.
          (() => {
            let offsetPct = 0;
            return renormalised.map((p) => {
              const colour = KIND_COLORS[p.kind]?.bg || 'var(--fg-3)';
              const widthPct = Math.min(100 - offsetPct, (p.tokens / ctxWindow) * 100);
              const segment = (
                <div key={p.kind} style={{
                  position: 'absolute', top: 0, bottom: 0,
                  left: `${offsetPct}%`, width: `${widthPct}%`,
                  background: colour,
                  // Hairline separator on the right edge — keeps adjacent
                  // segments visually distinct.
                  borderRight: '1px solid rgba(0,0,0,0.25)',
                }} />
              );
              offsetPct += widthPct;
              return segment;
            });
          })()
        ) : (
          // Fallback: spec-0029 single-fill rendering for pre-0030 data.
          <React.Fragment>
            {cacheRead > 0 && (
              <div style={{
                position: 'absolute', left: 0, top: 0, bottom: 0,
                width: `${Math.min(100, (cacheRead / ctxWindow) * 100)}%`,
                background: meta.color + '55',
              }} />
            )}
            {tokensIn - cacheRead > 0 && (
              <div style={{
                position: 'absolute',
                left: `${Math.min(100, (cacheRead / ctxWindow) * 100)}%`,
                top: 0, bottom: 0,
                width: `${Math.max(0, Math.min(100, ((tokensIn - cacheRead) / ctxWindow) * 100))}%`,
                background: meta.color,
              }} />
            )}
          </React.Fragment>
        )}
        {/* Output tail — thinner band, darker shade, sits after input. */}
        {outputPct > 0 && (
          <div style={{
            position: 'absolute', left: `${inputPct}%`, top: 3, bottom: 3,
            width: `${outputPct}%`,
            background: meta.color,
            opacity: 0.45,
            borderLeft: '1px solid rgba(0,0,0,0.25)',
          }} />
        )}
      </div>
      {/* Numeric row underneath */}
      <div className="mono" style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginTop: 5,
        fontSize: 10, color: 'var(--fg-3)',
      }}>
        <span style={{ color: 'var(--fg-2)' }}>{fmt.tokens(tokensIn)}t</span>
        <span>in</span>
        <span>·</span>
        <span style={{ color: 'var(--fg-2)' }}>{fmt.tokens(tokensOut)}t</span>
        <span>out</span>
        <span style={{ flex: 1 }} />
        <span>{inputPct.toFixed(1)}% of {fmt.tokens(ctxWindow)}t</span>
      </div>
    </div>
  );
}

function ConsumptionLegend() {
  // Spec 0030 — the bars now break down into prompt-piece kinds. Legend
  // shows the Tk palette + the output tail; bar total is the model's
  // real context window (from `RunStarted.{agent}_context_window`).
  // Spec 0031 — adds the click-to-expand hint.
  return (
    <React.Fragment>
      <div className="mono" style={{
        marginTop: 14, padding: '10px 14px',
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 6,
        display: 'flex', flexWrap: 'wrap', gap: 14,
        alignItems: 'center',
        fontSize: 10.5, color: 'var(--fg-3)',
      }}>
        {KIND_ORDER.map((k) => (
          <LegendSwatch key={k} color={KIND_COLORS[k].bg} label={KIND_COLORS[k].label} />
        ))}
        <span style={{ width: 1, alignSelf: 'stretch', background: 'var(--border-2)' }} />
        <LegendSwatch color="var(--agent-a)" label="output (tail)" alpha={0.45} thin />
        <span style={{ flex: 1 }} />
        <span>bar total = model context window</span>
      </div>
      <div className="mono" style={{
        marginTop: 6, padding: '0 4px',
        fontSize: 10, color: 'var(--fg-4)', fontStyle: 'italic',
      }}>
        click any phase row to see exact per-input numbers + web-search count
      </div>
    </React.Fragment>
  );
}

function LegendSwatch({ color, label, alpha, thin }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        display: 'inline-block',
        width: 16, height: thin ? 4 : 10,
        background: color, opacity: alpha ?? 1,
        borderRadius: 2,
      }} />
      <span>{label}</span>
    </span>
  );
}

function ConsumptionEmptyState() {
  return (
    <div style={{
      flex: 1, minHeight: 0, overflow: 'auto',
      padding: '32px 24px', background: 'var(--bg-0)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 12,
    }}>
      <div style={{ fontSize: 13, color: 'var(--fg-1)', fontWeight: 500 }}>
        No per-turn token data
      </div>
      <div className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-3)', textAlign: 'center',
        lineHeight: 1.6, maxWidth: 460,
      }}>
        This run was recorded before per-turn telemetry was added,<br/>
        so its individual chat sizes aren't tracked. The run-total chips<br/>
        above still reflect the full cost and token count.
      </div>
    </div>
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
function TimelineItem({ item, run, onOpen, highlightedTurnKeys }) {
  if (item.kind === 'phase-divider') return <PhaseDivider item={item} run={run} />;
  if (item.kind === 'error')         return <ErrorCard item={item} />;
  if (item.kind === 'deadlock')      return <DeadlockCard item={item} />;
  return <ArtifactCard
    item={item}
    run={run}
    onOpen={onOpen}
    highlightedTurnKeys={highlightedTurnKeys}
  />;
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
// Spec 0030: clicking a card toggles inline expansion (it no longer
// opens the modal directly). The unfolded body renders the gist line,
// the TL;DR summary, and a "View in full mode" button — that button is
// the ONLY entry point to the existing `ArtifactModal`.
function ArtifactCard({ item, run, onOpen, highlightedTurnKeys }) {
  const meta = item.agent ? AGENT_META[item.agent] : null;
  const [hover, setHover] = React.useState(false);
  const [expanded, setExpanded] = React.useState(false);

  const accentColor = meta?.color || 'var(--fg-2)';
  const isLive = item.live;
  const hasSummary = !isLive && !!(item.summary && String(item.summary).trim());
  const gist = !isLive ? composeGist(item, run) : '';
  // Spec 0034: sentiment paragraph (Phase 2/4 only) takes priority over
  // the single-line gist when there's enough material.
  const sentiment = !isLive ? composeSentiment(item, run) : '';
  const canExpand = !isLive && (hasSummary || gist || sentiment);

  const header = <ArtifactHeader item={item} meta={meta} hover={hover} />;

  // Spec 0034: cross-axis click-to-highlight. If this card's turnKey is
  // in the highlight set (from the CritiqueExplorer), apply a ring +
  // briefly draw attention. Two variants (q / d) for visual provenance.
  const flashKind = item.turnKey && highlightedTurnKeys
    ? (highlightedTurnKeys.get ? highlightedTurnKeys.get(item.turnKey) : null)
    : null;
  const flashColor = flashKind === 'q' ? COLORS.info
                   : flashKind === 'd' ? COLORS.warn
                   : null;

  const toggleExpand = () => {
    if (canExpand) setExpanded((v) => !v);
  };

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
        transition: 'border-color 120ms, background 120ms, box-shadow 1500ms ease-out',
        ...(isLive ? {
          borderLeft: `2px solid ${accentColor}`,
        } : {}),
        ...(expanded ? {
          borderColor: accentColor + '55',
          background: 'var(--bg-1)',
        } : {}),
        ...(flashColor ? {
          boxShadow: `0 0 0 2px ${flashColor}, 0 0 24px ${flashColor}55`,
          borderColor: flashColor,
        } : {}),
      }}
    >
      <button
        type="button"
        onClick={toggleExpand}
        disabled={!canExpand}
        aria-expanded={expanded}
        style={{
          display: 'block', width: '100%', textAlign: 'left',
          padding: '10px 12px',
          background: hover && canExpand ? 'var(--bg-2)' : 'transparent',
          transition: 'background 120ms',
          cursor: canExpand ? 'pointer' : 'default',
        }}>
        {header}
      </button>
      {expanded && (
        <ArtifactExpandedBody
          item={item}
          gist={sentiment || gist}
          summary={item.summary}
          onOpen={onOpen}
        />
      )}
      {isLive && <ArtifactLiveBody item={item} />}
    </div>
  );
}

// The unfolded body — gist line + summary paragraph + "View in full mode".
// Sits below the header inside the same card. No modal entry from anywhere
// here EXCEPT the explicit button.
function ArtifactExpandedBody({ item, gist, summary, onOpen }) {
  return (
    <div style={{
      borderTop: '1px solid var(--border-2)',
      padding: '10px 12px 12px',
      background: 'var(--bg-1)',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      {gist && (
        <div style={{
          fontSize: 11.5, color: 'var(--fg-1)', lineHeight: 1.55,
          fontStyle: 'italic',
        }}>
          {gist}
        </div>
      )}
      {summary && (
        <p style={{
          margin: 0,
          fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}>{summary}</p>
      )}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
        marginTop: 2,
      }}>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onOpen && onOpen(); }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 12px',
            fontSize: 11.5,
            color: 'var(--fg-0)',
            background: 'var(--bg-2)',
            border: '1px solid var(--border-1)',
            borderRadius: 999,
            fontFamily: 'inherit',
            fontWeight: 500,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}>
          View in full mode
          <Icon.Arrow style={{ width: 11, height: 11 }} />
        </button>
      </div>
    </div>
  );
}

// Synthesise a one-line gist describing what happened in this item.
// Reads `item.stats`, `item.statsPhase`, `item.agent`, `item.round` plus
// `run.disagreements` (filtered to the item's round/phase). Returns "" if
// nothing meaningful can be said.
function composeGist(item, run) {
  if (!item) return '';
  const phase = item.statsPhase;
  const agent = item.agent;
  const agentName = agent ? (AGENT_META[agent]?.name || agent) : 'Agent';
  const stats = item.stats || {};
  const ds = Array.isArray(run?.disagreements) ? run.disagreements : [];

  // Helpers
  const plur = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  const status = (stats.status || '').toUpperCase();

  // ─── Phase 0 — preflight critique (item.kind === 'input') ──────────────
  if (item.kind === 'input') {
    const s = stats || {};
    if (s.state === 'ok') return 'Both agents found the brief OK to proceed.';
    if (s.state === 'issues' && s.count > 0) {
      return `Brief came back with ${plur(s.count, 'issue')} flagged across the two agents.`;
    }
    return '';
  }

  // ─── Phase 0 — per-agent critique (spec 0033 split) ────────────────────
  if (item.kind === 'preflight') {
    const issues = stats.briefIssues ?? 0;
    if (status === 'BRIEF_OK') {
      return issues > 0
        ? `${agentName} approved the brief but flagged ${plur(issues, 'minor issue')}.`
        : `${agentName} approved the brief without changes.`;
    }
    if (status === 'BRIEF_NEEDS_INPUT') {
      return `${agentName} flagged ${plur(issues, 'issue')} requiring user input before Phase 1.`;
    }
    if (issues > 0) {
      return `${agentName} flagged ${plur(issues, 'issue')} on the brief.`;
    }
    return '';
  }

  // ─── Phase 1 — independent draft ───────────────────────────────────────
  if (phase === 1) {
    return `${agentName} wrote an independent Phase 1 draft (no critique stats this phase).`;
  }

  // ─── Phase 2 — negotiation turn ────────────────────────────────────────
  if (phase === 2) {
    const parts = [];
    if (status === 'AGREED') parts.push(`${agentName} agreed to the plan`);
    else if (status === 'NEGOTIATING') parts.push(`${agentName} still negotiating`);
    else parts.push(agentName);

    if (typeof stats.openQuestions === 'number' && stats.openQuestions > 0) {
      parts.push(`raised ${plur(stats.openQuestions, 'question')}`);
    }
    if (typeof stats.blocking === 'number' && stats.blocking > 0) {
      parts.push(`${plur(stats.blocking, 'blocking disagreement')}`);
    }
    if (typeof stats.fsd === 'number' && stats.fsd > 0) {
      parts.push(`${stats.fsd} final-surfaced`);
    }
    // Mention this round's disagreement transitions for THIS agent.
    const myProg = ds
      .filter((d) => d && d.phase === 2)
      .flatMap((d) => (d.progression || []).filter((p) => p.agent === agent && p.round === item.round))
      .map((p) => p.action);
    if (myProg.includes('conceded')) parts.push('conceded a held D-N');
    if (myProg.includes('aligned')) parts.push('marked one non-blocking');
    return parts.length === 1 ? '' : parts[0] + ', ' + parts.slice(1).join(', ') + '.';
  }

  // ─── Phase 3 — drafter wrote v1 ───────────────────────────────────────
  if (phase === 3 || item.kind === 'doc' || item.kind === 'doc-live') {
    return `${agentName} wrote v1 of the converged document.`;
  }

  // ─── Phase 4 — review turn ────────────────────────────────────────────
  if (phase === 4) {
    const parts = [];
    if (status === 'APPROVED') parts.push(`${agentName} approved the draft`);
    else if (status === 'REVIEWING') parts.push(`${agentName} still reviewing`);
    else parts.push(agentName);

    if (typeof stats.openIssues === 'number' && stats.openIssues > 0) {
      parts.push(`${plur(stats.openIssues, 'issue')} open`);
    }
    return parts.length === 1 ? '' : parts[0] + ', ' + parts.slice(1).join(', ') + '.';
  }

  return '';
}


// ─────────────────── Spec 0034 — sentiment paragraph composer ───────────────
//
// Replaces the single-line gist on Phase 1 + Phase 2 + Phase 4 unfolded
// cards with 2-3 sentences synthesised from:
// - item.stats (TurnStats)
// - run.questions filtered to (phase, raised_by=agent, raised_round=round)
// - run.disagreements filtered to (phase, round, agent)
// - prior-round counts (delta computation)
//
// Returns "" if there's not enough material for a meaningful paragraph
// (Phase 1 first turn before stats exist, etc.) — caller falls back to
// composeGist for those.
function composeSentiment(item, run) {
  if (!item) return '';
  const phase = item.statsPhase;
  const agent = item.agent;
  const agentName = agent ? (AGENT_META[agent]?.name || agent) : 'Agent';
  const stats = item.stats || {};
  const status = (stats.status || '').toUpperCase();
  const round = Number(item.round) || 0;
  const plur = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  const allQuestions = Array.isArray(run?.questions) ? run.questions : [];
  const allDis = Array.isArray(run?.disagreements) ? run.disagreements : [];

  // Phase 1 — independent draft. No critique stats; sentiment comes from
  // protocol artefacts in the draft itself (V/U tag counts via the draft
  // body — out of scope to parse here). Fall back to composeGist.
  if (phase === 1) {
    return '';
  }

  // Phase 2 — negotiation turn. Headline: status. Then counts + deltas
  // from question/disagreement objects.
  if (phase === 2) {
    const myNewQs = allQuestions.filter(
      q => q.phase === 2 && q.raisedBy === agent && q.raisedRound === round
    );
    const otherQsAnsweredHere = allQuestions.filter(
      q => q.phase === 2 && q.answeredRound === round && q.answeredBy === agent
    );
    const myOpenedDsHere = allDis.filter(
      d => d.phase === 2 && d.openedRound === round
              && (d.progression || []).some(p => p.round === round && p.agent === agent)
    );
    const myClosedDsHere = allDis.filter(
      d => d.phase === 2 && d.closedRound === round
              && (d.progression || []).some(p => p.round === round && p.agent === agent)
    );

    const sentences = [];

    // Lead: status + agent identity.
    if (status === 'AGREED') {
      sentences.push(`${agentName} endorsed the plan this round.`);
    } else if (status === 'NEGOTIATING' || !status) {
      if (round === 1) {
        sentences.push(`${agentName}'s round-1 difference inventory.`);
      } else {
        sentences.push(`${agentName} still negotiating in round ${round}.`);
      }
    } else {
      sentences.push(`${agentName} · ${status.toLowerCase()}.`);
    }

    // Activity sentence: what moved this round.
    const movements = [];
    if (myNewQs.length > 0) movements.push(`raised ${plur(myNewQs.length, 'new question')}`);
    if (otherQsAnsweredHere.length > 0) movements.push(
      `answered ${plur(otherQsAnsweredHere.length, 'prior question')}`,
    );
    if (myOpenedDsHere.length > 0) movements.push(
      `surfaced ${plur(myOpenedDsHere.length, 'disagreement')}`,
    );
    if (myClosedDsHere.length > 0) movements.push(
      `resolved ${plur(myClosedDsHere.length, 'disagreement')}`,
    );
    if (movements.length > 0) {
      sentences.push(`${capitalise(movements.join(', '))}.`);
    }

    // Standing snapshot: open Qs + Ds left holding.
    const standingParts = [];
    if (typeof stats.openQuestions === 'number' && stats.openQuestions > 0) {
      standingParts.push(plur(stats.openQuestions, 'open question'));
    }
    if (typeof stats.blocking === 'number' && stats.blocking > 0) {
      standingParts.push(plur(stats.blocking, 'open disagreement'));
    }
    if (typeof stats.fsd === 'number' && stats.fsd > 0) {
      standingParts.push(`${stats.fsd} final-surfaced`);
    }
    if (standingParts.length > 0) {
      sentences.push(`Standing: ${standingParts.join(' · ')}.`);
    }

    return sentences.join(' ');
  }

  // Phase 4 — review turn. Same pattern but issue-oriented.
  if (phase === 4) {
    const sentences = [];
    if (status === 'APPROVED') {
      sentences.push(`${agentName} approved the draft this round.`);
    } else if (status === 'REVIEWING') {
      sentences.push(`${agentName} still reviewing in round ${round}.`);
    } else {
      sentences.push(agentName + (status ? ` · ${status.toLowerCase()}.` : '.'));
    }
    if (typeof stats.openIssues === 'number' && stats.openIssues > 0) {
      sentences.push(`${plur(stats.openIssues, 'issue')} open against the current draft.`);
    } else if (stats.openIssues === 0) {
      sentences.push('No open issues this round.');
    }
    return sentences.join(' ');
  }

  return '';
}

function capitalise(s) {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Small mono chips surfacing parsed protocol stats on a turn/plan row.
// Stays out of the way: nothing rendered when stats are absent.
// Spec 0034: ``prevStats`` enables round-over-round delta annotations
// (e.g. ``4 Q (-2)`` for "two questions answered since prior round").
function StatsChips({ stats, phase, prevStats }) {
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
        delta: prevStats?.openIssues != null
          ? stats.openIssues - prevStats.openIssues
          : null,
      });
    }
  } else {
    if (stats.openQuestions != null) {
      chips.push({
        value: stats.openQuestions,
        label: stats.openQuestions === 1 ? 'question' : 'questions',
        tint: stats.openQuestions > 0 ? 'info' : 'ok',
        delta: prevStats?.openQuestions != null
          ? stats.openQuestions - prevStats.openQuestions
          : null,
      });
    }
    if (stats.blocking != null && stats.blocking > 0) {
      chips.push({
        value: stats.blocking,
        label: stats.blocking === 1 ? 'disagreement' : 'disagreements',
        tint: 'warn',
        delta: prevStats?.blocking != null
          ? stats.blocking - prevStats.blocking
          : null,
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

function StatChip({ label, value, tint, delta }) {
  const colorMap = { ok: COLORS.ok, info: COLORS.info, warn: COLORS.warn, err: COLORS.err };
  const c = colorMap[tint] || 'var(--fg-3)';
  // Spec 0034: a small delta annotation when this chip has a prior-round
  // value to compare against. ``-N`` means resolved since last round (good);
  // ``+N`` means new this round (neutral). Zero delta is hidden.
  const deltaSuffix = (delta != null && delta !== 0)
    ? ` (${delta > 0 ? '+' : ''}${delta})`
    : '';
  const deltaColor = delta != null && delta < 0
    ? COLORS.ok
    : delta != null && delta > 0
      ? c
      : 'var(--fg-3)';
  return (
    <span className="mono"
          title={delta != null && delta !== 0
            ? `${delta > 0 ? '+' + delta + ' new this round' : (-delta) + ' resolved or answered since last round'}`
            : undefined}
          style={{
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
      {deltaSuffix && (
        <span className="num" style={{ color: deltaColor, fontWeight: 500 }}>
          {deltaSuffix}
        </span>
      )}
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
  if (item.kind === 'preflight') {
    // Spec 0033: per-agent Phase 0 critique card.
    const stats = item.stats || null;
    const statusVal = stats?.status;
    const briefIssues = stats?.briefIssues ?? 0;
    const ok = statusVal === 'BRIEF_OK';
    const sub = ok
      ? 'approved the brief'
      : briefIssues > 0
        ? `flagged ${briefIssues} issue${briefIssues === 1 ? '' : 's'}`
        : 'brief critique';
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
        <AgentIcon agent={item.agent} size={14} />
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, minWidth: 52 }}>
          {meta?.name || item.agent}
        </span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', minWidth: 110 }}>
          brief critique
        </span>
        <span style={{ flex: 1, minWidth: 0, fontSize: 11.5, color: 'var(--fg-2)',
                       overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {sub}
        </span>
        {stats && (
          <span className="mono" style={{
            fontSize: 10.5, color: ok ? COLORS.ok : COLORS.warn,
            padding: '1px 6px', borderRadius: 999,
            background: ok ? 'rgba(111,179,128,0.10)' : 'rgba(212,160,86,0.10)',
            border: `1px solid ${ok ? 'rgba(111,179,128,0.30)' : 'rgba(212,160,86,0.30)'}`,
          }}>
            {ok ? 'ok' : `${briefIssues} issue${briefIssues === 1 ? '' : 's'}`}
          </span>
        )}
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
        <StatsChips stats={item.stats} phase={item.statsPhase} prevStats={item.prevStats} />
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
// Spec 0025 owns title + accent + body shape per artifact kind.
// Spec 0027 layers the side-by-side review modal on top of phase 2 turn cards.
function ArtifactModal({ item, run, onClose }) {
  const meta = item.agent ? AGENT_META[item.agent] : null;
  const accent = meta?.color || COLORS.info;

  if (item.kind === 'input') {
    return <InputBriefModal item={item} run={run} onClose={onClose} accent={accent} />;
  }
  if (item.kind === 'preflight') {
    return <PreflightResponseModal item={item} run={run} onClose={onClose} accent={accent} />;
  }
  if ((item.kind === 'turn' || item.kind === 'turn-live')
      && (item.statsPhase === 2 || item.statsPhase === 4)) {
    return <NegotiateReviewModal item={item} run={run} meta={meta} onClose={onClose} accent={accent} />;
  }
  // Spec 0034: Phase 1 plan drafts open a side-by-side viewer (brief on
  // the left, draft on the right) instead of the one-pane DocumentModal.
  if (item.kind === 'plan' || item.kind === 'plan-live') {
    return <DraftReviewModal item={item} run={run} meta={meta} onClose={onClose} accent={accent} />;
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
  // Spec 0033: every output modal gains an Input tab. The bundle key
  // is plumbed through ``item.turnKey`` by ``buildLiveTimeline``.
  const tabs = [
    {
      id: 'content',
      label: 'Content',
      content: <LazyMarkdownBody filePath={item.filePath} />,
    },
    {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={item.turnKey} />,
    },
  ];
  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      accent={accent}
      tabs={tabs}
    />
  );
}

// ─────────────────── Phase 2 side-by-side review modal (spec 0027) ───────────
//
// Left pane: the "thing being questioned" — the OTHER agent's most recent
// turn for round N≥2, or their Phase 1 draft for round 1. Right pane: a
// stack of ReviewCards grouped by kind (questions / disagreements /
// resolved). Clicking a card scrolls the left pane to the anchored block
// and flashes it. For `> after:` items we render a dashed-ghost placeholder
// under the anchored heading.
function NegotiateReviewModal({ item, run, meta, onClose, accent }) {
  const otherAgent = item.agent === 'claude' ? 'gpt' : 'claude';
  const priorFilePath = priorContentPathFor(item, otherAgent, run);
  const items = reviewItemsFor(run, item);

  const leftRef = React.useRef(null);
  const [activeIdx, setActiveIdx] = React.useState(null);
  const [ghost, setGhost] = React.useState(null); // { headingEl, kind, body }

  // Dismiss any previously-rendered ghost block.
  const clearGhost = React.useCallback(() => {
    if (ghost?.node && ghost.node.parentNode) {
      ghost.node.parentNode.removeChild(ghost.node);
    }
    setGhost(null);
  }, [ghost]);

  // Imperatively mount a dashed-ghost placeholder after the given heading.
  const mountGhost = React.useCallback((headingEl, kind, body) => {
    clearGhost();
    if (!headingEl || !headingEl.parentNode) return;
    const node = document.createElement('div');
    node.className = 'dr-ghost-block';
    const kindLabel = document.createElement('div');
    kindLabel.className = 'dr-ghost-block-kind';
    kindLabel.textContent = kind === 'after' ? 'insert here' : 'note';
    node.appendChild(kindLabel);
    const bodyEl = document.createElement('div');
    bodyEl.textContent = body || '(no detail)';
    node.appendChild(bodyEl);
    headingEl.insertAdjacentElement('afterend', node);
    setGhost({ node, kind, body });
  }, [clearGhost]);

  const jumpToItem = React.useCallback((it) => {
    if (!leftRef.current) return;
    // Spec 0034: try the pre-resolved block_id first — fastest + most
    // reliable (no DOM-text scan, no whitespace tolerance issues, no
    // failure on paraphrased quotes that happen to substring-match
    // unrelated content).
    if (it.blockId) {
      const node = leftRef.current.querySelector(`#${it.blockId}`);
      if (node) {
        clearGhost();
        node.scrollIntoView({ block: 'start', behavior: 'smooth' });
        if (window.scrollAndFlash) {
          // Use scrollAndFlash's flash animation by passing the resolved
          // text — the helper will find the same node again but the visual
          // flash is what we're after.
          const tx = (node.textContent || '').trim().slice(0, 80);
          if (tx) window.scrollAndFlash(leftRef.current, { text: tx });
        }
        return;
      }
      // Pre-resolved ID didn't match a node — fall through to text scan.
    }
    if (it.after) {
      const heading = window.scrollAndFlash(leftRef.current, {
        afterHeading: it.after,
      });
      if (heading) mountGhost(heading, 'after', it.body);
      return;
    }
    if (it.quote) {
      clearGhost();
      window.scrollAndFlash(leftRef.current, { text: it.quote });
      return;
    }
    // No anchor — nothing to jump to.
    clearGhost();
  }, [clearGhost, mountGhost]);

  const handleSelect = React.useCallback((idx) => {
    setActiveIdx(idx);
    const it = items[idx];
    if (it) jumpToItem(it);
  }, [items, jumpToItem]);

  // Keyboard j / k walk while the modal is open.
  React.useEffect(() => {
    if (!items.length) return;
    const onKey = (e) => {
      // Don't capture when the user is typing into an input/textarea.
      const t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((cur) => {
          const next = cur == null ? 0 : Math.min(items.length - 1, cur + 1);
          jumpToItem(items[next]);
          return next;
        });
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((cur) => {
          const next = cur == null ? 0 : Math.max(0, cur - 1);
          jumpToItem(items[next]);
          return next;
        });
      } else if (e.key === 'Enter' && activeIdx != null) {
        e.preventDefault();
        jumpToItem(items[activeIdx]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [items, jumpToItem, activeIdx]);

  const turnLabel = typeof item.index === 'string' ? `turn ${item.index}` : `turn ${item.index || ''}`;
  const title = `${meta?.name || 'Agent'} — ${turnLabel}`;
  const subtitle = item.statsPhase === 4
    ? `round ${item.round} · reviewing the converged document`
    : `round ${item.round} · reviewing ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior content`;

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      accent={accent}
      width={1300}
    >
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.5fr) minmax(0, 1fr)',
        gap: 18,
        minHeight: 0,
        height: '100%',
      }}>
        {/* Left: prior content + Input sub-tab (spec 0033). */}
        <NegotiateLeftPane
          item={item}
          otherAgent={otherAgent}
          priorFilePath={priorFilePath}
          leftRef={leftRef}
        />

        {/* Right: review cards */}
        <div style={{
          minHeight: 0, minWidth: 0,
          display: 'flex', flexDirection: 'column',
          gap: 12,
          overflow: 'auto',
          paddingRight: 4,
        }}>
          <ReviewKeyboardHint hasItems={items.length > 0} />
          <ReviewGroup
            label="Open questions"
            color={COLORS.info}
            items={items}
            kinds={['question']}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            label="Disagreements"
            color={COLORS.warn}
            items={items}
            kinds={['disagreement']}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            label="Resolved / non-blocking"
            color={COLORS.ok}
            items={items}
            kinds={['resolved']}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          {items.length === 0 && (
            <div style={{
              padding: '20px 14px', textAlign: 'center',
              color: 'var(--fg-3)', fontSize: 12.5,
              border: '1px dashed var(--border-2)',
              borderRadius: 'var(--r-2)',
              background: 'var(--bg-2)',
            }}>
              No structured questions or disagreements were anchored in
              this turn. Open the document modal from the timeline card
              header to read the full markdown body.
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

// Spec 0033: left pane carries an Original|Input sub-tab strip. ``Original``
// is the prior agent's content (unchanged from spec 0027); ``Input`` is the
// per-turn input bundle for THIS agent's turn — exactly what they were
// handed before generating the right-pane critique.
function NegotiateLeftPane({ item, otherAgent, priorFilePath, leftRef }) {
  const [sub, setSub] = React.useState('original');

  return (
    <div style={{
      minHeight: 0, minWidth: 0,
      background: 'var(--bg-0)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid var(--border-1)',
        background: 'var(--bg-2)',
        display: 'flex', alignItems: 'center', gap: 10,
        flexShrink: 0,
      }}>
        <NegotiateLeftSubTabs active={sub} onChange={setSub} />
        <span style={{ flex: 1 }} />
        {sub === 'original' && (
          <>
            {item.statsPhase === 4 ? (
              <span className="mono" style={{
                fontSize: 10, color: 'var(--fg-2)',
                letterSpacing: '0.06em', textTransform: 'uppercase',
              }}>current draft</span>
            ) : (
              <AgentIcon agent={otherAgent} size={14} />
            )}
            <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
              {priorFilePath || '— no draft yet —'}
            </span>
          </>
        )}
        {sub === 'input' && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
            inputs/{item.turnKey || '—'}.json
          </span>
        )}
      </div>
      <div ref={leftRef} style={{
        flex: 1, minHeight: 0, overflow: 'auto',
        padding: '14px 16px',
      }}>
        {sub === 'original' ? (
          <LazyMarkdownBody filePath={priorFilePath} />
        ) : (
          <InputTabContent turnKey={item.turnKey} />
        )}
      </div>
    </div>
  );
}

function NegotiateLeftSubTabs({ active, onChange }) {
  const tabs = [
    { id: 'original', label: 'Original' },
    { id: 'input',    label: 'Input' },
  ];
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'stretch',
      borderRadius: 999, overflow: 'hidden',
      border: '1px solid var(--border-1)',
      background: 'var(--bg-1)',
      flexShrink: 0,
    }}>
      {tabs.map((t, i) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            style={{
              appearance: 'none',
              border: 'none',
              borderLeft: i === 0 ? 'none' : '1px solid var(--border-1)',
              background: isActive ? 'var(--bg-3)' : 'transparent',
              color: isActive ? 'var(--fg-0)' : 'var(--fg-2)',
              fontSize: 11,
              fontWeight: isActive ? 600 : 500,
              padding: '3px 10px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontFamily: 'inherit',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

// ─────────────────── Spec 0034 — Phase 1 side-by-side draft viewer ──────────
//
// Brief on the left (with the spec-0033 ``Original | Input`` sub-tabs so
// the user can also see the system prompt), draft on the right. The
// right pane is plain markdown — no critique list, no keyboard nav —
// since Phase 1 is an independent draft, not a critique. A small "🔗 brief"
// affordance appears next to each section heading on the right pane;
// clicking attempts a best-effort substring match into the brief and
// flashes the matching block if found.
function DraftReviewModal({ item, run, meta, onClose, accent }) {
  const briefPath = "brief.md";
  const leftRef = React.useRef(null);
  const [sub, setSub] = React.useState('original');

  const onSectionAnchorClick = React.useCallback((sectionText) => {
    if (!leftRef.current || !sectionText || sub !== 'original') return;
    if (window.scrollAndFlash) {
      window.scrollAndFlash(leftRef.current, { text: sectionText.slice(0, 60) });
    }
  }, [sub]);

  const title = `${meta?.name || 'Agent'} — Phase 1 draft`;
  const subtitle = 'side-by-side with the brief';

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      accent={accent}
      width={1300}
    >
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.3fr)',
        gap: 18,
        minHeight: 0,
        height: '100%',
      }}>
        {/* Left: brief (with Original | Input sub-tabs, spec 0033). */}
        <div style={{
          minHeight: 0, minWidth: 0,
          background: 'var(--bg-0)',
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--r-2)',
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{
            padding: '6px 12px',
            borderBottom: '1px solid var(--border-1)',
            background: 'var(--bg-2)',
            display: 'flex', alignItems: 'center', gap: 10,
            flexShrink: 0,
          }}>
            <NegotiateLeftSubTabs active={sub} onChange={setSub} />
            <span style={{ flex: 1 }} />
            <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
              {sub === 'original' ? briefPath : `inputs/${item.turnKey || '—'}.json`}
            </span>
          </div>
          <div ref={leftRef} style={{
            flex: 1, minHeight: 0, overflow: 'auto',
            padding: '14px 16px',
          }}>
            {sub === 'original'
              ? <LazyMarkdownBody filePath={briefPath} />
              : <InputTabContent turnKey={item.turnKey} />}
          </div>
        </div>

        {/* Right: the draft + per-section "🔗 brief" affordance. */}
        <DraftRightPane filePath={item.filePath} onSectionClick={onSectionAnchorClick} />
      </div>
    </Modal>
  );
}

function DraftRightPane({ filePath, onSectionClick }) {
  const { body, loading } = window.useFileBody(filePath);
  const containerRef = React.useRef(null);

  // Walk the rendered DOM after each render and inject a "🔗 brief"
  // button into every section heading. Best-effort — the markdown
  // renderer may take a tick to settle on first mount.
  React.useEffect(() => {
    if (!containerRef.current) return;
    const root = containerRef.current;
    const headings = root.querySelectorAll('h2, h3');
    headings.forEach((h) => {
      if (h.dataset.briefBtn === '1') return;
      const text = (h.textContent || '').trim();
      if (!text) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = '🔗 brief';
      btn.title = 'Find the closest matching block in the brief';
      btn.className = 'dr-section-brief-btn';
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (onSectionClick) onSectionClick(text);
      });
      h.appendChild(document.createTextNode(' '));
      h.appendChild(btn);
      h.dataset.briefBtn = '1';
    });
  });

  return (
    <div style={{
      minHeight: 0, minWidth: 0,
      background: 'var(--bg-0)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid var(--border-1)',
        background: 'var(--bg-2)',
        display: 'flex', alignItems: 'center', gap: 10,
        flexShrink: 0,
      }}>
        <span className="mono" style={{
          fontSize: 10, color: 'var(--fg-2)',
          letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>draft</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
          {filePath || '—'}
        </span>
      </div>
      <div ref={containerRef} style={{
        flex: 1, minHeight: 0, overflow: 'auto',
        padding: '14px 16px',
      }}>
        {loading
          ? <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading…</div>
          : <Markdown text={body || '— body unavailable —'} />}
      </div>
    </div>
  );
}

function ReviewKeyboardHint({ hasItems }) {
  if (!hasItems) return null;
  return (
    <div className="mono" style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 10px',
      background: 'var(--bg-0)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      color: 'var(--fg-3)',
      fontSize: 10.5,
    }}>
      <kbd style={{ padding: '1px 4px', background: 'var(--bg-2)', border: '1px solid var(--border-2)', borderRadius: 3 }}>j</kbd>
      <kbd style={{ padding: '1px 4px', background: 'var(--bg-2)', border: '1px solid var(--border-2)', borderRadius: 3 }}>k</kbd>
      <span>walk · </span>
      <kbd style={{ padding: '1px 4px', background: 'var(--bg-2)', border: '1px solid var(--border-2)', borderRadius: 3 }}>Esc</kbd>
      <span>close</span>
    </div>
  );
}

function ReviewGroup({ label, color, items, kinds, activeIdx, onSelect }) {
  // Render items in their original flat-list order, with indices for selection.
  const entries = items
    .map((it, i) => ({ it, i }))
    .filter(({ it }) => kinds.includes(it.kind));
  if (entries.length === 0) return null;
  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 10.5, color, fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        marginBottom: 6,
      }}>
        <span>{label}</span>
        <span style={{
          padding: '0 6px',
          background: color + '22', color,
          borderRadius: 999, fontSize: 10,
          fontFamily: 'var(--mono)', fontWeight: 600,
        }}>{entries.length}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {entries.map(({ it, i }) => (
          <ReviewCard
            key={i}
            item={it}
            color={color}
            active={activeIdx === i}
            onClick={() => onSelect(i)}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewCard({ item, color, active, onClick }) {
  const hasAnchor = !!(item.quote || item.after);
  const isMissing = !!item.after;
  return (
    <button
      onClick={onClick}
      style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '10px 12px',
        background: active ? 'var(--bg-2)' : 'var(--bg-1)',
        border: `1px solid ${active ? color : 'var(--border-1)'}`,
        borderLeft: `3px solid ${isMissing ? COLORS.warn : color}${isMissing ? '' : ''}`,
        borderLeftStyle: isMissing ? 'dashed' : 'solid',
        borderRadius: 'var(--r-2)',
        cursor: hasAnchor ? 'pointer' : 'default',
        transition: 'background 100ms, border-color 100ms',
      }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginBottom: 4,
      }}>
        {item.itemId && (
          <span className="mono" style={{
            fontSize: 10, color, fontWeight: 600,
            padding: '1px 6px',
            background: color + '14',
            border: `1px solid ${color}44`,
            borderRadius: 4,
            letterSpacing: '0.04em',
          }}>{item.itemId}</span>
        )}
        {!hasAnchor && (
          <span className="mono" style={{
            fontSize: 9.5, color: 'var(--fg-3)',
            letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>no anchor</span>
        )}
        {isMissing && (
          <span className="mono" style={{
            fontSize: 9.5, color: COLORS.warn,
            letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>missing</span>
        )}
        <span style={{ flex: 1 }} />
        {hasAnchor && (
          <span style={{ color: 'var(--fg-3)' }}>
            <Icon.Arrow style={{ width: 12, height: 12 }} />
          </span>
        )}
      </div>
      {item.quote && (
        <div style={{
          fontSize: 11, color: 'var(--fg-2)',
          fontStyle: 'italic',
          marginBottom: 4,
          paddingLeft: 8,
          borderLeft: `2px solid ${color}55`,
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}>“{item.quote}”</div>
      )}
      {item.after && (
        <div className="mono" style={{
          fontSize: 10.5, color: COLORS.warn,
          marginBottom: 4,
        }}>after: {item.after}</div>
      )}
      <div style={{
        fontSize: 12.5, color: 'var(--fg-1)',
        lineHeight: 1.5,
        display: '-webkit-box',
        WebkitLineClamp: 3,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {item.body}
      </div>
    </button>
  );
}

// Resolve which file the left pane should render for a side-by-side modal.
//
// Phase 2:
//   - Round 1: the OTHER agent's Phase 1 draft.
//   - Round N≥2: the OTHER agent's round N-1 turn file.
// Phase 4:
//   - The latest converged-document version available, surfaced by the
//     aggregator on `run.currentDraftPath`. Falls back to `phase3/draft-v1.md`
//     server-side; null when neither file exists yet.
function priorContentPathFor(item, otherUiAgent, run) {
  const phase = item.statsPhase || 2;
  if (phase === 4) {
    return run?.currentDraftPath || null;
  }
  const beAgent = otherUiAgent === 'gpt' ? 'openai' : otherUiAgent;
  const round = Number(item.round) || 1;
  if (round <= 1) return `phase1/draft-${beAgent}.md`;
  const rr = String(round - 1).padStart(2, '0');
  return `phase2/round-${rr}-${beAgent}.md`;
}

function reviewItemsFor(run, item) {
  const phase = item.statsPhase || 2;
  const key = `phase${phase}_round${item.round}_${item.agent}`;
  const bucket = (run.phaseReviewItems || {})[key];
  return Array.isArray(bucket) ? bucket : [];
}

// ─────────────────── Spec 0033 — Input tab + bundle rendering ───────────────
//
// Friendly labels per Tk-vocab key. Stays in sync with KIND_COLORS.label
// from the Consumption tab.
const INPUT_PIECE_LABEL = {
  system: 'System prompt',
  brief:  'Brief',
  d1:     "Claude's Phase 1 draft",
  d2:     "GPT's Phase 1 draft",
  plan:   'Agreed plan',
  hist:   'Prior Phase 2 turns',
  draft:  'Current draft',
  histp:  'Prior Phase 4 review turns',
};

// Canonical render order — mirrors ``protocol/prompts.py::INPUT_BUNDLE_KEY_ORDER``.
const INPUT_PIECE_ORDER = ['system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'];

// Pieces collapsed by default. The `system` template is long boilerplate
// the user can drill into if they care; the substantive content (brief,
// drafts, history) is open by default so the audit content is immediately
// visible.
const INPUT_PIECE_DEFAULT_COLLAPSED = new Set(['system']);

function InputTabContent({ turnKey }) {
  const { bundle, loading, error } = window.useInputBundle(turnKey);

  if (!turnKey) {
    return <InputEmptyState label="No input record for this artifact." />;
  }
  if (loading) {
    return <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading input bundle…</div>;
  }
  if (error || !bundle) {
    return (
      <InputEmptyState label={
        error
          ? `Could not load input bundle (${error}).`
          : 'Input bundle not recorded — this run pre-dates spec 0033, or the bundle was lost.'
      } />
    );
  }
  const pieces = bundle.pieces || {};
  // Render the canonical order; any unknown keys append at the end.
  const renderKeys = INPUT_PIECE_ORDER.filter(k => k in pieces)
    .concat(Object.keys(pieces).filter(k => !INPUT_PIECE_ORDER.includes(k)));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {renderKeys.map(key => (
        <InputSection
          key={key}
          piece={key}
          text={pieces[key] || ''}
          defaultCollapsed={INPUT_PIECE_DEFAULT_COLLAPSED.has(key)}
        />
      ))}
    </div>
  );
}

function InputSection({ piece, text, defaultCollapsed }) {
  const [open, setOpen] = React.useState(!defaultCollapsed);
  const label = INPUT_PIECE_LABEL[piece] || piece;
  const isEmpty = !text;
  const chars = text ? text.length : 0;
  const approxTokens = text ? Math.max(1, Math.round(text.length / 3.5)) : 0;

  return (
    <div style={{
      border: '1px solid var(--border-1)',
      borderRadius: 6,
      background: 'var(--bg-1)',
    }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          width: '100%',
          padding: '7px 10px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'inherit',
          color: 'var(--fg-0)',
          fontSize: 12,
          textAlign: 'left',
        }}
      >
        <span style={{
          display: 'inline-block', width: 10, textAlign: 'center',
          color: 'var(--fg-3)', fontFamily: 'var(--mono)',
        }}>{open ? '▾' : '▸'}</span>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
          ({piece})
        </span>
        <span style={{ flex: 1 }} />
        {isEmpty ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
            (not used in this turn)
          </span>
        ) : (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
            {chars.toLocaleString()} chars · ~{approxTokens.toLocaleString()}t
          </span>
        )}
      </button>
      {open && !isEmpty && (
        <div style={{
          borderTop: '1px solid var(--border-1)',
          padding: '10px 12px',
          maxHeight: 360,
          overflow: 'auto',
          background: 'var(--bg-0)',
        }}>
          <pre style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'var(--mono)',
            fontSize: 11.5,
            lineHeight: 1.5,
            color: 'var(--fg-1)',
          }}>{text}</pre>
        </div>
      )}
    </div>
  );
}

function InputEmptyState({ label }) {
  return (
    <div style={{
      padding: '32px 16px',
      textAlign: 'center',
      color: 'var(--fg-3)',
      fontSize: 12.5,
      border: '1px dashed var(--border-2)',
      borderRadius: 'var(--r-2)',
      background: 'var(--bg-2)',
    }}>
      {label}
    </div>
  );
}

// ─────────────────── Spec 0033 — preflight modals ───────────────────────────
//
// Two modal variants for Phase 0:
// - InputBriefModal — opens from the shared `input` card. Default tab is
//   Input (the user's audit intent here is primary); the brief markdown is
//   one click away under Content.
// - PreflightResponseModal — opens from the per-agent `preflight` cards.
//   Default tab is Content (the user clicked through to read the response);
//   Input is available as a sibling tab and shows the SAME shared bundle as
//   the Phase 0 brief modal — deliberately repeated, because every output
//   modal in spec 0033 also shows that output's input.

function InputBriefModal({ item, run, onClose, accent }) {
  const { attachments, loading } = window.useAttachments(run.id);

  // Split attachments into Sources (links) vs Files (image/pdf/file).
  const fileKinds = new Set(['image', 'pdf', 'file']);
  const sources = (attachments || []).filter((a) => a.kind === 'link');
  const files = (attachments || []).filter((a) => fileKinds.has(a.kind));

  const tabs = [
    {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={item.turnKey || 'input'} />,
    },
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

function PreflightResponseModal({ item, run, onClose, accent }) {
  const meta = AGENT_META[item.agent];
  const tabs = [
    {
      id: 'content',
      label: 'Content',
      content: <LazyMarkdownBody filePath={item.filePath} />,
    },
    {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={item.turnKey || `phase0_${item.agent}`} />,
    },
  ];
  return (
    <Modal
      open={true}
      onClose={onClose}
      title={`${meta?.name || 'Agent'} — brief critique`}
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

// ─────────────────── Critique explorer (right panel, spec 0034) ────────────
//
// Renames the former "Disagreement explorer" and renders BOTH first-class
// questions and disagreements, typed. Three filters:
//   - phase tab:  Phase 2 (Negotiate) | Phase 4 (Review)
//   - type:       All | Questions | Disagreements
//   - status:     All | Open | Resolved/answered
//
// Clicking any card calls ``onHighlightTurns(keys, variant)`` which makes
// the corresponding turn-cards in the timeline flash for 2s.
function CritiqueExplorer({ run, onHighlightTurns }) {
  const questions = Array.isArray(run.questions) ? run.questions : [];
  const disagreements = Array.isArray(run.disagreements) ? run.disagreements : [];

  // Phase pick: prefer the currently-running phase; else any phase that has
  // either kind of item; else default to Phase 2.
  const haveAny = (pid) =>
    questions.some(q => q.phase === pid) || disagreements.some(d => d.phase === pid);
  const initial = (run.phase === 4 || run.phase === 2) ? run.phase
                 : haveAny(4) ? 4
                 : haveAny(2) ? 2
                 : 2;
  const [selectedPhase, setSelectedPhase] = React.useState(initial);
  const [typeFilter, setTypeFilter] = React.useState('all'); // 'all' | 'questions' | 'disagreements'
  React.useEffect(() => { setSelectedPhase(initial); setTypeFilter('all'); }, [run.id, initial]);

  // Phase-filtered slices.
  const phaseQuestions = questions.filter(q => q.phase === selectedPhase);
  const phaseDisagreements = disagreements.filter(d => d.phase === selectedPhase);

  // Type filter.
  const showQ = typeFilter === 'all' || typeFilter === 'questions';
  const showD = typeFilter === 'all' || typeFilter === 'disagreements';

  // Group by status.
  const openItems = [];
  const resolvedItems = [];
  if (showD) {
    for (const d of phaseDisagreements) {
      const item = { ...d, _critiqueKind: 'd' };
      (d.status === 'open' ? openItems : resolvedItems).push(item);
    }
  }
  if (showQ) {
    for (const q of phaseQuestions) {
      const item = { ...q, _critiqueKind: 'q' };
      (q.status === 'open' ? openItems : resolvedItems).push(item);
    }
  }

  // Sort: by round ascending so the user reads chronological history.
  const byRound = (a, b) => {
    const aR = a._critiqueKind === 'q' ? a.raisedRound : a.openedRound;
    const bR = b._critiqueKind === 'q' ? b.raisedRound : b.openedRound;
    return (aR || 0) - (bR || 0);
  };
  openItems.sort(byRound);
  resolvedItems.sort(byRound);

  const introduced = (showQ ? phaseQuestions.length : 0) + (showD ? phaseDisagreements.length : 0);
  const totalOpen = openItems.length;
  const totalResolved = resolvedItems.length;

  // Phase-tab info: shows Q + D counts per phase.
  const phaseInfo = (pid) => {
    const qInPhase = questions.filter(q => q.phase === pid);
    const dInPhase = disagreements.filter(d => d.phase === pid);
    const pending = run.phase < pid || (pid === 4 && run.phase < 3);
    return {
      pid,
      label: pid === 2 ? 'Negotiate' : 'Review',
      qTotal: qInPhase.length,
      dTotal: dInPhase.length,
      qOpen: qInPhase.filter(q => q.status === 'open').length,
      dOpen: dInPhase.filter(d => d.status === 'open').length,
      pending,
      active: (run.phase === pid && run.status === 'running'),
    };
  };
  const tabs = [phaseInfo(2), phaseInfo(4)];

  const totalIntroduced = questions.length + disagreements.length;

  const handleHighlight = React.useCallback((keys, variant) => {
    if (onHighlightTurns) onHighlightTurns(keys, variant);
  }, [onHighlightTurns]);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
      <PaneHeader
        title="Critique"
        count={`${totalIntroduced} introduced`}
        accentColor={COLORS.info}
        right={
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <SmallStat label="open"     value={totalOpen} color={totalOpen > 0 ? COLORS.warn : 'var(--fg-3)'} />
            <SmallStat label="resolved" value={totalResolved} color={totalResolved > 0 ? COLORS.ok : 'var(--fg-3)'} />
          </span>
        }
      />
      <PaneToolbar>
        {tabs.map((t) => (
          <CritiquePhaseTab
            key={t.pid}
            tab={t}
            active={selectedPhase === t.pid}
            onSelect={() => setSelectedPhase(t.pid)}
          />
        ))}
        <span style={{ flex: 1 }} />
        <CritiqueTypeFilter active={typeFilter} onChange={setTypeFilter} />
      </PaneToolbar>
      <CritiquePhaseContent
        run={run}
        phaseId={selectedPhase}
        openItems={openItems}
        resolvedItems={resolvedItems}
        introduced={introduced}
        onHighlight={handleHighlight}
      />
    </section>
  );
}

// Keep the old export name as an alias for backwards-compat in case any
// other module references it (no external links to break, but defensive).
const DisagreementExplorer = CritiqueExplorer;

function CritiqueTypeFilter({ active, onChange }) {
  const items = [
    { id: 'all',           label: 'All' },
    { id: 'questions',     label: 'Questions' },
    { id: 'disagreements', label: 'Disagreements' },
  ];
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'stretch',
      borderRadius: 999, overflow: 'hidden',
      border: '1px solid var(--border-1)',
      background: 'var(--bg-2)',
      flexShrink: 0,
    }}>
      {items.map((t, i) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            style={{
              appearance: 'none',
              border: 'none',
              borderLeft: i === 0 ? 'none' : '1px solid var(--border-1)',
              background: isActive ? 'var(--bg-3)' : 'transparent',
              color: isActive ? 'var(--fg-0)' : 'var(--fg-2)',
              fontSize: 11,
              fontWeight: isActive ? 600 : 500,
              padding: '3px 10px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontFamily: 'inherit',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

function CritiquePhaseTab({ tab, active, onSelect }) {
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
          : (tab.qTotal + tab.dTotal === 0) ? 'no items'
          : <>
              <span style={{ color: tab.qTotal > 0 ? COLORS.info : 'var(--fg-3)' }}>{tab.qTotal} Q</span>
              <span style={{ color: 'var(--fg-4)' }}> · </span>
              <span style={{ color: tab.dTotal > 0 ? COLORS.warn : 'var(--fg-3)' }}>{tab.dTotal} D</span>
            </>
        }
      </span>
    </button>
  );
}

function CritiquePhaseContent({ run, phaseId, openItems, resolvedItems, introduced, onHighlight }) {
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
          <div className="mono" style={{ fontSize: 12 }}>no questions or disagreements in this phase</div>
          {suspectedMiss && (
            <div className="mono" style={{ fontSize: 11, marginTop: 10, color: COLORS.warn, opacity: 0.85 }}>
              ⚠ couldn't reconstruct disagreements from this run — open the round files directly
            </div>
          )}
        </div>
      </div>
    );
  }

  const renderItem = (item) => item._critiqueKind === 'q'
    ? <QuestionCard key={item.id} q={item} onHighlight={onHighlight} />
    : <DisagreementCard key={item.id} d={item} onHighlight={onHighlight} />;

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--bg-0)' }}>
      <div style={{ padding: '6px 24px 28px' }}>
        {openItems.length > 0 && <GroupHeader label="Open" color={COLORS.warn} count={openItems.length} />}
        {openItems.map(renderItem)}
        {resolvedItems.length > 0 && (
          <GroupHeader label="Resolved / answered" color={COLORS.ok} count={resolvedItems.length}
                       style={{ marginTop: openItems.length ? 20 : 0 }} />
        )}
        {resolvedItems.map(renderItem)}
      </div>
    </div>
  );
}

// Spec 0034: Question card in the explorer.
function QuestionCard({ q, onHighlight }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const isAnswered = q.status === 'answered';
  const accentColor = COLORS.info;
  const raisedMeta = AGENT_META[q.raisedBy];
  const answerMeta = q.answeredBy ? AGENT_META[q.answeredBy] : null;

  const onCardClick = React.useCallback(() => {
    if (onHighlight) {
      const keys = [q.raisedTurnKey];
      if (q.answeredTurnKey) keys.push(q.answeredTurnKey);
      onHighlight(keys, 'q');
    }
    setOpen(o => !o);
  }, [q, onHighlight]);

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
      <button onClick={onCardClick} style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '12px 14px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
          <span className="mono" style={{
            fontSize: 10, color: COLORS.info, letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'rgba(107,156,240,0.10)',
            border: '1px solid rgba(107,156,240,0.30)',
            flexShrink: 0,
          }}>Q</span>
          <span style={{ flex: 1, fontSize: 13, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.35 }}>
            {q.body || '(no body)'}
          </span>
          <span className="mono" style={{
            fontSize: 10.5,
            padding: '1px 6px', borderRadius: 999,
            border: `1px solid ${isAnswered ? COLORS.ok + '55' : COLORS.warn + '55'}`,
            color: isAnswered ? COLORS.ok : COLORS.warn,
            background: isAnswered ? 'rgba(111,179,128,0.08)' : 'rgba(212,160,86,0.08)',
            flexShrink: 0,
          }}>
            {isAnswered ? 'answered' : 'open'}
          </span>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          fontSize: 11, color: 'var(--fg-3)',
        }}>
          <span className="mono">{q.id}</span>
          <span>·</span>
          <span>raised by {raisedMeta?.name || q.raisedBy} R{q.raisedRound}</span>
          {isAnswered && (
            <>
              <span>·</span>
              <span>answered by {answerMeta?.name || q.answeredBy} R{q.answeredRound}</span>
              {q.match === 'positional' && (
                <span className="mono" style={{ color: COLORS.warn, opacity: 0.8 }}>
                  · positional match
                </span>
              )}
            </>
          )}
        </div>
      </button>
      {open && (q.quote || q.after || q.answerBody) && (
        <div style={{
          padding: '10px 14px 14px',
          borderTop: '1px solid var(--border-1)',
          background: 'var(--bg-0)',
          fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.5,
        }}>
          {q.quote && (
            <div style={{ marginBottom: 6 }}>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>quote:</span>
              <span style={{ fontStyle: 'italic' }}>"{q.quote}"</span>
            </div>
          )}
          {q.after && (
            <div style={{ marginBottom: 6 }}>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>after:</span>
              <span style={{ fontStyle: 'italic' }}>{q.after}</span>
            </div>
          )}
          {isAnswered && q.answerBody && (
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed var(--border-1)' }}>
              <span className="mono" style={{ color: COLORS.ok, fontSize: 10.5, marginRight: 6 }}>answer:</span>
              {q.answerBody}
            </div>
          )}
        </div>
      )}
    </article>
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

function DisagreementCard({ d, onHighlight }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);

  // Spec 0034: click highlights the raised/closed turn-cards in the
  // timeline so the user can follow the disagreement's history visually.
  const onCardClick = React.useCallback(() => {
    if (onHighlight) {
      const keys = [];
      if (d.raisedTurnKey) keys.push(d.raisedTurnKey);
      if (d.closedTurnKey) keys.push(d.closedTurnKey);
      if (keys.length > 0) onHighlight(keys, 'd');
    }
    setOpen(o => !o);
  }, [d, onHighlight]);

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
      <button onClick={onCardClick} style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '12px 14px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        {/* Top row: label + status */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
          <span className="mono" style={{
            fontSize: 10, color: COLORS.warn, letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'rgba(212,160,86,0.10)',
            border: '1px solid rgba(212,160,86,0.30)',
            flexShrink: 0,
          }}>D</span>
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
  // Spec 0033: Conversation/Consumption tab state lifted from Timeline so
  // the header can render the pill control.
  const [timelineTab, setTimelineTab] = React.useState('conversation');
  // Spec 0034: cross-axis highlight. The CritiqueExplorer dispatches a
  // set of turn-keys here; Timeline forwards them to each ArtifactCard,
  // which applies a 1.5s flash ring. The Map carries the variant
  // (``'q'`` or ``'d'``) so the ring colour matches the source type.
  const [highlightedTurnKeys, setHighlightedTurnKeys] = React.useState(
    () => new Map()
  );
  React.useEffect(() => { setShowErrors(false); }, [run.id, run.phase, run.status]);
  React.useEffect(() => { setTimelineTab('conversation'); }, [run.id]);

  const highlightTurns = React.useCallback((keys, variant) => {
    const next = new Map();
    for (const k of (keys || [])) {
      if (k) next.set(k, variant);
    }
    setHighlightedTurnKeys(next);
    // Auto-clear after 2s so subsequent unrelated clicks don't pile.
    setTimeout(() => {
      setHighlightedTurnKeys(new Map());
    }, 2000);
  }, []);

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
        tab={timelineTab}
        onTabChange={setTimelineTab}
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
            <Timeline
              run={run}
              tab={timelineTab}
              highlightedTurnKeys={highlightedTurnKeys}
            />
            <CritiqueExplorer run={run} onHighlightTurns={highlightTurns} />
          </>
        )}
      </main>
      <Footer run={run} />
    </div>
  );
}

Object.assign(window, { RunDetail });
