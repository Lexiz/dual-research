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

// ─────────────────── Spec 0046 D9 — shared PaneButton ──────────────────────
//
// One uniform toggle/tab/filter button used across every in-pane control
// in the run-detail view:
//   - Critique pane phase buttons (`Phase 2` / `Phase 4` / `Summary`) — D1
//   - Critique pane filter chips (`All` / `Questions` / `Disagreements` /
//     `Claims` / `Issues` / `Comments`) — D2
//   - Timeline pane's `Conversation` / `Consumption` segmented control
//   - Future: any toolbar segmented control on the Critique / Consumption
//     surfaces
//
// Pre-spec each of these had its own border, padding, font, hover/active
// styling. Spec 0046 D9 collapses them onto one component so the eye reads
// the buttons as one design language across the panes.
function PaneButton({
  active, onClick, children, leftAccent,
  size = 'md',         // 'sm' | 'md' — sm is the filter-chip variant
  variant = 'default', // 'default' | 'subtle' — subtle drops the border
                       // for inline segmented use
  title,
  disabled,
}) {
  const [hover, setHover] = React.useState(false);
  const padV = size === 'sm' ? 3 : 5;
  const padH = size === 'sm' ? 10 : 12;
  const fontSize = size === 'sm' ? 11 : 12;
  const borderColor = variant === 'subtle'
    ? 'transparent'
    : (active ? 'var(--border-3)' : 'var(--border-1)');
  const bg = active
    ? 'var(--bg-3)'
    : hover ? 'var(--bg-2)' : (variant === 'subtle' ? 'transparent' : 'var(--bg-1)');
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      title={title}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      disabled={disabled}
      style={{
        appearance: 'none',
        display: 'inline-flex', alignItems: 'center', gap: 6,
        border: `1px solid ${borderColor}`,
        background: bg,
        color: active ? 'var(--fg-0)' : disabled ? 'var(--fg-4)' : 'var(--fg-2)',
        fontSize,
        fontWeight: active ? 600 : 500,
        padding: `${padV}px ${padH}px`,
        borderRadius: 'var(--r-2)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontFamily: 'inherit',
        whiteSpace: 'nowrap',
        transition: 'background 120ms, border-color 120ms, color 120ms',
        boxShadow: active && variant === 'default' ? `inset 0 -2px 0 ${COLORS.info}` : 'none',
        opacity: disabled ? 0.55 : 1,
      }}
    >
      {leftAccent && (
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: leftAccent, flexShrink: 0,
        }} />
      )}
      {children}
    </button>
  );
}

// Spec 0046 D9 — small grouping wrapper that keeps a row of `PaneButton`s
// tightly packed with a single shared gap. Used everywhere we render a
// segmented control (filter chips, phase buttons, etc.).
function PaneButtonGroup({ children, gap = 6 }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap, flexShrink: 0 }}>
      {children}
    </div>
  );
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
      {/* Row 1: topic + cost + reconcile-status + status/errors */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <Topic text={run.topic} />
        <CostBadge cost={total} tokens={totalTokens} searchCost={totalSearchCost} />
        <ReconcileChip run={run} localCost={total} />
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
//
// Spec 0045 D6 — equal-width pills (shared `min-width` via the
// AGENT_PILL_MIN_WIDTH constant below); internal layout is identity
// left-aligned (logo · provider · model), spacer, metrics right-aligned
// (tokens · cost · ● status). The shared min-width is hard-coded for v1
// — sized so the wider of the two model-id strings (Claude's longer one)
// fits comfortably without truncation; v2 can measure dynamically.
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
      title={`${meta.name} · ${modelId} · ${totalTokens.toLocaleString()} tokens · ${cost.toFixed(4)} USD · ${phrase}`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '4px 12px',
        background: 'var(--bg-2)',
        border: `1px solid ${meta.border}`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
        // Spec 0045 D6 — shared min-width turns the two pills into a
        // matched pair; combined with the flex spacer below, identity
        // sits at the left edge and metrics anchor to the right.
        minWidth: AGENT_PILL_MIN_WIDTH,
        flexShrink: 1,
      }}>
      {/* Left zone — identity (logo · provider · model). */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        flexShrink: 0,
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
      </span>
      {/* Spacer — pushes metrics to the right edge. */}
      <span style={{ flex: 1 }} />
      {/* Right zone — metrics (tokens · cost · ● status). */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        flexShrink: 0,
      }}>
        <span className="mono num" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>
          {fmt.tokens(totalTokens)}t
        </span>
        <span style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>·</span>
        <span className="mono num" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>
          {fmt.cost(cost)}
        </span>
        <span style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>·</span>
        <Dot color={dotColor} pulse={live ? 'pulse-a' : null} size={6} />
        <span style={{
          fontSize: 11, color: phraseColor,
          maxWidth: 140,
          overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {phrase}
        </span>
      </span>
    </span>
  );
}

// Spec 0045 D6 — shared min-width for the two timeline-header model
// pills. Hard-coded v1 (≈20% above the wider Claude pill's pre-spec
// width, so identity/metrics breathe at the new alignment); dynamic
// measurement is a v2 follow-up.
const AGENT_PILL_MIN_WIDTH = 480;

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

// ─────────────────── Spec 0048 — Reconcile verification chip ──────────
//
// Reads /api/reconcile/<run's UTC date>. Renders one of five visual
// states based on the report's ``verification_status``:
//
//   verified                → ✓ verified $X.XX
//   drift                   → ⚠ Δ $Y.YY (billed $Z.ZZ)
//   partial                 → local $X.XX · ✓ OpenAI · ⚠ Anthropic missing
//   unverified              → local $X.XX · unverified
//   awaiting_provider_data  → local $X.XX · awaiting provider data
//
// 404 from the endpoint (no reconciliation run yet for that date) ⇒
// "unverified" — the user hasn't asked for verification.
//
// Run id format is ``YYYYMMDD-HHMMSS-<slug>`` (see ``slugify_run_id``
// in the orchestrator); the leading 8 chars give us the UTC date.
function dateFromRunId(runId) {
  if (typeof runId !== 'string' || runId.length < 8) return null;
  const ymd = runId.slice(0, 8);
  if (!/^\d{8}$/.test(ymd)) return null;
  return `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`;
}

function useReconcileReport(runId) {
  const [state, setState] = React.useState({ loading: true, report: null, error: null });
  React.useEffect(() => {
    const date = dateFromRunId(runId);
    if (!date) {
      setState({ loading: false, report: null, error: 'bad-run-id' });
      return;
    }
    let cancelled = false;
    setState({ loading: true, report: null, error: null });
    fetch(`/api/reconcile/${date}`)
      .then((r) => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`http ${r.status}`);
        return r.json();
      })
      .then((report) => {
        if (cancelled) return;
        setState({ loading: false, report, error: null });
      })
      .catch((e) => {
        if (cancelled) return;
        setState({ loading: false, report: null, error: String(e) });
      });
    return () => { cancelled = true; };
  }, [runId]);
  return state;
}

function ReconcileChip({ run, localCost }) {
  const { loading, report, error } = useReconcileReport(run.id);
  const cost = Number(localCost) || 0;

  // Loading: show a quiet placeholder so layout doesn't shift.
  if (loading) {
    return (
      <span className="mono" style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 9px', borderRadius: 999,
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        fontSize: 11, color: 'var(--fg-3)', flexShrink: 0, whiteSpace: 'nowrap',
      }}>checking…</span>
    );
  }

  // No snapshot OR fetch error → render as "unverified" (404 is the
  // common case: the day's reconciliation hasn't run yet).
  if (!report) {
    return (
      <span
        className="mono"
        title={
          error
            ? `Reconciliation endpoint unreachable: ${error}`
            : "No reconciliation snapshot for this date. Run `dual-research reconcile-costs --run <id>` to verify."
        }
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '3px 9px', borderRadius: 999,
          background: 'var(--bg-2)', border: '1px solid var(--border-1)',
          fontSize: 11, color: 'var(--fg-2)', flexShrink: 0, whiteSpace: 'nowrap',
        }}>
        local <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span style={{ color: 'var(--fg-3)' }}>unverified</span>
      </span>
    );
  }

  const status = report.verificationStatus || report.verification_status || 'unverified';
  const totalProvider = Number(report.totalProviderUsd || report.total_provider_usd || 0);
  const totalDelta = Number(report.totalDeltaUsd || report.total_delta_usd || 0);
  const providersChecked = report.providersChecked || report.providers_checked || [];
  const providersSkipped = report.providersSkipped || report.providers_skipped || {};

  const palette = {
    verified:                { glyph: '✓', color: COLORS.ok,   bg: COLORS.ok + '14',   border: COLORS.ok + '55' },
    drift:                   { glyph: '⚠', color: COLORS.warn, bg: COLORS.warn + '14', border: COLORS.warn + '55' },
    partial:                 { glyph: '◐', color: COLORS.info, bg: COLORS.info + '14', border: COLORS.info + '55' },
    unverified:              { glyph: '·', color: 'var(--fg-3)', bg: 'var(--bg-2)', border: 'var(--border-1)' },
    awaiting_provider_data:  { glyph: '⏳', color: COLORS.info, bg: COLORS.info + '0a', border: COLORS.info + '33' },
  };
  const p = palette[status] || palette.unverified;

  const skippedLines = Object.entries(providersSkipped)
    .map(([prov, reason]) => `  • ${prov}: ${reason}`).join('\n');
  const tooltip = (() => {
    const lines = [`Verification: ${status}`];
    if (providersChecked.length) lines.push(`Checked: ${providersChecked.join(', ')}`);
    if (skippedLines) lines.push(`Skipped:\n${skippedLines}`);
    lines.push(`Local: ${cost.toFixed(4)} USD`);
    if (totalProvider > 0) lines.push(`Provider-billed: ${totalProvider.toFixed(4)} USD`);
    if (Math.abs(totalDelta) > 1e-9) {
      lines.push(`Δ: ${totalDelta >= 0 ? '+' : ''}${totalDelta.toFixed(4)} USD`);
    }
    if (report.checkedAt || report.checked_at) {
      lines.push(`Checked at: ${report.checkedAt || report.checked_at}`);
    }
    return lines.join('\n');
  })();

  let body;
  if (status === 'verified') {
    body = (
      <>
        <span style={{ color: p.color }}>{p.glyph}</span>
        <span style={{ color: 'var(--fg-1)' }}>verified</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span className="num">{fmt.cost(cost)}</span>
      </>
    );
  } else if (status === 'drift') {
    body = (
      <>
        <span style={{ color: p.color }}>{p.glyph}</span>
        <span style={{ color: 'var(--fg-1)' }}>Δ</span>
        <span className="num" style={{ color: 'var(--fg-1)' }}>
          {totalDelta >= 0 ? '+' : ''}{fmt.cost(totalDelta)}
        </span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span style={{ color: 'var(--fg-3)' }}>
          billed <span className="num">{fmt.cost(totalProvider)}</span>
        </span>
      </>
    );
  } else if (status === 'partial') {
    body = (
      <>
        <span style={{ color: p.color }}>{p.glyph}</span>
        <span style={{ color: 'var(--fg-2)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        {providersChecked.map((prov) => (
          <span key={prov} style={{ color: COLORS.ok }}>✓ {prov}</span>
        ))}
        {Object.keys(providersSkipped).map((prov) => (
          <span key={prov} style={{ color: COLORS.warn, marginLeft: 4 }}>
            ⚠ {prov}
          </span>
        ))}
      </>
    );
  } else if (status === 'awaiting_provider_data') {
    body = (
      <>
        <span style={{ color: p.color }}>{p.glyph}</span>
        <span style={{ color: 'var(--fg-2)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span style={{ color: 'var(--fg-3)' }}>awaiting provider data</span>
      </>
    );
  } else {
    body = (
      <>
        <span style={{ color: 'var(--fg-2)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span style={{ color: 'var(--fg-3)' }}>unverified</span>
      </>
    );
  }

  return (
    <span
      title={tooltip}
      className="mono"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 9px', borderRadius: 999,
        background: p.bg, border: `1px solid ${p.border}`,
        fontSize: 11, color: 'var(--fg-1)', flexShrink: 0, whiteSpace: 'nowrap',
      }}
    >
      {body}
    </span>
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
  // Spec 0046 D9 — adopts the shared `PaneButton`. Pre-spec this was a
  // pill-shaped segmented control with its own border + padding;
  // converging on `PaneButton` lines the Conversation/Consumption pair
  // up with the Critique pane buttons (D1) + filter chips (D2).
  const tabs = [
    { id: 'conversation', label: 'Conversation' },
    { id: 'consumption',  label: 'Consumption'  },
  ];
  return (
    <PaneButtonGroup>
      {tabs.map((t) => (
        <PaneButton
          key={t.id}
          size={prominent ? 'md' : 'sm'}
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </PaneButton>
      ))}
    </PaneButtonGroup>
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

// Spec 0047 — given an `item.turnKey` from the live timeline
// (snake_case, e.g. `phase4_round1_claude`), check whether the per-turn
// usage dict carries a repair sibling under the camelCase
// `phase4Round1ClaudeRepair` key. Used by `StatsChips` to surface a
// `+repair` hint on the parent timeline turn so the user knows to look
// at the Consumption tab for the breakdown.
function hasRepairSibling(run, snakeTurnKey) {
  if (!snakeTurnKey) return false;
  const usage = run?.phaseTokenUsage;
  if (!usage) return false;
  const camel = snakeTurnKey.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
  return Object.prototype.hasOwnProperty.call(usage, `${camel}Repair`);
}

// Walk the per-turn usage dict and produce ordered rows for rendering.
// Each row: { id, phase, round, label, claude, gpt }. `claude`/`gpt`
// is the `TurnTokenUsage`-shaped value or `null` (silent lane).
// Spec 0047 — small chip surfaced on Consumption-tab repair-sibling rows
// (and on timeline turns whose parent has a repair sibling) to mark the
// row as a protocol-repair re-prompt rather than the original turn.
function RepairChip({ compact = false }) {
  return (
    <span
      className="mono"
      title="Re-prompted turn after the original failed protocol parse — see the matching parent row for the original."
      style={{
        display: 'inline-flex', alignItems: 'center',
        padding: compact ? '0 5px' : '1px 6px',
        background: COLORS.warn + '14',
        border: `1px solid ${COLORS.warn}55`,
        borderRadius: 4,
        fontSize: compact ? 9.5 : 10, color: COLORS.warn,
        letterSpacing: '0.04em', textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}
    >
      repair
    </span>
  );
}

function buildConsumptionRows(run) {
  const usage = run.phaseTokenUsage || {};
  // Parse the camelized keys back into (phase, round, agent, isRepair).
  // Spec 0047: repair siblings (`-repair` / `-hashdrift-repair` turns) are
  // keyed `phase{N}Round{R}{Agent}Repair` server-side; they render as
  // their own row adjacent to the parent on the Consumption tab so each
  // LLM call gets its own card.
  const parsed = [];
  for (const k of Object.keys(usage)) {
    const m = /^phase(\d+)(?:Round(\d+))?(Claude|Gpt)(Repair)?$/.exec(k);
    if (!m) continue;
    parsed.push({
      key: k,
      phase: Number(m[1]),
      round: m[2] ? Number(m[2]) : 0,
      agent: m[3] === 'Gpt' ? 'gpt' : 'claude',
      isRepair: Boolean(m[4]),
    });
  }
  // Group by (phase, round, isRepair). Use a Map keyed `${phase}:${round}:${repairFlag}`
  // to preserve insertion-order; we'll re-sort below.
  const grouped = new Map();
  for (const p of parsed) {
    const k = `${p.phase}:${p.round}:${p.isRepair ? 'r' : ''}`;
    if (!grouped.has(k)) {
      grouped.set(k, {
        phase: p.phase, round: p.round, isRepair: p.isRepair,
        claude: null, gpt: null,
      });
    }
    grouped.get(k)[p.agent] = usage[p.key];
  }
  // Sort by phase, then round, then originals before their repair siblings.
  const rows = Array.from(grouped.values()).sort((a, b) => {
    if (a.phase !== b.phase) return a.phase - b.phase;
    if (a.round !== b.round) return a.round - b.round;
    return Number(a.isRepair) - Number(b.isRepair);
  });
  // Attach human labels.
  for (const r of rows) {
    r.id = `${r.phase}:${r.round}${r.isRepair ? ':repair' : ''}`;
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

// Spec 0048 — per-row provider-billed annotation.
//
// Given the reconcile report (fetched once at ConsumptionView level) +
// a card's (agent, model_id), find the matching ProviderDelta and
// render a small line: "Provider-billed: $X.XX · Δ $Y.YY (Z.Z%)".
// Hidden when no reconcile exists, when this provider wasn't checked,
// or when the row matches nothing in the report.
function ProviderBilledLine({ report, agent, modelId }) {
  if (!report || !modelId) return null;
  const status = report.verificationStatus || report.verification_status;
  if (status === 'unverified') return null;

  const provider = agent === 'claude' ? 'anthropic' : 'openai';
  const deltas = report.perModelDeltas || report.per_model_deltas || [];
  const match = deltas.find(
    (d) => (d.provider === provider) && (d.modelId === modelId || d.model_id === modelId)
  );
  if (!match) return null;

  const providerUsd = Number(match.providerUsd ?? match.provider_usd ?? 0);
  const deltaUsd = Number(match.deltaUsd ?? match.delta_usd ?? 0);
  const deltaPct = Number(match.deltaPct ?? match.delta_pct ?? 0);
  if (providerUsd === 0 && deltaUsd === 0) return null;

  const flagged = Boolean(match.flagged);
  const c = flagged ? COLORS.warn : 'var(--fg-3)';
  return (
    <div className="mono" style={{
      paddingTop: 4, marginTop: 2,
      fontSize: 10.5, color: c,
      display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
    }}>
      <span style={{ color: 'var(--fg-3)' }}>Provider-billed:{' '}
        <span className="num" style={{ color: 'var(--fg-2)' }}>
          {fmt.cost(providerUsd)}
        </span>
      </span>
      <span style={{ color: 'var(--fg-4)' }}>·</span>
      <span style={{ color: c }}>
        Δ <span className="num">{deltaUsd >= 0 ? '+' : ''}{fmt.cost(deltaUsd)}</span>
        {' '}({deltaPct.toFixed(1)}%)
      </span>
      {flagged && (
        <span title="Per-row delta exceeds reconcile tolerance threshold."
              style={{ color: COLORS.warn }}>⚠</span>
      )}
    </div>
  );
}

function ConsumptionView({ run }) {
  const reconcileState = useReconcileReport(run.id);
  const reconcileReport = reconcileState.report;
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
      {/* Spec 0046 D6 — column of single-row cards. Each card carries its
          own top bar (phase + round label + per-agent lane bars) and an
          inline-expanded detail body rendered inside the same card.
          Pre-spec the expand opened a separate full-width grid row below
          the lane row; the eye kept reorienting between the lanes and
          the detail panels. The new card keeps the visual flow linear. */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {rows.map((row, i) => {
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
              reconcileReport={reconcileReport}
            />
          );
        })}
      </div>

      <ConsumptionLegend />
    </div>
  );
}

function ConsumptionRow({ row, run, scale, showPhaseTitle, expanded, onToggle, reconcileReport }) {
  // Spec 0046 D6 — single-row card with inline expand. The entire top
  // bar is one clickable surface; expanded detail renders INSIDE the
  // same card so the width never jumps. Pre-spec the expand-body sat
  // as a separate full-width grid row below; the visual flow kept
  // reorienting left/right between the lanes and the detail.
  // Spec 0047 — repair-sibling rows use a slightly muted background +
  // a `repair` chip in the label cell so they visually cluster with
  // their parent row but stay individually addressable.
  return (
    <article style={{
      background: row.isRepair ? 'var(--bg-0)' : 'var(--bg-1)',
      border: `1px solid ${expanded ? 'var(--border-2)' : 'var(--border-1)'}`,
      borderRadius: 8,
      overflow: 'hidden',
      transition: 'border-color 120ms',
    }}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          appearance: 'none', border: 'none', background: 'transparent',
          width: '100%', textAlign: 'left',
          cursor: 'pointer', fontFamily: 'inherit',
          padding: '12px 14px',
          display: 'grid',
          gridTemplateColumns: '160px 1fr 1fr 24px',
          gap: 14, alignItems: 'center',
        }}>
        {/* Phase + round label cell */}
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 2,
          minHeight: 48,
        }}>
          {showPhaseTitle && (
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--fg-0)' }}>
              {PHASE_NAMES[row.phase] || `Phase ${row.phase}`}
            </div>
          )}
          {row.label && (
            <div className="mono" style={{
              fontSize: 9.5, color: 'var(--fg-3)', letterSpacing: '0.06em',
              textTransform: 'uppercase',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>{row.label}</span>
              {row.isRepair && <RepairChip />}
            </div>
          )}
          {!row.label && row.isRepair && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <RepairChip />
            </div>
          )}
        </div>
        {/* Claude lane */}
        <div>
          <TokenLaneCell usage={row.claude} agent="claude" run={run} scale={scale} />
        </div>
        {/* OpenAI lane */}
        <div>
          <TokenLaneCell usage={row.gpt} agent="gpt" run={run} scale={scale} />
        </div>
        {/* Chevron */}
        <CardChevron open={expanded} hover={false} />
      </button>
      {expanded && (
        <ConsumptionRowExpanded row={row} run={run} scale={scale} reconcileReport={reconcileReport} />
      )}
    </article>
  );
}

// Spec 0046 D6 — per-row expanded body. Now lives INSIDE the parent
// `ConsumptionRow`'s card (no `gridColumn: 1 / 4` escape); the two
// per-agent breakdowns sit side-by-side at the same width as the
// lane bars above. Visual flow stays linear top-to-bottom.
function ConsumptionRowExpanded({ row, run, scale, reconcileReport }) {
  return (
    <div style={{
      padding: '0 14px 14px',
      background: 'var(--bg-1)',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 14,
        alignItems: 'stretch',
        borderTop: '1px dashed var(--border-1)',
        paddingTop: 12,
      }}>
        <ConsumptionCard usage={row.claude} agent="claude" run={run} scale={scale} reconcileReport={reconcileReport} />
        <ConsumptionCard usage={row.gpt}    agent="gpt"    run={run} scale={scale} reconcileReport={reconcileReport} />
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
function ConsumptionCard({ usage, agent, run, scale, reconcileReport }) {
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

  const pctOfCap = ctxWindow > 0 ? (tokensIn / ctxWindow * 100) : 0;

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

      {/* Spec 0046 D7 — the pre-spec "not used in this turn: …" footnote
          is gone. Empty pieces simply don't render; absence is the
          signal (same rule as spec 0045 D3 for the input full-view). */}

      {/* Spec 0046 D8 — costs + counts cluster. Replaces the confusing
          "web searches: N · of which web search: $X" wording (there was
          no parent total for "of which" to refer to). New layout:
              line 1 — Tokens: $A · Web search: $B · Total: $T
              line 2 — Searches: N · Queries: M   (only when present)
          The Web-search column only renders when this turn ran a
          search; comma/dot separators stay consistent with the rest
          of the metrics cluster. */}
      <CostsCluster usage={usage} />

      {/* Spec 0048 — when reconciliation has run for this date and a
          per-model delta matches this (agent, model_id), surface a
          "Provider-billed: $X · Δ $Y (Z%)" line so the user can see
          the gap between local accounting and provider invoice on the
          same card. Hidden when no reconcile snapshot exists or when
          the provider for this agent wasn't checked. */}
      <ProviderBilledLine
        report={reconcileReport}
        agent={agent}
        modelId={usage?.modelId || usage?.model_id}
      />
    </div>
  );
}

// Spec 0046 D8 — clean per-card costs/counts cluster. Renders even on
// turns with zero searches (tokens + total only); the searches line is
// hidden when the turn used no web search.
function CostsCluster({ usage }) {
  const tokenCost = Number(usage?.tokenCost ?? usage?.cost ?? 0) || 0;
  const searchCost = Number(usage?.searchCost) || 0;
  const total = Number(usage?.cost ?? tokenCost) || 0;
  const searches = Number(usage?.searches) || 0;
  const queries  = Number(usage?.searchQueries) || 0;
  const hasSearches = searches > 0 || queries > 0 || searchCost > 0;
  return (
    <div className="mono" style={{
      paddingTop: 6, borderTop: '1px solid var(--border-1)',
      fontSize: 10.5, color: 'var(--fg-3)',
      display: 'flex', flexDirection: 'column', gap: 2,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span>Tokens:{' '}
          <span className="num" style={{ color: 'var(--fg-2)' }}>
            {fmt.cost(tokenCost)}
          </span>
        </span>
        {hasSearches && (
          <>
            <span style={{ color: 'var(--fg-4)' }}>·</span>
            <span>Web search:{' '}
              <span className="num" style={{ color: 'var(--fg-2)' }}>
                {fmt.cost(searchCost)}
              </span>
            </span>
          </>
        )}
        <span style={{ color: 'var(--fg-4)' }}>·</span>
        <span>Total:{' '}
          <span className="num" style={{ color: 'var(--fg-1)', fontWeight: 500 }}>
            {fmt.cost(total)}
          </span>
        </span>
      </div>
      {hasSearches && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span>Searches:{' '}
            <span className="num" style={{ color: 'var(--fg-1)' }}>
              {searches.toLocaleString()}
            </span>
          </span>
          {queries > 0 && (
            <>
              <span style={{ color: 'var(--fg-4)' }}>·</span>
              <span>Queries:{' '}
                <span className="num" style={{ color: 'var(--fg-1)' }}>
                  {queries.toLocaleString()}
                </span>
              </span>
            </>
          )}
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
function PaneHeader({ title, count, left, right, accentGradient, accentColor }) {
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
      gap: 14,
    }}>
      {/* 2px accent at top */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 2, ...accent,
      }} />
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 10,
        minWidth: 0, whiteSpace: 'nowrap', flexShrink: 0,
      }}>
        {/* Spec 0046 D1 — title kept as small chrome (so the pane is
            still labelled) but loses its visual primacy when ``left``
            carries the navigation. */}
        <span style={{
          fontSize: left ? 11.5 : 14,
          fontWeight: left ? 500 : 600,
          color: left ? 'var(--fg-3)' : 'var(--fg-0)',
          letterSpacing: '-0.005em',
        }}>
          {title}
        </span>
        {count != null && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
            {count}
          </span>
        )}
      </div>
      {left && (
        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          {left}
        </div>
      )}
      <span style={{ flex: 1 }} />
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
    // Spec 0044 D7 — when the ledger is wired (spec 0043), pull
    // phase-wide open counts from it so the standing line reflects
    // the system's authoritative view rather than the agent's
    // self-counter. Falls back to the agent counters when the ledger
    // isn't populated (legacy runs / kill-switch).
    const ledgerEntries = (run?.phaseLedgers && run.phaseLedgers[2]) || null;
    if (ledgerEntries) {
      const openCount = (kind) => ledgerEntries.filter(
        (e) => e.kind === kind && e.currentStatus === 'open'
      ).length;
      const openQ = openCount('question');
      const openD = openCount('disagreement');
      const openC = openCount('claim');
      if (openQ > 0) standingParts.push(plur(openQ, 'open question'));
      if (openD > 0) standingParts.push(plur(openD, 'open disagreement'));
      if (openC > 0) standingParts.push(plur(openC, 'open claim'));
    } else {
      if (typeof stats.openQuestions === 'number' && stats.openQuestions > 0) {
        standingParts.push(plur(stats.openQuestions, 'open question'));
      }
      if (typeof stats.blocking === 'number' && stats.blocking > 0) {
        standingParts.push(plur(stats.blocking, 'open disagreement'));
      }
    }
    if (typeof stats.fsd === 'number' && stats.fsd > 0) {
      standingParts.push(`${stats.fsd} final-surfaced`);
    }
    if (standingParts.length > 0) {
      sentences.push(`Standing across the phase: ${standingParts.join(' · ')}.`);
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

    // Spec 0044 D7 — prefer ledger-derived phase-wide open count for
    // the standing line. The legacy `openIssuesNow` reads the agent's
    // self-counter which can drift from the system view (cf. spec 0043
    // drift signal).
    const p4Ledger = (run?.phaseLedgers && run.phaseLedgers[4]) || null;
    if (p4Ledger) {
      const openIssuesLedger = p4Ledger.filter(
        (e) => e.kind === 'issue' && e.currentStatus === 'open'
      ).length;
      if (openIssuesLedger > 0) {
        sentences.push(`${plur(openIssuesLedger, 'issue')} open against the current draft.`);
      } else if (status === 'APPROVED') {
        sentences.push('No open issues across the phase.');
      }
    } else if (openIssuesNow > 0) {
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

// Spec 0044 D3 + D8 — compute per-turn ``+raised  −resolved`` deltas
// per kind, derived from the spec-0043 ledger. ``raised`` counts entries
// whose ``raisedTurnKey`` matches; ``resolved`` walks each entry's
// ``statusHistory`` for non-``open`` transitions whose ``turnKey``
// matches. Returns an object keyed by kind; absent kinds produce zero.
//
// When the ledger isn't available (legacy snapshots without
// ``phaseLedgers``), falls back to the spec-0042 parsed-item arrays
// for the raised-count only (resolved is treated as 0 — without
// transition history we have no signal).
function computeChipDeltas(run, item) {
  const phase = item.statsPhase || 2;
  const turnKey = item.turnKey;
  if (!turnKey) {
    return {
      question: { raised: 0, resolved: 0 },
      disagreement: { raised: 0, resolved: 0 },
      claim: { raised: 0, resolved: 0 },
      issue: { raised: 0, resolved: 0 },
      comment: { raised: 0, resolved: 0 },
    };
  }
  const entries = (run?.phaseLedgers && run.phaseLedgers[phase]) || null;

  if (entries) {
    const raised = (kind) => entries.filter(
      (e) => e.kind === kind && e.raisedTurnKey === turnKey
    ).length;
    const resolved = (kind) => entries.filter((e) => {
      if (e.kind !== kind) return false;
      const hist = e.statusHistory || [];
      return hist.some((t) => t.turnKey === turnKey && t.status !== 'open');
    }).length;
    return {
      question:     { raised: raised('question'),     resolved: resolved('question') },
      disagreement: { raised: raised('disagreement'), resolved: resolved('disagreement') },
      claim:        { raised: raised('claim'),        resolved: resolved('claim') },
      issue:        { raised: raised('issue'),        resolved: resolved('issue') },
      comment:      { raised: raised('comment'),      resolved: 0 },
    };
  }

  // Legacy fallback — parsed-item arrays, raised-count only.
  const filt = (arr) => (arr || []).filter((it) => it.raisedTurnKey === turnKey).length;
  return {
    question:     { raised: filt(run?.questions),     resolved: 0 },
    disagreement: { raised: filt(run?.disagreements), resolved: 0 },
    claim:        { raised: filt(run?.claims),        resolved: 0 },
    issue:        { raised: filt(run?.issues),        resolved: 0 },
    comment:      { raised: filt(run?.comments),      resolved: 0 },
  };
}

// Spec 0044 D2 + D9 — return ``true`` iff this card represents the
// LAST turn of a phase whose ledger has zero open entries (i.e. the
// phase converged cleanly). The chip layer + sentiment composer
// share this decision so they always agree on when to display the
// ``✓ agreed`` / ``✓ approved`` marker.
function isFinalConvergedTurn(item, run) {
  if (!item) return false;
  if (item.kind !== 'turn' && item.kind !== 'turn-live') return false;
  const phase = item.statsPhase;
  if (phase !== 2 && phase !== 4) return false;
  if (!run || !run.phaseTimings) return false;
  if (run.phaseTimings[phase] == null) return false;  // phase not yet exited
  const entries = (run.phaseLedgers && run.phaseLedgers[phase]) || [];
  // Phase 2 convergence considers questions + disagreements + claims;
  // Phase 4 gates on issues. Mirrors orchestrator/convergence semantics.
  const blockingOpen = entries.filter((e) => {
    if (e.currentStatus !== 'open') return false;
    if (phase === 4) return e.kind === 'issue';
    return e.kind === 'question' || e.kind === 'disagreement' || e.kind === 'claim';
  }).length;
  if (blockingOpen > 0) return false;
  // Must be the last round observed in this phase.
  const maxRound = entries.reduce(
    (acc, e) => Math.max(acc, e.raisedRound || 0), 0
  );
  return (item.round || 0) >= maxRound;
}

// Spec 0044 D5 — action-specific right-pane empty-state copy.
// Distinguishes three cases the user reads as the same thing today:
//  (a) zero activity at all — turn was prose-only
//  (b) only-closed — turn productive but no new items
//  (c) raised-but-unanchored — items exist but lack quote/after
//      markers so the side-by-side jump can't fire
function emptyStateCopy(item, run) {
  const deltas = computeChipDeltas(run, item);
  const raisedTotal   = Object.values(deltas).reduce((s, d) => s + d.raised, 0);
  const resolvedTotal = Object.values(deltas).reduce((s, d) => s + d.resolved, 0);

  if (raisedTotal === 0 && resolvedTotal === 0) {
    return (
      'This turn raised no new items and closed no prior ones. ' +
      'Open the document modal from the card header for the full markdown body.'
    );
  }
  if (raisedTotal === 0 && resolvedTotal > 0) {
    const parts = [];
    for (const [kind, d] of Object.entries(deltas)) {
      if (d.resolved > 0) {
        parts.push(`${d.resolved} ${kind}${d.resolved === 1 ? '' : 's'}`);
      }
    }
    return `This turn closed ${parts.join(' + ')} from prior rounds. No new items raised.`;
  }
  // raisedTotal > 0 + items.length == 0 → raised but none anchored.
  return (
    `This turn raised ${raisedTotal} item(s), but none had quote/after anchors for ` +
    'cross-reference. Open the document modal for the inline detail.'
  );
}

// Spec 0044 — kind metadata: chip label glyph + colour tint. The
// chip strip omits any kind with both raised=0 and resolved=0 so
// quiet turns stay sparse.
const CHIP_KIND_META = {
  question:     { label: 'Q',  tint: 'info' },
  disagreement: { label: 'D',  tint: 'warn' },
  claim:        { label: 'Cl', tint: 'info' },
  issue:        { label: 'I',  tint: 'warn' },
  comment:      { label: 'C',  tint: 'info' },
};

// Spec 0042 D5 + Spec 0044 D1 — per-phase chip allowlist. The
// ``negotiating`` / ``reviewing`` status pill is no longer rendered
// per-turn (Spec 0044 D1) — the phase-section header already labels
// the phase.
function StatsChips({ phase, run, item }) {
  const allowed = PHASE_CHIP_ALLOWLIST[phase] || [];
  // Spec 0047 — discoverability hint when this turn has a `_repair`
  // sibling on the wire; user knows to look at the Consumption tab for
  // the per-call breakdown.
  const showRepairHint = hasRepairSibling(run, item?.turnKey);
  if (allowed.length === 0 && !isFinalConvergedTurn(item, run) && !showRepairHint) return null;

  const deltas = computeChipDeltas(run, item);
  const chips = [];

  for (const allowedKey of allowed) {
    // ``allowed`` uses plurals (``questions``); deltas keyed by singular.
    const kind = allowedKey === 'questions' ? 'question'
              : allowedKey === 'disagreements' ? 'disagreement'
              : allowedKey === 'claims' ? 'claim'
              : allowedKey === 'issues' ? 'issue'
              : allowedKey === 'comments' ? 'comment'
              : null;
    if (!kind) continue;
    const d = deltas[kind];
    if (!d || (d.raised === 0 && d.resolved === 0)) continue;
    chips.push({ kind, ...CHIP_KIND_META[kind], raised: d.raised, resolved: d.resolved });
  }

  // Spec 0044 D2 — ``✓ agreed`` / ``✓ approved`` only on the LAST
  // turn of a phase that converged with zero open ledger items.
  const showAgreed = isFinalConvergedTurn(item, run);

  if (chips.length === 0 && !showAgreed && !showRepairHint) return null;

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
      {chips.map((c, i) => <StatChip key={i} {...c} />)}
      {showAgreed && <ConvergedChip phase={phase} />}
      {showRepairHint && <RepairChip compact />}
    </span>
  );
}

// Spec 0044 D3 — chip displaying ``+raised  −resolved`` per kind.
// Cases:
//   raised > 0, resolved == 0   → ``+5 Q``        (info/warn tint)
//   raised == 0, resolved > 0   → ``−3 prior Q``  (ok tint, "closed-only")
//   raised > 0, resolved > 0    → ``+5 Q  −1``    (info/warn tint, "+raised  −resolved")
function StatChip({ label, raised, resolved, tint }) {
  const colorMap = { ok: COLORS.ok, info: COLORS.info, warn: COLORS.warn, err: COLORS.err };
  const isClosedOnly = raised === 0 && resolved > 0;
  const c = isClosedOnly ? COLORS.ok : (colorMap[tint] || 'var(--fg-3)');
  const tooltip = isClosedOnly
    ? `Closed ${resolved} prior ${label}${resolved === 1 ? '' : 's'} this turn.`
    : raised > 0 && resolved > 0
      ? `Raised ${raised}, closed ${resolved} prior ${label}${raised === 1 ? '' : 's'} this turn.`
      : `Raised ${raised} ${label}${raised === 1 ? '' : 's'} this turn.`;
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
      {isClosedOnly ? (
        <>
          <span className="num" style={{ color: COLORS.ok, fontWeight: 500 }}>−{resolved} prior</span>
          <span style={{ color: 'var(--fg-3)' }}>{label}</span>
        </>
      ) : (
        <>
          <span className="num" style={{ color: c, fontWeight: 500 }}>+{raised}</span>
          <span style={{ color: 'var(--fg-3)' }}>{label}</span>
          {resolved > 0 && (
            <span className="num" style={{ color: COLORS.ok, fontWeight: 500, marginLeft: 2 }}>
              −{resolved}
            </span>
          )}
        </>
      )}
    </span>
  );
}

// Spec 0044 D2 — Phase-converged marker. Renders as `✓ agreed` for
// Phase 2 / `✓ approved` for Phase 4. Only shown by ``StatsChips``
// when ``isFinalConvergedTurn`` returns true.
function ConvergedChip({ phase }) {
  const label = phase === 4 ? 'approved' : 'agreed';
  return (
    <span className="mono"
          title="Phase converged with zero open ledger items."
          style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '1px 8px',
      background: 'transparent',
      border: `1px solid ${COLORS.ok}55`,
      borderRadius: 4,
      fontSize: 10.5, color: COLORS.ok,
      letterSpacing: '0.02em',
      fontWeight: 500,
    }}>
      <span>✓</span>
      <span>{label}</span>
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
        {meta && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>by {meta.name}</span>
        )}
        <span style={{ flex: 1 }} />
      </div>
    );
  }
  if (item.kind === 'doc-live') {
    if (!meta) return null;
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
          phase={item.statsPhase}
          run={run}
          item={item}
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

// ─────────────────── Spec 0045 — canonical tab order + hide-empty helpers ───
//
// D1 — every full-view modal builds its tabs list, then sorts by this
// index. Tabs whose `id` isn't in the canon keep their author-declared
// order at the end (no tab ever silently disappears just because its
// id was misspelled).
//
// D2 — modals filter falsy entries out of their tabs list BEFORE
// passing into `sortByCanon`, so a tab whose content is empty simply
// isn't rendered. Absence is the signal.
const TABS_CANON = ['content', 'input', 'webSearch', 'sources', 'files'];
function sortByCanon(tabs) {
  return [...tabs].sort((a, b) => {
    const ia = TABS_CANON.indexOf(a.id);
    const ib = TABS_CANON.indexOf(b.id);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

// Spec 0045 D2 helper — returns true when the per-turn web-search
// summary records at least one query or consulted source. Hallucination
// flags alone don't qualify (there's nothing for the tab to render
// without an event).
function hasWebSearchData(summary, turnKey) {
  if (!summary || !turnKey) return false;
  const s = summary.get(turnKey);
  if (!s) return false;
  return (s.queries || 0) > 0 || (s.consulted || 0) > 0;
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
  // Spec 0045 D1+D2: tabs render in canonical order; empty tabs are
  // hidden entirely (Input absent → no `inputs/<key>.json`; Web Search
  // absent → summary has no queries/consulted for this turn).
  const webSearch = useWebSearchTab(item.turnKey);
  const tabs = sortByCanon([
    {
      id: 'content',
      label: 'Content',
      content: <LazyMarkdownBody filePath={item.filePath} />,
    },
    item.turnKey && {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={item.turnKey} />,
    },
    webSearch,
  ].filter(Boolean));
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
// Spec 0045 D2 — returns ``null`` when this turn ran no searches /
// retrieved no sources; callers ``.filter(Boolean)`` the result so the
// tab simply isn't rendered (count was never in the label, only the
// hallucination ⚠ exception of D8 carries through).
function useWebSearchTab(turnKey) {
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  if (!hasWebSearchData(summary, turnKey)) return null;
  const s = summary.get(turnKey);
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
        // Spec 0045 D5 — equal-width panes; both columns now read as
        // parallel surfaces (was 1.5fr / 1fr, biased toward the left).
        gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
        gap: 18,
        minHeight: 0,
        height: '100%',
      }}>
        {/* Left: prior content + Input sub-tab (spec 0033).
            Spec 0044 D4: ``docTabs`` exposes the per-turn document
            context (other's prior turn / other's draft / brief / your
            draft / current converged draft). */}
        <NegotiateLeftPane
          item={item}
          otherAgent={otherAgent}
          priorFilePath={priorFilePath}
          docTabs={leftPaneTabsFor(item, otherAgent, run)}
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
              {/* Spec 0044 D5 — action-specific empty-state copy. */}
              {emptyStateCopy(item, run)}
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
function NegotiateLeftPane({ item, otherAgent, priorFilePath, docTabs, leftRef }) {
  const [sub, setSub] = React.useState('original');
  // Spec 0044 D4 — when in "Original" sub-mode, track which document
  // the user has selected. Defaults to the first docTabs entry
  // (= the "thing being responded to" per phase). Note: clicking a
  // right-pane review item still anchors against ``priorFilePath`` —
  // jump-against-active-tab is a future enhancement (see spec 0044
  // Risks).
  const fallbackDocs = docTabs && docTabs.length > 0
    ? docTabs
    : [{ id: 'fallback', label: 'Original', path: priorFilePath }];
  const [docId, setDocId] = React.useState(fallbackDocs[0].id);
  const activeDoc = fallbackDocs.find((d) => d.id === docId) || fallbackDocs[0];

  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  const hasWarning = !!(item.turnKey && summary && summary.get(item.turnKey)?.hasWarning);
  // Spec 0045 D2 — hide the Web Search sub-tab when this turn did no
  // searches. The hallucination ⚠ exception (D8) is moot in that case.
  const hasSearch = hasWebSearchData(summary, item.turnKey);
  // If the user had Web Search selected and the data disappears (e.g.
  // hot-reload), reset back to Original so we don't render an orphan
  // empty pane.
  React.useEffect(() => {
    if (sub === 'webSearch' && !hasSearch) setSub('original');
  }, [sub, hasSearch]);

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
        <NegotiateLeftSubTabs
          active={sub}
          onChange={setSub}
          hasSearchWarning={hasWarning}
          showWebSearch={hasSearch}
        />
        <span style={{ flex: 1 }} />
        {sub === 'original' && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
            {activeDoc.path || '— no document available —'}
          </span>
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
      {/* Spec 0044 D4 — document strip: one chip per document the
          agent had as input for this turn. Only rendered in the
          "Original" sub-mode (Input / Web Search are per-turn). */}
      {sub === 'original' && fallbackDocs.length > 1 && (
        <div style={{
          padding: '6px 12px',
          borderBottom: '1px solid var(--border-1)',
          background: 'var(--bg-1)',
          display: 'flex', alignItems: 'center', gap: 6,
          flexShrink: 0, overflow: 'auto',
        }}>
          <NegotiateDocTabs tabs={fallbackDocs} active={activeDoc.id} onChange={setDocId} />
        </div>
      )}
      <div ref={leftRef} style={{
        flex: 1, minHeight: 0, overflow: 'auto',
        padding: '14px 16px',
      }}>
        {sub === 'original' && <LazyMarkdownBody filePath={activeDoc.path} />}
        {sub === 'input' && <InputTabContent turnKey={item.turnKey} />}
        {sub === 'webSearch' && <WebSearchTabContent turnKey={item.turnKey} />}
      </div>
    </div>
  );
}

// Spec 0044 D4 — small horizontal chip strip naming each document
// the agent had as input. Active chip is highlighted; click switches
// the left-pane content.
function NegotiateDocTabs({ tabs, active, onChange }) {
  return (
    <>
      {tabs.map((t) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            title={t.path || ''}
            style={{
              appearance: 'none',
              border: `1px solid ${isActive ? 'var(--border-3)' : 'var(--border-1)'}`,
              background: isActive ? 'var(--bg-3)' : 'var(--bg-0)',
              color: isActive ? 'var(--fg-0)' : 'var(--fg-2)',
              fontSize: 11,
              fontWeight: isActive ? 600 : 500,
              padding: '3px 10px',
              borderRadius: 999,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </>
  );
}

function NegotiateLeftSubTabs({ active, onChange, hasSearchWarning, showWebSearch }) {
  // Spec 0045 D1+D2 — declared in canonical order
  // (Original ≡ Content slot, then Input, then Web Search); the Web
  // Search sub-tab only renders when the turn actually has search data
  // (the ⚠ hallucination badge of D8 still shows when present).
  const tabs = [
    { id: 'original',  label: 'Original' },
    { id: 'input',     label: 'Input' },
    showWebSearch && { id: 'webSearch', label: 'Web Search',
                       badge: hasSearchWarning ? '⚠' : null },
  ].filter(Boolean);
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

  // Spec 0044 D6 — structured items (Phase 1 claims + open questions
  // extracted by spec 0042 D1) get clickable cards that jump-to-brief
  // on the left pane. Anchors flow from each item's ``quote`` / ``after``
  // / ``blockId`` to ``scrollAndFlash`` on the left pane's brief view.
  const items = reviewItemsFor(run, item);
  const onItemClick = React.useCallback((it) => {
    if (!leftRef.current || sub !== 'original') return;
    if (it.blockId) {
      const node = leftRef.current.querySelector(`#${it.blockId}`);
      if (node) {
        node.scrollIntoView({ block: 'start', behavior: 'smooth' });
        const tx = (node.textContent || '').trim().slice(0, 80);
        if (tx && window.scrollAndFlash) window.scrollAndFlash(leftRef.current, { text: tx });
        return;
      }
    }
    if (it.after && window.scrollAndFlash) {
      window.scrollAndFlash(leftRef.current, { afterHeading: it.after });
      return;
    }
    if (it.quote && window.scrollAndFlash) {
      window.scrollAndFlash(leftRef.current, { text: it.quote });
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
        // Spec 0045 D5 — equal-width panes (was 1fr / 1.3fr, biased
        // toward the draft on the right).
        gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
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
            draft turn's audit bundle without changing the modal frame.
            Spec 0044 D6: structured items strip lets the user click
            into each Phase 1 claim/question and jump-to-brief. */}
        <DraftRightPane
          filePath={item.filePath}
          turnKey={item.turnKey}
          onSectionClick={onSectionAnchorClick}
          items={items}
          onItemClick={onItemClick}
        />
      </div>
    </Modal>
  );
}

function DraftRightPane({ filePath, turnKey, onSectionClick, items, onItemClick }) {
  const { body, loading } = window.useFileBody(filePath);
  const containerRef = React.useRef(null);
  const [sub, setSub] = React.useState('draft');
  const ctx = React.useContext(SearchIndexContext);
  const summary = ctx?.summary;
  const hasWarning = !!(turnKey && summary && summary.get(turnKey)?.hasWarning);
  // Spec 0045 D2 — Web Search sub-tab is hidden when this draft turn
  // ran no searches. Reset selection if it disappears while open.
  const hasSearch = hasWebSearchData(summary, turnKey);
  React.useEffect(() => {
    if (sub === 'webSearch' && !hasSearch) setSub('draft');
  }, [sub, hasSearch]);
  const anchoredItems = (items || []).filter((it) => it.quote || it.after || it.blockId);

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
        <DraftRightSubTabs
          active={sub}
          onChange={setSub}
          hasSearchWarning={hasWarning}
          showWebSearch={hasSearch}
        />
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
          {sub === 'draft'
            ? (filePath || '—')
            : `searches/${turnKey || '—'}.json`}
        </span>
      </div>
      {sub === 'draft' && anchoredItems.length > 0 && (
        <Phase1ItemStrip items={anchoredItems} onItemClick={onItemClick} />
      )}
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

function DraftRightSubTabs({ active, onChange, hasSearchWarning, showWebSearch }) {
  // Spec 0045 D2 — hide the Web Search sub-tab when the draft turn
  // had no searches.
  const tabs = [
    { id: 'draft',     label: 'Draft' },
    showWebSearch && { id: 'webSearch', label: 'Web Search',
                       badge: hasSearchWarning ? '⚠' : null },
  ].filter(Boolean);
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

// Spec 0044 D6 — compact strip of structured Phase 1 items (claims +
// open questions) above the draft body. Each chip click jumps the
// left-pane brief to the item's anchored block. Hidden when no
// anchored items exist (turns rendering this strip only on drafts
// the agent actually anchored).
function Phase1ItemStrip({ items, onItemClick }) {
  return (
    <div style={{
      padding: '6px 12px',
      borderBottom: '1px solid var(--border-1)',
      background: 'var(--bg-1)',
      display: 'flex', alignItems: 'center', gap: 6,
      flexShrink: 0, overflow: 'auto',
    }}>
      <span className="mono" style={{
        fontSize: 10, color: 'var(--fg-3)',
        letterSpacing: '0.06em', textTransform: 'uppercase',
        flexShrink: 0,
      }}>
        Items ({items.length}) →
      </span>
      {items.map((it, i) => {
        const tint = it.kind === 'claim' ? COLORS.info
                   : it.kind === 'question' ? COLORS.info
                   : COLORS.warn;
        const glyph = it.kind === 'claim' ? 'Cl'
                    : it.kind === 'question' ? 'Q'
                    : it.kind.slice(0, 1).toUpperCase();
        return (
          <button
            key={i}
            type="button"
            onClick={() => onItemClick && onItemClick(it)}
            title={(it.body || '').slice(0, 200)}
            style={{
              appearance: 'none',
              border: `1px solid ${tint}55`,
              background: 'var(--bg-0)',
              color: tint,
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 999,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontFamily: 'inherit',
              maxWidth: 240,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: 'inline-flex', alignItems: 'center', gap: 4,
            }}
          >
            <span className="mono num" style={{ fontWeight: 600 }}>{glyph}-{i + 1}</span>
            <span style={{
              color: 'var(--fg-2)',
              overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 180,
            }}>
              {(it.body || '').replace(/[*`]/g, '').slice(0, 60)}
            </span>
            <span style={{ color: 'var(--fg-3)', fontSize: 10 }}>↗</span>
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

// Spec 0044 D4 — phase-aware list of document tabs for the
// side-by-side modal's left pane. Each tab is a document the agent
// had as input for that turn (or a contextual reference like the
// brief). The default tab — first entry — is the most-likely-relevant
// "thing being responded to": other's prior turn for P2 R≥2, other's
// draft for P2 R1, current converged draft for P4.
//
// Returns: list of ``{id, label, path}``. Empty list signals no
// document context (caller falls back to the legacy ``priorFilePath``
// rendering).
function leftPaneTabsFor(item, otherUiAgent, run) {
  const phase = item.statsPhase || 2;
  const otherBe = otherUiAgent === 'gpt' ? 'openai' : otherUiAgent;
  const ownBe   = otherBe === 'openai' ? 'claude' : 'openai';
  const round   = Number(item.round) || 1;

  if (phase === 4) {
    const tabs = [];
    if (run?.currentDraftPath) {
      tabs.push({ id: 'current', label: 'Current draft', path: run.currentDraftPath });
    }
    if (round >= 2) {
      const rr = String(round - 1).padStart(2, '0');
      tabs.push({ id: 'priorTurn', label: "Other's prior turn",
                  path: `phase4/round-${rr}-${otherBe}.md` });
    }
    tabs.push({ id: 'brief', label: 'Brief', path: 'brief.md' });
    return tabs;
  }

  if (phase === 1) {
    // Phase 1 plan-draft modal — only input is the brief.
    return [{ id: 'brief', label: 'Brief', path: 'brief.md' }];
  }

  // Phase 2 — default tab is what's being responded to.
  const tabs = [];
  if (round >= 2) {
    const rr = String(round - 1).padStart(2, '0');
    tabs.push({ id: 'priorTurn', label: "Other's prior turn",
                path: `phase2/round-${rr}-${otherBe}.md` });
  }
  tabs.push({ id: 'otherDraft', label: "Other's draft",
              path: `phase1/draft-${otherBe}.md` });
  tabs.push({ id: 'brief', label: 'Brief', path: 'brief.md' });
  tabs.push({ id: 'ownDraft', label: 'Your draft',
              path: `phase1/draft-${ownBe}.md` });
  return tabs;
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
//
// Spec 0045 D4 — the brief IS the user-supplied research prompt for the
// run (today's CLI has no separate ``--prompt`` argument). Labelled
// "User prompt: Brief" to make that role legible; if a future spec
// adds a distinct prompt field, this label re-points to it.
const INPUT_PIECE_LABEL = {
  system: 'System prompt',
  brief:  'User prompt: Brief',
  d1:     "Claude's Phase 1 draft",
  d2:     "GPT's Phase 1 draft",
  plan:   'Agreed plan',
  hist:   'Prior Phase 2 turns',
  draft:  'Current draft',
  histp:  'Prior Phase 4 review turns',
};

// Spec 0045 D4 — `brief` floats to the top (it's always the most-relevant
// input piece). Then the system template, then the rest in canonical
// content order. Mirrors ``protocol/prompts.py::INPUT_BUNDLE_KEY_ORDER``
// with `brief` re-promoted above `system`.
const INPUT_PIECE_ORDER = ['brief', 'system', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'];

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
  // Spec 0045 D3 — render only the pieces the turn actually used. The
  // wire bundle (per `protocol/prompts.py`) carries empty strings for
  // pieces a turn didn't inline; absent pieces don't render at all
  // here. The "not used in this turn" footer is gone — absence is the
  // signal. System template is always informational and renders when
  // present.
  const renderKeys = INPUT_PIECE_ORDER
    .filter((k) => k in pieces && pieces[k])
    .concat(Object.keys(pieces).filter((k) => !INPUT_PIECE_ORDER.includes(k) && pieces[k]));

  if (renderKeys.length === 0) {
    return <InputEmptyState label="This turn's input bundle is empty." />;
  }

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
  // Spec 0045 D3 — InputTabContent filters out empty pieces upstream,
  // so the "(not used in this turn)" branch this section used to render
  // is gone (the section itself wouldn't have been built).
  const [open, setOpen] = React.useState(!defaultCollapsed);
  const label = INPUT_PIECE_LABEL[piece] || piece;
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
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
          {chars.toLocaleString()} chars · ~{approxTokens.toLocaleString()}t
        </span>
      </button>
      {open && (
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
  // Spec 0045 D7 — canonicalised on the same `sources`/`files` ids
  // every full-view modal uses; D2 hides whichever bucket is empty.
  const fileKinds = new Set(['image', 'pdf', 'file']);
  const sources = (attachments || []).filter((a) => a.kind === 'link');
  const files = (attachments || []).filter((a) => fileKinds.has(a.kind));

  // Spec 0045 D1+D2+D8 — canonical order, hide empties, drop counts
  // from tab labels (the body header carries the count instead).
  const tabs = sortByCanon([
    {
      id: 'content',
      label: 'Content',
      content: <PreflightContentTab item={item} />,
    },
    {
      id: 'input',
      label: 'Input',
      content: <InputTabContent turnKey={item.turnKey || 'input'} />,
    },
    sources.length > 0 && {
      id: 'sources',
      label: 'Sources',
      content: <PreflightSourcesTab sources={sources} loading={loading} />,
    },
    files.length > 0 && {
      id: 'files',
      label: 'Files',
      content: <PreflightFilesTab files={files} loading={loading} runId={run.id} />,
    },
  ].filter(Boolean));

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
  // Spec 0045 D1+D2 — canonical tab order; hide Web Search when the
  // critique didn't actually search.
  const webSearch = useWebSearchTab(turnKey);
  const tabs = sortByCanon([
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
  ].filter(Boolean));
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
  // Spec 0046 D2 — when the user switches phase, reset to ``all`` if the
  // previous filter isn't in the new phase's allowlist. Without this an
  // ``issues`` selection persists into Phase 2 and quietly renders no
  // matching cards.
  React.useEffect(() => {
    if (typeFilter === 'all') return;
    const allowed = PHASE_CHIP_ALLOWLIST[selectedPhase] || [];
    if (!allowed.includes(typeFilter)) setTypeFilter('all');
  }, [selectedPhase, typeFilter]);
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
      {/* Spec 0046 D1 — header rewrite. Three primary buttons on the
          left (Phase 2 / Phase 4 / Summary) ARE the navigation; the
          count cluster is right-aligned. Drop the "Critique · 99
          introduced" lead so the buttons sit at the visual anchor of
          the pane. The small "Critique" label stays as PaneHeader's
          title so the pane is still labelled. */}
      <PaneHeader
        title="Critique"
        accentColor={COLORS.info}
        left={
          <PaneButtonGroup>
            {tabs.map((t) => {
              const pInfo = t;
              const counts = phaseCountLabel(pInfo);
              return (
                <PaneButton
                  key={t.pid}
                  active={selectedPhase === t.pid}
                  onClick={() => setSelectedPhase(t.pid)}
                  leftAccent={t.active ? COLORS.info : null}
                  title={t.pending ? 'Phase has not started yet' : null}
                >
                  <span className="mono" style={{
                    fontSize: 10.5, letterSpacing: '0.06em',
                    textTransform: 'uppercase', color: 'var(--fg-3)',
                  }}>
                    Phase&nbsp;{t.pid}
                  </span>
                  <span>{t.label}</span>
                  {counts && (
                    <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
                      · {counts}
                    </span>
                  )}
                </PaneButton>
              );
            })}
            {isTerminal && (
              <PaneButton
                active={selectedPhase === 'summary'}
                onClick={() => setSelectedPhase('summary')}
              >
                <span style={{ marginRight: 2 }}>∑</span>
                <span>Summary</span>
              </PaneButton>
            )}
          </PaneButtonGroup>
        }
        right={
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <SmallStat label="introduced" value={totalIntroduced} color={totalIntroduced > 0 ? 'var(--fg-1)' : 'var(--fg-3)'} />
            <SmallStat label="open"       value={totalOpen}       color={totalOpen > 0 ? COLORS.warn : 'var(--fg-3)'} />
            <SmallStat label="resolved"   value={totalResolved}   color={totalResolved > 0 ? COLORS.ok : 'var(--fg-3)'} />
            <LedgerDriftChip drifts={run.drifts} phaseId={selectedPhase} />
          </span>
        }
      />
      {!isSummary && (
        <PaneToolbar>
          <CritiqueTypeFilter
            active={typeFilter}
            onChange={setTypeFilter}
            phaseId={selectedPhase}
          />
        </PaneToolbar>
      )}
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

// Spec 0046 D1 — phase-button count label, kept concise so the button
// stays a tight chip. Format mirrors the pre-spec `Phase 2 Negotiate ·
// 26 Q · 10 D` glyph cluster but only includes kinds that fired.
function phaseCountLabel(p) {
  if (p.pending) return 'pending';
  const parts = [];
  if (p.iTotal > 0) parts.push(`${p.iTotal} I`);
  if (p.qTotal > 0) parts.push(`${p.qTotal} Q`);
  if (p.dTotal > 0) parts.push(`${p.dTotal} D`);
  if (p.cTotal > 0) parts.push(`${p.cTotal} C`);
  return parts.length ? parts.join(' · ') : 'no items';
}

// Keep the old export name as an alias for backwards-compat in case any
// other module references it (no external links to break, but defensive).
const DisagreementExplorer = CritiqueExplorer;

// Spec 0046 D2 — per-phase context-aware filter chips. The Phase 2
// negotiation surface never has Issues; Phase 4 review never has Claims.
// Pre-spec the filter strip rendered all five kinds regardless of which
// phase tab was active; spec 0046 drops the kinds the phase doesn't
// emit so the user only sees filters that can actually match.
const FILTER_KIND_LABEL = {
  claims: 'Claims',
  questions: 'Questions',
  disagreements: 'Disagreements',
  issues: 'Issues',
  comments: 'Comments',
};
function filterChipsFor(phaseId) {
  if (phaseId === 'summary') return [];
  const allowed = PHASE_CHIP_ALLOWLIST[phaseId] || [];
  if (allowed.length === 0) return [];
  return [
    { id: 'all', label: 'All' },
    ...allowed.map((k) => ({ id: k, label: FILTER_KIND_LABEL[k] || k })),
  ];
}
function CritiqueTypeFilter({ active, onChange, phaseId }) {
  // Spec 0046 D2 + D9 — adopts the shared `PaneButton`. The pre-spec
  // pill-segmented control is gone; chips read as a row of buttons
  // that match the phase-button design language.
  const items = filterChipsFor(phaseId);
  if (items.length === 0) return null;
  return (
    <PaneButtonGroup>
      {items.map((t) => (
        <PaneButton
          key={t.id}
          size="sm"
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </PaneButton>
      ))}
    </PaneButtonGroup>
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
      case 'q': return <QuestionCard     key={item.id} q={item}        onHighlight={onHighlight} run={run} />;
      case 'd': return <DisagreementCard key={item.id} d={item}        onHighlight={onHighlight} run={run} />;
      case 'i': return <IssueCard        key={item.id} issue={item}    onHighlight={onHighlight} run={run} />;
      case 'c': return <CommentCard      key={item.id} comment={item}  onHighlight={onHighlight} run={run} />;
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

// Spec 0046 D5 — Summary view, redesigned as per-round × per-model
// breakdown. Each phase section shows one table per kind the phase
// actually emits (Phase 2 → Question / Disagreement / Claim; Phase 4 →
// Issue / Comment); empty kinds are excluded entirely. Columns are
// `Round` / `Claude raised` / `Claude resolved` / `GPT raised` /
// `GPT resolved` / `Open`. Pre-spec the table rendered ten columns
// (I/Q/D × raised/resolved/open + C noted) with most cells empty;
// the user's complaint was "most of this table is empty, and models
// are not there." Per-kind tables drop the empty columns; the
// per-model split surfaces who carried what.
//
// Helpers below shape each item kind into a uniform `{ round, raisedBy,
// closedRound, closedBy, isOpen }` envelope so one ``buildKindRows``
// function builds every table.
function _envelopesForKind(kind, items) {
  return items.map((it) => {
    switch (kind) {
      case 'question':
        return {
          raisedRound: it.raisedRound,
          raisedBy: it.raisedBy,
          closedRound: it.answeredRound,
          closedBy: it.answeredBy,
          isOpen: it.status === 'open',
        };
      case 'disagreement':
        return {
          raisedRound: it.openedRound,
          // Disagreements with ``raisedBy === 'both'`` count toward
          // both lanes; surface as a third bucket so the per-model
          // column is honest about co-raisers.
          raisedBy: it.raisedBy === 'both' ? 'both' : it.raisedBy,
          closedRound: it.closedRound,
          // ``status`` is ``resolved-claude``/``resolved-gpt``/``resolved-both``
          // — the closer is the side that yielded.
          closedBy: (it.status || '').startsWith('resolved-')
            ? (it.status.split('-')[1] === 'gpt' ? 'gpt'
              : it.status.split('-')[1] === 'claude' ? 'claude'
              : 'both')
            : null,
          isOpen: it.status === 'open',
        };
      case 'claim':
        return {
          raisedRound: it.raisedRound || 1,
          raisedBy: it.raisedBy,
          closedRound: null,
          closedBy: null,
          isOpen: it.status === 'open',
        };
      case 'issue':
        return {
          raisedRound: it.roundFirstSeen,
          raisedBy: it.raisedBy,
          closedRound: it.status === 'resolved' ? it.roundLastSeen : null,
          closedBy: it.status === 'resolved' ? it.raisedBy : null,
          isOpen: it.status === 'open',
        };
      case 'comment':
        return {
          raisedRound: it.raisedRound,
          raisedBy: it.raisedBy,
          closedRound: null,
          closedBy: null,
          isOpen: false,  // comments are always "noted"
        };
      default:
        return null;
    }
  }).filter(Boolean);
}

function _buildKindRows(envelopes) {
  const rounds = new Set();
  for (const e of envelopes) {
    if (e.raisedRound) rounds.add(e.raisedRound);
    if (e.closedRound) rounds.add(e.closedRound);
  }
  const sorted = Array.from(rounds).sort((a, b) => a - b);
  return sorted.map((r) => {
    const claudeRaised = envelopes.filter((e) => e.raisedRound === r && (e.raisedBy === 'claude' || e.raisedBy === 'both')).length;
    const gptRaised    = envelopes.filter((e) => e.raisedRound === r && (e.raisedBy === 'gpt'    || e.raisedBy === 'both')).length;
    const claudeResolved = envelopes.filter((e) => e.closedRound === r && (e.closedBy === 'claude' || e.closedBy === 'both')).length;
    const gptResolved    = envelopes.filter((e) => e.closedRound === r && (e.closedBy === 'gpt'    || e.closedBy === 'both')).length;
    const stillOpen = envelopes.filter((e) =>
      (e.raisedRound ?? 0) <= r
      && (e.isOpen || (e.closedRound != null && e.closedRound > r))
    ).length;
    return { round: r, claudeRaised, gptRaised, claudeResolved, gptResolved, stillOpen };
  });
}

// Spec 0046 D5 — pluralised kind labels for the per-section header.
const KIND_PLURAL = {
  question: 'Questions',
  disagreement: 'Disagreements',
  claim: 'Claims',
  issue: 'Issues',
  comment: 'Comments',
};

function CritiqueSummaryView({ run, questions, disagreements }) {
  const issues = Array.isArray(run?.issues) ? run.issues : [];
  const comments = Array.isArray(run?.comments) ? run.comments : [];
  const claims = Array.isArray(run?.claims) ? run.claims : [];

  // Per spec 0046 D5 + PHASE_CHIP_ALLOWLIST — only render kinds the
  // phase actually emits, so Phase 2 doesn't get an empty Issues
  // table and Phase 4 doesn't get an empty Questions table.
  const PHASE_KIND_ORDER = {
    2: ['question', 'disagreement', 'claim'],
    4: ['issue', 'comment', 'disagreement'],
  };

  const _itemsFor = (kind, pid) => {
    const src = kind === 'question'     ? questions
              : kind === 'disagreement' ? disagreements
              : kind === 'claim'        ? claims
              : kind === 'issue'        ? issues
              : kind === 'comment'      ? comments
              : [];
    return src.filter((it) => it.phase === pid);
  };

  const renderPhase = (label, pid) => {
    const kinds = PHASE_KIND_ORDER[pid] || [];
    // Build per-kind table data; drop kinds that emitted no items at all.
    const sections = kinds
      .map((kind) => {
        const items = _itemsFor(kind, pid);
        if (items.length === 0) return null;
        const envelopes = _envelopesForKind(kind, items);
        const rows = _buildKindRows(envelopes);
        const totalOpen = envelopes.filter((e) => e.isOpen).length;
        const totalResolved = envelopes.length - totalOpen;
        return { kind, items, rows, totalOpen, totalResolved };
      })
      .filter(Boolean);

    if (sections.length === 0) {
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
    return (
      <section style={{ marginBottom: 22 }}>
        <h3 style={{
          fontSize: 12, fontWeight: 600, color: 'var(--fg-2)',
          letterSpacing: '0.04em', textTransform: 'uppercase',
          margin: '0 0 10px',
        }}>{label}</h3>
        {sections.map((s) => (
          <SummaryKindTable
            key={s.kind}
            kind={s.kind}
            items={s.items}
            rows={s.rows}
            totalOpen={s.totalOpen}
            totalResolved={s.totalResolved}
          />
        ))}
      </section>
    );
  };

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--bg-0)' }}>
      <div style={{ padding: '16px 24px 28px' }}>
        <div style={{
          fontSize: 11.5, color: 'var(--fg-3)', lineHeight: 1.55, marginBottom: 16,
        }}>
          Post-mortem aggregate of the critique journey, split per round and per model.
          Click a phase tab above to drill into the individual cards.
        </div>
        {renderPhase('Phase 2 — Negotiate', 2)}
        {renderPhase('Phase 4 — Review', 4)}
      </div>
    </div>
  );
}

// Spec 0046 D5 — one table per kind. Per-row counts split by agent;
// the Open column carries the cumulative still-open count after the
// round in question.
function SummaryKindTable({ kind, items, rows, totalOpen, totalResolved }) {
  const closedLabel = kind === 'question' ? 'answered'
                   : kind === 'comment'   ? 'noted'
                   : 'resolved';
  // Comments don't have a closure protocol — drop the resolved
  // columns + Open column to keep the table honest.
  const isStateless = kind === 'comment';

  return (
    <div style={{ marginBottom: 14 }}>
      <div className="mono" style={{
        fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.04em',
        textTransform: 'uppercase',
        display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap',
        marginBottom: 6,
      }}>
        <span style={{ color: 'var(--fg-1)', fontWeight: 600 }}>{KIND_PLURAL[kind] || kind}</span>
        <span>·</span>
        <span>{items.length} total</span>
        {!isStateless && (
          <>
            <span>·</span>
            <span style={{ color: totalResolved > 0 ? COLORS.ok : 'var(--fg-3)' }}>
              {totalResolved} {closedLabel}
            </span>
            <span>·</span>
            <span style={{ color: totalOpen > 0 ? COLORS.warn : 'var(--fg-3)' }}>
              {totalOpen} open
            </span>
          </>
        )}
      </div>
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
            <th style={_summaryTh}>
              <span style={{ color: 'var(--agent-a)' }}>Claude</span> raised
            </th>
            {!isStateless && (
              <th style={_summaryTh}>
                <span style={{ color: 'var(--agent-a)' }}>Claude</span> {closedLabel}
              </th>
            )}
            <th style={_summaryTh}>
              <span style={{ color: 'var(--agent-b)' }}>GPT</span> raised
            </th>
            {!isStateless && (
              <th style={_summaryTh}>
                <span style={{ color: 'var(--agent-b)' }}>GPT</span> {closedLabel}
              </th>
            )}
            {!isStateless && <th style={_summaryTh}>Open</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.round} style={{ borderTop: '1px solid var(--border-1)' }}>
              <td style={_summaryTd}>R{r.round}</td>
              <td style={_summaryTd}>{r.claudeRaised || '—'}</td>
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.claudeResolved > 0 ? COLORS.ok : 'var(--fg-3)',
                }}>{r.claudeResolved || '—'}</td>
              )}
              <td style={_summaryTd}>{r.gptRaised || '—'}</td>
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.gptResolved > 0 ? COLORS.ok : 'var(--fg-3)',
                }}>{r.gptResolved || '—'}</td>
              )}
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.stillOpen > 0 ? COLORS.warn : 'var(--fg-3)',
                }}>{r.stillOpen || '—'}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
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
function QuestionCard({ q, onHighlight, run }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const isAnswered = q.status === 'answered';
  const accentColor = COLORS.info;
  const raisedMeta = AGENT_META[q.raisedBy];
  const answerMeta = q.answeredBy ? AGENT_META[q.answeredBy] : null;
  // Spec 0046 D4 — ghosted-rounds annotation from the spec-0043 ledger.
  const ledgerEntry = findLedgerEntry(run, q.phase, q.id);
  const ghostedRounds = ledgerEntry?.ghostedRounds || 0;

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
        {/* Spec 0046 D3 — `{Kind} {Public ID} · {status} · {body}`.
            Pre-spec the round range + the internal ID sat in the
            collapsed headline; both move into the expanded body so
            the headline reads as one human-readable sentence. */}
        <CardHeadline
          kind="question"
          publicId={q.id}
          statusLabel={isAnswered ? 'answered' : 'open'}
          statusColor={isAnswered ? COLORS.ok : COLORS.warn}
          body={q.body}
          ghostedRounds={ghostedRounds}
          accentColor={accentColor}
          trailing={<CardChevron open={open} hover={hover} />}
        />
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

// Spec 0046 D3 — shared headline for every critique card type
// (Question / Disagreement / Issue / Comment / Claim).
//
// Pre-spec each card type shot its own one-line header with a
// single-letter glyph (`Q`, `D`, `I`, `C`), a round range token
// (`R1`/`R1→R2`), the truncated body, the internal ID, and a status
// pill. The user's feedback flagged this as "cryptic" + duplicated;
// spec 0046 D3 collapses the visible signal to `{Kind label} {Public
// ID} · {status} · {body snippet}`. The round range + the cryptic
// internal IDs (`I-c-r1-01` etc.) move into the expanded body.
const KIND_LABELS = {
  question:     'Question',
  disagreement: 'Disagreement',
  issue:        'Issue',
  comment:      'Comment',
  claim:        'Claim',
};

// Spec 0046 D3 — strip the markdown formatting we render plain-text in
// a headline. The agents commonly emit `**C-1** — \`open\` — body` or
// `**Q1:** body`; we already render the public ID + status in their
// own spans, so the leading prefix doubles up. Strip:
//   - `**bold**` markers
//   - backtick spans (`open`/`resolved`)
//   - a leading `Cx-N`/`Q-x-rY-NN`/etc. plus the dash/em-dash separator
//   - a leading status word followed by a dash
function stripMarkdown(text) {
  if (!text) return '';
  let s = String(text);
  // Drop bold/italic/backtick markers.
  s = s.replace(/`+/g, '').replace(/\*\*/g, '').replace(/(?<!\\)_/g, '');
  // Drop a leading public/internal ID prefix (e.g. ``C-1 — `` or
  // ``Q1: ``) so the body snippet starts at the substantive content.
  s = s.replace(/^\s*[A-Z]+-?[a-z]?-?\d+[a-z]?(?:\s*[—:–-]\s*)/i, '');
  // Drop a leading status word + dash (``open — body``).
  s = s.replace(/^\s*(open|resolved|noted|answered|deferred|non-blocking)\s*[—:–-]\s*/i, '');
  return s.trim();
}

function CardHeadline({
  kind, publicId, statusLabel, statusColor, body,
  ghostedRounds, accentColor, trailing,
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
      <span className="mono" style={{
        fontSize: 10.5, letterSpacing: '0.04em',
        padding: '1px 6px', borderRadius: 4,
        color: accentColor,
        background: `${accentColor}14`,
        border: `1px solid ${accentColor}44`,
        flexShrink: 0,
        whiteSpace: 'nowrap',
      }}>
        {KIND_LABELS[kind] || kind}{publicId ? ` ${publicId}` : ''}
      </span>
      {statusLabel && (
        <>
          <span style={{ color: 'var(--fg-4)', flexShrink: 0 }}>·</span>
          <span className="mono" style={{
            fontSize: 10.5,
            padding: '1px 6px', borderRadius: 999,
            border: `1px solid ${statusColor}55`,
            color: statusColor,
            background: `${statusColor}14`,
            flexShrink: 0,
            whiteSpace: 'nowrap',
          }}>
            {statusLabel}
          </span>
        </>
      )}
      <span style={{ color: 'var(--fg-4)', flexShrink: 0 }}>·</span>
      <span style={{
        flex: 1, minWidth: 0,
        fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 500, lineHeight: 1.4,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {truncateBody(stripMarkdown(body), 70) || '(no body)'}
      </span>
      {ghostedRounds > 0 && <GhostedRoundsBadge ghostedRounds={ghostedRounds} />}
      {trailing}
    </div>
  );
}

// Spec 0046 D4 — inline ghosted-rounds badge, rendered inside the
// per-card headline. Same visual idiom as the `LedgerDriftChip`
// header chip — small warn-tinted ⚠ glyph + integer + tooltip.
// Renders nothing when ``ghostedRounds === 0``.
function GhostedRoundsBadge({ ghostedRounds }) {
  if (!ghostedRounds) return null;
  return (
    <span
      className="mono"
      title={`Open for ${ghostedRounds} round(s) without an explicit addressing signal (no ## Answers to: / Resolved / Substantive disagreements reference). Surface flag, does not block convergence.`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 3,
        padding: '1px 6px', borderRadius: 4,
        fontSize: 10,
        color: COLORS.warn,
        background: 'rgba(212,160,86,0.10)',
        border: `1px solid ${COLORS.warn}55`,
        cursor: 'help',
        flexShrink: 0,
        whiteSpace: 'nowrap',
      }}
    >
      <span>⚠</span>
      <span>ghosted {ghostedRounds}r</span>
    </span>
  );
}

// Spec 0046 D3 — shared chevron used by every critique card. Pre-spec
// each card type rendered its own copy; consolidating keeps the
// expand/collapse animation consistent.
function CardChevron({ open, hover }) {
  return (
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
  );
}

// Spec 0046 D4 — resolve a ledger entry by id. Wires ``GhostedAnnotation``
// + ``CardHeadline.ghostedRounds`` to the system-derived ledger built
// by spec 0043. Returns ``null`` when the ledger isn't populated for
// this phase (legacy snapshots).
function findLedgerEntry(run, phaseId, itemId) {
  if (!run || !run.phaseLedgers || !itemId) return null;
  const entries = run.phaseLedgers[phaseId] || [];
  return entries.find((e) => e.id === itemId) || null;
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

function DisagreementCard({ d, onHighlight, run }) {
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
  // Spec 0046 D4 — ghosted-rounds annotation from the spec-0043 ledger.
  const ledgerEntry = findLedgerEntry(run, d.phase, d.id);
  const ghostedRounds = ledgerEntry?.ghostedRounds || 0;

  // Card accent (left edge) color by status
  let accentColor;
  if (d.status === 'open' && d.deadlocked) accentColor = COLORS.warn;
  else if (d.status === 'open')            accentColor = COLORS.warn;
  else if (which === 'claude')             accentColor = COLORS.agentA;
  else if (which === 'gpt')                accentColor = COLORS.agentB;
  else if (which === 'both')               accentColor = COLORS.ok;

  // Spec 0046 D3 — status label + colour for the unified headline.
  let statusLabel, statusColor;
  if (d.status === 'open' && d.deadlocked) { statusLabel = 'deadlocked'; statusColor = COLORS.warn; }
  else if (d.status === 'open')            { statusLabel = 'open';       statusColor = COLORS.warn; }
  else if (which === 'claude')             { statusLabel = '→ claude';   statusColor = COLORS.agentA; }
  else if (which === 'gpt')                { statusLabel = '→ gpt';      statusColor = COLORS.agentB; }
  else if (which === 'both')               { statusLabel = 'aligned';    statusColor = COLORS.ok; }

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
        {/* Spec 0046 D3 — unified headline. The round range + exchange
            count move into the expanded body below. */}
        <CardHeadline
          kind="disagreement"
          publicId={d.id}
          statusLabel={statusLabel}
          statusColor={statusColor}
          body={d.shortLabel || d.point}
          ghostedRounds={ghostedRounds}
          accentColor={COLORS.warn}
          trailing={<CardChevron open={open} hover={hover} />}
        />
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
function IssueCard({ issue, onHighlight, run }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const isOpen = issue.status === 'open';
  const accentColor = isOpen ? COLORS.warn : COLORS.ok;
  const raisedMeta = AGENT_META[issue.raisedBy];
  // Spec 0046 D4 — ghosted-rounds annotation from the spec-0043 ledger.
  const ledgerEntry = findLedgerEntry(run, issue.phase, issue.id);
  const ghostedRounds = ledgerEntry?.ghostedRounds || 0;

  const onCardClick = React.useCallback(() => {
    if (onHighlight && issue.raisedTurnKey) {
      onHighlight([issue.raisedTurnKey], 'd');
    }
    setOpen(o => !o);
  }, [issue, onHighlight]);

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
        {/* Spec 0046 D3 — unified headline; round range moves to expanded body. */}
        <CardHeadline
          kind="issue"
          publicId={issue.id}
          statusLabel={isOpen ? 'open' : 'resolved'}
          statusColor={isOpen ? COLORS.warn : COLORS.ok}
          body={issue.body}
          ghostedRounds={ghostedRounds}
          accentColor={COLORS.warn}
          trailing={<CardChevron open={open} hover={hover} />}
        />
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
function CommentCard({ comment, onHighlight, run }) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const raisedMeta = AGENT_META[comment.raisedBy];
  // Spec 0046 D4 — ghosted-rounds annotation from the spec-0043 ledger.
  const ledgerEntry = findLedgerEntry(run, comment.phase, comment.id);
  const ghostedRounds = ledgerEntry?.ghostedRounds || 0;

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
        {/* Spec 0046 D3 — unified headline; round + raiser move to expanded body. */}
        <CardHeadline
          kind="comment"
          publicId={comment.id}
          statusLabel="noted"
          statusColor="var(--fg-3)"
          body={comment.body}
          ghostedRounds={ghostedRounds}
          accentColor="var(--fg-3)"
          trailing={<CardChevron open={open} hover={hover} />}
        />
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
