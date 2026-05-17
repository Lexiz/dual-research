// run-detail.jsx — v4: card-based timeline + phase-tabbed disagreement explorer
//
//   ┌─ top bar
//   ├─ phase strip
//   ├─ left: artifact cards (collapsible)   │  right: disagreements by phase (tabbed)
//   └─ footer

// ─────────────────── Spec 0038 — search index context ──────────────────────
//
// Run-scoped fetch of /api/runs/<id>/searches/index?include=summary. One
// network call per run-detail mount; consumers (SearchChip on each
// collapsed card, SearchGistLine on each expanded card, RunSearchSummary
// in the run header) all read from the same Map. Value shape:
//   { keys: Set<string>|null, summary: Map<turnKey,{queries,consulted,hasWarning}>|null }
// Both null while loading; after the fetch resolves they are non-null
// even when the run has no audit data (empty Set + empty Map).
const SearchIndexContext = React.createContext({ keys: null, summary: null });

// URL normaliser mirroring ``dual_research.audit.validate.normalize_url``
// for client-side membership comparison (used to mark a ConsultedSourceCard
// as ``[cited]``). Keep narrow on purpose — over-normalisation would let
// genuinely distinct URLs collapse into one. Aligned with the four rules
// the validator applies server-side.
const _SEARCH_TRACKING_PARAMS = new Set([
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
]);
function normalizeSearchUrl(url) {
  if (!url) return '';
  let u;
  try { u = new URL(url); } catch { return String(url).replace(/\/+$/, '').toLowerCase(); }
  const scheme = (u.protocol || '').replace(':', '').toLowerCase();
  const host = (u.hostname || '').toLowerCase();
  const port = u.port ? `:${u.port}` : '';
  let path = u.pathname || '';
  if (path.length > 1 && path.endsWith('/')) path = path.replace(/\/+$/, '');
  const kept = [];
  u.searchParams.forEach((v, k) => {
    if (!_SEARCH_TRACKING_PARAMS.has(k.toLowerCase())) {
      kept.push(`${k}=${v}`);
    }
  });
  let out = `${scheme}://${host}${port}${path}`;
  if (kept.length) out += `?${kept.join('&')}`;
  return out;
}

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

// ─────────────────── Compact run-detail header (spec 0024 pass 3) ────────────
// Spec 0035 reverts the spec-0033 four-row layout back to two rows:
//   row 1: topic · cost · status/errors
//   row 2: phase dots + dot labels + run metadata (started · drafter · elapsed · round)
// The per-agent activity strips moved into the Timeline pane (where they
// replace the deleted `AgentLegendChip`s) and the Conversation/Consumption
// tabs moved back into the Timeline `PaneToolbar`. The header is chrome
// only — global run identity + state — not per-agent or per-pane.
function RunDetailHeader({ run, errorCount, showErrors, onToggleErrors, onJumpToFirstSearch }) {
  const total = run.agents.claude.cost + run.agents.gpt.cost;
  // Spec 0039: ``cost`` is now the full invoice (tokens + web search).
  // ``searchCost`` carries the breakdown so the CostBadge tooltip can
  // show "of which web search" without losing the total.
  const totalSearchCost = (run.agents.claude.searchCost || 0) + (run.agents.gpt.searchCost || 0);
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
        <CostBadge cost={total} tokens={totalTokens} searchCost={totalSearchCost} />
        <RunSearchSummary onJump={onJumpToFirstSearch} />
        <StatusErrorsBadge
          status={run.status}
          errorCount={errorCount}
          showErrors={showErrors}
          onToggleErrors={onToggleErrors}
        />
      </div>
      {/* Row 2: phase dots + dot labels on the left; run metadata on the right. */}
      <PhaseDotsRow
        run={run}
        startedClock={startedClock}
        elapsedLabel={elapsedLabel}
        drafterLabel={drafterLabel}
      />
    </header>
  );
}

// ─────────────────── Spec 0035 — per-agent pill (Timeline toolbar) ──────────
//
// Single-line inline-flex pill carrying the same payload as spec 0033's
// full-row `AgentStrip` (icon · name · model · tokens·cost · ● phrase).
// Replaces the deleted `AgentLegendChip` (which lived in the toolbar but
// missed the live-activity sentence). Pill border picks up the agent's
// color — that's the "rail" cue; no separate left-border-rail like the
// header variant had.
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
    <span
      title={`${meta.name} · ${modelId} · ${totalTokens.toLocaleString()} tokens · ${cost.toFixed(4)} USD`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '3px 10px',
        background: 'var(--bg-2)',
        border: `1px solid ${meta.border}`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
        minWidth: 0,
        flexShrink: 1,
      }}>
      <AgentIcon agent={agent} size={14} />
      <span style={{ fontSize: 11.5, color: 'var(--fg-1)', fontWeight: 500 }}>
        {meta.name}
      </span>
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-3)',
        maxWidth: 160,
        overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {modelId}
      </span>
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-2)',
      }}>
        {fmt.tokens(totalTokens)}t · {fmt.cost(cost)}
      </span>
      <span style={{ color: 'var(--border-2)', fontSize: 11 }}>│</span>
      <Dot color={dotColor} pulse={live ? 'pulse-a' : null} size={6} />
      <span style={{
        fontSize: 11, color: phraseColor,
        maxWidth: 180,
        overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {phrase}
      </span>
    </span>
  );
}

// ─────────────────── Spec 0038 — RunSearchSummary header chip ───────────────
//
// Reads the SearchIndexContext (populated once per run by `useSearchIndex`)
// and renders a single chip in the run header:
//   🔎 N · M URLs · ⚠ K unmatched
// The warning segment renders only when at least one turn has a flagged
// citation. Click jumps to the first flagged card (or the first card
// with searches if no warnings). Hidden when the run has no audit data
// — pre-0036 transcripts + runs where web search was disabled both
// gracefully render nothing.
function RunSearchSummary({ onJump }) {
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  if (!summary || summary.size === 0) return null;
  let totalQueries = 0;
  let totalUrls = 0;
  let warnings = 0;
  for (const v of summary.values()) {
    totalQueries += v.queries || 0;
    totalUrls += v.consulted || 0;
    if (v.hasWarning) warnings += 1;
  }
  if (totalQueries === 0) return null;
  const handle = (e) => {
    e.stopPropagation();
    if (onJump) onJump({ warningOnly: warnings > 0 });
  };
  return (
    <button
      type="button"
      onClick={handle}
      title={warnings > 0
        ? `${totalQueries} web searches · ${totalUrls} URLs retrieved · ${warnings} turn${warnings === 1 ? '' : 's'} flagged for unmatched citations — click to jump`
        : `${totalQueries} web searches · ${totalUrls} URLs retrieved across the run — click to jump to the first searched turn`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 10px',
        background: 'var(--bg-2)',
        border: `1px solid ${warnings > 0 ? COLORS.warn + '55' : 'var(--border-1)'}`,
        borderRadius: 999,
        fontFamily: 'inherit', cursor: 'pointer',
        fontSize: 11, color: 'var(--fg-1)',
        whiteSpace: 'nowrap', flexShrink: 0,
      }}>
      <span>🔎</span>
      <span className="mono">{totalQueries}</span>
      <span style={{ color: 'var(--fg-3)' }}>·</span>
      <span className="mono">{totalUrls} URLs</span>
      {warnings > 0 && (
        <>
          <span style={{ color: 'var(--fg-3)' }}>·</span>
          <span className="mono" style={{ color: COLORS.warn }}>
            ⚠ {warnings} unmatched
          </span>
        </>
      )}
    </button>
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

function CostBadge({ cost, tokens, searchCost }) {
  // Spec 0039: ``cost`` is now the full invoice (tokens + web search).
  // When ``searchCost`` is non-zero, tooltip surfaces the breakdown so
  // the user can see how much of the headline was tool spend.
  const sc = Number(searchCost) || 0;
  const tokenCost = Math.max(0, cost - sc);
  let tip = `${cost.toFixed(4)} USD · ${tokens.toLocaleString()} tokens`;
  if (sc > 0) {
    tip = (
      `${cost.toFixed(4)} USD (tokens ${tokenCost.toFixed(4)} · `
      + `web search ${sc.toFixed(4)}) · ${tokens.toLocaleString()} tokens`
    );
  }
  return (
    <span title={tip}
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
// `Consumption` (per-turn context-window bars).
//
// Spec 0035 layout:
//   PaneHeader (row 1): "Timeline · N artifacts" .................. [Claude pill]
//   PaneToolbar (row 2): [GPT pill] [live-count chip] ............. [Conversation | Consumption]
// Tab state is owned by Timeline (re-internalised — spec 0033 had lifted
// it to RunDetail so the header could render the pill; spec 0035 moved
// the tabs back here and unwound the lift).
function Timeline({ run, highlightedTurnKeys }) {
  const items = React.useMemo(() => buildTimeline(run), [run]);
  const [openId, setOpenId] = React.useState(null);
  const [tab, setTab] = React.useState('conversation'); // 'conversation' | 'consumption'

  // Reset open modal + active tab when navigating between runs.
  React.useEffect(() => {
    setOpenId(null);
    setTab('conversation');
  }, [run.id]);

  const openItem = items.find((i) => i.id === openId) || null;

  const artifactCount = items.filter(i => i.kind !== 'phase-divider' && i.kind !== 'error' && i.kind !== 'deadlock').length;
  const liveCount = items.filter(i => i.live).length;

  return (
    <section style={{
      display: 'flex', flexDirection: 'column',
      borderRight: '1px solid var(--border-1)',
      minWidth: 0, minHeight: 0,
    }}>
      {/* Row 1 — PaneHeader: title on the left, Claude pill on the right. */}
      <PaneHeader
        title="Timeline"
        count={`${artifactCount} artifacts`}
        accentGradient="linear-gradient(to right, var(--agent-a) 0%, var(--agent-a) 48%, var(--agent-b) 52%, var(--agent-b) 100%)"
        right={<AgentStrip agent="claude" run={run} />}
      />
      {/* Row 2 — PaneToolbar: Conversation/Consumption tabs on the LEFT,
          directly under the "Timeline" title in the row above (spec 0040 D6 —
          previously the tabs were stranded on the right, next to the GPT
          pill they had no semantic relationship to). The live-count chip
          sits to the right of the tabs; GPT pill stays on the right edge,
          vertically aligned with the Claude pill on the PaneHeader row. */}
      <PaneToolbar>
        <TimelineTabs active={tab} onChange={setTab} prominent />
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
        <span style={{ flex: 1 }} />
        <AgentStrip agent="gpt" run={run} />
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

// `AgentLegendChip` (spec 0029) was deleted in spec 0035 — the same
// payload (icon · name · tokens · cost), plus the live-activity
// sentence, now lives on the per-agent `AgentStrip` pill rendered
// directly in the Timeline pane header / toolbar.

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

// Spec 0035 — distinct palette for the expanded-card sub-input bars.
// Stays explicitly out of the agent-color space (Claude amber / GPT
// green) so the TOTAL bar in agent color reads as the aggregate and
// the sub-bars in these neutrals read as the components. The
// collapsed-row segmented bar still uses ``KIND_COLORS`` above — that
// compact view continues to mirror the how-it-works Tk palette.
const SUBINPUT_COLORS = {
  brief: '#5a7fc7',  // indigo
  d1:    '#a98a5a',  // ochre (NOT Claude orange)
  d2:    '#6f8c7a',  // sage (NOT GPT green)
  plan:  '#7a6b9a',  // plum
  hist:  '#c08570',  // rose
  draft: '#5d8a8a',  // teal
  histp: '#a18560',  // slate-amber
};

// Spec 0035 — compute a shared denominator for every bar in the
// Consumption tab. Default behaviour: data-relative scale with 15%
// headroom so the largest row fills ~85% of the bar (still leaves room
// for the context-window tick marker if the cap sits beyond the data).
// Returns ``{ denom, window, dataRelative }``.
function computeConsumptionScale(rows, run) {
  let maxConsumption = 0;
  let maxWindow = 0;
  for (const row of rows || []) {
    for (const ag of ['claude', 'gpt']) {
      const u = row[ag];
      if (!u) continue;
      const tokensIn = Number(u.in) || 0;
      if (tokensIn > maxConsumption) maxConsumption = tokensIn;
      const w = contextWindowFor(u, run, ag);
      if (w > maxWindow) maxWindow = w;
    }
  }
  if (maxConsumption <= 0) {
    // No data yet — fall back to the full context window (or the default).
    const w = maxWindow > 0 ? maxWindow : DEFAULT_CONTEXT_WINDOW;
    return { denom: w, window: w, dataRelative: false };
  }
  const headroom = Math.max(maxConsumption + 1, Math.round(maxConsumption * 1.15));
  // If the actual consumption is already > the recorded window (impossible
  // but defensive), grow the scale to fit.
  const denom = Math.max(headroom, maxConsumption);
  return { denom, window: maxWindow || DEFAULT_CONTEXT_WINDOW, dataRelative: true };
}

// Tiny pretty-printer for a context-window cap (e.g. ``1M`` / ``400K`` / ``128K``).
function _fmtCapLabel(n) {
  if (!n) return '';
  if (n >= 1_000_000 && n % 1_000_000 === 0) return `${n / 1_000_000}M`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${Math.round(n / 1000)}K`;
  return `${n}`;
}

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
  // Spec 0035: shared scale across every bar in this grid. Recomputes
  // when the per-turn usage dict changes (the rows are derived from it).
  const scale = React.useMemo(() => computeConsumptionScale(rows, run), [rows, run]);

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
      {/* Spec 0035: caption telling the user the bars are data-relative
          (not the full 1M-cap-relative). Same denominator across the grid. */}
      <div className="mono" style={{
        marginBottom: 10, padding: '0 4px',
        fontSize: 10.5, color: 'var(--fg-3)',
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <span>scale: <span style={{ color: 'var(--fg-1)' }}>{fmt.tokens(scale.denom)}t</span></span>
        {scale.window > 0 && scale.window !== scale.denom && (
          <>
            <span>·</span>
            <span>cap <span style={{ color: 'var(--fg-1)' }}>{_fmtCapLabel(scale.window)}</span></span>
          </>
        )}
        <span style={{ flex: 1 }} />
        {scale.dataRelative && (
          <span style={{ fontStyle: 'italic', color: 'var(--fg-4)' }}>
            bars sized to the largest input in this run, not the full window
          </span>
        )}
      </div>
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
              scale={scale}
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

function ConsumptionRow({ row, run, scale, showPhaseTitle, expanded, onToggle }) {
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
        <TokenLaneCell usage={row.claude} agent="claude" run={run} scale={scale} />
      </div>
      {/* OpenAI lane */}
      <div onClick={onToggle} style={{ cursor: 'pointer' }}>
        <TokenLaneCell usage={row.gpt} agent="gpt" run={run} scale={scale} />
      </div>
      {expanded && (
        <ConsumptionRowExpanded row={row} run={run} scale={scale} />
      )}
    </React.Fragment>
  );
}

// Per-row expanded body — spec 0035 rework. Two per-agent
// ``ConsumptionCard``s side-by-side, each carrying its agent's total
// bar at top + stacked sub-bars per input piece below. Spans all 3
// columns of the parent grid.
function ConsumptionRowExpanded({ row, run, scale }) {
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
        marginBottom: 10,
      }}>
        per-input breakdown · {PHASE_NAMES[row.phase] || `Phase ${row.phase}`}
        {row.label && ` · ${row.label}`}
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 14,
        alignItems: 'stretch',
      }}>
        <ConsumptionCard usage={row.claude} agent="claude" run={run} scale={scale} />
        <ConsumptionCard usage={row.gpt}    agent="gpt"    run={run} scale={scale} />
      </div>
    </div>
  );
}

// Spec 0035 — one card per agent, rendered side-by-side in the expanded
// row. Header carries the agent name + total tokens / cost; total bar
// fills against the shared ``scale``; stacked sub-bars beneath show each
// input piece's contribution at the same scale. Sort toggle flips
// between size-descending (default) and canonical Tk order. Web-search
// count + cost (spec 0031) survive at the bottom.
function ConsumptionCard({ usage, agent, run, scale }) {
  const meta = AGENT_META[agent];
  const [sortMode, setSortMode] = React.useState('size'); // 'size' | 'order'

  if (!usage) {
    return (
      <div style={{
        padding: '14px 16px',
        background: 'var(--bg-1)',
        border: '1px dashed var(--border-2)', borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--fg-4)', fontSize: 12,
        fontFamily: 'var(--mono)',
      }}>
        {meta.name} · silent this turn
      </div>
    );
  }

  const tokensIn  = Number(usage.in)  || 0;
  const tokensOut = Number(usage.out) || 0;
  const cost      = Number(usage.cost) || 0;
  const ctxWindow = contextWindowFor(usage, run, agent);
  const piecesRaw = usage.promptPieces || {};

  // Renormalise piece counts so they sum to the provider's input_tokens.
  const renormalised = (() => {
    const present = KIND_ORDER.filter((k) => Number(piecesRaw[k]) > 0);
    if (present.length === 0 || tokensIn <= 0) return [];
    const rawSum = present.reduce((acc, k) => acc + Number(piecesRaw[k] || 0), 0);
    if (rawSum <= 0) return [];
    const s = tokensIn / rawSum;
    return present.map((k) => ({
      kind: k,
      tokens: Math.max(0, Math.round(Number(piecesRaw[k] || 0) * s)),
    }));
  })();

  // Sort.
  const sorted = (() => {
    const copy = renormalised.slice();
    if (sortMode === 'size') {
      copy.sort((a, b) => b.tokens - a.tokens);
    } else {
      copy.sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
    }
    return copy;
  })();

  // Pieces that the protocol could have inlined here but didn't (zero
  // count in `promptPieces`) — surfaced as a footnote.
  const presentKinds = new Set(renormalised.map((p) => p.kind));
  const missingKinds = KIND_ORDER.filter((k) => !presentKinds.has(k));

  const pctOfCap = ctxWindow > 0 ? (tokensIn / ctxWindow * 100) : 0;
  const hasSearches = Number(usage.searches) > 0;

  return (
    <div style={{
      padding: '12px 14px',
      background: 'var(--bg-1)',
      border: `1px solid ${meta.border}`, borderRadius: 6,
      display: 'flex', flexDirection: 'column', gap: 10,
      minWidth: 0,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        flexWrap: 'wrap',
      }}>
        <AgentIcon agent={agent} size={14} />
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500 }}>
          {meta.name}
        </span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
          {fmt.tokens(tokensIn)}t in · {fmt.tokens(tokensOut)}t out
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
          ({pctOfCap.toFixed(1)}% of {_fmtCapLabel(ctxWindow)})
        </span>
        <span style={{ flex: 1 }} />
        {sorted.length > 1 && (
          <button
            type="button"
            onClick={() => setSortMode(m => m === 'size' ? 'order' : 'size')}
            title="Toggle sort: by size / canonical Tk order"
            style={{
              appearance: 'none', border: '1px solid var(--border-1)',
              background: 'var(--bg-2)', color: 'var(--fg-3)',
              borderRadius: 999, padding: '1px 8px',
              fontSize: 10.5, fontFamily: 'var(--mono)',
              cursor: 'pointer',
            }}
          >
            sort: {sortMode === 'size' ? '↓ size' : '↘ order'}
          </button>
        )}
      </div>

      {/* Total bar (agent color, against shared scale). */}
      <SubInputBar
        label="total input"
        tokens={tokensIn}
        scale={scale}
        color={meta.color}
        accent={true}
      />

      {/* Stacked sub-bars per piece. Empty when no pieces (pre-0030 turn). */}
      {sorted.length > 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 4,
          paddingLeft: 8,
          borderLeft: `1px dashed var(--border-2)`,
        }}>
          {sorted.map((p) => (
            <SubInputBar
              key={p.kind}
              label={INPUT_PIECE_LABEL[p.kind] || KIND_COLORS[p.kind]?.label || p.kind}
              tokens={p.tokens}
              scale={scale}
              color={SUBINPUT_COLORS[p.kind] || 'var(--fg-3)'}
            />
          ))}
        </div>
      )}

      {/* Empty-piece footnote — friendly labels, not raw Tk keys. */}
      {missingKinds.length > 0 && (
        <div className="mono" style={{
          fontSize: 10, color: 'var(--fg-4)', fontStyle: 'italic',
          paddingLeft: 8,
        }}>
          not used in this turn:{' '}
          {missingKinds.map((k) => INPUT_PIECE_LABEL[k] || KIND_COLORS[k]?.label || k).join(', ')}
        </div>
      )}

      {/* Web-search row — spec 0031 carry-forward. Spec 0039 relabels
          "tool cost" to "of which web search" since the per-turn ``cost``
          field now includes search fees in the headline (no longer a
          separate side-channel that needs to be added on top). */}
      {hasSearches && (
        <div className="mono" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          paddingTop: 6, borderTop: '1px solid var(--border-1)',
          fontSize: 10.5, color: 'var(--fg-3)',
        }}>
          <span>web searches:{' '}
            <span className="num" style={{ color: 'var(--fg-1)' }}>
              {Number(usage.searches).toLocaleString()}
            </span>
          </span>
          <span>·</span>
          <span>of which web search:{' '}
            <span className="num" style={{ color: 'var(--fg-2)' }}>
              {fmt.cost(Number(usage.searchCost) || 0)}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}

// One row inside a ConsumptionCard — label + bar + token count.
function SubInputBar({ label, tokens, scale, color, accent }) {
  const denom = scale?.denom || 1;
  const widthPct = denom > 0 ? Math.min(100, (tokens / denom) * 100) : 0;
  // Spec 0035: tick marker for the context-window cap shows ONLY on the
  // accent (total) bar. Sub-bars share the same scale but the marker is
  // visual noise repeated 7 times — keep it on the total only.
  const markerPct = (accent && scale?.window > 0 && scale.window <= scale.denom)
    ? (scale.window / scale.denom) * 100
    : null;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '140px 1fr 80px',
      alignItems: 'center', gap: 10,
      minWidth: 0,
    }}>
      <span style={{
        fontSize: accent ? 11 : 10.5,
        color: accent ? 'var(--fg-1)' : 'var(--fg-2)',
        fontWeight: accent ? 500 : 400,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {label}
      </span>
      <div style={{
        position: 'relative',
        width: '100%', height: accent ? 14 : 10,
        background: 'var(--bg-3)',
        borderRadius: 3, overflow: 'hidden',
        border: accent ? '1px solid rgba(0,0,0,0.10)' : 'none',
      }}>
        <div style={{
          position: 'absolute', top: 0, bottom: 0, left: 0,
          width: `${widthPct}%`,
          background: color,
          opacity: accent ? 0.9 : 0.75,
        }} />
        {markerPct != null && markerPct < 100 && (
          <ContextWindowMarker pct={markerPct} label={_fmtCapLabel(scale.window)} />
        )}
      </div>
      <span className="mono num" style={{
        fontSize: 10.5, color: 'var(--fg-2)',
        textAlign: 'right', whiteSpace: 'nowrap',
      }}>
        {fmt.tokens(tokens)}t
      </span>
    </div>
  );
}

// Spec 0035 — tiny vertical tick + label at the context-window position
// on a bar that's been zoomed-in to data scale. Tells the user where the
// budget cap is without re-sizing the bar to the cap.
function ContextWindowMarker({ pct, label }) {
  return (
    <React.Fragment>
      <div style={{
        position: 'absolute', top: -2, bottom: -2,
        left: `${pct}%`, width: 1,
        background: 'var(--fg-3)',
        opacity: 0.55,
      }} />
      <span className="mono" style={{
        position: 'absolute', left: `${pct}%`,
        top: -1, transform: 'translateX(-50%) translateY(-100%)',
        fontSize: 9, color: 'var(--fg-3)',
        background: 'var(--bg-1)',
        padding: '0 3px', borderRadius: 2,
        whiteSpace: 'nowrap',
      }}>
        {label}
      </span>
    </React.Fragment>
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
function TokenLaneCell({ usage, agent, run, scale }) {
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
  return <TokenBar usage={usage} agent={agent} run={run} scale={scale} />;
}

// Spec 0030: the bar now renders one segment per prompt-piece kind
// from `usage.promptPieces` (Tk palette), renormalised against
// `usage.in` so heuristic-vs-provider-token mismatches don't distort
// segment widths. An output tail still trails the input region (darker
// shade, thinner band). When `promptPieces` is missing (pre-0030
// transcripts) we fall back to the spec-0029 single-fill rendering.
function TokenBar({ usage, agent, run, scale }) {
  const meta = AGENT_META[agent];
  const tokensIn  = Number(usage.in)  || 0;
  const tokensOut = Number(usage.out) || 0;
  const cacheRead = Number(usage.cacheRead) || 0;
  const cacheWrite = Number(usage.cacheWrite) || 0;
  const modelId   = usage.modelId || null;
  const cost      = Number(usage.cost) || 0;
  const ctxWindow = contextWindowFor(usage, run, agent);
  // Spec 0035: bars are sized to the shared per-grid denominator (15%
  // headroom over the largest input observed) rather than the context-
  // window cap. The cap shows as a vertical tick marker on the bar.
  // Falls back to the cap when no scale is supplied (older render paths).
  const denom     = (scale && scale.denom) || ctxWindow;
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

  const inputPct  = Math.min(100, (tokensIn  / denom) * 100);
  const outputPct = Math.min(100 - inputPct, (tokensOut / denom) * 100);
  // Marker position for the context-window cap on a data-relative scale.
  // Only render the marker when the cap sits inside the visible bar range
  // (scale denom <= window) — when the bar IS sized to the cap, the
  // marker would just sit at 100% and is redundant.
  const showMarker = scale && scale.dataRelative && ctxWindow > 0
    && ctxWindow <= denom && (ctxWindow / denom) < 0.99;
  const markerPct = showMarker ? (ctxWindow / denom) * 100 : null;

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
          // share of the bar's denominator (spec 0035: data-relative).
          (() => {
            let offsetPct = 0;
            return renormalised.map((p) => {
              const colour = KIND_COLORS[p.kind]?.bg || 'var(--fg-3)';
              const widthPct = Math.min(100 - offsetPct, (p.tokens / denom) * 100);
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
                width: `${Math.min(100, (cacheRead / denom) * 100)}%`,
                background: meta.color + '55',
              }} />
            )}
            {tokensIn - cacheRead > 0 && (
              <div style={{
                position: 'absolute',
                left: `${Math.min(100, (cacheRead / denom) * 100)}%`,
                top: 0, bottom: 0,
                width: `${Math.max(0, Math.min(100, ((tokensIn - cacheRead) / denom) * 100))}%`,
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
        {/* Spec 0035: vertical tick marker at the context-window cap. */}
        {markerPct != null && (
          <ContextWindowMarker pct={markerPct} label={_fmtCapLabel(ctxWindow)} />
        )}
      </div>
      {/* Numeric row underneath. Spec 0035: percent is now against the
          context-window cap (the budget number that matters), not the
          bar's data-relative denominator. */}
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
        <span>{((tokensIn / ctxWindow) * 100).toFixed(1)}% of {_fmtCapLabel(ctxWindow)}</span>
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

  const header = <ArtifactHeader item={item} meta={meta} hover={hover} run={run} />;

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
      data-turn-key={item.turnKey || undefined}
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
          turnKey={item.turnKey}
        />
      )}
      {isLive && <ArtifactLiveBody item={item} />}
    </div>
  );
}

// The unfolded body — gist line + summary paragraph + "View in full mode".
// Sits below the header inside the same card. No modal entry from anywhere
// here EXCEPT the explicit button.
// Spec 0041 — the sentiment composer emits ``**Word —** rest of sentence``
// patterns. Inline-render those as bold spans without dragging in the
// full markdown pipeline.
function renderInlineBold(text) {
  if (!text) return text;
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} style={{ color: 'var(--fg-0)', fontWeight: 600 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

function ArtifactExpandedBody({ item, gist, summary, onOpen, turnKey }) {
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
          fontStyle: 'normal',
        }}>
          {renderInlineBold(gist)}
        </div>
      )}
      {summary && (
        <p style={{
          margin: 0,
          fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}>{summary}</p>
      )}
      <SearchGistLine turnKey={turnKey} onOpen={onOpen} />
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

// ─────────────────── Spec 0038 — SearchChip / SearchGistLine ────────────────
//
// Both reads from SearchIndexContext (one fetch per run) — no per-card
// network calls. Hidden when no audit data exists for this turn-key, or
// when the run has no audit data at all (pre-0036 transcripts).
function SearchChip({ turnKey }) {
  const ctx = React.useContext(SearchIndexContext);
  if (!turnKey) return null;
  const summary = ctx?.summary;
  if (!summary) return null;
  const s = summary.get(turnKey);
  if (!s || s.queries === 0) return null;
  const tip = `${s.queries} web search${s.queries === 1 ? '' : 'es'} · ${s.consulted} URL${s.consulted === 1 ? '' : 's'} retrieved`
    + (s.hasWarning ? ' · ⚠ unmatched citation' : '');
  return (
    <span title={tip} style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      padding: '1px 7px',
      borderRadius: 999,
      border: `1px solid ${s.hasWarning ? COLORS.warn + '55' : 'var(--border-1)'}`,
      background: 'var(--bg-2)',
      fontSize: 10.5, color: 'var(--fg-1)',
      fontFamily: 'var(--mono)',
      whiteSpace: 'nowrap',
    }}>
      <span style={{ fontSize: 10 }}>🔎</span>
      {s.queries}
      {s.hasWarning && (
        <span style={{ color: COLORS.warn, fontWeight: 700 }}>⚠</span>
      )}
    </span>
  );
}

function SearchGistLine({ turnKey, onOpen }) {
  const ctx = React.useContext(SearchIndexContext);
  if (!turnKey) return null;
  const summary = ctx?.summary;
  if (!summary) return null;
  const s = summary.get(turnKey);
  if (!s || s.queries === 0) return null;
  const handle = (e) => { e.stopPropagation(); if (onOpen) onOpen(); };
  const { queries, consulted, hasWarning } = s;
  const base = consulted > 0
    ? `Pulled ${consulted} result${consulted === 1 ? '' : 's'} across ${queries} quer${queries === 1 ? 'y' : 'ies'}`
    : `${queries} quer${queries === 1 ? 'y' : 'ies'} fired (no source list returned)`;
  return (
    <button
      type="button"
      onClick={handle}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: 0,
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        textAlign: 'left',
        fontFamily: 'inherit',
        fontSize: 11.5,
        color: hasWarning ? COLORS.warn : 'var(--fg-2)',
      }}>
      <span style={{ fontSize: 11 }}>🔎</span>
      <span>{hasWarning ? '⚠ ' : ''}{base} · click to inspect</span>
      <Icon.Arrow style={{ width: 10, height: 10 }} />
    </button>
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
// Spec 0041 D7 — body truncation helper. Compact-card headlines clip
// at ~70 chars before ellipsis so the column reads as a scannable list
// rather than a wall of wrapped text. The full body lives in the
// expanded surface (no truncation) and on the ``title`` attribute for
// hover tooltips.
function truncateBody(s, max = 70) {
  if (s == null) return '';
  const trimmed = String(s).trim();
  if (trimmed.length <= max) return trimmed;
  return trimmed.slice(0, max - 1).trimEnd() + '…';
}

// Spec 0041 D8 — sentiment composer with overall-sentiment lead.
// Pre-spec the composer covered Phase 2 + Phase 4 with terse output
// and Phase 0 / 1 / 3 / 5 returned ''. Now every phase emits a 2–3
// sentence paragraph: sentence 1 is the overall sentiment word + the
// agent identity + the round-level cue; sentence 2 carries the
// activity counts (raised / answered / resolved); sentence 3 is the
// standing snapshot when there's something to say.
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
  const allIssues = Array.isArray(run?.issues) ? run.issues : [];
  const allComments = Array.isArray(run?.comments) ? run.comments : [];

  const lead = (word, rest) =>
    `**${word} —** ${rest}`;

  // ─── Phase 0 — per-agent brief critique ─────────────────────────────────
  if (item.kind === 'preflight') {
    const briefIssues = stats.briefIssues ?? 0;
    if (status === 'BRIEF_OK' && briefIssues === 0) {
      return lead('Positive', `${agentName} approved the brief outright.`);
    }
    if (status === 'BRIEF_OK') {
      return lead(
        'Mostly positive',
        `${agentName} approved the brief but flagged ${plur(briefIssues, 'minor issue')}.`,
      );
    }
    if (status === 'BRIEF_NEEDS_INPUT') {
      return lead(
        'Cautious',
        `${agentName} flagged ${plur(briefIssues, 'blocking issue')} before drafting.`,
      );
    }
    return briefIssues > 0
      ? lead('Cautious', `${agentName} flagged ${plur(briefIssues, 'issue')} on the brief.`)
      : lead('Neutral', `${agentName} reviewed the brief.`);
  }

  // ─── Phase 0 — shared input card ────────────────────────────────────────
  if (item.kind === 'input') {
    const s = stats || {};
    if (s.state === 'ok') {
      return lead('Positive', `Both agents found the brief OK to proceed.`);
    }
    if (s.state === 'issues' && s.count > 0) {
      return lead(
        'Cautious',
        `Brief came back with ${plur(s.count, 'issue')} flagged across the two agents.`,
      );
    }
    return '';
  }

  // ─── Phase 1 — independent draft ────────────────────────────────────────
  if (phase === 1) {
    // What we know cheaply about a Phase 1 draft: it landed. The
    // counts that matter (V/U tags, question count) live in the
    // draft body which we don't parse here. The sentiment lead just
    // marks it as solid; sentence 2 nods to "independent draft".
    return lead(
      'Solid',
      `${agentName} delivered an independent Phase 1 draft. The draft is now an input to Phase 2 negotiation.`,
    );
  }

  // ─── Phase 2 — negotiation turn ─────────────────────────────────────────
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

    let sentimentWord = 'Neutral';
    let leadRest;
    if (status === 'AGREED') {
      sentimentWord = 'Positive';
      leadRest = `${agentName} endorsed the plan this round.`;
    } else if (status === 'NEGOTIATING' || !status) {
      if (round === 1) {
        sentimentWord = 'Cautious';
        leadRest = `${agentName}'s round-1 difference inventory.`;
      } else if (myClosedDsHere.length === 0 && otherQsAnsweredHere.length === 0
                 && myOpenedDsHere.length === 0 && myNewQs.length === 0) {
        sentimentWord = 'Critical';
        leadRest = `${agentName} still negotiating in round ${round} with no movement.`;
      } else {
        sentimentWord = 'Cautious';
        leadRest = `${agentName} still negotiating in round ${round}.`;
      }
    } else if (status === 'DISAGREED') {
      sentimentWord = 'Critical';
      leadRest = `${agentName} disagreed in round ${round}.`;
    } else {
      leadRest = `${agentName} · ${status.toLowerCase()}.`;
    }

    const sentences = [lead(sentimentWord, leadRest)];

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

  // ─── Phase 3 — drafter writes the converged document ────────────────────
  if (phase === 3 || item.kind === 'doc' || item.kind === 'doc-live') {
    if (item.completed) {
      return lead('Done', `Final document emitted by ${agentName}.`);
    }
    return lead(
      'Solid',
      `${agentName} wrote v1 of the converged document.`,
    );
  }

  // ─── Phase 4 — review turn ──────────────────────────────────────────────
  if (phase === 4) {
    const openIssuesNow = typeof stats.openIssues === 'number'
      ? stats.openIssues
      : allIssues.filter(i => i.phase === 4 && i.raisedBy === agent && i.status === 'open').length;
    const myCommentsHere = allComments.filter(
      c => c.phase === 4 && c.raisedBy === agent && c.raisedRound === round
    );
    const myIssuesNewHere = allIssues.filter(
      i => i.phase === 4 && i.raisedBy === agent && i.roundFirstSeen === round
    );

    let sentimentWord;
    let leadRest;
    if (status === 'APPROVED' && openIssuesNow === 0) {
      sentimentWord = 'Positive';
      leadRest = `${agentName} approved the draft this round.`;
    } else if (status === 'APPROVED') {
      sentimentWord = 'Mostly positive';
      leadRest = `${agentName} approved with ${plur(openIssuesNow, 'open issue')} carried.`;
    } else if (status === 'NOT_APPROVED') {
      sentimentWord = 'Critical';
      leadRest = `${agentName} did not approve; ${plur(openIssuesNow, 'open issue')}.`;
    } else if (status === 'REVIEWING') {
      sentimentWord = openIssuesNow > 0 ? 'Cautious' : 'Neutral';
      leadRest = `${agentName} still reviewing in round ${round}.`;
    } else {
      sentimentWord = 'Neutral';
      leadRest = `${agentName} · ${status ? status.toLowerCase() : 'reviewing'}.`;
    }

    const sentences = [lead(sentimentWord, leadRest)];

    const movements = [];
    if (myIssuesNewHere.length > 0) movements.push(`raised ${plur(myIssuesNewHere.length, 'new issue')}`);
    if (myCommentsHere.length > 0) movements.push(`noted ${plur(myCommentsHere.length, 'comment')}`);
    if (movements.length > 0) {
      sentences.push(`${capitalise(movements.join(', '))}.`);
    }

    if (openIssuesNow > 0) {
      sentences.push(`${plur(openIssuesNow, 'issue')} open against the current draft.`);
    } else if (status === 'APPROVED') {
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

// Spec 0042 D5 — per-phase chip allowlist. Each phase only renders the
// chip kinds its protocol actually emits. Phase 0 (preflight) + Phase 3
// (silent drafter) + Phase 5 (final) have no structured turn items and
// render no chips. Phase 1 (plan draft) renders claims + questions.
// Phase 2 (negotiate) renders questions + disagreements + claims (R1
// only). Phase 4 (review) renders issues + comments + disagreements.
const PHASE_CHIP_ALLOWLIST = {
  0: [],
  1: ['claims', 'questions'],
  2: ['questions', 'disagreements', 'claims'],
  3: [],
  4: ['issues', 'comments', 'disagreements'],
  5: [],
};

// Small mono chips surfacing parsed protocol stats on a turn/plan row.
// Stays out of the way: nothing rendered when stats are absent.
// Spec 0034: ``prevStats`` enables round-over-round delta annotations
// (e.g. ``4 Q (-2)`` for "two questions answered since prior round").
// Spec 0042 D4 + D5: when ``run`` + ``turnKey`` are available, chip
// counts come from parsed-item arrays filtered by ``raisedTurnKey``
// (the typed lists on ``run`` — ``questions`` / ``disagreements`` /
// ``claims`` / ``issues`` / ``comments``). The agent's self-reported
// ``OPEN_QUESTIONS:`` / ``OPEN_ISSUES:`` / ``BLOCKING_DISAGREEMENTS:``
// counters become a sanity-check (logged when mismatched) but are not
// the source of truth. When ``run`` or ``turnKey`` is missing (older
// callers, or transcripts without parsed items), the function falls
// back to the legacy self-counter path.
function StatsChips({ stats, phase, prevStats, run, turnKey }) {
  // Per-phase chip allowlist (D5). Phase 0/3/5 → no chips even if the
  // parser found something stray.
  const allowed = PHASE_CHIP_ALLOWLIST[phase] || [];

  // D4 — derive counts from parsed-item arrays when the modern data is
  // wired. Filter each list by ``raisedTurnKey``. Fall back to
  // self-counters when ``run`` or ``turnKey`` is absent.
  const useParsed = run != null && turnKey != null && allowed.length > 0;
  let parsedCounts = null;
  if (useParsed) {
    const filt = (arr) => (arr || []).filter((it) => it.raisedTurnKey === turnKey).length;
    parsedCounts = {
      questions:     filt(run.questions),
      disagreements: filt(run.disagreements),
      claims:        filt(run.claims),
      issues:        filt(run.issues),
      comments:      filt(run.comments),
    };
    // Sanity-check the self-counter when both are present (logs once
    // per render mismatch; no UI surface — that's spec 0043's job).
    if (stats) {
      if (stats.openQuestions != null && stats.openQuestions !== parsedCounts.questions) {
        // eslint-disable-next-line no-console
        console.debug(
          `[stats] turn ${turnKey}: agent reported OPEN_QUESTIONS=${stats.openQuestions} but parser found ${parsedCounts.questions}`
        );
      }
      if (stats.openIssues != null && stats.openIssues !== parsedCounts.issues) {
        // eslint-disable-next-line no-console
        console.debug(
          `[stats] turn ${turnKey}: agent reported OPEN_ISSUES=${stats.openIssues} but parser found ${parsedCounts.issues}`
        );
      }
    }
  }

  const chips = [];

  // Spec 0042 — emit one chip per allowed kind whose count is > 0. The
  // delta annotation (round-over-round) still reads from ``prevStats``
  // for Phase 2/4 turns; for Phase 1 plan drafts there is no prior round
  // so no deltas are emitted.
  const pushChip = (kind, label, tint, value, prevValue) => {
    if (value <= 0) return;
    chips.push({
      value,
      label: value === 1 ? label : `${label}s`,
      tint,
      delta: prevValue != null ? value - prevValue : null,
    });
  };

  if (allowed.includes('claims')) {
    const value = useParsed ? parsedCounts.claims : 0;
    pushChip('claims', 'claim', 'info', value, null);
  }
  if (allowed.includes('questions')) {
    const value = useParsed
      ? parsedCounts.questions
      : (stats && stats.openQuestions != null ? stats.openQuestions : 0);
    const prev = prevStats?.openQuestions != null ? prevStats.openQuestions : null;
    pushChip('questions', 'question', 'info', value, prev);
  }
  if (allowed.includes('disagreements')) {
    const value = useParsed
      ? parsedCounts.disagreements
      : (stats && stats.blocking != null && stats.blocking > 0 ? stats.blocking : 0);
    const prev = prevStats?.blocking != null ? prevStats.blocking : null;
    pushChip('disagreements', 'disagreement', 'warn', value, prev);
  }
  if (allowed.includes('issues')) {
    const value = useParsed
      ? parsedCounts.issues
      : (stats && stats.openIssues != null ? stats.openIssues : 0);
    const prev = prevStats?.openIssues != null ? prevStats.openIssues : null;
    pushChip('issues', 'issue', 'warn', value, prev);
  }
  if (allowed.includes('comments')) {
    const value = useParsed ? parsedCounts.comments : 0;
    pushChip('comments', 'comment', 'info', value, null);
  }

  if (chips.length === 0 && !(stats && stats.status)) return null;

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
      {chips.map((c, i) => <StatChip key={i} {...c} />)}
      {stats && stats.status && <StatusInline label={stats.status} />}
    </span>
  );
}

function StatChip({ label, value, tint, delta }) {
  const colorMap = { ok: COLORS.ok, info: COLORS.info, warn: COLORS.warn, err: COLORS.err };
  const c = colorMap[tint] || 'var(--fg-3)';
  // Spec 0034 + 0040: small delta annotations.
  //   negative delta = answered/resolved since last round → render as
  //   `↩ N` glyph (clearly readable as "answered this round")
  //   positive delta = new this round → render as `+N`
  //   zero delta is hidden
  const answeredCount = (delta != null && delta < 0) ? -delta : 0;
  const newCount      = (delta != null && delta > 0) ?  delta : 0;
  const tooltip =
    answeredCount > 0 ? `${answeredCount} answered or resolved since last round`
    : newCount > 0    ? `${newCount} new this round`
    : undefined;
  return (
    <span className="mono"
          title={tooltip}
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
      {answeredCount > 0 && (
        <span className="num"
              style={{ color: COLORS.ok, fontWeight: 500, marginLeft: 2 }}>
          ↩ {answeredCount}
        </span>
      )}
      {newCount > 0 && (
        <span className="num"
              style={{ color: c, fontWeight: 500, marginLeft: 2 }}>
          +{newCount}
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

function ArtifactHeader({ item, meta, hover, run }) {
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
        <SearchChip turnKey={item.turnKey} />
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
        <StatsChips
          stats={item.stats}
          phase={item.statsPhase}
          prevStats={item.prevStats}
          run={run}
          turnKey={item.turnKey}
        />
        <SearchChip turnKey={item.turnKey} />
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
  // Spec 0038: a Web Search tab joins as the last default tab.
  const webSearch = useWebSearchTab(item.turnKey);
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
    webSearch,
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

// Spec 0038: helper used by every full-view modal that gains a Web Search
// tab. The badge string comes from the run-scoped SearchIndexContext —
// when this turn has a hallucinated-citation flag, the tab label
// renders a small `⚠` to match the per-card chip and the run-header
// summary.
function useWebSearchTab(turnKey) {
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  const s = turnKey && summary ? summary.get(turnKey) : null;
  const badge = s && s.hasWarning ? '⚠' : null;
  return {
    id: 'webSearch',
    label: 'Web Search',
    badge,
    content: <WebSearchTabContent turnKey={turnKey} />,
  };
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
          {/* Spec 0042 D6 — round-1 difference inventory now parses as
              "claim" not "disagreement"; render claims as their own
              group so the badge counts on the timeline card reconcile
              with what the modal shows. */}
          <ReviewGroup
            label="Claims"
            color={COLORS.info}
            items={items}
            kinds={['claim']}
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
              No structured items in this turn — open the document
              modal from the card header to read the full markdown body.
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
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  const hasWarning = !!(item.turnKey && summary && summary.get(item.turnKey)?.hasWarning);

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
        <NegotiateLeftSubTabs active={sub} onChange={setSub} hasSearchWarning={hasWarning} />
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
        {sub === 'webSearch' && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
            searches/{item.turnKey || '—'}.json
          </span>
        )}
      </div>
      <div ref={leftRef} style={{
        flex: 1, minHeight: 0, overflow: 'auto',
        padding: '14px 16px',
      }}>
        {sub === 'original' && <LazyMarkdownBody filePath={priorFilePath} />}
        {sub === 'input' && <InputTabContent turnKey={item.turnKey} />}
        {sub === 'webSearch' && <WebSearchTabContent turnKey={item.turnKey} />}
      </div>
    </div>
  );
}

function NegotiateLeftSubTabs({ active, onChange, hasSearchWarning }) {
  const tabs = [
    { id: 'original',  label: 'Original' },
    { id: 'input',     label: 'Input' },
    { id: 'webSearch', label: 'Web Search', badge: hasSearchWarning ? '⚠' : null },
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
            {t.badge && (
              <span style={{ marginLeft: 4, color: COLORS.warn, fontWeight: 700 }}>
                {t.badge}
              </span>
            )}
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

        {/* Right: the draft + per-section "🔗 brief" affordance.
            Spec 0038: a Draft|Web Search sub-tab strip surfaces the
            draft turn's audit bundle without changing the modal frame. */}
        <DraftRightPane
          filePath={item.filePath}
          turnKey={item.turnKey}
          onSectionClick={onSectionAnchorClick}
        />
      </div>
    </Modal>
  );
}

function DraftRightPane({ filePath, turnKey, onSectionClick }) {
  const { body, loading } = window.useFileBody(filePath);
  const containerRef = React.useRef(null);
  const [sub, setSub] = React.useState('draft');
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  const hasWarning = !!(turnKey && summary && summary.get(turnKey)?.hasWarning);

  // Walk the rendered DOM after each render and inject a "🔗 brief"
  // button into every section heading. Best-effort — the markdown
  // renderer may take a tick to settle on first mount.
  React.useEffect(() => {
    if (sub !== 'draft') return;
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
        <DraftRightSubTabs active={sub} onChange={setSub} hasSearchWarning={hasWarning} />
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
          {sub === 'draft'
            ? (filePath || '—')
            : `searches/${turnKey || '—'}.json`}
        </span>
      </div>
      <div ref={containerRef} style={{
        flex: 1, minHeight: 0, overflow: 'auto',
        padding: '14px 16px',
      }}>
        {sub === 'draft' ? (
          loading
            ? <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading…</div>
            : <Markdown text={body || '— body unavailable —'} />
        ) : (
          <WebSearchTabContent turnKey={turnKey} />
        )}
      </div>
    </div>
  );
}

function DraftRightSubTabs({ active, onChange, hasSearchWarning }) {
  const tabs = [
    { id: 'draft',     label: 'Draft' },
    { id: 'webSearch', label: 'Web Search', badge: hasSearchWarning ? '⚠' : null },
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
            {t.badge && (
              <span style={{ marginLeft: 4, color: COLORS.warn, fontWeight: 700 }}>
                {t.badge}
              </span>
            )}
          </button>
        );
      })}
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
// Phase 1 (spec 0042 — plan-draft modal):
//   - The brief; the agent's only input at that point. Claims and
//     ``## Open Questions`` items anchor against brief blocks.
// Phase 2:
//   - Round 1: the OTHER agent's Phase 1 draft.
//   - Round N≥2: the OTHER agent's round N-1 turn file.
// Phase 4:
//   - The latest converged-document version available, surfaced by the
//     aggregator on `run.currentDraftPath`. Falls back to `phase3/draft-v1.md`
//     server-side; null when neither file exists yet.
function priorContentPathFor(item, otherUiAgent, run) {
  const phase = item.statsPhase || 2;
  if (phase === 1) {
    return 'brief.md';
  }
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
  // Spec 0042 D7 — bucket keys arrive camelCased from the server
  // (``_to_camel`` walks every string dict key). Phase 1 plan-draft
  // cards have no round dimension; the aggregator keys their bucket
  // as ``phase1_<agent>`` → ``phase1Claude`` / ``phase1Gpt`` on the
  // wire. Pre-spec the frontend looked up snake_case keys and always
  // got ``undefined`` — that's why the right pane reported "no
  // structured items" even for turns that emitted them.
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const key = phase === 1
    ? `phase1${cap(item.agent)}`
    : `phase${phase}Round${item.round}${cap(item.agent)}`;
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

// ─────────────────── Spec 0038 — Web Search tab ─────────────────────────────
//
// Renders a per-turn audit bundle persisted under
// ``session_dir/searches/<turn-key>.json`` by spec 0036. The provider
// asymmetry is rendered honestly:
//   - Anthropic: full per-query result list with title, host, page_age,
//     `[cited]` tags on cited URLs, and a monospace `cited_text` block
//     under each citation that points to that URL.
//   - OpenAI: URL-only consulted sources (when `include` was sent) +
//     URL+title citations without snippet text.
// Hallucinated citations (cited URL not in any retrieval set) surface in
// three places: tab badge, query-group dot, banner inside the tab body.
function WebSearchTabContent({ turnKey }) {
  const { bundle, loading, error } = window.useSearchBundle(turnKey);
  if (!turnKey) {
    return <SearchEmptyState kind="no-bundle" />;
  }
  if (loading) {
    return <div className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>loading search audit…</div>;
  }
  if (error) {
    return <SearchEmptyState kind="error" detail={error} />;
  }
  if (!bundle) {
    return <SearchEmptyState kind="no-bundle" />;
  }
  const events = bundle.tool_events || [];
  const citations = bundle.citations || [];
  const provider = bundle.provider || 'unknown';
  if (events.length === 0 && citations.length === 0) {
    return <SearchEmptyState kind="no-search" />;
  }
  const flags = bundle.flags || {};

  // Group citations by their `matched_query_id` so each QueryGroup body
  // can render the per-query citations alongside the consulted sources.
  // Citations with `matched_query_id === null` are the hallucinated ones
  // — collected separately + listed in the banner.
  const citationsByEventId = new Map();
  const unmatched = [];
  for (const c of citations) {
    if (c.matched_query_id) {
      const arr = citationsByEventId.get(c.matched_query_id) || [];
      arr.push(c);
      citationsByEventId.set(c.matched_query_id, arr);
    } else {
      unmatched.push(c);
    }
  }

  const showBanner = !!flags.cited_url_not_in_consulted_sources && unmatched.length > 0;
  const defaultOpen = events.length <= 2;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {showBanner && <HallucinationBanner unmatched={unmatched} />}
      {events.length === 0 && citations.length > 0 && (
        <SearchEmptyState kind="citations-only" provider={provider} />
      )}
      {events.map((ev, i) => (
        <QueryGroup
          key={ev.event_id || `ev-${i}`}
          event={ev}
          citations={citationsByEventId.get(ev.event_id) || []}
          provider={provider}
          defaultOpen={defaultOpen}
        />
      ))}
      {events.length > 0 && citations.length === 0 && (
        <div className="mono" style={{
          fontSize: 11.5, color: 'var(--fg-3)',
          padding: '8px 10px',
          background: 'var(--bg-2)',
          border: '1px dashed var(--border-2)',
          borderRadius: 'var(--r-2)',
        }}>
          The model performed {events.length} search{events.length === 1 ? '' : 'es'} but cited none of the results in its final output.
        </div>
      )}
    </div>
  );
}

function HallucinationBanner({ unmatched }) {
  return (
    <div style={{
      padding: '10px 12px',
      borderRadius: 'var(--r-2)',
      border: `1px solid ${COLORS.warn}55`,
      background: 'rgba(212,160,86,0.10)',
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 12, color: COLORS.warn, fontWeight: 600,
      }}>
        <span>⚠</span>
        <span>
          {unmatched.length} citation{unmatched.length === 1 ? '' : 's'} reference{unmatched.length === 1 ? 's' : ''} a URL that wasn't in any retrieval set
        </span>
      </div>
      <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {unmatched.map((c, i) => (
          <li key={i} style={{ fontSize: 11.5, color: 'var(--fg-1)' }}>
            <a href={c.url} target="_blank" rel="noopener noreferrer"
               style={{ color: 'var(--fg-0)', textDecoration: 'underline', wordBreak: 'break-all' }}>
              {c.url}
            </a>
            {c.title && (
              <span className="mono" style={{ display: 'block', color: 'var(--fg-3)', fontSize: 10.5 }}>
                “{c.title}”
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function QueryGroup({ event, citations, provider, defaultOpen }) {
  const [open, setOpen] = React.useState(defaultOpen);
  const queries = event.queries || [];
  const sources = event.consulted_sources || [];
  const actionType = event.action_type || 'search';
  const queryLabel = queries.length
    ? queries.join(' · ')
    : actionType === 'search'
      ? '(query not exposed)'
      : `(${actionType})`;

  // Build the set of cited URLs (normalised) so consulted-source cards can
  // render a [cited] tag — and so the per-source cited_text blocks can be
  // attached to the right card.
  const citedNorm = new Set();
  const citationsByNormUrl = new Map();
  for (const c of citations) {
    const n = normalizeSearchUrl(c.url || '');
    if (!n) continue;
    citedNorm.add(n);
    const arr = citationsByNormUrl.get(n) || [];
    arr.push(c);
    citationsByNormUrl.set(n, arr);
  }

  // QueryGroup-level warning dot: any citation that resolved to THIS event
  // but whose URL is not in this event's consulted set. (Rare — the
  // common cross-ref miss is matched_query_id === null which is folded
  // into the banner/tab badge, not here.)
  const sourceNorm = new Set(sources.map(s => normalizeSearchUrl(s.url || '')).filter(Boolean));
  const groupWarning = citations.some(c => {
    const n = normalizeSearchUrl(c.url || '');
    return n && !sourceNorm.has(n);
  });

  return (
    <div style={{
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
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
        <span style={{ fontWeight: 500, flex: 1, minWidth: 0,
                       overflow: 'hidden', textOverflow: 'ellipsis',
                       whiteSpace: 'nowrap' }}>
          {queryLabel}
        </span>
        <span className="mono" style={{
          fontSize: 10, color: 'var(--fg-3)',
          padding: '1px 6px',
          background: 'var(--bg-2)',
          border: '1px solid var(--border-1)',
          borderRadius: 999,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>{actionType}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
          {sources.length} result{sources.length === 1 ? '' : 's'}
          {citations.length > 0 && ` · ${citations.length} cited`}
        </span>
        {groupWarning && (
          <span title="A citation pinned to this query references a URL not in its retrieval set"
                style={{ color: COLORS.warn, fontSize: 12 }}>⚠</span>
        )}
      </button>
      {open && (
        <div style={{
          borderTop: '1px solid var(--border-1)',
          padding: '10px 12px',
          background: 'var(--bg-0)',
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {sources.length === 0 ? (
            <div className="mono" style={{
              fontSize: 11, color: 'var(--fg-3)',
              padding: '4px 0',
            }}>
              {provider === 'openai'
                ? 'Provider returned no retrieval list — only citations are auditable.'
                : 'No consulted sources returned for this event.'}
            </div>
          ) : (
            sources.map((s, i) => {
              const norm = normalizeSearchUrl(s.url || '');
              const isCited = norm && citedNorm.has(norm);
              const sourceCitations = (norm && citationsByNormUrl.get(norm)) || [];
              return (
                <ConsultedSourceCard
                  key={i}
                  source={s}
                  isCited={isCited}
                  citationsForSource={sourceCitations}
                />
              );
            })
          )}
          {sources.length === 0 && citations.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {citations.map((c, i) => (
                <CitationOnlyCard key={i} citation={c} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ConsultedSourceCard({ source, isCited, citationsForSource }) {
  const url = source.url || '';
  let host = '';
  try { host = new URL(url).hostname; } catch { host = ''; }
  const title = source.title || null;
  const pageAge = source.page_age || null;
  return (
    <div style={{
      padding: '8px 10px',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      background: 'var(--bg-1)',
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <a href={url} target="_blank" rel="noopener noreferrer"
           title={url}
           style={{
             color: 'var(--fg-0)', fontSize: 12.5, fontWeight: 500,
             textDecoration: 'none', wordBreak: 'break-word', minWidth: 0,
           }}>
          {title || host || url}
        </a>
        {host && title && (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{host}</span>
        )}
        {pageAge && (
          <span className="mono" style={{
            fontSize: 10, color: 'var(--fg-3)',
            padding: '0 6px',
            background: 'var(--bg-2)',
            border: '1px solid var(--border-1)',
            borderRadius: 999,
          }}>{pageAge}</span>
        )}
        <span style={{ flex: 1 }} />
        {isCited && (
          <span style={{
            fontSize: 10, color: COLORS.info, fontWeight: 600,
            padding: '0 6px',
            background: 'rgba(107,156,240,0.10)',
            border: '1px solid rgba(107,156,240,0.30)',
            borderRadius: 999,
            letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>[cited]</span>
        )}
      </div>
      {citationsForSource && citationsForSource.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 2 }}>
          {citationsForSource.map((c, i) => (
            <CitedTextBlock key={i} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function CitedTextBlock({ citation }) {
  const text = citation.cited_text;
  return (
    <div style={{
      borderLeft: `2px solid ${COLORS.info}55`,
      paddingLeft: 10,
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div className="mono" style={{
        fontSize: 9.5, color: 'var(--fg-3)',
        letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>
        cited from this URL
      </div>
      {text ? (
        <pre style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: 'var(--mono)',
          fontSize: 11.5,
          lineHeight: 1.5,
          color: 'var(--fg-1)',
        }}>{text}</pre>
      ) : (
        <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', fontStyle: 'italic' }}>
          (provider returned no source-side snippet)
        </div>
      )}
    </div>
  );
}

function CitationOnlyCard({ citation }) {
  const url = citation.url || '';
  let host = '';
  try { host = new URL(url).hostname; } catch { host = ''; }
  return (
    <div style={{
      padding: '8px 10px',
      border: '1px dashed var(--border-1)',
      borderRadius: 'var(--r-2)',
      background: 'var(--bg-1)',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <a href={url} target="_blank" rel="noopener noreferrer"
           title={url}
           style={{
             color: 'var(--fg-0)', fontSize: 12.5, fontWeight: 500,
             textDecoration: 'none', wordBreak: 'break-word',
           }}>
          {citation.title || host || url}
        </a>
        {host && citation.title && (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{host}</span>
        )}
        <span style={{ flex: 1 }} />
        <span style={{
          fontSize: 10, color: COLORS.info, fontWeight: 600,
          padding: '0 6px',
          background: 'rgba(107,156,240,0.10)',
          border: '1px solid rgba(107,156,240,0.30)',
          borderRadius: 999,
          letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>citation</span>
      </div>
      {citation.cited_text && (
        <CitedTextBlock citation={citation} />
      )}
    </div>
  );
}

function SearchEmptyState({ kind, provider, detail }) {
  let label;
  if (kind === 'error') {
    label = `Could not load web search audit${detail ? ` (${detail})` : ''}.`;
  } else if (kind === 'no-search') {
    label = 'Web search was available but not used in this turn.';
  } else if (kind === 'citations-only') {
    label = provider === 'openai'
      ? 'Provider returned no retrieval list — only citations are auditable.'
      : 'Citations recorded but no tool events captured.';
  } else {
    label = 'Web search audit not recorded for this turn. This run pre-dates spec 0036 or web search was disabled.';
  }
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
  const turnKey = item.turnKey || `phase0_${item.agent}`;
  const webSearch = useWebSearchTab(turnKey);
  const tabs = [
    {
      id: 'content',
      label: 'Content',
      content: <LazyMarkdownBody filePath={item.filePath} />,
    },
    {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={turnKey} />,
    },
    webSearch,
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
  // Spec 0041 — Phase 4 ``Issue ledger`` + ``Comments on the current
  // draft`` get their own first-class arrays alongside questions /
  // disagreements. Older runs (transcripts without `run.issues`) get
  // empty lists.
  const issues = Array.isArray(run.issues) ? run.issues : [];
  const comments = Array.isArray(run.comments) ? run.comments : [];

  // Spec 0040 D5: the Summary tab is visible only when the run has
  // reached a terminal state — the post-mortem aggregate doesn't make
  // sense while numbers are still shifting each poll.
  const isTerminal = run.status === 'completed'
    || run.status === 'deadlocked'
    || run.status === 'errored';

  // Phase pick: prefer the currently-running phase; else any phase that has
  // either kind of item; else default to Phase 2.
  const haveAny = (pid) =>
    questions.some(q => q.phase === pid) || disagreements.some(d => d.phase === pid);
  const initial = (run.phase === 4 || run.phase === 2) ? run.phase
                 : haveAny(4) ? 4
                 : haveAny(2) ? 2
                 : 2;
  // selectedPhase is 2 | 4 | 'summary'.
  const [selectedPhase, setSelectedPhase] = React.useState(initial);
  const [typeFilter, setTypeFilter] = React.useState('all'); // 'all' | 'questions' | 'disagreements'
  React.useEffect(() => { setSelectedPhase(initial); setTypeFilter('all'); }, [run.id, initial]);
  // If the user had selected Summary but the run later regressed out of
  // a terminal state (rare — e.g. a resume), fall back to a phase view.
  React.useEffect(() => {
    if (selectedPhase === 'summary' && !isTerminal) setSelectedPhase(initial);
  }, [isTerminal, selectedPhase, initial]);

  // Phase-filtered slices. (Summary view ignores both filters and uses
  // the full lists directly — see SummaryView.)
  const isSummary = selectedPhase === 'summary';
  const phaseQuestions = isSummary ? [] : questions.filter(q => q.phase === selectedPhase);
  const phaseDisagreements = isSummary ? [] : disagreements.filter(d => d.phase === selectedPhase);
  const phaseIssues = isSummary ? [] : issues.filter(i => i.phase === selectedPhase);
  const phaseComments = isSummary ? [] : comments.filter(c => c.phase === selectedPhase);

  // Spec 0041 D5 — type filter now distinguishes four kinds.
  const showI = typeFilter === 'all' || typeFilter === 'issues';
  const showQ = typeFilter === 'all' || typeFilter === 'questions';
  const showD = typeFilter === 'all' || typeFilter === 'disagreements';
  const showC = typeFilter === 'all' || typeFilter === 'comments';

  // Group by status. Comments don't have a status — they're always
  // "noted"; they go in the resolved column to keep open-vs-noise
  // separation clean.
  const openItems = [];
  const resolvedItems = [];
  if (showI) {
    for (const i of phaseIssues) {
      const item = { ...i, _critiqueKind: 'i' };
      (i.status === 'open' ? openItems : resolvedItems).push(item);
    }
  }
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
  if (showC) {
    for (const c of phaseComments) {
      const item = { ...c, _critiqueKind: 'c' };
      resolvedItems.push(item);
    }
  }

  // Sort: by round ascending so the user reads chronological history.
  const sortRound = (it) => {
    switch (it._critiqueKind) {
      case 'q': return it.raisedRound;
      case 'd': return it.openedRound;
      case 'i': return it.roundFirstSeen;
      case 'c': return it.raisedRound;
      default:  return 0;
    }
  };
  const byRound = (a, b) => (sortRound(a) || 0) - (sortRound(b) || 0);
  openItems.sort(byRound);
  resolvedItems.sort(byRound);

  const totalOpen = openItems.length;
  const totalResolved = resolvedItems.length;
  const introduced = (showI ? phaseIssues.length : 0)
                   + (showQ ? phaseQuestions.length : 0)
                   + (showD ? phaseDisagreements.length : 0)
                   + (showC ? phaseComments.length : 0);

  // Phase-tab info: shows I + Q + D + C counts per phase (any zeros
  // collapse out of the label).
  const phaseInfo = (pid) => {
    const iInPhase = issues.filter(i => i.phase === pid);
    const qInPhase = questions.filter(q => q.phase === pid);
    const dInPhase = disagreements.filter(d => d.phase === pid);
    const cInPhase = comments.filter(c => c.phase === pid);
    const pending = run.phase < pid || (pid === 4 && run.phase < 3);
    return {
      pid,
      label: pid === 2 ? 'Negotiate' : 'Review',
      iTotal: iInPhase.length,
      iOpen: iInPhase.filter(i => i.status === 'open').length,
      qTotal: qInPhase.length,
      qOpen: qInPhase.filter(q => q.status === 'open').length,
      dTotal: dInPhase.length,
      dOpen: dInPhase.filter(d => d.status === 'open').length,
      cTotal: cInPhase.length,
      pending,
      active: (run.phase === pid && run.status === 'running'),
    };
  };
  const tabs = [phaseInfo(2), phaseInfo(4)];

  // Spec 0042 D11 — ``totalIntroduced`` is the phase-scoped sum, not a
  // global one across both phases. Previously read all phases' totals
  // here, which then didn't reconcile with ``totalOpen + totalResolved``
  // (which ARE phase-scoped). Math now adds up within the selected tab.
  const totalIntroduced = introduced;

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
            <LedgerDriftChip drifts={run.drifts} phaseId={selectedPhase} />
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
        {/* Spec 0040 D5 — Summary tab joins as the rightmost choice once
            the run reaches a terminal state. */}
        {isTerminal && (
          <CritiquePhaseTab
            tab={{
              pid: 'summary', label: 'Summary',
              qTotal: questions.length, dTotal: disagreements.length,
              pending: false, active: false, summary: true,
            }}
            active={selectedPhase === 'summary'}
            onSelect={() => setSelectedPhase('summary')}
          />
        )}
        <span style={{ flex: 1 }} />
        {!isSummary && <CritiqueTypeFilter active={typeFilter} onChange={setTypeFilter} />}
      </PaneToolbar>
      {isSummary ? (
        <CritiqueSummaryView run={run} questions={questions} disagreements={disagreements} />
      ) : (
        <CritiquePhaseContent
          run={run}
          phaseId={selectedPhase}
          openItems={openItems}
          resolvedItems={resolvedItems}
          introduced={introduced}
          onHighlight={handleHighlight}
        />
      )}
    </section>
  );
}

// Keep the old export name as an alias for backwards-compat in case any
// other module references it (no external links to break, but defensive).
const DisagreementExplorer = CritiqueExplorer;

function CritiqueTypeFilter({ active, onChange }) {
  // Spec 0041 D5 — four typed groups instead of two. Order is the
  // visual hierarchy: Issues + Questions are the items that gate
  // approval; Disagreements are blocking stances; Comments are
  // non-blocking commentary at the end.
  const items = [
    { id: 'all',           label: 'All' },
    { id: 'issues',        label: 'Issues' },
    { id: 'questions',     label: 'Questions' },
    { id: 'disagreements', label: 'Disagreements' },
    { id: 'comments',      label: 'Comments' },
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
      {!tab.summary && (
        <>
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
              : ((tab.iTotal || 0) + (tab.qTotal || 0) + (tab.dTotal || 0) + (tab.cTotal || 0) === 0) ? 'no items'
              : <>
                  {tab.iTotal > 0 && (
                    <>
                      <span style={{ color: COLORS.warn }}>{tab.iTotal} I</span>
                      <span style={{ color: 'var(--fg-4)' }}> · </span>
                    </>
                  )}
                  {tab.qTotal > 0 && (
                    <>
                      <span style={{ color: COLORS.info }}>{tab.qTotal} Q</span>
                      <span style={{ color: 'var(--fg-4)' }}> · </span>
                    </>
                  )}
                  {tab.dTotal > 0 && (
                    <>
                      <span style={{ color: COLORS.warn }}>{tab.dTotal} D</span>
                      {tab.cTotal > 0 && <span style={{ color: 'var(--fg-4)' }}> · </span>}
                    </>
                  )}
                  {tab.cTotal > 0 && (
                    <span style={{ color: 'var(--fg-3)' }}>{tab.cTotal} C</span>
                  )}
                </>
            }
          </span>
        </>
      )}
      {tab.summary && (
        <span style={{
          fontSize: 12.5,
          color: active ? 'var(--fg-0)' : 'var(--fg-2)',
          fontWeight: active ? 600 : 500,
        }}>
          ∑ {tab.label}
        </span>
      )}
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

  const renderItem = (item) => {
    switch (item._critiqueKind) {
      case 'q': return <QuestionCard key={item.id} q={item} onHighlight={onHighlight} />;
      case 'd': return <DisagreementCard key={item.id} d={item} onHighlight={onHighlight} />;
      case 'i': return <IssueCard key={item.id} issue={item} onHighlight={onHighlight} />;
      case 'c': return <CommentCard key={item.id} comment={item} onHighlight={onHighlight} />;
      default:  return null;
    }
  };

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

// Spec 0040 — Summary view. Post-mortem aggregate of the critique
// journey: one row per (phase, round) tuple, columns for Q raised /
// answered / open + D raised / resolved / open. Rounds with zero
// activity in both kinds are omitted to keep the surface compact.
function CritiqueSummaryView({ run, questions, disagreements }) {
  // Spec 0041 — extend the summary with Issues + Comments alongside
  // Questions + Disagreements. The full Run carries all four lists.
  const issues = Array.isArray(run?.issues) ? run.issues : [];
  const comments = Array.isArray(run?.comments) ? run.comments : [];

  const collect = (pid) => {
    const qs = questions.filter(q => q.phase === pid);
    const ds = disagreements.filter(d => d.phase === pid);
    const is_ = issues.filter(i => i.phase === pid);
    const cs = comments.filter(c => c.phase === pid);
    const rounds = new Set();
    for (const q of qs) {
      if (q.raisedRound) rounds.add(q.raisedRound);
      if (q.answeredRound) rounds.add(q.answeredRound);
    }
    for (const d of ds) {
      if (d.openedRound) rounds.add(d.openedRound);
      if (d.closedRound) rounds.add(d.closedRound);
    }
    for (const i of is_) {
      if (i.roundFirstSeen) rounds.add(i.roundFirstSeen);
      if (i.roundLastSeen) rounds.add(i.roundLastSeen);
    }
    for (const c of cs) {
      if (c.raisedRound) rounds.add(c.raisedRound);
    }
    const rows = Array.from(rounds).sort((a, b) => a - b).map((r) => ({
      round: r,
      iRaised: is_.filter(i => i.roundFirstSeen === r).length,
      iResolved: is_.filter(i =>
        i.status === 'resolved' && i.roundLastSeen === r
      ).length,
      iStillOpen: is_.filter(i =>
        i.roundFirstSeen <= r
        && (i.status === 'open' || i.roundLastSeen > r)
      ).length,
      qRaised: qs.filter(q => q.raisedRound === r).length,
      qAnswered: qs.filter(q => q.answeredRound === r).length,
      qStillOpen: qs.filter(q =>
        q.raisedRound <= r && (q.status === 'open' || (q.answeredRound != null && q.answeredRound > r))
      ).length,
      dRaised: ds.filter(d => d.openedRound === r).length,
      dResolved: ds.filter(d => d.closedRound === r).length,
      dStillOpen: ds.filter(d =>
        (d.openedRound ?? 0) <= r && (d.status === 'open' || (d.closedRound != null && d.closedRound > r))
      ).length,
      cNoted: cs.filter(c => c.raisedRound === r).length,
    }));
    return { qs, ds, is_, cs, rows };
  };
  const p2 = collect(2);
  const p4 = collect(4);

  const renderPhase = (label, phaseInfo) => {
    if (phaseInfo.qs.length === 0 && phaseInfo.ds.length === 0
        && phaseInfo.is_.length === 0 && phaseInfo.cs.length === 0) {
      return (
        <section style={{ marginBottom: 22 }}>
          <h3 style={{
            fontSize: 12, fontWeight: 600, color: 'var(--fg-2)',
            letterSpacing: '0.04em', textTransform: 'uppercase',
            margin: '0 0 8px',
          }}>{label}</h3>
          <div className="mono" style={{
            fontSize: 11.5, color: 'var(--fg-3)',
            padding: '12px 14px',
            background: 'var(--bg-1)',
            border: '1px dashed var(--border-1)',
            borderRadius: 'var(--r-2)',
          }}>
            no critique items were raised in this phase
          </div>
        </section>
      );
    }
    const totalQOpen = phaseInfo.qs.filter(q => q.status === 'open').length;
    const totalQAnswered = phaseInfo.qs.length - totalQOpen;
    const totalDOpen = phaseInfo.ds.filter(d => d.status === 'open').length;
    const totalDResolved = phaseInfo.ds.length - totalDOpen;
    const totalIOpen = phaseInfo.is_.filter(i => i.status === 'open').length;
    const totalIResolved = phaseInfo.is_.length - totalIOpen;
    return (
      <section style={{ marginBottom: 22 }}>
        <h3 style={{
          fontSize: 12, fontWeight: 600, color: 'var(--fg-2)',
          letterSpacing: '0.04em', textTransform: 'uppercase',
          margin: '0 0 8px',
          display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap',
        }}>
          <span>{label}</span>
          <span className="mono" style={{
            fontSize: 10.5, letterSpacing: '0.02em', color: 'var(--fg-3)',
            textTransform: 'none', fontWeight: 400,
          }}>
            {phaseInfo.is_.length > 0 && (
              <>{phaseInfo.is_.length} I ({totalIResolved} resolved · {totalIOpen} open) · </>
            )}
            {phaseInfo.qs.length} Q ({totalQAnswered} answered · {totalQOpen} open) ·{' '}
            {phaseInfo.ds.length} D ({totalDResolved} resolved · {totalDOpen} open)
            {phaseInfo.cs.length > 0 && <> · {phaseInfo.cs.length} C</>}
          </span>
        </h3>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          fontSize: 12, color: 'var(--fg-1)',
          background: 'var(--bg-1)',
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--r-2)',
          overflow: 'hidden',
          fontFamily: 'var(--mono)',
        }}>
          <thead>
            <tr style={{ background: 'var(--bg-2)', textAlign: 'left' }}>
              <th style={_summaryTh}>Round</th>
              <th style={_summaryTh}>I raised</th>
              <th style={_summaryTh}>I resolved</th>
              <th style={_summaryTh}>I still open</th>
              <th style={_summaryTh}>Q raised</th>
              <th style={_summaryTh}>Q answered</th>
              <th style={_summaryTh}>Q still open</th>
              <th style={_summaryTh}>D raised</th>
              <th style={_summaryTh}>D resolved</th>
              <th style={_summaryTh}>D still open</th>
              <th style={_summaryTh}>C noted</th>
            </tr>
          </thead>
          <tbody>
            {phaseInfo.rows.map((r) => (
              <tr key={r.round} style={{ borderTop: '1px solid var(--border-1)' }}>
                <td style={_summaryTd}>R{r.round}</td>
                <td style={_summaryTd}>{r.iRaised || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.iResolved > 0 ? COLORS.ok : 'var(--fg-3)',
                }}>{r.iResolved || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.iStillOpen > 0 ? COLORS.warn : 'var(--fg-3)',
                }}>{r.iStillOpen || '—'}</td>
                <td style={_summaryTd}>{r.qRaised || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.qAnswered > 0 ? COLORS.ok : 'var(--fg-3)',
                }}>{r.qAnswered || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.qStillOpen > 0 ? COLORS.warn : 'var(--fg-3)',
                }}>{r.qStillOpen || '—'}</td>
                <td style={_summaryTd}>{r.dRaised || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.dResolved > 0 ? COLORS.ok : 'var(--fg-3)',
                }}>{r.dResolved || '—'}</td>
                <td style={{
                  ..._summaryTd,
                  color: r.dStillOpen > 0 ? COLORS.warn : 'var(--fg-3)',
                }}>{r.dStillOpen || '—'}</td>
                <td style={_summaryTd}>{r.cNoted || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  };

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--bg-0)' }}>
      <div style={{ padding: '16px 24px 28px' }}>
        <div style={{
          fontSize: 11.5, color: 'var(--fg-3)', lineHeight: 1.55, marginBottom: 16,
        }}>
          Post-mortem aggregate of the critique journey across both phases.
          Click a phase tab above to drill into the individual questions and
          disagreements.
        </div>
        {renderPhase('Phase 2 — Negotiate', p2)}
        {renderPhase('Phase 4 — Review', p4)}
      </div>
    </div>
  );
}

const _summaryTh = {
  padding: '8px 10px',
  fontSize: 10, color: 'var(--fg-3)',
  letterSpacing: '0.06em', textTransform: 'uppercase',
  fontWeight: 600,
};
const _summaryTd = {
  padding: '7px 10px',
  fontSize: 12, color: 'var(--fg-1)',
};

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
      <button onClick={onCardClick}
              title={q.body || ''}
              style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '9px 12px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        {/* Spec 0040 D2 — header row is a single line: type pill,
            one-line truncated body, round + status badges.  Click expands. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span className="mono" style={{
            fontSize: 10, color: COLORS.info, letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'rgba(107,156,240,0.10)',
            border: '1px solid rgba(107,156,240,0.30)',
            flexShrink: 0,
          }}>Q</span>
          <span className="mono" style={{
            fontSize: 10, color: 'var(--fg-3)', flexShrink: 0,
          }}>
            R{q.raisedRound}{isAnswered ? `→R${q.answeredRound}` : ''}
          </span>
          <span style={{
            flex: 1, minWidth: 0,
            fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.4,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {truncateBody(q.body, 70) || '(no body)'}
          </span>
          <span className="mono" style={{
            fontSize: 10, color: 'var(--fg-3)', flexShrink: 0,
          }}>{q.id}</span>
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
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 16, height: 16,
            opacity: open ? 0.6 : hover ? 0.5 : 0.25,
            transition: 'opacity 120ms, transform 120ms',
            color: 'var(--fg-2)',
            transform: open ? 'rotate(90deg)' : 'none',
            flexShrink: 0,
          }}>
            <Icon.Chevron />
          </span>
        </div>
      </button>
      {open && (
        <div style={{
          padding: '10px 14px 14px',
          borderTop: '1px solid var(--border-1)',
          background: 'var(--bg-0)',
          fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.55,
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {/* Spec 0040 D2 — full body lives in the expanded surface so
              the collapsed header can stay a single readable line. */}
          <div style={{
            fontSize: 12.5, color: 'var(--fg-0)', lineHeight: 1.55,
            whiteSpace: 'pre-wrap',
          }}>
            {q.body || '(no body)'}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
          }}>
            <span>raised by {raisedMeta?.name || q.raisedBy} · R{q.raisedRound}</span>
            {isAnswered && (
              <>
                <span>·</span>
                <span>answered by {answerMeta?.name || q.answeredBy} · R{q.answeredRound}</span>
                {q.match === 'positional' && (
                  <span style={{ color: COLORS.warn, opacity: 0.85 }}>· positional match</span>
                )}
              </>
            )}
          </div>
          {q.quote && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>quote:</span>
              <span style={{ fontStyle: 'italic' }}>"{q.quote}"</span>
            </div>
          )}
          {q.after && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>after:</span>
              <span style={{ fontStyle: 'italic' }}>{q.after}</span>
            </div>
          )}
          {isAnswered && q.answerBody && (
            <div style={{ marginTop: 4, paddingTop: 8, borderTop: '1px dashed var(--border-1)' }}>
              <div className="mono" style={{ color: COLORS.ok, fontSize: 10.5, marginBottom: 4 }}>answer</div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{q.answerBody}</div>
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

// Spec 0043 D8 — small ⚠ chip surfacing per-phase drift events. A drift
// is a mismatch between the agents' final self-counter (`OPEN_QUESTIONS:
// N` etc.) and what the system-derived ledger counted for the same
// (phase, kind). Renders nothing when there are no drifts for the
// selected phase. Tooltip lists the per-kind breakdown.
function LedgerDriftChip({ drifts, phaseId }) {
  if (!drifts || drifts.length === 0) return null;
  // Drift turn-keys are shaped `phase{N}_round{R}_summary` (end-of-phase
  // events emitted by the aggregator). Filter to the selected phase.
  const phasePrefix = `phase${phaseId}_`;
  const phaseDrifts = drifts.filter((d) => (d.turnKey || '').startsWith(phasePrefix));
  if (phaseDrifts.length === 0) return null;
  const tooltip = phaseDrifts
    .map((d) => `${d.kind}: agent=${d.agentCount} · ledger=${d.ledgerCount}`)
    .join('\n');
  return (
    <span
      className="mono"
      title={tooltip}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '1px 8px',
        background: 'transparent',
        border: `1px solid ${COLORS.warn}55`,
        borderRadius: 4,
        fontSize: 10.5,
        color: COLORS.warn,
        letterSpacing: '0.02em',
        cursor: 'help',
      }}
    >
      <span>⚠</span>
      <span className="num" style={{ fontWeight: 500 }}>{phaseDrifts.length}</span>
      <span style={{ color: 'var(--fg-3)' }}>drift</span>
    </span>
  );
}

// Spec 0043 D5 — small "ghosted" annotation rendered below a critique
// card's headline when the corresponding ledger entry shows
// `ghostedRounds > 0`. Pulls from `run.phaseLedgers[phaseId]` keyed by
// item id. Renders nothing when the ledger doesn't track the item or
// the entry has no ghost annotations.
function GhostedAnnotation({ run, phaseId, itemId }) {
  const entries = (run && run.phaseLedgers && run.phaseLedgers[phaseId]) || [];
  const entry = entries.find((e) => e.id === itemId);
  if (!entry || !entry.ghostedRounds) return null;
  return (
    <span
      className="mono"
      title={`Open for ${entry.ghostedRounds} round(s) without an explicit addressing signal (no ## Answers to: / Resolved / Substantive disagreements reference). Surface flag, does not block convergence.`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        marginLeft: 8,
        fontSize: 10,
        color: COLORS.warn,
        cursor: 'help',
      }}
    >
      <span>⚠</span>
      <span>ghosted {entry.ghostedRounds}r</span>
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
      <button onClick={onCardClick}
              title={d.point || d.shortLabel || ''}
              style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '9px 12px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        {/* Spec 0040 D2 — single-line header. Expanded surface below
            carries the full point, progression, positions, resolution. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span className="mono" style={{
            fontSize: 10, color: COLORS.warn, letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'rgba(212,160,86,0.10)',
            border: '1px solid rgba(212,160,86,0.30)',
            flexShrink: 0,
          }}>D</span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {roundRange.replace(' · still open', '')}
          </span>
          <span style={{
            flex: 1, minWidth: 0,
            fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.4,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {truncateBody(d.shortLabel || d.point, 70)}
          </span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {exchanges} ex
          </span>
          {statusPill}
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 16, height: 16,
            opacity: open ? 0.6 : hover ? 0.5 : 0.25,
            transition: 'opacity 120ms, transform 120ms',
            color: 'var(--fg-2)',
            transform: open ? 'rotate(90deg)' : 'none',
            flexShrink: 0,
          }}>
            <Icon.Chevron />
          </span>
        </div>
      </button>

      {open && (
        <div style={{
          padding: '14px',
          borderTop: '1px dashed var(--border-1)',
          background: 'var(--bg-0)',
        }}>
          {/* Meta row — restored from the (now-compact) collapsed header. */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            marginBottom: 12,
            fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
          }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              <span style={{ color: 'var(--fg-4)' }}>raised by</span>
              {raisedMeta ? (
                <>
                  <AgentIcon agent={d.raisedBy} size={12} variant="ghost" />
                  <span style={{ color: 'var(--fg-1)' }}>{raisedMeta.name.toLowerCase()}</span>
                </>
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

// Spec 0041 D5 — Phase 4 Issue ledger items have their own card type.
// Same compact-header + expandable-body shape as QuestionCard. The
// left-rail color is the warn-amber issue color (matches the timeline
// chip's "issues" tint). Click flashes the timeline turn-card where
// the issue was first raised.
function IssueCard({ issue, onHighlight }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const isOpen = issue.status === 'open';
  const accentColor = isOpen ? COLORS.warn : COLORS.ok;
  const raisedMeta = AGENT_META[issue.raisedBy];

  const onCardClick = React.useCallback(() => {
    if (onHighlight && issue.raisedTurnKey) {
      onHighlight([issue.raisedTurnKey], 'd');
    }
    setOpen(o => !o);
  }, [issue, onHighlight]);

  const roundLabel = issue.roundFirstSeen === issue.roundLastSeen
    ? `R${issue.roundFirstSeen}`
    : `R${issue.roundFirstSeen}→R${issue.roundLastSeen}`;

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
      }}>
      <button onClick={onCardClick}
              title={issue.body || ''}
              style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '9px 12px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span className="mono" style={{
            fontSize: 10, color: COLORS.warn, letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'rgba(212,160,86,0.10)',
            border: '1px solid rgba(212,160,86,0.30)',
            flexShrink: 0,
          }}>I</span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {roundLabel}
          </span>
          <span style={{
            flex: 1, minWidth: 0,
            fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.4,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {truncateBody(issue.body, 70)}
          </span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {issue.id}
          </span>
          <span className="mono" style={{
            fontSize: 10.5,
            padding: '1px 6px', borderRadius: 999,
            border: `1px solid ${isOpen ? COLORS.warn + '55' : COLORS.ok + '55'}`,
            color: isOpen ? COLORS.warn : COLORS.ok,
            background: isOpen ? 'rgba(212,160,86,0.08)' : 'rgba(111,179,128,0.08)',
            flexShrink: 0,
          }}>
            {isOpen ? 'open' : 'resolved'}
          </span>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 16, height: 16,
            opacity: open ? 0.6 : hover ? 0.5 : 0.25,
            transition: 'opacity 120ms, transform 120ms',
            color: 'var(--fg-2)',
            transform: open ? 'rotate(90deg)' : 'none',
            flexShrink: 0,
          }}>
            <Icon.Chevron />
          </span>
        </div>
      </button>
      {open && (
        <div style={{
          padding: '10px 14px 14px',
          borderTop: '1px solid var(--border-1)',
          background: 'var(--bg-0)',
          fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.55,
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          <div style={{
            fontSize: 12.5, color: 'var(--fg-0)', lineHeight: 1.55,
            whiteSpace: 'pre-wrap',
          }}>
            {issue.body || '(no body)'}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
          }}>
            <span>flagged by {raisedMeta?.name || issue.raisedBy} · first seen R{issue.roundFirstSeen}</span>
            {issue.roundLastSeen !== issue.roundFirstSeen && (
              <>
                <span>·</span>
                <span>last seen R{issue.roundLastSeen}</span>
              </>
            )}
          </div>
          {issue.quote && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>quote:</span>
              <span style={{ fontStyle: 'italic' }}>"{issue.quote}"</span>
            </div>
          )}
          {issue.after && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>after:</span>
              <span style={{ fontStyle: 'italic' }}>{issue.after}</span>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

// Spec 0041 D5 — Comments on the current draft. Non-blocking, no
// closure protocol; always renders as ``noted``. The left-rail is
// neutral grey so it's visually de-prioritised next to issues +
// questions + disagreements.
function CommentCard({ comment, onHighlight }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const raisedMeta = AGENT_META[comment.raisedBy];

  const onCardClick = React.useCallback(() => {
    if (onHighlight && comment.raisedTurnKey) {
      onHighlight([comment.raisedTurnKey], 'd');
    }
    setOpen(o => !o);
  }, [comment, onHighlight]);

  return (
    <article
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        marginBottom: 8,
        background: 'var(--bg-1)',
        border: `1px solid ${open ? 'var(--border-2)' : 'var(--border-1)'}`,
        borderLeft: `3px solid var(--border-3)`,
        borderRadius: 'var(--r-3)',
        overflow: 'hidden',
        transition: 'border-color 120ms',
      }}>
      <button onClick={onCardClick}
              title={comment.body || ''}
              style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '9px 12px',
        background: hover && !open ? 'var(--bg-2)' : 'transparent',
        transition: 'background 120ms',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span className="mono" style={{
            fontSize: 10, color: 'var(--fg-2)', letterSpacing: '0.06em',
            padding: '1px 6px', borderRadius: 4,
            background: 'var(--bg-2)',
            border: '1px solid var(--border-1)',
            flexShrink: 0,
          }}>C</span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            R{comment.raisedRound}
          </span>
          <span style={{
            flex: 1, minWidth: 0,
            fontSize: 12.5, color: 'var(--fg-1)', fontWeight: 500, lineHeight: 1.4,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {truncateBody(comment.body, 70)}
          </span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {comment.id}
          </span>
          <span className="mono" style={{
            fontSize: 10.5,
            padding: '1px 6px', borderRadius: 999,
            border: '1px solid var(--border-1)',
            color: 'var(--fg-3)',
            background: 'var(--bg-2)',
            flexShrink: 0,
          }}>noted</span>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 16, height: 16,
            opacity: open ? 0.6 : hover ? 0.5 : 0.25,
            transition: 'opacity 120ms, transform 120ms',
            color: 'var(--fg-2)',
            transform: open ? 'rotate(90deg)' : 'none',
            flexShrink: 0,
          }}>
            <Icon.Chevron />
          </span>
        </div>
      </button>
      {open && (
        <div style={{
          padding: '10px 14px 14px',
          borderTop: '1px solid var(--border-1)',
          background: 'var(--bg-0)',
          fontSize: 12, color: 'var(--fg-1)', lineHeight: 1.55,
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          <div style={{
            fontSize: 12.5, color: 'var(--fg-0)', lineHeight: 1.55,
            whiteSpace: 'pre-wrap',
          }}>
            {comment.body || '(no body)'}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
          }}>
            <span>noted by {raisedMeta?.name || comment.raisedBy} · R{comment.raisedRound}</span>
          </div>
          {comment.quote && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>quote:</span>
              <span style={{ fontStyle: 'italic' }}>"{comment.quote}"</span>
            </div>
          )}
          {comment.after && (
            <div>
              <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5, marginRight: 6 }}>after:</span>
              <span style={{ fontStyle: 'italic' }}>{comment.after}</span>
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
  // Spec 0034: cross-axis highlight. The CritiqueExplorer dispatches a
  // set of turn-keys here; Timeline forwards them to each ArtifactCard,
  // which applies a 1.5s flash ring. The Map carries the variant
  // (``'q'`` or ``'d'``) so the ring colour matches the source type.
  // Spec 0035: the Conversation/Consumption tab state lifted to
  // RunDetail by spec 0033 is unwound — `Timeline` re-owns its own
  // `tab` state now that the tabs live in the Timeline pane toolbar.
  const [highlightedTurnKeys, setHighlightedTurnKeys] = React.useState(
    () => new Map()
  );
  React.useEffect(() => { setShowErrors(false); }, [run.id, run.phase, run.status]);

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

  // Spec 0038: one fetch of /searches/index?include=summary per run.
  // Provided via context so the chip on every collapsed ArtifactCard,
  // the gist line on every expanded card, and the RunSearchSummary
  // header chip all share the same payload.
  const searchIndex = window.useSearchIndex(run.id);
  const onJumpToFirstSearch = React.useCallback((opts) => {
    // ``opts.warningOnly`` — when true, prefer the first card flagged for
    // an unmatched citation; otherwise the first card with any searches.
    const summary = searchIndex.summary;
    if (!summary) return;
    let targetKey = null;
    if (opts?.warningOnly) {
      for (const [k, v] of summary.entries()) {
        if (v.hasWarning) { targetKey = k; break; }
      }
    }
    if (!targetKey) {
      for (const [k, v] of summary.entries()) {
        if (v.queries > 0) { targetKey = k; break; }
      }
    }
    if (!targetKey) return;
    // Find the DOM card carrying this turn-key and scroll into view.
    const card = document.querySelector(`[data-turn-key="${targetKey}"]`);
    if (card && card.scrollIntoView) {
      card.scrollIntoView({ block: 'center', behavior: 'smooth' });
      if (window.scrollAndFlash) {
        // Fall through to flash if available.
      }
    }
  }, [searchIndex.summary]);

  return (
    <SearchIndexContext.Provider value={searchIndex}>
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
          onJumpToFirstSearch={onJumpToFirstSearch}
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
                highlightedTurnKeys={highlightedTurnKeys}
              />
              <CritiqueExplorer run={run} onHighlightTurns={highlightTurns} />
            </>
          )}
        </main>
        <Footer run={run} />
      </div>
    </SearchIndexContext.Provider>
  );
}

Object.assign(window, { RunDetail });
