// design-language.jsx — DNA one-pager (default) + full reference (?full=1)
// SPEC-0068: restructured to serve as the live source-of-truth for the
// design system. The DNA one-pager is the curated tour; the full reference
// preserves all original palette / type / spacing / motion / vocabulary /
// principles content.

function DesignLanguageView() {
  const params = new URLSearchParams(window.location.search);
  const showFull = params.get('full') === '1';
  return (
    <div style={{
      height: '100vh', overflow: 'auto',
      background: 'var(--md-surface)',
    }}>
      {showFull ? <FullReference /> : <DnaOnePager />}
    </div>
  );
}

// ─────────────────── DNA one-pager (default view) ───────────────────
// Five sections: Hero, Palette, Brand marks, Component spotlights, Construction.

function DnaOnePager() {
  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '36px 32px 72px' }}>
      {/* Hero */}
      <section style={{ marginBottom: 48 }}>
        <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
          dual-research · design language
        </div>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--md-on-surface)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
          A calm, dense observability surface for a two-agent convergence loop.
        </h1>
        <p style={{ marginTop: 12, color: 'var(--md-on-surface-muted)', fontSize: 13.5, maxWidth: 720, lineHeight: 1.55 }}>
          Read-only, terminal-adjacent, single user. Heavy emoji removed, dense Plex Sans on cream, never decoration that fights the signal. Information density is a feature.
        </p>
        <div className="mono" style={{ marginTop: 8, fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
          <a href="?full=1" style={{ color: 'var(--md-on-surface-faint)', textDecoration: 'underline' }}>Full reference</a>
        </div>
      </section>

      {/* Palette */}
      <DnaSection title="Palette">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
          <DnaSwatch label="Claude" color="var(--agent-a)" token="--agent-a" />
          <DnaSwatch label="OpenAI" color="var(--agent-b)" token="--agent-b" />
          <span style={{ width: 1, background: 'var(--md-outline-variant)', margin: '0 4px' }} />
          <DnaSwatch label="surface"   color="var(--md-surface)"                  token="--md-surface" border />
          <DnaSwatch label="surf-low"  color="var(--md-surface-container-low)"    token="--md-surface-container-low" border />
          <DnaSwatch label="surf-mid"  color="var(--md-surface-container)"        token="--md-surface-container" border />
          <DnaSwatch label="surf-high" color="var(--md-surface-container-high)"   token="--md-surface-container-high" border />
          <span style={{ width: 1, background: 'var(--md-outline-variant)', margin: '0 4px' }} />
          <DnaSwatch label="info" color="var(--info)" token="--info" />
          <DnaSwatch label="warn" color="var(--warn)" token="--warn" />
          <DnaSwatch label="ok"   color="var(--ok)"   token="--ok" />
          <DnaSwatch label="err"  color="var(--err)"  token="--err" />
          <span style={{ width: 1, background: 'var(--md-outline-variant)', margin: '0 4px' }} />
          <DnaSwatch label="on-surface" color="var(--md-on-surface)"          token="--md-on-surface" />
          <DnaSwatch label="on-variant" color="var(--md-on-surface-variant)"  token="--md-on-surface-variant" />
          <DnaSwatch label="on-muted"   color="var(--md-on-surface-muted)"    token="--md-on-surface-muted" />
          <DnaSwatch label="on-faint"   color="var(--md-on-surface-faint)"    token="--md-on-surface-faint" />
        </div>
      </DnaSection>

      {/* Brand marks */}
      <DnaSection title="Brand marks">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          {[
            ['claude', 'Claude', 'Used everywhere a Claude turn is rendered — list rows, run-detail header, AgentStrip pills, timeline cards, critique cards, the disagreement explorer.'],
            ['openai', 'OpenAI', 'Used everywhere a GPT turn is rendered — list rows, run-detail header, AgentStrip pills, timeline cards, critique cards, the disagreement explorer.'],
          ].map(([name, label, description]) => (
            <div key={name} style={{ background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)', padding: 14 }}>
              <div className="uppercase-label" style={{ marginBottom: 10 }}>{label}</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
                {/* SPEC-0087 § N — `solid 48` variant added back to the
                    DNA page per delta 20.41. Pre-spec the page rendered
                    only 32 / 24 / 16; the briefing had a `solid 48` XL
                    variant as the leftmost example. */}
                {[48, 32, 24, 16].map(s => (
                  <div key={s} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <BrandMark name={name} size={s} variant="solid" />
                    <span className="mono" style={{ fontSize: 9, color: 'var(--md-on-surface-faint)' }}>{s}</span>
                  </div>
                ))}
                {[16, 12].map(s => (
                  <div key={'g'+s} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <BrandMark name={name} size={s} variant="ghost" />
                    <span className="mono" style={{ fontSize: 9, color: 'var(--md-on-surface-faint)' }}>ghost {s}</span>
                  </div>
                ))}
              </div>
              {/* SPEC-0087 § N — per-card description text restored from
                  the original 20.41 briefing. Self-documents where the
                  glyph appears in the app. */}
              <p style={{ marginTop: 12, fontSize: 11, color: 'var(--md-on-surface-faint)', lineHeight: 1.5 }}>
                {description}
              </p>
            </div>
          ))}
        </div>
      </DnaSection>

      {/* Component spotlights */}
      <DnaSection title="Component spotlights">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
          <Spotlight label="<Chip>" caption="Spec 0119 — one primitive, nine canonical kinds. Slots: leadingDot · leadingIcon · categoryBubble · label · value · add · sub · trailingSuffix.">
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
              <Chip tone="claude" leadingIcon={<AgentIcon agent="claude" size={12} />} label="Claude" />
              <Chip tone="gpt" leadingIcon={<AgentIcon agent="gpt" size={12} />} label="GPT" />
              <Chip mono tone="neutral" label="turn 1" />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
              <Chip tone="info" categoryBubble="Q" value={4} add={2} sub={1} ariaLabel="Questions: 4 standing, 2 raised, 1 closed" />
              <Chip tone="warn" categoryBubble="D" value={2} add={1} sub={0} ariaLabel="Disagreements: 2 standing, 1 raised, 0 closed" />
              <Chip tone="err" categoryBubble="I" value={3} add={0} sub={2} ariaLabel="Issues: 3 standing, 0 raised, 2 closed" />
              <Chip tone="idle" dim categoryBubble="C" value={0} add={0} sub={0} ariaLabel="Comments: zero activity" />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
              <Chip tone="info" categoryBubble="Q" label="Questions" value={30} />
              <Chip tone="warn" categoryBubble="D" label="Disagreements" value={1} />
              <Chip tone="neutral" label="All" value={31} />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
              <Chip tone="info" leadingDot label="running" />
              <Chip tone="ok" leadingIcon={<CheckGlyph size={12} />} label="agreed" />
              <Chip tone="ok" iconOnly leadingIcon={<CheckGlyph size={12} />} ariaLabel="Round completed" />
              <Chip tone="idle" leadingDot label="queued" />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
              <Chip tone="info" label="raised" />
              <Chip tone="ok" label="resolved" />
              <Chip tone="warn" label="acknowledged" />
              <Chip tone="idle" label="withdrawn" />
              <Chip tone="err" label="capped" />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <Chip mono tone="neutral" label="↻ closeout" />
              <Chip mono tone="warn" label="⚠ ledger drift" value={3} />
              <Chip tone="neutral" label="Sources" value={2} />
              <Chip mono shape="square" tone="neutral" label="Q-plan-c-04" />
            </div>
          </Spotlight>

          <Spotlight label="<Card>" caption="Expandable container for timeline entries and critique items.">
            <Card style={{ padding: 10 }}>
              <div style={{ fontSize: 12, color: 'var(--md-on-surface-variant)' }}>Phase 2 draft</div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', marginTop: 4 }}>Claude · R4 · 2,847 tokens</div>
            </Card>
          </Spotlight>

          <Spotlight label="<Tab>" caption="Three variants: bordered pill, minimal underline, segmented solid.">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <TabGroup><Tab active>Timeline</Tab><Tab>Critique</Tab><Tab>Input</Tab></TabGroup>
              <TabGroup variant="line"><Tab active>Overview</Tab><Tab>Rounds</Tab></TabGroup>
              <TabGroup variant="solid"><Tab active>Dark</Tab><Tab>Light</Tab></TabGroup>
            </div>
          </Spotlight>

          <Spotlight label="<AgentStrip>" caption="Equal-width agent identifier with model, tokens, cost, and status. Compact 4px vertical padding (SPEC-0070). Both pills share width via flex: 1 1 0.">
            <div style={{ display: 'flex', gap: 6 }}>
              <AgentStrip agent="a" model="claude-sonnet-4.5" tokens={12480} cost={0.042} status="completed" />
              <AgentStrip agent="b" model="gpt-5.1" tokens={9120} cost={0.031} status="completed" />
            </div>
          </Spotlight>

          <Spotlight label="<StatusBadge>" caption="Fixed-width status pill with dot + label. Uniform 88px min-width.">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
              <StatusBadge status="running" />
              <StatusBadge status="converged" />
              <StatusBadge status="deadlocked" />
              <StatusBadge status="errored" />
              <StatusBadge status="completed" />
            </div>
          </Spotlight>

          <Spotlight label="<CollapsibleSection>" caption="Generic disclosure primitive. Persists open/closed state to localStorage. Used by timeline phase headers and critique pane sections.">
            <CollapsibleSection title="Example section" count={3} countColor="var(--md-on-surface-muted)">
              <div style={{ padding: '8px 12px', fontSize: 12, color: 'var(--md-on-surface-muted)' }}>Collapsed content appears here. Click the header to toggle.</div>
            </CollapsibleSection>
          </Spotlight>

          <Spotlight label="<QuoteCallout>" caption="Styled callout for quote fields on critique cards. Left border + italic + muted background. SPEC-0073.">
            <QuoteCallout text="The architecture should prioritize horizontal scaling over vertical scaling for the ingestion layer." />
          </Spotlight>

          <Spotlight label="Agent Input panel" caption="Three-tier hierarchy: System Prompt (collapsed by default) → User Prompt (expanded, with nested 'From chat' + 'External resources mentioned' sub-sections) → Child Pages (one top-level entry per external resource pulled). Uses CollapsibleSection + Markdown rendering. SPEC-0085 (extends 0074).">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
              <div className="agent-input-entry" style={{ pointerEvents: 'none' }}>
                <div className="cs-header" style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="cs-chevron" style={{ fontSize: 8, color: 'var(--md-on-surface-faint)' }}>&#9654;</span>
                  <span style={{ fontWeight: 500, fontSize: 12 }}>System prompt</span>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>(system)</span>
                  <span style={{ flex: 1 }} />
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>4,915 chars</span>
                </div>
              </div>
              <div className="agent-input-entry" style={{ pointerEvents: 'none' }}>
                <div className="cs-header" style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="cs-chevron" style={{ fontSize: 8, color: 'var(--md-on-surface-faint)', transform: 'rotate(90deg)' }}>&#9654;</span>
                  <span style={{ fontWeight: 500, fontSize: 12 }}>User prompt</span>
                  <span style={{ flex: 1 }} />
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>245,378 chars</span>
                </div>
                <div style={{ paddingLeft: 22, marginTop: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <div style={{ padding: '4px 10px', fontSize: 11, color: 'var(--md-on-surface-muted)', borderLeft: '1px solid var(--md-outline-variant)' }}>
                    From chat <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)', marginLeft: 6 }}>3,142 chars</span>
                  </div>
                  <div style={{ padding: '4px 10px', fontSize: 11, color: 'var(--md-on-surface-muted)', borderLeft: '1px solid var(--md-outline-variant)' }}>
                    External resources mentioned <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)', marginLeft: 6 }}>2 resources</span>
                  </div>
                </div>
              </div>
              <div className="agent-input-entry" style={{ pointerEvents: 'none' }}>
                <div className="cs-header" style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="cs-chevron" style={{ fontSize: 8, color: 'var(--md-on-surface-faint)' }}>&#9654;</span>
                  <span style={{ fontWeight: 500, fontSize: 12 }}>Child page: Notion ADR-014</span>
                  <span style={{ flex: 1 }} />
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>12,847 chars</span>
                </div>
              </div>
            </div>
          </Spotlight>

          <Spotlight label="Consumption row" caption="Phase header sits above the row (not glued to the left edge of cards). Below: paired agent cards — three zones each (data header, divider, bars zone). Equal-height via grid stretch. SPEC-0086 (rework of 0075).">
            <div className="consumption-phase-group" style={{ marginBottom: 0 }}>
              <div className="consumption-phase-header">
                <span className="consumption-phase-name">Phase 2 · Negotiate</span>
                <span className="consumption-phase-meta">5 rounds · 17m 32s</span>
              </div>
              <div className="consumption-row">
                <div className="consumption-card" style={{ border: '1px solid var(--agent-a-border)' }}>
                  <div className="consumption-data-zone">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                      <span style={{ fontWeight: 500, color: 'var(--md-on-surface)' }}>Claude</span>
                      <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-muted)' }}>86.5kt seen</span>
                    </div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>Input: $0.56 · Total: $0.72</div>
                  </div>
                  <hr className="consumption-divider" />
                  <div className="consumption-bars-zone">
                    <div style={{ height: 10, background: 'var(--agent-a)', borderRadius: 3, opacity: 0.8, width: '70%' }} />
                    <div style={{ height: 6, background: 'var(--agent-a)', borderRadius: 2, opacity: 0.5, width: '40%', marginLeft: 8 }} />
                  </div>
                </div>
                <div className="consumption-card" style={{ border: '1px solid var(--agent-b-border)' }}>
                  <div className="consumption-data-zone">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                      <span style={{ fontWeight: 500, color: 'var(--md-on-surface)' }}>GPT</span>
                      <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-muted)' }}>42.1kt seen</span>
                    </div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>Input: $0.21 · Total: $0.35</div>
                  </div>
                  <hr className="consumption-divider" />
                  <div className="consumption-bars-zone">
                    <div style={{ height: 10, background: 'var(--agent-b)', borderRadius: 3, opacity: 0.8, width: '45%' }} />
                    <div style={{ height: 6, background: 'var(--agent-b)', borderRadius: 2, opacity: 0.5, width: '25%', marginLeft: 8 }} />
                  </div>
                </div>
              </div>
            </div>
          </Spotlight>

          <Spotlight label="<LoadingState>" caption="Three sizes — `inline` (14px spinner, row), `panel` (28px, column), `page` (44px, column). Spinner + label + optional hint. Default hint: 'Just a moment, please.' One loading visual everywhere the UI is waiting on a first useful payload. SPEC-0084.">
            <LoadingState size="panel" label="Loading runs…" />
          </Spotlight>

          {/* M1: subsequent specs add their new primitives here.
               Format: <Spotlight label="<Foo>" caption="...">{live <Foo .../>}</Spotlight>
          */}
        </div>
      </DnaSection>

      {/* States gallery — SPEC-0104 */}
      <DnaSection title="States">
        <div className="states-grid">
          {[
            ['running',    'Active processing',      'The run is actively streaming tokens between agents.'],
            ['converged',  'Agreement reached',       'Both agents converged on a shared position.'],
            ['drift',      'Position drift detected', 'Agents drifted apart after initial agreement.'],
            ['errored',    'Error halted the run',    'An unrecoverable error stopped processing.'],
            ['idle',       'Waiting',                 'The run is idle, not currently processing.'],
            ['queued',     'In queue',                'The run is queued and waiting to start.'],
          ].map(([status, name, desc]) => (
            <div key={status} className="state-card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <StatusBadge status={status} />
              </div>
              <div className="name">{name}</div>
              <div className="desc">{desc}</div>
            </div>
          ))}
        </div>
      </DnaSection>

      {/* A11y — SPEC-0104 */}
      <DnaSection title="Accessibility">
        <div>
          {[
            ['Focus ring',        '3px tertiary ring with 2px offset on :focus-visible. Every interactive primitive.'],
            ['Hit area',          'Every touch target is at least 48 x 48 dp (visual size 40 dp + 4 dp hidden padding ring on icon buttons).'],
            ['Contrast',          'All on-surface text hits WCAG AA at body sizes and AAA at headline+ sizes in both themes.'],
            ['Reduced motion',    'Global prefers-reduced-motion: reduce rule kills every animation and transition. Shimmer, caret pulse, state-layer overlay, hover-elevation, chevron rotation, tour spotlight — all frozen.'],
            ['Semantic landmarks', '<header>, <aside aria-label>, <main>, <section id> present in the app shell. Skip link jumps to #main as the first tab stop.'],
          ].map(([name, desc], i) => (
            <div key={i} className="a11y-row">
              <div className="name">{name}</div>
              <div className="desc">{desc}</div>
            </div>
          ))}
        </div>
      </DnaSection>

      {/* Responsive — SPEC-0104 */}
      <DnaSection title="Responsive">
        <div className="resp-grid">
          {[
            ['Full', '\u2265 1500 px', [
              'Full rail + three-column layout',
              'Consumption cards in paired grid',
              'Timeline and critique side by side',
            ]],
            ['Compact', '< 1500 px', [
              'Compact rail (icons only)',
              'Denser grid, two-column layout',
              'Consumption cards stack vertically within phase groups',
            ]],
            ['Single column', '< 900 px', [
              'Rail collapses to bottom nav or hamburger',
              'Single column, full-width cards',
              'Tab groups stack or scroll horizontally',
            ]],
            ['Rules of thumb', 'All breakpoints', [
              'Never hide data — reflow, never remove',
              'Touch targets stay at 48 dp minimum',
              'Font sizes don\'t change across breakpoints',
              'Padding scales down by one step per bucket',
            ]],
          ].map(([title, bp, rules], i) => (
            <div key={i} className="resp-card">
              <div className="lbl">{bp}</div>
              <h4 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 500, color: 'var(--md-on-surface)' }}>{title}</h4>
              <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--md-on-surface-muted)', fontSize: 13, lineHeight: 1.6 }}>
                {rules.map((r, j) => <li key={j}>{r}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </DnaSection>

      {/* Construction */}
      <DnaSection title="Construction">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            ['Token-only colors', 'No hex codes in components. Every color reads from tokens.css so theme changes propagate everywhere.'],
            ['Full-word vocabulary', 'Labels use complete words, never abbreviated codes. "conceded by Claude", not "-> c". Codified in SPEC-0067.'],
            ['Brand fidelity', 'Official Anthropic sunburst and OpenAI hexagonal rosette everywhere an agent is identified. No generic substitutes.'],
            // SPEC-0087 § N — Accessibility principle added per delta 20.46.
            ['Accessibility', ':focus-visible ring on every interactive primitive; prefers-reduced-motion honored on every animation; semantic ARIA where the markup needs it.'],
          ].map(([t, d], i) => (
            <div key={i} style={{ padding: '10px 14px', background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)' }}>
              <span style={{ color: 'var(--md-on-surface)', fontWeight: 600, fontSize: 12.5 }}>{t}</span>
              <span style={{ color: 'var(--md-on-surface-muted)', fontSize: 12, marginLeft: 8 }}>{d}</span>
            </div>
          ))}
        </div>
      </DnaSection>
    </div>
  );
}

function DnaSection({ title, children }) {
  return (
    <section style={{ marginBottom: 36 }}>
      <h2 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: 'var(--md-on-surface)', borderBottom: '1px solid var(--md-outline-hair)', paddingBottom: 8 }}>{title}</h2>
      {children}
    </section>
  );
}

function DnaSwatch({ label, color, token, border }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
      <div style={{ width: 28, height: 28, borderRadius: 4, background: color, border: border ? '1px solid var(--md-outline-variant)' : 'none' }} />
      <span className="mono" style={{ fontSize: 9, color: 'var(--md-on-surface-faint)' }}>{label}</span>
    </div>
  );
}

function Spotlight({ label, caption, children }) {
  return (
    <div role="figure" aria-label={label + ': ' + caption}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
        <span className="mono" style={{ fontSize: 12, color: 'var(--md-on-surface)', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)', padding: 12, marginBottom: 6 }}>
        {children}
      </div>
      <div style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', lineHeight: 1.4 }}>{caption}</div>
    </div>
  );
}

// ─────────────────── Full reference (at ?full=1) ───────────────────
// This is the original design-language page content, preserved verbatim.

function FullReference() {
  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '36px 32px 72px' }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
            dual-research · design language · full reference
          </div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--md-on-surface)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            A calm, dense observability surface for a two-agent convergence loop.
          </h1>
          <p style={{ marginTop: 12, color: 'var(--md-on-surface-muted)', fontSize: 13.5, maxWidth: 720, lineHeight: 1.55 }}>
            Read-only, terminal-adjacent, single user. Information density is a feature.
            The whole document follows three rules: never compete with the agent output, never compete with the terminal next to it, and never hide the one number that matters.
          </p>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', textAlign: 'right' }}>
          <a href="?" style={{ color: 'var(--md-on-surface-faint)', textDecoration: 'underline' }}>DNA view</a>
          <div style={{ marginTop: 4 }}>v0.1 · {new Date().toLocaleDateString('en-CA')}</div>
        </div>
      </div>

      {/* Palette */}
      <Section title="01 — Palette" subtitle="Two-agent system in calm dark. One color per agent, distinguishable but harmonious.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 18 }}>
          <AgentSwatch
            name="Claude — Sable"
            hex="#d4a574"
            role="Track A. Output, accents on Claude side, last-turn tags."
            dim="#8a6d4e"
            alpha="rgba(212, 165, 116, 0.16)"
            border="rgba(212, 165, 116, 0.22)"
            isFirst
          />
          <AgentSwatch
            name="GPT — Sage"
            hex="#7cc4b8"
            role="Track B. Output, accents on GPT side, last-turn tags."
            dim="#4f8079"
            alpha="rgba(124, 196, 184, 0.16)"
            border="rgba(124, 196, 184, 0.22)"
          />
        </div>

        <SwatchGrid title="Surfaces" cols={5} items={[
          { name: 'surface',      hex: '#0d0f12', role: 'Default surface — panels, sheets' },
          { name: 'surf-low',     hex: '#111317', role: 'Recessed surface — default panel' },
          { name: 'surf-mid',     hex: '#14171c', role: 'Elevated row / chip background / modal header' },
          { name: 'surf-high',    hex: '#191c21', role: 'Hover / active chip' },
          { name: 'surf-highest', hex: '#21252b', role: 'Highest static tier — dropdown row' },
        ]} />

        <SwatchGrid title="Foreground" cols={5} items={[
          { name: 'on-surface', hex: '#ffffff', role: 'Primary text / numbers / headings' },
          { name: 'on-variant', hex: '#b4bac4', role: 'Body prose' },
          { name: 'on-muted',   hex: '#9aa0ac', role: 'Secondary text / meta / labels' },
          { name: 'on-faint',   hex: '#7d8290', role: 'Muted / column headers' },
          { name: 'on-decor',   hex: '#50545d', role: 'Decorative / inline dividers' },
        ]} />

        <SwatchGrid title="Status — minimal, used only on state changes" cols={4} items={[
          { name: 'ok',    hex: '#6fb380', role: 'Resolved / converged / completed' },
          { name: 'info',  hex: '#6b9cf0', role: 'Running / current phase' },
          { name: 'warn',  hex: '#d4a056', role: 'Approaching cap / deadlocked' },
          { name: 'err',   hex: '#d96a6a', role: 'Errored / halted' },
        ]} />

        <Note>
          <b>Why this works.</b> Sable and sage sit on opposite sides of the warm/cool axis at near-identical L*, so neither agent feels louder. Status colors share the same dusty saturation — they read as the same family, never as marketing-grade reds and greens. No gradient backgrounds anywhere; the only gradient in the entire app is the 18-pixel wordmark tile.
        </Note>
      </Section>

      {/* Brand marks */}
      <Section title="01.5 — Brand marks" subtitle="The two agents are identified by their official brand glyphs everywhere they appear — agent labels, timeline cards, error rows, the disagreement explorer.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          <BrandCard agent="claude" name="Claude" sourceNote="Official Anthropic brand mark (simple-icons.org, CC0)." />
          <BrandCard agent="gpt"    name="OpenAI" sourceNote="Official OpenAI logomark (public brand kit)." />
        </div>
        <Note>
          <b>Sourcing.</b> The Claude mark is the canonical Anthropic sunburst from simple-icons; the OpenAI mark is the well-known hexagonal logomark from OpenAI's brand kit. Both are trademarks of their respective owners — appropriate for an internal monitoring tool, would need licensing review for public redistribution.
        </Note>
      </Section>

      {/* Typography */}
      <Section title="02 — Typography" subtitle="One sans for UI chrome + data (tabular figures via .num utility), one serif for agent-produced prose and hero text. No monospace.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          <FontCard
            kind="Sans-serif"
            face="IBM Plex Sans"
            fallback="ui-sans-serif, system-ui, -apple-system, sans-serif"
            role="UI chrome, body, labels, buttons, navigation, status pills, IDs, costs, tokens (with tabular-nums via .num utility)."
            sampleFamily="var(--md-font-plain)"
            weights={[400, 500, 600]}
          />
          <FontCard
            kind="Serif"
            face="IBM Plex Serif"
            fallback='ui-serif, "Iowan Old Style", Charter, Georgia, serif'
            role="Agent-produced prose, hero text, page-level headings, blockquotes, QuestionThread quotes. The agent's voice — humanist proportions blend with the sans."
            sampleFamily="var(--md-font-brand)"
            weights={[400, 500, 600]}
          />
        </div>

        <div style={{
          marginTop: 18,
          border: '1px solid var(--md-outline-hair)',
          borderRadius: 'var(--md-shape-md)',
          background: 'var(--md-surface-container-low)',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--md-outline-hair)', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--md-on-surface)', fontWeight: 600 }}>Type scale</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>13px body · 1.45 line-height</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '120px 90px 1fr', borderTop: '1px solid var(--md-outline-hair)' }}>
            {[
              ['Display',  '28 / 600',  'A calm, dense observability surface', 'var(--md-font-plain)'],
              ['Title',    '20 / 600',  'Section heading',                     'var(--md-font-plain)'],
              ['Body lg',  '14 / 400',  'Default reading size for body prose', 'var(--md-font-plain)'],
              ['Body',     '13 / 400',  'Run topic, last-turn summary',         'var(--md-font-plain)'],
              ['Meta',     '12 / 400',  'Disagreement positions, agent output', 'var(--md-font-data)'],
              ['Caption',  '11 / 500',  'Metric values, run IDs',               'var(--md-font-data)'],
              ['Label',    '10 / 500',  'Uppercase labels, column headers',     'var(--md-font-plain)'],
            ].map(([name, spec, sample, family], i) => (
              <React.Fragment key={i}>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--md-outline-hair)', color: 'var(--md-on-surface-variant)', fontSize: 12 }}>{name}</div>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--md-outline-hair)', color: 'var(--md-on-surface-faint)', fontSize: 11, fontFamily: 'var(--md-font-data)' }}>{spec}</div>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--md-outline-hair)', fontFamily: family, fontSize: Number(spec.split(' /')[0]), fontWeight: Number(spec.split('/ ')[1]), color: 'var(--md-on-surface)', letterSpacing: name === 'Display' ? '-0.02em' : 0 }}>{sample}</div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </Section>

      {/* Spacing */}
      <Section title="03 — Spacing & shape" subtitle="A 4px scale. Generous outside, dense inside — there are five tabular numbers per row and they should still breathe.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          <div style={{ background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--md-outline-hair)' }}>
              <span style={{ fontSize: 12, color: 'var(--md-on-surface)', fontWeight: 600 }}>Spacing scale (4px base)</span>
            </div>
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[2, 4, 6, 8, 10, 12, 14, 18, 24, 32, 48].map(s => (
                <div key={s} style={{ display: 'grid', gridTemplateColumns: '40px 60px 1fr', alignItems: 'center', gap: 12 }}>
                  <span className="mono num" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)' }}>{s}px</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>s-{s}</span>
                  <div style={{ height: 4, width: s * 3, background: 'var(--agent-a)', borderRadius: 999, opacity: 0.6 }} />
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--md-outline-hair)' }}>
              <span style={{ fontSize: 12, color: 'var(--md-on-surface)', fontWeight: 600 }}>Radii & borders</span>
            </div>
            <div style={{ padding: 14, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
              {[
                ['r-1', '4px',  'Status pills, mini chips'],
                ['r-2', '6px',  'Buttons, segmented'],
                ['r-3', '8px',  'Panels, streaming boxes'],
                ['r-4', '10px', 'Cards'],
                ['r-5', '14px', 'Tweaks panel'],
              ].map(([name, val, role]) => (
                <div key={name}>
                  <div style={{ height: 60, background: 'var(--md-surface-container-high)', borderRadius: val, border: '1px solid var(--md-outline-variant)' }} />
                  <div className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-muted)', marginTop: 6 }}>{name} · {val}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)', lineHeight: 1.4 }}>{role}</div>
                </div>
              ))}
            </div>
            <div style={{ borderTop: '1px solid var(--md-outline-hair)', padding: 14 }}>
              <div className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-muted)', marginBottom: 6 }}>Hairlines</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ height: 1, background: 'var(--md-outline-hair)' }} />
                <div style={{ height: 1, background: 'var(--md-outline-variant)' }} />
                <div style={{ height: 1, background: 'var(--md-outline)' }} />
              </div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)', marginTop: 6 }}>
                outline-hair (#1c1f24) hairline · outline-variant medium · outline strong
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* Motion */}
      <Section title="04 — Motion" subtitle="Streaming should feel like a calm typewriter, not a slot machine. State transitions should be noticed, not announced.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 16 }}>
          <MotionCard
            title="Streaming tokens"
            spec="60-90 chars/sec · per-frame batch · no per-char layout thrash"
            detail="Tokens append in 16 ms batches with one re-flow per frame. A 0.9-opacity block caret pulses at 1.05 s to anchor the eye. We never animate width or scroll-jump — content grows downward only; the scroll container auto-stays-pinned when the user is already at the bottom."
            demo={<StreamingDemo />}
          />
          <MotionCard
            title="State transitions"
            spec="180 ms ease-out · single property at a time"
            detail="Phase advance: timeline dot fills, label crossfades. No translate, no scale. A new disagreement row fades in over 180 ms; a resolution strikethrough draws in 220 ms. Loud states (cap, deadlock, error) get a slow 2.2 s soft-pulse halo — never a hard flash."
            demo={<PulseDemo />}
          />
        </div>

        <Note>
          <b>What we don't do.</b> No scroll-into-view (it jolts the layout next to a terminal). No spinners <em>within</em> the run document — the live caret and pulsing dot do that job for streaming text. The one exception is <code>LoadingState</code> (spec 0084), used at the page or panel level when no useful payload has arrived yet. No success animations on convergence — the document just renders. No toast notifications; this is a read-only surface.
        </Note>
      </Section>

      {/* Component vocabulary */}
      <Section title="05 — Component vocabulary" subtitle="Six primitives compose the entire surface.">
        <div style={{
          background: 'var(--md-surface-container-low)',
          border: '1px solid var(--md-outline-hair)',
          borderRadius: 'var(--md-shape-md)',
          padding: 18,
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18,
        }}>
          <PrimitiveCard name="StatusBadge" role="Single source of truth for run + agent state. Always a single dot + a mono label.">
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <StatusBadge status="running" />
              <StatusBadge status="thinking" />
              <StatusBadge status="drafting" />
              <StatusBadge status="responding" />
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
              <StatusBadge status="converged" />
              <StatusBadge status="deadlocked" />
              <StatusBadge status="errored" />
              <StatusBadge status="idle" />
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Pill" role="Lightweight categorical tag. Inline with rows, never standalone.">
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <Pill color={COLORS.warn}>open</Pill>
              <Pill color={COLORS.agentA}>conceded by Claude</Pill>
              <Pill color={COLORS.agentB}>conceded by GPT</Pill>
              <Pill color={COLORS.ok}>both aligned</Pill>
              <Pill color={COLORS.info}>live</Pill>
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="PhaseMini" role="6-dot strip that fits in a table cell. Each dot = one phase.">
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={2} status="running" /><span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>P2 running</span></div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={5} status="completed" /><span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>done</span></div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={2} status="deadlocked" /><span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>deadlock</span></div>
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Streaming box" role="Bordered well that hosts streaming agent output. Agent-tinted border, never agent-tinted fill.">
            <div style={{
              background: 'var(--md-surface)',
              border: '1px solid var(--agent-a-border)',
              borderRadius: 'var(--md-shape-md)',
              padding: 10,
              fontFamily: 'var(--md-font-data)',
              fontSize: 11.5,
              color: 'var(--md-on-surface)',
            }}>
              Tokens stream here <span className="caret" style={{ color: 'var(--agent-a)' }} />
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Cap bar" role="Round counter against soft + hard caps. Soft mark is a tick, hard cap is the end.">
            <div style={{ padding: '6px 0' }}>
              <div className="cap-bar"><i style={{ width: '66%', background: COLORS.info }} /><span className="soft-mark" style={{ left: '50%' }} /></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--md-font-data)', fontSize: 10, color: 'var(--md-on-surface-faint)', marginTop: 4 }}>
                <span>0</span><span>up soft (6)</span><span>hard (12)</span>
              </div>
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Disagreement row" role="Three columns: contested point | claude position | gpt position. 2px left border per agent.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, fontSize: 11 }}>
              <div style={{ color: 'var(--md-on-surface-variant)' }}>"temperate" scope</div>
              <div className="mono" style={{ paddingLeft: 6, borderLeft: `2px solid ${COLORS.agentA}`, color: 'var(--md-on-surface-variant)' }}>Cfa + Cfb</div>
              <div className="mono" style={{ paddingLeft: 6, borderLeft: `2px solid ${COLORS.agentB}`, color: 'var(--md-on-surface-variant)' }}>Cfa only</div>
            </div>
          </PrimitiveCard>
        </div>
      </Section>

      {/* Principles */}
      <Section title="06 — Principles" subtitle="Six rules that bind the rest together.">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {[
            ['Read-only is a discipline', 'No buttons that mutate state. Every affordance is a view filter, a tab, or a focus shift. If the user wants to act, they go to the terminal.'],
            ['One color per agent, everywhere', 'Sable for Claude, sage for GPT. Status colors are the only other hues. If a third hue appears in the wireframe, it gets cut.'],
            ['Mono for anything an agent produced', 'Streaming output, tokens, costs, IDs, positions in the disagreements panel. Sans for prose the UI itself wrote.'],
            ['Density is a feature', 'A run-list row fits eight columns at 1200px without ellipses below the topic. Padding is generous between panels and minimal within them.'],
            ['Calm transitions or none', 'No bounces, no scale, no springs. Soft pulses for live states; everything else is opacity + position only.'],
            ['Show why a run is slow', 'The disagreements panel always tells the operator which contested point is blocking convergence. No buried logs.'],
          ].map(([t, d], i) => (
            <div key={i} style={{
              padding: '12px 14px',
              background: 'var(--md-surface-container-low)',
              border: '1px solid var(--md-outline-hair)',
              borderRadius: 'var(--md-shape-md)',
            }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>{String(i + 1).padStart(2, '0')}</span>
                <span style={{ color: 'var(--md-on-surface)', fontWeight: 600, fontSize: 13 }}>{t}</span>
              </div>
              <p style={{ margin: 0, color: 'var(--md-on-surface-muted)', fontSize: 12, lineHeight: 1.55 }}>{d}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ─────────────────── helper components (shared by both views) ───────────────────

function Section({ title, subtitle, children }) {
  return (
    <section style={{ marginBottom: 48 }}>
      <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--md-outline-hair)' }}>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--md-on-surface)', letterSpacing: '-0.01em' }}>{title}</div>
        {subtitle && <div style={{ marginTop: 4, fontSize: 12.5, color: 'var(--md-on-surface-muted)' }}>{subtitle}</div>}
      </div>
      {children}
    </section>
  );
}

function AgentSwatch({ name, hex, role, dim, alpha, border, isFirst }) {
  return (
    <div style={{
      background: 'var(--md-surface-container-low)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      overflow: 'hidden',
    }}>
      <div style={{ height: 56, background: hex, position: 'relative' }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, bottom: 0, width: '34%',
          background: alpha,
          borderRight: `1px solid ${border}`,
        }} />
        <div style={{
          position: 'absolute', top: 0, right: 0, bottom: 0, width: '20%',
          background: dim,
        }} />
      </div>
      <div style={{ padding: '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 600, whiteSpace: 'nowrap' }}>{name}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-variant)', whiteSpace: 'nowrap' }}>{hex.toUpperCase()}</span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--md-on-surface-muted)', marginTop: 4 }}>{role}</div>
        <div style={{ display: 'flex', gap: 10, marginTop: 8, fontFamily: 'var(--md-font-data)', fontSize: 10, color: 'var(--md-on-surface-faint)' }}>
          <span><span style={{ display: 'inline-block', width: 6, height: 6, background: hex, marginRight: 4, borderRadius: 1 }} />base</span>
          <span><span style={{ display: 'inline-block', width: 6, height: 6, background: alpha, marginRight: 4, borderRadius: 1, border: `1px solid ${border}` }} />alpha/16</span>
          <span><span style={{ display: 'inline-block', width: 6, height: 6, background: dim, marginRight: 4, borderRadius: 1 }} />dim {dim.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
}

function SwatchGrid({ title, items, cols }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div className="uppercase-label" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 8 }}>
        {items.map((s) => (
          <div key={s.name} style={{
            background: 'var(--md-surface-container-low)',
            border: '1px solid var(--md-outline-hair)',
            borderRadius: 'var(--md-shape-md)',
            overflow: 'hidden',
          }}>
            <div style={{ height: 44, background: s.hex, borderBottom: '1px solid var(--md-outline-hair)' }} />
            <div style={{ padding: '8px 10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-variant)' }}>{s.name}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--md-on-surface-faint)' }}>{s.hex.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)', marginTop: 2, lineHeight: 1.4 }}>{s.role}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BrandCard({ agent, name, sourceNote }) {
  const meta = AGENT_META[agent];
  const brandName = agent === 'claude' ? 'claude' : 'openai';
  return (
    <div style={{
      background: 'var(--md-surface-container-low)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      padding: 18,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14 }}>
        <span className="uppercase-label">{name}</span>
        <span className="mono" style={{ fontSize: 10.5, color: meta.color }}>{meta.color}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 20, marginBottom: 16 }}>
        <BrandSwatch brandName={brandName} agent={agent} size={48} variant="solid" caption="solid 48" />
        <BrandSwatch brandName={brandName} agent={agent} size={32} variant="solid" caption="solid 32" />
        <BrandSwatch brandName={brandName} agent={agent} size={24} variant="solid" caption="solid 24" />
        <BrandSwatch brandName={brandName} agent={agent} size={16} variant="solid" caption="solid 16" />
        <BrandSwatch brandName={brandName} agent={agent} size={16} variant="ghost" caption="ghost 16" />
        <BrandSwatch brandName={brandName} agent={agent} size={12} variant="ghost" caption="ghost 12" />
      </div>
      <div style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', lineHeight: 1.55, marginBottom: 8 }}>
        Used everywhere the {name} agent is identified — list rows, run-detail headers, timeline cards, error rows, and the disagreement explorer.
      </div>
      <div className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{sourceNote}</div>
    </div>
  );
}

function BrandSwatch({ brandName, agent, size, variant, caption }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <BrandMark name={brandName} size={size} variant={variant} aria-hidden="true" />
      <span className="mono" style={{ fontSize: 9.5, color: 'var(--md-on-surface-faint)' }}>{caption}</span>
    </div>
  );
}

function FontCard({ kind, face, fallback, role, sampleFamily, weights, mono }) {
  return (
    <div style={{
      background: 'var(--md-surface-container-low)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      padding: 18,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="uppercase-label">{kind}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>weights {weights.join(', ')}</span>
      </div>
      <div style={{ fontFamily: sampleFamily, fontSize: 36, color: 'var(--md-on-surface)', letterSpacing: mono ? 0 : '-0.02em', lineHeight: 1.05, marginBottom: 4 }}>
        {face}
      </div>
      <div style={{ fontFamily: sampleFamily, fontSize: 14, color: 'var(--md-on-surface-muted)', marginBottom: 12 }}>
        {mono ? 'Aa Bb Cc · 0123 · ()<>{}/' : 'AaBbCc 0123 — Aa Bb Cc 0 1 2 3'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', lineHeight: 1.55, marginBottom: 8 }}>{role}</div>
      <div className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
        fallback: {fallback}
      </div>
    </div>
  );
}

function MotionCard({ title, spec, detail, demo }) {
  return (
    <div style={{
      background: 'var(--md-surface-container-low)',
      border: '1px solid var(--md-outline-hair)',
      borderRadius: 'var(--md-shape-md)',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--md-outline-hair)', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 600 }}>{title}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>{spec}</span>
      </div>
      <div style={{ padding: 14, background: 'var(--md-surface)', borderBottom: '1px solid var(--md-outline-hair)' }}>
        {demo}
      </div>
      <div style={{ padding: '12px 14px', fontSize: 12, color: 'var(--md-on-surface-muted)', lineHeight: 1.55 }}>
        {detail}
      </div>
    </div>
  );
}

function StreamingDemo() {
  const sample = `> phase 2 / round 4 / claude
appending to position vector...
agreed: section 2 vintage taxonomy
contested: section 4 financing split`;
  const [k, setK] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setK(x => x + 1), 4400);
    return () => clearInterval(id);
  }, []);
  return (
    <div style={{
      height: 110,
      background: 'var(--md-surface)',
      border: '1px solid var(--agent-a-border)',
      borderRadius: 'var(--md-shape-sm)',
      padding: 10,
      overflow: 'hidden',
    }}>
      <StreamingText key={k} content={sample} speed={45} color="var(--md-on-surface)" />
    </div>
  );
}

function PulseDemo() {
  const [phase, setPhase] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setPhase(p => (p + 1) % 3), 2200);
    return () => clearInterval(id);
  }, []);
  const tones = [
    { status: 'running',    label: 'running',    color: COLORS.info, pulse: 'pulse-a' },
    { status: 'deadlocked', label: 'deadlocked', color: COLORS.warn, pulse: 'pulse-warn' },
    { status: 'errored',    label: 'errored',    color: COLORS.err,  pulse: 'pulse-err' },
  ];
  const t = tones[phase];
  return (
    <div style={{ height: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 18 }}>
      <Dot color={t.color} pulse={t.pulse} size={12} />
      <div className="mono" style={{ fontSize: 12, color: t.color, letterSpacing: '0.04em' }}>
        state: {t.label}
      </div>
    </div>
  );
}

function PrimitiveCard({ name, role, children }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 12.5, color: 'var(--md-on-surface)', fontWeight: 600 }}>{name}</span>
      </div>
      <div style={{
        background: 'var(--md-surface)',
        border: '1px solid var(--md-outline-hair)',
        borderRadius: 'var(--md-shape-md)',
        padding: 12,
        minHeight: 80,
        marginBottom: 8,
      }}>{children}</div>
      <div style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', lineHeight: 1.5 }}>{role}</div>
    </div>
  );
}

function Note({ children }) {
  return (
    <div style={{
      marginTop: 18,
      padding: '12px 14px',
      background: 'var(--md-surface-container-low)',
      borderLeft: '2px solid var(--agent-b)',
      borderRadius: '0 var(--md-shape-md) var(--md-shape-md) 0',
      fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.6,
    }}>
      {children}
    </div>
  );
}

Object.assign(window, { DesignLanguageView });
