// live-data.jsx — replaces the prototype's data.jsx mock constants with live
// hooks against the spec 0010 API (/api/runs, /api/runs/:id, SSE stream,
// /api/runs/:id/files/...).
//
// Components consume:
//   - useLiveRun(runId)       → { run, connected, error }
//   - useRunList()            → { rows, connected }
//   - useFileBody(filePath)   → string body for an artifact (lazy fetched)
//   - PHASES                  → static phase definitions
//   - RunContext              → wraps RunDetail so deep components know the runId
//
// Spec 0011. Single-user, localhost. No retry backoff beyond what
// EventSource gives us for free.

// ─────────────────── Static constants ───────────────────

const PHASES = [
  { id: 0, key: 'preflight', label: 'Preflight',     short: 'P0' },
  { id: 1, key: 'parallel',  label: 'Parallel draft', short: 'P1' },
  { id: 2, key: 'negotiate', label: 'Negotiate plan', short: 'P2' },
  { id: 3, key: 'draft',     label: 'Converged draft', short: 'P3' },
  { id: 4, key: 'review',    label: 'Cross-review',   short: 'P4' },
  { id: 5, key: 'done',      label: 'Done',           short: '✓'  },
];

// Placeholder constants kept for components that still reference them.
// They're empty in live mode; the live data flow uses the run + filePath model.
const TOPIC = '';
const INPUT_BRIEF = '';
const TURN_HISTORY = [];

// ─────────────────── Context for nested components ───────────────────

const RunContext = React.createContext({ runId: null });

// Module-level "active run id" for components that can't easily plumb
// context (e.g. shared.jsx primitives). RunContext is the preferred path;
// this is a fallback only.
let __activeRunId = null;
function setActiveRunId(id) { __activeRunId = id; }
function getActiveRunId() { return __activeRunId; }

// ─────────────────── useLiveRun ───────────────────

// REST fetch + repeated polling at DETAIL_POLL_MS. Snapshot replies overwrite
// the run wholesale (same shape as the spec-0010 SSE frames). Auth tokens
// (when hosted-mode is on) are injected by `authedFetch`. SSE is gone in
// favour of polling: EventSource can't send Authorization headers and the
// hosted polled-SSE adapter (spec 0020) makes this is a clean win.
const DETAIL_POLL_MS = 5000;
const CONNECTED_WINDOW_MS = 7000;

// Spec 0041 D6 — load-time resilience.
//
// Pre-spec: a single transient 502 on the first poll (Fly machine
// wake, Supabase materialise-temp-dir for a 141-event run) flipped
// `error` immediately and the DetailScreen rendered a full-page
// "Could not load run" until the next poll 5s later succeeded. The
// user saw the error screen flash and disappear for no obvious
// reason.
//
// Now: tolerate up to 2 consecutive failures before surfacing
// `error`. Once we have run data, never overwrite it with an error
// screen — a transient failure keeps showing the stale data while
// the connected indicator dims. First-load retries are paced
// faster (1s, 2s, 4s) before settling into 5s steady-state polling.
const INITIAL_RETRY_DELAYS_MS = [1000, 2000, 4000];
const ERROR_VISIBILITY_THRESHOLD = 3;

function useLiveRun(runId) {
  const [run, setRun] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [lastOk, setLastOk] = React.useState(0);
  const runRef = React.useRef(null);
  const consecErrorsRef = React.useRef(0);

  React.useEffect(() => {
    if (!runId) return;
    setRun(null);
    setError(null);
    setLastOk(0);
    runRef.current = null;
    consecErrorsRef.current = 0;

    let cancelled = false;
    let attempt = 0;
    let timer = null;

    const tick = () => {
      authedFetch(`/api/runs/${encodeURIComponent(runId)}`)
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (cancelled) return;
          runRef.current = data;
          setRun(data);
          setLastOk(Date.now());
          setError(null);
          consecErrorsRef.current = 0;
        })
        .catch(e => {
          if (cancelled) return;
          consecErrorsRef.current += 1;
          // Never overwrite a successful run with an error screen —
          // the connected indicator dims naturally when polls fail.
          // The error screen only fires on the initial-load sequence,
          // and only after ERROR_VISIBILITY_THRESHOLD consecutive
          // failures (so a single transient 502 doesn't flash).
          if (runRef.current == null
              && consecErrorsRef.current >= ERROR_VISIBILITY_THRESHOLD) {
            setError(String(e));
          }
        });
    };

    const schedule = () => {
      tick();
      attempt += 1;
      const next = attempt - 1 < INITIAL_RETRY_DELAYS_MS.length
        ? INITIAL_RETRY_DELAYS_MS[attempt - 1]
        : DETAIL_POLL_MS;
      timer = setTimeout(schedule, next);
    };
    timer = setTimeout(schedule, 0);
    return () => {
      cancelled = true;
      if (timer != null) clearTimeout(timer);
    };
  }, [runId]);

  const [connected, setConnected] = React.useState(false);
  React.useEffect(() => {
    const id = setInterval(() => {
      setConnected(Date.now() - lastOk < CONNECTED_WINDOW_MS);
    }, 500);
    return () => clearInterval(id);
  }, [lastOk]);

  return { run, connected, error };
}

// ─────────────────── useRunList ───────────────────

// Polls /api/runs every 3 seconds. The endpoint is cheap (one stat per
// session dir). No global SSE in v1 per spec 0010.
function useRunList() {
  const [rows, setRows] = React.useState([]);
  const [lastOk, setLastOk] = React.useState(0);
  // Spec 0083 — stays true until we get one SUCCESSFUL response. A
  // transient network blip must not flip us into the "confirmed empty"
  // state where the UI renders "No runs". Promoting on success only
  // means stale data keeps showing the list, and a cold mount keeps
  // showing the loading visual until the server actually answers.
  const [hasLoaded, setHasLoaded] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    const tick = () => {
      authedFetch('/api/runs')
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (cancelled) return;
          setRows(data);
          setLastOk(Date.now());
          setHasLoaded(true);
        })
        .catch(() => { /* keep waiting; don't promote to "confirmed empty" on error */ });
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // Indicator: "connected" when last successful fetch was < 5s ago.
  const [connected, setConnected] = React.useState(false);
  React.useEffect(() => {
    const id = setInterval(() => {
      setConnected(Date.now() - lastOk < 5000);
    }, 500);
    return () => clearInterval(id);
  }, [lastOk]);

  return { rows, connected, loading: !hasLoaded };
}

// ─────────────────── useAttachments ───────────────────

// Spec 0025. Lazy fetch of the attachments index for the active run.
// Returns `{ attachments, loading }`. Empty list when the run has none
// — the preflight modal renders an empty-state.
function useAttachments(runId) {
  const [attachments, setAttachments] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  React.useEffect(() => {
    if (!runId) { setAttachments([]); return; }
    let cancelled = false;
    setLoading(true);
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/attachments`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setAttachments(Array.isArray(data?.attachments) ? data.attachments : []);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setAttachments([]);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [runId]);
  return { attachments, loading };
}

function attachmentBlobUrl(runId, relPath) {
  if (!runId || !relPath) return null;
  return `/api/runs/${encodeURIComponent(runId)}/attachment-blobs/${relPath
    .split('/')
    .map(encodeURIComponent)
    .join('/')}`;
}

// ─────────────────── useFileBody ───────────────────

// Lazy fetch of a markdown file body. The runId is taken from the active
// RunContext; if absent, falls back to the module-level setActiveRunId.
// Returns the body string (empty until the fetch resolves).
function useFileBody(filePath) {
  const ctx = React.useContext(RunContext);
  const runId = ctx?.runId || getActiveRunId();
  const [body, setBody] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!filePath || !runId) { setBody(''); return; }
    let cancelled = false;
    setLoading(true);
    setBody('');
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/files/${filePath}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then(text => {
        if (cancelled) return;
        setBody(text);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setBody(`— body unavailable —`);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [filePath, runId]);

  return { body, loading };
}

// ─────────────────── Spec 0035 — useAppMeta ─────────────────────────────────
//
// Lazy-fetch /api/health on app mount; cache the result on
// ``window.__appMeta`` so a navigation between runs doesn't re-request.
// Returns ``{ version, ... } | null``. The version chip in the chrome
// bar reads this; first-paint shows nothing until the fetch lands (one
// HTTP round-trip), then renders.
function useAppMeta() {
  const [meta, setMeta] = React.useState(
    typeof window !== 'undefined' ? (window.__appMeta || null) : null
  );
  React.useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.__appMeta) {
      setMeta(window.__appMeta);
      return;
    }
    let cancelled = false;
    authedFetch('/api/health')
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (cancelled || !d) return;
        window.__appMeta = d;
        setMeta(d);
      })
      .catch(() => { /* silent — chip just doesn't render */ });
    return () => { cancelled = true; };
  }, []);
  return meta;
}

// ─────────────────── Spec 0033 — useInputBundle ─────────────────────────────
//
// Lazy-fetch a per-turn input bundle from the server. ``turnKey`` is one of
// the snake-case keys the aggregator stamps (``phase2_round3_claude``) or
// the special ``input`` key for the synthesised Phase 0 shared bundle.
// Returns ``{ bundle, loading, error }``.
function useInputBundle(turnKey) {
  const ctx = React.useContext(RunContext);
  const runId = ctx?.runId || getActiveRunId();
  const [bundle, setBundle] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!turnKey || !runId) { setBundle(null); return; }
    let cancelled = false;
    setLoading(true);
    setBundle(null);
    setError(null);
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/inputs/${encodeURIComponent(turnKey)}`)
      .then(r => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        setBundle(data);
        setLoading(false);
      })
      .catch(e => {
        if (cancelled) return;
        setError(String(e));
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [turnKey, runId]);

  return { bundle, loading, error };
}

// ─────────────────── Spec 0038 — useSearchBundle / useSearchIndex ───────────
//
// Lazy-fetch a per-turn web-search audit bundle. 404 is the legitimate
// "no audit recorded" case — bundle stays null, loading flips false,
// no error raised. Mirrors ``useInputBundle``.
function useSearchBundle(turnKey) {
  const ctx = React.useContext(RunContext);
  const runId = ctx?.runId || getActiveRunId();
  const [bundle, setBundle] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!turnKey || !runId) { setBundle(null); return; }
    let cancelled = false;
    setLoading(true);
    setBundle(null);
    setError(null);
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/searches/${encodeURIComponent(turnKey)}`)
      .then(r => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        setBundle(data);
        setLoading(false);
      })
      .catch(e => {
        if (cancelled) return;
        setError(String(e));
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [turnKey, runId]);

  return { bundle, loading, error };
}

// Lazy-fetch the per-run search-audit index + summary. Returns
// ``{ keys: Set<string> | null, summary: Map<string,{queries,consulted,hasWarning}> | null }``.
// Both stay null while loading. The chip + gist + run-header summary
// share this one fetch — no per-card network calls.
function useSearchIndex(runId) {
  const [state, setState] = React.useState({ keys: null, summary: null });

  React.useEffect(() => {
    if (!runId) { setState({ keys: null, summary: null }); return; }
    let cancelled = false;
    authedFetch(`/api/runs/${encodeURIComponent(runId)}/searches/index?include=summary`)
      .then(r => r.ok ? r.json() : { keys: [], summary: {} })
      .then(data => {
        if (cancelled) return;
        const keys = new Set(Array.isArray(data?.keys) ? data.keys : []);
        const summary = new Map();
        const rawSummary = data?.summary || {};
        for (const k of Object.keys(rawSummary)) {
          const v = rawSummary[k] || {};
          summary.set(k, {
            queries: Number(v.queries) || 0,
            consulted: Number(v.consulted) || 0,
            hasWarning: !!v.has_warning,
          });
        }
        setState({ keys, summary });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ keys: new Set(), summary: new Map() });
      });
    return () => { cancelled = true; };
  }, [runId]);

  return state;
}

// ─────────────────── Topic formatting ───────────────────

// Trim a research-brief H1 down to one readable line. Many briefs are long
// run-on questions; we clamp at the first sentence terminator or at 120
// chars, whichever comes first. Full topic stays available in tooltip
// attributes.
function formatTopic(topic, { maxChars = 120 } = {}) {
  if (!topic) return '';
  const t = String(topic).trim();
  if (!t) return '';
  // Find first sentence terminator (?, ., !) that isn't part of a number.
  const m = t.match(/^[^?.!]*[?.!]/);
  let head = m ? m[0].trim() : t;
  if (head.length > maxChars) {
    head = head.slice(0, maxChars).replace(/\s+\S*$/, '') + '…';
  }
  return head;
}

// ─────────────────── Run-id chrome ───────────────────

// Parse a session-dir name like `20260515-124552-cache-multi-round` into
// {time: '12:45', slug: 'cache-multi-round'} for the two-line id cell.
function splitRunId(id) {
  if (!id) return { time: '', slug: '' };
  const m = String(id).match(/^(\d{8})-(\d{2})(\d{2})\d{2}-(.+)$/);
  if (!m) return { time: '', slug: String(id) };
  return { time: `${m[2]}:${m[3]}`, slug: m[4] };
}

// ─────────────────── Filename conventions ───────────────────

// The aggregator + on-disk layout use {agent} = {claude, openai}. The UI
// vocabulary uses {claude, gpt}. Translate for filename building.
const UI_TO_BACKEND_AGENT = { claude: 'claude', gpt: 'openai' };

function fileForRound(phase, round, uiAgent) {
  const be = UI_TO_BACKEND_AGENT[uiAgent] || uiAgent;
  const rr = String(round).padStart(2, '0');
  return `phase${phase}/round-${rr}-${be}.md`;
}

function fileForPhase1Draft(uiAgent) {
  const be = UI_TO_BACKEND_AGENT[uiAgent] || uiAgent;
  return `phase1/draft-${be}.md`;
}

// ─────────────────── Live timeline builder ───────────────────

// Produces the ordered list of items the run-detail Timeline consumes.
// Each item carries either an inline `body` (live, in-flight turn) or a
// `filePath` (past artifact — body is lazily fetched on expand).
function buildLiveTimeline(run) {
  if (!run) return [];
  const items = [];
  const ph = run.phase;
  const st = run.status;

  // Phase 0: the brief + per-agent preflight critiques (spec 0033).
  //
  // Spec 0033 split the single Phase 0 card into three:
  // - `input` — the shared brief + system prompt (one modal)
  // - `p0-claude` — Claude's brief-critique response (per-agent modal)
  // - `p0-gpt` — GPT's brief-critique response (per-agent modal)
  //
  // The per-agent critique cards only render once both responses are on
  // disk (i.e. Phase 0 has completed). While Phase 0 is in-flight the
  // single `input` card stands alone — same behaviour as pre-0033 so
  // there's no flicker mid-preflight.
  items.push({ id: 'phase-0', kind: 'phase-divider', phaseId: 0, duration: run.phaseTimings?.['0'] });
  items.push({
    id: 'input', kind: 'input', filePath: 'brief.md', topic: run.topic,
    turnKey: 'input',
  });
  if (ph >= 1) {
    items.push({
      id: 'p0-claude', kind: 'preflight', agent: 'claude',
      filePath: 'phase0/preflight-claude.md',
      stats: run.phaseStats?.phase0?.claude || null,
      statsPhase: 0,
      summary: run.phaseSummaries?.phase0_claude || '',
      turnKey: 'phase0_claude',
    });
    items.push({
      id: 'p0-gpt', kind: 'preflight', agent: 'gpt',
      filePath: 'phase0/preflight-openai.md',
      stats: run.phaseStats?.phase0?.gpt || null,
      statsPhase: 0,
      summary: run.phaseSummaries?.phase0_gpt || '',
      turnKey: 'phase0_gpt',
    });
  }

  if (ph >= 1) {
    items.push({ id: 'phase-1', kind: 'phase-divider', phaseId: 1, duration: run.phaseTimings?.['1'] });
    if (ph === 1) {
      // Live: bodies come from agents.{agent}.currentTurn.body, which the
      // aggregator populates from the on-disk draft file as soon as it lands.
      items.push({
        id: 'p1-claude-live', kind: 'plan-live', agent: 'claude', live: true,
        status: run.agents?.claude?.status,
        body: run.agents?.claude?.currentTurn?.body || '',
        filePath: fileForPhase1Draft('claude'),
        turnKey: 'phase1_claude',
      });
      items.push({
        id: 'p1-gpt-live', kind: 'plan-live', agent: 'gpt', live: true,
        status: run.agents?.gpt?.status,
        body: run.agents?.gpt?.currentTurn?.body || '',
        filePath: fileForPhase1Draft('gpt'),
        turnKey: 'phase1_gpt',
      });
    } else {
      items.push({ id: 'p1-claude', kind: 'plan', agent: 'claude',
                   filePath: fileForPhase1Draft('claude'), turnKey: 'phase1_claude' });
      items.push({ id: 'p1-gpt',    kind: 'plan', agent: 'gpt',
                   filePath: fileForPhase1Draft('gpt'),    turnKey: 'phase1_gpt' });
    }
  }

  if (ph >= 2) {
    const cur = run.round?.current ?? 0;
    // Phase 2 round count: while ph === 2, `cur` is the current phase's
    // counter (authoritative). Once the run advances, `cur` is overwritten by
    // Phase 4's round, so we derive the count from phaseStats keys instead.
    const p2Rounds = ph === 2 ? cur : Object.keys(run.phaseStats?.phase2 || {}).length;
    items.push({
      id: 'phase-2', kind: 'phase-divider', phaseId: 2,
      duration: run.phaseTimings?.['2'],
      extra: `${p2Rounds} round${p2Rounds === 1 ? '' : 's'}`,
    });
    if (ph === 2 && (st === 'running' || st === 'deadlocked' || st === 'errored')) {
      // For `running`, `cur` is the in-flight round handled by the live branch
      // below. For `deadlocked` / `errored`, `cur` is already on disk and
      // complete, so include it in the static-card loop. (Spec 0017.)
      const completedThrough = st === 'running' ? Math.max(0, cur - 1) : cur;
      for (let r = 1; r <= completedThrough; r++) {
        items.push({ id: `p2-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                     filePath: fileForRound(2, r, 'claude'),
                     turnKey: `phase2_round${r}_claude` });
        items.push({ id: `p2-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                     filePath: fileForRound(2, r, 'gpt'),
                     turnKey: `phase2_round${r}_gpt`    });
      }
      if (cur > 0 && st === 'running') {
        items.push({
          id: `p2-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
          round: cur, index: cur, live: true,
          status: run.agents?.claude?.status,
          body: run.agents?.claude?.currentTurn?.body || '',
          filePath: fileForRound(2, cur, 'claude'),
          turnKey: `phase2_round${cur}_claude`,
        });
        items.push({
          id: `p2-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
          round: cur, index: cur, live: true,
          status: run.agents?.gpt?.status,
          body: run.agents?.gpt?.currentTurn?.body || '',
          filePath: fileForRound(2, cur, 'gpt'),
          turnKey: `phase2_round${cur}_gpt`,
        });
      }
    } else if (ph >= 3 || st === 'completed' || st === 'deadlocked') {
      // Run moved past P2 — enumerate all completed rounds. `run.round.current`
      // has been overwritten by the next phase, so use the per-phase count.
      for (let r = 1; r <= p2Rounds; r++) {
        items.push({ id: `p2-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                     filePath: fileForRound(2, r, 'claude'),
                     turnKey: `phase2_round${r}_claude` });
        items.push({ id: `p2-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                     filePath: fileForRound(2, r, 'gpt'),
                     turnKey: `phase2_round${r}_gpt`    });
      }
    }
  }

  if (ph >= 3 && st !== 'errored' && st !== 'deadlocked') {
    items.push({ id: 'phase-3', kind: 'phase-divider', phaseId: 3, duration: run.phaseTimings?.['3'] });
    if (ph === 3 && run.drafter) {
      items.push({
        id: 'doc-live', kind: 'doc-live', agent: run.drafter, live: true,
        status: run.agents?.[run.drafter]?.status,
        body: run.agents?.[run.drafter]?.currentTurn?.body || '',
        filePath: 'phase3/draft-v1.md',
        turnKey: `phase3_${run.drafter}`,
      });
    } else if (run.drafter) {
      items.push({
        id: 'doc-converged', kind: 'doc', agent: run.drafter,
        summary: `Converged document drafted by ${run.drafter}.`,
        filePath: 'phase3/draft-v1.md',
        turnKey: `phase3_${run.drafter}`,
      });
    }
  }

  if (ph >= 4 && st !== 'errored' && st !== 'deadlocked') {
    const cur = run.round?.current ?? 0;
    // While ph === 4 we trust `cur`; afterwards we'd be reading whatever
    // phase reset it. (At present nothing comes after Phase 4 but we treat
    // the past-phase branch symmetrically with Phase 2 for future-proofing.)
    const p4Rounds = ph === 4 ? cur : Object.keys(run.phaseStats?.phase4 || {}).length;
    items.push({
      id: 'phase-4', kind: 'phase-divider', phaseId: 4,
      duration: run.phaseTimings?.['4'],
      extra: `${p4Rounds} review round${p4Rounds === 1 ? '' : 's'}`,
    });
    if (ph === 4) {
      const completedThrough = Math.max(0, cur - 1);
      for (let r = 1; r <= completedThrough; r++) {
        items.push({ id: `p4-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'claude'),
                     turnKey: `phase4_round${r}_claude` });
        items.push({ id: `p4-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'gpt'),
                     turnKey: `phase4_round${r}_gpt`    });
      }
      if (cur > 0) {
        items.push({
          id: `p4-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
          round: cur, index: `rev-${cur}`, live: true,
          status: run.agents?.claude?.status,
          body: run.agents?.claude?.currentTurn?.body || '',
          filePath: fileForRound(4, cur, 'claude'),
          turnKey: `phase4_round${cur}_claude`,
        });
        items.push({
          id: `p4-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
          round: cur, index: `rev-${cur}`, live: true,
          status: run.agents?.gpt?.status,
          body: run.agents?.gpt?.currentTurn?.body || '',
          filePath: fileForRound(4, cur, 'gpt'),
          turnKey: `phase4_round${cur}_gpt`,
        });
      }
    } else if (ph === 5 || st === 'completed') {
      for (let r = 1; r <= p4Rounds; r++) {
        items.push({ id: `p4-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'claude'),
                     turnKey: `phase4_round${r}_claude` });
        items.push({ id: `p4-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'gpt'),
                     turnKey: `phase4_round${r}_gpt`    });
      }
    }
  }

  if (ph >= 5 || st === 'completed') {
    items.push({ id: 'phase-5', kind: 'phase-divider', phaseId: 5, duration: run.phaseTimings?.['4'] });
    // Spec 0047: historical runs that reached `completed` without a drafter
    // (e.g. orchestrator versions that marked the run complete before Phase 3
    // ran) would otherwise emit `agent: null` here and crash ArtifactHeader
    // downstream. Skip the final artifact entirely when there's no drafter to
    // attribute it to.
    if (run.drafter) {
      items.push({
        id: 'doc-final', kind: 'doc', agent: run.drafter, completed: true,
        summary: 'Final document — emitted.',
        filePath: 'final.md',
      });
    }
  }

  if (st === 'errored' && run.error) items.push({ id: 'error', kind: 'error', error: run.error });
  if (st === 'deadlocked') {
    items.push({
      id: 'deadlock', kind: 'deadlock', round: run.round,
      open: (run.disagreements || []).filter(d => d.status === 'open').length,
    });
  }

  return attachItemStats(items, run);
}

// Walk the built timeline and attach `item.stats` from run.phaseStats so
// ArtifactHeader can render inline chips (spec 0013). Also attaches
// `item.summary` (spec 0025) from run.phaseSummaries for the new
// summary-card collapsed state.
function attachItemStats(items, run) {
  const ps = run.phaseStats || {};
  const sums = run.phaseSummaries || {};
  for (const item of items) {
    if (item.kind === 'phase-divider' || item.kind === 'error' || item.kind === 'deadlock') continue;
    if (item.kind === 'input') {
      // Phase 0 preflight is keyed per agent, but the input card is shared.
      // Use max(claude, gpt) rather than the sum — the two agents critique
      // the same brief and their issue lists overlap heavily, so the sum is
      // misleading. The larger of the two is the better single proxy.
      const p0 = ps.phase0 || {};
      const cIssues = p0.claude?.briefIssues ?? 0;
      const gIssues = p0.gpt?.briefIssues ?? 0;
      const count = Math.max(cIssues, gIssues);
      const bothOk = p0.claude?.status === 'BRIEF_OK' && p0.gpt?.status === 'BRIEF_OK';
      item.stats = bothOk
        ? { kind: 'preflight', state: 'ok' }
        : count > 0
          ? { kind: 'preflight', state: 'issues', count }
          : null;
      // briefSummary is the heuristic TL;DR; falls back to topic.
      item.summary = run.briefSummary || item.summary || '';
      continue;
    }
    if (item.kind === 'preflight') {
      // Spec 0033: per-agent Phase 0 critique card.
      const p0 = ps.phase0 || {};
      item.stats = p0[item.agent] || null;
      item.statsPhase = 0;
      item.summary = sums[`phase0_${item.agent}`] || item.summary || '';
      continue;
    }
    if (item.kind === 'plan' || item.kind === 'plan-live') {
      item.stats = ps.phase1?.[item.agent] || null;
      item.statsPhase = 1;
      item.summary = sums[`phase1_${item.agent}`] || item.summary || '';
      continue;
    }
    if (item.kind === 'turn' || item.kind === 'turn-live') {
      // Round + agent lookup. Round-keyed dicts come over the wire with
      // string keys after the snake_case → camelCase server pass.
      const phase = (item.round && item.index && String(item.index).startsWith('rev-')) ? 4 : 2;
      const bucket = phase === 4 ? ps.phase4 : ps.phase2;
      item.stats = bucket?.[String(item.round)]?.[item.agent] || null;
      item.statsPhase = phase;
      item.summary =
        sums[`phase${phase}_round${item.round}_${item.agent}`] || item.summary || '';
      // Spec 0034: round-over-round delta annotations on chips need the
      // prior round's stats for the same agent. Lookup is best-effort; if
      // we're on round 1 it stays null and chips render without deltas.
      if (item.round > 1) {
        item.prevStats = bucket?.[String(item.round - 1)]?.[item.agent] || null;
      }
      continue;
    }
    if (item.kind === 'doc' || item.kind === 'doc-live') {
      // Phase 3 converged draft + final document — surface a summary if
      // the drafter wrote one in the markdown.
      const key = item.id === 'doc-final' ? 'final' : 'phase3';
      const s = sums[key];
      if (s) item.summary = s;
      continue;
    }
  }
  return items;
}

// ─────────────────── Window exports ───────────────────

Object.assign(window, {
  PHASES, TOPIC, INPUT_BRIEF, TURN_HISTORY,
  RunContext, useLiveRun, useRunList, useFileBody, useAttachments,
  useInputBundle, useSearchBundle, useSearchIndex, useAppMeta,
  attachmentBlobUrl,
  buildLiveTimeline, formatTopic, splitRunId,
  setActiveRunId, getActiveRunId,
});
