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

// ─── SPEC-0068 — Brand-icon system ───────────────────────────
// BRAND_SVGS: single source of truth for the two brand glyphs.
// BrandMark: standalone SVG primitive — renders the glyph at the
// requested size in the agent's brand color (solid) or a tinted
// variant (ghost). AgentIcon delegates to BrandMark for the tiled
// presentation used in strips and cards.

const BRAND_SVGS = {
  claude: "m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z",
  openai: "M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z",
};

// BrandMark — standalone brand glyph. Renders the official Anthropic
// sunburst (claude) or OpenAI hexagonal rosette (openai) at the
// requested pixel size. `solid` fills with agent brand color; `ghost`
// uses a lower-opacity tint. Use aria-label when the mark identifies
// an agent in context; set aria-hidden="true" when decorative.
function BrandMark({ name, size = 16, variant = 'solid', className, style, ...rest }) {
  const path = BRAND_SVGS[name];
  if (!path) return null;
  const agentKey = name === 'claude' ? 'claude' : 'gpt';
  const meta = AGENT_META[agentKey];
  const color = variant === 'ghost' ? (meta.color + '88') : meta.color;
  const ariaLabel = rest['aria-label'] != null ? rest['aria-label']
    : rest['aria-hidden'] ? undefined
    : (name === 'claude' ? 'Claude' : 'OpenAI GPT');
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      style={{ flexShrink: 0, display: 'inline-block', verticalAlign: 'middle', ...style }}
      aria-label={ariaLabel}
      aria-hidden={rest['aria-hidden'] || undefined}
      role={ariaLabel ? 'img' : undefined}
    >
      <path d={path} fill={color} />
    </svg>
  );
}

// AgentIcon — tiled agent identifier (background square + glyph).
// Delegates to BRAND_SVGS for the path data. Keeps the existing API
// (agent='claude'|'gpt', size, variant='solid'|'ghost') so all call
// sites work unchanged.
function AgentIcon({ agent, size = 16, variant = 'solid' }) {
  const meta = AGENT_META[agent];
  const r = Math.max(3, Math.round(size * 0.22));
  const glyphSize = Math.round(size * 0.7);
  const brandName = agent === 'claude' ? 'claude' : 'openai';
  const path = BRAND_SVGS[brandName];
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

// SPEC-0093 — StatusBadge now emits M3 `.md-status` class names.
// Maps every known status string to one of the six M3 status pill
// modifiers. Prop API unchanged — callers pass `status="running"` etc.
const _STATUS_TO_M3 = {
  running:    'running',
  converged:  'converged',
  completed:  'converged',
  deadlocked: 'drift',
  errored:    'errored',
  idle:       'idle',
  queued:     'queued',
  thinking:   'running',
  drafting:   'running',
  responding: 'running',
  reviewing:  'running',
  waiting:    'idle',
};
function StatusBadge({ status, label }) {
  const m3 = _STATUS_TO_M3[status] || 'idle';
  const text = label || status || 'idle';
  return (
    <span className={`md-status md-status--${m3}`}>
      {text}
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

// ───────────────────────── modal (SPEC-0058 — CSS-class-backed) ─────────────────────────
// Class-backed modal using `.dr-modal` / `.dr-backdrop` from components.css.
// Replaces the original inline-styled Modal from spec 0025.
//
// Props:
//   open      bool     — render or not.
//   onClose   fn       — called on overlay click, X button, or Esc.
//   title     node     — header content (left-aligned).
//   subtitle  node     — optional small text under the title.
//   tabs      [{id,label,content,count?,badge?}] — optional tab strip (rendered
//              via TabGroup line variant). When provided the body renders only
//              the active tab's `content`; `children` is ignored.
//   agent     'a'|'b'|null — controls the 4 px left-border color (v1 compat).
//   agentTint 'a'|'b'|null — M3 alias for agent (spec 0096).
//   variant   'single'|'split'|'basic'|'rich' — default 'single'/'basic'.
//   footer    node     — optional fixed footer below the body (e.g. RoundScrubber).
//   children  node     — body content (ignored when `tabs` is provided).
function Modal({ open, onClose, title, subtitle, tabs, agent, agentTint, variant = 'split', footer, children }) {
  const [activeId, setActiveId] = React.useState(null);
  const modalRef = React.useRef(null);
  const previousFocusRef = React.useRef(null);

  // Re-seed active tab when tabs change.
  React.useEffect(() => {
    if (tabs && tabs.length) setActiveId(tabs[0].id);
  }, [tabs ? tabs.map((t) => t.id).join('|') : null]);

  // Esc to close + body overflow lock.
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

  // Focus trap: capture on mount, return on unmount.
  React.useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement;
    const timer = setTimeout(() => {
      if (modalRef.current) {
        const first = modalRef.current.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (first) first.focus();
      }
    }, 0);
    return () => {
      clearTimeout(timer);
      if (previousFocusRef.current && typeof previousFocusRef.current.focus === 'function') {
        previousFocusRef.current.focus();
      }
    };
  }, [open]);

  // Tab cycling within modal.
  React.useEffect(() => {
    if (!open || !modalRef.current) return;
    const onKeyTrap = (e) => {
      if (e.key !== 'Tab') return;
      const focusable = modalRef.current.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', onKeyTrap);
    return () => window.removeEventListener('keydown', onKeyTrap);
  }, [open]);

  if (!open) return null;

  const activeTab = tabs && tabs.find ? tabs.find((t) => t.id === activeId) : null;
  const body = tabs ? (activeTab ? activeTab.content : null) : children;

  // Resolve agent tint: new `agentTint` prop takes priority over v1 `agent`.
  const tint = agentTint || agent || null;

  // Map variant: v1 'single'→'basic', v1 'split'→'rich'; M3 names pass through.
  const resolvedVariant = variant === 'split' ? 'rich' : (variant === 'single' ? 'basic' : variant);

  const modalCls = _cn(
    'dr-modal', 'md-dialog',
    resolvedVariant === 'rich' ? 'is-split' : null,
    resolvedVariant === 'rich' ? 'md-dialog--rich' : 'md-dialog--basic',
    tint && `is-${tint}`,
    tint && `md-dialog--agent-${tint}`,
  );

  return (
    <div className="dr-backdrop md-dialog__scrim" onClick={onClose}>
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        className={modalCls}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="dr-modal-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="dr-modal-title md-dialog__title">{title}</div>
            {subtitle && <div className="dr-modal-sub">{subtitle}</div>}
          </div>
          <button
            className="dr-modal-close"
            onClick={onClose}
            title="Close (Esc)"
            aria-label="Close"
          >
            <Icon.X />
          </button>
        </div>

        {/* Tab strip — uses TabGroup line variant (SPEC-0053) */}
        {tabs && tabs.length > 0 && (
          <div className="dr-modal-tabs">
            <TabGroup variant="line">
              {tabs.map((t) => (
                <Tab
                  key={t.id}
                  size="sm"
                  active={t.id === activeId}
                  onClick={() => setActiveId(t.id)}
                  count={t.count}
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
          </div>
        )}

        {/* Body */}
        <div className="dr-modal-body md-dialog__body">
          {body}
        </div>

        {/* Footer (e.g. RoundScrubber) */}
        {footer}
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

// ───────────────────────── icon set — MDI-backed shim (SPEC-0050) ─────────────────────────
// Legacy `Icon.X` keys preserved; each forwards to `<Mdi>` from icons.jsx
// (loaded ahead of this file in index.html, exposed on window.Mdi).
// SPEC-0051 will sweep call sites onto `<Mdi name="…">` directly and
// retire this shim.
const _mkIcon = (mdiName, defaultSize) => (p = {}) => {
  const { size, ...rest } = p;
  return <Mdi name={mdiName} size={size || defaultSize} {...rest} />;
};
const Icon = {
  Activity:     _mkIcon('pulse',          14),
  List:         _mkIcon('menu',           14),
  Palette:      _mkIcon('palette',        14),
  Chevron:      _mkIcon('chevron-right',  12),
  Dot:          _mkIcon('circle-filled',   8),
  Check:        _mkIcon('check',          12),
  X:            _mkIcon('close',          12),
  Arrow:        _mkIcon('arrow-right',    12),
  ArrowLeft:    _mkIcon('arrow-left',     14),
  Spark:        _mkIcon('shimmer',        12),
  Warn:         _mkIcon('alert',          14),
  Gear:         _mkIcon('cog',            14),
  SignOut:      _mkIcon('logout',         14),
  Help:         _mkIcon('help-circle',    14),
  FileDocument: _mkIcon('file-document',  12),
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

// ─────────────────────────── SPEC-0052 — new primitive vocabulary ───────────────────────────
// Class-backed wrappers around `components.css`. These coexist with the legacy
// inline-styled `Pill`, `StatusBadge`, `MetricRow`, etc. (kept as-is so existing
// surfaces don't break); future surface specs migrate call sites onto these.
// Naming uses the brief's React API ([scripts/primitives.jsx]).
//
// agent='a' = Claude, agent='b' = GPT (matches CSS .ai-a / .ai-b classes).

function _cn(...parts) { return parts.filter(Boolean).join(' '); }

// Button — SPEC-0093: emits M3 `md-btn md-btn--{variant}` class names.
// Variant map: primary→filled, secondary→outlined, ghost→text, danger→outlined.
// Size map: sm→md-btn--sm, md→(default 40dp), lg→md-btn--lg.
// Keeps the existing prop API so call sites don't break.
const _BTN_VARIANT_MAP = { primary: 'filled', secondary: 'outlined', ghost: 'text', danger: 'outlined' };
const _BTN_SIZE_MAP = { sm: 'md-btn--sm', lg: 'md-btn--lg' };
function Button({ size = 'md', variant = 'secondary', leadingIcon, trailingIcon, children, onClick, disabled, className, type = 'button', title }) {
  const m3Variant = _BTN_VARIANT_MAP[variant] || 'outlined';
  const sizeClass = _BTN_SIZE_MAP[size] || null;
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title}
            className={_cn('md-btn', `md-btn--${m3Variant}`, sizeClass, className)}>
      {leadingIcon && <Mdi name={leadingIcon} size={14} />}
      {children && <span>{children}</span>}
      {trailingIcon && <Mdi name={trailingIcon} size={14} />}
    </button>
  );
}

// SB — class-backed StatusBadge primitive. Renamed to avoid shadowing the
// legacy inline-styled `StatusBadge` that run-list and other surfaces still
// consume; SPEC-0055..0057 will sweep call sites onto this and retire the old.
// tone: 'idle' | 'ok' | 'info' | 'warn' | 'err' | 'a' | 'b' | 'running'
function SB({ tone = 'idle', size = 'md', children, live = false, className }) {
  const sizeClass = size === 'sm' ? 'sb-sm' : null;
  return (
    <span className={_cn('sb', tone && `sb-${tone}`, sizeClass, live && 'sb-running', className)}>
      <i className="dot" />
      <span>{children}</span>
    </span>
  );
}

// Chip — Spec 0119 unified primitive. The single chip across every
// surface. Two prop tiers coexist:
//
//   • Slot API (preferred, spec 0119): leadingDot / leadingIcon /
//     categoryBubble (mutually exclusive leading element), then
//     label, value, add, sub, trailingSuffix, plus modifiers
//     iconOnly / dim / mono / shape / size.
//   • Legacy props: tone / pill / lg / icon / noDot / asButton /
//     children. Still honored so existing callsites render
//     unchanged until they're migrated.
//
// Tones: info · ok · warn · err · idle · claude · gpt · neutral
//        (legacy aliases: a (=claude), b (=gpt), muted, info-strong)
//
// Auto leading-dot: when a tone is set and the caller is using the
// LEGACY API, the chip auto-renders a ::before dot for status tones
// (info/ok/warn/err/idle/muted/info-strong). New slot-API callers
// auto-suppress the auto-dot, so explicit leadingDot / leadingIcon
// / categoryBubble never collide with it.
function Chip({
  // ─── new slot API ───────────────────────────
  leadingDot,
  leadingIcon,
  categoryBubble,
  label,
  value,
  add,
  sub,
  trailingSuffix,
  iconOnly,
  dim,
  shape,
  size,
  mono,
  ariaLabel,
  // ─── legacy ────────────────────────────────
  tone,
  pill,
  lg,
  icon,
  children,
  asButton,
  onClick,
  className,
  title,
  style,
  m3,
  noDot,
  ...rest
}) {
  // Detect new-slot usage so the auto-dot ::before stays out of the way.
  const usesNewSlots = (
    leadingDot != null || leadingIcon != null || categoryBubble != null ||
    iconOnly || value != null || add != null || sub != null ||
    trailingSuffix != null || dim || mono || label != null
  );
  const suppressAutoDot = noDot || usesNewSlots;

  const isTonal = tone && !m3;
  const cls = isTonal
    ? _cn(
        'chip',
        `tone-${tone}`,
        pill && 'chip-pill',                                 // legacy no-op (pill is default)
        (lg || size === 'lg') && 'chip-lg',
        shape === 'square' && 'chip-square',
        mono && 'mono',
        dim && 'dim',
        iconOnly && 'chip-icon-only',
        suppressAutoDot && 'no-dot',
        className,
      )
    : _cn('md-chip', lg && 'md-chip--sm', className);

  const content = (
    <>
      {leadingDot && <span className="chip-dot" aria-hidden="true" />}
      {leadingIcon && <span className="chip-leading-icon" aria-hidden="true">{leadingIcon}</span>}
      {categoryBubble && (
        <span className="cat-bubble" aria-hidden="true">{categoryBubble}</span>
      )}
      {icon && <Mdi name={icon} size={12} className="ico" />}
      {label != null && <span className="chip-label">{label}</span>}
      {value != null && <span className="chip-value">{value}</span>}
      {add != null && <span className="chip-add">+{add}</span>}
      {sub != null && <span className="chip-sub">−{sub}</span>}
      {trailingSuffix != null && <span className="chip-suffix">{trailingSuffix}</span>}
      {children}
    </>
  );

  // If onClick is set, render as a button so the click actually fires.
  const renderButton = !!(asButton || onClick);
  if (renderButton) {
    return (
      <button
        type="button"
        className={cls}
        onClick={onClick}
        title={title}
        style={style}
        aria-label={ariaLabel}
        {...rest}
      >
        {content}
      </button>
    );
  }
  return (
    <span
      className={cls}
      title={title}
      style={style}
      aria-label={ariaLabel}
      {...rest}
    >
      {content}
    </span>
  );
}

// Spec 0119 — bare ✓ status chip glyph. Thin alias over Icon.Check at
// the canonical 12 px size; lives here so chip callsites can read it
// alongside the Chip primitive without a separate import dance.
function CheckGlyph(props) {
  return <Icon.Check {...props} />;
}

// RunIDChip — pure identity, pill-shaped 4-char hex. Size sm or md.
function RunIDChip({ id, size = 'md', className, onClick, title }) {
  const sizeClass = size === 'sm' ? 'rid-sm' : null;
  const cls = _cn('rid', sizeClass, className);
  if (onClick) {
    return <button type="button" className={cls} onClick={onClick} title={title || id}>{id}</button>;
  }
  return <span className={cls} title={title || id}>{id}</span>;
}

// Card — base + variants. Wrap in `<CardBody>` for the expanded body region
// (the `.card-body` margin/padding kicks in when the parent has `.card-expanded`).
// SPEC-0094: `variant` selects M3 card style (elevated/filled/outlined/tonal-a/tonal-b).
// `hoverable` sets data-hoverable="true" for the hover-elevation rule.
// When variant is set, the M3 `.md-card` base is used instead of v1 `.card`.
function Card({ live, agent, expanded, interactive, onClick, className, children, role, ariaLabel, variant, hoverable, ...rest }) {
  const Tag = interactive ? 'button' : 'div';
  const useM3 = !!variant;
  const cls = useM3
    ? _cn('md-card', variant && `md-card--${variant}`, interactive && 'is-interactive', className)
    : _cn('card', interactive && 'is-interactive', expanded && 'card-expanded', live && 'card-live', live && agent === 'b' && 'is-b', className);
  return (
    <Tag
      onClick={interactive ? onClick : undefined}
      type={interactive ? 'button' : undefined}
      role={role}
      aria-label={ariaLabel}
      className={cls}
      data-hoverable={hoverable ? 'true' : undefined}
      {...rest}
    >
      {children}
    </Tag>
  );
}
function CardBody({ children, className }) {
  return <div className={_cn('card-body', className)}>{children}</div>;
}

// AgentStrip — uses brief's 'a'/'b' agent convention.
// `name` defaults to 'Claude'/'GPT' based on agent.
function AgentStrip({ agent = 'a', name, model, tokens, cost, status = 'idle', live, right, className }) {
  const displayName = name || (agent === 'a' ? 'Claude' : 'GPT');
  return (
    <div className={_cn('as', `is-${agent}`, className)}>
      <span className="as-left">
        <span className={`ai ai-md ai-${agent}`} role="img" aria-label={displayName}>
          {agent === 'a' ? <ClaudeMonogram /> : <OpenAIMonogram />}
        </span>
        <span className="as-name">{displayName}</span>
        {model && <span className="as-model mono">{model}</span>}
      </span>
      <span className="as-right mono">
        {tokens != null && (
          <>
            <span className="num v">{fmt.tokens(tokens)}</span>
            <span className="sep">·</span>
          </>
        )}
        {cost != null && (
          <>
            <span className="num v">{fmt.cost(cost)}</span>
            <span className="sep">·</span>
          </>
        )}
        {right != null ? right : <SB tone={status} size="sm" live={live}>{status}</SB>}
      </span>
    </div>
  );
}

// SPEC-0094 — ModelBadge: 56dp right-cluster pill containing an AgentStrip + model id.
// Both Claude and GPT pills render identically at 56dp height (Issue 1 symmetry).
// The model name truncates with ellipsis if longer than the pill width; height never changes.
function ModelBadge({ agent, model }) {
  const slot = agent === 'claude' ? 'a' : 'b';
  const meta = AGENT_META[agent] || AGENT_META.claude;
  const displayName = meta.name;
  return (
    <span className={_cn('agent-strip', `agent-strip--${slot}`)}
          style={{ height: 56, minWidth: 0 }}
          title={`${displayName} · ${model}`}>
      <span className="dot" />
      <span style={{ fontWeight: 'var(--md-w-medium)', whiteSpace: 'nowrap' }}>{displayName}</span>
      <span style={{
        fontFamily: 'var(--mono)', fontSize: 'var(--t-mono)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        opacity: 0.8,
      }}>{model}</span>
    </span>
  );
}

// Brand monograms used inside .ai tile — reference BRAND_SVGS dict.
function ClaudeMonogram() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d={BRAND_SVGS.claude} fill="currentColor" /></svg>;
}
function OpenAIMonogram() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d={BRAND_SVGS.openai} fill="currentColor" /></svg>;
}

// ─── SPEC-0053 / SPEC-0095 — Tab + TabGroup ───────────────────
// TabGroup variant: undefined (bordered pill), 'line', 'solid',
//   'md-tabs' (M3 primary tabs), 'tab-group-solid' (M3 segmented pill),
//   'phase-tabs', 'kind-tabs', 'fgroup'.
// Tab variant (SPEC-0095): undefined (v1 bordered pill), 'primary' (M3
//   md-tab), 'solid' (tab-solid), 'kind' (kind-tab), 'phase' (phase-tab),
//   'chrome' (md-btn--text for app-bar use).
function TabGroup({ children, className, variant }) {
  const variantClass = variant === 'line' ? 'tabs-line'
    : variant === 'solid' ? 'tabs-solid'
    : variant === 'md-tabs' ? null
    : variant === 'tab-group-solid' ? null
    : variant === 'phase-tabs' ? null
    : variant === 'kind-tabs' ? null
    : variant === 'fgroup' ? null
    : null;
  const baseClass = variant === 'md-tabs' ? 'md-tabs'
    : variant === 'tab-group-solid' ? 'tab-group-solid'
    : variant === 'phase-tabs' ? 'phase-tabs'
    : variant === 'kind-tabs' ? 'kind-tabs'
    : variant === 'fgroup' ? 'fgroup'
    : 'tab-group';
  return (
    <div className={_cn(baseClass, variantClass, className)} role="tablist">
      {children}
    </div>
  );
}
function Tab({ active, onClick, size = 'md', icon, children, count, disabled, dot, filterTone, className, variant }) {
  if (variant === 'primary') {
    return (
      <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
              onClick={onClick} disabled={disabled}
              className={_cn('md-tab', className)}>
        {icon && <Mdi name={icon} size={14} />}
        <span>{children}</span>
        {count != null && <span className="count num">{count}</span>}
      </button>
    );
  }
  if (variant === 'solid') {
    return (
      <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
              onClick={onClick} disabled={disabled}
              className={_cn('tab-solid', active && 'is-active', className)}>
        {dot && <i className="dot" />}
        {icon && <Mdi name={icon} size={14} />}
        <span>{children}</span>
      </button>
    );
  }
  if (variant === 'kind') {
    return (
      <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
              onClick={onClick} disabled={disabled}
              className={_cn('kind-tab', active && 'is-active', count === 0 && 'is-zero', className)}>
        {icon && <Mdi name={icon} size={14} />}
        <span>{children}</span>
        {count != null && <span className="ct">{count}</span>}
      </button>
    );
  }
  if (variant === 'phase') {
    return (
      <button type="button" role="tab" aria-selected={active ? 'true' : 'false'}
              onClick={onClick} disabled={disabled}
              className={_cn('phase-tab', active && 'is-active', className)}>
        {children}
      </button>
    );
  }
  if (variant === 'chrome') {
    return (
      <button type="button" onClick={onClick} disabled={disabled}
              className={_cn('md-btn', 'md-btn--text', 'md-btn--sm', active && 'is-active', className)}
              style={{ height: 40 }}>
        {icon && <Mdi name={icon} size={14} />}
        <span>{children}</span>
      </button>
    );
  }
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active ? 'true' : 'false'}
      onClick={onClick}
      disabled={disabled}
      className={_cn('tab', size === 'sm' && 'tab-sm', active && 'is-active', dot && 'tab-filter', filterTone && `tab-${filterTone}`, count === 0 && 'is-zero', className)}
    >
      {dot && <i className="dot" />}
      {icon && <Mdi name={icon} size={14} />}
      <span>{children}</span>
      {count != null && <span className="count num">{count}</span>}
    </button>
  );
}

// ThemeToggle — segmented two-cell sun/moon with sliding thumb (CMP-02).
// Accepts either `onChange(newTheme)` (brief's API) or `onToggle()` (legacy).
function ThemeToggleSegmented({ theme = 'dark', onChange, onToggle }) {
  const setTheme = (next) => {
    if (next === theme) return;
    if (onChange) onChange(next);
    else if (onToggle) onToggle();
  };
  return (
    <div className="tt" data-theme={theme} role="group" aria-label="Theme">
      <span className="tt-thumb" aria-hidden="true" />
      <button type="button"
              className={_cn('tt-cell', theme === 'light' && 'is-active')}
              onClick={() => setTheme('light')}
              aria-label="Switch to light theme"
              aria-pressed={theme === 'light' ? 'true' : 'false'}
              title="Switch to light theme">
        <Mdi name="white-balance-sunny" size={12} />
      </button>
      <button type="button"
              className={_cn('tt-cell', theme === 'dark' && 'is-active')}
              onClick={() => setTheme('dark')}
              aria-label="Switch to dark theme"
              aria-pressed={theme === 'dark' ? 'true' : 'false'}
              title="Switch to dark theme">
        <Mdi name="weather-night" size={12} />
      </button>
    </div>
  );
}

// ── SPEC-0054 primitives ─────────────────────────────────────────────────────

// parseQId — decode legacy "Q-g-r1-04" string into structured fields.
// c = Claude (maps to 'claude'), g = GPT (maps to 'gpt').
function parseQId(legacy) {
  if (typeof legacy !== 'string') return { number: legacy };
  const m = /^Q-([cg])-r(\d+)-(\d+)$/.exec(legacy);
  if (!m) return { number: legacy };
  return {
    number: parseInt(m[3], 10),
    raisedBy: m[1] === 'c' ? 'claude' : 'gpt',
    round: parseInt(m[2], 10),
  };
}

// agentSlot — map "claude"/"gpt" to "a"/"b" for CSS class names.
function _agentSlot(agent) { return agent === 'claude' ? 'a' : agent === 'gpt' ? 'b' : agent; }

// QuestionRef — decoded reference for a critique question.
// format='compact' (default): "Q · 04"
// format='full': "Q · 04 · [Claude] · r1"
// format='split' (Spec 0111): "Q · 04" only. Agent + round are rendered as
// sibling chips by QuestionThread per Notion issue 4 ("no badge encodes
// two facts; agent and round get their own pills").
// kindLetter: 'Q' (default) | 'D' | 'I' | 'C' — Spec 0097
function QuestionRef({ id, number, raisedBy, round, format = 'compact', kindLetter = 'Q', className }) {
  if (id != null && (number == null || raisedBy == null || round == null)) {
    const p = parseQId(id);
    if (number == null)   number   = p.number;
    if (raisedBy == null) raisedBy = p.raisedBy;
    if (round == null)    round    = p.round;
  }
  const num = typeof number === 'number' ? String(number).padStart(2, '0') : (number || '');
  const agentLabel = raisedBy === 'claude' ? 'Claude' : raisedBy === 'gpt' ? 'GPT' : null;
  const slot = _agentSlot(raisedBy);
  const kindName = { Q: 'Question', D: 'Disagreement', I: 'Issue', C: 'Comment' }[kindLetter] || kindLetter;
  const title = [kindName + ' ' + num, agentLabel && 'raised by ' + agentLabel, round != null && 'in round ' + round].filter(Boolean).join(' — ');
  const wantsAuthor = format === 'full' && agentLabel;
  const wantsRound  = format === 'full' && round != null;
  return (
    <span
      className={_cn('qref', format === 'full' && 'qref-full', format === 'split' && 'qref-split', className)}
      data-kind={kindLetter}
      title={title}
    >
      <span className="qref-k">{kindLetter}</span>
      <span className="qref-sep" aria-hidden="true">&middot;</span>
      <span className="qref-n num">{num}</span>
      {wantsAuthor && (
        <span className={_cn('qref-by', `is-${slot}`)}>
          <AgentIcon agent={raisedBy} size={14} />
          <span className="qref-by-n">{agentLabel}</span>
        </span>
      )}
      {wantsRound && (
        <span className="qref-round num">r{round}</span>
      )}
    </span>
  );
}

// Spec 0097 — canonical six-word verdict vocabulary.
const VERDICT_VOCAB = ['raised', 'pushback', 'conceded', 'resolved', 'ghosted', 'drift'];

// QuestionThread — unified item-card for Q · D · I · C critique items.
// Spec 0097: single anatomy with expand/collapse, tonal bubbles, dashed footer.
// kind: 'question' | 'disagreement' | 'issue' | 'comment'
// status: 'open' | 'open-new' | 'resolved' | 'drift'
// turns: [{ agent, round, verdict, quote }]
function QuestionThread({
  id, kind: threadKind = 'question', status = 'open',
  raisedBy, raisedRound, phase,
  turns = [], footer, onHighlight,
  // Spec 0111 — when nested inside a phase-grouped section (e.g.
  // <CritiquePhaseContent> renders inside .crit-group for a specific
  // phase), the phase chip on the card is redundant. Callers pass
  // showPhaseChip={false} to suppress it. Defaults to true so the chip
  // still shows at out-of-context callsites (Σ Summary, search results).
  showPhaseChip = true,
  // Legacy compat — ignored by new header, kept for SummaryView callsite
  question, statusChips,
}) {
  const [open, setOpen] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const articleRef = React.useRef(null);

  // Dev-mode verdict validation
  turns.forEach((t) => {
    if (t.verdict && !VERDICT_VOCAB.includes(t.verdict)) {
      console.error('[QuestionThread] verdict "' + t.verdict + '" is not in VERDICT_VOCAB: ' + VERDICT_VOCAB.join(', '));
    }
  });

  const kindLetter = threadKind === 'question' ? 'Q'
                   : threadKind === 'disagreement' ? 'D'
                   : threadKind === 'issue' ? 'I'
                   : threadKind === 'comment' ? 'C' : 'Q';

  // Derive a display number from the id
  const parsed = threadKind === 'question' ? parseQId(id) : { number: id };
  const displayNum = typeof parsed.number === 'number' ? parsed.number : null;

  // Status chip
  const statusCss = status === 'open-new' ? 'open' : status;
  const statusTone = (status === 'open' || status === 'open-new') ? 'warn'
                   : status === 'resolved' ? 'ok'
                   : status === 'drift' ? 'err' : 'warn';
  const lastRound = turns.length > 0 ? turns[turns.length - 1].round : null;
  // Spec 0111 \u2014 verbose status labels. No `r2`-style abbreviations; rounds
  // spell out as `round 2`. Resolves Notion issue 4.
  const verboseStatusLabel = status === 'open-new' ? 'Open \u00b7 new'
                           : status === 'open' ? 'Open'
                           : status === 'resolved' ? ('Resolved' + (lastRound ? ' in round ' + lastRound : ''))
                           : status === 'drift' ? 'Drift'
                           : status;

  const agentLabel = raisedBy === 'claude' ? 'Claude' : raisedBy === 'gpt' ? 'GPT' : null;

  // Spec 0111 dev assertion \u2014 flag a UI/data desync where the card's status
  // and the surrounding .crit-group's data-tone disagree. Resolves Notion
  // issue 2's invariant (status pill must match the section it sits in).
  React.useEffect(() => {
    const el = articleRef.current;
    if (!el) return;
    const group = el.closest('.crit-group');
    if (!group) return;
    const tone = group.getAttribute('data-tone');
    const expectedTone = (status === 'open' || status === 'open-new') ? 'warn'
                       : status === 'resolved' ? 'ok'
                       : status === 'drift' ? 'err'
                       : null;
    if (expectedTone && tone && tone !== expectedTone) {
      console.error('[critique] status/section mismatch: status=' + status + ', section=' + tone, el);
    }
  }, [status]);

  const onCardClick = () => {
    if (onHighlight) onHighlight();
    setOpen(o => !o);
  };

  return (
    <article
      ref={articleRef}
      className={_cn('qthread', 'is-' + statusCss)}
      aria-labelledby={id ? 'qt-' + id : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCardClick(); } }}
      /* Spec 0116 — inline marginBottom: 8 removed. Parent flex container
         (`gap: 8px` on .crit-group__body and .tl-phase__body) is now the
         single source of card spacing — Critique was 16 px effective
         (8 px parent + 8 px child); Timeline was 8 px (child overridden
         to 0 via `.qthread.tl-thread { margin: 0 }`). Both panes at 8 px now. */
    >
      {/* HEADER — Spec 0119 §8.4. Provider FIRST. Category chip
          (bubble + singular label). Raised-in chip. Status chip
          right-aligned with leading dot. Public-ID moves out of
          the header into a small mono text element inside the
          card body. */}
      <header className="crit-card-head" onClick={onCardClick}>
        {agentLabel && (
          <Chip
            tone={raisedBy === 'gpt' ? 'gpt' : 'claude'}
            leadingIcon={<AgentIcon agent={raisedBy} size={12} />}
            label={agentLabel}
          />
        )}
        {(() => {
          // QuestionThread receives `kind` in singular form; the
          // canonical CATEGORY_* maps live in run-detail.jsx and key
          // on the plural form (`questions` / `disagreements` / …).
          // A thin singular-to-plural shim keeps shared.jsx
          // dependency-free.
          const pluralKind = threadKind === 'question' ? 'questions'
                           : threadKind === 'disagreement' ? 'disagreements'
                           : threadKind === 'issue' ? 'issues'
                           : threadKind === 'comment' ? 'comments'
                           : 'questions';
          const tones = { questions: 'info', disagreements: 'warn', issues: 'err', comments: 'idle' };
          const bubbles = { questions: 'Q', disagreements: 'D', issues: 'I', comments: 'C' };
          const labels = { questions: 'Question', disagreements: 'Disagreement', issues: 'Issue', comments: 'Comment' };
          return (
            <Chip
              tone={tones[pluralKind]}
              categoryBubble={bubbles[pluralKind]}
              label={labels[pluralKind]}
              ariaLabel={labels[pluralKind]}
            />
          );
        })()}
        {raisedRound != null && (
          <Chip mono tone="neutral" label={`raised in r${raisedRound}`} />
        )}
        {showPhaseChip && phase && (
          <Chip mono tone="neutral" label={`phase ${phase}`} />
        )}
        <span className="crit-card-head__spacer" />
        <Chip tone={statusTone} leadingDot label={verboseStatusLabel.toLowerCase()} />
        <span
          className="crit-card-chev"
          aria-hidden="true"
          data-open={open ? 'true' : undefined}
        >
          <Icon.Chevron />
        </span>
      </header>
      {/* Spec 0119 §8.4 — public ID renders as small mono inline text,
          not as a chip in the header. Always visible (collapsed or
          expanded) so it's copyable. */}
      {id && <div className="crit-card-id">id: {id}</div>}

      {/* TIMELINE + FOOTER — visible when expanded */}
      {open && <>
        <ol className="qt-timeline" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {turns.map((t, i) => {
            const agent = t.agent === 'both' ? 'claude' : (t.agent || 'claude');
            const slot = _agentSlot(agent);
            const agentLabel = t.agent === 'both' ? 'Both' : (agent === 'claude' ? 'Claude' : 'GPT');
            const isGhosted = t.verdict === 'ghosted' || t.kind === 'ghosted';
            return (
              <li key={i} className={_cn('qt-row', 'is-' + slot, isGhosted && 'is-ghosted')}>
                <span className="qt-pill" aria-label={agentLabel + ' round ' + t.round + (t.verdict ? ' \u2014 ' + t.verdict : '')}>
                  <AgentIcon agent={agent} size={14} />
                  <span className="qt-agent">{agentLabel}</span>
                  {t.round != null && <>
                    <span className="qt-sep" aria-hidden="true">&middot;</span>
                    <span className="qt-round num">r{t.round}</span>
                  </>}
                  {t.verdict && <>
                    <span className="qt-sep" aria-hidden="true">&middot;</span>
                    <span className="qt-verdict">{t.verdict}</span>
                  </>}
                </span>
                {t.quote && <p className="qt-quote">
                  {typeof t.quote === 'string' ? <Markdown text={t.quote} /> : t.quote}
                </p>}
              </li>
            );
          })}
        </ol>
        {footer && status === 'resolved' && <div className="qt-resolved-foot">{footer}</div>}
        {footer && status === 'drift'    && <div className="qt-drift">{footer}</div>}
      </>}
    </article>
  );
}

// ── SPEC-0073 — QuoteCallout ──────────────────────────────────────────────────
// Styled callout for .quote fields on critique cards (issues, comments).
// Replaces inline italic rendering with a visually distinct callout block.
function QuoteCallout({ text, children }) {
  if (!text && !children) return null;
  return (
    <div className="quote-callout">
      {text ? `"${text}"` : children}
    </div>
  );
}

// ── SPEC-0057 — ChipCluster ───────────────────────────────────────────────────
// Wraps a list of chip children and collapses overflow beyond `max` into a +N
// button. Clicking the overflow toggles showing all chips.
function ChipCluster({ max = 5, children, className }) {
  const [expanded, setExpanded] = React.useState(false);
  const items = React.Children.toArray(children).filter(Boolean);
  if (items.length <= max || expanded) {
    return (
      <span className={_cn('cc', className)}>
        {items}
        {expanded && items.length > max && (
          <button type="button" className="cc-overflow" onClick={() => setExpanded(false)}>
            collapse
          </button>
        )}
      </span>
    );
  }
  const visible = items.slice(0, max);
  const overflow = items.length - max;
  return (
    <span className={_cn('cc', className)}>
      {visible}
      <button type="button" className="cc-overflow" onClick={() => setExpanded(true)}>
        +{overflow}
      </button>
    </span>
  );
}

// ── SPEC-0101 — RoundScrubber (M3 segmented-button + icon-btn) ─────────────────
// Horizontal round-stepping bar for split modals. Uses M3 .md-seg
// segmented buttons for round pills and .md-icon-btn for prev/next.
// rounds: array of round numbers available (e.g. [1,2,3,4,5]).
// current: the currently selected round number.
// onChange(roundNum): called when user clicks a round or arrow.
function RoundScrubber({ rounds, current, onChange }) {
  if (!rounds || rounds.length <= 1) return null;
  const idx = rounds.indexOf(current);
  const hasPrev = idx > 0;
  const hasNext = idx < rounds.length - 1;
  return (
    <div className="round-scrubber" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '8px 16px', borderTop: '1px solid var(--md-outline-hair)', flexShrink: 0 }}>
      <button
        type="button"
        className="md-icon-btn"
        disabled={!hasPrev}
        onClick={() => hasPrev && onChange(rounds[idx - 1])}
        aria-label="Previous round"
      >
        <span className="ms ms-20">chevron_left</span>
      </button>
      <div className="md-seg" role="tablist">
        {rounds.map((r) => (
          <button
            key={r}
            type="button"
            role="tab"
            className="md-seg__opt"
            aria-selected={r === current ? 'true' : 'false'}
            onClick={() => onChange(r)}
          >
            r{r}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="md-icon-btn"
        disabled={!hasNext}
        onClick={() => hasNext && onChange(rounds[idx + 1])}
        aria-label="Next round"
      >
        <span className="ms ms-20">chevron_right</span>
      </button>
      <span style={{ font: '12px/1 var(--md-font-plain)', color: 'var(--md-on-surface-faint)', marginLeft: 4 }}>
        round {current} of {rounds.length}
      </span>
    </div>
  );
}

// ── SPEC-0067 — parseCodeId + CodeCluster ────────────────────────────────────
// parseCodeId(id) — parse a critique public ID into structured components.
// Five known prefixes: Q- (question), I- (issue), C- (comment), Cl- (claim),
// d- (disagreement). Format: PREFIX-RAISER-ROUND_OR_PHASE-SEQ (e.g. I-c-r1-06)
// or d-SEQ (e.g. d-04). Returns { kind, raiser, round, phase, sequence, raw }.
const CODE_KIND_MAP = {
  Q:  'question',
  I:  'issue',
  C:  'comment',
  Cl: 'claim',
  d:  'disagreement',
};
const CODE_KIND_LABELS = {
  question:     'Question',
  issue:        'Issue',
  comment:      'Comment',
  claim:        'Claim',
  disagreement: 'Disagreement',
};

function parseCodeId(id) {
  if (typeof id !== 'string') return { raw: String(id ?? ''), kind: null, raiser: null, round: null, phase: null, sequence: null };
  const raw = id;

  // Disagreement: d-NN
  const dm = /^d-(\d+)$/.exec(id);
  if (dm) return { raw, kind: 'disagreement', raiser: null, round: null, phase: null, sequence: parseInt(dm[1], 10) };

  // Q/I/C/Cl: PREFIX-RAISER-r/pN-SEQ  (e.g. I-c-r1-06, Cl-g-p1-01)
  const m = /^(Q|I|C|Cl)-([cg])-([rp])(\d+)-(\d+)$/.exec(id);
  if (m) {
    const kind = CODE_KIND_MAP[m[1]] || m[1];
    const raiser = m[2] === 'c' ? 'claude' : 'gpt';
    const isPhase = m[3] === 'p';
    return {
      raw,
      kind,
      raiser,
      round: isPhase ? null : parseInt(m[4], 10),
      phase: isPhase ? parseInt(m[4], 10) : null,
      sequence: parseInt(m[5], 10),
    };
  }

  // Fallback — unparseable
  return { raw, kind: null, raiser: null, round: null, phase: null, sequence: null };
}

// CodeCluster — structured chip cluster for any critique public ID.
// Renders: [Kind SEQ] [agent chip] [round chip] with tooltip showing raw code.
function CodeCluster({ id, kind, hideRound, size }) {
  const parsed = typeof id === 'string' ? parseCodeId(id) : { raw: String(id ?? ''), kind: null, sequence: null, raiser: null, round: null, phase: null };
  const effectiveKind = kind || parsed.kind;
  const kindLabel = CODE_KIND_LABELS[effectiveKind] || effectiveKind || '';
  const seq = parsed.sequence != null ? String(parsed.sequence).padStart(2, '0') : null;
  const chipSize = size === 'sm';

  return (
    <span className="cc" title={parsed.raw} data-code={parsed.raw}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
      <Chip tone={effectiveKind === 'disagreement' || effectiveKind === 'issue' ? 'warn' : 'info'}
            style={chipSize ? { fontSize: 10 } : undefined}>
        {kindLabel}{seq ? ` ${seq}` : ''}
      </Chip>
      {parsed.raiser && (
        <Chip tone={parsed.raiser === 'claude' ? 'a' : 'b'}
              style={chipSize ? { fontSize: 10 } : undefined}>
          <BrandMark name={parsed.raiser === 'claude' ? 'claude' : 'openai'} size={12} variant="ghost" aria-hidden="true" />
          {' '}{AGENT_META[parsed.raiser]?.name || parsed.raiser}
        </Chip>
      )}
      {!hideRound && parsed.round != null && (
        <Chip tone="muted" style={chipSize ? { fontSize: 10 } : undefined}>
          R{parsed.round}
        </Chip>
      )}
      {!hideRound && parsed.phase != null && (
        <Chip tone="muted" style={chipSize ? { fontSize: 10 } : undefined}>
          P{parsed.phase}
        </Chip>
      )}
    </span>
  );
}

// ─────────────────── CollapsibleSection (SPEC-0071 D9) ───────────────────
// Generic disclosure primitive. Used by timeline phase headers (D4)
// and critique pane section headers (D8).
function CollapsibleSection({ title, count, countColor, defaultOpen = true, persistKey, onToggle, children, renderTitle, style }) {
  const [open, setOpen] = React.useState(() => {
    if (!persistKey) return defaultOpen;
    try { const v = localStorage.getItem(persistKey); return v == null ? defaultOpen : v === '1'; } catch { return defaultOpen; }
  });
  const toggle = React.useCallback(() => {
    setOpen(prev => {
      const next = !prev;
      if (persistKey) try { localStorage.setItem(persistKey, next ? '1' : '0'); } catch {}
      if (onToggle) onToggle(next);
      return next;
    });
  }, [persistKey, onToggle]);
  return (
    <div className="cs" style={style}>
      <button type="button" className="cs-header" onClick={toggle} aria-expanded={open}>
        {renderTitle ? renderTitle({ open }) : (
          <>
            <span className="cs-chevron" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
            <span className="cs-title">{title}</span>
            {count != null && <span className="cs-count mono num" style={countColor ? { color: countColor } : undefined}>{count}</span>}
          </>
        )}
      </button>
      <div className={`cs-body ${open ? 'cs-open' : 'cs-closed'}`}>
        {open && children}
      </div>
    </div>
  );
}

// ─────────────────── LoadingState (SPEC-0084) ───────────────────
//
// One harmonious loading visual across the app. Three sizes:
//   - 'inline'  → a small spinner + label, row-flex; for inside cards
//                 and modals (where the prior copy was "loading…" in
//                 mono).
//   - 'panel'   → medium spinner stacked above the label + optional
//                 hint; for the run-list empty state, comparison
//                 panels, and other mid-page placeholders.
//   - 'page'    → large spinner stacked above the label + optional
//                 hint; for full-page waiting states (run-detail's
//                 "Loading run…", app boot's "Connecting").
//
// The hint defaults to "Just a moment, please." for panel/page sizes;
// pass `hint={null}` (or `hint=""`) to suppress, or override with a
// surface-specific string (e.g. the run id while the run snapshot is
// hydrating).

const _LOADING_DIMS = {
  inline: { skelH: 12, skelW: 120, gap: 8,  fontSize: 11, padding: '4px 0',     dir: 'row'    },
  panel:  { skelH: 16, skelW: 200, gap: 10, fontSize: 13, padding: '60px 18px', dir: 'column' },
  page:   { skelH: 20, skelW: 280, gap: 14, fontSize: 15, padding: '80px 18px', dir: 'column' },
};

const _LOADING_DEFAULT_HINT = 'Just a moment, please.';

function LoadingState({ size = 'panel', label, hint, className, style }) {
  const dims = _LOADING_DIMS[size] || _LOADING_DIMS.panel;
  const resolvedHint = hint === undefined
    ? (size === 'inline' ? null : _LOADING_DEFAULT_HINT)
    : hint;
  return (
    <div
      className={_cn('dr-loading', `dr-loading-${size}`, className)}
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: dims.dir,
        alignItems: 'center',
        justifyContent: 'center',
        gap: dims.gap,
        padding: dims.padding,
        color: 'var(--fg-3)',
        ...style,
      }}
    >
      <div className="load-card" aria-hidden="true" style={{ alignItems: 'center' }}>
        <div className="skel" style={{ width: dims.skelW, height: dims.skelH, borderRadius: 4 }} />
        {size !== 'inline' && <div className="skel" style={{ width: dims.skelW * 0.6, height: dims.skelH * 0.7, borderRadius: 4 }} />}
      </div>
      {label && (
        <div style={{
          fontSize: dims.fontSize,
          color: 'var(--fg-1)',
          fontWeight: size === 'inline' ? 400 : 500,
        }}>
          {label}
        </div>
      )}
      {resolvedHint && (
        <div style={{
          fontSize: size === 'page' ? 12 : 11,
          color: 'var(--fg-3)',
          letterSpacing: 0.1,
        }}>
          {resolvedHint}
        </div>
      )}
    </div>
  );
}

Object.assign(window, {
  COLORS, AGENT_META,
  Dot, AgentIcon, StatusBadge, Pill, MetricRow, PanelHeader, StreamingText, Markdown, Modal, Icon, fmt,
  scrollAndFlash, BRAND_SVGS, BrandMark,
  // SPEC-0052 primitives
  Button, SB, Chip, RunIDChip, Card, CardBody, AgentStrip, ThemeToggleSegmented,
  // SPEC-0053 primitives
  Tab, TabGroup,
  // SPEC-0054 + SPEC-0097 primitives
  parseQId, QuestionRef, QuestionThread, VERDICT_VOCAB,
  // SPEC-0057 primitives
  ChipCluster,
  // SPEC-0058 primitives
  RoundScrubber,
  // SPEC-0067 primitives
  parseCodeId, CodeCluster, CODE_KIND_LABELS,
  // SPEC-0071 primitives
  CollapsibleSection,
  // SPEC-0073 primitives
  QuoteCallout,
  // SPEC-0084 primitives
  LoadingState,
  // SPEC-0093 primitives
  _STATUS_TO_M3,
  // SPEC-0094 primitives
  ModelBadge,
});
