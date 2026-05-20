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

// PaneButton / PaneButtonGroup removed in SPEC-0057 D8 — all call sites
// migrated to Tab/TabGroup in SPEC-0053. See CHANGELOG 0.55.0.

// ─────────────────── Compact run-detail header (spec 0024 pass 3) ────────────
// Spec 0035 reverts the spec-0033 four-row layout back to two rows:
//   row 1: topic · cost · status/errors
//   row 2: phase dots + dot labels + run metadata (started · drafter · elapsed · round)
// Spec 0056 SUR-07: equal-row padding (12/16), drafter callout pill replaces
// inline drafter label. ReconcileChip 5-state preserved in row 1.
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
  const totalTokens =
    (run.agents.claude.tokens?.in || 0) + (run.agents.claude.tokens?.out || 0) +
    (run.agents.gpt.tokens?.in || 0) + (run.agents.gpt.tokens?.out || 0);

  return (
    <header className="run-detail__head" data-tour-anchor="run-detail-header">
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
      {/* Row 2: phase dots + drafter callout pill + run metadata */}
      <PhaseDotsRow
        run={run}
        startedClock={startedClock}
        elapsedLabel={elapsedLabel}
      />
    </header>
  );
}

// ─────────────────── Spec 0035 — per-agent pill (Timeline toolbar) ──────────
// Spec 0056 D7: migrated to the class-backed AgentStrip from shared.jsx
// (SPEC-0052). The `right` prop carries the live-activity phrase (dot +
// sentence) that the bespoke version rendered inline.
function TimelineAgentPill({ agent, run }) {
  const meta = AGENT_META[agent];
  const ag = run.agents?.[agent] || {};
  const tokensIn = ag.tokens?.in || 0;
  const tokensOut = ag.tokens?.out || 0;
  const totalTokens = tokensIn + tokensOut;
  const cost = ag.cost || 0;
  const modelId = ag.modelId || ag.model_id || meta?.name || agent;
  const { live, phrase } = composeAgentActivity(agent, run);
  const slot = agent === 'claude' ? 'a' : 'b';
  const dotColor = live ? meta.color : 'var(--md-outline)';
  const phraseColor = live ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-faint)';

  const activityRight = (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
      <Dot color={dotColor} pulse={live ? 'pulse-a' : null} size={6} />
      {/* Spec 0112 — sizing/overflow lives in .as-activity (components.css).
          Only the dynamic phraseColor remains inline. */}
      <span className="as-activity" style={{ color: phraseColor }}>
        {phrase}
      </span>
    </span>
  );

  return (
    <AgentStrip
      agent={slot}
      name={meta.name}
      model={modelId}
      tokens={totalTokens}
      cost={cost}
      right={activityRight}
      className="as-timeline"
    />
  );
}

// ─────────────────── Spec 0105 — restored agent bar above timeline ───────────
function TimelineAgentBar({ run }) {
  return (
    <div className="agent-bar">
      <TimelineAgentPill agent="claude" run={run} />
      <TimelineAgentPill agent="gpt" run={run} />
    </div>
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
        background: 'var(--md-surface-container)',
        border: `1px solid ${warnings > 0 ? COLORS.warn + '55' : 'var(--md-outline-hair)'}`,
        borderRadius: 999,
        fontFamily: 'inherit', cursor: 'pointer',
        fontSize: 11, color: 'var(--md-on-surface-variant)',
        whiteSpace: 'nowrap', flexShrink: 0,
      }}>
      <Mdi name="magnify" size={11} />
      <span className="mono">{totalQueries}</span>
      <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
      <span className="mono">{totalUrls} URLs</span>
      {warnings > 0 && (
        <>
          <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
          <span className="mono" style={{ color: COLORS.warn, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
            <Mdi name="alert" size={11} /> {warnings} unmatched
          </span>
        </>
      )}
    </button>
  );
}

// ─────────────────── Spec 0033 — phase dots row with labels ─────────────────
// Spec 0056 SUR-07: drafter callout pill replaces inline "drafter: X" text.
function PhaseDotsRow({ run, startedClock, elapsedLabel }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      paddingTop: 2,
    }}>
      <PhaseDots run={run} />
      <span className="mono" style={{
        fontSize: 9.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.03em',
      }}>
        preflight · drafts · negotiate · drafting · review
      </span>
      {/* Spec 0056 D4: drafter callout pill — agent-tinted Chip with icon. */}
      {run.drafter && <DrafterCalloutPill drafter={run.drafter} />}
      <span style={{ flex: 1 }} />
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-faint)',
        whiteSpace: 'nowrap',
      }}>
        started <span style={{ color: 'var(--md-on-surface-variant)' }}>{startedClock}</span>
        &nbsp;·&nbsp;<span style={{ color: 'var(--md-on-surface-variant)' }}>{elapsedLabel}</span> elapsed
        {run.status === 'running' && (run.phase === 2 || run.phase === 4) && run.round && (
          <>&nbsp;·&nbsp;round <span style={{ color: 'var(--md-on-surface-variant)' }}>
            {run.round.current}/{run.round.soft}
          </span><span style={{ color: 'var(--md-on-surface-faint)' }}>&nbsp;(hard {run.round.hard})</span></>
        )}
      </span>
    </div>
  );
}

// Spec 0056 D4 — drafter callout pill. Agent-tinted Chip with AgentIcon.
// Shows "Claude drafter" or "GPT drafter". Hidden when run.drafter is null.
function DrafterCalloutPill({ drafter }) {
  const meta = AGENT_META[drafter];
  if (!meta) return null;
  const slot = drafter === 'claude' ? 'a' : 'b';
  return (
    <Chip tone={slot} pill title={`Drafter: ${meta.name}`}>
      <AgentIcon agent={drafter} size={14} />
      <span>{meta.name} drafter</span>
    </Chip>
  );
}

// Spec 0056 D5 SUR-08 — blocking-item callout bar. Renders between header
// and main content when the run has open standing items in phaseLedgers.
// Shows "N open . M ghosted" with a click-to-jump action.
function BlockingItemCallout({ run }) {
  const counts = React.useMemo(() => {
    if (!run?.phaseLedgers) return { open: 0, ghosted: 0 };
    let open = 0;
    let ghosted = 0;
    for (const phase of [2, 4]) {
      const entries = run.phaseLedgers[phase] || [];
      for (const e of entries) {
        if (e.currentStatus === 'open') open++;
        if (e.ghostedRounds > 0) ghosted++;
      }
    }
    return { open, ghosted };
  }, [run?.phaseLedgers]);

  if (counts.open === 0 && counts.ghosted === 0) return null;

  const parts = [];
  if (counts.open > 0) parts.push(`${counts.open} open`);
  if (counts.ghosted > 0) parts.push(`${counts.ghosted} ghosted`);

  const onJump = () => {
    // Find the first open item in the critique pane and scroll to it.
    const card = document.querySelector('[data-critique-status="open"]');
    if (card) {
      card.scrollIntoView({ block: 'center', behavior: 'smooth' });
      card.classList.add('dr-flash');
      setTimeout(() => card.classList.remove('dr-flash'), 1600);
    }
  };

  return (
    <button
      type="button"
      onClick={onJump}
      title={`${parts.join(' · ')} — click to jump to first`}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        padding: '6px 20px',
        background: counts.ghosted > 0 ? `${COLORS.warn}0d` : `${COLORS.info}0d`,
        borderBottom: '1px solid var(--md-outline-hair)',
        border: 'none',
        borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--md-outline-hair)',
        cursor: 'pointer',
        fontFamily: 'inherit', fontSize: 11.5, color: 'var(--md-on-surface-variant)',
        flexShrink: 0,
        width: '100%',
      }}
    >
      <Mdi name={counts.ghosted > 0 ? 'alert-circle-outline' : 'information-outline'} size={14}
           style={{ color: counts.ghosted > 0 ? COLORS.warn : COLORS.info }} />
      <span className="mono" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
        {counts.open > 0 && (
          <span><span className="num" style={{ fontWeight: 600 }}>{counts.open}</span> open</span>
        )}
        {counts.open > 0 && counts.ghosted > 0 && (
          <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        )}
        {counts.ghosted > 0 && (
          <span style={{ color: COLORS.warn }}>
            <span className="num" style={{ fontWeight: 600 }}>{counts.ghosted}</span> ghosted
          </span>
        )}
      </span>
      <span style={{ color: 'var(--md-on-surface-faint)', fontSize: 10.5 }}>click to jump</span>
    </button>
  );
}

function Topic({ text }) {
  return (
    <div title={text}
         style={{
           color: 'var(--md-on-surface)', fontSize: 14, lineHeight: 1.35, fontWeight: 500,
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
      <Chip tone="muted" pill lg>checking…</Chip>
    );
  }

  // No snapshot OR fetch error → render as "unverified" (404 is the
  // common case: the day's reconciliation hasn't run yet).
  if (!report) {
    return (
      <Chip tone="muted" pill lg icon="circle"
            title={error
              ? `Reconciliation endpoint unreachable: ${error}`
              : "No reconciliation snapshot for this date. Run `dual-research reconcile-costs --run <id>` to verify."}>
        <span style={{ color: 'var(--md-on-surface-muted)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>unverified</span>
      </Chip>
    );
  }

  const status = report.verificationStatus || report.verification_status || 'unverified';
  const totalProvider = Number(report.totalProviderUsd || report.total_provider_usd || 0);
  const totalDelta = Number(report.totalDeltaUsd || report.total_delta_usd || 0);
  const providersChecked = report.providersChecked || report.providers_checked || [];
  const providersSkipped = report.providersSkipped || report.providers_skipped || {};

  // SPEC-0052 D7 — migrate to Chip primitive. Each state's tone maps to a
  // chip.tone-X class (ok/warn/info/muted); icon ships via Chip's `icon`
  // prop. Body composition stays bespoke (5 different bodies).
  const palette = {
    verified:                { icon: 'check',        tone: 'ok'    },
    drift:                   { icon: 'alert',        tone: 'warn'  },
    partial:                 { icon: 'circle-half',  tone: 'info'  },
    unverified:              { icon: 'circle',       tone: 'muted' },
    awaiting_provider_data:  { icon: 'timer',        tone: 'info'  },
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
        <span>verified</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        <span className="num">{fmt.cost(cost)}</span>
      </>
    );
  } else if (status === 'drift') {
    body = (
      <>
        <span>Δ</span>
        <span className="num">
          {totalDelta >= 0 ? '+' : ''}{fmt.cost(totalDelta)}
        </span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>
          billed <span className="num">{fmt.cost(totalProvider)}</span>
        </span>
      </>
    );
  } else if (status === 'partial') {
    body = (
      <>
        <span style={{ color: 'var(--md-on-surface-muted)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        {providersChecked.map((prov) => (
          <span key={prov} style={{ color: COLORS.ok, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
            <Mdi name="check" size={10} /> {prov}
          </span>
        ))}
        {Object.keys(providersSkipped).map((prov) => (
          <span key={prov} style={{ color: COLORS.warn, marginLeft: 4, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
            <Mdi name="alert" size={10} /> {prov}
          </span>
        ))}
      </>
    );
  } else if (status === 'awaiting_provider_data') {
    body = (
      <>
        <span style={{ color: 'var(--md-on-surface-muted)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>awaiting provider data</span>
      </>
    );
  } else {
    body = (
      <>
        <span style={{ color: 'var(--md-on-surface-muted)' }}>local</span>
        <span className="num">{fmt.cost(cost)}</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        <span style={{ color: 'var(--md-on-surface-faint)' }}>unverified</span>
      </>
    );
  }

  // SPEC-0052 D7 — Chip primitive wraps the 5-state body. tone class drives
  // background/border/text-color; `icon` prop renders the per-state Mdi; `pill`
  // modifier preserves the pill shape; `chip-lg` matches the prior 22-ish-px
  // height. Body's inline color spans override Chip's tone color where the
  // copy needs to be neutral (var(--md-on-surface-variant/muted/faint)) rather than tone-colored.
  return (
    <Chip tone={p.tone} pill lg icon={p.icon} title={tooltip}>
      {body}
    </Chip>
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
            background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)',
            fontSize: 11, color: 'var(--md-on-surface-variant)', flexShrink: 0,
            whiteSpace: 'nowrap',
          }}>
      <span className="num">{fmt.cost(cost)}</span>
      <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
      <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(tokens)}t</span>
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
      border: '1px solid var(--md-outline-hair)',
      background: 'var(--md-surface-container-high)',
      flexShrink: 0,
      fontFamily: 'var(--md-font-data)',
      // SPEC-0087 § A — align the run-detail status pill's vertical
      // sizing with the run-list `.sb` primitive (20px tall). The
      // inner status half stays a bespoke layout to keep the
      // errors-half toggle behaviour, but visually it now matches.
      minHeight: 20,
    }}>
      {/* Status half */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '0 10px',
        fontSize: 11, color: 'var(--md-on-surface-variant)', letterSpacing: '0.01em',
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
            padding: '0 10px',
            background: showErrors ? COLORS.err + '20' : 'transparent',
            border: 'none', borderLeft: '1px solid var(--md-outline-hair)',
            color: COLORS.err, fontSize: 11, cursor: 'pointer',
            fontFamily: 'inherit',
          }}
          onMouseEnter={e => { if (!showErrors) e.currentTarget.style.background = COLORS.err + '14'; }}
          onMouseLeave={e => { if (!showErrors) e.currentTarget.style.background = 'transparent'; }}>
          <Icon.Warn />
          <span className="num">{errorCount}</span>
          <span style={{ color: COLORS.err, opacity: 0.85 }}>error{errorCount === 1 ? '' : 's'}</span>
          {showErrors && (
            <span style={{ marginLeft: 4, transform: 'rotate(180deg)', display: 'inline-block', color: 'var(--md-on-surface-variant)' }}>
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
          : 'var(--md-outline)';
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
                background: completed ? COLORS.ok : 'var(--md-outline-variant)',
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

// ─────────────────── PhaseRail (SPEC-0101 M3) ───────────────────
// Horizontal 5-cell phase indicator strip. Renders inside modals
// to show phase progress at a glance. Cells P0..P4 carry --done or
// --current state tinting per the M3 design-system anatomy.
function PhaseRail({ run }) {
  const { phase, status } = run;
  return (
    <div className="phase-rail">
      {PHASES.filter(p => p.id <= 4).map(p => {
        const done = p.id < phase || (status === 'completed' && p.id <= 4);
        const current = p.id === phase && status !== 'completed';
        const cls = ['phase-rail__cell'];
        if (done) cls.push('phase-rail__cell--done');
        if (current) cls.push('phase-rail__cell--current');
        return (
          <div key={p.id} className={cls.join(' ')}>
            <span className="ph">{p.short}</span>
            <span className="name">{p.label}</span>
            <span className="meta">{done ? 'Done' : current ? 'In progress' : 'Queued'}</span>
          </div>
        );
      })}
    </div>
  );
}

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
// Spec 0099 — M3 Timeline pane rework. Header chrome + vertical phase
// rail outside the column, anchored to header centres via CSS grid.
// Resolves Issue 5 (rail anchoring), Issue 11 (single dashed border on
// unfold), Issue 16 (REPAIR-round explainer).
function Timeline({ run, highlightedTurnKeys }) {
  const items = React.useMemo(() => buildTimeline(run), [run]);
  const [openId, setOpenId] = React.useState(null);
  const [tab, setTab] = React.useState('conversation'); // 'conversation' | 'consumption'

  // Reset open card + active tab when navigating between runs.
  React.useEffect(() => {
    setOpenId(null);
    setTab('conversation');
  }, [run.id]);

  const openItem = items.find((i) => i.id === openId) || null;

  const artifactCount = items.filter(i => i.kind !== 'phase-divider' && i.kind !== 'error' && i.kind !== 'deadlock').length;

  // Group items by phase for the Conversation tab.
  const phaseGroups = React.useMemo(() => groupTimelineByPhase(items), [items]);

  // Visible phases: phases that have at least one non-divider item.
  const visiblePhases = React.useMemo(() => {
    return phaseGroups
      .filter(g => g.divider && g.items.length > 0)
      .map(g => {
        const pid = g.divider.phaseId;
        const pDef = PHASES[pid] || PHASES.find(p => p.id === pid);
        const allDone = pid < run.phase || run.status === 'completed';
        const isCurrent = pid === run.phase && run.status !== 'completed';
        return { ...g, pid, pDef, allDone, isCurrent };
      });
  }, [phaseGroups, run.phase, run.status]);

  // Phase collapse state (persisted per-run).
  const [collapsed, setCollapsed] = React.useState({});
  React.useEffect(() => { setCollapsed({}); }, [run.id]);
  const togglePhase = React.useCallback((pid) => {
    setCollapsed(prev => ({ ...prev, [pid]: !prev[pid] }));
  }, []);

  return (
    <div className="rdvc__pane" style={{
      display: 'flex', flexDirection: 'column',
      borderRight: '1px solid var(--md-outline-hair)',
      minWidth: 0, minHeight: 0,
    }}>
      {/* HEAD — title + count */}
      <header className="tl__head">
        <span className="ttl">Timeline</span>
        <span className="ct">{artifactCount} artifacts</span>
      </header>

      {/* TABS — Conversation / Consumption. Outer .tl__tabs is the full-width
          band (matches .bar2); inner .tl__tabs-inner is the segmented pill. */}
      <div className="tl__tabs">
        <div className="tl__tabs-inner">
          <button
            className={`tl__tab${tab === 'conversation' ? ' is-active' : ''}`}
            onClick={() => setTab('conversation')}
          >
            <span className="ms ms-18">forum</span>Conversation
          </button>
          <button
            className={`tl__tab${tab === 'consumption' ? ' is-active' : ''}`}
            onClick={() => setTab('consumption')}
          >
            <span className="ms ms-18">stacked_bar_chart</span>Consumption
          </button>
        </div>
      </div>

      {tab === 'conversation' ? (
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {/* BODY — phases only. Per-phase marker lives inside each header so
              collapse / expand can never desync the rail from the phase it
              belongs to (the bug was that .tl__rail laid markers out as
              equal flex segments, drifting once phase heights diverged). */}
          <div className="tl__body" data-tour-anchor="timeline-phase-rail">
            <div className="tl__phases">
              {visiblePhases.map(vp => {
                const isCollapsed = !!collapsed[vp.pid];
                const divider = vp.divider;
                const metaParts = [];
                if (divider.duration) metaParts.push(fmt.duration(divider.duration));
                if (divider.extra) metaParts.push(divider.extra);
                const markerStateCls = vp.allDone ? 'is-done' : vp.isCurrent ? 'is-current' : '';
                return (
                  <section key={vp.pid} className="tl-phase" data-collapsed={isCollapsed ? 'true' : 'false'}>
                    <header
                      className="tl-phase__hd"
                      role="button"
                      tabIndex={0}
                      onClick={() => togglePhase(vp.pid)}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); togglePhase(vp.pid); } }}
                    >
                      <span className={`tl-phase__marker ${markerStateCls}`} aria-hidden="true">
                        <span className="dot"></span>
                        <span className="lbl">{vp.pDef?.short || `P${vp.pid}`}</span>
                      </span>
                      <span className="chev"><span className="ms ms-18">expand_more</span></span>
                      <span className="tl-phase__pcode">PHASE {vp.pid}</span>
                      <span className="tl-phase__name">{vp.pDef?.label || `Phase ${vp.pid}`}</span>
                      <span className="tl-phase__meta">{metaParts.join(' \u00b7 ') || '\u2014'}</span>
                      <TlPhaseHeadChips phaseId={vp.pid} run={run} />
                    </header>
                    {!isCollapsed && (
                      <div className="tl-phase__body">
                        {vp.items.map(item => (
                          <TlTurnRow
                            key={item.id}
                            item={item}
                            run={run}
                            isOpen={openId === item.id}
                            onToggle={() => setOpenId(openId === item.id ? null : item.id)}
                          />
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          </div>
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
    </div>
  );
}

// ─── Spec 0119 — canonical category vocabulary for chip rendering ────
//
// CATEGORY_TONE / _BUBBLE / _LABEL_* are shared by every chip-bearing
// surface (timeline turn cards, phase headers, critique pane filter
// row, critique card headers). Treat them as immutable: the order
// Q→D→I→C and the fixed color mapping are part of the governance.
const CATEGORY_TONE = {
  questions:     'info',
  disagreements: 'warn',
  issues:        'err',
  comments:      'idle',
};
const CATEGORY_BUBBLE = {
  questions:     'Q',
  disagreements: 'D',
  issues:        'I',
  comments:      'C',
};
const CATEGORY_LABEL_PLURAL = {
  questions:     'Questions',
  disagreements: 'Disagreements',
  issues:        'Issues',
  comments:      'Comments',
};
const CATEGORY_LABEL_SINGULAR = {
  questions:     'Question',
  disagreements: 'Disagreement',
  issues:        'Issue',
  comments:      'Comment',
};

// Spec 0119 — cross-pane jump signal. Timeline chips dispatch this
// when clicked; CritiqueExplorer listens and applies the resulting
// (phase, kindFilter) update. Decoupling via a window event keeps
// us from threading prop drilling through Timeline → TlPhase →
// TlTurnRow just for one cross-cutting affordance.
function dispatchCritiqueJump({ category, round, phase }) {
  if (typeof window === 'undefined' || !window.dispatchEvent) return;
  window.dispatchEvent(new CustomEvent('dr-critique-jump', {
    detail: { category, round, phase },
  }));
}

// Spec 0119 §8.2 — phase-header category-summary chip cluster.
//
// Aggregates ``PhaseCategoryStats`` across both agents for the phase.
// Phase 0 + 2 show Questions + Disagreements; Phase 4 also shows
// Issues + Comments. Phase 1 + 3 (parallel research / draft) raise
// no items and render no category chips.
//
// Ledger-drift modifier (spec 0119 §6 / Q5): when ``run.drifts``
// contains entries whose turnKey starts with ``phase{N}_``, prepend
// a ``⚠ ledger drift`` chip with the count. Drift is computed
// end-of-phase by the aggregator (per-turn granularity isn't there
// yet), so the phase header is the right surface.
function TlPhaseHeadChips({ phaseId, run }) {
  const phaseSummary = run?.phaseStats?.[`phaseSummary_${phaseId}`];
  const cats = (phaseId === 4)
    ? ['questions', 'disagreements', 'issues', 'comments']
    : (phaseId === 0 || phaseId === 2)
      ? ['questions', 'disagreements']
      : [];

  const phaseDrifts = (run?.drifts || []).filter(
    (d) => (d.turnKey || '').startsWith(`phase${phaseId}_`)
  );

  if (!phaseSummary && phaseDrifts.length === 0) return null;
  if (cats.length === 0 && phaseDrifts.length === 0) return null;

  return (
    <div className="tl-phase__chips">
      {phaseDrifts.length > 0 && (
        <Chip
          mono
          tone="warn"
          label="⚠ ledger drift"
          value={phaseDrifts.length}
          title={phaseDrifts.map(d => `${d.kind}: agent=${d.agentCount} · ledger=${d.ledgerCount}`).join('\n')}
        />
      )}
      {cats.map((cat) => {
        const c = phaseSummary?.[cat] || { standing: 0, raised: 0, closed: 0, capped: 0 };
        const noActivity = (c.raised + c.closed) === 0;
        return (
          <Chip
            key={cat}
            tone={CATEGORY_TONE[cat]}
            categoryBubble={CATEGORY_BUBBLE[cat]}
            value={c.standing}
            add={c.raised}
            sub={c.closed}
            trailingSuffix={c.capped > 0 ? `⊘ ${c.capped}` : null}
            dim={noActivity}
            ariaLabel={`${CATEGORY_LABEL_PLURAL[cat]}: ${c.standing} standing, ${c.raised} raised, ${c.closed} closed${c.capped > 0 ? `, ${c.capped} capped` : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              dispatchCritiqueJump({ category: cat, phase: phaseId });
            }}
          />
        );
      })}
    </div>
  );
}

// Spec 0119 §5.4 / §8.1 — never-bare status chip for timeline turn
// cards. The contract module's TurnStatus stays {IN_PROGRESS, AGREED};
// the bare ✓ chip is a UX-only marker for "turn finished, didn't
// emit AGREED."
function TlStatusChip({ item, isLive }) {
  if (isLive) return <Chip tone="info" leadingDot label="running" />;
  if (item.agreed) {
    return <Chip tone="ok" leadingIcon={<CheckGlyph size={12} />} label="agreed" />;
  }
  if (item.status === 'queued') {
    return <Chip tone="idle" leadingDot label="queued" />;
  }
  return (
    <Chip
      tone="ok"
      iconOnly
      leadingIcon={<CheckGlyph size={12} />}
      ariaLabel="Round completed"
    />
  );
}

// Spec 0099 + spec 0119 — timeline turn row.
//
// Every row in the timeline (input, preflight, plan, turn 1..N,
// doc) renders as a card whose header is a single chip row:
//
//   [provider] [activity] [modifiers…] [Q D I C…]  ────►  [status] [chev]
//
// Provider FIRST, activity SECOND, category chips in fixed Q→D→I→C
// order (when applicable), status chip right-aligned, never bare.
// See spec 0119 §6 (composition rules).
function TlTurnRow({ item, run, isOpen, onToggle }) {
  const agent = item.agent || null;
  const agentSlot = agent === 'gpt' ? 'b' : agent === 'claude' ? 'a' : null;
  const agentName = agent ? (AGENT_META[agent]?.name || agent) : null;
  const isRepair = hasRepairSibling(run, item.turnKey);
  const isLive = item.live;

  // Spec 0115 — full-word activity label (no single-letter badge).
  const activityLabel = item.round != null ? `Turn ${item.round}`
                      : item.kind === 'input' ? 'Brief'
                      : item.kind === 'preflight' ? 'Preflight'
                      : item.kind === 'plan' ? 'Plan'
                      : item.kind === 'plan-live' ? 'Plan'
                      : item.kind === 'doc' ? 'Draft'
                      : item.kind === 'doc-live' ? 'Draft'
                      : item.kind || '—';

  const phase = item.phase ?? null;

  // Spec 0115 — per-category summary chips for interaction-phase rounds.
  // ``item.stats.categories`` is populated by the Python aggregator from
  // the new ItemRaised/ItemTransitioned event stream. Phase 0 + 2 carry
  // Questions + Disagreements; phase 4 also carries Issues + Comments.
  const stats = item.stats || {};
  const categories = stats.categories || null;
  const isInteractionTurn = item.round != null || item.kind === 'preflight';
  const showCategoryChips = isInteractionTurn && categories;
  const chipCategories = (phase === 4)
    ? ['questions', 'disagreements', 'issues', 'comments']
    : ['questions', 'disagreements'];

  // Expanded body content.
  const gist = !isLive ? composeGist(item, run) : '';
  const summary = item.summary || '';
  const silentAgent = isRepair ? (agent === 'gpt' ? 'GPT' : 'Claude') : null;
  const otherAgent = silentAgent === 'GPT' ? 'Claude' : 'GPT';
  const repairExplainer = isRepair
    ? `${silentAgent} was silent this turn. ${otherAgent} will reissue the same plan on the next round. No data lost.`
    : null;

  const usage = run.phaseTokenUsage || {};
  const turnUsageKey = item.turnKey
    ? item.turnKey.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
    : null;
  const turnUsage = turnUsageKey ? usage[turnUsageKey] : null;
  const tokensIn = turnUsage?.inputTokens || turnUsage?.input_tokens || 0;
  const tokensOut = turnUsage?.outputTokens || turnUsage?.output_tokens || 0;
  const totalTokens = tokensIn + tokensOut;
  const cost = turnUsage?.cost || 0;

  // Side-accent class on the card — mirrors the critique pane's
  // is-open / is-resolved / is-drift left-border tint convention.
  const cardStatusCss = isLive ? 'open'
                      : isRepair ? 'drift'
                      : 'resolved';

  // Spec 0117 §6 — hover tooltip shows the full registry display name
  // even though the visible chip uses the short activity label.
  const fullDisplayName = displayNameForItem(item, null);

  return (
    <article
      className={_cn('qthread', 'tl-thread', `is-${cardStatusCss}`, isOpen && 'is-open-expanded')}
      onClick={onToggle}
      tabIndex={0}
      role="button"
      title={fullDisplayName || undefined}
      aria-label={fullDisplayName || undefined}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}
    >
      <header className="tl-card-head">
        {agent && (
          <Chip
            tone={agent === 'gpt' ? 'gpt' : 'claude'}
            leadingIcon={<AgentIcon agent={agent} size={12} />}
            label={agentName}
          />
        )}
        {/* Spec 0119 §8.8 — Phase 0 brief card is the only no-agent
            card; it gets a file-document glyph as its leading icon so
            it reads as "the document we're working from" rather than
            as an activity step. */}
        {!agent && item.kind === 'input' ? (
          <Chip
            tone="neutral"
            leadingIcon={<Icon.FileDocument size={12} />}
            label="brief"
          />
        ) : (
          <Chip mono tone="neutral" label={activityLabel.toLowerCase()} />
        )}

        {/* Spec 0124 — right-aligned cluster: per-category Q/D/I/C
            counter chips + status chip + chevron. margin-left:auto on
            .tl-card-head__right pins it to the trailing edge so the
            left group reads as [agent] [turn/brief] and the right
            edge reads as a stable counters→status→expand stack across
            a column of cards. */}
        <div className="tl-card-head__right">
          {/* Spec 0119 §8.1 — per-category summary chips in fixed
              Q→D→I→C order. Always present (zero-activity dims to
              0.55 opacity) so columns align across rounds. Clicking
              a chip jumps the critique pane to (category, round). */}
          {showCategoryChips && chipCategories.map((cat) => {
            const c = categories[cat] || { standing: 0, raised: 0, closed: 0, capped: 0 };
            const noActivity = (c.raised + c.closed) === 0;
            return (
              <Chip
                key={cat}
                tone={CATEGORY_TONE[cat]}
                categoryBubble={CATEGORY_BUBBLE[cat]}
                value={c.standing}
                add={c.raised}
                sub={c.closed}
                trailingSuffix={c.capped > 0 ? `⊘ ${c.capped}` : null}
                dim={noActivity}
                ariaLabel={`${CATEGORY_LABEL_PLURAL[cat]}: ${c.standing} standing, ${c.raised} raised, ${c.closed} closed${c.capped > 0 ? `, ${c.capped} capped` : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  dispatchCritiqueJump({
                    category: cat,
                    round: item.round,
                    phase,
                  });
                }}
              />
            );
          })}

          <TlStatusChip item={item} isLive={isLive} />

          <span
            className="tl-card-chev"
            aria-hidden="true"
            data-open={isOpen ? 'true' : undefined}
          >
            <Icon.Chevron />
          </span>
        </div>
      </header>

      {isOpen && (
        <>
          <div className="tl-thread__body">
            {repairExplainer || summary || gist || '—'}
          </div>
          <div className="tl-thread__actions">
            <button className="md-btn md-btn--tonal md-btn--sm" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
              Open full view
            </button>
            <span style={{ flex: 1 }}></span>
            <span className="md-chip md-chip--sm">
              {isRepair ? '0 tokens' : `${(totalTokens / 1000).toFixed(1)}kt in`}
            </span>
            <span className="md-chip md-chip--sm">
              {isRepair ? '$0.0000' : fmt.cost(cost)}
            </span>
          </div>
        </>
      )}
    </article>
  );
}

// ─── Spec 0115 — SourceRow + ItemCard (Critique pane v2) ───────────
//
// SourceRow is the per-evidence-record collapsible row inside a
// critique card. Multiple instances per card. Default collapsed:
// shows title + URL hostname + chevron. Expanded: full URL, fetched
// timestamp, search query, content excerpt (bounded scroll for long
// excerpts). Keyboard accessible.
//
// ItemCard is the card surface for one Item from the new event
// stream. It replaces the legacy QuestionThread for new-protocol
// runs (legacy runs keep their existing renderer).

function _hostnameOf(url) {
  try { return new URL(url).hostname; } catch { return url || ''; }
}

function SourceRow({ record }) {
  const [open, setOpen] = React.useState(false);
  const toggle = () => setOpen((v) => !v);
  const onKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  };
  const title = record.title || 'Untitled source';
  const hostname = _hostnameOf(record.url);
  const isUnverified = !!record.unverified;
  const excerpt = record.contentExcerpt || record.content_excerpt || '';
  // Long excerpts → bounded height with internal scroll. Spec 0115 §2.
  const excerptStyle = excerpt.length > 800
    ? { maxHeight: 200, overflowY: 'auto' }
    : null;
  return (
    <div className={`source-row ${open ? 'is-open' : ''} ${isUnverified ? 'is-unverified' : ''}`}>
      <div
        className="source-row__head"
        role="button"
        tabIndex={0}
        onClick={toggle}
        onKeyDown={onKey}
        aria-expanded={open}
      >
        <span className="source-row__chev" aria-hidden="true">{open ? '▼' : '▶'}</span>
        <span className="source-row__title">{title}</span>
        <span className="source-row__host">{hostname}</span>
        {isUnverified && (
          <span
            className="md-chip md-chip--sm md-chip--warn"
            title={record.unverifiedReason || record.unverified_reason || 'evidence flagged by validator'}
          >
            ⚠ unverified
          </span>
        )}
      </div>
      {open && (
        <div className="source-row__body">
          {record.url && (
            <div className="source-row__field">
              <span className="source-row__label">URL:</span>{' '}
              <a href={record.url} target="_blank" rel="noopener noreferrer">{record.url}</a>
            </div>
          )}
          {(record.fetchedAt || record.fetched_at) && (
            <div className="source-row__field">
              <span className="source-row__label">Fetched:</span>{' '}
              {record.fetchedAt || record.fetched_at}
            </div>
          )}
          {(record.searchQuery || record.search_query) && (
            <div className="source-row__field">
              <span className="source-row__label">Search query:</span>{' '}
              <code>{record.searchQuery || record.search_query}</code>
            </div>
          )}
          {excerpt && (
            <div className="source-row__excerpt-wrap">
              <div className="source-row__label">Content excerpt:</div>
              <pre className="source-row__excerpt" style={excerptStyle || undefined}>
                {excerpt}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ItemCard({ item, onHighlight }) {
  const kindLabel = ({
    question: 'Question',
    disagreement: 'Disagreement',
    issue: 'Issue',
    comment: 'Comment',
  })[item.kind] || item.kind;
  const stateLabel = item.currentState || item.current_state || 'open';
  const stateTone = ({
    resolved: 'ok',
    acknowledged: 'warn',
    withdrawn: 'muted',
    capped: 'error',
    open: 'info',
    addressed: 'info',
  })[stateLabel] || 'info';
  const raiserName = item.raiser === 'openai' ? 'GPT' : 'Claude';
  const transitions = item.transitions || [];
  const evidence = item.evidence || [];
  return (
    <article
      className={`item-card item-card--${stateLabel}`}
      onClick={onHighlight}
    >
      <header className="item-card__head">
        <span className="md-chip md-chip--sm"><code>{item.id}</code></span>
        <span className="md-chip md-chip--sm">{kindLabel}</span>
        <Chip tone={stateTone}>{stateLabel}</Chip>
        <span className="md-chip md-chip--sm">raised by {raiserName}</span>
        <span className="md-chip md-chip--sm">round {item.raisedRound || item.raised_round}</span>
      </header>
      <div className="item-card__body">
        {item.body}
        {item.anchorType && item.anchorType !== 'none' && (
          <blockquote className="item-card__anchor">
            {item.anchorType === 'quote' ? '> quote: ' : '> after: '}
            {item.anchorText || item.anchor_text}
          </blockquote>
        )}
      </div>
      {transitions.length > 0 && (
        <div className="item-card__timeline">
          <div className="item-card__timeline-hd">Timeline</div>
          {transitions.map((t, i) => {
            const fromS = t.fromState || t.from_state;
            const toS = t.toState || t.to_state;
            const actor = t.actor || '';
            const actorLabel = actor === 'openai' ? 'GPT'
                             : actor === 'claude' ? 'Claude'
                             : actor === 'mutual' ? 'Both (mutual)'
                             : actor === 'orchestrator' ? 'Orchestrator'
                             : actor;
            const via = t.via ? ` (${t.via})` : '';
            return (
              <div key={i} className="item-card__transition">
                <span className="item-card__transition-meta">
                  Round {t.round} — {fromS} → <strong>{toS}</strong>{via} · by {actorLabel}
                </span>
                {t.reason && (
                  <div className="item-card__transition-reason">{t.reason}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
      {evidence.length > 0 && (
        <div className="item-card__sources">
          <div className="item-card__sources-hd">Sources ({evidence.length})</div>
          {evidence.map((rec, i) => (
            <SourceRow key={i} record={rec} />
          ))}
        </div>
      )}
    </article>
  );
}

function TimelineTabs({ active, onChange, prominent = false }) {
  // Spec 0053 D4 — migrated from PaneButton to Tab (tabs-solid variant).
  const tabs = [
    { id: 'conversation', label: 'Conversation' },
    { id: 'consumption',  label: 'Consumption'  },
  ];
  return (
    <TabGroup variant="solid">
      {tabs.map((t) => (
        <Tab
          key={t.id}
          size={prominent ? 'md' : 'sm'}
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </Tab>
      ))}
    </TabGroup>
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

// Spec 0051 — billed vs content split.
//
// Two quantities matter for a turn's input on the Consumption tab:
//
//   • billed   = `in + cache_read + cache_write`. What the provider charged
//                for. For Anthropic this can far exceed the unique content
//                in the prompt — the Messages API re-reads the cached
//                prefix on every internal turn of a tool-use loop, and
//                each re-read counts as `cache_read_tokens`. Six web
//                searches with a 60kt cached prefix → ~420kt of cache_read.
//   • content  = the unique prompt content the model actually saw, once.
//                The frontend approximates this as the sum of the heuristic
//                `promptPieces` estimates (char ÷ 3.5 per piece).
//
// Pre-0051 the Consumption tab conflated these — it sized every input bar
// on `billed` and renormalised the pieces breakdown to sum to `billed`,
// which inflated the "Brief" sub-bar to 411kt on P1 Claude even though the
// brief is 60kt of distinct content. Spec 0051 separates the two:
//
//   • The total bar fills to `billed` (what we paid for; matches
//     context-window pressure too — each cache_read does occupy context
//     for that internal turn).
//   • The pieces sub-bars fill to their raw `promptPieces` size (content,
//     no renormalisation). They sum to roughly `content`, leaving a visible
//     gap inside the total bar.
//   • That gap = `billed - content` = the cache-reuse overlay. A small
//     "× N reuse" chip surfaces the multiplier in the card headline.
//
// `effectiveTokensIn` keeps its 0.47.1 hotfix semantic — it returns billed
// tokens — because every place that used it before (the shared
// denominator, the headline number, the percent-of-cap calculation) wants
// the billed number. New code uses `contentTokensIn` / `reuseInfo` when
// the question is "what unique content did the model see."
function effectiveTokensIn(usage) {
  if (!usage) return 0;
  return (Number(usage.in) || 0)
       + (Number(usage.cacheRead) || 0)
       + (Number(usage.cacheWrite) || 0);
}

// Sum of the heuristic `promptPieces` estimates — the unique content size,
// before any per-turn re-read inflation. Falls back to `effectiveTokensIn`
// when pieces are missing (pre-0030 transcripts) so older runs still show
// a sensible "content" number rather than zero.
function contentTokensIn(usage) {
  if (!usage) return 0;
  const pieces = usage.promptPieces || {};
  let sum = 0;
  for (const k of Object.keys(pieces)) {
    sum += Number(pieces[k]) || 0;
  }
  if (sum > 0) return sum;
  return effectiveTokensIn(usage);
}

// Returns the content / billed / reuse breakdown for a turn. `reused` is
// the amount of billed-but-not-unique content (the cache-amplification
// overlay). `hasReuse` is true when the reuse overlay is large enough to
// be worth surfacing — guards against tiny rounding-driven multipliers.
function reuseInfo(usage) {
  const billed  = effectiveTokensIn(usage);
  const content = contentTokensIn(usage);
  // Clamp content to billed defensively: the heuristic char ÷ 3.5
  // estimate occasionally overshoots tokeniser truth on symbol-heavy
  // text; we never want the bar to underflow.
  const contentClamped = Math.min(content, billed);
  const reused = Math.max(0, billed - contentClamped);
  const multiplier = contentClamped > 0 ? billed / contentClamped : 1;
  // Surface the chip only when reuse is materially > 1x. A 1.05x multiplier
  // would just be heuristic-vs-truth noise; 1.5x means real cache reuse.
  const hasReuse = reused > 0 && multiplier >= 1.5;
  return { content: contentClamped, billed, reused, multiplier, hasReuse };
}

// Spec 0051 B2 — protocol-slot mapping for each turn's output.
//
// Each turn's output lands in exactly one input slot in some later turn.
// The Consumption tab's output bar uses this to label the bar (`→ d1`,
// `→ hist`, etc.) and to colour it in the destination slot's colour, so
// the same artifact reads visually identical on this card (as output)
// and on later cards (as input).
//
//   phase 0 → null (preflight critique consumed by orchestrator for
//                   go/no-go; never inlined into a later turn's input)
//   phase 1 / claude → 'd1' (Claude's Phase 1 draft → P2 R1+, P3)
//   phase 1 / gpt    → 'd2' (GPT's Phase 1 draft → P2 R1+, P3)
//   phase 2          → 'hist' (every P2 round contributes to the
//                              accumulated history of later P2 rounds + P3)
//   phase 3          → 'draft' (drafter's converged document → P4 R1+).
//                              The non-drafter is silent in P3; we still
//                              return 'draft' here since the wire only
//                              records the drafter's TurnTokenUsage row.
//   phase 4          → 'histp' (every P4 round contributes to the
//                               accumulated review history of later P4
//                               rounds; P5 finalisation reads it).
function outputSlotFor(phase, agent) {
  const p = Number(phase);
  if (p === 0) return null;
  if (p === 1) return agent === 'gpt' ? 'd2' : 'd1';
  if (p === 2) return 'hist';
  if (p === 3) return 'draft';
  if (p === 4) return 'histp';
  return null;
}

// SPEC-0067 D9 — output bar labels expanded to full descriptions.
// P0 is the only turn whose output doesn't fold into a later input slot.
function outputBarLabel(phase, agent) {
  const slot = outputSlotFor(phase, agent);
  if (slot == null) return 'feeds preflight critique';
  const slotLabel = INPUT_PIECE_LABEL[slot] || slot;
  return `feeds ${slotLabel}`;
}

// Spec 0051 B4 — output cost is the biggest per-token rate (output is
// priced ~5× input on most models) and was previously hidden inside the
// "Tokens" aggregate. The Consumption tab now surfaces the input/output
// split so users can see *why* a turn was expensive.
//
// This client-side rate table mirrors `output_per_mtok` from
// `src/dual_research/agents/pricing.py::PRICING`. Kept as a small
// frontend constant rather than a wire-shipped field because (a) the
// table is short and changes rarely, (b) avoiding a schema bump keeps
// this spec frontend-only, (c) when a new model is added, this table
// gets updated alongside `pricing.py` — same pattern already in place
// for context-window tiers (`_CONTEXT_WINDOW_BY_MODEL` further down).
//
// If a model isn't in the table we fall back to a conservative $10/MTok
// (~Sonnet 4 ballpark) and mark the cost with a "~" in the tooltip so
// the user knows it's approximate. Backfill the table when a new model
// ships rather than chase silently.
const OUTPUT_RATE_PER_MTOK = {
  'claude-sonnet-4-6': 15.00,
  'claude-haiku-4-5':  5.00,
  'gpt-5.5':           10.00,
  'gpt-5.5-mini':      2.00,
  'gpt-5.5-nano':      0.50,
};
const OUTPUT_RATE_FALLBACK = 10.00;

function outputCostFor(usage) {
  if (!usage) return { cost: 0, approx: false };
  const out = Number(usage.out) || 0;
  if (out <= 0) return { cost: 0, approx: false };
  const modelId = usage.modelId || '';
  // Match server-side `lookup_pricing` semantics: exact key match first,
  // then prefix-match. Live model IDs include dated revision suffixes
  // (e.g. `gpt-5.5-2026-04-23`) that the pricing table doesn't carry.
  let rate = OUTPUT_RATE_PER_MTOK[modelId];
  if (rate == null) {
    for (const key of Object.keys(OUTPUT_RATE_PER_MTOK)) {
      if (modelId.startsWith(key)) { rate = OUTPUT_RATE_PER_MTOK[key]; break; }
    }
  }
  const effectiveRate = rate != null ? rate : OUTPUT_RATE_FALLBACK;
  return { cost: (out / 1_000_000) * effectiveRate, approx: rate == null };
}

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
      const tokensIn = effectiveTokensIn(u);
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
  5: 'P5 Final',
};

// SPEC-0086 — group flat consumption rows into per-phase clusters so
// the view can render a phase-name HEADER above each cluster instead
// of inside the row's leftmost cell. Returns
// ``[{phase, name, durationMs, rounds, rows: ConsumptionRow[]}]``.
//
// Rationale (per the user's repeated feedback on the Consumption tab):
// the inline phase-label cell ate ~100 px of horizontal space across
// every row; pulling the name into a header lets the agent cards
// reclaim the full pane width.
function groupConsumptionRowsByPhase(rows, run) {
  const timings = (run && run.phaseTimings) || {};
  // run.phaseTimings is keyed by phase number, but the Phase 5 timing
  // is stored under key '4' (the "P5 Final" label is really "Phase 4
  // ended at"). buildLiveTimeline encodes this with phaseId 5 →
  // phaseTimings['4']. Mirror that mapping here.
  const timingKeyFor = (phase) => (phase === 5 ? '4' : String(phase));
  // Number of rounds in a phase, derived from the rows that landed
  // under it (rounds with non-zero round index). Only meaningful for
  // P2 / P4.
  const groups = new Map();
  for (const r of rows) {
    if (!groups.has(r.phase)) {
      groups.set(r.phase, {
        phase: r.phase,
        name: PHASE_NAMES[r.phase] || `Phase ${r.phase}`,
        durationMs: Number(timings[timingKeyFor(r.phase)]) || 0,
        rounds: 0,
        rows: [],
      });
    }
    const g = groups.get(r.phase);
    g.rows.push(r);
    if (r.round > 0 && !r.isRepair) g.rounds = Math.max(g.rounds, r.round);
  }
  // Stable order: ascending phase number.
  return Array.from(groups.values()).sort((a, b) => a.phase - b.phase);
}

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
  const c = flagged ? COLORS.warn : 'var(--md-on-surface-faint)';
  return (
    <div className="mono" style={{
      paddingTop: 4, marginTop: 2,
      fontSize: 10.5, color: c,
      display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
    }}>
      <span style={{ color: 'var(--md-on-surface-faint)' }}>Provider-billed:{' '}
        <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>
          {fmt.cost(providerUsd)}
        </span>
      </span>
      <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
      <span style={{ color: c }}>
        Δ <span className="num">{deltaUsd >= 0 ? '+' : ''}{fmt.cost(deltaUsd)}</span>
        {' '}({deltaPct.toFixed(1)}%)
      </span>
      {flagged && (
        <span title="Per-row delta exceeds reconcile tolerance threshold."
              style={{ color: COLORS.warn, display: 'inline-flex', alignItems: 'center' }}>
          <Mdi name="alert" size={11} />
        </span>
      )}
    </div>
  );
}

// SPEC-0100 — CCX fill-class mapping for input sub-buckets.
// Maps promptPieces keys to the ccx CSS `.fl.*` class name.
const CCX_INPUT_FILL = {
  system: 'sys',
  brief:  'sys',
  d1:     'hist',
  d2:     'hist',
  plan:   'round',
  hist:   'hist',
  draft:  'resp',
  histp:  'hist',
};

// SPEC-0100 — CCX sub-bucket labels for the M3 anatomy.
const CCX_INPUT_LABEL = {
  system: 'system prompt',
  brief:  'brief',
  d1:     'Claude draft',
  d2:     'GPT draft',
  plan:   'agreed plan',
  hist:   'conversation history',
  draft:  'current draft',
  histp:  'review history',
};

function ConsumptionView({ run }) {
  const rows = React.useMemo(() => buildConsumptionRows(run), [run.phaseTokenUsage]);
  const [expanded, setExpanded] = React.useState(() => new Set());
  const toggleRow = React.useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);
  const scale = React.useMemo(() => computeConsumptionScale(rows, run), [rows, run]);

  if (rows.length === 0) {
    return <ConsumptionEmptyState />;
  }

  const groups = groupConsumptionRowsByPhase(rows, run);

  return (
    <div className="ccx-pane">
      <div className="ccx-pane__body">
        {groups.map((group, gi) => (
          <div key={group.phase}>
            <div className="phase-group-head">{group.name}</div>
            {group.rows.map((row, ri) => {
              const hasRound = !!row.label;
              const roundCount = group.rounds || 0;
              const phaseCode = `P${row.phase}`;
              const roundLabel = hasRound
                ? `round ${row.round} of ${roundCount}${row.isRepair ? ' repair' : ' soft'}`
                : null;
              return (
                <div key={row.id} className="cards-2up" style={{ marginBottom: 16 }}>
                  {['claude', 'gpt'].map((agent, ai) => (
                    <div key={agent}>
                      {hasRound && (
                        <div className="round-label">
                          <span className="pcode">{phaseCode}</span>
                          <span>&middot;</span>
                          <span>{roundLabel}</span>
                        </div>
                      )}
                      <CcxCard
                        usage={row[agent]}
                        agent={agent}
                        run={run}
                        scale={scale}
                        phase={row.phase}
                        expanded={expanded.has(row.id)}
                        onToggle={() => toggleRow(row.id)}
                        tourAnchor={gi === 0 && ri === 0 && ai === 0}
                      />
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <CcxLegend />
    </div>
  );
}

// SPEC-0086 — phase group header (kept for backwards compat; SPEC-0100
// replaces with .phase-group-head inline in ConsumptionView).
function ConsumptionPhaseHeader({ group }) {
  return null;
}

// SPEC-0086 ConsumptionRow — kept as stub; SPEC-0100 inlines into ConsumptionView.
function ConsumptionRow() { return null; }

// SPEC-0086 ConsumptionCard — kept as stub; SPEC-0100 replaces with CcxCard.
function ConsumptionCard() { return null; }

// ── Spec 0118 — Consumption-tab piece grouping & vocabulary detection ──

// Spec 0030 legacy piece-vocabulary keys. Detection is by key-presence:
// if a turn carries ANY non-legacy key, the new renderer is used; otherwise
// the legacy fallback path renders pre-0118 runs with their original labels.
const LEGACY_PIECE_KEYS = new Set(['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']);

// Legacy display names for the legacy renderer path. Tied to the 7-key
// spec 0030 vocabulary; only consulted when a turn's piecesRaw matches
// the legacy pattern (no spec-0118 canonical keys present).
const LEGACY_PIECE_LABELS = {
  brief: 'Brief',
  d1:    "Claude's Phase 1 draft",
  d2:    "GPT's Phase 1 draft",
  plan:  'Agreed plan',
  hist:  'Prior Phase 2 turns',
  draft: 'Current draft',
  histp: 'Prior Phase 4 turns',
};

// Spec 0118: detect new vocab by key-presence. Returns true iff piecesRaw
// contains any key NOT in the legacy 7-key set (i.e. at least one spec-
// 0117 canonical artifact ID). Empty dicts return false → legacy renderer.
function hasNewVocabPieces(piecesRaw) {
  if (!piecesRaw) return false;
  for (const k of Object.keys(piecesRaw)) {
    if (!LEGACY_PIECE_KEYS.has(k)) return true;
  }
  return false;
}

// Spec 0118 master grouping table (NORMATIVE). For each phase, which
// canonical artifact IDs collapse into the "System prompt" aggregate row,
// and which appear as their own separate rows. Output is handled outside.
const SYSTEM_PROMPT_AGGREGATE_KEYS = {
  0: ['system.task.input', 'prior_turns.phase0', 'ledger.standing_items', 'closeout.request'],
  1: ['system.task.research_plan', 'phase0.agreement.interpretation'],
  2: ['system.task.plan_negotiation', 'phase0.agreement.interpretation',
      'prior_turns.phase2', 'ledger.standing_items', 'closeout.request'],
  3: ['system.task.drafting', 'phase0.agreement.interpretation',
      'phase2.agreement.plan', 'carry_forward.phase2'],
  4: ['system.task.review', 'ledger.standing_items', 'closeout.request'],
};

const PHASE_SEPARATE_KEYS = {
  0: [],
  1: [],
  2: ['phase1.claude', 'phase1.openai'],
  3: ['phase1.claude', 'phase1.openai', 'all_p2_turns'],
  4: ['current_draft', 'prior_turns.phase4'],
};

// Group a piecesRaw dict (canonical-key vocab) into the per-phase row
// structure described in the spec 0118 master table.
//
// Returns { rows: [{ id, label, tokens, breakdown? }, ...] } where rows
// are in display order: user_prompt → phase-specific separates →
// System prompt aggregate. (Output is rendered separately.) The System
// prompt entry has a `breakdown: [{ id, tokens }, ...]` for the tooltip.
function groupPiecesForPhase(piecesRaw, phase) {
  const get = (k) => Number(piecesRaw?.[k]) || 0;
  const p = Number(phase);
  const sysKeys = SYSTEM_PROMPT_AGGREGATE_KEYS[p] || [];
  const sepKeys = PHASE_SEPARATE_KEYS[p] || [];

  const rows = [];
  // user_prompt always first (per spec § "Always-separate rows").
  rows.push({ id: 'user_prompt', tokens: get('user_prompt') });

  // Phase-specific separate rows.
  for (const k of sepKeys) {
    rows.push({ id: k, tokens: get(k) });
  }

  // System prompt aggregate (always present, even if tokens=0).
  const breakdown = sysKeys
    .map((k) => ({ id: k, tokens: get(k) }))
    .filter((x) => x.tokens > 0);
  const sysTotal = breakdown.reduce((s, x) => s + x.tokens, 0);
  rows.push({
    id: 'system_prompt',
    label: 'System prompt',
    tokens: sysTotal,
    breakdown,
  });

  return { rows };
}

// Spec 0030 fallback for pre-0118 runs. Returns rows in the order the
// legacy renderer used (brief, d1, d2, plan, hist, draft, histp), with
// legacy display names. Each row that ends up with zero tokens is dropped.
function legacyGroupPieces(piecesRaw) {
  const rows = [];
  for (const k of ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']) {
    const tokens = Number(piecesRaw?.[k]) || 0;
    if (tokens > 0) {
      rows.push({
        id: k,
        label: LEGACY_PIECE_LABELS[k] || k,
        tokens,
        legacy: true,
      });
    }
  }
  return { rows };
}

// Proportional cost share for a piece. The total INPUT cost is exact
// (API-billed); each piece's cost is its proportional share of that
// total. Returns 0 when billed_input_tokens is zero (defensive).
function piecePropCost(pieceTokens, billedInputTokens, totalInputCost) {
  if (!billedInputTokens || billedInputTokens <= 0) return 0;
  return (pieceTokens / billedInputTokens) * totalInputCost;
}

// Display-name resolver. Routes through the spec 0117 registry
// (window.DrArtifacts.displayName) so no display strings are hardcoded
// in the Consumption tab. Falls back to the artifact ID if the registry
// is missing (paranoid; the artifacts.jsx module always loads).
function consumptionLabel(artifactId) {
  if (window.DrArtifacts && typeof window.DrArtifacts.displayName === 'function') {
    return window.DrArtifacts.displayName(artifactId);
  }
  return artifactId;
}

// Multiline tooltip text for the System prompt aggregate row. Each line:
// "<display name>  <tokens>t". The "(proportional)" annotation on the
// header line signals the cost-share heuristic.
function systemPromptTooltip(breakdown, totalTokens, proportionalCost) {
  const lines = [];
  lines.push(
    `System prompt · ${fmt.tokens(totalTokens)}t · ${fmt.cost(proportionalCost)} (proportional)`,
    '',
  );
  for (const item of breakdown) {
    const lbl = consumptionLabel(item.id);
    const tokensStr = `${fmt.tokens(item.tokens)}t`;
    lines.push(`  ${lbl.padEnd(40, ' ')} ${tokensStr.padStart(8, ' ')}`);
  }
  return lines.join('\n');
}

// SPEC-0100 — CcxCard: M3 consumption card with collapsed + unfolded anatomy.
// Spec 0118 redesign: single Total tokens bar (collapsed) + per-phase
// canonical input rows (unfolded). Legacy 7-key vocab still renders via
// the fallback path so pre-0118 runs look reasonable.
function CcxCard({ usage, agent, run, scale, expanded = false, onToggle, tourAnchor, phase }) {
  const meta = AGENT_META[agent];
  const iconClass = agent === 'claude' ? 'a' : 'b';
  const fillIn = agent === 'claude' ? 'in' : 'in-b';
  const fillOut = agent === 'claude' ? 'out' : 'out-b';

  if (!usage) {
    return (
      <article className="ccx" data-tour-anchor={tourAnchor ? 'consumption-card' : undefined} style={{ opacity: 0.5, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 60 }}>
        <span style={{ fontSize: 12, color: 'var(--md-on-surface-faint)' }}>
          {meta.name} &middot; silent this turn
        </span>
      </article>
    );
  }

  const tokensIn   = effectiveTokensIn(usage);
  const tokensOut  = Number(usage.out) || 0;
  const totalTok   = tokensIn + tokensOut;
  const cost       = Number(usage.cost) || 0;
  const ctxWindow  = contextWindowFor(usage, run, agent);
  // Spec 0118 collapsed-card: context-window percent now uses
  // total = input + output (one bar = total tokens).
  const pctOfCap   = ctxWindow > 0 ? (totalTok / ctxWindow * 100) : 0;
  const denom      = scale?.denom || 1;
  const reuse      = reuseInfo(usage);
  const piecesRaw  = usage.promptPieces || {};
  const outputCost = outputCostFor(usage);

  const tokenCost  = Number(usage?.tokenCost ?? usage?.cost ?? 0) || 0;
  const outCostUsd = Number(outputCost?.cost) || 0;
  const inputCost  = Math.max(0, tokenCost - outCostUsd);
  const searchCost = Number(usage?.searchCost) || 0;
  const searches   = Number(usage?.searches) || 0;
  const queries    = Number(usage?.searchQueries) || 0;
  const hasSearches = searches > 0 || queries > 0 || searchCost > 0;

  // Spec 0118: single Total tokens bar. Scale is shared per-card-pair so
  // claude vs gpt widths remain comparable; we widen the denom slightly
  // for the total bar so input+output fits without saturating at 100%.
  const totalDenom = denom > 0 ? denom : Math.max(1, totalTok);
  const totalPct   = totalDenom > 0 ? Math.min(100, (totalTok / totalDenom) * 100) : 0;

  // Reuse overlay on the total bar (cache-reuse stripe). Covers the
  // billed-but-not-unique portion of the input — stays on the total bar
  // only (no per-row stripes per spec 0118).
  const reusePct = reuse.reused > 0 && totalDenom > 0
    ? Math.min(totalPct, (reuse.reused / totalDenom) * 100)
    : 0;

  // Vocabulary detection: new canonical-key vocab vs legacy 7-key vocab.
  const isNewVocab = hasNewVocabPieces(piecesRaw);
  const grouped = isNewVocab
    ? groupPiecesForPhase(piecesRaw, phase)
    : legacyGroupPieces(piecesRaw);

  // Sum of piece tokens used as denominator for proportional cost.
  // Use billed input tokens (exact) so per-piece costs sum to inputCost.
  const billedIn = tokensIn;

  // Row renderer: 3-column grid [label] [bar] [tokens · cost]
  const renderInputRow = (row) => {
    const label = row.label || consumptionLabel(row.id);
    const tokens = row.tokens || 0;
    const piecePct = totalDenom > 0 ? Math.min(100, (tokens / totalDenom) * 100) : 0;
    const propCost = piecePropCost(tokens, billedIn, inputCost);
    const isSystem = row.id === 'system_prompt';
    const tip = isSystem && row.breakdown
      ? systemPromptTooltip(row.breakdown, tokens, propCost)
      : undefined;
    return (
      <div key={row.id} className="ccx-bar-row" title={tip} style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)',
        alignItems: 'center', gap: 10,
        padding: '2px 0',
      }}>
        <span className="lbl" style={{
          fontSize: 11, color: 'var(--md-on-surface-muted)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{label}</span>
        <div className="ccx-bar" style={{ height: 6 }}>
          <div className={`fl ${fillIn}`} style={{ width: `${piecePct}%` }} />
        </div>
        <span className="num" style={{
          fontSize: 11, color: 'var(--md-on-surface-muted)', whiteSpace: 'nowrap',
          textAlign: 'right',
        }}>
          {fmt.tokens(tokens)}t &middot; {fmt.cost(propCost)}
        </span>
      </div>
    );
  };

  return (
    <article className="ccx" data-tour-anchor={tourAnchor ? 'consumption-card' : undefined} onClick={onToggle} style={{ cursor: 'pointer' }}>
      {/* Spec 0118 header: provider badge + agent name (left), bracketed
          context-window-% (right). No more separate total/cost in header. */}
      <header className="ccx-header">
        <span className={`ccx-icon ${iconClass}`}>{meta.name[0]}</span>
        <span className="nm">{meta.name}</span>
        <span className="stats" style={{ marginLeft: 'auto' }}>
          <span className="pct" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>
            ({pctOfCap.toFixed(1)}% of {_fmtCapLabel(ctxWindow)})
          </span>
        </span>
        <span className="chev" tabIndex={0} role="button" aria-expanded={expanded}
              aria-label={expanded ? 'Collapse' : 'Expand'}
              style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <span className="ms ms-20">expand_more</span>
        </span>
      </header>

      {/* Spec 0118 Total tokens bar (single bar replaces total-in / total-out).
          tokens · cost at the right edge. Cache stripe overlay retained. */}
      <div className="ccx-bar-row is-total" style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)',
        alignItems: 'center', gap: 10,
      }}>
        <span className="lbl">Total tokens</span>
        <div className="ccx-bar">
          <div className={`fl ${fillIn}`} style={{ width: `${totalPct}%` }} />
          {reuse.hasReuse && (
            <div className="reuse" style={{ left: 0, width: `${reusePct}%` }} />
          )}
        </div>
        <span className="num" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
          {fmt.tokens(totalTok)}t &middot; {fmt.cost(cost)}
        </span>
      </div>

      {/* Cache-reuse signal text (collapsed; spec 0051 line, retained) */}
      {reuse.hasReuse && (
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--md-on-surface-faint)', paddingTop: 2,
        }}>
          {fmt.tokens(reuse.content)}kt seen &middot; {fmt.tokens(reuse.billed)}kt billed
          {' '}(&times; {reuse.multiplier.toFixed(1)} token reuse)
          {' '}&middot; {fmt.tokens(tokensOut)}t out
        </div>
      )}

      {/* ── UNFOLDED SECTION (Spec 0118) ── */}
      {expanded && (
        <React.Fragment>
          {/* Divider between total bar and input rows */}
          <div className="ccx-divider" />

          {/* Per-phase input rows. Always-separate user_prompt + phase-
              specific separates + System prompt aggregate. */}
          {grouped.rows.map(renderInputRow)}

          {/* Divider between inputs and output row */}
          <div className="ccx-divider" />

          {/* Output row */}
          <div className="ccx-bar-row" style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)',
            alignItems: 'center', gap: 10,
            padding: '2px 0',
          }}>
            <span className="lbl" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
              Output
            </span>
            <div className="ccx-bar" style={{ height: 6 }}>
              <div className={`fl ${fillOut}`} style={{
                width: `${totalDenom > 0 ? Math.min(100, (tokensOut / totalDenom) * 100) : 0}%`,
              }} />
            </div>
            <span className="num" style={{
              fontSize: 11, color: 'var(--md-on-surface-muted)', whiteSpace: 'nowrap',
              textAlign: 'right',
            }}>
              {fmt.tokens(tokensOut)}t &middot; {fmt.cost(outCostUsd)}
            </span>
          </div>

          {/* Web-search cost line (orthogonal to spec 0118; kept here
              because it's the only place per-turn search cost surfaces). */}
          {hasSearches && (
            <div className="mono" style={{
              fontSize: 10.5, color: 'var(--md-on-surface-faint)', paddingTop: 4,
              textAlign: 'right',
            }}>
              Web search &middot; {queries || searches} queries &middot;{' '}
              {fmt.cost(searchCost)}
            </div>
          )}
        </React.Fragment>
      )}
    </article>
  );
}

// Spec 0046 D8 — clean per-card costs/counts cluster. Renders even on
// turns with zero searches (tokens + total only); the searches line is
// hidden when the turn used no web search.
//
// Spec 0051 B4 — the previously-aggregate "Tokens: $X" line is split
// into "Input: $A · Output: $B" so the output cost (often the dominant
// per-token rate — output is 5× input on most models) is visible.
// `outputCost` is computed client-side via the per-model rate table
// (see `outputCostFor`); when the model isn't in the table we fall back
// to a conservative rate and mark the figure with a "~" indicator in
// the tooltip. Input cost is `tokenCost - outputCost` so the two
// always sum to `tokenCost`, which preserves the existing invariant
// `tokenCost + searchCost == cost` end-to-end.
function CostsCluster({ usage, outputCost }) {
  const tokenCost = Number(usage?.tokenCost ?? usage?.cost ?? 0) || 0;
  const searchCost = Number(usage?.searchCost) || 0;
  const total = Number(usage?.cost ?? tokenCost) || 0;
  const searches = Number(usage?.searches) || 0;
  const queries  = Number(usage?.searchQueries) || 0;
  const hasSearches = searches > 0 || queries > 0 || searchCost > 0;
  // Split tokenCost into input + output. `outputCost` is approximate
  // when the model isn't in the rate table; `inputCost` is the residual
  // so the sum always reconciles to `tokenCost` exactly.
  const outCostUsd = Number(outputCost?.cost) || 0;
  const outApprox  = Boolean(outputCost?.approx);
  const inputCost  = Math.max(0, tokenCost - outCostUsd);
  const hasOutputCost = outCostUsd > 0;
  return (
    <div className="mono" style={{
      paddingTop: 6, borderTop: '1px solid var(--md-outline-hair)',
      fontSize: 10.5, color: 'var(--md-on-surface-faint)',
      display: 'flex', flexDirection: 'column', gap: 2,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span>Input:{' '}
          <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>
            {fmt.cost(inputCost)}
          </span>
        </span>
        {hasOutputCost && (
          <>
            <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
            <span
              title={outApprox
                ? 'Output cost approximated — model not in the frontend rate table; falling back to $10/MTok. Update OUTPUT_RATE_PER_MTOK in run-detail.jsx when a new model ships.'
                : 'Output cost computed from the model\'s output_per_mtok rate (mirrors src/dual_research/agents/pricing.py).'}
            >Output:{' '}
              <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>
                {outApprox ? '~' : ''}{fmt.cost(outCostUsd)}
              </span>
            </span>
          </>
        )}
        {hasSearches && (
          <>
            <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
            <span>Web search:{' '}
              <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>
                {fmt.cost(searchCost)}
              </span>
            </span>
          </>
        )}
        <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
        <span>Total:{' '}
          <span className="num" style={{ color: 'var(--md-on-surface-variant)', fontWeight: 500 }}>
            {fmt.cost(total)}
          </span>
        </span>
      </div>
      {hasSearches && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span>Searches:{' '}
            <span className="num" style={{ color: 'var(--md-on-surface-variant)' }}>
              {searches.toLocaleString()}
            </span>
          </span>
          {queries > 0 && (
            <>
              <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
              <span>Queries:{' '}
                <span className="num" style={{ color: 'var(--md-on-surface-variant)' }}>
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
      gridTemplateColumns: 'var(--consumption-label-w) 1fr 80px',
      alignItems: 'center', gap: 10,
      minWidth: 0,
    }}>
      <span style={{
        fontSize: accent ? 11 : 10.5,
        color: accent ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-muted)',
        fontWeight: accent ? 500 : 400,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {label}
      </span>
      <div style={{
        position: 'relative',
        width: '100%', height: accent ? 14 : 10,
        background: 'var(--md-surface-container-high)',
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
        fontSize: 10.5, color: 'var(--md-on-surface-muted)',
        textAlign: 'right', whiteSpace: 'nowrap',
      }}>
        {fmt.tokens(tokens)}t
      </span>
    </div>
  );
}

// Spec 0051 A — total input bar with content / reuse split.
//
// Layout: a solid-colour fill from 0 to `content` (the unique prompt
// content the model saw, the same amount the piece sub-bars sum to);
// then a striped overlay from `content` to `billed` (the cache-reuse
// region — same content re-read once or more by the provider). When
// `reused == 0` the bar fills solid edge-to-edge at `content` (which
// equals `billed`).
//
// The label cell + numeric cell match `SubInputBar` exactly so the new
// bar lines up with the piece breakdown directly underneath. The
// numeric cell shows `billed` since that's the headline number the
// percent-of-cap is computed against; the tooltip explains the
// content/billed split.
function TotalInputBar({ label, content, reused, billed, scale, color }) {
  const denom = scale?.denom || 1;
  const contentPct = denom > 0 ? Math.min(100, (content / denom) * 100) : 0;
  const reusedPct  = denom > 0
    ? Math.min(Math.max(0, 100 - contentPct), (reused / denom) * 100)
    : 0;
  const markerPct = (scale?.window > 0 && scale.window <= scale.denom)
    ? (scale.window / scale.denom) * 100
    : null;
  const tooltip = reused > 0
    ? `${fmt.tokens(content)}t unique content seen by the model\n`
      + `+ ${fmt.tokens(reused)}t cache reuse (same content, re-read)\n`
      + `= ${fmt.tokens(billed)}t total billed`
    : `${fmt.tokens(content)}t input`;
  return (
    <div title={tooltip} style={{
      display: 'grid',
      gridTemplateColumns: 'var(--consumption-label-w) 1fr 80px',
      alignItems: 'center', gap: 10,
      minWidth: 0,
    }}>
      <span style={{
        fontSize: 11, color: 'var(--md-on-surface-variant)', fontWeight: 500,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {label}
      </span>
      <div style={{
        position: 'relative',
        width: '100%', height: 14,
        background: 'var(--md-surface-container-high)',
        borderRadius: 3, overflow: 'hidden',
        border: '1px solid rgba(0,0,0,0.10)',
      }}>
        {/* Solid content fill */}
        {contentPct > 0 && (
          <div style={{
            position: 'absolute', top: 0, bottom: 0, left: 0,
            width: `${contentPct}%`,
            background: color,
            opacity: 0.9,
          }} />
        )}
        {/* Striped reuse overlay — same hue, diagonal stripes to read
            as "same content, repeated". Stripes use the agent colour at
            reduced opacity so the eye still groups the two segments. */}
        {reusedPct > 0 && (
          <div
            title="cache reuse — Anthropic's tool-use loop re-reads the cached prefix on every internal turn"
            style={{
              position: 'absolute', top: 0, bottom: 0,
              left: `${contentPct}%`,
              width: `${reusedPct}%`,
              backgroundImage:
                `repeating-linear-gradient(`
                + `45deg,`
                + ` ${color} 0px,`
                + ` ${color} 4px,`
                + ` rgba(0,0,0,0) 4px,`
                + ` rgba(0,0,0,0) 8px)`,
              opacity: 0.55,
            }}
          />
        )}
        {markerPct != null && markerPct < 100 && (
          <ContextWindowMarker pct={markerPct} label={_fmtCapLabel(scale.window)} />
        )}
      </div>
      <span className="mono num" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-muted)',
        textAlign: 'right', whiteSpace: 'nowrap',
      }}>
        {fmt.tokens(billed)}t
      </span>
    </div>
  );
}

// Spec 0051 B — output bar.
//
// Mirrors `SubInputBar` (same 3-column grid: label, bar, numeric) so it
// stacks cleanly under the input piece bars. The arrow prefix in the
// label (`→ d1`) cues that the output FEEDS the named slot in later
// turns' inputs — open the next round's card and the same colour shows
// up as a sub-bar by the same name. The bar fill is the destination
// slot's colour, not the agent colour, so the lineage reads visually
// regardless of which agent produced it.
function OutputBar({ label, tokens, scale, color, outputCost, modelId, slot }) {
  const denom = scale?.denom || 1;
  const widthPct = denom > 0 ? Math.min(100, (tokens / denom) * 100) : 0;
  const rateLine = outputCost?.cost > 0
    ? (outputCost.approx
        ? `~${fmt.cost(outputCost.cost)} (rate approximated — model not in OUTPUT_RATE_PER_MTOK; defaulting to $10/MTok)`
        : `${fmt.cost(outputCost.cost)} at the model's published output rate`)
    : '';
  const tooltip = [
    `${tokens.toLocaleString()}t output`,
    slot ? `feeds the \`${slot}\` slot in later turns' inputs` : 'feeds preflight critique (consumed by orchestrator for go/no-go)',
    rateLine,
    modelId ? `model: ${modelId}` : null,
  ].filter(Boolean).join('\n');
  return (
    <div
      data-output-slot={slot || undefined}
      title={tooltip}
      style={{
        display: 'grid',
        gridTemplateColumns: 'var(--consumption-label-w) 1fr 80px',
        alignItems: 'center', gap: 10,
        minWidth: 0,
      }}
    >
      <span style={{
        fontSize: 10.5,
        color: 'var(--md-on-surface-muted)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {label}
      </span>
      <div style={{
        position: 'relative',
        width: '100%', height: 10,
        background: 'var(--md-surface-container-high)',
        borderRadius: 3, overflow: 'hidden',
      }}>
        {widthPct > 0 && (
          <div style={{
            position: 'absolute', top: 0, bottom: 0, left: 0,
            width: `${widthPct}%`,
            background: color,
            opacity: 0.75,
          }} />
        )}
      </div>
      <span className="mono num" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-muted)',
        textAlign: 'right', whiteSpace: 'nowrap',
      }}>
        {fmt.tokens(tokens)}t
      </span>
    </div>
  );
}

// Spec 0051 A3 — small chip alongside the card headline when the
// turn's billed input exceeds its content size by a meaningful
// multiplier. The chip says "× N reuse" where N is the round-trip
// multiplier (billed / content). Reads as informational, not warning:
// neutral fg-3 tone, matches the existing chip-radius vocabulary.
function ReuseChip({ multiplier }) {
  const n = multiplier >= 10 ? Math.round(multiplier) : multiplier.toFixed(1);
  return (
    <span
      className="mono"
      title="cache reuse multiplier: the cached prompt prefix was read this many times across internal tool-use turns. Same content; provider bills each re-read."
      style={{
        display: 'inline-flex', alignItems: 'center',
        padding: '1px 6px',
        background: 'var(--info-bg, rgba(107,156,240,0.15))',
        border: `1px solid var(--info, rgba(107,156,240,0.55))`,
        borderRadius: 4,
        fontSize: 10, color: 'var(--info, #9ab6e8)',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
      }}
    >
      × {n} token reuse
    </span>
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
        background: 'var(--md-on-surface-faint)',
        opacity: 0.55,
      }} />
      <span className="mono" style={{
        position: 'absolute', left: `${pct}%`,
        top: -1, transform: 'translateX(-50%) translateY(-100%)',
        fontSize: 9, color: 'var(--md-on-surface-faint)',
        background: 'var(--md-surface-container-low)',
        padding: '0 3px', borderRadius: 2,
        whiteSpace: 'nowrap',
      }}>
        {label}
      </span>
    </React.Fragment>
  );
}

function searchCell(usage) {
  if (!usage) return <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>—</span>;
  const n = Number(usage.searches) || 0;
  return (
    <span className="mono num" style={{ fontSize: 11, color: 'var(--md-on-surface-variant)' }}>
      {n.toLocaleString()}
    </span>
  );
}

// SPEC-0086 — `TokenLaneCell` retired. The Consumption tab no longer
// renders compact top-row bars above the per-agent cards (which used
// to duplicate the total bar inside the expanded card). The card
// itself is now the click-to-expand surface; see `ConsumptionCard`.

// Spec 0030: the bar now renders one segment per prompt-piece kind
// from `usage.promptPieces` (Tk palette), renormalised against
// `usage.in` so heuristic-vs-provider-token mismatches don't distort
// segment widths. An output tail still trails the input region (darker
// shade, thinner band). When `promptPieces` is missing (pre-0030
// transcripts) we fall back to the spec-0029 single-fill rendering.
function TokenBar({ usage, agent, run, scale }) {
  const meta = AGENT_META[agent];
  const tokensIn  = effectiveTokensIn(usage);
  const freshIn   = Number(usage.in)  || 0;
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
  const reuse = reuseInfo(usage);

  // Spec 0051 A2/A4 — pieces use raw heuristic counts (no renormalisation
  // against billed `tokensIn`). The cache-reuse overlay is drawn as a
  // striped segment after the per-piece segments end.
  const piecesList = (() => {
    const present = KIND_ORDER.filter((k) => Number(piecesRaw[k]) > 0);
    return present.map((k) => ({
      kind: k,
      tokens: Number(piecesRaw[k]) || 0,
    }));
  })();
  const hasPieces = piecesList.length > 0;

  const inputPct  = Math.min(100, (tokensIn  / denom) * 100);
  const outputPct = Math.min(100 - inputPct, (tokensOut / denom) * 100);
  const reusedPct = Math.max(0, Math.min(100, (reuse.reused / denom) * 100));
  // Marker position for the context-window cap on a data-relative scale.
  // Only render the marker when the cap sits inside the visible bar range
  // (scale denom <= window) — when the bar IS sized to the cap, the
  // marker would just sit at 100% and is redundant.
  const showMarker = scale && scale.dataRelative && ctxWindow > 0
    && ctxWindow <= denom && (ctxWindow / denom) < 0.99;
  const markerPct = showMarker ? (ctxWindow / denom) * 100 : null;

  // Spec 0051 — tooltip splits content (unique input the model saw) from
  // billed (what the provider charged), so the asymmetry between the two
  // is auditable on hover without expanding the row.
  const tooltipLines = [
    `${meta.name} · ${modelId || 'unknown model'}`,
    reuse.hasReuse
      ? `input:  ${reuse.content.toLocaleString()}t seen · ${reuse.billed.toLocaleString()}t billed (× ${reuse.multiplier.toFixed(1)} token reuse)`
      : `input:  ${tokensIn.toLocaleString()}t`,
  ];
  if (reuse.hasReuse) {
    tooltipLines.push(`  ${freshIn.toLocaleString()}t fresh + ${cacheRead.toLocaleString()}t cache read`
      + (cacheWrite ? ` + ${cacheWrite.toLocaleString()}t cache write` : ''));
  }
  tooltipLines.push(
    `output: ${tokensOut.toLocaleString()}t`,
    `cost:   ${fmt.cost(cost)}`,
    `window: ${ctxWindow.toLocaleString()}t (${inputPct.toFixed(1)}% used)`,
  );
  if (hasPieces) {
    tooltipLines.push('', 'inputs:');
    for (const p of piecesList) {
      const lbl = KIND_COLORS[p.kind]?.label || p.kind;
      tooltipLines.push(`  ${lbl.padEnd(18, ' ')} ${p.tokens.toLocaleString()}t`);
    }
  }
  const tooltip = tooltipLines.filter((l) => l !== null).join('\n');

  return (
    <div title={tooltip} style={{
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      padding: '8px 10px', minHeight: 56,
      background: 'var(--md-surface-container)',
      border: `1px solid ${meta.border}`, borderRadius: 6,
    }}>
      {/* Bar */}
      <div style={{
        position: 'relative',
        width: '100%', height: 14,
        background: 'var(--md-surface-container-high)',
        borderRadius: 4, overflow: 'hidden',
      }}>
        {hasPieces ? (
          // Per-piece segments (spec 0030, now raw counts under spec 0051
          // A2/A4 — no renormalisation against billed tokens). Each
          // segment's width is its share of the shared denominator.
          // The cache-reuse overlay (striped segment) trails the pieces
          // when `reuse.reused > 0` so the bar still fills end-to-end at
          // `tokensIn` even though the solid segments sum only to
          // `content`.
          (() => {
            let offsetPct = 0;
            const segments = piecesList.map((p) => {
              const colour = KIND_COLORS[p.kind]?.bg || 'var(--md-on-surface-faint)';
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
            if (reusedPct > 0) {
              const stripeWidthPct = Math.min(100 - offsetPct, reusedPct);
              segments.push(
                <div key="__reuse__" style={{
                  position: 'absolute', top: 0, bottom: 0,
                  left: `${offsetPct}%`, width: `${stripeWidthPct}%`,
                  backgroundImage:
                    `repeating-linear-gradient(`
                    + `45deg,`
                    + ` ${meta.color} 0px,`
                    + ` ${meta.color} 4px,`
                    + ` rgba(0,0,0,0) 4px,`
                    + ` rgba(0,0,0,0) 8px)`,
                  opacity: 0.5,
                }} />
              );
            }
            return segments;
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
          bar's data-relative denominator.
          Spec 0051 A1/A3: when there's measurable cache reuse, the "in"
          number shows content seen (not billed) and a small reuse chip
          surfaces the multiplier — matches the expanded card's headline
          semantic so the two views agree at a glance. */}
      <div className="mono" style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginTop: 5,
        fontSize: 10, color: 'var(--md-on-surface-faint)',
      }}>
        {reuse.hasReuse ? (
          <>
            <span style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(reuse.content)}t</span>
            <span>seen</span>
            <span>·</span>
            <span style={{ color: 'var(--md-on-surface-faint)' }}>{fmt.tokens(reuse.billed)}t</span>
            <span>billed</span>
            <span>·</span>
            <span style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(tokensOut)}t</span>
            <span>out</span>
            <ReuseChip multiplier={reuse.multiplier} />
          </>
        ) : (
          <>
            <span style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(tokensIn)}t</span>
            <span>in</span>
            <span>·</span>
            <span style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(tokensOut)}t</span>
            <span>out</span>
          </>
        )}
        <span style={{ flex: 1 }} />
        <span>{((tokensIn / ctxWindow) * 100).toFixed(1)}% of {_fmtCapLabel(ctxWindow)}</span>
      </div>
    </div>
  );
}

// SPEC-0100 — sticky bottom legend (Issue 15).
function CcxLegend() {
  return (
    <footer className="ccx-pane__legend">
      <span className="legend-row">
        <span className="legend-sw a" />
        <span>Claude</span>
        <span className="legend-sw b" />
        <span>GPT</span>
      </span>
      <span className="legend-sep">|</span>
      <span className="legend-row">
        <span className="legend-sw solid" />
        <span>current charge</span>
        <span className="legend-sw striped" />
        <span>cache reuse</span>
        <span className="legend-sw web" />
        <span>web search</span>
      </span>
    </footer>
  );
}

function ConsumptionLegend() {
  // Kept for backwards compat — SPEC-0100 replaces with CcxLegend.
  return <CcxLegend />;
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
      padding: '32px 24px', background: 'var(--md-surface)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 12,
    }}>
      <div style={{ fontSize: 13, color: 'var(--md-on-surface-variant)', fontWeight: 500 }}>
        No per-turn token data
      </div>
      <div className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-faint)', textAlign: 'center',
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
      background: 'var(--md-surface-container-low)',
      borderBottom: '1px solid var(--md-outline-hair)',
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
        {/* SPEC-0087 § F — title typography is now CONSTANT regardless of
            whether the `left` slot is provided. Pre-spec the title was
            demoted to 11.5px / fg-3 muted gray when `left` carried
            navigation (Critique pane), creating a visible asymmetry
            with the Timeline pane's 14px / fg-0 title. The user flagged
            this twice — see the critique-pane chrome screenshot. */}
        <span style={{
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--md-on-surface)',
          letterSpacing: '-0.005em',
        }}>
          {title}
        </span>
        {count != null && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>
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

// Pane toolbar — min 44px, subtle bg to differentiate from content.
// SPEC-0072 D1: use minHeight so multi-row filter strips expand naturally.
function PaneToolbar({ children }) {
  return (
    <div style={{
      minHeight: 44,
      flexShrink: 0,
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 24px',
      background: 'var(--md-surface-container-low)',
      borderBottom: '1px solid var(--md-outline-hair)',
    }}>{children}</div>
  );
}

// Group header — tinted full-row bar with label + count. Used for OPEN /
// RESOLVED / ERRORS sections. The same shape as phase dividers in the
// timeline, just with status-keyed colors instead of neutral grey.
function GroupHeader({ label, color, count, style, tone = 'tinted' }) {
  const bg = tone === 'neutral'
    ? 'var(--md-surface-container)'
    : color + '14';
  const border = tone === 'neutral'
    ? 'var(--md-outline-hair)'
    : color + '44';
  const labelColor = tone === 'neutral' ? 'var(--md-on-surface-muted)' : color;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px',
      marginTop: 16, marginBottom: 8,
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 'var(--md-shape-sm)',
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

// SPEC-0071 D4: group flat timeline items into phase sections for collapsibility.
function groupTimelineByPhase(items) {
  const groups = [];
  let current = null;
  for (const item of items) {
    if (item.kind === 'phase-divider') {
      current = { divider: item, items: [] };
      groups.push(current);
    } else if (current) {
      current.items.push(item);
    } else {
      // Items before any phase divider — render ungrouped
      groups.push({ divider: null, items: [item] });
    }
  }
  return groups;
}

function PhaseDividerHeader({ item, run, open }) {
  const p = PHASES[item.phaseId];
  const current = item.phaseId === run.phase && run.status !== 'completed';
  return (
    <div data-phase-id={item.phaseId} style={{
      // SPEC-0087 § G — phase-header bands now ALL render at the same
      // width across phases. Pre-spec each band sized to its label
      // content, producing a ragged left edge across Phase 0 / 1 / 2 /
      // 3 / 4 / 5 (user-flagged in the 2026-05-18 follow-up). The 6 px
      // negative margins extend the band beyond the row content area
      // per the 14.49 spec; `calc(100% + 12px)` widens the box to
      // match so the right edge also overhangs.
      width: 'calc(100% + 12px)',
      boxSizing: 'border-box',
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px',
      marginTop: 16, marginBottom: 8,
      marginLeft: -6, marginRight: -6,
      background: 'var(--md-surface-container)',
      border: '1px solid var(--md-outline-variant)',
      borderRadius: 'var(--md-shape-sm)',
      whiteSpace: 'nowrap',
    }}>
      <span className="cs-chevron" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-muted)',
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 700,
      }}>
        Phase&nbsp;{item.phaseId}
      </span>
      <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
      <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)', fontWeight: current ? 700 : 600 }}>
        {p.label}
      </span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
        {item.duration ? fmt.duration(item.duration) : '—'}
        {item.extra ? ` · ${item.extra}` : ''}
      </span>
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
        <strong key={i} style={{ color: 'var(--md-on-surface)', fontWeight: 600 }}>
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
      borderTop: '1px solid var(--md-outline-variant)',
      padding: '10px 12px 12px',
      background: 'var(--md-surface-container-low)',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      {gist && (
        <div style={{
          fontSize: 11.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55,
          fontStyle: 'normal',
        }}>
          {renderInlineBold(gist)}
        </div>
      )}
      {summary && (
        <p style={{
          margin: 0,
          fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.6,
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
            color: 'var(--md-on-surface)',
            background: 'var(--md-surface-container)',
            border: '1px solid var(--md-outline-hair)',
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
        color: hasWarning ? COLORS.warn : 'var(--md-on-surface-muted)',
      }}>
      <Mdi name="magnify" size={11} />
      {hasWarning && <Mdi name="alert" size={10} color={COLORS.warn} />}
      <span>{base} · click to inspect</span>
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
    if (myProg.includes('conceded')) parts.push('resolved a held D-N'); // spec-0119:vocab-ok (legacy progression-action key)
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
      if (openQ > 0) standingParts.push(plur(openQ, 'open question'));
      if (openD > 0) standingParts.push(plur(openD, 'open disagreement'));
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
// render no chips. Phase 1 (plan draft) raises questions only.
// Phase 2 (negotiate) renders questions + disagreements. Phase 4
// (review) renders issues + comments + disagreements.
//
// Spec 0119 §7 — the legacy ``claim`` category is gone post-0114.
const PHASE_CHIP_ALLOWLIST = {
  0: [],
  1: ['questions'],
  2: ['questions', 'disagreements'],
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
      issue:        { raised: raised('issue'),        resolved: resolved('issue') },
      comment:      { raised: raised('comment'),      resolved: 0 },
    };
  }

  // Legacy fallback — parsed-item arrays, raised-count only.
  const filt = (arr) => (arr || []).filter((it) => it.raisedTurnKey === turnKey).length;
  return {
    question:     { raised: filt(run?.questions),     resolved: 0 },
    disagreement: { raised: filt(run?.disagreements), resolved: 0 },
    issue:        { raised: filt(run?.issues),        resolved: 0 },
    comment:      { raised: filt(run?.comments),      resolved: 0 },
  };
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

// Live (streaming) body — same UX as before but with a stable container.
function ArtifactLiveBody({ item }) {
  return (
    <div style={{
      padding: '0 14px 14px',
      borderTop: '1px dashed var(--md-outline-hair)',
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
    return <LoadingState size="inline" label="Loading…" />;
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
// Spec 0074 D2 — Agent Input tab first in every modal.
const TABS_CANON = ['input', 'content', 'webSearch', 'sources', 'files'];
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
// Spec 0117: map a UI ``item`` to its canonical artifact ID so every
// modal header can resolve through the registry's display_name().
function artifactIdFromItem(item) {
  if (!item) return null;
  const agent = item.agent === 'gpt' ? 'openai' : item.agent;
  const round = item.round || 1;
  if (item.kind === 'input') return 'user_prompt';
  if (item.kind === 'preflight' && agent) return `phase0.${agent}.r${round}`;
  if ((item.kind === 'plan' || item.kind === 'plan-live') && agent) return `phase1.${agent}`;
  if (item.kind === 'doc' || item.kind === 'doc-live') {
    return item.completed ? 'final.document' : 'current_draft';
  }
  if (item.kind === 'turn' || item.kind === 'turn-live') {
    if (item.statsPhase === 0 && agent) return `phase0.${agent}.r${round}`;
    if (item.statsPhase === 2 && agent) return `phase2.${agent}.r${round}`;
    if (item.statsPhase === 4 && agent) return `phase4.${agent}.r${round}`;
  }
  return null;
}

function displayNameForItem(item, fallback) {
  const id = artifactIdFromItem(item);
  if (id && typeof window !== 'undefined' && window.DrArtifacts) {
    return window.DrArtifacts.displayName(id);
  }
  return fallback;
}

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
  // Spec 0117 §5 single-mode header rule: display_name + producer
  // suffix when the artifact has one.
  let title = displayNameForItem(item, 'Document');
  let subtitle = null;
  if (item.kind === 'doc') {
    if (item.completed) {
      subtitle = meta ? `by ${meta.name}` : null;
    } else if (meta) {
      title = `${title} · drafted by ${meta.name}`;
    }
  } else if (item.kind === 'plan' || item.kind === 'plan-live') {
    // display_name already encodes the agent ("Claude's research plan").
  } else if (item.kind === 'turn' || item.kind === 'turn-live') {
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
      label: 'Agent Input',
      content: <InputTabContent turnKey={item.turnKey} />,
    },
    webSearch,
  ].filter(Boolean));
  const agentSlot = item.agent === 'claude' ? 'a' : item.agent === 'gpt' ? 'b' : null;
  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      agent={agentSlot}
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
  const badge = s && s.hasWarning ? <Mdi name="alert" size={11} color={COLORS.warn} /> : null;
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

  // Spec 0117 §5 — header resolves through the registry; the round
  // number is already encoded in the display name (e.g. "Negotiation
  // turn · Claude · round 3"). Subtitle keeps the reviewing-context
  // clue for readers.
  const turnLabel = typeof item.index === 'string' ? `turn ${item.index}` : `turn ${item.index || ''}`;
  const title = displayNameForItem(item, `${meta?.name || 'Agent'} — ${turnLabel}`);
  const subtitle = item.statsPhase === 4
    ? `reviewing the converged document`
    : `reviewing ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior content`;
  const agentSlot = item.agent === 'claude' ? 'a' : 'b';

  // SPEC-0058 SUR-12: RoundScrubber — find available rounds for this agent+phase.
  const timeline = React.useMemo(() => buildTimeline(run), [run]);
  const roundsForPhase = React.useMemo(() => {
    const seen = new Set();
    for (const t of timeline) {
      if (t.agent === item.agent && t.statsPhase === item.statsPhase && t.round != null) {
        seen.add(Number(t.round));
      }
    }
    return Array.from(seen).sort((a, b) => a - b);
  }, [timeline, item.agent, item.statsPhase]);
  const [scrubRound, setScrubRound] = React.useState(Number(item.round) || 1);
  // Find the timeline item for the scrubbed round.
  const scrubItem = React.useMemo(() => {
    if (Number(item.round) === scrubRound) return item;
    return timeline.find(
      (t) => t.agent === item.agent && t.statsPhase === item.statsPhase && Number(t.round) === scrubRound
    ) || item;
  }, [timeline, item, scrubRound]);
  // Recompute data when scrubbing to a different round.
  const scrubOtherFilePath = priorContentPathFor(scrubItem, otherAgent, run);
  const scrubReviewItems = reviewItemsFor(run, scrubItem);

  const scrubber = roundsForPhase.length > 1 ? (
    <RoundScrubber rounds={roundsForPhase} current={scrubRound} onChange={setScrubRound} />
  ) : null;

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      agent={agentSlot}
      variant="split"
      footer={scrubber}
    >
      {/* Spec 0116 — PhaseRail callsite removed (Notion issues 8 + 10).
          The 5-cell phase stepper duplicated context already shown in the
          run-detail header + the modal's own title/subtitle. The component
          itself (~`:712-732`) stays defined for future use. */}
      <div className="dr-modal-split">
        {/* Left: prior content + Input sub-tab (spec 0033).
            Spec 0044 D4: ``docTabs`` exposes the per-turn document
            context (other's prior turn / other's draft / brief / your
            draft / current converged draft). */}
        <NegotiateLeftPane
          item={scrubItem}
          otherAgent={otherAgent}
          priorFilePath={scrubOtherFilePath}
          docTabs={leftPaneTabsFor(scrubItem, otherAgent, run)}
          leftRef={leftRef}
          run={run}
        />

        {/* Right: review cards */}
        <div style={{
          minHeight: 0, minWidth: 0,
          display: 'flex', flexDirection: 'column',
          gap: 12,
          overflow: 'auto',
          paddingRight: 4,
        }}>
          <ReviewKeyboardHint hasItems={scrubReviewItems.length > 0} />
          {/* Spec 0120 — every panel uses the 0119 category-chip header.
              The raiser (= the turn's agent) and raised-round flow into
              each card's Provider / "raised in rN" chips. Phase 4 adds
              Issues + Comments groups; legacy ``Claims`` ReviewGroup
              was retired in 0119 §7 along with the claim data path. */}
          <ReviewGroup
            panelKind="question"
            color={COLORS.info}
            items={scrubReviewItems}
            kinds={['question']}
            raiser={scrubItem.agent}
            raisedRound={Number(scrubItem.round) || null}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            panelKind="disagreement"
            color={COLORS.warn}
            items={scrubReviewItems}
            kinds={['disagreement']}
            raiser={scrubItem.agent}
            raisedRound={Number(scrubItem.round) || null}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            panelKind="issue"
            color={COLORS.err}
            items={scrubReviewItems}
            kinds={['issue']}
            raiser={scrubItem.agent}
            raisedRound={Number(scrubItem.round) || null}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            panelKind="comment"
            color={COLORS.idle}
            items={scrubReviewItems}
            kinds={['comment']}
            raiser={scrubItem.agent}
            raisedRound={Number(scrubItem.round) || null}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          <ReviewGroup
            panelKind="resolved"
            color={COLORS.ok}
            items={scrubReviewItems}
            kinds={['resolved']}
            raiser={scrubItem.agent}
            raisedRound={Number(scrubItem.round) || null}
            activeIdx={activeIdx}
            onSelect={handleSelect}
          />
          {scrubReviewItems.length === 0 && (
            <div style={{
              padding: '20px 14px', textAlign: 'center',
              color: 'var(--md-on-surface-faint)', fontSize: 12.5,
              border: '1px dashed var(--md-outline-variant)',
              borderRadius: 'var(--md-shape-sm)',
              background: 'var(--md-surface-container)',
            }}>
              {/* Spec 0044 D5 — action-specific empty-state copy. */}
              {emptyStateCopy(scrubItem, run)}
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
function NegotiateLeftPane({ item, otherAgent, priorFilePath, docTabs, leftRef, run }) {
  // Spec 0116 — land on the "Original" sub-tab so the FIRST thing the user
  // sees inside a turn modal is what this agent was actually responding to:
  // counterpart's prior turn (Phase 2 r ≥ 2), counterpart's Phase 1 draft
  // (Phase 2 r1), or the Converged Draft (Phase 4). Resolves Notion issues
  // 8 + 10. The prior Spec 0085 default ('input' → AgentInputDualPane's
  // dual-bundle view) was confusing in a per-turn context where input vs
  // output is the natural mental model. 'input' stays one click away.
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
      background: 'var(--md-surface)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid var(--md-outline-hair)',
        background: 'var(--md-surface-container)',
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
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
            {activeDoc.path || '— no document available —'}
          </span>
        )}
        {sub === 'input' && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
            inputs/{item.turnKey || '—'}.json
          </span>
        )}
        {sub === 'webSearch' && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
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
          borderBottom: '1px solid var(--md-outline-hair)',
          background: 'var(--md-surface-container-low)',
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
        {sub === 'input' && <AgentInputDualPane item={item} run={run} />}
        {sub === 'webSearch' && <WebSearchTabContent turnKey={item.turnKey} />}
      </div>
    </div>
  );
}

// Spec 0044 D4 — small horizontal chip strip naming each document
// the agent had as input. Active chip is highlighted; click switches
// the left-pane content.
// Spec 0058 D4 — migrated to TabGroup line variant for doc strip.
function NegotiateDocTabs({ tabs, active, onChange }) {
  return (
    <TabGroup variant="line">
      {tabs.map((t) => (
        <Tab
          key={t.id}
          size="sm"
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </Tab>
      ))}
    </TabGroup>
  );
}

function NegotiateLeftSubTabs({ active, onChange, hasSearchWarning, showWebSearch }) {
  // Spec 0085 — Agent Input is the canonical first tab in every modal
  // (single-view from spec 0074; split-view aligned here per the
  // 2026-05-18 briefing, delta 15.13). Order is now:
  //   Agent Input → Original → Web Search (when present).
  // Spec 0058 D4 — TabGroup line variant.
  const tabs = [
    { id: 'input',     label: 'Agent Input' },
    { id: 'original',  label: 'Original' },
    showWebSearch && { id: 'webSearch', label: 'Web Search',
                       badge: hasSearchWarning ? <Mdi name="alert" size={11} color={COLORS.warn} /> : null },
  ].filter(Boolean);
  return (
    <TabGroup variant="line">
      {tabs.map((t) => (
        <Tab
          key={t.id}
          size="sm"
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.badge && (
            <span style={{ marginLeft: 4, display: 'inline-flex', alignItems: 'center' }}>
              {t.badge}
            </span>
          )}
        </Tab>
      ))}
    </TabGroup>
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
  // Spec 0085 — split-view modals open on Agent Input by default
  // (matches NegotiateLeftPane + the single-view modal default).
  const [sub, setSub] = React.useState('input');

  const onSectionAnchorClick = React.useCallback((sectionText) => {
    if (!leftRef.current || !sectionText || sub !== 'original') return;
    if (window.scrollAndFlash) {
      window.scrollAndFlash(leftRef.current, { text: sectionText.slice(0, 60) });
    }
  }, [sub]);

  // Spec 0044 D6 — structured items (Phase 1 open questions extracted
  // by spec 0042 D1; the legacy ``claim`` kind was retired by spec 0114
  // and the data path by spec 0119) get clickable cards that jump-to-
  // brief on the left pane. Anchors flow from each item's ``quote`` /
  // ``after`` / ``blockId`` to ``scrollAndFlash`` on the left pane's
  // brief view.
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

  // Spec 0117 §5 — header resolves to e.g. "Claude's research plan".
  const title = displayNameForItem(item, `${meta?.name || 'Agent'} — Phase 1 draft`);
  const subtitle = 'side-by-side with the brief';
  const agentSlot = item.agent === 'claude' ? 'a' : item.agent === 'gpt' ? 'b' : null;

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      agent={agentSlot}
      variant="split"
    >
      <div className="dr-modal-split">
        {/* Left: brief (with Original | Input sub-tabs, spec 0033). */}
        <div className="dr-modal-pane" style={{
          background: 'var(--md-surface)',
          border: '1px solid var(--md-outline-hair)',
          borderRadius: 'var(--md-shape-sm)',
        }}>
          <div style={{
            padding: '6px 12px',
            borderBottom: '1px solid var(--md-outline-hair)',
            background: 'var(--md-surface-container)',
            display: 'flex', alignItems: 'center', gap: 10,
            flexShrink: 0,
          }}>
            <NegotiateLeftSubTabs active={sub} onChange={setSub} />
            <span style={{ flex: 1 }} />
            <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
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
            into each Phase 1 open question and jump-to-brief. */}
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
      btn.textContent = 'brief';
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
      background: 'var(--md-surface)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid var(--md-outline-hair)',
        background: 'var(--md-surface-container)',
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
        <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>
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
            ? <LoadingState size="inline" label="Loading…" />
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
  // Spec 0058 D4 — migrated to TabGroup line variant.
  const tabs = [
    { id: 'draft',     label: 'Draft' },
    showWebSearch && { id: 'webSearch', label: 'Web Search',
                       badge: hasSearchWarning ? <Mdi name="alert" size={11} color={COLORS.warn} /> : null },
  ].filter(Boolean);
  return (
    <TabGroup variant="line">
      {tabs.map((t) => (
        <Tab
          key={t.id}
          size="sm"
          active={t.id === active}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.badge && (
            <span style={{ marginLeft: 4, display: 'inline-flex', alignItems: 'center' }}>
              {t.badge}
            </span>
          )}
        </Tab>
      ))}
    </TabGroup>
  );
}

// Spec 0044 D6 + Spec 0119 §7 — compact strip of structured Phase 1
// items (open questions) above the draft body. Each chip click jumps
// the left-pane brief to the item's anchored block. The legacy
// ``claim`` kind is gone post-0114; only questions and disagreements
// flow through here on new-protocol runs.
function Phase1ItemStrip({ items, onItemClick }) {
  return (
    <div style={{
      padding: '6px 12px',
      borderBottom: '1px solid var(--md-outline-hair)',
      background: 'var(--md-surface-container-low)',
      display: 'flex', alignItems: 'center', gap: 6,
      flexShrink: 0, overflow: 'auto',
    }}>
      <span className="mono" style={{
        fontSize: 10, color: 'var(--md-on-surface-faint)',
        letterSpacing: '0.06em', textTransform: 'uppercase',
        flexShrink: 0,
      }}>
        Items ({items.length}) →
      </span>
      {items.map((it, i) => {
        const tint = it.kind === 'question' ? COLORS.info : COLORS.warn;
        const glyph = it.kind === 'question' ? 'Q'
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
              background: 'var(--md-surface)',
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
              color: 'var(--md-on-surface-muted)',
              overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 180,
            }}>
              {(it.body || '').replace(/[*`]/g, '').slice(0, 60)}
            </span>
            <span style={{ color: 'var(--md-on-surface-faint)', fontSize: 10 }}>↗</span>
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
      background: 'var(--md-surface)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      color: 'var(--md-on-surface-faint)',
      fontSize: 10.5,
    }}>
      <kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container)', border: '1px solid var(--md-outline-variant)', borderRadius: 3 }}>j</kbd>
      <kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container)', border: '1px solid var(--md-outline-variant)', borderRadius: 3 }}>k</kbd>
      <span>walk · </span>
      <kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container)', border: '1px solid var(--md-outline-variant)', borderRadius: 3 }}>Esc</kbd>
      <span>close</span>
    </div>
  );
}

// Spec 0120 §5.4 — panel headers use the 0119 category-filter Chip so
// the modal's right-pane legend matches the critique pane's filter row.
// ``panelKind`` is one of the canonical four (question / disagreement /
// issue / comment) or the legacy curated ``resolved`` bucket; the
// latter gets a neutral chip since "resolved" isn't a category bubble.
const REVIEW_PANEL_CATEGORY = {
  question:     'questions',
  disagreement: 'disagreements',
  issue:        'issues',
  comment:      'comments',
};

function ReviewGroup({ panelKind, items, kinds, color, raiser, raisedRound, activeIdx, onSelect }) {
  // Render items in their original flat-list order, with indices for selection.
  const entries = items
    .map((it, i) => ({ it, i }))
    .filter(({ it }) => kinds.includes(it.kind));
  if (entries.length === 0) return null;
  const cat = REVIEW_PANEL_CATEGORY[panelKind];
  return (
    <div>
      <div className="rp-panel-head">
        {cat ? (
          <Chip
            tone={CATEGORY_TONE[cat]}
            categoryBubble={CATEGORY_BUBBLE[cat]}
            label={CATEGORY_LABEL_PLURAL[cat]}
            value={entries.length}
            ariaLabel={`${CATEGORY_LABEL_PLURAL[cat]}: ${entries.length}`}
          />
        ) : (
          <Chip tone="ok" label="Resolved / non-blocking" value={entries.length} />
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {entries.map(({ it, i }) => (
          <ReviewCard
            key={i}
            item={it}
            panelKind={panelKind}
            color={color}
            raiser={raiser}
            raisedRound={raisedRound}
            active={activeIdx === i}
            onClick={() => onSelect(i)}
          />
        ))}
      </div>
    </div>
  );
}

// Spec 0120 §5.2 + §5.3 — each card carries an explicit chip header
// (Provider · Category · raised-in-rN · Sources · modifier chips, in
// fixed 0119 §6 composition order) and a per-segment-labelled body
// (Anchor / Title / Rationale / Sources). The bare ``itemId`` chip
// from spec 0044 D6 is gone — per 0119 §6.6 the public ID is small
// mono text inside the body, never a primary header chip.
function ReviewCard({ item, panelKind, color, raiser, raisedRound, active, onClick }) {
  const hasAnchor = !!(item.quote || item.after);
  const isMissing = !!item.after;
  const cat = REVIEW_PANEL_CATEGORY[panelKind];
  const providerTone = raiser === 'claude' ? 'claude' : raiser === 'gpt' ? 'gpt' : 'neutral';
  const raiserName = raiser ? (AGENT_META[raiser]?.name || raiser) : null;
  const otherAgent = raiser === 'claude' ? 'gpt' : raiser === 'gpt' ? 'claude' : null;
  const otherName = otherAgent ? (AGENT_META[otherAgent]?.name || otherAgent) : 'the other agent';
  const evidence = Array.isArray(item.evidence) ? item.evidence : [];
  // Strip the anchor sub-lines from the body — the Anchor segment
  // below surfaces them separately; leaving them in the rationale
  // would render the same content twice.
  const rationaleBody = (window.DrItemBody
    ? window.DrItemBody.stripAnchorLines(item.body || '')
    : item.body || '');
  const { title, rationale } = (window.DrItemBody
    ? window.DrItemBody.splitTitleAndRationale(rationaleBody)
    : { title: '', rationale: rationaleBody });
  return (
    <button
      onClick={onClick}
      className={`rp-item-card${active ? ' is-active' : ''}${isMissing ? ' is-missing' : ''}`}
      style={{
        // The border-left color is data-driven (per-kind), so it stays
        // inline; the rest of the visual treatment is in components.css.
        borderLeftColor: isMissing ? COLORS.warn : color,
        cursor: hasAnchor ? 'pointer' : 'default',
      }}>
      <div className="rp-item-card-head">
        {raiser && (
          <Chip
            tone={providerTone}
            leadingIcon={<AgentIcon agent={raiser} size={12} />}
            label={raiserName}
          />
        )}
        {cat && (
          <Chip
            tone={CATEGORY_TONE[cat]}
            categoryBubble={CATEGORY_BUBBLE[cat]}
            label={CATEGORY_LABEL_SINGULAR[cat]}
          />
        )}
        {raisedRound != null && (
          <Chip mono tone="neutral" label={`raised in r${raisedRound}`} />
        )}
        {evidence.length > 0 && (
          <Chip tone="neutral" label="Sources" value={evidence.length} />
        )}
        {!hasAnchor && (
          <Chip mono tone="idle" label="no anchor" />
        )}
        {isMissing && (
          <Chip mono tone="warn" label="missing" />
        )}
        <span style={{ flex: 1 }} />
        {hasAnchor && (
          <span style={{ color: 'var(--md-on-surface-faint)', display: 'inline-flex' }}>
            <Icon.Arrow style={{ width: 12, height: 12 }} />
          </span>
        )}
      </div>
      <div className="rp-item-card-body">
        {item.quote && (
          <section className="rp-segment">
            <div className="rp-segment-label">{`Anchored to ${otherName}'s draft`}</div>
            <blockquote className="rp-anchor" style={{ borderLeftColor: color + '88' }}>
              {`“${item.quote}”`}
            </blockquote>
          </section>
        )}
        {item.after && (
          <section className="rp-segment">
            <div className="rp-segment-label">{`Anchored to ${otherName}'s draft`}</div>
            <div className="rp-anchor rp-anchor--after mono">{`after: ${item.after}`}</div>
          </section>
        )}
        {title && (
          <section className="rp-segment">
            <div className="rp-segment-label">Title</div>
            <div className="rp-title">{title}</div>
          </section>
        )}
        <section className="rp-segment">
          <div className="rp-segment-label">Rationale</div>
          <div className="rp-rationale">{rationale || '(no detail)'}</div>
        </section>
        {evidence.length > 0 && (
          <section className="rp-segment">
            <div className="rp-segment-label">{`Sources (${evidence.length})`}</div>
            <div className="rp-sources">
              {evidence.map((rec, i) => <SourceRow key={i} record={rec} />)}
            </div>
          </section>
        )}
        {item.itemId && (
          <div className="rp-item-card-id mono">id: {item.itemId}</div>
        )}
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

// ─────────────────── SPEC-0101 — AgentInputDualPane ──────────────────────────
// Two-pane M3 agent-input layout showing both agents' input bundles side by
// side. Pane A = Claude, Pane B = GPT. Each pane: AgentStrip + StatusBadge
// in the head, collapsible input sections in the body.
function AgentInputDualPane({ item, run }) {
  const timeline = React.useMemo(() => buildTimeline(run), [run]);
  const pairedTurn = React.useMemo(() => {
    return timeline.find(t =>
      t.agent !== item.agent &&
      t.statsPhase === item.statsPhase &&
      Number(t.round) === Number(item.round)
    );
  }, [timeline, item]);

  const agentAKey = item.agent === 'claude' ? item.turnKey : pairedTurn?.turnKey;
  const agentBKey = item.agent === 'gpt' ? item.turnKey : pairedTurn?.turnKey;

  return (
    <div className="agent-input">
      <AgentInputPane slot="a" turnKey={agentAKey} run={run} />
      <AgentInputPane slot="b" turnKey={agentBKey} run={run} />
    </div>
  );
}

function AgentInputPane({ slot, turnKey, run }) {
  const { bundle, loading, error } = window.useInputBundle(turnKey);
  const agentName = slot === 'a' ? 'Claude' : 'GPT';
  const statusLabel = run?.status || 'idle';

  return (
    <div className={`agent-input__pane agent-input__pane--${slot}`}>
      <div className="agent-input__head">
        <AgentStrip agent={slot} name={agentName} />
        <StatusBadge status={statusLabel} />
      </div>
      <div className="agent-input__body">
        {!turnKey && 'No paired turn available.'}
        {turnKey && loading && 'Loading…'}
        {turnKey && error && `Error: ${error}`}
        {turnKey && bundle && (() => {
          const pieces = bundle.pieces || {};
          const keys = INPUT_PIECE_ORDER
            .filter(k => k in pieces && pieces[k])
            .concat(Object.keys(pieces).filter(k => !INPUT_PIECE_ORDER.includes(k) && pieces[k]));
          if (keys.length === 0) return 'Empty input bundle.';
          return keys.map(k => (
            <InputSection
              key={k}
              piece={k}
              text={pieces[k] || ''}
              defaultCollapsed={INPUT_PIECE_DEFAULT_COLLAPSED.has(k)}
              isAgentDefault={k === 'system' && (bundle.system_source || 'recorded') === 'agent-default'}
            />
          ));
        })()}
      </div>
    </div>
  );
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

// Spec 0074 D3 — System prompt first (collapsed), user prompt second
// (expanded), then the rest in canonical content order. This matches the
// briefing's "what was fed to the agent" top-to-bottom ordering.
const INPUT_PIECE_ORDER = ['system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'];

// Spec 0074 D4 — system prompt collapsed by default (long boilerplate);
// brief (user prompt) expanded; everything else expanded.
const INPUT_PIECE_DEFAULT_COLLAPSED = new Set(['system']);

// Spec 0085 — 3-tier Agent Input panel:
//   1. System Prompt (always first, collapsed by default; rendered
//      with an italic "agent default" caveat when ``bundle.system_source``
//      is ``'agent-default'`` — i.e., the per-run system prompt wasn't
//      recorded and we synthesised it from current source).
//   2. User Prompt (= the brief, second, expanded by default).
//   3. Remaining canonical pieces (d1/d2/plan/hist/draft/histp) in the
//      existing canonical order, hidden if empty.
// The historical "Agent input bundle was not recorded" placeholder is
// retired — the backend always returns at least a synthesised System
// Prompt (per spec 0085 sections A+B), so the panel is never empty for
// a real turn.
function InputTabContent({ turnKey }) {
  const { bundle, loading, error } = window.useInputBundle(turnKey);

  if (!turnKey) {
    return <InputEmptyState label="No input record for this artifact." />;
  }
  if (loading) {
    return <LoadingState size="inline" label="Loading input bundle…" />;
  }
  if (error) {
    return <InputEmptyState label={`Could not load agent input bundle (${error}).`} />;
  }
  if (!bundle) {
    return <InputEmptyState label="No agent input bundle available for this turn." />;
  }
  const pieces = bundle.pieces || {};
  const systemSource = bundle.system_source || 'recorded';
  const renderKeys = INPUT_PIECE_ORDER
    .filter((k) => k in pieces && pieces[k])
    .concat(Object.keys(pieces).filter((k) => !INPUT_PIECE_ORDER.includes(k) && pieces[k]));

  if (renderKeys.length === 0) {
    return <InputEmptyState label="This turn's agent input bundle is empty." />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {renderKeys.map(key => (
        <InputSection
          key={key}
          piece={key}
          text={pieces[key] || ''}
          defaultCollapsed={INPUT_PIECE_DEFAULT_COLLAPSED.has(key)}
          isAgentDefault={key === 'system' && systemSource === 'agent-default'}
        />
      ))}
    </div>
  );
}

// Spec 0074 D4 — uses CollapsibleSection for consistent disclosure UX.
// Spec 0074 D5 — body rendered via Markdown instead of raw <pre>.
// Spec 0085 — when the system piece is the agent's default (not the
// per-run recorded prompt), prepend a small italic caveat inside the
// body so the user knows the displayed text may differ from what the
// historical run actually used.
function InputSection({ piece, text, defaultCollapsed, isAgentDefault }) {
  const label = INPUT_PIECE_LABEL[piece] || piece;
  const chars = text ? text.length : 0;
  const approxTokens = text ? Math.max(1, Math.round(text.length / 3.5)) : 0;
  const stats = `${chars.toLocaleString()} chars · ~${approxTokens.toLocaleString()}t`;

  return (
    <div className="agent-input-entry">
      <CollapsibleSection
        defaultOpen={!defaultCollapsed}
        renderTitle={({ open }) => (
          <>
            <span className="cs-chevron" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
            <span className="cs-title" style={{ fontWeight: 500, fontSize: 12 }}>{label}</span>
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>({piece})</span>
            {isAgentDefault && (
              <span
                className="chip tone-muted"
                style={{ marginLeft: 6, fontSize: 10, padding: '0 6px' }}
                title="The per-run system prompt was not recorded; showing the agent's current default."
              >
                agent default
              </span>
            )}
            <span style={{ flex: 1 }} />
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{stats}</span>
          </>
        )}
      >
        <div className="agent-input-body">
          {isAgentDefault && (
            <p style={{
              margin: '0 0 10px',
              padding: '8px 10px',
              fontStyle: 'italic',
              fontSize: 11.5,
              color: 'var(--md-on-surface-muted)',
              background: 'var(--md-surface-container)',
              borderLeft: '2px solid var(--md-outline-variant)',
              borderRadius: 'var(--md-shape-xs)',
            }}>
              This is the agent&apos;s current default system prompt — the per-run system
              prompt for this older turn was not recorded. The exact prompt the model
              saw may have differed.
            </p>
          )}
          <Markdown text={text} />
        </div>
      </CollapsibleSection>
    </div>
  );
}

function InputEmptyState({ label }) {
  return (
    <div style={{
      padding: '32px 16px',
      textAlign: 'center',
      color: 'var(--md-on-surface-faint)',
      fontSize: 12.5,
      border: '1px dashed var(--md-outline-variant)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container)',
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
    return <LoadingState size="inline" label="Loading search audit…" />;
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
          fontSize: 11.5, color: 'var(--md-on-surface-faint)',
          padding: '8px 10px',
          background: 'var(--md-surface-container)',
          border: '1px dashed var(--md-outline-variant)',
          borderRadius: 'var(--md-shape-sm)',
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
      borderRadius: 'var(--md-shape-sm)',
      border: `1px solid ${COLORS.warn}55`,
      background: 'rgba(212,160,86,0.10)',
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 12, color: COLORS.warn, fontWeight: 600,
      }}>
        <Mdi name="alert" size={12} />
        <span>
          {unmatched.length} citation{unmatched.length === 1 ? '' : 's'} reference{unmatched.length === 1 ? 's' : ''} a URL that wasn't in any retrieval set
        </span>
      </div>
      <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {unmatched.map((c, i) => (
          <li key={i} style={{ fontSize: 11.5, color: 'var(--md-on-surface-variant)' }}>
            <a href={c.url} target="_blank" rel="noopener noreferrer"
               style={{ color: 'var(--md-on-surface)', textDecoration: 'underline', wordBreak: 'break-all' }}>
              {c.url}
            </a>
            {c.title && (
              <span className="mono" style={{ display: 'block', color: 'var(--md-on-surface-faint)', fontSize: 10.5 }}>
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
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container-low)',
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
          color: 'var(--md-on-surface)',
          fontSize: 12,
          textAlign: 'left',
        }}
      >
        <span style={{
          display: 'inline-block', width: 10, textAlign: 'center',
          color: 'var(--md-on-surface-faint)', fontFamily: 'var(--md-font-data)',
        }}>{open ? '▾' : '▸'}</span>
        <span style={{ fontWeight: 500, flex: 1, minWidth: 0,
                       overflow: 'hidden', textOverflow: 'ellipsis',
                       whiteSpace: 'nowrap' }}>
          {queryLabel}
        </span>
        <span className="mono" style={{
          fontSize: 10, color: 'var(--md-on-surface-faint)',
          padding: '1px 6px',
          background: 'var(--md-surface-container)',
          border: '1px solid var(--md-outline-hair)',
          borderRadius: 999,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>{actionType}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
          {sources.length} result{sources.length === 1 ? '' : 's'}
          {citations.length > 0 && ` · ${citations.length} cited`}
        </span>
        {groupWarning && (
          <span title="A citation pinned to this query references a URL not in its retrieval set"
                style={{ color: COLORS.warn, display: 'inline-flex', alignItems: 'center' }}>
            <Mdi name="alert" size={12} />
          </span>
        )}
      </button>
      {open && (
        <div style={{
          borderTop: '1px solid var(--md-outline-hair)',
          padding: '10px 12px',
          background: 'var(--md-surface)',
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {sources.length === 0 ? (
            <div className="mono" style={{
              fontSize: 11, color: 'var(--md-on-surface-faint)',
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

// Spec 0058 SUR-13 — provider-symmetric ConsultedSourceCard.
// Both Anthropic and OpenAI sources render the same layout:
// title (or URL fallback) + host chip + page_age chip (when available)
// + cited_text block (when available) + [cited] tag.
// Missing fields render as muted placeholders instead of being hidden.
function ConsultedSourceCard({ source, isCited, citationsForSource }) {
  const url = source.url || '';
  let host = '';
  try { host = new URL(url).hostname; } catch { host = ''; }
  const title = source.title || null;
  const pageAge = source.page_age || null;
  return (
    <div style={{
      padding: '8px 10px',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container-low)',
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <a href={url} target="_blank" rel="noopener noreferrer"
           title={url}
           style={{
             color: title ? 'var(--md-on-surface)' : 'var(--md-on-surface-faint)',
             fontSize: 12.5, fontWeight: 500,
             textDecoration: 'none', wordBreak: 'break-word', minWidth: 0,
             fontStyle: title ? 'normal' : 'italic',
           }}>
          {title || host || url || '(no title)'}
        </a>
        {/* Host chip — always rendered when extractable */}
        {host && (
          <Chip tone="muted" style={{ height: 18, fontSize: '10.5px' }}>{host}</Chip>
        )}
        {/* Page age chip — rendered when available, placeholder when not */}
        {pageAge ? (
          <Chip tone="muted" style={{ height: 18, fontSize: '10px' }}>{pageAge}</Chip>
        ) : (
          <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-decor)', fontStyle: 'italic' }}>(no age)</span>
        )}
        <span style={{ flex: 1 }} />
        {isCited && (
          <Chip tone="info" style={{ height: 18, fontSize: '10px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>[cited]</Chip>
        )}
      </div>
      {/* Cited text blocks — always show the section, with placeholder if no text */}
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
        fontSize: 9.5, color: 'var(--md-on-surface-faint)',
        letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>
        cited from this URL
      </div>
      {text ? (
        <pre style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: 'var(--md-font-data)',
          fontSize: 11.5,
          lineHeight: 1.5,
          color: 'var(--md-on-surface-variant)',
        }}>{text}</pre>
      ) : (
        <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', fontStyle: 'italic' }}>
          (provider returned no source-side snippet)
        </div>
      )}
    </div>
  );
}

// Spec 0058 SUR-13 — symmetric CitationOnlyCard.
function CitationOnlyCard({ citation }) {
  const url = citation.url || '';
  let host = '';
  try { host = new URL(url).hostname; } catch { host = ''; }
  const title = citation.title || null;
  return (
    <div style={{
      padding: '8px 10px',
      border: '1px dashed var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container-low)',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <a href={url} target="_blank" rel="noopener noreferrer"
           title={url}
           style={{
             color: title ? 'var(--md-on-surface)' : 'var(--md-on-surface-faint)',
             fontSize: 12.5, fontWeight: 500,
             textDecoration: 'none', wordBreak: 'break-word',
             fontStyle: title ? 'normal' : 'italic',
           }}>
          {title || host || url || '(no title)'}
        </a>
        {host && (
          <Chip tone="muted" style={{ height: 18, fontSize: '10.5px' }}>{host}</Chip>
        )}
        <span style={{ flex: 1 }} />
        <Chip tone="info" style={{ height: 18, fontSize: '10px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>citation</Chip>
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
      color: 'var(--md-on-surface-faint)',
      fontSize: 12.5,
      border: '1px dashed var(--md-outline-variant)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container)',
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
      label: 'Agent Input',
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
      title={displayNameForItem(item, 'Input — brief')}
      subtitle={item.topic || ''}
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
      label: 'Agent Input',
      content: <InputTabContent turnKey={turnKey} />,
    },
    webSearch,
  ].filter(Boolean));
  const agentSlot = item.agent === 'claude' ? 'a' : item.agent === 'gpt' ? 'b' : null;
  return (
    <Modal
      open={true}
      onClose={onClose}
      title={displayNameForItem(item, `${meta?.name || 'Agent'} — brief critique`)}
      subtitle={item.topic || ''}
      agent={agentSlot}
      tabs={tabs}
    />
  );
}

function PreflightContentTab({ item }) {
  return <LazyMarkdownBody filePath={item.filePath} />;
}

function PreflightSourcesTab({ sources, loading }) {
  if (loading) {
    return <div className="mono" style={{ color: 'var(--md-on-surface-faint)', fontSize: 12 }}>loading…</div>;
  }
  if (sources.length === 0) {
    return <AttachmentsEmpty label="No external links were extracted from this brief." />;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {sources.map((s, i) => (
        <SourceRowAttachment key={i} attachment={s} />
      ))}
    </div>
  );
}

function PreflightFilesTab({ files, loading, runId }) {
  if (loading) {
    return <div className="mono" style={{ color: 'var(--md-on-surface-faint)', fontSize: 12 }}>loading…</div>;
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
      color: 'var(--md-on-surface-faint)',
      fontSize: 12.5,
      lineHeight: 1.6,
      border: '1px dashed var(--md-outline-variant)',
      borderRadius: 'var(--md-shape-sm)',
      background: 'var(--md-surface-container)',
    }}>
      {label}
    </div>
  );
}

// Hotfix — renamed from `SourceRow` to `SourceRowAttachment` to disambiguate
// from the spec 0115 `SourceRow({ record })` at ~`:1074`. Both names appearing
// at module scope caused Babel to throw "Identifier 'SourceRow' has already
// been declared", which crashed the whole run-detail page (RunDetail not
// defined). The two components have different prop shapes — keeping both is
// correct; only the name collision needed fixing.
function SourceRowAttachment({ attachment }) {
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
        background: 'var(--md-surface-container-low)',
        border: '1px solid var(--md-outline-hair)',
        borderRadius: 'var(--md-shape-sm)',
        textDecoration: 'none',
        color: 'var(--md-on-surface)',
      }}>
      <div style={{
        fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 500,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>{displayTitle}</div>
      <div className="mono" style={{
        fontSize: 11, color: 'var(--md-on-surface-faint)', marginTop: 3,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {host || url || '—'}
      </div>
      {caption && (
        <div style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', marginTop: 6, lineHeight: 1.55 }}>
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
      background: 'var(--md-surface-container-low)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        flex: 1, minHeight: 140,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--md-surface)',
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
            color: 'var(--md-on-surface-faint)', padding: 12, textAlign: 'center',
          }}>
            <Mdi name="file-document" size={28} />
            <span className="mono" style={{
              fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase',
            }}>{kind}</span>
          </div>
        )}
      </div>
      <div style={{ padding: '10px 12px' }}>
        <div title={title || ''} style={{
          fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 500,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{title || '(unnamed)'}</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--md-on-surface-faint)', marginTop: 4,
        }}>
          {[mime, size_bytes ? formatBytes(size_bytes) : null].filter(Boolean).join(' · ') || '—'}
        </div>
        {caption && (
          <div style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', marginTop: 6, lineHeight: 1.5 }}>
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
      <h2 style={{ margin: '0 0 10px', fontSize: 15, color: 'var(--md-on-surface)', fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.35 }}>
        Effects of urban density on residential heat-pump retrofit economics in temperate climates
      </h2>
      <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--md-on-surface-muted)', lineHeight: 1.6 }}>
        We assess the relationship between residential density and heat-pump retrofit economics across a cohort of 4,218 single-family households in IPCC Köppen-Geiger Cfa and (separately) Cfb climates between 2015 and 2024…
      </p>
      <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', lineHeight: 1.6 }}>
        §1 framing · §2 vintage taxonomy (5 buckets) · §3 heat-pump baseline · §4 financing (unified, with regressivity callout) · §5 cohort outcomes · §6 limitations · 12pp
      </div>
    </div>
  );
}

function ErrorCard({ item }) {
  return (
    <div style={{
      marginBottom: 6,
      padding: '12px 14px',
      background: 'rgba(217,106,106,0.04)',
      border: '1px solid rgba(217,106,106,0.30)',
      borderRadius: 'var(--md-shape-md)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <Icon.Warn style={{ color: COLORS.err }} />
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.err, letterSpacing: '0.04em' }}>{item.error.code}</span>
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>at {item.error.where}</span>
      </div>
      <pre className="mono" style={{ margin: 0, fontSize: 11.5, color: 'var(--md-on-surface-variant)', whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{item.error.detail}</pre>
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
      borderRadius: 'var(--md-shape-md)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <Icon.Warn style={{ color: COLORS.warn }} />
        <span className="mono" style={{ fontSize: 11.5, color: COLORS.warn, letterSpacing: '0.04em' }}>HARD_CAP_REACHED</span>
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55 }}>
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
  const issues = Array.isArray(run.issues) ? run.issues : [];
  const comments = Array.isArray(run.comments) ? run.comments : [];

  const isTerminal = run.status === 'completed'
    || run.status === 'deadlocked'
    || run.status === 'errored';

  const haveAny = (pid) =>
    questions.some(q => q.phase === pid) || disagreements.some(d => d.phase === pid);
  const initial = (run.phase === 4 || run.phase === 2) ? run.phase
                 : haveAny(4) ? 4
                 : haveAny(2) ? 2
                 : 2;
  const [selectedPhase, setSelectedPhase] = React.useState(initial);
  const [kindFilter, setKindFilter] = React.useState('all');
  const [agentFilter, setAgentFilter] = React.useState('all');
  const [statusFilter, setStatusFilter] = React.useState('all');
  React.useEffect(() => { setSelectedPhase(initial); setKindFilter('all'); setAgentFilter('all'); setStatusFilter('all'); }, [run.id, initial]);
  React.useEffect(() => {
    if (kindFilter === 'all') return;
    const allowed = PHASE_CHIP_ALLOWLIST[selectedPhase] || [];
    if (!allowed.includes(kindFilter)) setKindFilter('all');
  }, [selectedPhase, kindFilter]);
  React.useEffect(() => {
    if (kindFilter === 'questions' && statusFilter === 'drift') setStatusFilter('all');
  }, [kindFilter, statusFilter]);
  React.useEffect(() => {
    if (selectedPhase === 'summary' && !isTerminal) setSelectedPhase(initial);
  }, [isTerminal, selectedPhase, initial]);

  // Spec 0119 §8.1 + Q2 — cross-pane jump: a click on a timeline turn
  // card's category chip dispatches `dr-critique-jump` with
  // (category, round, phase); the critique pane snaps to that phase +
  // category filter and scrolls itself into view.
  React.useEffect(() => {
    const handler = (e) => {
      const detail = e.detail || {};
      const { category, phase: targetPhase } = detail;
      if (targetPhase === 2 || targetPhase === 4) {
        setSelectedPhase(targetPhase);
      }
      const validCategories = ['questions', 'disagreements', 'issues', 'comments'];
      if (validCategories.includes(category)) {
        setKindFilter(category);
      }
      // Bring the critique pane into the visible area.
      window.setTimeout(() => {
        const el = document.querySelector('.crit2');
        if (el && el.scrollIntoView) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 50);
    };
    window.addEventListener('dr-critique-jump', handler);
    return () => window.removeEventListener('dr-critique-jump', handler);
  }, []);

  const isSummary = selectedPhase === 'summary';
  const phaseQuestions = isSummary ? [] : questions.filter(q => q.phase === selectedPhase);
  const phaseDisagreements = isSummary ? [] : disagreements.filter(d => d.phase === selectedPhase);
  const phaseIssues = isSummary ? [] : issues.filter(i => i.phase === selectedPhase);
  const phaseComments = isSummary ? [] : comments.filter(c => c.phase === selectedPhase);

  const showI = kindFilter === 'all' || kindFilter === 'issues';
  const showQ = kindFilter === 'all' || kindFilter === 'questions';
  const showD = kindFilter === 'all' || kindFilter === 'disagreements';
  const showC = kindFilter === 'all' || kindFilter === 'comments';

  const matchesAgent = (it) => {
    if (agentFilter === 'all') return true;
    return it.raisedBy === agentFilter;
  };

  const findLedgerGhostRounds = (phaseId, itemId) => {
    const entries = (run && run.phaseLedgers && run.phaseLedgers[phaseId]) || [];
    const entry = entries.find((e) => e.id === itemId);
    return entry?.ghostedRounds || 0;
  };
  const isDrift = (it) => {
    const ghost = findLedgerGhostRounds(selectedPhase, it.id);
    return ghost > 0 && it.status === 'open';
  };

  // Determine the latest visible round for "new this round" vs "carried over".
  const _itemRound = (it, kind) => {
    if (kind === 'q' || kind === 'c') return it.raisedRound || 0;
    if (kind === 'd') return it.openedRound || it.round || 0;
    if (kind === 'i') return it.roundFirstSeen || 0;
    return 0;
  };
  let latestRound = 0;
  for (const q of phaseQuestions) latestRound = Math.max(latestRound, q.raisedRound || 0);
  for (const d of phaseDisagreements) latestRound = Math.max(latestRound, d.openedRound || d.round || 0);
  for (const i of phaseIssues) latestRound = Math.max(latestRound, i.roundFirstSeen || 0);
  for (const c of phaseComments) latestRound = Math.max(latestRound, c.raisedRound || 0);

  // Group by status into four buckets: openNew, openCarried, resolved, drift
  // Spec 0111 — strict allow-list per status; unknown statuses fall back to
  // openCarried (safest: keeps the item visible) with a dev console.warn so
  // a UI/data desync surfaces immediately. Resolves Notion issue 2 (an
  // `open` card was being bucketed under Resolved because Resolved was the
  // implicit `!== 'open'` default).
  //
  // Real backend statuses vary by kind (see src/dual_research/ui/models.py):
  //   - questions: 'open' | 'answered'
  //   - issues:    'open' | 'resolved'
  //   - disagreements: 'open' | 'resolved-claude' | 'resolved-gpt' | 'resolved-both'
  //   - comments:  no status field (non-blocking, "noted" / never closed)
  // Comments live in the Resolved bucket (their displayed status is
  // normalised to 'resolved' in _normalizeToThread below, so the visible
  // pill matches the bucket they sit in).
  const openNewItems = [];
  const openCarriedItems = [];
  const resolvedItems = [];
  const driftItems = [];
  const _isOpenStatus = (s) => s === 'open' || s === 'open-new';
  const _isResolvedStatus = (s) =>
    s === 'resolved' || s === 'answered' || // spec-0119:vocab-ok (legacy question.status value)
    (typeof s === 'string' && s.startsWith('resolved-'));
  const pushItem = (it, critiqueKind) => {
    const item = { ...it, _critiqueKind: critiqueKind };
    if (!matchesAgent(it)) return;
    const drift = isDrift(it);
    // Comments are non-blocking commentary — bucket as resolved (see header).
    const isComment = critiqueKind === 'c';
    const isResolved = isComment || _isResolvedStatus(it.status);
    if (statusFilter === 'open' && (isResolved || !_isOpenStatus(it.status) || drift)) return;
    if (statusFilter === 'resolved' && !isResolved) return;
    if (statusFilter === 'drift' && !drift) return;
    if (drift) {
      driftItems.push(item);
      return;
    }
    if (isResolved) {
      resolvedItems.push(item);
      return;
    }
    if (_isOpenStatus(it.status)) {
      const round = _itemRound(it, critiqueKind);
      if (round >= latestRound && latestRound > 0) {
        openNewItems.push(item);
      } else {
        openCarriedItems.push(item);
      }
      return;
    }
    // Unknown status — surface it in dev, keep item visible.
    if (typeof console !== 'undefined' && console.warn) {
      // eslint-disable-next-line no-console
      console.warn('[critique] unknown item.status:', it.status, it);
    }
    openCarriedItems.push(item);
  };
  if (showI) for (const i of phaseIssues) pushItem(i, 'i');
  if (showD) for (const d of phaseDisagreements) pushItem(d, 'd');
  if (showQ) for (const q of phaseQuestions) pushItem(q, 'q');
  if (showC) for (const c of phaseComments) pushItem(c, 'c');

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
  openNewItems.sort(byRound);
  openCarriedItems.sort(byRound);
  resolvedItems.sort(byRound);
  driftItems.sort(byRound);

  // Run-wide totals for Bar 1 (unfiltered, phase-scoped)
  const allPhaseItems = [...phaseQuestions, ...phaseDisagreements, ...phaseIssues, ...phaseComments];
  const runWideIntroduced = allPhaseItems.length;
  const runWideOpen = allPhaseItems.filter(it => it.status === 'open').length;
  const runWideResolved = allPhaseItems.filter(it => it.status !== 'open').length;

  // Kind-tab counts (filtered by agent + status)
  const filteredAll = [...openNewItems, ...openCarriedItems, ...resolvedItems, ...driftItems];
  const kindCounts = {
    all: filteredAll.length,
    issues: filteredAll.filter(it => it._critiqueKind === 'i').length,
    comments: filteredAll.filter(it => it._critiqueKind === 'c').length,
    questions: filteredAll.filter(it => it._critiqueKind === 'q').length,
    disagreements: filteredAll.filter(it => it._critiqueKind === 'd').length,
  };

  const handleHighlight = React.useCallback((keys, variant) => {
    if (onHighlightTurns) onHighlightTurns(keys, variant);
  }, [onHighlightTurns]);

  // Toggle handler for collapsible crit-group headers
  const toggleGroup = React.useCallback((e) => {
    const hd = e.currentTarget;
    const group = hd.closest('.crit-group');
    if (!group) return;
    const collapsed = group.getAttribute('data-collapsed') === 'true';
    group.setAttribute('data-collapsed', collapsed ? 'false' : 'true');
  }, []);

  // Spec 0097 — unified renderItem: all four kinds -> <QuestionThread />
  const renderItem = (item) => {
    const props = _normalizeToThread(item, run, selectedPhase);
    if (!props) return null;
    const highlightFn = () => {
      if (!handleHighlight) return;
      handleHighlight(props._highlightKeys, props._highlightVariant);
    };
    return (
      <QuestionThread
        key={item.id}
        id={props.id}
        kind={props.kind}
        status={props.status}
        raisedBy={props.raisedBy}
        raisedRound={props.raisedRound}
        phase={props.phase}
        turns={props.turns}
        footer={props.footer}
        onHighlight={highlightFn}
        // Spec 0111 — phase is implied by the surrounding .crit-group
        // header (rendered by CritiquePhaseContent); per-card chip would
        // be redundant. Other callsites keep the default (true).
        showPhaseChip={false}
      />
    );
  };

  // Spec 0115 — count-augmented kind tabs. Counts come from the new
  // unified Item bundle when available; legacy runs fall back to the
  // per-kind list lengths the legacy renderer already computes.
  const _itemsAll = (run.phaseStats?.items) || [];
  const _phaseItemsForCount = isSummary
    ? _itemsAll
    : _itemsAll.filter((it) => it.phase === selectedPhase);
  const _itemCountByKind = (kind) =>
    _phaseItemsForCount.filter((it) => it.kind === kind).length;
  // Prefer the new-bundle count when available (>0); else legacy.
  const _displayCount = (newCount, legacyCount) =>
    (newCount > 0 ? newCount : legacyCount);

  const KIND_TABS = [
    { id: 'all', label: 'All', tone: null,
      count: _phaseItemsForCount.length || undefined },
    { id: 'issues', label: 'Issues', tone: 'is-warn',
      count: _displayCount(_itemCountByKind('issue'), phaseIssues.length) },
    { id: 'comments', label: 'Comments', tone: null,
      count: _displayCount(_itemCountByKind('comment'), phaseComments.length) },
    { id: 'questions', label: 'Questions', tone: 'is-info',
      count: _displayCount(_itemCountByKind('question'), phaseQuestions.length) },
    { id: 'disagreements', label: 'Disagreements', tone: 'is-warn',
      count: _displayCount(_itemCountByKind('disagreement'), phaseDisagreements.length) },
  ].map((t) => ({
    ...t,
    label: (t.count != null && t.count > 0) ? `${t.label} (${t.count})` : t.label,
  }));

  // Render a collapsible crit-group section
  const renderGroup = (title, items, tone, countClass, collapsed) => {
    if (items.length === 0) return null;
    return (
      <section className="crit-group" data-collapsed={collapsed ? 'true' : 'false'} data-tone={tone}>
        <header className="crit-group__hd" role="button" tabIndex={0}
          onClick={toggleGroup}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleGroup(e); } }}>
          <span className="crit-group__chev"><span className="ms ms-20">expand_more</span></span>
          <span className="crit-group__title">
            {title}
            <span className={`crit-group__count ${countClass}`}>{items.length}</span>
          </span>
          {latestRound > 0 && <span className="crit-group__meta">round {latestRound}</span>}
        </header>
        <div className="crit-group__body">
          {items.map(renderItem)}
        </div>
      </section>
    );
  };

  return (
    <section className="crit2" data-tour-anchor="critique-pane">
      {/* BAR 1 — Title + Phase tabs + Totals + Drift chip */}
      <header className="bar1">
        <span className="ttl">Critique</span>
        <span className="vbar"></span>
        <div className="phase-tabs">
          <button
            className={`phase-tab${selectedPhase === 2 ? ' is-active' : ''}`}
            onClick={() => setSelectedPhase(2)}>
            <span className="pcode">P2</span><span className="pname">Negotiate</span>
          </button>
          <button
            className={`phase-tab${selectedPhase === 4 ? ' is-active' : ''}`}
            onClick={() => setSelectedPhase(4)}>
            <span className="pcode">P4</span><span className="pname">Review</span>
          </button>
          {isTerminal && (
            <button
              className={`phase-tab${selectedPhase === 'summary' ? ' is-active' : ''}`}
              onClick={() => setSelectedPhase('summary')}>
              <span className="sigma">{'\u03A3'}</span><span className="pname">Summary</span>
            </button>
          )}
        </div>
        <div className="right">
          <span className="crit-totals">
            <span><span className="n">{runWideIntroduced}</span><span className="lbl">introduced</span></span>
            <span><span className="n is-info">{runWideOpen}</span><span className="lbl">open</span></span>
            <span><span className="n is-ok">{runWideResolved}</span><span className="lbl">resolved</span></span>
          </span>
          {/* Spec 0119 §8.6 — run-wide drift chip retired from the
              critique-pane header. Per-phase ledger-drift now surfaces
              on the timeline phase header (commit 4); validate-run is
              the canonical surface for per-run drift totals. */}
        </div>
      </header>

      {/* BAR 2 — Spec 0119 §8.3 — chip-row legend.
          The filter row at the top of the Critique pane IS the
          canonical legend: every bubble + full-word + count appears
          here so anywhere a dense-form chip appears on the timeline,
          the reader can scroll to this row to confirm what each
          bubble means. */}
      {!isSummary && (
        <header className="bar2 crit-filter-row">
          {['questions', 'disagreements', 'issues', 'comments'].map((cat) => (
            <Chip
              key={cat}
              tone={CATEGORY_TONE[cat]}
              categoryBubble={CATEGORY_BUBBLE[cat]}
              label={CATEGORY_LABEL_PLURAL[cat]}
              value={kindCounts[cat] || 0}
              onClick={() => setKindFilter(cat)}
              data-active={kindFilter === cat ? 'true' : undefined}
              data-kind-filter="true"
              title={`Show only ${CATEGORY_LABEL_PLURAL[cat]}`}
            />
          ))}
          <Chip
            tone="neutral"
            label="All"
            value={kindCounts.all || 0}
            onClick={() => setKindFilter('all')}
            data-active={kindFilter === 'all' ? 'true' : undefined}
            data-kind-filter="true"
            title="Show all critique item types"
          />
          <span className="crit-filter-spacer" aria-hidden="true" />
          <Chip
            tone="info"
            leadingDot
            label="Open"
            value={runWideOpen}
            onClick={() => setStatusFilter(statusFilter === 'open' ? 'all' : 'open')}
            data-active={statusFilter === 'open' ? 'true' : undefined}
            title="Show only open items"
          />
          <Chip
            tone="ok"
            leadingDot
            label="Resolved"
            value={runWideResolved}
            onClick={() => setStatusFilter(statusFilter === 'resolved' ? 'all' : 'resolved')}
            data-active={statusFilter === 'resolved' ? 'true' : undefined}
            title="Show only resolved items"
          />
          {kindFilter !== 'questions' && (
            <Chip
              tone="warn"
              leadingDot
              label="Drift"
              onClick={() => setStatusFilter(statusFilter === 'drift' ? 'all' : 'drift')}
              data-active={statusFilter === 'drift' ? 'true' : undefined}
              title="Show only items with ledger drift"
            />
          )}
          <span className="crit-filter-spacer" aria-hidden="true" />
          <Chip
            tone={agentFilter === 'claude' ? 'claude' : 'neutral'}
            leadingIcon={<AgentIcon agent="claude" size={12} />}
            label="Claude"
            onClick={() => setAgentFilter(agentFilter === 'claude' ? 'all' : 'claude')}
            data-active={agentFilter === 'claude' ? 'true' : undefined}
            title="Show only items raised by Claude"
          />
          <Chip
            tone={agentFilter === 'gpt' ? 'gpt' : 'neutral'}
            leadingIcon={<AgentIcon agent="gpt" size={12} />}
            label="GPT"
            onClick={() => setAgentFilter(agentFilter === 'gpt' ? 'all' : 'gpt')}
            data-active={agentFilter === 'gpt' ? 'true' : undefined}
            title="Show only items raised by GPT"
          />
        </header>
      )}

      {/* BODY */}
      {isSummary ? (
        <CritiqueSummaryView run={run} questions={questions} disagreements={disagreements} />
      ) : (
        <CritiquePhaseContent
          run={run}
          phaseId={selectedPhase}
          openNewItems={openNewItems}
          openCarriedItems={openCarriedItems}
          resolvedItems={resolvedItems}
          driftItems={driftItems}
          latestRound={latestRound}
          onHighlight={handleHighlight}
          renderItem={renderItem}
          renderGroup={renderGroup}
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

// Spec 0097 — normalize any critique item into QuestionThread props.
// Restored after spec 0097 dropped the function definition while keeping one
// call site (line ~6182 inside the `k === 'c'` comment branch of
// _normalizeToThread). The canonical verify fixture used by spec 0097 had no
// comment items so the missing reference never fired during verify; runs that
// DO contain comment items (e.g. 27de = 20260518-083618-backend-language-
// choice) crashed the whole React tree with "ReferenceError:
// _parseSelfRaised is not defined" and rendered as a blank page.
function _parseSelfRaised(body) {
  if (!body) return { isSelfRaised: false, body: body || '' };
  const re = /\[Self-raised\]\s*/gi;
  if (!re.test(body)) return { isSelfRaised: false, body };
  const stripped = body.replace(/\[Self-raised\]\s*/gi, '').replace(/  +/g, ' ').trim();
  return { isSelfRaised: true, body: stripped };
}

function _normalizeToThread(item, run, phaseId) {
  const k = item._critiqueKind;
  const ledgerEntry = findLedgerEntry(run, phaseId || item.phase, item.id);
  const ghostedRounds = ledgerEntry?.ghostedRounds || 0;

  if (k === 'q') {
    const q = item;
    const isAnswered = q.status === 'answered'; // spec-0119:vocab-ok (legacy question.status value)
    const turns = [];
    turns.push({ agent: q.raisedBy, round: q.raisedRound, verdict: 'raised', quote: q.body || null });
    if (isAnswered && q.answeredBy) {
      // Spec 0119 §7.1 — legacy 'conceded'/'answered' resolution
      // collapses onto the canonical 'resolved' lifecycle verb.
      turns.push({ agent: q.answeredBy, round: q.answeredRound, verdict: 'resolved', quote: q.answerBody || null });
    }
    if (ghostedRounds > 0 && !isAnswered) {
      // Spec 0119 §7.1 — legacy 'ghosted' (unaddressed across rounds)
      // canonicalises to 'capped' (orchestrator-cap terminal state).
      turns.push({
        agent: q.raisedBy === 'claude' ? 'gpt' : 'claude',
        round: q.raisedRound + ghostedRounds,
        verdict: 'capped',
      });
    }
    const status = ghostedRounds > 0 && !isAnswered ? 'drift' : isAnswered ? 'resolved' : 'open';
    const footer = status === 'drift'
      ? 'drift \u00b7 recorded with full history \u00b7 does not block exit'
      : status === 'resolved'
      ? `resolved at round ${q.answeredRound} \u00b7 ${turns.length} turn${turns.length === 1 ? '' : 's'} to converge`
      : null;
    return {
      id: q.id, kind: 'question', status, raisedBy: q.raisedBy, raisedRound: q.raisedRound,
      phase: q.phase, turns, footer,
      _highlightKeys: [q.raisedTurnKey, q.answeredTurnKey].filter(Boolean),
      _highlightVariant: 'q',
    };
  }

  if (k === 'd') {
    const d = item;
    const isResolved = (d.status || '').startsWith('resolved');
    const turns = (d.progression || []).map((step, i) => ({
      agent: step.agent || 'claude',
      round: step.round,
      verdict: _mapVerdict(step.action),
      quote: step.note,
    }));
    const status = isResolved ? 'resolved' : 'open';
    const which = isResolved ? d.status.split('-')[1] : null;
    let footerText = null;
    if (isResolved) {
      const who = which === 'claude' ? 'Claude' : which === 'gpt' ? 'GPT' : which === 'both' ? 'both agents' : which;
      footerText = `resolved at round ${d.closedRound || '?'} \u00b7 conceded by ${who}`;
    }
    return {
      id: d.id, kind: 'disagreement', status, raisedBy: d.raisedBy,
      raisedRound: d.openedRound || d.round, phase: d.phase, turns, footer: footerText,
      _highlightKeys: [d.raisedTurnKey, d.closedTurnKey].filter(Boolean),
      _highlightVariant: 'd',
    };
  }

  if (k === 'i') {
    const issue = item;
    const isOpen = issue.status === 'open';
    const turns = [{ agent: issue.raisedBy, round: issue.roundFirstSeen, verdict: 'raised', quote: issue.body || null }];
    return {
      id: issue.id, kind: 'issue', status: isOpen ? 'open' : 'resolved',
      raisedBy: issue.raisedBy, raisedRound: issue.roundFirstSeen, phase: issue.phase, turns, footer: null,
      _highlightKeys: issue.raisedTurnKey ? [issue.raisedTurnKey] : [],
      _highlightVariant: 'd',
    };
  }

  if (k === 'c') {
    const comment = item;
    const { body: cleanedBody } = _parseSelfRaised(comment.body);
    const turns = [{ agent: comment.raisedBy, round: comment.raisedRound, verdict: 'raised', quote: cleanedBody || null }];
    // Spec 0111 — comments are non-blocking commentary with no closure
    // protocol. They were previously rendered with status='open' but
    // bucketed into Resolved by the prior `!== 'open'` default, which
    // produced the Notion issue 2 contradiction (open pill inside the
    // Resolved section). Rendering them as 'resolved' keeps them in the
    // Resolved bucket AND makes the visible status pill agree with the
    // section that holds them.
    return {
      id: comment.id, kind: 'comment', status: 'resolved',
      raisedBy: comment.raisedBy, raisedRound: comment.raisedRound, phase: comment.phase, turns, footer: null,
      _highlightKeys: comment.raisedTurnKey ? [comment.raisedTurnKey] : [],
      _highlightVariant: 'd',
    };
  }

  return null;
}

// Spec 0119 §7.1 — canonicalize legacy verbs into the lifecycle
// vocabulary: raised · addressed · resolved · acknowledged ·
// withdrawn · capped · "raised again". The lifecycle vocab is the
// source of truth across critique-card surfaces; this map lets the
// legacy negotiation-parser action strings ("conceded", "pushback",
// "ghosted") flow through into the new chip cluster without
// surfacing pre-0114 verbs to the user.
function _mapVerdict(action) {
  if (!action) return undefined;
  const a = action.toLowerCase().trim();
  // Already canonical.
  if (['raised', 'addressed', 'resolved', 'acknowledged', 'withdrawn', 'capped', 'raised again'].includes(a)) return a;
  // Item creation aliases.
  if (a === 'opened' || a === 'introduced' || a === 'flagged by') return 'raised';
  // Addressee response → addressed.
  if (a === 'pushback' || a === 'response' || a === 'responded' || a === 'restated' || a === 'noted' || a === 'flagged') return 'addressed'; // spec-0119:vocab-ok (legacy action-string canonicalisation)
  // Raiser accepts addressee's response → resolved.
  if (a === 'conceded' || a === 'answered' || a === 'agreed' || a === 'accepted') return 'resolved'; // spec-0119:vocab-ok (legacy action-string canonicalisation)
  // Orchestrator cap aliases (legacy "ghosted" = unaddressed across rounds; "drift" = ledger drift).
  if (a === 'ghosted' || a === 'drift') return 'capped'; // spec-0119:vocab-ok (legacy action-string canonicalisation)
  return a; // fallback — flagged by the VERDICT_VOCAB dev assertion
}

function CritiquePhaseContent({ run, phaseId, openNewItems, openCarriedItems, resolvedItems, driftItems, latestRound, onHighlight, renderItem, renderGroup }) {
  const pending = run.phase < phaseId || (phaseId === 4 && run.phase < 3);
  if (pending) {
    return (
      <div className="crit2__body" style={{ display: 'grid', placeItems: 'center' }}>
        <div style={{ textAlign: 'center', maxWidth: 280, lineHeight: 1.6, fontSize: 12.5, color: 'var(--md-on-surface-faint)' }}>
          {phaseId === 2 ? (
            <>
              <div style={{ marginBottom: 10, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <AgentIcon agent="claude" size={16} />
                <span className="mono" style={{ color: 'var(--md-on-surface-faint)' }}>{'\u2194'}</span>
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

  const totalVisible = openNewItems.length + openCarriedItems.length + resolvedItems.length + driftItems.length;
  if (totalVisible === 0) {
    return (
      <div className="crit2__body" style={{ display: 'grid', placeItems: 'center' }}>
        <div style={{ textAlign: 'center', maxWidth: 320, lineHeight: 1.6, color: 'var(--md-on-surface-faint)' }}>
          <div style={{ fontSize: 12 }}>no items match the current filters</div>
        </div>
      </div>
    );
  }

  return (
    <div className="crit2__body">
      {renderGroup('Open \u00b7 new this round', openNewItems, 'info', 'is-info', false)}
      {renderGroup('Open \u00b7 carried over', openCarriedItems, 'warn', 'is-warn', false)}
      {renderGroup('Resolved', resolvedItems, 'ok', 'is-ok', true)}
      {renderGroup('Drift', driftItems, 'err', 'is-err', true)}
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

// Spec 0046 D5 + Spec 0119 §7 — pluralised kind labels. The legacy
// ``claim`` kind is gone post-0114.
const KIND_PLURAL = {
  question: 'Questions',
  disagreement: 'Disagreements',
  issue: 'Issues',
  comment: 'Comments',
};

function CritiqueSummaryView({ run, questions, disagreements }) {
  const issues = Array.isArray(run?.issues) ? run.issues : [];
  const comments = Array.isArray(run?.comments) ? run.comments : [];

  // Per spec 0046 D5 + PHASE_CHIP_ALLOWLIST — only render kinds the
  // phase actually emits, so Phase 2 doesn't get an empty Issues
  // table and Phase 4 doesn't get an empty Questions table.
  const PHASE_KIND_ORDER = {
    2: ['question', 'disagreement'],
    4: ['issue', 'comment', 'disagreement'],
  };

  const _itemsFor = (kind, pid) => {
    const src = kind === 'question'     ? questions
              : kind === 'disagreement' ? disagreements
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
            fontSize: 12, fontWeight: 600, color: 'var(--md-on-surface-muted)',
            letterSpacing: '0.04em', textTransform: 'uppercase',
            margin: '0 0 8px',
          }}>{label}</h3>
          <div className="mono" style={{
            fontSize: 11.5, color: 'var(--md-on-surface-faint)',
            padding: '12px 14px',
            background: 'var(--md-surface-container-low)',
            border: '1px dashed var(--md-outline-hair)',
            borderRadius: 'var(--md-shape-sm)',
          }}>
            no critique items were raised in this phase
          </div>
        </section>
      );
    }
    return (
      <section style={{ marginBottom: 22 }}>
        <h3 style={{
          fontSize: 12, fontWeight: 600, color: 'var(--md-on-surface-muted)',
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

  // SPEC-0057 D6 — highest-leverage open thread: the question with the most
  // ghosted rounds, indicating a deadlock/neglect pattern. Renders as a
  // QuestionThread at the top of the summary.
  const highestLeverageThread = React.useMemo(() => {
    const allQ = [...questions, ...(Array.isArray(run?.issues) ? run.issues : [])];
    const openQ = allQ.filter(q => q.status === 'open');
    if (openQ.length === 0) return null;
    const entries = (run && run.phaseLedgers) || {};
    let best = null;
    let bestGhost = 0;
    for (const q of openQ) {
      const phase = q.phase || 2;
      const ledger = entries[phase] || [];
      const le = ledger.find(e => e.id === q.id);
      const ghost = le?.ghostedRounds || 0;
      if (ghost > bestGhost || (!best && ghost === 0)) {
        best = q;
        bestGhost = ghost;
      }
    }
    if (!best) return null;
    // Build minimal turns for the thread.
    const turns = [];
    if (best.raisedBy) {
      turns.push({ agent: best.raisedBy, round: best.raisedRound || 1, verdict: 'raised', quote: best.body || null, kind: 'origin' });
    }
    if (bestGhost > 0) {
      const other = best.raisedBy === 'claude' ? 'gpt' : 'claude';
      // Spec 0119 §7.1 — legacy 'ghosted' → 'capped' canonical verb.
      turns.push({ agent: other, round: (best.raisedRound || 1) + bestGhost, verdict: 'capped' });
    }
    const threadStatus = bestGhost > 0 ? 'drift' : 'open';
    const footer = bestGhost > 0 ? `Not addressed for ${bestGhost} round(s) — highest-leverage open item.` : null;
    return { question: best, turns, threadStatus, footer, ghostedRounds: bestGhost };
  }, [questions, run]);

  // SPEC-0072 D7-D10 — three-sentence summary copy generation.
  const summaryCopy = React.useMemo(() => {
    const totalQ = questions.length;
    const resolvedQ = questions.filter(q => q.status !== 'open').length;
    const totalD = disagreements.length;
    const resolvedD = disagreements.filter(d => (d.status || '').startsWith('resolved')).length;
    const totalI = issues.length;
    const resolvedI = issues.filter(i => i.status !== 'open').length;
    const totalC = comments.length;

    const totalItems = totalQ + totalD + totalI;
    const totalResolved = resolvedQ + resolvedD + resolvedI;
    const resolveRatio = totalItems > 0 ? totalResolved / totalItems : 1;

    // Count drift items across all phases.
    const ledgers = (run && run.phaseLedgers) || {};
    let driftCount = 0;
    for (const phaseId of Object.keys(ledgers)) {
      for (const entry of ledgers[phaseId]) {
        if (entry.ghostedRounds > 0) driftCount++;
      }
    }
    const driftRatio = totalItems > 0 ? driftCount / totalItems : 0;

    // D9: sentiment verdict vocabulary.
    let verdict;
    if (totalItems === 0) {
      verdict = 'Inconclusive';
    } else if (resolveRatio >= 0.7 && driftRatio < 0.2) {
      verdict = 'Mostly positive';
    } else if (resolveRatio < 0.4 || driftRatio >= 0.4) {
      verdict = 'Mostly negative';
    } else {
      verdict = 'Mixed';
    }

    // Sentence 1: sentiment verdict.
    const s1Parts = [`**${verdict}**`];
    if (totalItems > 0) {
      const pct = Math.round(resolveRatio * 100);
      s1Parts.push(` \u2014 ${pct}% of critique items resolved across both agents.`);
    } else {
      s1Parts.push(' \u2014 no critique items were raised in this run.');
    }
    const sentence1 = s1Parts.join('');

    // Sentence 2: qualitative line. Spec 0119 §7/§8 — canonical
    // resolution verb is 'resolved' across all kinds; legacy
    // 'answered'/'noted' phrasing retired.
    const qualParts = [];
    if (totalQ > 0) qualParts.push(`${totalQ} question${totalQ !== 1 ? 's' : ''} raised (${resolvedQ} resolved)`);
    if (totalD > 0) qualParts.push(`${totalD} disagreement${totalD !== 1 ? 's' : ''} raised (${resolvedD} resolved)`);
    if (totalI > 0) qualParts.push(`${totalI} issue${totalI !== 1 ? 's' : ''} flagged (${resolvedI} resolved)`);
    if (totalC > 0) qualParts.push(`${totalC} comment${totalC !== 1 ? 's' : ''} raised`);
    const sentence2 = qualParts.length > 0 ? qualParts.join(', ') + '.' : '';

    // Sentence 3: drift note if any.
    const sentence3 = driftCount > 0
      ? `${driftCount} item${driftCount !== 1 ? 's' : ''} drifted without response for multiple rounds.`
      : '';

    return [sentence1, sentence2, sentence3].filter(Boolean).join(' ');
  }, [questions, disagreements, issues, comments, run]);

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--md-surface)' }}>
      <div style={{ padding: '16px 24px 28px' }}>
        {/* SPEC-0072 D7-D10 — three-sentence summary */}
        {summaryCopy && (
          <div style={{ marginBottom: 20, fontSize: 13, lineHeight: 1.6, color: 'var(--md-on-surface-variant)' }}>
            <Markdown text={summaryCopy} />
          </div>
        )}
        {/* SPEC-0057 D6 — highest-leverage thread as opening artifact */}
        {highestLeverageThread && (
          <div style={{ marginBottom: 20 }}>
            <div style={{
              fontSize: 11, fontWeight: 600, color: 'var(--md-on-surface-muted)',
              letterSpacing: '0.06em', textTransform: 'uppercase',
              marginBottom: 8,
            }}>
              Highest-leverage open item
            </div>
            <QuestionThread
              id={highestLeverageThread.question.id}
              kind="question"
              status={highestLeverageThread.threadStatus}
              raisedBy={highestLeverageThread.question.raisedBy}
              raisedRound={highestLeverageThread.question.raisedRound}
              phase={highestLeverageThread.question.phase}
              turns={highestLeverageThread.turns}
              footer={highestLeverageThread.footer}
            />
          </div>
        )}
        <div style={{
          fontSize: 11.5, color: 'var(--md-on-surface-faint)', lineHeight: 1.55, marginBottom: 16,
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

// Spec 0046 D5 + Spec 0119 §7 — one table per kind. Per-row counts
// split by agent; the Open column carries the cumulative still-open
// count after the round in question. The closed-column label is now
// uniformly 'resolved' across kinds (legacy 'answered'/'noted'
// retired).
function SummaryKindTable({ kind, items, rows, totalOpen, totalResolved }) {
  const closedLabel = 'resolved';
  // Comments don't have a closure protocol — drop the resolved
  // columns + Open column to keep the table honest.
  const isStateless = kind === 'comment';

  return (
    <div style={{ marginBottom: 14 }}>
      <div className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.04em',
        textTransform: 'uppercase',
        display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap',
        marginBottom: 6,
      }}>
        <span style={{ color: 'var(--md-on-surface-variant)', fontWeight: 600 }}>{KIND_PLURAL[kind] || kind}</span>
        <span>·</span>
        <span>{items.length} total</span>
        {!isStateless && (
          <>
            <span>·</span>
            <span style={{ color: totalResolved > 0 ? COLORS.ok : 'var(--md-on-surface-faint)' }}>
              {totalResolved} {closedLabel}
            </span>
            <span>·</span>
            <span style={{ color: totalOpen > 0 ? COLORS.warn : 'var(--md-on-surface-faint)' }}>
              {totalOpen} open
            </span>
          </>
        )}
      </div>
      <table style={{
        width: '100%', borderCollapse: 'collapse',
        fontSize: 12, color: 'var(--md-on-surface-variant)',
        background: 'var(--md-surface-container-low)',
        border: '1px solid var(--md-outline-hair)',
        borderRadius: 'var(--md-shape-sm)',
        overflow: 'hidden',
        fontFamily: 'var(--md-font-data)',
      }}>
        <thead>
          <tr style={{ background: 'var(--md-surface-container)', textAlign: 'left' }}>
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
            <tr key={r.round} style={{ borderTop: '1px solid var(--md-outline-hair)' }}>
              <td style={_summaryTd}>R{r.round}</td>
              <td style={_summaryTd}>{r.claudeRaised || '—'}</td>
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.claudeResolved > 0 ? COLORS.ok : 'var(--md-on-surface-faint)',
                }}>{r.claudeResolved || '—'}</td>
              )}
              <td style={_summaryTd}>{r.gptRaised || '—'}</td>
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.gptResolved > 0 ? COLORS.ok : 'var(--md-on-surface-faint)',
                }}>{r.gptResolved || '—'}</td>
              )}
              {!isStateless && (
                <td style={{
                  ..._summaryTd,
                  color: r.stillOpen > 0 ? COLORS.warn : 'var(--md-on-surface-faint)',
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
  fontSize: 10, color: 'var(--md-on-surface-faint)',
  letterSpacing: '0.06em', textTransform: 'uppercase',
  fontWeight: 600,
};
const _summaryTd = {
  padding: '7px 10px',
  fontSize: 12, color: 'var(--md-on-surface-variant)',
};

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
      color: 'var(--md-on-surface-muted)',
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
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{label}</span>
    </span>
  );
}

function PhaseContent({ run, phaseId, open, resolved, introduced }) {
  const pending = run.phase < phaseId || (phaseId === 4 && run.phase < 3);
  if (pending) {
    return (
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--md-on-surface-faint)', background: 'var(--md-surface)' }}>
        <div style={{ textAlign: 'center', maxWidth: 280, lineHeight: 1.6, fontSize: 12.5 }}>
          {phaseId === 2 ? (
            <>
              <div style={{ marginBottom: 10, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <AgentIcon agent="claude" size={16} />
                <span className="mono" style={{ color: 'var(--md-on-surface-decor)' }}>↔</span>
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
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--md-on-surface-faint)', background: 'var(--md-surface)' }}>
        <div style={{ textAlign: 'center', maxWidth: 320, lineHeight: 1.6 }}>
          <div className="mono" style={{ fontSize: 12 }}>no disagreements in this phase</div>
          {suspectedMiss && (
            <div className="mono" style={{ fontSize: 11, marginTop: 10, color: COLORS.warn, opacity: 0.85, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Mdi name="alert" size={11} />
              <span>couldn't reconstruct disagreements from this run — open the round files directly</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--md-surface)' }}>
      {/* Spec 0116 — flex column + gap: 8 so card spacing comes from the
          parent (parallel to the inline-margin removal on .qthread in
          shared.jsx:1117). "Resolved" GroupHeader's compensating
          marginTop drops 20 → 12 because the parent gap contributes 8. */}
      <div style={{
        padding: '6px 24px 28px',
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {open.length > 0 && <GroupHeader label="Open" color={COLORS.warn} count={open.length} />}
        {open.map(d => {
          const props = _normalizeToThread({ ...d, _critiqueKind: 'd' }, run, phaseId);
          return props ? <QuestionThread key={d.id} {...props} /> : null;
        })}
        {resolved.length > 0 && (
          <GroupHeader label="Resolved" color={COLORS.ok} count={resolved.length}
                       style={{ marginTop: open.length ? 12 : 0 }} />
        )}
        {resolved.map(d => {
          const props = _normalizeToThread({ ...d, _critiqueKind: 'd' }, run, phaseId);
          return props ? <QuestionThread key={d.id} {...props} /> : null;
        })}
      </div>
    </div>
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
      fontSize: 10, color: color || 'var(--md-on-surface-faint)',
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
    restated:     'var(--md-on-surface-muted)',
    conceded:     COLORS.ok,
    aligned:      COLORS.ok,
    open:         COLORS.warn,
  };
  const actionColor = actionTones[step.action] || 'var(--md-on-surface-muted)';

  return (
    <div style={{ display: 'flex', gap: 10, position: 'relative', paddingBottom: last ? 0 : 14 }}>
      {/* Rail */}
      <div style={{
        position: 'absolute',
        left: 7, top: 16,
        bottom: last ? 'auto' : 0, height: last ? 0 : undefined,
        width: 1, background: 'var(--md-outline-variant)',
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
            background: COLORS.ok, color: 'var(--md-surface)',
            lineHeight: 1,
          }}>
            <Mdi name="check" size={11} />
          </span>
        ) : (
          <span style={{
            display: 'inline-block', width: 9, height: 9, borderRadius: '50%',
            background: pending ? 'var(--md-on-surface-decor)' : COLORS.warn,
            margin: 3,
            opacity: pending ? 0.6 : 1,
          }} />
        )}
      </div>
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 3 }}>
          {step.round != null && (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>R{step.round}</span>
          )}
          {meta && (
            <span style={{ fontSize: 11.5, color: 'var(--md-on-surface-variant)', fontWeight: 500 }}>{meta.name}</span>
          )}
          {step.agent === 'both' && (
            <span style={{ fontSize: 11.5, color: 'var(--md-on-surface-variant)', fontWeight: 500 }}>Both agents</span>
          )}
          <span className="mono" style={{
            fontSize: 10.5, color: actionColor, letterSpacing: '0.02em',
            textTransform: 'lowercase',
          }}>{step.action}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--md-on-surface-variant)', lineHeight: 1.5 }}>
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
      <div style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55 }}>{text}</div>
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
      borderTop: '1px solid var(--md-outline-hair)',
      background: 'var(--md-surface)',
      flexShrink: 0,
      fontSize: 11.5,
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <AgentIcon agent="claude" size={12} variant="ghost" />
        <span className="mono num" style={{ color: 'var(--md-on-surface-variant)' }}>{fmt.cost(a)}</span>
        <span style={{ color: 'var(--md-on-surface-decor)' }}>+</span>
        <AgentIcon agent="gpt" size={12} variant="ghost" />
        <span className="mono num" style={{ color: 'var(--md-on-surface-variant)' }}>{fmt.cost(b)}</span>
        <span style={{ color: 'var(--md-on-surface-decor)' }}>=</span>
        <span className="mono num" style={{ color: 'var(--md-on-surface)' }}>{fmt.cost(total)}</span>
      </span>
      {hasBudget && (
        <>
          <div style={{ flex: 1, position: 'relative', height: 4, background: 'var(--md-surface-container-high)', borderRadius: 999, maxWidth: 380 }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${Math.min(100, aPct)}%`, background: COLORS.agentA, borderRadius: '999px 0 0 999px' }} />
            <div style={{ position: 'absolute', left: `${Math.min(100, aPct)}%`, top: 0, bottom: 0, width: `${Math.min(100 - aPct, bPct)}%`, background: COLORS.agentB }} />
            <span style={{ position: 'absolute', top: -2, bottom: -2, left: `${warnPct}%`, width: 1, background: over ? COLORS.warn : 'var(--md-outline)' }} />
          </div>
          <span className="mono num" style={{ color: over ? COLORS.warn : 'var(--md-on-surface-muted)' }}>
            {pct.toFixed(0)}% of ${budget.toFixed(2)}
          </span>
          {over && (
            <span className="mono" style={{ color: COLORS.warn, fontSize: 11 }}>above 75% threshold</span>
          )}
        </>
      )}
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ color: 'var(--md-on-surface-faint)', fontSize: 11 }}>SSE · /runs/{run.id}/stream</span>
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
      background: 'var(--md-surface)',
      overflow: 'hidden',
    }}>
      <PaneHeader
        title="Errors"
        count={`${errors.length} logged for run ${run.id}`}
        accentColor={COLORS.err}
        right={
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <SmallStat label="critical" value={counts.critical || 0} color={(counts.critical || 0) > 0 ? COLORS.err : 'var(--md-on-surface-faint)'} />
            <SmallStat label="error"    value={counts.error || 0}    color={(counts.error || 0) > 0 ? COLORS.err : 'var(--md-on-surface-faint)'} />
            <SmallStat label="warning"  value={counts.warning || 0}  color={(counts.warning || 0) > 0 ? COLORS.warn : 'var(--md-on-surface-faint)'} />
          </span>
        }
      />
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '14px 24px 28px' }}>
        <GroupHeader label="Errors" color={COLORS.err} count={errors.length} />
        {errors.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--md-on-surface-faint)', fontSize: 12.5 }}>
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
        background: 'var(--md-surface)',
        overflow: 'hidden',
      }}>
        <RunDetailHeader
          run={run}
          errorCount={errorCount}
          showErrors={showErrors}
          onToggleErrors={() => setShowErrors(s => !s)}
          onJumpToFirstSearch={onJumpToFirstSearch}
        />
        <TimelineAgentBar run={run} />
        {/* Spec 0070 D4: blocking-item callout banner removed (user: "completely useless").
           Same info available in critique pane DRIFT/OPEN section headers. */}
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
