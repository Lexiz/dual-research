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

// Initial REST fetch + live SSE stream. Snapshot frames overwrite the run
// state wholesale (the aggregator emits full snapshots — see spec 0010).
function useLiveRun(runId) {
  const [run, setRun] = React.useState(null);
  const [connected, setConnected] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!runId) return;
    setRun(null);
    setError(null);
    setConnected(false);

    let cancelled = false;
    let es = null;

    // Initial REST fetch — populates the view before the first SSE frame.
    fetch(`/api/runs/${encodeURIComponent(runId)}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => { if (!cancelled) setRun(data); })
      .catch(e => { if (!cancelled) setError(String(e)); });

    // Live SSE — replaces the run on every snapshot frame.
    try {
      es = new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream`);
      es.addEventListener('snapshot', (ev) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(ev.data);
          setRun(data);
          setConnected(true);
        } catch (e) { /* drop malformed frame */ }
      });
      es.addEventListener('open', () => setConnected(true));
      es.addEventListener('error', () => setConnected(false));
    } catch (e) {
      setError(String(e));
    }

    return () => {
      cancelled = true;
      if (es) es.close();
    };
  }, [runId]);

  return { run, connected, error };
}

// ─────────────────── useRunList ───────────────────

// Polls /api/runs every 3 seconds. The endpoint is cheap (one stat per
// session dir). No global SSE in v1 per spec 0010.
function useRunList() {
  const [rows, setRows] = React.useState([]);
  const [lastOk, setLastOk] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    const tick = () => {
      fetch('/api/runs')
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (cancelled) return;
          setRows(data);
          setLastOk(Date.now());
        })
        .catch(() => { /* leave previous rows; lastOk goes stale → indicator dims */ });
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

  return { rows, connected };
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
    fetch(`/api/runs/${encodeURIComponent(runId)}/files/${filePath}`)
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

  // Phase 0: the brief.
  items.push({ id: 'phase-0', kind: 'phase-divider', phaseId: 0, duration: run.phaseTimings?.['0'] });
  items.push({ id: 'input', kind: 'input', filePath: 'brief.md', topic: run.topic });

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
      });
      items.push({
        id: 'p1-gpt-live', kind: 'plan-live', agent: 'gpt', live: true,
        status: run.agents?.gpt?.status,
        body: run.agents?.gpt?.currentTurn?.body || '',
        filePath: fileForPhase1Draft('gpt'),
      });
    } else {
      items.push({ id: 'p1-claude', kind: 'plan', agent: 'claude', filePath: fileForPhase1Draft('claude') });
      items.push({ id: 'p1-gpt',    kind: 'plan', agent: 'gpt',    filePath: fileForPhase1Draft('gpt')    });
    }
  }

  if (ph >= 2) {
    const cur = run.round?.current ?? 0;
    items.push({
      id: 'phase-2', kind: 'phase-divider', phaseId: 2,
      duration: run.phaseTimings?.['2'],
      extra: `${cur} round${cur === 1 ? '' : 's'}`,
    });
    if (ph === 2 && (st === 'running' || st === 'deadlocked' || st === 'errored')) {
      const completedThrough = Math.max(0, cur - 1);
      for (let r = 1; r <= completedThrough; r++) {
        items.push({ id: `p2-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                     filePath: fileForRound(2, r, 'claude') });
        items.push({ id: `p2-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                     filePath: fileForRound(2, r, 'gpt')    });
      }
      if (cur > 0 && st === 'running') {
        items.push({
          id: `p2-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
          round: cur, index: cur, live: true,
          status: run.agents?.claude?.status,
          body: run.agents?.claude?.currentTurn?.body || '',
          filePath: fileForRound(2, cur, 'claude'),
        });
        items.push({
          id: `p2-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
          round: cur, index: cur, live: true,
          status: run.agents?.gpt?.status,
          body: run.agents?.gpt?.currentTurn?.body || '',
          filePath: fileForRound(2, cur, 'gpt'),
        });
      }
    } else if (ph >= 3 || st === 'completed' || st === 'deadlocked') {
      // Run moved past P2 — enumerate all completed rounds from disk.
      const maxRound = cur;
      for (let r = 1; r <= maxRound; r++) {
        items.push({ id: `p2-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                     filePath: fileForRound(2, r, 'claude') });
        items.push({ id: `p2-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                     filePath: fileForRound(2, r, 'gpt')    });
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
      });
    } else if (run.drafter) {
      items.push({
        id: 'doc-converged', kind: 'doc', agent: run.drafter,
        summary: `Converged document drafted by ${run.drafter}.`,
        filePath: 'phase3/draft-v1.md',
      });
    }
  }

  if (ph >= 4 && st !== 'errored' && st !== 'deadlocked') {
    const cur = run.round?.current ?? 0;
    items.push({
      id: 'phase-4', kind: 'phase-divider', phaseId: 4,
      duration: run.phaseTimings?.['4'],
      extra: `${cur} review round${cur === 1 ? '' : 's'}`,
    });
    if (ph === 4) {
      const completedThrough = Math.max(0, cur - 1);
      for (let r = 1; r <= completedThrough; r++) {
        items.push({ id: `p4-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'claude') });
        items.push({ id: `p4-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'gpt')    });
      }
      if (cur > 0) {
        items.push({
          id: `p4-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
          round: cur, index: `rev-${cur}`, live: true,
          status: run.agents?.claude?.status,
          body: run.agents?.claude?.currentTurn?.body || '',
          filePath: fileForRound(4, cur, 'claude'),
        });
        items.push({
          id: `p4-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
          round: cur, index: `rev-${cur}`, live: true,
          status: run.agents?.gpt?.status,
          body: run.agents?.gpt?.currentTurn?.body || '',
          filePath: fileForRound(4, cur, 'gpt'),
        });
      }
    } else if (ph === 5 || st === 'completed') {
      const maxRound = cur;
      for (let r = 1; r <= maxRound; r++) {
        items.push({ id: `p4-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'claude') });
        items.push({ id: `p4-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'gpt')    });
      }
    }
  }

  if (ph >= 5 || st === 'completed') {
    items.push({ id: 'phase-5', kind: 'phase-divider', phaseId: 5, duration: run.phaseTimings?.['4'] });
    items.push({
      id: 'doc-final', kind: 'doc', agent: run.drafter, completed: true,
      summary: 'Final document — emitted.',
      filePath: 'final.md',
    });
  }

  if (st === 'errored' && run.error) items.push({ id: 'error', kind: 'error', error: run.error });
  if (st === 'deadlocked') {
    items.push({
      id: 'deadlock', kind: 'deadlock', round: run.round,
      open: (run.disagreements || []).filter(d => d.status === 'open').length,
    });
  }

  return items;
}

// ─────────────────── Window exports ───────────────────

Object.assign(window, {
  PHASES, TOPIC, INPUT_BRIEF, TURN_HISTORY,
  RunContext, useLiveRun, useRunList, useFileBody,
  buildLiveTimeline, formatTopic, splitRunId,
  setActiveRunId, getActiveRunId,
});
