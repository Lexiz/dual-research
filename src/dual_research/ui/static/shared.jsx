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

// AgentIcon — model identifier tile. Renders the official Claude brand
// mark (Anthropic sunburst) for the warm track and the OpenAI logomark
// (hexagonal rosette) for the cool track. SVG path for Claude is from
// simple-icons.org; OpenAI path is the well-published logomark from the
// OpenAI brand kit. Tile background is the agent color token; glyph is
// rendered in `--on-accent` on the solid variant and in the agent color
// on ghost.
const CLAUDE_PATH = "m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z";
const OPENAI_PATH = "M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z";

function AgentIcon({ agent, size = 16, variant = 'solid' }) {
  const meta = AGENT_META[agent];
  const r = Math.max(3, Math.round(size * 0.22));
  const glyphSize = Math.round(size * 0.7);
  const path = agent === 'claude' ? CLAUDE_PATH : OPENAI_PATH;
  const glyph = (
    <svg viewBox="0 0 24 24" width={glyphSize} height={glyphSize} aria-hidden="true">
      <path d={path} fill="currentColor" />
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
//
// Spec 0025 layers stable block ids on every paragraph / heading / list
// item / blockquote / pre. The id is FNV-1a 32-bit of the block's
// textContent, formatted as base-36 — `id="b-1abc23de"`. Same text →
// same id across re-renders, which lets future specs anchor inline
// comments to specific blocks without fighting `marked`'s internals.
function _hashBlock(s) {
  // FNV-1a 32-bit. Imul for proper 32-bit arithmetic in JS.
  let h = 0x811c9dc5 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return ('0000000' + (h >>> 0).toString(36)).slice(-7);
}

function _injectBlockIds(html) {
  if (typeof document === 'undefined') return html;
  const container = document.createElement('div');
  container.innerHTML = html;
  const blocks = container.querySelectorAll(
    'p, li, h1, h2, h3, h4, h5, h6, blockquote, pre'
  );
  const used = new Set();
  blocks.forEach((el) => {
    if (el.id) return;
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!text) return;
    let id = `b-${_hashBlock(text)}`;
    // Disambiguate collisions within the same render so jump-to-id stays
    // deterministic if the same paragraph appears twice.
    let i = 1;
    while (used.has(id)) {
      id = `b-${_hashBlock(text)}-${i++}`;
    }
    used.add(id);
    el.id = id;
  });
  return container.innerHTML;
}

// Spec 0034: when the source markdown carries backend-emitted block-id
// comments (``<!-- block-id: b-N -->``), use those IDs verbatim so the
// pre-resolved anchors on ReviewItem.block_id point at real DOM nodes.
// Returns ``{ stripped, ids }`` — the markdown with comments removed +
// the ordered list of IDs in document order.
function _extractBackendBlockIds(source) {
  if (!source || source.indexOf('<!-- block-id:') === -1) {
    return { stripped: source, ids: [] };
  }
  const re = /^<!--\s*block-id:\s*(b-\d+)\s*-->\s*$/;
  const ids = [];
  const outLines = [];
  const lines = source.split('\n');
  for (const ln of lines) {
    const m = re.exec(ln);
    if (m) {
      ids.push(m[1]);
    } else {
      outLines.push(ln);
    }
  }
  return { stripped: outLines.join('\n'), ids };
}

// Apply backend IDs to rendered blocks in document order. If the backend
// emitted N IDs and the renderer emits N block elements, mapping is 1-1.
// If the counts don't match (edge: list-item splitting differs slightly),
// the un-matched blocks fall through to the hash-based fallback.
function _applyBackendBlockIds(html, ids) {
  if (typeof document === 'undefined' || !ids || ids.length === 0) return html;
  const container = document.createElement('div');
  container.innerHTML = html;
  const blocks = container.querySelectorAll(
    'p, li, h1, h2, h3, h4, h5, h6, blockquote, pre'
  );
  let i = 0;
  blocks.forEach((el) => {
    if (el.id) return;
    if (i < ids.length) {
      el.id = ids[i];
      i += 1;
    }
  });
  // Anything still un-IDed gets the hash fallback (no collisions because
  // hash IDs and backend IDs live in different namespaces — b-{digits} vs
  // b-{base36}).
  return _injectBlockIds(container.innerHTML);
}

// Spec 0042 D9/D10 — prose like ``**Purpose:** ...\n---\n## 1. Foo`` was
// rendering as an H2 wrapping the entire ``**Purpose:**`` paragraph
// (which then displayed bold). Root cause: CommonMark setext headings
// use ``---`` IMMEDIATELY following a paragraph as an H2 underline, so
// a bare ``---`` divider line without a blank line above it gets eaten
// as a heading marker for the previous paragraph. The brief content
// uses ``---`` as a section divider without blank-line padding.
//
// Fix: pre-process the source so every bare ``---`` line is surrounded
// by blank lines. Marked then interprets it as a thematic break
// (``<hr>``) instead of a heading underline. Same fix covers
// ``===`` (setext H1).
function _padSetextDividers(text) {
  if (!text) return text;
  // Match a line that is exactly 3+ dashes (or 3+ equals) optionally
  // followed by trailing whitespace, anywhere in the source. Insert
  // blank lines on either side if they're missing.
  return text.replace(
    /(^|[^\n])\n(---+|===+)[ \t]*\n([^\n]|$)/g,
    (m, before, divider, after) => {
      const lead = before === '\n' || before === '' ? before + '\n' : before + '\n\n';
      const tail = after === '\n' || after === '' ? '\n' + after : '\n\n' + after;
      return lead + divider + tail;
    }
  );
}

function Markdown({ text, className, style }) {
  const html = React.useMemo(() => {
    if (typeof window === 'undefined' || typeof window.marked === 'undefined') return null;
    try {
      // Spec 0034: pull backend-emitted block-id comments out of the
      // source BEFORE parsing — marked can otherwise inline them as raw
      // HTML or drop them depending on the gfm setting.
      const { stripped, ids } = _extractBackendBlockIds(text || '');
      // Spec 0042: normalise setext-heading-triggering dividers.
      const padded = _padSetextDividers(stripped);
      const raw = window.marked.parse(padded, { gfm: true, breaks: false });
      if (ids.length > 0) return _applyBackendBlockIds(raw, ids);
      return _injectBlockIds(raw);
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

// ───────────────────────── modal ─────────────────────────
// Big centred surface over a dimmed overlay. Spec 0025.
//
// Props:
//   open      bool     — render or not.
//   onClose   fn       — called on overlay click, X button, or Esc.
//   title     node     — header content (left-aligned).
//   subtitle  node     — optional small text under the title.
//   tabs      [{id,label,content,count?}]  — optional tab strip. When
//              provided the surface body renders only the active tab's
//              `content`; the `children` prop is ignored.
//   accent    color    — left-rail color (defaults to var(--info)).
//   width     px       — max surface width (default 1100).
function Modal({ open, onClose, title, subtitle, tabs, accent, children, width = 1100 }) {
  const [activeId, setActiveId] = React.useState(null);
  // Re-seed active tab when tabs change.
  React.useEffect(() => {
    if (tabs && tabs.length) setActiveId(tabs[0].id);
  }, [tabs ? tabs.map((t) => t.id).join('|') : null]);

  React.useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose && onClose(); };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const activeTab = tabs && tabs.find ? tabs.find((t) => t.id === activeId) : null;
  const body = tabs ? (activeTab ? activeTab.content : null) : children;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
        animation: 'dr-modal-in 120ms ease-out',
      }}>
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-1)',
          border: '1px solid var(--border-2)',
          borderLeft: `3px solid ${accent || COLORS.info}`,
          borderRadius: 'var(--r-3)',
          width: '100%', maxWidth: width,
          maxHeight: '92vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 24px 80px rgba(0,0,0,0.55), 0 4px 12px rgba(0,0,0,0.35)',
          overflow: 'hidden',
        }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-1)',
          background: 'var(--bg-0)',
          flexShrink: 0,
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 14, color: 'var(--fg-0)', fontWeight: 600,
              letterSpacing: '-0.005em',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{title}</div>
            {subtitle && (
              <div className="mono" style={{
                fontSize: 11, color: 'var(--fg-3)', marginTop: 2,
              }}>{subtitle}</div>
            )}
          </div>
          <button
            onClick={onClose}
            title="Close (Esc)"
            aria-label="Close"
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 28,
              background: 'transparent', border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-2)',
              color: 'var(--fg-2)',
              cursor: 'pointer',
            }}>
            <Icon.X />
          </button>
        </div>

        {/* Tab strip */}
        {tabs && tabs.length > 0 && (
          <div role="tablist" style={{
            display: 'flex', alignItems: 'stretch',
            padding: '0 16px',
            borderBottom: '1px solid var(--border-1)',
            background: 'var(--bg-0)',
            gap: 0,
            flexShrink: 0,
          }}>
            {tabs.map((t) => {
              const active = t.id === activeId;
              return (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setActiveId(t.id)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    padding: '10px 14px',
                    background: 'transparent', border: 'none',
                    color: active ? 'var(--fg-0)' : 'var(--fg-3)',
                    fontWeight: active ? 600 : 500,
                    fontSize: 12.5,
                    cursor: 'pointer',
                    borderBottom: `2px solid ${active ? (accent || COLORS.info) : 'transparent'}`,
                    marginBottom: -1,
                  }}>
                  <span>{t.label}</span>
                  {t.count != null && (
                    <span className="mono" style={{
                      fontSize: 10.5,
                      padding: '1px 6px',
                      background: active ? (accent || COLORS.info) + '20' : 'var(--bg-2)',
                      color: active ? (accent || COLORS.info) : 'var(--fg-3)',
                      borderRadius: 999,
                    }}>{t.count}</span>
                  )}
                  {t.badge && (
                    <span style={{
                      fontSize: 10.5,
                      color: COLORS.warn,
                      fontWeight: 700,
                    }}>{t.badge}</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Body */}
        <div style={{
          flex: 1, minHeight: 0, overflow: 'auto',
          padding: '18px 22px 22px',
          background: 'var(--bg-1)',
        }}>
          {body}
        </div>
      </div>
    </div>
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
  ArrowLeft:(p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>,
  Spark:    (p) => <svg {...p} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 17 9 11 13 15 21 7"/></svg>,
  Warn:     (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  Gear:     (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  SignOut:  (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  Help:     (p) => <svg {...p} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
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
// ───────────────────────── anchor scroll (spec 0027) ─────────────────────────
// Scroll a block inside `container` into view and apply a brief flash highlight.
//
// Resolution order:
//   1. If `blockId` is provided, getElementById within container.
//   2. If `text` is provided, scan rendered blocks for substring match
//      (case-insensitive, whitespace-collapsed).
//   3. If `afterHeading` is provided, find heading whose text begins with
//      that string; the caller renders the dashed-ghost placeholder under it.
//
// Returns the resolved element (or null) so callers can layer additional
// behaviour (e.g. mounting a ghost placeholder).
function _normaliseText(s) {
  return (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function _findBlockByText(container, text) {
  if (!container || !text) return null;
  const needle = _normaliseText(text);
  if (!needle) return null;
  // Cheap exact-hash route first: spec 0025's renderer already hashed every
  // block, so a same-text paragraph in this container has the same id.
  const blocks = container.querySelectorAll(
    'p[id^="b-"], h1[id^="b-"], h2[id^="b-"], h3[id^="b-"], h4[id^="b-"], h5[id^="b-"], h6[id^="b-"], li[id^="b-"], blockquote[id^="b-"], pre[id^="b-"]'
  );
  // Pass 1: exact textContent match.
  for (const el of blocks) {
    if (_normaliseText(el.textContent) === needle) return el;
  }
  // Pass 2: substring (the quote is typically a span inside a longer block).
  for (const el of blocks) {
    if (_normaliseText(el.textContent).includes(needle)) return el;
  }
  return null;
}

function _findHeadingByPrefix(container, headingText) {
  if (!container || !headingText) return null;
  const needle = _normaliseText(headingText);
  if (!needle) return null;
  const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
  for (const el of headings) {
    const t = _normaliseText(el.textContent);
    if (t === needle || t.startsWith(needle) || needle.startsWith(t)) return el;
  }
  return null;
}

function scrollAndFlash(container, { blockId, text, afterHeading } = {}) {
  if (!container) return null;
  let target = null;
  if (blockId) target = container.querySelector(`#${CSS.escape(blockId)}`);
  if (!target && text) target = _findBlockByText(container, text);
  if (!target && afterHeading) target = _findHeadingByPrefix(container, afterHeading);
  if (!target) return null;

  // Smooth-scroll the target into the container's vertical centre.
  const cRect = container.getBoundingClientRect();
  const tRect = target.getBoundingClientRect();
  const offset = tRect.top - cRect.top - container.clientHeight / 3;
  container.scrollBy({ top: offset, behavior: 'smooth' });

  // Flash highlight: add class, remove after the animation completes.
  target.classList.remove('dr-flash');
  // Force reflow so re-applying the class restarts the animation.
  // eslint-disable-next-line no-unused-expressions
  void target.offsetWidth;
  target.classList.add('dr-flash');
  window.setTimeout(() => target.classList.remove('dr-flash'), 1600);
  return target;
}

Object.assign(window, {
  COLORS, AGENT_META,
  Dot, AgentIcon, StatusBadge, Pill, MetricRow, PanelHeader, StreamingText, Markdown, Modal, Icon, fmt,
  scrollAndFlash,
});
