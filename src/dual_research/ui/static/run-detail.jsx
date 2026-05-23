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
// Spec 0133: relocated from the dedicated `.agent-bar` row into the
// Timeline pane headers (Claude in `.tl__head`, GPT in `.tl__tabs`).
// `className="in-header"` lets `components.css` swap the `.as-timeline`
// 460–720 px width contract for content-natural sizing + tight padding.
// Cost renders at 2 decimals (fmt.costShort) — 4-digit precision is noise
// at this surface; the top-bar CostBadge keeps the precise figure.
function TimelineAgentPill({ agent, run, className = 'in-header' }) {
  const meta = AGENT_META[agent];
  const ag = run.agents?.[agent] || {};
  const tokensIn = ag.tokens?.in || 0;
  const tokensOut = ag.tokens?.out || 0;
  const totalTokens = tokensIn + tokensOut;
  const cost = ag.cost || 0;
  const modelId = ag.modelId || ag.model_id || meta?.name || agent;
  const { live, phrase } = composeAgentActivity(agent, run);
  const slot = agent === 'claude' ? 'a' : 'b';
  const phraseColor = live ? 'var(--md-on-surface-variant)' : 'var(--md-on-surface-faint)';

  const activityRight = (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
      {/* Spec 0173 §2.1 — dot's colour + pulse are owned by components.css
          via `.as.in-header[.is-live] .activity-dot`. Not-live = grey;
          live = info-blue + pulse-info halo. */}
      <i className="activity-dot" aria-hidden="true" />
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
      costFormatter={fmt.costShort}
      right={activityRight}
      // Spec 0138 §5.1 — append `is-live` when the agent is mid-round so
      // the `.as.in-header.is-live::before` gradient sweep (added in the
      // CSS at components.css) animates. The class is keyed off the same
      // `live` boolean that drives the inner dot pulse, so the two
      // animations engage / disengage together as one "this model is
      // breathing" gesture. `_cn` is a top-level helper in shared.jsx
      // (line 682), reachable from this file by virtue of the
      // index.html script ordering (shared.jsx loads before run-detail.jsx).
      className={_cn(className, live && 'is-live')}
    />
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
// Spec 0138 §5.3: full run-id RunIDChip with click-to-copy, sitting in
// the right-side cluster to the left of the started/elapsed/round metadata
// so the visual hierarchy reads identity first → activity context second.
function PhaseDotsRow({ run, startedClock, elapsedLabel }) {
  // Spec 0138 §5.3 — click-to-copy state for the run-id chip. The
  // confirmation surface is the chip's `title` tooltip; on success it
  // swaps to "copied!" for ~1.4 s and reverts. The spec considered a
  // full M3 snackbar (§7) but defers to keep the affordance simple.
  // Spec 0143 §3.2.2 — payload now carries total cost + total tokens
  // alongside the id so a single click yields a paste-ready
  // "<id> · $X · Yt" line. Same fmt.cost / fmt.tokens helpers the
  // CostBadge uses, so the copied numbers always match the on-screen
  // pill verbatim.
  const [copiedRunId, setCopiedRunId] = React.useState(false);
  const totalCost = (run?.agents?.claude?.cost || 0) + (run?.agents?.gpt?.cost || 0);
  const totalTokens =
    (run?.agents?.claude?.tokens?.in || 0) + (run?.agents?.claude?.tokens?.out || 0) +
    (run?.agents?.gpt?.tokens?.in || 0)    + (run?.agents?.gpt?.tokens?.out || 0);
  const copyPayload = run?.id
    ? `${run.id} · ${fmt.cost(totalCost)} · ${fmt.tokens(totalTokens)}t`
    : '';
  const copyRunId = React.useCallback((e) => {
    e.stopPropagation();
    if (!run?.id || !navigator.clipboard) return;
    navigator.clipboard.writeText(copyPayload).then(
      () => {
        setCopiedRunId(true);
        setTimeout(() => setCopiedRunId(false), 1400);
      },
      () => {
        // navigator.clipboard.writeText can reject in non-secure
        // contexts (HTTP non-localhost). Silently no-op — the user can
        // still triple-click the chip text and Cmd+C manually.
      },
    );
  }, [run?.id, copyPayload]);

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
      {/* Spec 0138 §5.3 — full run id, copyable. Sits to the LEFT of the
          existing started/elapsed/round metadata so the visual hierarchy
          reads identity first → activity context second. Spec 0151 §3.3 —
          RunIDChip is now compound: the id span is inert and a separate
          copy button (right of a hairline divider) is the sole copy
          affordance. The handler payload (id · cost · tokens) is
          unchanged. */}
      {run.id && (
        <RunIDChip
          id={run.id}
          onCopy={copyRunId}
          copyTitle={copiedRunId
            ? 'copied — id · cost · tokens'
            : `Copy ${copyPayload}`}
        />
      )}
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
          <span><span className="num" style={{ fontWeight: 'var(--md-w-semi)' }}>{counts.open}</span> open</span>
        )}
        {counts.open > 0 && counts.ghosted > 0 && (
          <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
        )}
        {counts.ghosted > 0 && (
          <span style={{ color: COLORS.warn }}>
            <span className="num" style={{ fontWeight: 'var(--md-w-semi)' }}>{counts.ghosted}</span> ghosted
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
           color: 'var(--md-on-surface)', fontSize: 14, lineHeight: 1.35, fontWeight: 'var(--md-w-medium)',
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
  // Spec 0143 §3.2.1 — prefix the pill with a small "total" label so
  // the number can't be misread as per-phase / per-model (the Timeline
  // agent pills next to it show per-agent figures — the visual
  // proximity is the failure mode). Tooltip also leads with "Total:".
  const sc = Number(searchCost) || 0;
  const tokenCost = Math.max(0, cost - sc);
  let tip = `Total: ${cost.toFixed(4)} USD · ${tokens.toLocaleString()} tokens`;
  if (sc > 0) {
    tip = (
      `Total: ${cost.toFixed(4)} USD (tokens ${tokenCost.toFixed(4)} · `
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
      <span style={{ color: 'var(--md-on-surface-faint)', fontSize: 10 }}>total</span>
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

// Spec 0133 — M3 segmented linear phase-progress indicator. Replaces the
// pre-M3 circles-and-lines treatment with one rounded bar segment per
// PHASES entry. Cell state (done / current / errored / deadlocked /
// pending) maps to a class that drives the background color via the
// existing palette tokens in components.css (.phase-progress__seg.is-*).
function PhaseDots({ run }) {
  const { phase, status } = run;
  return (
    <div className="phase-progress" aria-label="Run progress">
      {PHASES.map((p) => {
        const completed = p.id < phase || (status === 'completed' && p.id <= PHASES.length - 1);
        const current   = p.id === phase && status !== 'completed';
        const failed    = (status === 'errored' || status === 'deadlocked') && p.id === phase;
        const cls = ['phase-progress__seg'];
        if (failed && status === 'errored')         cls.push('is-error');
        else if (failed && status === 'deadlocked') cls.push('is-warn');
        else if (current)                            cls.push('is-current');
        else if (completed)                          cls.push('is-done');
        const stateLabel = completed
          ? 'done'
          : current
            ? 'in progress'
            : failed
              ? status
              : 'pending';
        return (
          <span
            key={p.id}
            className={cls.join(' ')}
            title={`${p.short} ${p.label} · ${stateLabel}`}
          />
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
      {/* HEAD — title + count + (spec 0133) right-aligned Claude agent pill. */}
      <header className="tl__head">
        <span className="ttl">Timeline</span>
        <span className="ct">{artifactCount} artifacts</span>
        <TimelineAgentPill agent="claude" run={run} />
      </header>

      {/* TABS — Conversation / Consumption. Outer .tl__tabs is the full-width
          band (matches .bar2); inner .tl__tabs-inner is the segmented pill.
          Spec 0133 — GPT agent pill rides on the right of this row, vertically
          aligned with the Claude pill above. */}
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
        <TimelineAgentPill agent="gpt" run={run} />
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
                        {/* Spec 0164 §2.1 — marker label now reads the full
                            "Phase N" identity. Previously fell back to the
                            short "P0" form from live-data PHASES.short,
                            kept for the PhaseRail cells (line 784) and the
                            tooltip on the progress strip (line 756). */}
                        <span className="lbl">Phase {vp.pid}</span>
                      </span>
                      <span className="chev"><span className="ms ms-18">expand_more</span></span>
                      {/* Spec 0164 §2.2 — .tl-phase__pcode removed.
                          The marker above carries the canonical identity. */}
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
// Spec 0148 D03 — warning chip surface for ProtocolViolation /
// EmptyTurnDetected events emitted by the orchestrator (spec 0141) and
// mirrored to ``transcript.jsonl`` via the spec-0122 bridge. Joins by
// (phase, round, agent) against ``run.violations``; one chip per
// matching event. Click expands an inline JSON detail.
function ViolationChip({ event }) {
  const [open, setOpen] = React.useState(false);
  const kind = event && event.event;
  const label = kind === 'protocol_violation' ? 'Protocol violation' : 'Empty turn';
  const tone = kind === 'protocol_violation' ? 'error' : 'tertiary';
  const stop = (e) => e.stopPropagation();
  return (
    <span className={`violation-chip violation-chip--${tone}`} onClick={stop}>
      <button
        type="button"
        className="violation-chip__head"
        title={label}
        aria-label={label}
        onClick={(e) => { stop(e); setOpen((o) => !o); }}
      >
        <span className="violation-chip__dot" aria-hidden="true" />
        <span className="violation-chip__label">{label}</span>
        <span className="violation-chip__chev">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <pre className="violation-chip__body">{JSON.stringify(event, null, 2)}</pre>
      )}
    </span>
  );
}

// Spec 0148 D03 — agent-name join key: ``run.violations`` events carry
// ``agent`` as the backend label (``claude`` / ``openai``); the turn
// card uses ``item.agent`` in UI vocabulary (``claude`` / ``gpt``).
function _violationsForTurnCard(violations, phase, round, agent) {
  if (!Array.isArray(violations) || !violations.length) return [];
  if (phase == null || round == null || !agent) return [];
  const backendAgent = agent === 'gpt' ? 'openai' : agent;
  return violations.filter((v) =>
    Number(v.phase) === Number(phase)
    && Number(v.round) === Number(round)
    && v.agent === backendAgent
  );
}

function TlTurnRow({ item, run, isOpen, onToggle }) {
  const agent = item.agent || null;
  const agentSlot = agent === 'gpt' ? 'b' : agent === 'claude' ? 'a' : null;
  const agentName = agent ? (AGENT_META[agent]?.name || agent) : null;
  const isRepair = hasRepairSibling(run, item.turnKey);
  const isLive = item.live;

  // Spec 0148 D03 — protocol-violation / empty-turn events for this
  // turn card. Joined off run.violations by (phase, round, agent).
  const cardViolations = _violationsForTurnCard(
    run && run.violations, item.phase, item.round, agent
  );

  // Spec 0115 — full-word activity label (no single-letter badge).
  // Spec 0166 §2.4 — defensive guard: an upstream regression in the
  // anchor run `20260521-010637-dvs-backend-language-choice` (Phase 4
  // cross-review) handed `item.round` an object instead of a numeric
  // index, producing `turn [object object]` after the lowercase pass.
  // If we ever get a non-number where a number is expected, set
  // `activityLabelError` so the chip render falls back to a SystemChip +
  // ErrorChip pair rather than stringifying the object. The check is
  // strictly a safety net — once the data layer is correct, this branch
  // never fires.
  let activityLabel;
  let activityLabelError = null;
  if (item.round != null) {
    if (typeof item.round === 'number') {
      activityLabel = `Turn ${item.round}`;
    } else {
      activityLabelError = 'Could not render this turn';
      activityLabel = '—';
    }
  } else if (item.kind === 'input') {
    activityLabel = 'Brief';
  } else if (item.kind === 'preflight') {
    activityLabel = 'Preflight';
  } else if (item.kind === 'plan' || item.kind === 'plan-live') {
    activityLabel = 'Plan';
  } else if (item.kind === 'doc' || item.kind === 'doc-live') {
    activityLabel = 'Draft';
  } else {
    activityLabel = item.kind || '—';
  }

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
        {/* Spec 0166 §2.3 / §2.4 — three branches in the activity-chip slot.
            Defensive path FIRST: if the data layer handed us a non-numeric
            turn index, render [SystemChip] [ErrorChip] so the card head
            never carries `turn [object object]`. Otherwise: agentless brief
            card → [SystemChip] [brief] (replaces the spec-0119 file-document
            glyph variant — System is the canonical identity now). Agent
            cards: mono activity chip as before. */}
        {activityLabelError ? (
          <>
            <SystemChip />
            <ErrorChip label={activityLabelError} />
          </>
        ) : !agent && item.kind === 'input' ? (
          <>
            <SystemChip />
            <Chip mono tone="neutral" label="brief" />
          </>
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
              a chip jumps the critique pane to (category, round).
              Spec 0133 §5.9 — slim Δ-pair presentation: bubble and
              standing-total slots dropped; tone color + Q→D→I→C order
              carry category identity, add + sub carry the per-round
              delta. Phase-aggregate standing reads at TlPhaseHeadChips
              instead. */}
          {showCategoryChips && chipCategories.map((cat) => {
            const c = categories[cat] || { standing: 0, raised: 0, closed: 0, capped: 0 };
            const noActivity = (c.raised + c.closed) === 0;
            return (
              <Chip
                key={cat}
                tone={CATEGORY_TONE[cat]}
                add={c.raised}
                sub={c.closed}
                trailingSuffix={c.capped > 0 ? `⊘ ${c.capped}` : null}
                dim={noActivity}
                ariaLabel={`${CATEGORY_LABEL_PLURAL[cat]} this round: ${c.raised} raised, ${c.closed} closed${c.capped > 0 ? `, ${c.capped} capped` : ''}`}
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

          {/* Spec 0148 D03 — warning chips for ProtocolViolation /
              EmptyTurnDetected on this turn (zero hits → no chips). */}
          {cardViolations.map((ev, i) => (
            <ViolationChip key={`${ev.event}-${i}`} event={ev} />
          ))}

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
            {/* Spec 0165 §2.5 — 2-decimal precision for card-internal cost
                display. `fmt.cost` (4-decimal) stays the audit value for the
                run-detail footer aggregate. */}
            <span className="md-chip md-chip--sm">
              {isRepair ? '$0.00' : fmtCost2(cost)}
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

// Spec 0173 §2.10 / §2.11 — SourceRow extended with `provider` + `round`
// for the per-source attribution chip (between title and host badge),
// and `defaultExpanded` for the spec 0168 §3.J first-source-pre-expanded
// rule (lands together with the per-card collapse affordance).
function SourceRow({ record, provider, round, defaultExpanded = false }) {
  const [open, setOpen] = React.useState(!!defaultExpanded);
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

  // Spec 0173 §2.10 — attribution chip. Read from the explicit props
  // first, then fall back to the EvidenceRecord shape (camelCased from
  // models.py — `providedBy` + `answeredInRound`) so existing call
  // sites (which pass record only) still surface attribution.
  const attrProvider = provider
    || record.provider || record.providerAgent
    || record.providedBy || record.provided_by
    || null;
  const attrRound = round != null
    ? round
    : (record.round != null ? record.round
       : record.answeredInRound != null ? record.answeredInRound
       : record.answered_in_round != null ? record.answered_in_round
       : record.raisedInRound != null ? record.raisedInRound
       : record.raised_in_round != null ? record.raised_in_round
       : null);
  const attrAgent = _resolveAgent(attrProvider);
  const attributionChip = (attrAgent && attrRound != null) ? (
    <Chip
      tone={attrAgent === 'gpt' ? 'gpt' : 'claude'}
      size="sm"
      leadingIcon={<AgentIcon agent={attrAgent} size={10} />}
      label={`r${attrRound}`}
    />
  ) : (attrProvider === 'auto' || attrProvider === 'orchestrator' || attrProvider === 'system') && attrRound != null ? (
    <Chip tone="neutral" noDot size="sm" label={`auto · r${attrRound}`} />
  ) : null;

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
        {attributionChip && (
          <span className="source-row__attribution">{attributionChip}</span>
        )}
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

// Spec 0144 §4.8 — Terminal states for the lifecycle footer. The
// invariant: all four item kinds render the same "✓ {state} at round
// N · M turns to converge" footer when terminal; open items render no
// footer. Disagreement's legacy "conceded by X" suffix is rolled into
// the via-clause on the last transition.
const _ITEM_CARD_TERMINAL_STATES = new Set([
  'resolved', 'acknowledged', 'withdrawn', 'capped',
]);

// Spec 0173 §2.5 — kind chip vocabulary + tone for the rebuilt
// item-card head. Q → info, D → warn, I → err, C → muted. Mirrors the
// canonical kind cluster on bar 2 (Q · D · I · C).
const _ITEM_KIND_LABEL = {
  question: 'Question', disagreement: 'Disagreement',
  issue: 'Issue', comment: 'Comment',
};
const _ITEM_KIND_TONE = {
  question: 'info', disagreement: 'warn', issue: 'err', comment: 'muted',
};
const _ITEM_KIND_LETTER = {
  question: 'Q', disagreement: 'D', issue: 'I', comment: 'C',
};

// Spec 0173 §2.6 + §2.8 — lifecycle chip helpers. The composite chip
// carries the raise → resolve arc with provenance (round + resolver).
// `_resolveAgent` normalises `openai` → `gpt` for the AgentIcon prop
// while preserving the agent identity for tone selection.
function _resolveAgent(actor) {
  if (actor === 'openai') return 'gpt';
  if (actor === 'claude' || actor === 'gpt') return actor;
  return null;
}

// Spec 0173 §2.9 — ItemCardThreadView. Renders the raise → respond →
// resolve arc as tonal-tinted message bubbles, mirroring the
// QuestionThread anatomy from design-system/SPEC.md §4.2 (canonical
// `.qthread` `.lc-row` chip-cluster + indented quote body). The first
// bubble is always the "raised" turn (with item.body as the quote);
// subsequent bubbles come from `item.transitions` in chronological
// order. Verdict tone follows the existing `_verbTone` mapping.
function ItemCardThreadView({ item }) {
  const transitions = item.transitions || [];
  const raisedAgent = _resolveAgent(item.raisedBy || item.raiser);
  const raisedRound = item.raisedRound || item.raised_round || item.roundFirstSeen || item.openedRound || null;
  const raisedQuote = item.body || '';
  const turns = [];
  if (raisedAgent || raisedRound != null || raisedQuote) {
    turns.push({
      agent: raisedAgent,
      round: raisedRound,
      verb: 'raised',
      tone: 'muted',
      text: raisedQuote,
    });
  }
  for (const t of transitions) {
    const verb = _transitionVerb(t);
    turns.push({
      agent: _resolveAgent(t.actor),
      round: t.round,
      verb,
      tone: _verbTone(verb),
      text: t.reason || '',
    });
  }
  if (turns.length === 0) return null;
  return (
    <ol className="item-card__qt-rows" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {turns.map((t, i) => {
        const agentName = t.agent === 'gpt' ? 'GPT' : t.agent === 'claude' ? 'Claude' : 'System';
        return (
          <li key={i} className={`item-card__qt-row item-card__qt-row--${t.agent || 'system'}`}>
            <div className="item-card__qt-chips">
              {t.agent ? (
                <Chip
                  tone={t.agent === 'gpt' ? 'gpt' : 'claude'}
                  size="sm"
                  leadingIcon={<AgentIcon agent={t.agent} size={10} />}
                  label={agentName}
                />
              ) : (
                <SystemChip />
              )}
              {t.round != null && (
                <Chip mono size="sm" tone="neutral" label={`round ${t.round}`} />
              )}
              {t.verb && (
                <Chip size="sm" tone={t.tone === 'error' ? 'err' : t.tone} label={t.verb} />
              )}
            </div>
            {t.text && (
              <blockquote className="item-card__qt-quote">
                {typeof t.text === 'string' ? <Markdown text={t.text} /> : t.text}
              </blockquote>
            )}
          </li>
        );
      })}
    </ol>
  );
}

// Spec 0151 §3.4.3 — per-kind verb labels for the footer strip.
// Disagreement and Question have agent-specific terminal phrasing
// ("both aligned" vs "answered"); Issue and Comment stay literal.
// These verb strings come directly from the design-system reference
// screenshots (07/08/09/10) and supersede the spec 0119 §13 vocabulary
// scan for this specific call site — they are chip labels by intent.
const _FOOTER_VERBS = {
  disagreement: { resolved: 'both aligned', acknowledged: 'acknowledged',
                  capped: 'capped', withdrawn: 'withdrawn' },
  question:     { resolved: 'answered', acknowledged: 'acknowledged', // spec-0119:vocab-ok (spec 0151 §3.4.3 design-system verb)
                  capped: 'capped', withdrawn: 'withdrawn' },
  issue:        { resolved: 'resolved', acknowledged: 'acknowledged',
                  capped: 'capped', withdrawn: 'withdrawn' },
  comment:      { resolved: 'noted', acknowledged: 'noted', // spec-0119:vocab-ok (spec 0151 §3.4.3 design-system verb)
                  capped: 'noted',   withdrawn: 'noted' }, // spec-0119:vocab-ok (spec 0151 §3.4.3 design-system verb)
};

// Map a transition to a per-turn verb chip (design-system reference
// `08-disagreement-card.png`: conceded / pushed back / restated /
// aligned / raised).
function _transitionVerb(t) {
  const to = t.toState || t.to_state || '';
  const from = t.fromState || t.from_state || '';
  if (to === 'addressed') return 'pushed back';
  if (from === 'addressed' && to === 'open') return 'restated';
  if (to === 'acknowledged') return 'aligned';
  if (to === 'resolved' || to === 'withdrawn') return 'conceded'; // spec-0119:vocab-ok (spec 0151 §3.4.3 design-system verb)
  if (to === 'capped') return 'capped';
  return to || 'raised';
}

function _verbTone(verb) {
  if (verb === 'conceded' || verb === 'aligned') return 'info'; // spec-0119:vocab-ok (data-layer comparison)
  if (verb === 'pushed back' || verb === 'restated') return 'warn';
  if (verb === 'capped') return 'error';
  return 'muted';
}

function _actorTone(actor) {
  const a = actor === 'openai' ? 'gpt' : actor;
  if (a === 'claude') return 'a';
  if (a === 'gpt') return 'b';
  if (a === 'mutual') return 'muted';
  return 'muted';
}

function _actorLabel(actor) {
  if (actor === 'openai' || actor === 'gpt') return 'GPT';
  if (actor === 'claude') return 'Claude';
  if (actor === 'mutual') return 'Both';
  if (actor === 'orchestrator') return 'Orchestrator';
  return actor || '—';
}

// Per-turn row inside Disagreement / Question bodies. Matches design
// reference `08-disagreement-card.png`:
//   [Agent badge] · r<N> · [verb badge]
//     ┃ <quoted reason text>
function ItemCardTurnRow({ actor, round, verb, tone, text }) {
  const a = actor === 'openai' ? 'gpt' : actor;
  const agentTone = _actorTone(actor);
  return (
    <div className="item-card__turn">
      <div className="item-card__turn-head">
        <span className={`item-card__agent item-card__agent--${a}`}>
          <i className="dot" style={{ background: a === 'mutual' ? 'var(--md-on-surface-variant)' : `var(--${a})` }} />
          {_actorLabel(actor)}
        </span>
        <span className="item-card__turn-sep">·</span>
        <span className="item-card__turn-round">r{round}</span>
        <span className="item-card__turn-sep">·</span>
        <Chip tone={tone} size="sm">{verb}</Chip>
      </div>
      {text && (
        <blockquote className="item-card__turn-text">{text}</blockquote>
      )}
    </div>
  );
}

// Disagreement / Question body — matches `08-disagreement-card.png`.
// Layout:
//   id chip · [state] ........... N turns
//   [state] — <resolution text>          (terminal only)
//   <per-turn rows: raise + each transition>
// Spec 0179 §3.1 — terminal-verdict row deleted. The state was already
// surfaced by the head's lifecycle chip (spec 0173 §2.8); the
// resolution text is carried by the resolve transition's bubble inside
// ItemCardThreadView (§2.9). The pre-0179 `.item-card__verdict` row
// was the third repetition of the same datum per terminal card.
function ItemCardDQBody({ item, transitions }) {
  const turnsCount = transitions.length;
  return (
    <div className="item-card__body item-card__body--turns">
      <div className="item-card__bmeta">
        <span style={{ flex: 1 }} />
        <span className="item-card__turn-count">{turnsCount} turn{turnsCount === 1 ? '' : 's'}</span>
      </div>
      {/* Spec 0173 §2.9 — flat ItemCardTurnRow stack replaced by the
          QuestionThread-anatomy bubble timeline. The new view carries
          the same data (agent identity, round, verb, quote) but renders
          each transition as a tonal-tinted message bubble keyed off
          provider, mirroring `.lc-row` from shared.jsx::QuestionThread. */}
      <ItemCardThreadView item={item} />
    </div>
  );
}

// Issue body — matches `09-issue-card.png`, post-spec-0172 + 0179. Layout:
//   <markdown body>                         (full item.body via <Markdown>)
//   > quote: <anchor>                       (inline anchor, if quote)
//
// Spec 0172 §3 dropped the `[shortCode] [state] — <title>` row; spec
// 0179 §3.2 / §3.4 dropped the seen-row chip cluster (raised-by + round
// metadata duplicated the head's lifecycle chip) and the bottom-anchor
// blockquote (duplicated the inline anchor). The inline anchor at the
// top of the body is now the only canonical anchor surface; the head's
// lifecycle chip is the only raised-by + lifecycle surface.
function ItemCardIssueBody({ item, anchorType, anchorText }) {
  return (
    <div className="item-card__body item-card__body--issue">
      {item.body && (
        <div className="item-card__text"><Markdown text={String(item.body)} /></div>
      )}
      {anchorType === 'quote' && anchorText && (
        <blockquote className="item-card__quote-inline">quote: {anchorText}</blockquote>
      )}
    </div>
  );
}

// Comment body — matches `10-comments-card.png`, post-spec-0179. Layout:
//   <markdown body>
//   > quote: <anchor>                       (inline anchor, if quote)
//
// Spec 0179 §3.3 / §3.5 dropped the seen-row chip cluster
// ([noted by Agent] [R<N>]) and the bottom-anchor blockquote — both
// duplicated data the head's lifecycle chip (raised-by + round) and
// the inline anchor already carry.
function ItemCardCommentBody({ item, anchorType, anchorText }) {
  return (
    <div className="item-card__body item-card__body--comment">
      {item.body && (
        <div className="item-card__text"><Markdown text={String(item.body)} /></div>
      )}
      {anchorType === 'quote' && anchorText && (
        <blockquote className="item-card__quote-inline">quote: {anchorText}</blockquote>
      )}
    </div>
  );
}

// Spec 0151 §3.4.3 — ItemCard rewritten so each kind matches its
// design-system reference pixel-by-pixel:
//   Question     → design-system/notion-issues/screenshots/07-question-card-duplicate.png
//   Disagreement → design-system/notion-issues/screenshots/08-disagreement-card.png
//   Issue        → design-system/notion-issues/screenshots/09-issue-card.png
//   Comment      → design-system/notion-issues/screenshots/10-comments-card.png
// The slim header (id + kind + state, no raised-by/round badges) is
// shared; the body delegates to a per-kind sub-renderer. Lifecycle is
// surfaced via per-turn rows inside Q/D bodies (not as a separate
// "Lifecycle" timeline section). Terminal items get a green footer
// strip whose verb is kind-aware (`both aligned` / `answered` /
// `resolved` / `noted`). Hover elevation per design-system/notion-
// issues/ISSUES.md Issue 3 via the shared `data-hoverable` token.
function ItemCard({ item, onHighlight, isDrift = false }) {
  const cardRef = React.useRef(null);
  const kindLabel = _ITEM_KIND_LABEL[item.kind] || item.kind;
  const kindTone = _ITEM_KIND_TONE[item.kind] || 'info';
  const kindLetter = _ITEM_KIND_LETTER[item.kind] || (item.kind || '?')[0].toUpperCase();
  const stateLabel = item.currentState || item.current_state || 'open';
  const stateTone = ({
    resolved: 'ok',
    acknowledged: 'warn',
    withdrawn: 'muted',
    capped: 'error',
    open: 'info',
    addressed: 'info',
  })[stateLabel] || 'info';
  const transitions = item.transitions || [];
  const evidence = item.evidence || [];
  const evidenceRequired = !!(item.evidenceRequired || item.evidence_required);
  const anchorType = item.anchorType || item.anchor_type;
  const anchorText = item.anchorText || item.anchor_text;
  const isTerminal = _ITEM_CARD_TERMINAL_STATES.has(stateLabel);

  // Spec 0173 §2.6 + §2.8 — derive lifecycle data once, reuse across
  // the head chip and the (future) expanded-view scaffolding.
  const raisedByAgent = _resolveAgent(item.raisedBy);
  const raisedRound = item.raisedRound || item.raised_round || item.roundFirstSeen || item.openedRound || null;
  const lastTerminalT = isTerminal
    ? [...transitions].reverse().find((t) => _ITEM_CARD_TERMINAL_STATES.has(t.toState || t.to_state || ''))
    : null;
  const resolvedRound = lastTerminalT ? lastTerminalT.round : null;
  const resolvedActor = lastTerminalT ? lastTerminalT.actor : null;
  const resolvedByAgent = _resolveAgent(resolvedActor);
  const isAutoResolve = isTerminal && !resolvedByAgent;

  // Lifecycle footer (Spec 0151 §3.4.3): kind-aware verb, green strip.
  let lifecycleFooter = null;
  if (isTerminal) {
    const lastTerminal = [...transitions].reverse()
      .find((t) => _ITEM_CARD_TERMINAL_STATES.has(t.toState || t.to_state || ''));
    const terminalRound = lastTerminal ? lastTerminal.round : (item.raisedRound || item.raised_round);
    const verb = (_FOOTER_VERBS[item.kind] || {})[stateLabel] || stateLabel;
    lifecycleFooter = (
      <div className="item-card__footer item-card__footer--ok">
        <span aria-hidden="true">✓</span>{' '}
        {verb}{terminalRound != null ? ` in round ${terminalRound}` : ''}
      </div>
    );
  }

  const handleSourcesChipClick = (e) => {
    e.stopPropagation();
    const root = cardRef.current;
    if (!root) return;
    const target = root.querySelector('.item-card__sources');
    if (!target) return;
    let scroller = target.parentElement;
    while (scroller && scroller !== document.body) {
      const cs = window.getComputedStyle(scroller);
      const oy = cs.overflowY;
      if ((oy === 'auto' || oy === 'scroll') && scroller.scrollHeight > scroller.clientHeight) {
        break;
      }
      scroller = scroller.parentElement;
    }
    if (!scroller || scroller === document.body) {
      target.scrollIntoView({ behavior: 'auto', block: 'start' });
      return;
    }
    const targetRect = target.getBoundingClientRect();
    const scrollerRect = scroller.getBoundingClientRect();
    const delta = targetRect.top - scrollerRect.top - 12;
    scroller.scrollBy({ top: delta, behavior: 'auto' });
  };

  // Per-kind body
  let body;
  if (item.kind === 'disagreement' || item.kind === 'question') {
    // Spec 0179 §3.1 — stateLabel / stateTone / isTerminal no longer forwarded;
    // the head's lifecycle chip is the canonical state surface and ItemCardThreadView
    // carries the resolution text via the resolve-transition bubble.
    body = (
      <ItemCardDQBody
        item={item}
        transitions={transitions}
      />
    );
  } else if (item.kind === 'issue') {
    // Spec 0172 — stateLabel / stateTone dropped from ItemCardIssueBody;
    // the head's lifecycle chip (spec 0173 §2.8) is the canonical state surface.
    body = (
      <ItemCardIssueBody
        item={item}
        anchorType={anchorType}
        anchorText={anchorText}
      />
    );
  } else if (item.kind === 'comment') {
    body = (
      <ItemCardCommentBody
        item={item}
        anchorType={anchorType}
        anchorText={anchorText}
      />
    );
  } else {
    // Fallback for unknown kinds — keep the legacy compact body.
    body = (
      <div className="item-card__body">
        {item.body}
        {anchorType && anchorType !== 'none' && (
          <blockquote className="item-card__anchor">
            {anchorType === 'quote' ? '> quote: ' : '> after: '}
            {anchorText}
          </blockquote>
        )}
      </div>
    );
  }

  // Spec 0173 §2.5 + §2.6 + §2.7 + §2.8 — rebuilt head composition.
  // `[provider chip] [kind chip] [evidence-needed modifier?] [lifecycle chip — right-aligned]`.
  // The ID chip and the standalone sources chip are dropped (per §2.5
  // and the deferred 0168 §2.3 covered by spec 0172). The state chip
  // is subsumed by the lifecycle chip per §2.8.
  const providerChip = raisedByAgent ? (
    <Chip
      tone={raisedByAgent === 'gpt' ? 'gpt' : 'claude'}
      size="sm"
      leadingIcon={<AgentIcon agent={raisedByAgent} size={10} />}
      label={raisedByAgent === 'gpt' ? 'GPT' : 'Claude'}
    />
  ) : <SystemChip />;

  const kindChip = (
    <Chip tone={kindTone} size="sm" categoryBubble={kindLetter} label={kindLabel} />
  );

  const evidenceModifierChip = evidenceRequired ? (
    <Chip
      tone="warn"
      size="sm"
      leadingIcon={<Mdi name="alert" size={12} />}
      label="evidence needed"
    />
  ) : null;

  // Lifecycle chip — composite arc. Drift: err tone, raised + drift
  // narrative. Resolved: ok-toned cluster of two micro-chips (raised
  // by · resolved by). Open: kind-toned single chip with raised
  // provenance. Auto-resolve uses SystemChip leading icon per §2.8.
  let lifecycleChip;
  if (isDrift) {
    lifecycleChip = (
      <Chip
        tone="err"
        size="sm"
        leadingIcon={raisedByAgent ? <AgentIcon agent={raisedByAgent} size={10} /> : null}
        label={`raised r${raisedRound || '?'} · drift`}
      />
    );
  } else if (isTerminal) {
    lifecycleChip = (
      <span className="item-card__lifecycle">
        <Chip
          tone="muted"
          size="sm"
          leadingIcon={raisedByAgent ? <AgentIcon agent={raisedByAgent} size={10} /> : null}
          label={`raised r${raisedRound || '?'}`}
        />
        <span className="item-card__lifecycle-sep" aria-hidden="true">·</span>
        <Chip
          tone="ok"
          size="sm"
          leadingIcon={isAutoResolve
            ? <Mdi name="cog-outline" size={10} />
            : <AgentIcon agent={resolvedByAgent} size={10} />}
          label={`resolved r${resolvedRound || '?'}${isAutoResolve ? ' · auto' : ''}`}
        />
      </span>
    );
  } else {
    const agentSuffix = raisedByAgent === 'gpt' ? ' · GPT' : raisedByAgent === 'claude' ? ' · Claude' : '';
    lifecycleChip = (
      <Chip
        tone={kindTone}
        size="sm"
        leadingIcon={raisedByAgent ? <AgentIcon agent={raisedByAgent} size={10} /> : null}
        label={`raised · r${raisedRound || '?'}${agentSuffix}`}
      />
    );
  }

  // Spec 0173 §2.11 — per-card collapse affordance. Default collapsed
  // (head only); clicking the head (or Enter / Space on the focused
  // head, role=button) toggles. The body, timeline, and sources blocks
  // hide via CSS scoped to `data-expanded="false"`. The original
  // `onClick={onHighlight}` is preserved on the article so phase-level
  // highlight wiring still fires — the head's onClick stops propagation
  // for the toggle path so the two handlers don't fight.
  const [isExpanded, setIsExpanded] = React.useState(false);
  const toggleExpanded = (e) => {
    e.stopPropagation();
    setIsExpanded((v) => !v);
  };
  const onHeadKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      setIsExpanded((v) => !v);
    }
  };

  return (
    <article
      ref={cardRef}
      className={`item-card item-card--${item.kind} item-card--${stateLabel}`}
      data-hoverable="true"
      data-expanded={isExpanded ? 'true' : 'false'}
      onClick={onHighlight}
    >
      <header
        className="item-card__head"
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        onClick={toggleExpanded}
        onKeyDown={onHeadKey}
      >
        {providerChip}
        {kindChip}
        {evidenceModifierChip}
        <span className="item-card__head-spacer" aria-hidden="true" />
        {lifecycleChip}
      </header>
      {body}
      {lifecycleFooter}
      {evidence.length > 0 && (
        <div className="item-card__sources">
          <div className="item-card__sources-hd">Sources ({evidence.length})</div>
          {evidence.map((rec, i) => (
            <SourceRow key={i} record={rec} defaultExpanded={i === 0} />
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
  // Spec 0145 — return canonical artifact IDs (replaces legacy
  // d1/d2/hist/draft/histp short keys).
  const p = Number(phase);
  if (p === 0) return null;
  if (p === 1) return agent === 'gpt' ? 'phase1.openai' : 'phase1.claude';
  if (p === 2) return 'prior_turns.phase2';
  if (p === 3) return 'current_draft';
  if (p === 4) return 'prior_turns.phase4';
  return null;
}

// SPEC-0067 D9 — output bar labels expanded to full descriptions.
// P0 is the only turn whose output doesn't fold into a later input slot.
function outputBarLabel(phase, agent) {
  const slot = outputSlotFor(phase, agent);
  if (slot == null) return 'feeds preflight critique';
  const slotLabel = (window.DrArtifacts && window.DrArtifacts.displayName)
    ? window.DrArtifacts.displayName(slot)
    : slot;
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

// ── Spec 0118 — Consumption-tab piece grouping ──
// Spec 0150 — legacy 7-key vocab detection and labels removed.
// Historical events were backfilled to canonical artifact IDs; the
// legacy fallback render branch is gone.

// Spec 0118 master grouping table (NORMATIVE). For each phase, which
// canonical artifact IDs collapse into the "System prompt" aggregate row,
// and which appear as their own separate rows. Output is handled outside.
//
// Spec 0148 — ``closeout.request``, ``system.web_sources``, and
// ``system.tool_definitions`` are pulled OUT of the system-prompt
// aggregate and rendered as discrete rows (when present) via
// ``DYNAMIC_SEPARATE_KEYS`` below. Empty/zero tokens → no row.
const SYSTEM_PROMPT_AGGREGATE_KEYS = {
  0: ['system.task.input', 'prior_turns.phase0', 'ledger.standing_items'],
  1: ['system.task.research_plan', 'phase0.agreement.interpretation'],
  2: ['system.task.plan_negotiation', 'phase0.agreement.interpretation',
      'prior_turns.phase2', 'ledger.standing_items'],
  3: ['system.task.drafting', 'phase0.agreement.interpretation',
      'phase2.agreement.plan', 'carry_forward.phase2'],
  4: ['system.task.review', 'ledger.standing_items'],
};

const PHASE_SEPARATE_KEYS = {
  0: [],
  1: [],
  2: ['phase1.claude', 'phase1.openai'],
  3: ['phase1.claude', 'phase1.openai', 'all_p2_turns'],
  4: ['current_draft', 'prior_turns.phase4'],
};

// Spec 0148 — canonical artifact IDs that should always render as their
// own row when their token count is non-zero, regardless of phase.
// ``closeout.request`` surfaces the closeout-request text on the turn
// that received it (D10); ``system.web_sources`` and
// ``system.tool_definitions`` surface input-token bands the spec-0145
// emitter never broke out (D13/D14).
const DYNAMIC_SEPARATE_KEYS = [
  'closeout.request',
  'system.web_sources',
  'system.tool_definitions',
];

// Spec 0145 — gather per-attachment piece keys + the message piece into
// a single "User prompt" row breakdown. When the producer emitted the
// new vocab (`user_prompt.message` + zero-or-more
// `user_prompt.attachment.<id>`), the breakdown is the sum of those.
// When a legacy run still carries the aggregate `user_prompt` key
// (pre-0145 canonical-vocab era), the legacy value flows through.
function userPromptRowBreakdown(piecesRaw) {
  const message = Number(piecesRaw?.['user_prompt.message']) || 0;
  const attachments = [];
  for (const [k, v] of Object.entries(piecesRaw || {})) {
    if (k.startsWith('user_prompt.attachment.')) {
      const tokens = Number(v) || 0;
      attachments.push({ id: k, attId: k.slice('user_prompt.attachment.'.length), tokens });
    }
  }
  const legacyAggregate = Number(piecesRaw?.['user_prompt']) || 0;
  const newVocabTotal = message + attachments.reduce((s, a) => s + a.tokens, 0);
  const total = newVocabTotal > 0 ? newVocabTotal : legacyAggregate;
  return {
    total,
    message,
    attachments,
    hasAttachments: attachments.length > 0,
    hasMessage: message > 0,
  };
}

// Group a piecesRaw dict (canonical-key vocab) into the per-phase row
// structure described in the spec 0118 master table.
//
// Returns { rows: [{ id, label, tokens, breakdown? }, ...] } where rows
// are in display order: user_prompt → phase-specific separates →
// System prompt aggregate. (Output is rendered separately.) The System
// prompt entry has a `breakdown: [{ id, tokens }, ...]` for the tooltip.
//
// Spec 0145 — the user_prompt row carries an `attachmentBreakdown`
// when the producer emitted per-attachment keys; the card renders an
// expand affordance over those sub-rows.
function groupPiecesForPhase(piecesRaw, phase) {
  const get = (k) => Number(piecesRaw?.[k]) || 0;
  const p = Number(phase);
  const sysKeys = SYSTEM_PROMPT_AGGREGATE_KEYS[p] || [];
  const sepKeys = PHASE_SEPARATE_KEYS[p] || [];

  const rows = [];
  // user_prompt always first (per spec § "Always-separate rows").
  const up = userPromptRowBreakdown(piecesRaw);
  rows.push({
    id: 'user_prompt',
    tokens: up.total,
    attachmentBreakdown: up.hasAttachments ? up : null,
  });

  // Phase-specific separate rows.
  for (const k of sepKeys) {
    rows.push({ id: k, tokens: get(k) });
  }

  // Spec 0148 — dynamic separate rows. Emit each only when present in
  // the wire payload with non-zero tokens, so non-closeout / non-search
  // / no-tool turns don't grow noise rows.
  for (const k of DYNAMIC_SEPARATE_KEYS) {
    const tokens = get(k);
    if (tokens > 0) {
      rows.push({ id: k, tokens });
    }
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

// Proportional cost share for a piece. The total INPUT cost is exact
// (API-billed); each piece's cost is its proportional share of that
// total. Returns 0 when billed_input_tokens is zero (defensive).
function piecePropCost(pieceTokens, billedInputTokens, totalInputCost) {
  if (!billedInputTokens || billedInputTokens <= 0) return 0;
  return (pieceTokens / billedInputTokens) * totalInputCost;
}

// Spec 0148 — `normalisePiecesRaw` retired. The server-side `_to_camel`
// now passes both dotted and allowlisted single-segment canonical IDs
// through verbatim (allowlist derived from the artifact registry at
// import time), so the JS side reads canonical IDs straight off the
// wire with no aliasing. See `src/dual_research/ui/server.py::_to_camel`.

// Spec 0146 — one-decimal cost formatter scoped to the Consumption card.
// The global `fmt.cost` keeps 4-decimal precision for audit surfaces
// (footer aggregate, reconcile delta, status chips, tooltips).
function fmtCost1(n) {
  const v = Number(n) || 0;
  return `$${v.toFixed(1)}`;
}

// Spec 0165 §2.5 — two-decimal cost formatter for the expanded turn-card
// action row. Sub-cent values render as `<$0.01` so they don't round to
// `$0.00`. `fmt.cost` (4-decimal) stays the audit value for the run-detail
// footer aggregate per design-system/SPEC.md §4.3 / §4.4.
function fmtCost2(n) {
  if (n == null || isNaN(n)) return '$—';
  const v = Number(n) || 0;
  if (v > 0 && v < 0.01) return '<$0.01';
  return `$${v.toFixed(2)}`;
}

// Spec 0150 — synthetic display names for FE-only aggregate row ids
// that no longer have a registry entry (the bare `user_prompt`
// ArtifactDef was dropped; the canonical entries are `user_prompt.message`
// and `user_prompt.attachment.<id>`). The CcxCard still emits a
// synthetic `user_prompt` row that aggregates the message + attachments.
const SYNTHETIC_ROW_LABELS = {
  user_prompt: 'User prompt',
};

// Display-name resolver. Routes through the spec 0117 registry
// (window.DrArtifacts.displayName) so no display strings are hardcoded
// in the Consumption tab. Falls back to the artifact ID if the registry
// is missing (paranoid; the artifacts.jsx module always loads).
function consumptionLabel(artifactId) {
  if (SYNTHETIC_ROW_LABELS[artifactId]) return SYNTHETIC_ROW_LABELS[artifactId];
  if (window.DrArtifacts && typeof window.DrArtifacts.displayName === 'function') {
    return window.DrArtifacts.displayName(artifactId);
  }
  return artifactId;
}

// Spec 0149 §5.7 (D19) — per-attachment rich preview. Routes by attachment
// kind + file extension / MIME. Markdown / txt → <pre>; PDF → <iframe>;
// image → <img>; link → external anchor; else → download link. The
// matching from `attachmentId` (the `<id>` part of `user_prompt.attachment.<id>`)
// to an entry in `attachments.json` mirrors `buildAttachmentTitleMap`
// — sha256[:8] first, then slugified basename of rel_path / source.
function _deriveAttachmentSlug(a) {
  if (!a) return '';
  const sha = (a.sha256 || '').slice(0, 8);
  if (sha) return sha;
  const base = ((a.rel_path || a.source || '').split('/').pop() || '');
  return base
    .replace(/\.[^.]+$/, '')
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-|-$/g, '')
    || 'attachment';
}

function AttachmentPreview({ runId, attachmentId, displayTitle }) {
  const { attachments, loading } = window.useAttachments(runId);
  const att = React.useMemo(() => {
    if (!Array.isArray(attachments)) return null;
    for (const a of attachments) {
      if (_deriveAttachmentSlug(a) === attachmentId) return a;
    }
    return null;
  }, [attachments, attachmentId]);

  if (loading) {
    return (
      <div className="attachment-preview attachment-preview--loading" style={{
        fontSize: 11, color: 'var(--md-on-surface-faint)', padding: '4px 0 4px 36px',
      }}>
        Loading attachment…
      </div>
    );
  }
  if (!att) {
    return (
      <div className="attachment-preview attachment-preview--missing" style={{
        fontSize: 11, color: 'var(--md-on-surface-faint)', padding: '4px 0 4px 36px',
        fontStyle: 'italic',
      }}>
        No matching attachment for &nbsp;<code>{attachmentId}</code> &nbsp;in this run.
      </div>
    );
  }

  // Link-kind attachments (e.g. Notion pages) — render an external anchor.
  if (att.kind === 'link' || (!att.rel_path && att.url)) {
    return (
      <div className="attachment-preview attachment-preview--link" style={{
        fontSize: 11.5, padding: '4px 0 4px 36px',
      }}>
        <a href={att.url} target="_blank" rel="noopener noreferrer"
           style={{ color: 'var(--md-sys-color-primary)' }}>
          {att.title || displayTitle || att.url}
        </a>
        {att.source && (
          <span style={{ marginLeft: 8, color: 'var(--md-on-surface-faint)' }}>
            &middot; {att.source}
          </span>
        )}
      </div>
    );
  }

  // File-kind attachments — branch on extension / MIME.
  const relPath = att.rel_path || '';
  const blobUrl = window.attachmentBlobUrl(runId, relPath);
  const lower = relPath.toLowerCase();
  const mime = (att.mime || '').toLowerCase();
  const isText = lower.endsWith('.md') || lower.endsWith('.txt')
    || mime.startsWith('text/');
  const isPdf = lower.endsWith('.pdf') || mime === 'application/pdf';
  const isImage = lower.endsWith('.png') || lower.endsWith('.jpg')
    || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp')
    || mime.startsWith('image/');

  if (isText && blobUrl) {
    return <AttachmentTextPreview blobUrl={blobUrl} title={att.title || displayTitle} />;
  }
  if (isPdf && blobUrl) {
    return (
      <div className="attachment-preview attachment-preview--pdf" style={{
        padding: '4px 0 4px 36px',
      }}>
        <iframe
          src={blobUrl}
          title={att.title || displayTitle || relPath}
          style={{
            width: '100%', height: 420, border: '1px solid var(--md-outline-hair)',
            borderRadius: 4, background: 'var(--md-surface)',
          }}
        />
      </div>
    );
  }
  if (isImage && blobUrl) {
    return (
      <div className="attachment-preview attachment-preview--image" style={{
        padding: '4px 0 4px 36px',
      }}>
        <img
          src={blobUrl}
          alt={att.title || displayTitle || relPath}
          style={{
            maxWidth: '100%', maxHeight: 320,
            border: '1px solid var(--md-outline-hair)', borderRadius: 4,
          }}
        />
      </div>
    );
  }
  // Fallback — download link.
  return (
    <div className="attachment-preview attachment-preview--download" style={{
      fontSize: 11.5, padding: '4px 0 4px 36px',
    }}>
      {blobUrl ? (
        <a href={blobUrl} download={relPath.split('/').pop() || 'attachment'}
           style={{ color: 'var(--md-sys-color-primary)' }}>
          Download {att.title || displayTitle || relPath}
        </a>
      ) : (
        <span style={{ color: 'var(--md-on-surface-faint)', fontStyle: 'italic' }}>
          No previewable content
        </span>
      )}
    </div>
  );
}

// Lazy-fetch + truncated-render of a text / markdown attachment body.
// Capped at 80 lines with a "show more" affordance so the consumption
// card stays scannable.
function AttachmentTextPreview({ blobUrl, title }) {
  const [body, setBody] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [expanded, setExpanded] = React.useState(false);
  const MAX_LINES = 80;
  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(blobUrl)
      .then((r) => r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then((t) => { if (!cancelled) { setBody(t); setLoading(false); } })
      .catch(() => { if (!cancelled) { setBody(''); setLoading(false); } });
    return () => { cancelled = true; };
  }, [blobUrl]);
  if (loading) {
    return (
      <div className="attachment-preview attachment-preview--text-loading" style={{
        fontSize: 11, color: 'var(--md-on-surface-faint)', padding: '4px 0 4px 36px',
      }}>
        Loading {title || 'attachment'}…
      </div>
    );
  }
  const lines = body.split('\n');
  const truncated = !expanded && lines.length > MAX_LINES;
  const shown = truncated ? lines.slice(0, MAX_LINES).join('\n') : body;
  return (
    <div className="attachment-preview attachment-preview--text" style={{
      padding: '4px 0 4px 36px',
    }}>
      <pre style={{
        background: 'var(--md-surface-container-low)',
        border: '1px solid var(--md-outline-hair)',
        borderRadius: 4,
        padding: '8px 10px',
        margin: 0,
        fontSize: 11,
        fontFamily: 'var(--md-font-data)',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        maxHeight: expanded ? 'none' : 280,
        overflowY: 'auto',
      }}>{shown || '(empty)'}</pre>
      {truncated && (
        <button type="button" onClick={() => setExpanded(true)} style={{
          marginTop: 4, fontSize: 11, color: 'var(--md-sys-color-primary)',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
        }}>
          Show all {lines.length} lines
        </button>
      )}
    </div>
  );
}

// Spec 0145 §5.4 — indented sub-row for the User-prompt expansion. Reuses
// the existing 3-column ccx-bar-row grid; the `--sub` modifier indents
// the label and dims the bar color so the nesting reads clearly.
//
// Spec 0149 §5.7 (D19) — when `attachmentId` + `runId` are both set, a
// per-row chevron toggles a rich preview rendered by `AttachmentPreview`.
function SubInputRow({
  id, label, tokens, totalDenom, billedIn, inputCost, fillIn,
  runId, attachmentId,
}) {
  const piecePct = totalDenom > 0 ? Math.min(100, (tokens / totalDenom) * 100) : 0;
  const propCost = piecePropCost(tokens, billedIn, inputCost);
  const previewable = !!(runId && attachmentId);
  const [previewOpen, setPreviewOpen] = React.useState(false);
  return (
    <React.Fragment>
      {/* Spec 0180 §3.7 — grid layout on the .ccx-bar-row class; only the
          sub-row-specific offsets (left padding, opacity) stay inline. */}
      <div className="ccx-bar-row ccx-bar-row--sub" key={id} style={{
        paddingLeft: 20, opacity: 0.85,
      }}>
        <span className="lbl" style={{
          fontSize: 10.5, color: 'var(--md-on-surface-faint)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>
          {previewable && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setPreviewOpen((v) => !v); }}
              aria-expanded={previewOpen}
              aria-label={previewOpen ? 'Hide preview' : 'Show preview'}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                color: 'var(--md-on-surface-faint)', lineHeight: 1,
                transform: previewOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.15s',
              }}
            >
              <span className="ms ms-16">chevron_right</span>
            </button>
          )}
          {label}
        </span>
        <div className="ccx-bar" style={{ height: 5 }}>
          <div className={`fl ${fillIn}`} style={{ width: `${piecePct}%`, opacity: 0.7 }} />
        </div>
        <span className="num" style={{
          fontSize: 10.5, color: 'var(--md-on-surface-faint)', whiteSpace: 'nowrap',
          textAlign: 'right',
        }}>
          {fmt.tokens(tokens)}t &middot; {fmtCost1(propCost)}
        </span>
      </div>
      {previewable && previewOpen && (
        <AttachmentPreview
          runId={runId}
          attachmentId={attachmentId}
          displayTitle={label}
        />
      )}
    </React.Fragment>
  );
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
  // Spec 0118 collapsed-card: context-window percent uses
  // total = input + output (denominator of the bracketed header value).
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

  // Spec 0180 §3.2 — two stacked bars (total-input + total-output) share
  // a single denominator so the visual comparison is meaningful. Scale is
  // shared per-card-pair (claude vs gpt widths stay comparable); fallback
  // to max(totalTok, 1) when no scale denom is provided.
  const totalDenom = denom > 0 ? denom : Math.max(1, totalTok);
  const inputPct   = totalDenom > 0 ? Math.min(100, (tokensIn  / totalDenom) * 100) : 0;
  const outputPct  = totalDenom > 0 ? Math.min(100, (tokensOut / totalDenom) * 100) : 0;

  // Reuse overlay on the total-input bar (cache-reuse stripe). Cache reuse
  // is an input-side phenomenon — no stripe on the output bar.
  const reusePct = reuse.reused > 0 && totalDenom > 0
    ? Math.min(inputPct, (reuse.reused / totalDenom) * 100)
    : 0;

  // Spec 0150 — legacy-vocab branch retired; events are canonical-only.
  const grouped = groupPiecesForPhase(piecesRaw, phase);

  // Sum of piece tokens used as denominator for proportional cost.
  // Use billed input tokens (exact) so per-piece costs sum to inputCost.
  const billedIn = tokensIn;

  // Row renderer: grid layout is on the .ccx-bar-row class per spec 0180 §3.7.
  const renderInputRow = (row) => {
    const label = row.label || consumptionLabel(row.id);
    const tokens = row.tokens || 0;
    const piecePct = totalDenom > 0 ? Math.min(100, (tokens / totalDenom) * 100) : 0;
    const propCost = piecePropCost(tokens, billedIn, inputCost);
    const isSystem = row.id === 'system_prompt';
    const tip = isSystem && row.breakdown
      ? systemPromptTooltip(row.breakdown, tokens, propCost)
      : undefined;
    // Spec 0146 — User-prompt row with per-attachment breakdown auto-shows
    // its sub-rows when the card is unfolded. Spec 0145's chevron-collapse
    // is retired so the per-attachment surface is visible without a second
    // click.
    const hasSubRows = row.id === 'user_prompt' && row.attachmentBreakdown;
    return (
      <React.Fragment key={row.id}>
        <div className="ccx-bar-row" title={tip}>
          <span className="lbl" style={{
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {label}
          </span>
          <div className="ccx-bar" style={{ height: 6 }}>
            <div className={`fl ${fillIn}`} style={{ width: `${piecePct}%` }} />
          </div>
          <span className="num" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
            {fmt.tokens(tokens)}t &middot; {fmtCost1(propCost)}
          </span>
        </div>
        {hasSubRows && (
          <React.Fragment>
            {row.attachmentBreakdown.hasMessage && (
              <SubInputRow
                id="user_prompt.message"
                label={consumptionLabel('user_prompt.message')}
                tokens={row.attachmentBreakdown.message}
                totalDenom={totalDenom}
                billedIn={billedIn}
                inputCost={inputCost}
                fillIn={fillIn}
              />
            )}
            {row.attachmentBreakdown.attachments.map((att) => (
              <SubInputRow
                key={att.id}
                id={att.id}
                label={consumptionLabel(att.id)}
                tokens={att.tokens}
                totalDenom={totalDenom}
                billedIn={billedIn}
                inputCost={inputCost}
                fillIn={fillIn}
              />
            ))}
          </React.Fragment>
        )}
      </React.Fragment>
    );
  };

  // Spec 0180 §3.4 step 6 — per-output sub-rows (Reasoning / Response /
  // Tool calls) render inside the unfolded body, between the total-output
  // bar (now above the gate, §3.2) and the second divider. The output
  // header bar from V1 is gone — replaced by the always-visible
  // total-output bar.
  const outputBreakdown = usage.outputBreakdown || {};
  const rTok  = Number(outputBreakdown.reasoning)  || 0;
  const tcTok = Number(outputBreakdown.tool_calls) || 0;
  const rsTok = Number(outputBreakdown.response)   || 0;
  const hasOutputSplit = (rTok + tcTok) > 0 && tokensOut > 0;
  const renderOutputSubRow = (id, label, tokens) => (
    <SubInputRow
      key={id}
      id={id}
      label={label}
      tokens={tokens}
      totalDenom={totalDenom}
      billedIn={tokensOut > 0 ? tokensOut : 1}
      inputCost={outCostUsd}
      fillIn={fillOut}
    />
  );

  // Spec 0180 §3.6 — cache-savings derivation, lifted out of its V1 IIFE
  // inside the input totals so it can render in the output totals block.
  const cacheReadTokens = Number(usage?.cacheRead ?? usage?.cache_read ?? 0) || 0;
  const cacheSavingsUsd = Number(usage?.cacheSavingsUsd ?? usage?.cache_savings_usd ?? 0) || 0;
  const hasCacheSavings = cacheReadTokens > 0 && cacheSavingsUsd > 0;
  const cacheMultiplier = hasCacheSavings && tokensIn > 0
    ? cacheReadTokens / tokensIn
    : 0;

  return (
    <article className="ccx" data-tour-anchor={tourAnchor ? 'consumption-card' : undefined} onClick={onToggle} style={{ cursor: 'pointer' }}>
      {/* Spec 0180 §3.1 header: 4-column grid. hd-id · hd-totals (total
          tokens · total cost, right-aligned at bar-fill column's right
          edge) · stats (bracketed % of context) · chev. */}
      <header className="ccx-header">
        <span className="hd-id">
          <span className={`ccx-icon ${iconClass}`}>{meta.name[0]}</span>
          <span className="nm">{meta.name}</span>
        </span>
        <span className="hd-totals">
          <span className="num">{fmt.tokens(totalTok)}t</span>
          <span className="sep">&middot;</span>
          <span className="num">{fmtCost1(cost)}</span>
        </span>
        <span className="stats">
          ({pctOfCap.toFixed(1)}% of {_fmtCapLabel(ctxWindow)})
        </span>
        <span className="chev" tabIndex={0} role="button" aria-expanded={expanded}
              aria-label={expanded ? 'Collapse' : 'Expand'}
              style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <span className="ms ms-20">expand_more</span>
        </span>
      </header>

      {/* Spec 0180 §3.2 — total INPUT bar (collapsed + unfolded). Reuse
          stripe overlay retained — cache reuse is an input-side
          phenomenon. */}
      <div className="ccx-bar-row ccx-bar-row--total-input">
        <span className="lbl">Total input</span>
        <div className="ccx-bar">
          <div className={`fl ${fillIn}`} style={{ width: `${inputPct}%` }} />
          {reuse.hasReuse && (
            <div className="reuse" style={{ left: 0, width: `${reusePct}%` }} />
          )}
        </div>
        <span className="num" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
          {fmt.tokens(tokensIn)}t &middot; {fmtCost1(inputCost)}
        </span>
      </div>

      {/* Spec 0180 §3.2 — total OUTPUT bar (collapsed + unfolded). Same
          denominator as the input bar so visual comparison is
          meaningful. */}
      <div className="ccx-bar-row ccx-bar-row--total-output">
        <span className="lbl">Total output</span>
        <div className="ccx-bar">
          <div className={`fl ${fillOut}`} style={{ width: `${outputPct}%` }} />
        </div>
        <span className="num" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
          {fmt.tokens(tokensOut)}t &middot; {fmtCost1(outCostUsd)}
        </span>
      </div>

      {/* ── UNFOLDED SECTION (Spec 0180 §3.4) ──
          Order: per-input rows → divider → input totals → per-output
          sub-rows → divider → output totals. Both top bars already
          render above this gate. */}
      {expanded && (
        <React.Fragment>
          <div className="ccx-divider" />

          {/* Per-phase input rows. Always-separate user_prompt + phase-
              specific separates + System prompt aggregate. */}
          {grouped.rows.map(renderInputRow)}

          <div className="ccx-divider" />

          {/* Spec 0180 §3.5 — input totals block, input-only.
              Cache-savings line moved to the output totals (§3.6). */}
          <div className="ccx-totals">
            <div className="line">
              <span className="l">input tokens &middot; billed</span>
              <span className="v">{tokensIn.toLocaleString()}</span>
            </div>
            <div className="line">
              <span className="l">input cost</span>
              <span className="v">{fmtCost1(inputCost)}</span>
            </div>
            {hasSearches && (
              <div className="line">
                <span className="l">
                  web search &middot; {queries || searches}{' '}
                  {(queries || searches) === 1 ? 'query' : 'queries'}
                </span>
                <span className="v">{fmtCost1(searchCost)}</span>
              </div>
            )}
            <div className="line is-grand">
              <span className="l">total input</span>
              <span className="v">{fmtCost1(inputCost + searchCost)}</span>
            </div>
          </div>

          {/* Spec 0180 §3.4 step 6 — per-output sub-rows
              (Reasoning / Response / Tool calls) when the split data
              exists. Cost share via token-share proportional split is
              invoice-grade since output rate is a single per-model
              constant. */}
          {hasOutputSplit && (
            <React.Fragment>
              {rTok  > 0 && renderOutputSubRow('output.reasoning',  'Reasoning', rTok)}
              {rsTok > 0 && renderOutputSubRow('output.response',   'Response',  rsTok)}
              {tcTok > 0 && renderOutputSubRow('output.tool_calls', 'Tool calls', tcTok)}
            </React.Fragment>
          )}

          {hasOutputSplit && <div className="ccx-divider" />}

          {/* Spec 0180 §3.6 — output totals block. Cache-savings lives
              here per Issue 13 (cache reuse is an input-side phenomenon
              but the V2 anatomy surfaces it on the output side as a
              cost-savings annotation, paralleling input-side billed
              totals). Web-search line not duplicated here — the current
              wire format carries a single combined `searches`/`searchCost`
              that's surfaced in the input totals block above. */}
          <div className="ccx-totals ccx-totals--output">
            <div className="line">
              <span className="l">output tokens</span>
              <span className="v">{tokensOut.toLocaleString()}</span>
            </div>
            <div className="line">
              <span className="l">output cost</span>
              <span className="v">{fmtCost1(outCostUsd)}</span>
            </div>
            {hasCacheSavings && (
              <div className="line">
                <span className="l">
                  cache savings &middot; &times;{cacheMultiplier.toFixed(1)} reuse on{' '}
                  {(cacheReadTokens / 1000).toFixed(1)}kt
                </span>
                <span className="v">{fmtCost1(cacheSavingsUsd)}</span>
              </div>
            )}
            <div className="line is-grand">
              <span className="l">total output</span>
              <span className="v">{fmtCost1(outCostUsd)}</span>
            </div>
          </div>
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
          <span className="num" style={{ color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-medium)' }}>
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
        fontSize: 11, color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-medium)',
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
      <div style={{ fontSize: 13, color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-medium)' }}>
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
          fontWeight: 'var(--md-w-semi)',
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
        fontSize: 11, fontWeight: 'var(--md-w-bold)', color: labelColor,
        letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>{label}</span>
      <span style={{ flex: 1 }} />
      {count != null && (
        <span className="mono num" style={{
          fontSize: 11.5, color: labelColor, fontWeight: 'var(--md-w-semi)',
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
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 'var(--md-w-bold)',
      }}>
        Phase&nbsp;{item.phaseId}
      </span>
      <span style={{ color: 'var(--md-on-surface-decor)' }}>·</span>
      <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)', fontWeight: current ? 'var(--md-w-bold)' : 'var(--md-w-semi)' }}>
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
        <strong key={i} style={{ color: 'var(--md-on-surface)', fontWeight: 'var(--md-w-semi)' }}>
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
            fontWeight: 'var(--md-w-medium)',
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

  // ─── Phase 0 — multi-round brief critique (spec 0135) ──────────────────
  if (phase === 0 && item.round != null) {
    const parts = [];
    if (status === 'AGREED' || status === 'BRIEF_OK') parts.push(`${agentName} agreed`);
    else if (status === 'NEGOTIATING' || status === 'BRIEF_NEEDS_INPUT') parts.push(`${agentName} still negotiating`);
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
    if (typeof stats.briefIssues === 'number' && stats.briefIssues > 0) {
      parts.push(`${plur(stats.briefIssues, 'brief issue')}`);
    }
    return parts.length === 1 ? '' : parts[0] + ', ' + parts.slice(1).join(', ') + '.';
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

  // ─── Phase 0 — multi-round critique turn (spec 0135) ────────────────────
  if (phase === 0 && item.round != null) {
    const myNewQs = allQuestions.filter(
      q => q.phase === 0 && q.raisedBy === agent && q.raisedRound === round
    );
    const otherQsAnsweredHere = allQuestions.filter(
      q => q.phase === 0 && q.answeredRound === round && q.answeredBy === agent
    );
    const myOpenedDsHere = allDis.filter(
      d => d.phase === 0 && d.openedRound === round
              && (d.progression || []).some(p => p.round === round && p.agent === agent)
    );
    const myClosedDsHere = allDis.filter(
      d => d.phase === 0 && d.closedRound === round
              && (d.progression || []).some(p => p.round === round && p.agent === agent)
    );

    let sentimentWord = 'Neutral';
    let leadRest;
    if (status === 'AGREED' || status === 'BRIEF_OK') {
      sentimentWord = 'Positive';
      leadRest = `${agentName} agreed the brief is ready to research.`;
    } else if (status === 'NEGOTIATING' || status === 'BRIEF_NEEDS_INPUT' || !status) {
      if (round === 1) {
        sentimentWord = 'Cautious';
        leadRest = `${agentName}'s round-1 brief critique.`;
      } else if (myClosedDsHere.length === 0 && otherQsAnsweredHere.length === 0
                 && myOpenedDsHere.length === 0 && myNewQs.length === 0) {
        sentimentWord = 'Critical';
        leadRest = `${agentName} still negotiating in round ${round} with no movement.`;
      } else {
        sentimentWord = 'Cautious';
        leadRest = `${agentName} still negotiating in round ${round}.`;
      }
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
      sentences.push(`This round, ${agentName} ${movements.join(', ')}.`);
    }
    return sentences.join(' ');
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
// chip kinds its protocol actually emits. Phase 3 (silent drafter) +
// Phase 5 (final) have no structured turn items and render no chips.
// Phase 1 (plan draft) raises questions only. Phase 2 (negotiate)
// renders questions + disagreements. Phase 4 (review) renders
// issues + comments + disagreements.
//
// Spec 0119 §7 — the legacy ``claim`` category is gone post-0114.
// Spec 0135 promoted Phase 0 to a full multi-round negotiation that
// emits the same item kinds as Phase 2 (questions + disagreements);
// spec 0147 surfaces them via a P0 tab in the Critique pane.
const PHASE_CHIP_ALLOWLIST = {
  0: ['questions', 'disagreements'],
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
  if (id && SYNTHETIC_ROW_LABELS[id]) return SYNTHETIC_ROW_LABELS[id];
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
      && (item.statsPhase === 0 || item.statsPhase === 2 || item.statsPhase === 4)) {
    // Spec 0135 — Phase 0 multi-round critique cards open the same
    // side-by-side modal Phase 2 / Phase 4 use, with the brief on the
    // left at round 1 and the other agent's prior phase-0 turn at
    // round ≥ 2.
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
  // Spec 0135 — Phase 0 gets its own subtitle phrasing: round 1
  // critiques the brief directly; round ≥ 2 responds to the other
  // agent's prior phase-0 turn.
  let subtitle;
  if (item.statsPhase === 4) {
    subtitle = 'reviewing the converged document';
  } else if (item.statsPhase === 0) {
    const otherName = otherAgent === 'claude' ? 'Claude' : 'GPT';
    subtitle = (Number(item.round) || 1) === 1
      ? 'critiquing the brief'
      : `responding to ${otherName}'s prior critique`;
  } else {
    subtitle = `reviewing ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior content`;
  }
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
  // 8 + 10. The prior Spec 0085 default ('input' → the dual-bundle agent-
  // input view, since spec 0171 collapsed to AgentInputSingleColumn) was
  // confusing in a per-turn context where input vs output is the natural
  // mental model. 'input' stays one click away.
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
        {sub === 'input' && <AgentInputSingleColumn item={item} run={run} />}
        {sub === 'webSearch' && <WebSearchTabContent turnKey={item.turnKey} />}
      </div>
    </div>
  );
}

// Spec 0171 — Agent Input pane renders as a single column with an agent
// segmented selector at the top, instead of the spec-0101 dual-pane that
// stacked two narrow cards inside the already-narrow split-modal left
// pane. Anatomy matches the single-pane modals (DocumentModal,
// PreflightResponseModal, InputBriefModal): one PromptPiecesThreeSectionView
// at frame="single", driven by the canonical .tab-group-solid + .tab-solid
// segmented control (spec 0173 §2.3) for agent switching.
function AgentInputSingleColumn({ item, run }) {
  const timeline = React.useMemo(() => buildTimeline(run), [run]);
  const pairedTurn = React.useMemo(() => {
    return timeline.find((t) =>
      t.agent !== item.agent
      && t.statsPhase === item.statsPhase
      && Number(t.round) === Number(item.round)
    );
  }, [timeline, item]);

  const claudeKey = item.agent === 'claude' ? item.turnKey : pairedTurn?.turnKey;
  const gptKey = item.agent === 'gpt' ? item.turnKey : pairedTurn?.turnKey;

  const initialAgent = item.agent === 'gpt' ? 'gpt' : 'claude';
  const [selectedAgent, setSelectedAgent] = React.useState(initialAgent);
  const selectedTurnKey = selectedAgent === 'gpt' ? gptKey : claudeKey;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="tab-group-solid" role="group" aria-label="Select agent input">
        <button
          type="button"
          className="tab-solid"
          data-active={selectedAgent === 'claude' ? 'true' : 'false'}
          onClick={() => setSelectedAgent('claude')}
          title="Show Claude's input bundle"
        >
          <i className="dot" style={{ background: 'var(--claude)' }} />
          Claude
        </button>
        <button
          type="button"
          className="tab-solid"
          data-active={selectedAgent === 'gpt' ? 'true' : 'false'}
          onClick={() => setSelectedAgent('gpt')}
          title="Show GPT's input bundle"
        >
          <i className="dot" style={{ background: 'var(--gpt)' }} />
          GPT
        </button>
      </div>
      <PromptPiecesThreeSectionView turnKey={selectedTurnKey} frame="single" />
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
            <span className="mono num" style={{ fontWeight: 'var(--md-w-semi)' }}>{glyph}-{i + 1}</span>
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
  // Spec 0135 — accept `statsPhase === 0` explicitly (the legacy
  // `item.statsPhase || 2` fallback collapsed Phase 0 onto the Phase 2
  // path, which would point the left pane at a non-existent
  // `phase1/draft-<other>.md`).
  const phase = item.statsPhase != null ? item.statsPhase : 2;
  if (phase === 0) {
    const beAgent = otherUiAgent === 'gpt' ? 'openai' : otherUiAgent;
    const round = Number(item.round) || 1;
    if (round <= 1) return 'brief.md';
    const rr = String(round - 1).padStart(2, '0');
    return `phase0/round-${rr}-${beAgent}.md`;
  }
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
  // Spec 0135 — accept `statsPhase === 0` explicitly. See
  // `priorContentPathFor` for the same fix.
  const phase = item.statsPhase != null ? item.statsPhase : 2;
  const otherBe = otherUiAgent === 'gpt' ? 'openai' : otherUiAgent;
  const ownBe   = otherBe === 'openai' ? 'claude' : 'openai';
  const round   = Number(item.round) || 1;

  if (phase === 0) {
    // Phase 0 — brief is the artefact being critiqued. From round 2
    // onward the other agent's prior phase-0 turn joins as the default
    // tab.
    const tabs = [];
    if (round >= 2) {
      const rr = String(round - 1).padStart(2, '0');
      tabs.push({ id: 'priorTurn', label: "Other's prior turn",
                  path: `phase0/round-${rr}-${otherBe}.md` });
    }
    tabs.push({ id: 'brief', label: 'Brief', path: 'brief.md' });
    return tabs;
  }

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

// ─────────────────── Spec 0145 — Input tab + bundle rendering ───────────────
//
// Display names resolve via `window.DrArtifacts.displayName(id, {titleForId})`
// against the canonical artifact registry. Spec 0150 retired the read-shim;
// every bundle now arrives canonical-keyed (historical runs were backfilled).

// Spec 0178 — the per-piece default-collapse heuristic (spec 0085) was
// retired. With spec 0145 §5.4's outer InputSectionGroup gating the bulk
// system / prior-turn text, a second inner collapse default only created
// a "clicked but got nothing" two-click reveal bug. Inner per-piece
// chevrons stay present for user-initiated folding; their default state
// is now unconditionally open.

function isSystemPiece(canonicalKey) {
  return typeof canonicalKey === 'string' && canonicalKey.startsWith('system.');
}

function isUserPromptPiece(canonicalKey) {
  return canonicalKey === 'user_prompt.message'
    || (typeof canonicalKey === 'string' && canonicalKey.startsWith('user_prompt.attachment.'));
}

// Extract a phase integer 0..4 from a turn-key like 'phase2_round1_claude'
// or 'phase0_gpt'. Returns null for the special 'input' sentinel (which
// maps to phase 0 conceptually but doesn't carry the literal prefix).
function phaseNumFromTurnKey(turnKey) {
  if (typeof turnKey !== 'string') return null;
  if (turnKey === 'input') return 0;
  const m = /^phase(\d+)/.exec(turnKey);
  return m ? Number(m[1]) : null;
}

// Spec 0145 — order the (possibly canonicalised) piece keys by the
// per-phase canonical arrival order, with any extras appended at the
// end. `user_prompt.attachment.*` in the phase order expands into one
// row per attachment in their `pieces`-dict insertion order.
function orderPiecesForPhase(pieces, phaseNum) {
  const keys = Object.keys(pieces);
  if (phaseNum === null || phaseNum === undefined) return keys;
  const order = (window.DrArtifacts && window.DrArtifacts.phaseOrderFor)
    ? window.DrArtifacts.phaseOrderFor(phaseNum)
    : [];
  const seen = new Set();
  const out = [];
  for (const slot of order) {
    if (slot === 'user_prompt.attachment.*') {
      for (const k of keys) {
        if (k.startsWith('user_prompt.attachment.') && !seen.has(k)) {
          out.push(k);
          seen.add(k);
        }
      }
    } else if (keys.includes(slot) && !seen.has(slot)) {
      out.push(slot);
      seen.add(slot);
    }
  }
  for (const k of keys) {
    if (!seen.has(k)) out.push(k);
  }
  return out;
}

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
// Spec 0145 — three-section bucket assignment for the canonical-key
// piece rows. System.* lives under "System prompt"; user_prompt.* under
// "User prompt"; everything else under "Derived inputs". The buckets
// match the spec §5.4 section names; default-collapsed state mirrors
// the previous per-row heuristic so visual density is unchanged.
function sectionFor(canonicalKey) {
  if (typeof canonicalKey !== 'string') return 'derived';
  if (canonicalKey.startsWith('system.')) return 'system';
  if (canonicalKey === 'user_prompt.message') return 'user_prompt';
  if (canonicalKey.startsWith('user_prompt.attachment.')) return 'user_prompt';
  return 'derived';
}

// Spec 0145 §5.4 — shared three-section renderer. Single-pane consumers
// (InputTabContent → DocumentModal / PreflightResponseModal /
// InputBriefModal) plus the spec-0171 AgentInputSingleColumn all call
// it with `frame="single"`. The `frame` prop is retained as a vestigial
// hook; only "single" is in use today (spec 0171 retired "split" along
// with the dual-pane AgentInputPane).
function PromptPiecesThreeSectionView({ turnKey, attachmentTitles, frame = 'single' }) {
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
  const phaseNum = phaseNumFromTurnKey(turnKey);
  // Spec 0150 — bundles are canonical-only post-backfill.
  const pieces = bundle.pieces || {};
  const systemSource = bundle.system_source || 'recorded';
  // Spec 0151 §3.2 — keep every piece present in the bundle, including
  // empty-string values. Empty pieces render with an `(empty)`
  // placeholder so users can see the field exists in the bundle even
  // when no value was written for this turn (e.g. `phase1.claude` is
  // an empty string before Claude's draft lands at Phase 2 r1).
  const renderKeys = orderPiecesForPhase(pieces, phaseNum);

  if (renderKeys.length === 0) {
    return <InputEmptyState label="This turn's agent input bundle is empty." />;
  }

  // Spec 0145 §5.4 — bucket per-piece rows into three named sections:
  // System prompt · User prompt · Derived inputs. Each section has a
  // visible header; section bodies preserve the canonical arrival order
  // computed by `orderPiecesForPhase`.
  const grouped = { system: [], user_prompt: [], derived: [] };
  for (const key of renderKeys) {
    grouped[sectionFor(key)].push(key);
  }

  const sections = [
    {
      id: 'system',
      label: 'System prompt',
      keys: grouped.system,
      defaultOpen: false,
    },
    {
      id: 'user_prompt',
      label: 'User prompt',
      keys: grouped.user_prompt,
      defaultOpen: true,
    },
    {
      id: 'derived',
      label: 'Derived inputs',
      keys: grouped.derived,
      defaultOpen: false,
    },
  ].filter((s) => s.keys.length > 0);

  // Spec 0151 §3.1 — `frame="split"` reduces the inter-section gap to
  // suit the denser dual-pane layout; `frame="single"` keeps the
  // single-modal spacing unchanged from pre-0151.
  const outerGap = frame === 'split' ? 10 : 14;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: outerGap }}>
      {sections.map((section) => (
        <InputSectionGroup
          key={section.id}
          label={section.label}
          defaultOpen={section.defaultOpen}
          itemCount={section.keys.length}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {section.keys.map((key) => (
              <InputSection
                key={key}
                piece={key}
                text={pieces[key] || ''}
                isAgentDefault={isSystemPiece(key) && systemSource === 'agent-default'}
                attachmentTitles={attachmentTitles}
              />
            ))}
          </div>
        </InputSectionGroup>
      ))}
    </div>
  );
}

// Spec 0145 §5.4 introduced the three-section grouping; spec 0151 §3.1
// extracted it into PromptPiecesThreeSectionView so the dual-pane
// preflight renderer could share the same structure. Spec 0171 retired
// the dual-pane consumer; InputTabContent + AgentInputSingleColumn are
// now the only callers.
function InputTabContent({ turnKey, attachmentTitles }) {
  return (
    <PromptPiecesThreeSectionView
      turnKey={turnKey}
      attachmentTitles={attachmentTitles}
      frame="single"
    />
  );
}

// Spec 0145 §5.4 — section header above a per-piece-row group inside
// the User-prompt tab. Reuses the existing CollapsibleSection visual
// shape with a slightly heavier label so the section nesting is legible.
function InputSectionGroup({ label, defaultOpen, itemCount, children }) {
  return (
    <CollapsibleSection
      defaultOpen={defaultOpen}
      renderTitle={({ open }) => (
        <>
          <span className="cs-chevron" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
          <span
            className="cs-title"
            style={{
              fontWeight: 'var(--md-w-medium)',
              fontSize: 12.5,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {label}
          </span>
          <span style={{ flex: 1 }} />
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
            {itemCount} {itemCount === 1 ? 'piece' : 'pieces'}
          </span>
        </>
      )}
    >
      <div style={{ paddingLeft: 8, borderLeft: '1px solid var(--md-outline-variant)', marginTop: 6 }}>
        {children}
      </div>
    </CollapsibleSection>
  );
}

// Spec 0074 D4 — uses CollapsibleSection for consistent disclosure UX.
// Spec 0074 D5 — body rendered via Markdown instead of raw <pre>.
// Spec 0085 — when the system piece is the agent's default (not the
// per-run recorded prompt), prepend a small italic caveat inside the
// body so the user knows the displayed text may differ from what the
// historical run actually used.
function InputSection({ piece, text, isAgentDefault, attachmentTitles }) {
  // Spec 0145 — resolve the row label via the canonical-ID registry.
  // Attachment IDs need a `titleForId` map so the template
  // `Attachment · {title}` substitutes the human-readable name from
  // attachments.json (passed in via the modal-level `attachmentTitles`).
  const label = (window.DrArtifacts && window.DrArtifacts.displayName)
    ? window.DrArtifacts.displayName(piece, { titleForId: attachmentTitles || {} })
    : piece;
  const chars = text ? text.length : 0;
  const approxTokens = text ? Math.max(1, Math.round(text.length / 3.5)) : 0;
  const stats = `${chars.toLocaleString()} chars · ~${approxTokens.toLocaleString()}t`;

  return (
    <div className="agent-input-entry">
      <CollapsibleSection
        defaultOpen={true}
        renderTitle={({ open }) => (
          <>
            <span className="cs-chevron" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
            <span className="cs-title" style={{ fontWeight: 'var(--md-w-medium)', fontSize: 12 }}>{label}</span>
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
          {text
            ? <Markdown text={text} />
            : <span className="prompt-piece__empty">(empty)</span>}
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
        fontSize: 12, color: COLORS.warn, fontWeight: 'var(--md-w-semi)',
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
        <span style={{ fontWeight: 'var(--md-w-medium)', flex: 1, minWidth: 0,
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
             fontSize: 12.5, fontWeight: 'var(--md-w-medium)',
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
             fontSize: 12.5, fontWeight: 'var(--md-w-medium)',
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

// Spec 0145 — build the `titleForId` map the canonical-ID display
// templates need to resolve `user_prompt.attachment.<id>` rows to
// `Attachment · {title}`. Keyed by the same `_attachment_id` the
// orchestrator emits (sha256[:8] fallback to slugified basename).
function buildAttachmentTitleMap(attachments) {
  const out = {};
  if (!Array.isArray(attachments)) return out;
  for (const a of attachments) {
    if (!a) continue;
    const sha = (a.sha256 || '').slice(0, 8);
    const id = sha
      || ((a.rel_path || a.source || '').split('/').pop() || '').replace(/\.[^.]+$/, '').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '')
      || 'attachment';
    out[id] = a.title || (a.rel_path || a.source || '').split('/').pop() || 'attachment';
  }
  return out;
}

function InputBriefModal({ item, run, onClose, accent }) {
  // Spec 0145 §5.4 — collapsed to a single "User prompt" tab containing
  // the three-section InputTabContent restructure. The legacy four-tab
  // layout (Content / Agent Input / Sources / Files) is replaced; the
  // brief markdown surfaces as the `user_prompt.message` row, and any
  // attachments surface as `user_prompt.attachment.<id>` rows in
  // attachment-list order. Empty Sources/Files surfaces simply disappear.
  const { attachments } = window.useAttachments(run.id);
  const attachmentTitles = React.useMemo(
    () => buildAttachmentTitleMap(attachments),
    [attachments],
  );

  const tabs = [
    {
      id: 'user_prompt',
      label: 'User prompt',
      content: (
        <InputTabContent
          turnKey={item.turnKey || 'input'}
          attachmentTitles={attachmentTitles}
        />
      ),
    },
  ];

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
  // Spec 0145 — Web Search stays; the Agent Input tab is restructured
  // (renamed to "User prompt" + three-section grouping) but the agent's
  // response markdown is kept under the Content tab because it isn't
  // covered by the user-prompt grouping.
  const { attachments } = window.useAttachments(run.id);
  const attachmentTitles = React.useMemo(
    () => buildAttachmentTitleMap(attachments),
    [attachments],
  );
  const webSearch = useWebSearchTab(turnKey);
  const tabs = sortByCanon([
    {
      id: 'content',
      label: 'Content',
      content: <LazyMarkdownBody filePath={item.filePath} />,
    },
    {
      id: 'input',
      label: 'User prompt',
      content: (
        <InputTabContent
          turnKey={turnKey}
          attachmentTitles={attachmentTitles}
        />
      ),
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

// Spec 0149 §5.10 (D20) — six dead preflight components removed
// (PreflightContentTab, PreflightSourcesTab, PreflightFilesTab,
// AttachmentsEmpty, SourceRowAttachment, FileCard) along with the
// formatBytes helper that was used only by FileCard. All six lost their
// last external caller when spec 0145 collapsed the preflight modal
// down to a single "User prompt" tab; they were retained then for
// minimal blast radius and are removed here.

function FinalDocPreview() {
  return (
    <div>
      <h2 style={{ margin: '0 0 10px', fontSize: 15, color: 'var(--md-on-surface)', fontWeight: 'var(--md-w-semi)', letterSpacing: '-0.01em', lineHeight: 1.35 }}>
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
  // Spec 0147 — Phase 0 joins the active-tab fallback chain. While the run
  // is in Phase 0, the critique pane defaults to P0; otherwise the
  // existing precedence (latest active > earliest has-items) takes over.
  const initial = (run.phase === 4 || run.phase === 2 || run.phase === 0) ? run.phase
                 : haveAny(4) ? 4
                 : haveAny(2) ? 2
                 : haveAny(0) ? 0
                 : 2;
  const [selectedPhase, setSelectedPhase] = React.useState(initial);
  const [kindFilter, setKindFilter] = React.useState('all');
  const [agentFilter, setAgentFilter] = React.useState('all');
  const [statusFilter, setStatusFilter] = React.useState('all');
  // Spec 0175 §2.5 — auto-jump to summary on `running → terminal` transition,
  // unless the user has manually picked a different tab during this session.
  const userPickedTabRef = React.useRef(false);
  const wasTerminalRef = React.useRef(isTerminal);
  React.useEffect(() => {
    setSelectedPhase(initial);
    setKindFilter('all'); setAgentFilter('all'); setStatusFilter('all');
    userPickedTabRef.current = false;
    wasTerminalRef.current = isTerminal;
  }, [run.id, initial, isTerminal]);
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
  // Spec 0175 §2.5 — fires once when isTerminal flips false → true, if the
  // user hasn't manually picked a non-summary tab during this session.
  React.useEffect(() => {
    if (!wasTerminalRef.current && isTerminal && !userPickedTabRef.current) {
      setSelectedPhase('summary');
    }
    wasTerminalRef.current = isTerminal;
  }, [isTerminal]);

  // Spec 0175 §2.5 — picking any tab suppresses the auto-jump for the
  // rest of this session (until run.id changes).
  const pickPhase = React.useCallback((phase) => {
    userPickedTabRef.current = true;
    setSelectedPhase(phase);
  }, []);

  // Spec 0119 §8.1 + Q2 — cross-pane jump: a click on a timeline turn
  // card's category chip dispatches `dr-critique-jump` with
  // (category, round, phase); the critique pane snaps to that phase +
  // category filter and scrolls itself into view.
  React.useEffect(() => {
    const handler = (e) => {
      const detail = e.detail || {};
      const { category, phase: targetPhase } = detail;
      if (targetPhase === 0 || targetPhase === 2 || targetPhase === 4) {
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
  // Spec 0151 §3.4.1.3 — reinstate the run-wide drift count for bar1.
  // Spec 0119 §8.6 had retired the drift surface from the critique
  // header; spec 0151 supersedes that decision per the design-system
  // target at design-system/notion-issues/screenshots/02-critique-target.png
  // (which shows `⚠ N drift` adjacent to the introduced/open/resolved
  // totals). Uses the same `isDrift` predicate as the bar2 chip so the
  // header count matches what the user can filter to.
  const runWideDrift = allPhaseItems.filter((it) => isDrift(it)).length;

  // Kind-tab counts (filtered by agent + status)
  const filteredAll = [...openNewItems, ...openCarriedItems, ...resolvedItems, ...driftItems];
  const kindCounts = {
    all: filteredAll.length,
    issues: filteredAll.filter(it => it._critiqueKind === 'i').length,
    comments: filteredAll.filter(it => it._critiqueKind === 'c').length,
    questions: filteredAll.filter(it => it._critiqueKind === 'q').length,
    disagreements: filteredAll.filter(it => it._critiqueKind === 'd').length,
  };

  // Spec 0173 §2.4 — per-segment counts on agent + status filter
  // buttons. Computed over the unfiltered active-phase item list so
  // each button shows a stable "what's available here" count regardless
  // of the other filters' current state. Drift uses the same `isDrift`
  // predicate as Bar 1's `runWideDrift`. Comments are bucketed under
  // "resolved" (non-blocking commentary, matching `pushItem`'s
  // `isResolved = isComment || ...` branch). `All` and `Drift` counts
  // must always render even at 0 (chip-stability rule from spec 0167
  // §2.2).
  const agentCounts = {
    all: allPhaseItems.length,
    claude: allPhaseItems.filter(it => it.raisedBy === 'claude').length,
    gpt: allPhaseItems.filter(it => it.raisedBy === 'gpt').length,
  };
  const _commentIds = new Set(phaseComments.map(c => c.id));
  const statusCounts = {
    all: allPhaseItems.length,
    open: allPhaseItems.filter(it => !_commentIds.has(it.id) && _isOpenStatus(it.status) && !isDrift(it)).length,
    resolved: allPhaseItems.filter(it => _commentIds.has(it.id) || _isResolvedStatus(it.status)).length,
    drift: allPhaseItems.filter(it => isDrift(it)).length,
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

  // Spec 0097 — unified renderItem: legacy items → <QuestionThread />.
  // Spec 0144 §6.2.a — new-protocol items (those present in
  // ``run.phaseStats.items`` with a ``transitions`` array from the
  // ItemRaised/ItemTransitioned event stream) route through
  // <ItemCard /> so ``evidence``, ``transitions``, ``anchor_*``, and
  // ``evidence_required`` survive the trip from the event bus to the
  // JSX. This single switch closes B09's render gap for all four
  // kinds simultaneously and makes B08 (missing I/C patches on
  // Phase 4 cards) fall out automatically because ItemCard is
  // kind-agnostic.
  const _itemsAll = (run.phaseStats?.items) || [];
  const _itemsById = new Map();
  for (const it of _itemsAll) {
    if (it && it.id) _itemsById.set(it.id, it);
  }
  const renderItem = (item) => {
    const newItem = _itemsById.get(item && item.id);
    if (newItem && Array.isArray(newItem.transitions)) {
      const variant = item._critiqueKind || (
        newItem.kind === 'disagreement' ? 'd'
        : newItem.kind === 'issue' ? 'i'
        : newItem.kind === 'comment' ? 'c'
        : 'q'
      );
      const highlightKeys = [item.raisedTurnKey, item.answeredTurnKey, item.closedTurnKey]
        .filter(Boolean);
      const highlightFn = () => {
        if (!handleHighlight) return;
        handleHighlight(highlightKeys, variant);
      };
      return <ItemCard key={newItem.id} item={newItem} onHighlight={highlightFn} />;
    }
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

  // Spec 0151 §3.4.1 — the previous KIND_TABS descriptor + its private
  // helpers (`_phaseItemsForCount`, `_itemCountByKind`, `_displayCount`,
  // formerly used to munge "Label (N)" strings) are removed. The
  // kind-filter row is now rendered inline below via
  // <TabGroup variant="kind-tabs"> + <Tab variant="kind" count={…}>,
  // which surfaces the count as a separate visual token per the
  // design-system target (count appears next to the label, not inside it).

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
          {/* Spec 0175 \u00A72.5 \u2014 onClick goes through pickPhase so the
              auto-jump-to-summary effect knows the user has chosen
              a tab in this session. */}
          <button
            className={`phase-tab${selectedPhase === 0 ? ' is-active' : ''}`}
            onClick={() => pickPhase(0)}>
            <span className="pcode">P0</span><span className="pname">Brief</span>
          </button>
          <button
            className={`phase-tab${selectedPhase === 2 ? ' is-active' : ''}`}
            onClick={() => pickPhase(2)}>
            <span className="pcode">P2</span><span className="pname">Negotiate</span>
          </button>
          <button
            className={`phase-tab${selectedPhase === 4 ? ' is-active' : ''}`}
            onClick={() => pickPhase(4)}>
            <span className="pcode">P4</span><span className="pname">Review</span>
          </button>
          {isTerminal && (
            <button
              className={`phase-tab${selectedPhase === 'summary' ? ' is-active' : ''}`}
              onClick={() => pickPhase('summary')}>
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
          {/* Spec 0151 §3.4.1.3 — reinstated run-wide drift pill,
              superseding the spec 0119 §8.6 decision to retire it. The
              design-system target (`02-critique-target.png`) shows the
              `⚠ N drift` pill adjacent to the introduced/open/resolved
              totals; this restores that affordance. Per-phase drift on
              the timeline header and validate-run remain canonical
              alternative surfaces.

              Spec 0167 §2.3 — the slot is now rendered unconditionally
              with `data-count={N}`. When count=0 the chip renders muted
              (.crit-drift-pill[data-count="0"] in components.css) so the
              bar-1 right cluster doesn't reflow if drift appears mid-run.
              Per spec 0167 §2.3 + design-system/SPEC.md §4.1. */}
          <span
            className="crit-drift-pill"
            data-count={runWideDrift}
            role="status"
            title={
              runWideDrift > 0
                ? `${runWideDrift} item${runWideDrift === 1 ? '' : 's'} with ledger drift`
                : 'No items with ledger drift'
            }
          >
            <Mdi name="alert" size={11} color="var(--p-warn)" />
            <span className="crit-drift-pill__n">{runWideDrift}</span>
            <span className="crit-drift-pill__lbl">drift</span>
          </span>
        </div>
      </header>

      {/* BAR 2 — Spec 0151 §3.4.1 — design-system parity. Layout per
          design-system/notion-issues/screenshots/02-critique-target.png:
          [kind-tabs row]  [agent .tab-group-solid] [state .tab-group-solid]
          The kind-tab row uses .kind-tabs / .kind-tab CSS already
          present in components.css; the agent and state filters use
          the canonical .tab-group-solid segmented control (renamed
          from .fgroup by spec 0173 §2.3, with `[data-active="true"]`
          attribute state replacing `.is-active` class). Pre-0151 this
          row used <Chip> for everything with label-embedded count
          strings (`Issues (3)`) — superseded so counts render as
          separate tokens per the target. Spec 0173 §2.4 adds
          per-segment counts on every button (incl. All and Drift at 0,
          chip-stability rule from spec 0167 §2.2). */}
      {!isSummary && (
        <header className="bar2 crit-filter-row">
          {/* Spec 0167 §2.5 / §2.6 — kind-cluster order locked to
              Q · D · I · C (matches timeline `.tl-phase__chips` cluster).
              The leading "All" reset chip is dropped — no active kind
              chip = "show all categories". Clicking an active chip
              deselects it (toggles kindFilter back to 'all'). The bar-1
              `.crit-totals` is the run-wide global; the kind cluster
              shows per-kind phase counts only. */}
          <TabGroup variant="kind-tabs">
            <Tab
              variant="kind"
              active={kindFilter === 'questions'}
              count={kindCounts.questions || 0}
              onClick={() => setKindFilter(kindFilter === 'questions' ? 'all' : 'questions')}
            >Questions</Tab>
            <Tab
              variant="kind"
              active={kindFilter === 'disagreements'}
              count={kindCounts.disagreements || 0}
              onClick={() => setKindFilter(kindFilter === 'disagreements' ? 'all' : 'disagreements')}
            >Disagreements</Tab>
            <Tab
              variant="kind"
              active={kindFilter === 'issues'}
              count={kindCounts.issues || 0}
              onClick={() => setKindFilter(kindFilter === 'issues' ? 'all' : 'issues')}
            >Issues</Tab>
            <Tab
              variant="kind"
              active={kindFilter === 'comments'}
              count={kindCounts.comments || 0}
              onClick={() => setKindFilter(kindFilter === 'comments' ? 'all' : 'comments')}
            >Comments</Tab>
          </TabGroup>

          <span className="crit-filter-spacer" aria-hidden="true" />

          {/* Agent segment — [All N] [• Claude N] [• GPT N] */}
          <div className="tab-group-solid" role="group" aria-label="Filter by raising agent">
            <button
              type="button"
              className="tab-solid"
              data-active={agentFilter === 'all' ? 'true' : 'false'}
              onClick={() => setAgentFilter('all')}
              title="Show items raised by any agent"
            >
              All
              <span className="chip-value">{agentCounts.all}</span>
            </button>
            <button
              type="button"
              className="tab-solid"
              data-active={agentFilter === 'claude' ? 'true' : 'false'}
              onClick={() => setAgentFilter('claude')}
              title="Show only items raised by Claude"
            >
              <i className="dot" style={{ background: 'var(--claude)' }} />
              Claude
              <span className="chip-value">{agentCounts.claude}</span>
            </button>
            <button
              type="button"
              className="tab-solid"
              data-active={agentFilter === 'gpt' ? 'true' : 'false'}
              onClick={() => setAgentFilter('gpt')}
              title="Show only items raised by GPT"
            >
              <i className="dot" style={{ background: 'var(--gpt)' }} />
              GPT
              <span className="chip-value">{agentCounts.gpt}</span>
            </button>
          </div>

          {/* State segment — [All N] [Open N] [Resolved N] [Drift N?] */}
          <div className="tab-group-solid" role="group" aria-label="Filter by item state">
            <button
              type="button"
              className="tab-solid"
              data-active={statusFilter === 'all' ? 'true' : 'false'}
              onClick={() => setStatusFilter('all')}
              title="Show items in any state"
            >
              All
              <span className="chip-value">{statusCounts.all}</span>
            </button>
            <button
              type="button"
              className="tab-solid"
              data-active={statusFilter === 'open' ? 'true' : 'false'}
              onClick={() => setStatusFilter('open')}
              title="Show only open items"
            >
              Open
              <span className="chip-value">{statusCounts.open}</span>
            </button>
            <button
              type="button"
              className="tab-solid"
              data-active={statusFilter === 'resolved' ? 'true' : 'false'}
              onClick={() => setStatusFilter('resolved')}
              title="Show only resolved items"
            >
              Resolved
              <span className="chip-value">{statusCounts.resolved}</span>
            </button>
            {kindFilter !== 'questions' && (
              <button
                type="button"
                className="tab-solid"
                data-active={statusFilter === 'drift' ? 'true' : 'false'}
                onClick={() => setStatusFilter('drift')}
                title="Show only items with ledger drift"
              >
                Drift
                <span className="chip-value">{statusCounts.drift}</span>
              </button>
            )}
          </div>
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
      // Spec 0144 §6.2.b — surface evidence / transitions / anchor /
      // evidence_required on the props bag even on the legacy path so
      // a future caller that still routes a new-protocol item through
      // QuestionThread doesn't throw the data away. Defaults are safe
      // for pre-0114 archived runs that never captured these fields.
      evidence: q.evidence || [],
      transitions: q.transitions || [],
      anchor_type: q.anchor_type || q.anchorType || 'none',
      anchor_text: q.anchor_text || q.anchorText || '',
      evidence_required: !!(q.evidence_required || q.evidenceRequired),
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
      // Spec 0144 §6.2.b — see question branch above.
      evidence: d.evidence || [],
      transitions: d.transitions || [],
      anchor_type: d.anchor_type || d.anchorType || 'none',
      anchor_text: d.anchor_text || d.anchorText || '',
      evidence_required: !!(d.evidence_required || d.evidenceRequired),
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
      // Spec 0144 §6.2.b — see question branch above.
      evidence: issue.evidence || [],
      transitions: issue.transitions || [],
      anchor_type: issue.anchor_type || issue.anchorType || 'none',
      anchor_text: issue.anchor_text || issue.anchorText || '',
      evidence_required: !!(issue.evidence_required || issue.evidenceRequired),
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
      // Spec 0144 §6.2.b — see question branch above.
      evidence: comment.evidence || [],
      transitions: comment.transitions || [],
      anchor_type: comment.anchor_type || comment.anchorType || 'none',
      anchor_text: comment.anchor_text || comment.anchorText || '',
      evidence_required: !!(comment.evidence_required || comment.evidenceRequired),
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
          {phaseId === 0 ? (
            // Spec 0147 \u2014 defensive: in practice Phase 0 starts at run
            // creation and `run.phase < 0` is never true, but if the
            // pending guard ever fires this gives an honest message.
            <>Phase 0 hasn't started yet. The brief negotiation begins on run start.</>
          ) : phaseId === 2 ? (
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

// Spec 0175 §2.10 — kind dot palette aliases used by CritiqueBreakdown
// sub-rows. The four hues match the canonical M3-aligned chip tones
// (DS SPEC §3 — Chip; spec 0167 §2.5).
const _KIND_DOT = {
  question: COLORS.info,
  disagreement: COLORS.warn,
  issue: COLORS.err,
  comment: 'var(--md-on-surface-muted)',
};

// Spec 0175 §2.3 — pure helper: derive every number the Summary tab
// renders from the run snapshot. Pure function, no DOM / context
// access — covered by tests/spec0175/test_compute_summary_stats.py.
function _computeSummaryStats(run, questions, disagreements, issues, comments) {
  const claudeAgent = (run && run.agents && run.agents.claude) || {};
  const gptAgent    = (run && run.agents && run.agents.gpt)    || {};
  const cTok = (claudeAgent.tokens?.in || 0) + (claudeAgent.tokens?.out || 0);
  const gTok = (gptAgent.tokens?.in    || 0) + (gptAgent.tokens?.out    || 0);
  const totalTokens = cTok + gTok;
  const cCost = claudeAgent.cost || 0;
  const gCost = gptAgent.cost    || 0;
  const totalCost = cCost + gCost;

  const timings = (run && run.phaseTimings) || {};
  let elapsedTotal = 0;
  for (const v of Object.values(timings)) {
    if (typeof v === 'number' && v > 0) elapsedTotal += v;
  }

  const totalItems = questions.length + disagreements.length + issues.length;
  const totalComments = comments.length;
  const totalRaised = totalItems + totalComments;

  const resolvedQ = questions.filter((q) => q.status !== 'open').length;
  const resolvedD = disagreements.filter((d) => (d.status || '').startsWith('resolved')).length;
  const resolvedI = issues.filter((i) => i.status === 'resolved').length;
  const totalResolved = resolvedQ + resolvedD + resolvedI;
  const resolveRatio = totalItems > 0 ? totalResolved / totalItems : 1;

  // Per-agent tally (spec 0175 §2.3). The `'both'` closer (resolved-both)
  // is NOT credited to either per-agent solved row — it's surfaced
  // separately as `mutualAligned`.
  const raised = {
    claude: { question: 0, disagreement: 0, issue: 0, comment: 0 },
    gpt:    { question: 0, disagreement: 0, issue: 0, comment: 0 },
  };
  const solved = {
    claude: { question: 0, disagreement: 0, issue: 0 },
    gpt:    { question: 0, disagreement: 0, issue: 0 },
  };

  const _creditRaise = (item, kind) => {
    const r = item.raisedBy;
    if (r === 'claude' || r === 'both') raised.claude[kind]++;
    if (r === 'gpt' || r === 'both')    raised.gpt[kind]++;
  };
  const _creditSolve = (closer, kind) => {
    if (closer === 'claude') solved.claude[kind]++;
    else if (closer === 'gpt') solved.gpt[kind]++;
    // closer === 'both' → counted in mutualAligned only (below).
  };

  questions.forEach((q) => {
    _creditRaise(q, 'question');
    if (q.status !== 'open' && q.answeredBy) _creditSolve(q.answeredBy, 'question');
  });

  // Spec 0119 §7 — `resolved-claude` = Claude yielded, `resolved-gpt` = GPT yielded,
  // `resolved-both` = mutual alignment.
  let mutualAligned = 0;
  disagreements.forEach((d) => {
    _creditRaise(d, 'disagreement');
    const s = d.status || '';
    if (s === 'resolved-claude') _creditSolve('claude', 'disagreement');
    else if (s === 'resolved-gpt') _creditSolve('gpt', 'disagreement');
    else if (s === 'resolved-both') mutualAligned++;
  });

  issues.forEach((i) => {
    _creditRaise(i, 'issue');
    if (i.status === 'resolved' && i.raisedBy) _creditSolve(i.raisedBy, 'issue');
  });

  comments.forEach((c) => _creditRaise(c, 'comment'));

  const claudeRaisedTotal = raised.claude.question + raised.claude.disagreement + raised.claude.issue + raised.claude.comment;
  const gptRaisedTotal    = raised.gpt.question    + raised.gpt.disagreement    + raised.gpt.issue    + raised.gpt.comment;
  const claudeSolvedTotal = solved.claude.question + solved.claude.disagreement + solved.claude.issue;
  const gptSolvedTotal    = solved.gpt.question    + solved.gpt.disagreement    + solved.gpt.issue;

  // Drift count from phase ledgers (existing logic).
  const ledgers = (run && run.phaseLedgers) || {};
  let driftCount = 0;
  for (const phaseId of Object.keys(ledgers)) {
    for (const entry of (ledgers[phaseId] || [])) {
      if ((entry.ghostedRounds || 0) > 0) driftCount++;
    }
  }
  const driftRatio = totalItems > 0 ? driftCount / totalItems : 0;

  // Verdict — spec 0175 §2.2 tightens the green threshold from 0.7 → 0.85.
  let verdict;
  if (totalItems === 0) verdict = 'Inconclusive';
  else if (resolveRatio >= 0.85 && driftRatio < 0.2) verdict = 'Mostly positive';
  else if (resolveRatio < 0.40 || driftRatio >= 0.40) verdict = 'Mostly negative';
  else verdict = 'Mixed';

  // Round count: max round across items, falling back to run.round.current.
  const roundFromItems = [...questions, ...disagreements, ...issues, ...comments]
    .map((it) => Number(it.raisedRound || it.raised_round || 0))
    .reduce((m, v) => (v > m ? v : m), 0);
  const currentRound = run?.round?.current || 0;
  const roundCount = Math.max(roundFromItems, currentRound);

  return {
    cTok, gTok, totalTokens,
    cCost, gCost, totalCost,
    elapsedTotal,
    roundCount,
    totalItems, totalComments, totalRaised,
    totalResolved, resolveRatio,
    driftCount, driftRatio,
    verdict,
    mutualAligned,
    raised, solved,
    claudeRaisedTotal, gptRaisedTotal,
    claudeSolvedTotal, gptSolvedTotal,
  };
}

// Spec 0175 §2.7 — web-search stat: queries + URLs retrieved across all
// turns. SearchIndexContext.summary is a Map<turnKey, { queries: N, consulted: M, … }>.
function _computeWebSearchStats(searchSummary) {
  if (!searchSummary || typeof searchSummary.values !== 'function') {
    return { queries: 0, consulted: 0, hasAny: false };
  }
  let queries = 0;
  let consulted = 0;
  for (const entry of searchSummary.values()) {
    queries += (entry?.queries || 0);
    consulted += (entry?.consulted || 0);
  }
  return { queries, consulted, hasAny: queries > 0 || consulted > 0 };
}

// Spec 0175 §2.4 — verdict tone lookup. Resolved at runtime so the
// status-aware hero (errored variant) can override the computed verdict.
function _pickVerdictTone(verdict, runStatus) {
  if (runStatus === 'errored') {
    return { key: 'errored', color: COLORS.err, label: 'Incomplete' };
  }
  if (verdict === 'Mostly positive') return { key: 'positive', color: COLORS.ok,   label: 'Mostly positive' };
  if (verdict === 'Mostly negative') return { key: 'negative', color: COLORS.warn, label: 'Mostly negative' };
  if (verdict === 'Mixed')           return { key: 'mixed',    color: COLORS.info, label: 'Mixed' };
  return { key: 'inconclusive', color: 'var(--md-on-surface-muted)', label: 'Inconclusive' };
}

// Spec 0175 §2.4 — hero variant copy. Returns the cheer line, glyph
// name, and explanation line for each terminal status.
function _pickHeroVariant(run, stats) {
  const status = run?.status;
  if (status === 'deadlocked') {
    const hardCap = run?.round?.hard || run?.round?.total || stats.roundCount;
    return {
      cheer: 'Run deadlocked · ran out of rounds',
      glyph: 'pause',
      glyphColor: COLORS.warn,
      explanation: `Hit the hard cap of ${hardCap} rounds with ${stats.totalItems - stats.totalResolved} items still open.`,
    };
  }
  if (status === 'errored') {
    const err = run?.error || {};
    const where = err.where || 'unknown phase';
    return {
      cheer: `Run errored at ${where}`,
      glyph: 'alert',
      glyphColor: COLORS.err,
      explanation: err.detail || 'No further detail.',
      code: err.code || null,
    };
  }
  // completed / converged
  if (stats.totalItems === 0) {
    return {
      cheer: 'Run complete',
      glyph: 'help-circle',
      glyphColor: 'var(--md-on-surface-muted)',
      explanation: 'No critique items were raised in this run.',
    };
  }
  if (stats.driftCount > 0) {
    return {
      cheer: 'Run complete · with some loose ends',
      glyph: 'compare',
      glyphColor: COLORS.warn,
      explanation: `${Math.round(stats.resolveRatio * 100)}% of critique items resolved · ${stats.driftCount} drifted`,
    };
  }
  if (stats.verdict === 'Mostly positive') {
    return {
      cheer: 'Run complete · nice work',
      glyph: 'shimmer',
      glyphColor: COLORS.ok,
      explanation: `${Math.round(stats.resolveRatio * 100)}% of critique items resolved`,
    };
  }
  if (stats.verdict === 'Mostly negative') {
    return {
      cheer: 'Run complete · plenty to chew on',
      glyph: 'alert-circle',
      glyphColor: COLORS.warn,
      explanation: `${Math.round(stats.resolveRatio * 100)}% of critique items resolved`,
    };
  }
  return {
    cheer: 'Run complete',
    glyph: 'compare',
    glyphColor: COLORS.info,
    explanation: `${Math.round(stats.resolveRatio * 100)}% of critique items resolved`,
  };
}

// Spec 0175 §2.6 — small, dependency-free confetti burst. ~600 ms,
// compositor-only transforms, respects prefers-reduced-motion (skipped
// in caller). Returns a cleanup function.
function _fireConfetti(originRect) {
  if (typeof document === 'undefined') return () => {};
  const N = 80;
  const palette = ['var(--p-sage)', 'var(--p-sable)', 'var(--md-surface)'];
  const container = document.createElement('div');
  container.style.cssText = 'position:fixed;left:0;top:0;width:0;height:0;pointer-events:none;z-index:9999;';
  document.body.appendChild(container);
  const cx = originRect ? (originRect.left + originRect.width / 2) : (window.innerWidth / 2);
  const cy = originRect ? (originRect.top + originRect.height / 2) : (window.innerHeight / 3);
  for (let i = 0; i < N; i++) {
    const piece = document.createElement('span');
    const angle = (Math.PI * 2 * i) / N + Math.random() * 0.2;
    const dist = 60 + Math.random() * 140;
    const dx = Math.cos(angle) * dist;
    const dy = Math.sin(angle) * dist + 40; // bias slightly downward
    const sz = 5 + Math.random() * 5;
    const c = palette[i % palette.length];
    piece.style.cssText = `position:absolute;left:${cx}px;top:${cy}px;width:${sz}px;height:${sz}px;background:${c};border-radius:50%;transition:transform 600ms cubic-bezier(.2,.7,.2,1), opacity 600ms ease-out;opacity:1;will-change:transform,opacity;`;
    container.appendChild(piece);
    // Force layout, then animate.
    requestAnimationFrame(() => {
      piece.style.transform = `translate(${dx}px, ${dy}px) rotate(${Math.random() * 360}deg)`;
      piece.style.opacity = '0';
    });
  }
  const timer = window.setTimeout(() => {
    if (container.parentNode) container.parentNode.removeChild(container);
  }, 750);
  return () => {
    window.clearTimeout(timer);
    if (container.parentNode) container.parentNode.removeChild(container);
  };
}

// Spec 0175 §2.7 — single tile inside the headline stat grid. Uses the
// M3 --md-surface-container-high chrome that spec 0168 §2.1 locked in
// for the .item-card primitive.
function StatTile({ icon, label, value, hint }) {
  return (
    <div className="summary-stat-tile" style={{
      position: 'relative',
      padding: '14px 16px',
      background: 'var(--md-surface-container-high)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      minHeight: 78,
      display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 2,
    }}>
      {icon && (
        <span aria-hidden="true" style={{
          position: 'absolute', top: 10, right: 10,
          opacity: 0.6, color: 'var(--md-on-surface-variant)',
          display: 'inline-flex',
        }}>
          <Mdi name={icon} size={16} />
        </span>
      )}
      <div className="mono num" style={{
        fontSize: 22, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface)',
        fontVariantNumeric: 'tabular-nums', lineHeight: 1.1,
      }}>{value}</div>
      <div className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-muted)',
        letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>{label}</div>
      {hint && (
        <div className="mono" style={{
          fontSize: 11, color: 'var(--md-on-surface-faint)',
          fontVariantNumeric: 'tabular-nums', marginTop: 2,
        }}>{hint}</div>
      )}
    </div>
  );
}

// Spec 0175 §2.1 — head-to-head per-agent card. Provider stripe via the
// 2 px --p-sable/--p-sage left border (same pattern spec 0168 §2.1
// introduced for `.item-card`).
function AgentSummaryCard({ agent, stats }) {
  const isClaude = agent === 'claude';
  const meta = AGENT_META[isClaude ? 'claude' : 'gpt'];
  const tokens = isClaude ? stats.cTok : stats.gTok;
  const cost   = isClaude ? stats.cCost : stats.gCost;
  const tokenShare = stats.totalTokens > 0 ? tokens / stats.totalTokens : 0;
  const raisedTotal = isClaude ? stats.claudeRaisedTotal : stats.gptRaisedTotal;
  const solvedTotal = isClaude ? stats.claudeSolvedTotal : stats.gptSolvedTotal;
  const stripeColor = isClaude ? 'var(--p-sable)' : 'var(--p-sage)';
  return (
    <div className="summary-agent-card" style={{
      position: 'relative',
      padding: '14px 16px',
      background: 'var(--md-surface-container-high)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      borderLeft: `2px solid ${stripeColor}`,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <AgentIcon agent={agent} size={20} variant="ghost" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          <span style={{ fontSize: 13, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface)' }}>{meta.name}</span>
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{meta.model}</span>
        </div>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px' }}>
        <SmallStat label="tokens" value={fmt.tokens(tokens)} color="var(--md-on-surface)" />
        <SmallStat label="cost" value={fmt.costShort(cost)} color="var(--md-on-surface)" />
        <SmallStat label="raised" value={String(raisedTotal)} color={COLORS.warn} />
        <SmallStat label="solved" value={String(solvedTotal)} color={COLORS.ok} />
      </div>
      <div style={{
        height: 4, borderRadius: 2,
        background: 'var(--md-surface-container)',
        overflow: 'hidden',
      }} aria-hidden="true">
        <div style={{
          width: `${Math.round(tokenShare * 100)}%`,
          height: '100%', background: stripeColor,
          transition: 'width var(--md-dur-short-3, 150ms) var(--md-easing-standard, ease)',
        }} />
      </div>
    </div>
  );
}

// Spec 0175 §2.3 — Critique outcomes breakdown. Four expandable rows
// (claude raised / claude solved / gpt raised / gpt solved) with kind
// sub-rows. Per-row state via React.useState; per-kind sub-row colors
// from _KIND_DOT.
function CritiqueBreakdownRow({ agent, side, count, breakdown }) {
  const [open, setOpen] = React.useState(false);
  const isRaised = side === 'raised';
  const meta = AGENT_META[agent === 'claude' ? 'claude' : 'gpt'];
  const actionGlyph = isRaised ? 'arrow-up' : 'check';
  const actionColor = isRaised ? COLORS.warn : COLORS.ok;
  const actionLabel = isRaised ? 'critique raised' : 'critique solved';
  const kindsForSide = isRaised
    ? ['question', 'disagreement', 'issue', 'comment']
    : ['question', 'disagreement', 'issue'];
  return (
    <div style={{
      borderTop: '1px solid var(--md-outline-hair)',
    }}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          width: '100%', padding: '10px 12px',
          background: 'transparent', border: 'none', cursor: 'pointer',
          textAlign: 'left',
          color: 'var(--md-on-surface)',
        }}
      >
        <Mdi
          name="chevron-right"
          size={14}
          style={{
            transition: 'transform var(--md-dur-short-3, 150ms) var(--md-easing-standard, ease)',
            transform: open ? 'rotate(90deg)' : 'rotate(0)',
            color: 'var(--md-on-surface-muted)',
          }}
        />
        <AgentIcon agent={agent} size={16} variant="ghost" />
        <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)' }}>{meta.name}</span>
        <Dot color={actionColor} size={6} />
        <Mdi name={actionGlyph} size={12} color={actionColor} />
        <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)' }}>{actionLabel}</span>
        <span style={{ flex: 1 }} />
        <span className="mono num" style={{
          fontSize: 15, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface)',
          fontVariantNumeric: 'tabular-nums',
        }}>{count}</span>
      </button>
      {open && (
        <div style={{
          padding: '4px 12px 12px 38px',
          display: 'flex', flexDirection: 'column', gap: 4,
          fontFamily: 'var(--md-font-data)', fontSize: 11.5,
          color: 'var(--md-on-surface-variant)',
        }}>
          {kindsForSide.map((kind) => (
            <div key={kind} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Dot color={_KIND_DOT[kind]} size={6} />
              <span style={{ flex: 1 }}>{KIND_PLURAL[kind] || kind}</span>
              <span className="mono num" style={{
                color: (breakdown[kind] || 0) > 0 ? 'var(--md-on-surface)' : 'var(--md-on-surface-faint)',
                fontVariantNumeric: 'tabular-nums',
              }}>{breakdown[kind] || 0}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CritiqueBreakdown({ stats }) {
  return (
    <section style={{
      background: 'var(--md-surface-container-high)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      overflow: 'hidden',
    }}>
      <header style={{
        display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap',
        padding: '12px 14px',
      }}>
        <Mdi name="list" size={14} color="var(--md-on-surface-muted)" />
        <span className="mono" style={{
          fontSize: 11, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface-muted)',
          letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>Critique outcomes</span>
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 11.5, color: 'var(--md-on-surface-faint)' }}>
          <span style={{ color: 'var(--md-on-surface)' }}>{stats.totalRaised}</span>{' raised · '}
          <span style={{ color: COLORS.ok }}>{stats.claudeSolvedTotal + stats.gptSolvedTotal}</span>{' solved · '}
          <span
            style={{ color: COLORS.info }}
            title="Disagreements both agents shifted on — neither yielded."
          >{stats.mutualAligned}</span>{' aligned'}
        </span>
      </header>
      <CritiqueBreakdownRow agent="claude" side="raised" count={stats.claudeRaisedTotal} breakdown={stats.raised.claude} />
      <CritiqueBreakdownRow agent="claude" side="solved" count={stats.claudeSolvedTotal} breakdown={stats.solved.claude} />
      <CritiqueBreakdownRow agent="gpt"    side="raised" count={stats.gptRaisedTotal}    breakdown={stats.raised.gpt} />
      <CritiqueBreakdownRow agent="gpt"    side="solved" count={stats.gptSolvedTotal}    breakdown={stats.solved.gpt} />
    </section>
  );
}

function CritiqueSummaryView({ run, questions, disagreements }) {
  const issues = Array.isArray(run?.issues) ? run.issues : [];
  const comments = Array.isArray(run?.comments) ? run.comments : [];
  const ctx = React.useContext(SearchIndexContext);

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
            fontSize: 12, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface-muted)',
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
          fontSize: 12, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface-muted)',
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

  // Spec 0175 §2.2 — all derived stats in one memo.
  const stats = React.useMemo(
    () => _computeSummaryStats(run, questions, disagreements, issues, comments),
    [run, questions, disagreements, issues, comments],
  );
  const verdictTone = _pickVerdictTone(stats.verdict, run?.status);
  const heroVariant = _pickHeroVariant(run, stats);
  const webStats = React.useMemo(() => _computeWebSearchStats(ctx?.summary), [ctx?.summary]);

  // Spec 0175 §2.7 — story copy. The verdict line that used to be the
  // first sentence is now surfaced by the hero band, so this memo keeps
  // only the qualitative + drift sentences (spec 0072 D7-D10 shape).
  const summaryCopy = React.useMemo(() => {
    const totalQ = questions.length;
    const resolvedQ = questions.filter((q) => q.status !== 'open').length;
    const totalD = disagreements.length;
    const resolvedD = disagreements.filter((d) => (d.status || '').startsWith('resolved')).length;
    const totalI = issues.length;
    const resolvedI = issues.filter((i) => i.status !== 'open').length;
    const totalC = comments.length;

    const qualParts = [];
    if (totalQ > 0) qualParts.push(`${totalQ} question${totalQ !== 1 ? 's' : ''} raised (${resolvedQ} resolved)`);
    if (totalD > 0) qualParts.push(`${totalD} disagreement${totalD !== 1 ? 's' : ''} raised (${resolvedD} resolved)`);
    if (totalI > 0) qualParts.push(`${totalI} issue${totalI !== 1 ? 's' : ''} flagged (${resolvedI} resolved)`);
    if (totalC > 0) qualParts.push(`${totalC} comment${totalC !== 1 ? 's' : ''} raised`);
    const sentence2 = qualParts.length > 0 ? qualParts.join(', ') + '.' : '';
    const sentence3 = stats.driftCount > 0
      ? `${stats.driftCount} item${stats.driftCount !== 1 ? 's' : ''} drifted without response for multiple rounds.`
      : '';
    return [sentence2, sentence3].filter(Boolean).join(' ');
  }, [questions, disagreements, issues, comments, stats.driftCount]);

  // Spec 0175 §2.8 — HEAD probe for the final-document download.
  const [finalDocAvailable, setFinalDocAvailable] = React.useState(true);
  React.useEffect(() => {
    let cancelled = false;
    if (!run?.id) { setFinalDocAvailable(false); return; }
    fetch(`/api/runs/${encodeURIComponent(run.id)}/files/final.md`, { method: 'HEAD' })
      .then((r) => { if (!cancelled) setFinalDocAvailable(r.ok); })
      .catch(() => { if (!cancelled) setFinalDocAvailable(false); });
    return () => { cancelled = true; };
  }, [run?.id]);

  const [showTables, setShowTables] = React.useState(false);

  // Spec 0175 §2.8 — copy summary as plain text.
  const [copied, setCopied] = React.useState(false);
  const handleCopy = React.useCallback(() => {
    const plain = String(summaryCopy || '').replace(/\*\*/g, '');
    const verdictLine = heroVariant.cheer + ' — ' + verdictTone.label + '. ';
    const out = (verdictLine + plain).trim();
    if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(out).then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1400);
      }).catch(() => { /* clipboard denied — ignore */ });
    }
  }, [summaryCopy, heroVariant.cheer, verdictTone.label]);

  // Spec 0175 §2.6 — confetti, gated by verdict + per-run localStorage flag.
  const verdictGlyphRef = React.useRef(null);
  React.useEffect(() => {
    if (verdictTone.key !== 'positive') return;
    if (!run?.id) return;
    const key = 'dr-confetti-' + run.id;
    if (typeof window === 'undefined' || !window.localStorage) return;
    if (window.localStorage.getItem(key) === '1') return;
    window.localStorage.setItem(key, '1');
    const mq = typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    if (mq && mq.matches) return;
    const rect = verdictGlyphRef.current && verdictGlyphRef.current.getBoundingClientRect
      ? verdictGlyphRef.current.getBoundingClientRect() : null;
    const cleanup = _fireConfetti(rect);
    return cleanup;
  }, [verdictTone.key, run?.id]);

  // Spec 0175 §2.4 — deadlocked runs promote the highest-leverage thread.
  const showLeveragePre  = run?.status === 'deadlocked' && highestLeverageThread;
  const showLeveragePost = run?.status !== 'deadlocked' && highestLeverageThread;

  const heroBg = (verdictTone.key === 'inconclusive')
    ? 'var(--md-surface-container-low)'
    : verdictTone.color + '1A';
  const heroBorder = (verdictTone.key === 'inconclusive')
    ? 'var(--md-outline-hair)'
    : verdictTone.color + '55';

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--md-surface)' }}>
      <div style={{ maxWidth: 980, margin: '0 auto', padding: '16px 24px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* HERO BAND — spec 0175 §2.4 */}
        <section style={{
          background: heroBg,
          border: `1px solid ${heroBorder}`,
          borderRadius: 'var(--md-shape-md)',
          padding: '18px 20px',
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Mdi name="check-bold" size={12} color={verdictTone.color} />
            <span style={{ fontSize: 12.5, color: verdictTone.color, fontWeight: 'var(--md-w-semi)' }}>{heroVariant.cheer}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <span ref={verdictGlyphRef} aria-hidden="true" style={{ display: 'inline-flex' }}>
              <Mdi name={heroVariant.glyph} size={32} color={heroVariant.glyphColor} />
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 22, fontWeight: 'var(--md-w-semi)', color: verdictTone.color, lineHeight: 1.1 }}>{verdictTone.label}</span>
              <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-variant)' }}>{heroVariant.explanation}</span>
              {heroVariant.code && (
                <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)', marginTop: 2 }}>code: {heroVariant.code}</span>
              )}
            </div>
          </div>
          {run?.topic && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, maxWidth: 760, marginTop: 2 }}>
              <span aria-hidden="true" style={{ opacity: 0.55, color: 'var(--md-on-surface-muted)', display: 'inline-flex', paddingTop: 2 }}>
                <Mdi name="format-quote" size={14} />
              </span>
              <span style={{
                fontFamily: 'var(--md-font-brand)', fontStyle: 'italic',
                fontSize: 14, lineHeight: 1.45, color: 'var(--md-on-surface-variant)',
              }}>{run.topic}</span>
            </div>
          )}
        </section>

        {/* HIGHEST-LEVERAGE — promoted on deadlock */}
        {showLeveragePre && (
          <section>
            <div style={{
              fontSize: 11, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface-muted)',
              letterSpacing: '0.06em', textTransform: 'uppercase',
              marginBottom: 8,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <Mdi name="alert-circle" size={14} color={COLORS.warn} />
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
          </section>
        )}

        {/* STAT GRID — spec 0175 §2.7 */}
        <section style={{
          display: 'grid', gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        }}>
          <StatTile
            icon="lightning"
            label="tokens burned"
            value={fmt.tokens(stats.totalTokens)}
            hint={stats.totalTokens > 0 ? `${fmt.tokens(stats.cTok)} + ${fmt.tokens(stats.gTok)}` : null}
          />
          <StatTile
            icon="currency-usd"
            label="spent"
            value={fmt.costShort(stats.totalCost)}
            hint={stats.totalCost > 0 ? `${fmt.costShort(stats.cCost)} · ${fmt.costShort(stats.gCost)}` : null}
          />
          <StatTile
            icon="timer"
            label="elapsed"
            value={stats.elapsedTotal > 0 ? fmt.duration(stats.elapsedTotal) : '—'}
          />
          <StatTile
            icon="history"
            label="rounds"
            value={stats.roundCount > 0 ? `R${stats.roundCount}` : '—'}
            hint={stats.totalItems > 0 ? `${stats.totalItems} items debated` : null}
          />
          <StatTile
            icon="magnify"
            label="web searches"
            value={webStats.hasAny ? String(webStats.queries) : '—'}
            hint={webStats.hasAny ? `${webStats.consulted} URLs retrieved` : null}
          />
        </section>

        {/* STORY BLOCK */}
        {summaryCopy && (
          <section style={{
            display: 'flex', gap: 10, alignItems: 'flex-start',
            padding: '12px 14px',
            background: 'var(--md-surface-container-low)',
            border: '1px solid var(--md-outline-hair)',
            borderLeft: `3px solid ${verdictTone.color}`,
            borderRadius: 'var(--md-shape-sm)',
          }}>
            <span aria-hidden="true" style={{ display: 'inline-flex', color: verdictTone.color, opacity: 0.7, paddingTop: 2 }}>
              <Mdi name="format-quote" size={20} />
            </span>
            <div style={{ flex: 1, fontSize: 13, lineHeight: 1.6, color: 'var(--md-on-surface-variant)' }}>
              <Markdown text={summaryCopy} />
            </div>
          </section>
        )}

        {/* HEAD-TO-HEAD AGENT CARDS */}
        <section style={{
          display: 'grid', gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        }}>
          <AgentSummaryCard agent="claude" stats={stats} />
          <AgentSummaryCard agent="gpt"    stats={stats} />
        </section>

        {/* CRITIQUE OUTCOMES */}
        {stats.totalRaised > 0 && (
          <CritiqueBreakdown stats={stats} />
        )}

        {/* HIGHEST-LEVERAGE — default position */}
        {showLeveragePost && (
          <section>
            <div style={{
              fontSize: 11, fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface-muted)',
              letterSpacing: '0.06em', textTransform: 'uppercase',
              marginBottom: 8,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <Mdi name="alert-circle" size={14} color={COLORS.warn} />
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
          </section>
        )}

        {/* PER-ROUND DRILL-DOWN — legacy tables, collapsed by default */}
        <section>
          <button
            type="button"
            aria-expanded={showTables}
            onClick={() => setShowTables((v) => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              width: '100%', padding: '10px 12px',
              background: 'var(--md-surface-container-low)',
              border: '1px solid var(--md-outline-hair)',
              borderRadius: 'var(--md-shape-sm)',
              cursor: 'pointer',
              color: 'var(--md-on-surface)',
            }}
          >
            <Mdi
              name="chevron-right"
              size={14}
              style={{
                transition: 'transform var(--md-dur-short-3, 150ms) var(--md-easing-standard, ease)',
                transform: showTables ? 'rotate(90deg)' : 'rotate(0)',
                color: 'var(--md-on-surface-muted)',
              }}
            />
            <Mdi name="chart-line" size={14} color="var(--md-on-surface-muted)" />
            <span style={{ fontSize: 12.5, fontWeight: 'var(--md-w-semi)' }}>Per-round breakdown</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>raised / resolved by round, per model</span>
          </button>
          {showTables && (
            <div style={{ padding: '14px 4px 0' }}>
              {renderPhase('Phase 2 — Negotiate', 2)}
              {renderPhase('Phase 4 — Review', 4)}
            </div>
          )}
        </section>

        {/* FOOTER */}
        <footer style={{
          display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center',
          paddingTop: 14,
          borderTop: '1px solid var(--md-outline-hair)',
        }}>
          <a
            href={finalDocAvailable ? `/api/runs/${encodeURIComponent(run?.id || '')}/files/final.md` : undefined}
            download={finalDocAvailable ? 'final.md' : undefined}
            aria-disabled={!finalDocAvailable}
            title={finalDocAvailable ? undefined : 'No final document was produced for this run.'}
            className="md-btn md-btn--filled"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '0 18px', height: 36,
              // Spec 0175 §3.3 — verdict-tone base hexes (`#6fb380` etc.)
              // fail AA at 4.5:1 against white. Darken via `color-mix` to
              // ~70 % verdict + 30 % black, which yields ~5:1+ in both
              // themes (the bg is the same hex in dark + light).
              background: verdictTone.key === 'inconclusive'
                ? 'var(--md-surface-container)'
                : `color-mix(in srgb, ${verdictTone.color} 70%, #000000)`,
              color: verdictTone.key === 'inconclusive' ? 'var(--md-on-surface)' : '#ffffff',
              border: 'none',
              borderRadius: 'var(--md-shape-full)',
              fontWeight: 'var(--md-w-semi)', fontSize: 13,
              cursor: finalDocAvailable ? 'pointer' : 'not-allowed',
              opacity: finalDocAvailable ? 1 : 0.5,
              pointerEvents: finalDocAvailable ? 'auto' : 'none',
              textDecoration: 'none',
            }}
          >
            <Mdi name="download" size={14} color="currentColor" />
            Download final document (.md)
          </a>
          <button
            type="button"
            onClick={handleCopy}
            className="md-btn md-btn--outlined"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '0 16px', height: 36,
              background: 'transparent',
              color: 'var(--md-on-surface)',
              border: '1px solid var(--md-outline)',
              borderRadius: 'var(--md-shape-full)',
              fontWeight: 'var(--md-w-semi)', fontSize: 13,
              cursor: 'pointer',
            }}
          >
            <Mdi name={copied ? 'check' : 'content-copy'} size={14} color="currentColor" />
            {copied ? 'Copied!' : 'Copy summary'}
          </button>
          <span style={{ flex: 1 }} />
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>
            run {run?.id || '—'}
          </span>
        </footer>
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
        <span style={{ color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-semi)' }}>{KIND_PLURAL[kind] || kind}</span>
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
  fontWeight: 'var(--md-w-semi)',
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
      <span className="mono num" style={{ fontSize: 13, color, fontWeight: 'var(--md-w-semi)' }}>{value}</span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{label}</span>
    </span>
  );
}

// Spec 0149 §5.12 (D23) — `PhaseContent` function removed (was at line
// ~7672 pre-edit). Zero external callers as of post-0148; the live
// critique surface is rendered by `CritiquePhaseContent` instead.

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
      fontWeight: 'var(--md-w-medium)',
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
            <span style={{ fontSize: 11.5, color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-medium)' }}>{meta.name}</span>
          )}
          {step.agent === 'both' && (
            <span style={{ fontSize: 11.5, color: 'var(--md-on-surface-variant)', fontWeight: 'var(--md-w-medium)' }}>Both agents</span>
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
        {/* Spec 0070 D4: blocking-item callout banner removed (user: "completely useless").
           Same info available in critique pane DRIFT/OPEN section headers.
           Spec 0133: <TimelineAgentBar /> removed; per-agent pills now ride inside
           the Timeline pane headers (Claude in .tl__head, GPT in .tl__tabs). */}
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
