// shared.jsx — tokens, primitives, and the demo data store
// Loaded as <script type="text/babel"> so React + JSX are available

// ───────────────────────── tokens (mirrors theme.css) ─────────────────────────
const COLORS = {
  agentA: '#d4a574',
  agentB: '#7cc4b8',
  ok: '#6fb380',
  warn: '#d4a056',
  err: '#d96a6a',
  info: '#6b9cf0',
  idle: '#5e636d',
};

const AGENT_META = {
  claude: { key: 'claude', name: 'Claude', model: 'claude-sonnet-4.5', color: COLORS.agentA, pulse: 'pulse-a', bg: 'var(--agent-a-bg)', bgStrong: 'var(--agent-a-bg-strong)', border: 'var(--agent-a-border)' },
  gpt:    { key: 'gpt',    name: 'GPT',    model: 'gpt-5.1',          color: COLORS.agentB, pulse: 'pulse-b', bg: 'var(--agent-b-bg)', bgStrong: 'var(--agent-b-bg-strong)', border: 'var(--agent-b-border)' },
};

// ───────────────────────── small primitives ─────────────────────────

function Dot({ color, pulse, size = 8 }) {
  return (
    <span
      className={pulse || ''}
      style={{
        display: 'inline-block', width: size, height: size, borderRadius: '50%',
        background: color, flexShrink: 0,
      }}
    />
  );
}

// AgentIcon — model identifier tile. Uses an abstract glyph (4-petal asterisk
// for the warm/Claude track, hex-node for the cool/GPT track). These are
// original geometric shapes, not brand marks — swap in licensed SVGs later.
function AgentIcon({ agent, size = 16, variant = 'solid' }) {
  const meta = AGENT_META[agent];
  const r = Math.max(3, Math.round(size * 0.22));
  const glyphSize = Math.round(size * 0.72);
  const glyph = agent === 'claude' ? (
    <svg viewBox="0 0 16 16" width={glyphSize} height={glyphSize} aria-hidden="true">
      <polygon points="8,2 9,7 8,8 7,7" fill="currentColor" />
      <polygon points="8,14 9,9 8,8 7,9" fill="currentColor" />
      <polygon points="2,8 7,7 8,8 7,9" fill="currentColor" />
      <polygon points="14,8 9,7 8,8 9,9" fill="currentColor" />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" width={glyphSize} height={glyphSize} aria-hidden="true">
      <path d="M8 1.6 L14 5 L14 11 L8 14.4 L2 11 L2 5 Z"
            fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="1.5" fill="currentColor" />
    </svg>
  );

  if (variant === 'ghost') {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: size, height: size, borderRadius: r,
        background: meta.color + '1f',
        color: meta.color,
        border: `1px solid ${meta.color}55`,
        flexShrink: 0, lineHeight: 1,
      }}>{glyph}</span>
    );
  }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: size, height: size, borderRadius: r,
      background: meta.color,
      color: 'var(--on-accent)',
      flexShrink: 0, lineHeight: 1,
    }}>{glyph}</span>
  );
}

function StatusBadge({ status }) {
  const map = {
    running:    { label: 'running',    color: COLORS.info, pulse: 'pulse-a' },
    converged:  { label: 'converged',  color: COLORS.ok,   pulse: null },
    deadlocked: { label: 'deadlocked', color: COLORS.warn, pulse: 'pulse-warn' },
    errored:    { label: 'errored',    color: COLORS.err,  pulse: 'pulse-err' },
    completed:  { label: 'completed',  color: COLORS.ok,   pulse: null },
    idle:       { label: 'idle',       color: COLORS.idle, pulse: null },
    thinking:   { label: 'thinking',   color: COLORS.info, pulse: 'pulse-a' },
    drafting:   { label: 'drafting',   color: COLORS.info, pulse: 'pulse-a' },
    responding: { label: 'responding', color: COLORS.info, pulse: 'pulse-a' },
    reviewing:  { label: 'reviewing',  color: COLORS.info, pulse: 'pulse-a' },
    waiting:    { label: 'waiting',    color: COLORS.idle, pulse: null },
  };
  const m = map[status] || map.idle;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 8px 3px 7px',
      background: 'var(--bg-2)',
      border: '1px solid var(--border-1)',
      borderRadius: 999,
      fontSize: 11,
      color: 'var(--fg-1)',
      fontFamily: 'var(--mono)',
      letterSpacing: '0.01em',
    }}>
      <Dot color={m.color} pulse={m.pulse} size={6} />
      {m.label}
    </span>
  );
}

function Pill({ children, color, tone = 'subtle' }) {
  const bg = tone === 'subtle' ? 'transparent' : (color + '20');
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '2px 7px',
      background: bg,
      border: `1px solid ${color || 'var(--border-2)'}55`,
      borderRadius: 4,
      fontSize: 10.5,
      color: color || 'var(--fg-1)',
      fontFamily: 'var(--mono)',
      letterSpacing: '0.02em',
      textTransform: 'lowercase',
      whiteSpace: 'nowrap',
    }}>{children}</span>
  );
}

function MetricRow({ label, value, mono = true, color, accent }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '4px 0',
      borderBottom: '1px dashed var(--border-1)',
      fontSize: 12,
    }}>
      <span style={{ color: 'var(--fg-3)', fontSize: 11, letterSpacing: '0.01em' }}>{label}</span>
      <span className={mono ? 'mono num' : 'num'} style={{ color: color || 'var(--fg-0)', fontSize: 12 }}>
        {value}
      </span>
    </div>
  );
}

function PanelHeader({ icon, agent, title, status, right }) {
  const meta = agent ? AGENT_META[agent] : null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 14px',
      borderBottom: '1px solid var(--border-1)',
      background: meta ? meta.bg : 'var(--bg-2)',
    }}>
      {meta && (
        <div style={{
          width: 22, height: 22, borderRadius: 5,
          background: meta.bgStrong,
          border: `1px solid ${meta.border}`,
          display: 'grid', placeItems: 'center',
          fontFamily: 'var(--mono)',
          color: meta.color,
          fontSize: 11,
          fontWeight: 600,
        }}>{meta.name[0]}</div>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ color: meta ? meta.color : 'var(--fg-0)', fontWeight: 600, fontSize: 13, letterSpacing: '-0.005em' }}>
            {meta ? meta.name : title}
          </span>
          {meta && (
            <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>{meta.model}</span>
          )}
        </div>
      </div>
      {status && <StatusBadge status={status} />}
      {right}
    </div>
  );
}

// ───────────────────────── markdown ─────────────────────────
// Render markdown content with consistent typography. Falls back to plain
// pre-wrap text if `marked` isn't loaded for any reason.
function Markdown({ text, className, style }) {
  const html = React.useMemo(() => {
    if (typeof window === 'undefined' || typeof window.marked === 'undefined') return null;
    try {
      return window.marked.parse(text || '', { gfm: true, breaks: false });
    } catch (e) {
      return null;
    }
  }, [text]);
  if (html == null) {
    return (
      <pre style={{ margin: 0, fontFamily: 'var(--sans)', fontSize: 13,
                    color: 'var(--fg-0)', whiteSpace: 'pre-wrap', lineHeight: 1.6, ...style }}>
        {text}
      </pre>
    );
  }
  return (
    <div className={`md ${className || ''}`} style={style}
         dangerouslySetInnerHTML={{ __html: html }} />
  );
}

// ───────────────────────── streaming text ─────────────────────────

// Renders body text that "streams" character by character.
// content: full string; speed: chars/second; playing: bool
function StreamingText({ content, speed = 60, playing = true, caret = true, color }) {
  const [shown, setShown] = React.useState(playing ? 0 : content.length);

  React.useEffect(() => {
    if (!playing) { setShown(content.length); return; }
    setShown(0);
    const start = performance.now();
    const id = setInterval(() => {
      const elapsed = (performance.now() - start) / 1000;
      const target = Math.min(content.length, Math.floor(elapsed * speed));
      setShown(target);
      if (target >= content.length) clearInterval(id);
    }, 1000 / 30); // ~30 fps tick; runs even when raf is throttled
    return () => clearInterval(id);
  }, [content, speed, playing]);

  const text = content.slice(0, shown);
  const done = shown >= content.length;
  return (
    <span style={{
      fontFamily: 'var(--sans)',
      color: color || 'var(--fg-1)', fontSize: 13, lineHeight: 1.6,
      whiteSpace: 'pre-wrap',
    }}>
      {text}
      {caret && !done && playing && <span className="caret" style={{ color: color || 'var(--fg-2)' }} />}
    </span>
  );
}

// ───────────────────────── tiny icon set (single-stroke) ─────────────────────────
const Icon = {
  Activity: (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>,
  List:     (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>,
  Palette:  (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="7" r="1.2" fill="currentColor"/><circle cx="7" cy="12" r="1.2" fill="currentColor"/><circle cx="17" cy="12" r="1.2" fill="currentColor"/></svg>,
  Chevron:  (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>,
  Dot:      (p) => <svg {...p} width="8" height="8" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>,
  Check:    (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  X:        (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  Arrow:    (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>,
  Spark:    (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 17 9 11 13 15 21 7"/></svg>,
  Warn:     (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
};

// ───────────────────────── formatting helpers ─────────────────────────
const fmt = {
  cost: (n) => `$${n.toFixed(4)}`,
  costShort: (n) => `$${n.toFixed(2)}`,
  tokens: (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n),
  duration: (s) => {
    const m = Math.floor(s / 60);
    const r = Math.floor(s % 60);
    return `${m}m ${String(r).padStart(2, '0')}s`;
  },
  relTime: (s) => {
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  },
};

// ───────────────────────── share to window for other Babel files ─────────────────────────
Object.assign(window, {
  COLORS, AGENT_META,
  Dot, AgentIcon, StatusBadge, Pill, MetricRow, PanelHeader, StreamingText, Markdown, Icon, fmt,
});
