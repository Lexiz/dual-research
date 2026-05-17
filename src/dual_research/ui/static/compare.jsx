// compare.jsx -- SPEC-0060 NEW-01
// Two-run side-by-side comparison dashboard.
// Fetches both runs via /api/runs/<id> and renders synced-scroll panels.

(function () {

function CompareScreen({ navigate }) {
  const { rows } = useRunList();
  const [runIdA, setRunIdA] = React.useState('');
  const [runIdB, setRunIdB] = React.useState('');
  const [runA, setRunA] = React.useState(null);
  const [runB, setRunB] = React.useState(null);
  const [loadingA, setLoadingA] = React.useState(false);
  const [loadingB, setLoadingB] = React.useState(false);
  const leftRef = React.useRef(null);
  const rightRef = React.useRef(null);
  const syncingRef = React.useRef(false);

  // Fetch run A.
  React.useEffect(() => {
    if (!runIdA) { setRunA(null); return; }
    setLoadingA(true);
    fetch(`/api/runs/${encodeURIComponent(runIdA)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { setRunA(data); setLoadingA(false); })
      .catch(() => { setRunA(null); setLoadingA(false); });
  }, [runIdA]);

  // Fetch run B.
  React.useEffect(() => {
    if (!runIdB) { setRunB(null); return; }
    setLoadingB(true);
    fetch(`/api/runs/${encodeURIComponent(runIdB)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { setRunB(data); setLoadingB(false); })
      .catch(() => { setRunB(null); setLoadingB(false); });
  }, [runIdB]);

  // Synced scroll.
  React.useEffect(() => {
    const left = leftRef.current;
    const right = rightRef.current;
    if (!left || !right) return;

    const syncScroll = (source, target) => () => {
      if (syncingRef.current) return;
      syncingRef.current = true;
      const maxScroll = source.scrollHeight - source.clientHeight;
      const ratio = maxScroll > 0 ? source.scrollTop / maxScroll : 0;
      const targetMax = target.scrollHeight - target.clientHeight;
      target.scrollTop = ratio * targetMax;
      requestAnimationFrame(() => { syncingRef.current = false; });
    };

    const onLeftScroll = syncScroll(left, right);
    const onRightScroll = syncScroll(right, left);

    left.addEventListener('scroll', onLeftScroll);
    right.addEventListener('scroll', onRightScroll);
    return () => {
      left.removeEventListener('scroll', onLeftScroll);
      right.removeEventListener('scroll', onRightScroll);
    };
  }, [runA, runB]);

  const runOptions = (rows || []).map((r) => ({
    id: r.id,
    displayId: r.displayId || r.id.slice(0, 4),
    topic: r.topic || r.id,
  }));

  return (
    <div style={{
      height: '100%', overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      background: 'var(--bg-0)',
    }}>
      {/* Header + pickers */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid var(--border-1)',
        display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Mdi name="compare" size={18} style={{ color: 'var(--fg-2)' }} />
          <span style={{
            fontSize: 'var(--t-title)',
            fontWeight: 'var(--w-semibold)',
            color: 'var(--fg-0)',
          }}>
            Compare runs
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <RunPicker
            label="Run A"
            value={runIdA}
            onChange={setRunIdA}
            options={runOptions}
            exclude={runIdB}
          />
          <span style={{ color: 'var(--fg-3)', fontSize: 13 }}>vs</span>
          <RunPicker
            label="Run B"
            value={runIdB}
            onChange={setRunIdB}
            options={runOptions}
            exclude={runIdA}
          />
        </div>
      </div>

      {/* Panels */}
      {(!runIdA || !runIdB) ? (
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--fg-3)', flexDirection: 'column', gap: 12,
        }}>
          <Mdi name="compare" size={32} style={{ opacity: 0.3 }} />
          <span style={{ fontSize: 13 }}>Select two runs above to compare them side-by-side</span>
        </div>
      ) : (
        <div style={{
          flex: 1, display: 'flex', overflow: 'hidden',
        }}>
          {/* Left panel */}
          <div ref={leftRef} style={{
            flex: 1, overflow: 'auto', borderRight: 'none',
            padding: '16px',
          }}>
            {loadingA ? (
              <PanelLoading label="Loading run A..." />
            ) : runA ? (
              <RunSummaryPanel run={runA} label="A" navigate={navigate} />
            ) : (
              <PanelLoading label="Failed to load run A" />
            )}
          </div>

          {/* Delta column */}
          <DeltaColumn runA={runA} runB={runB} />

          {/* Right panel */}
          <div ref={rightRef} style={{
            flex: 1, overflow: 'auto', borderLeft: 'none',
            padding: '16px',
          }}>
            {loadingB ? (
              <PanelLoading label="Loading run B..." />
            ) : runB ? (
              <RunSummaryPanel run={runB} label="B" navigate={navigate} />
            ) : (
              <PanelLoading label="Failed to load run B" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function RunPicker({ label, value, onChange, options, exclude }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      style={{
        padding: '4px 8px',
        fontSize: 12,
        fontFamily: 'var(--mono)',
        background: 'var(--bg-1)',
        color: 'var(--fg-0)',
        border: '1px solid var(--border-2)',
        borderRadius: 'var(--r-2)',
        maxWidth: 280,
      }}
    >
      <option value="">{label}: select...</option>
      {options.filter((o) => o.id !== exclude).map((o) => (
        <option key={o.id} value={o.id}>
          {o.displayId} - {o.topic.slice(0, 60)}
        </option>
      ))}
    </select>
  );
}

function PanelLoading({ label }) {
  return (
    <div style={{
      padding: '32px 0', textAlign: 'center',
      color: 'var(--fg-3)', fontSize: 13,
    }}>
      {label}
    </div>
  );
}

function RunSummaryPanel({ run, label, navigate }) {
  const phases = run.phases || [];
  const drafter = run.drafter;
  const topic = run.topic || run.id;
  const displayId = run.displayId || (run.id || '').slice(0, 4);
  const status = run.status || 'unknown';
  const cost = run.metrics?.totalCostUsd;
  const duration = run.duration;

  return (
    <div>
      {/* Run header */}
      <div style={{
        marginBottom: 16, paddingBottom: 12,
        borderBottom: '1px solid var(--border-1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span className="rid" style={{ fontSize: 12 }}>{displayId}</span>
          <span className="chip chip-sm">{status}</span>
          {drafter && (
            <span className="chip chip-sm" style={{
              background: drafter.key === 'claude' ? 'var(--agent-a-bg)' : 'var(--agent-b-bg)',
              borderColor: drafter.key === 'claude' ? 'var(--agent-a-border)' : 'var(--agent-b-border)',
              color: drafter.key === 'claude' ? 'var(--agent-a)' : 'var(--agent-b)',
            }}>
              {drafter.name} drafts
            </span>
          )}
        </div>
        <div style={{
          fontSize: 14, color: 'var(--fg-0)', fontWeight: 500,
          cursor: 'pointer',
        }}
        onClick={() => navigate('detail', run.id)}
        >
          {topic}
        </div>
        <div style={{
          fontSize: 11, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
          marginTop: 4, display: 'flex', gap: 12,
        }}>
          {cost != null && <span>${cost.toFixed(2)}</span>}
          {duration != null && <span>{Math.round(duration)}s</span>}
          <span>{phases.length} phase{phases.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Phase timeline */}
      {phases.map((phase, i) => (
        <PhaseCard key={i} phase={phase} index={i} />
      ))}

      {phases.length === 0 && (
        <div style={{
          padding: '16px 0', textAlign: 'center',
          color: 'var(--fg-3)', fontSize: 12,
        }}>
          No phase data
        </div>
      )}
    </div>
  );
}

function PhaseCard({ phase, index }) {
  const label = phase.label || `Phase ${index}`;
  const turns = phase.turns || [];
  const openItems = (phase.openItems || 0);

  return (
    <div style={{
      marginBottom: 12,
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: turns.length > 0 ? '1px solid var(--border-1)' : 'none',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{
          fontSize: 12, fontWeight: 600, color: 'var(--fg-0)',
        }}>
          {label}
        </span>
        <span style={{
          fontSize: 10, color: 'var(--fg-3)', fontFamily: 'var(--mono)',
        }}>
          {turns.length} turn{turns.length !== 1 ? 's' : ''}
        </span>
        {openItems > 0 && (
          <span className="chip chip-sm" style={{
            fontSize: 10,
            background: 'var(--warn-bg)',
            borderColor: 'var(--warn-border)',
            color: 'var(--warn)',
          }}>
            {openItems} open
          </span>
        )}
      </div>
      {turns.slice(0, 6).map((turn, ti) => (
        <div key={ti} style={{
          padding: '4px 12px',
          fontSize: 11, color: 'var(--fg-2)',
          borderBottom: ti < Math.min(turns.length, 6) - 1 ? '1px solid var(--border-1)' : 'none',
          display: 'flex', gap: 8, alignItems: 'center',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
            background: (turn.agent === 'claude') ? 'var(--agent-a)' : 'var(--agent-b)',
          }} />
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--fg-3)', flexShrink: 0 }}>
            {turn.label || `Turn ${ti + 1}`}
          </span>
          {turn.cost != null && (
            <span style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--mono)' }}>
              ${turn.cost.toFixed(3)}
            </span>
          )}
        </div>
      ))}
      {turns.length > 6 && (
        <div style={{
          padding: '4px 12px', fontSize: 10, color: 'var(--fg-4)',
          fontFamily: 'var(--mono)',
        }}>
          +{turns.length - 6} more turns
        </div>
      )}
    </div>
  );
}

function DeltaColumn({ runA, runB }) {
  if (!runA || !runB) return null;

  const deltas = [];

  // Drafter difference.
  const drafterA = runA.drafter?.name || 'unknown';
  const drafterB = runB.drafter?.name || 'unknown';
  if (drafterA !== drafterB) {
    deltas.push({ label: 'drafter', detail: `${drafterA} vs ${drafterB}` });
  }

  // Phase count difference.
  const phasesA = (runA.phases || []).length;
  const phasesB = (runB.phases || []).length;
  if (phasesA !== phasesB) {
    deltas.push({ label: 'phases', detail: `${phasesA} vs ${phasesB}` });
  }

  // Status difference.
  if (runA.status !== runB.status) {
    deltas.push({ label: 'status', detail: `${runA.status} vs ${runB.status}` });
  }

  // Cost difference.
  const costA = runA.metrics?.totalCostUsd || 0;
  const costB = runB.metrics?.totalCostUsd || 0;
  const costDiff = Math.abs(costA - costB);
  if (costDiff > 0.01) {
    deltas.push({ label: 'cost', detail: `$${costA.toFixed(2)} vs $${costB.toFixed(2)}` });
  }

  // Turn count per phase.
  const maxPhases = Math.max(phasesA, phasesB);
  for (let i = 0; i < maxPhases; i++) {
    const tA = (runA.phases || [])[i]?.turns?.length || 0;
    const tB = (runB.phases || [])[i]?.turns?.length || 0;
    if (tA !== tB) {
      const phaseLabel = (runA.phases || [])[i]?.label || (runB.phases || [])[i]?.label || `P${i}`;
      deltas.push({ label: phaseLabel, detail: `${tA} vs ${tB} turns` });
    }
  }

  return (
    <div style={{
      width: 140, flexShrink: 0,
      borderLeft: '1px solid var(--border-1)',
      borderRight: '1px solid var(--border-1)',
      padding: '16px 8px',
      overflow: 'auto',
      background: 'var(--bg-0)',
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, color: 'var(--fg-2)',
        textTransform: 'uppercase', letterSpacing: '0.06em',
        marginBottom: 12, textAlign: 'center',
      }}>
        Differences
      </div>
      {deltas.length === 0 && (
        <div style={{
          fontSize: 11, color: 'var(--fg-4)', textAlign: 'center',
          padding: '8px 0',
        }}>
          No differences
        </div>
      )}
      {deltas.map((d, i) => (
        <div key={i} style={{
          marginBottom: 8,
          padding: '6px 8px',
          background: 'var(--bg-1)',
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--r-2)',
        }}>
          <div style={{
            fontSize: 10, fontWeight: 600, color: 'var(--warn)',
            marginBottom: 2, display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <span style={{ fontSize: 11 }}>&#916;</span>
            {d.label}
          </div>
          <div style={{
            fontSize: 10, color: 'var(--fg-2)',
            fontFamily: 'var(--mono)',
          }}>
            {d.detail}
          </div>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { CompareScreen });
})();
