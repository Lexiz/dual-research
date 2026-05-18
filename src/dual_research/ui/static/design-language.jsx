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
      background: 'var(--bg-0)',
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
        <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
          dual-research · design language
        </div>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--fg-0)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
          A calm, dense observability surface for a two-agent convergence loop.
        </h1>
        <p style={{ marginTop: 12, color: 'var(--fg-2)', fontSize: 13.5, maxWidth: 720, lineHeight: 1.55 }}>
          Read-only, terminal-adjacent, single user. Heavy emoji removed, dense Plex Sans on cream, never decoration that fights the signal. Information density is a feature.
        </p>
        <div className="mono" style={{ marginTop: 8, fontSize: 10.5, color: 'var(--fg-3)' }}>
          <a href="?full=1" style={{ color: 'var(--fg-3)', textDecoration: 'underline' }}>Full reference</a>
        </div>
      </section>

      {/* Palette */}
      <DnaSection title="Palette">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
          <DnaSwatch label="Claude" color="var(--agent-a)" token="--agent-a" />
          <DnaSwatch label="OpenAI" color="var(--agent-b)" token="--agent-b" />
          <span style={{ width: 1, background: 'var(--border-2)', margin: '0 4px' }} />
          <DnaSwatch label="bg-0" color="var(--bg-0)" token="--bg-0" border />
          <DnaSwatch label="bg-1" color="var(--bg-1)" token="--bg-1" border />
          <DnaSwatch label="bg-2" color="var(--bg-2)" token="--bg-2" border />
          <DnaSwatch label="bg-3" color="var(--bg-3)" token="--bg-3" border />
          <span style={{ width: 1, background: 'var(--border-2)', margin: '0 4px' }} />
          <DnaSwatch label="info" color="var(--info)" token="--info" />
          <DnaSwatch label="warn" color="var(--warn)" token="--warn" />
          <DnaSwatch label="ok"   color="var(--ok)"   token="--ok" />
          <DnaSwatch label="err"  color="var(--err)"  token="--err" />
          <span style={{ width: 1, background: 'var(--border-2)', margin: '0 4px' }} />
          <DnaSwatch label="fg-0" color="var(--fg-0)" token="--fg-0" />
          <DnaSwatch label="fg-1" color="var(--fg-1)" token="--fg-1" />
          <DnaSwatch label="fg-2" color="var(--fg-2)" token="--fg-2" />
          <DnaSwatch label="fg-3" color="var(--fg-3)" token="--fg-3" />
        </div>
      </DnaSection>

      {/* Brand marks */}
      <DnaSection title="Brand marks">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          {[['claude', 'Claude'], ['openai', 'OpenAI']].map(([name, label]) => (
            <div key={name} style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', padding: 14 }}>
              <div className="uppercase-label" style={{ marginBottom: 10 }}>{label}</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
                {[32, 24, 16].map(s => (
                  <div key={s} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <BrandMark name={name} size={s} variant="solid" />
                    <span className="mono" style={{ fontSize: 9, color: 'var(--fg-3)' }}>{s}</span>
                  </div>
                ))}
                {[16, 12].map(s => (
                  <div key={'g'+s} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <BrandMark name={name} size={s} variant="ghost" />
                    <span className="mono" style={{ fontSize: 9, color: 'var(--fg-3)' }}>ghost {s}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DnaSection>

      {/* Component spotlights */}
      <DnaSection title="Component spotlights">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
          <Spotlight label="<Chip>" caption="Compact labeled token with optional icon and count.">
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <Chip tone="info" icon="alert-circle" count={6}>open claims</Chip>
              <Chip tone="ok">resolved</Chip>
              <Chip tone="warn">deadlocked</Chip>
              <Chip tone="neutral">draft</Chip>
            </div>
          </Spotlight>

          <Spotlight label="<Card>" caption="Expandable container for timeline entries and critique items.">
            <Card style={{ padding: 10 }}>
              <div style={{ fontSize: 12, color: 'var(--fg-1)' }}>Phase 2 draft</div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 4 }}>Claude · R4 · 2,847 tokens</div>
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
            <CollapsibleSection title="Example section" count={3} countColor="var(--fg-2)">
              <div style={{ padding: '8px 12px', fontSize: 12, color: 'var(--fg-2)' }}>Collapsed content appears here. Click the header to toggle.</div>
            </CollapsibleSection>
          </Spotlight>

          <Spotlight label="<QuoteCallout>" caption="Styled callout for quote fields on critique cards. Left border + italic + muted background. SPEC-0073.">
            <QuoteCallout text="The architecture should prioritize horizontal scaling over vertical scaling for the ingestion layer." />
          </Spotlight>

          {/* M1: subsequent specs add their new primitives here.
               Format: <Spotlight label="<Foo>" caption="...">{live <Foo .../>}</Spotlight>
          */}
        </div>
      </DnaSection>

      {/* Construction */}
      <DnaSection title="Construction">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            ['Token-only colors', 'No hex codes in components. Every color reads from tokens.css so theme changes propagate everywhere.'],
            ['Full-word vocabulary', 'Labels use complete words, never abbreviated codes. "conceded by Claude", not "-> c". Codified in SPEC-0067.'],
            ['Brand fidelity', 'Official Anthropic sunburst and OpenAI hexagonal rosette everywhere an agent is identified. No generic substitutes.'],
          ].map(([t, d], i) => (
            <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)' }}>
              <span style={{ color: 'var(--fg-0)', fontWeight: 600, fontSize: 12.5 }}>{t}</span>
              <span style={{ color: 'var(--fg-2)', fontSize: 12, marginLeft: 8 }}>{d}</span>
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
      <h2 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: 'var(--fg-0)', borderBottom: '1px solid var(--border-1)', paddingBottom: 8 }}>{title}</h2>
      {children}
    </section>
  );
}

function DnaSwatch({ label, color, token, border }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
      <div style={{ width: 28, height: 28, borderRadius: 4, background: color, border: border ? '1px solid var(--border-2)' : 'none' }} />
      <span className="mono" style={{ fontSize: 9, color: 'var(--fg-3)' }}>{label}</span>
    </div>
  );
}

function Spotlight({ label, caption, children }) {
  return (
    <div role="figure" aria-label={label + ': ' + caption}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
        <span className="mono" style={{ fontSize: 12, color: 'var(--fg-0)', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', padding: 12, marginBottom: 6 }}>
        {children}
      </div>
      <div style={{ fontSize: 11, color: 'var(--fg-3)', lineHeight: 1.4 }}>{caption}</div>
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
          <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
            dual-research · design language · full reference
          </div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--fg-0)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            A calm, dense observability surface for a two-agent convergence loop.
          </h1>
          <p style={{ marginTop: 12, color: 'var(--fg-2)', fontSize: 13.5, maxWidth: 720, lineHeight: 1.55 }}>
            Read-only, terminal-adjacent, single user. Information density is a feature.
            The whole document follows three rules: never compete with the agent output, never compete with the terminal next to it, and never hide the one number that matters.
          </p>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', textAlign: 'right' }}>
          <a href="?" style={{ color: 'var(--fg-3)', textDecoration: 'underline' }}>DNA view</a>
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
          { name: 'bg-0',  hex: '#08090b', role: 'Page / streaming body' },
          { name: 'bg-1',  hex: '#0d0f12', role: 'Panels' },
          { name: 'bg-2',  hex: '#131519', role: 'Elevated rows' },
          { name: 'bg-3',  hex: '#191c21', role: 'Hover / chip' },
          { name: 'bg-4',  hex: '#1f2329', role: 'High contrast' },
        ]} />

        <SwatchGrid title="Foreground" cols={5} items={[
          { name: 'fg-0', hex: '#f2f4f7', role: 'Primary text / numbers' },
          { name: 'fg-1', hex: '#c8ccd3', role: 'Body text' },
          { name: 'fg-2', hex: '#8c929c', role: 'Secondary / meta' },
          { name: 'fg-3', hex: '#5e636d', role: 'Muted / labels' },
          { name: 'fg-4', hex: '#3f444c', role: 'Decorative' },
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
            sampleFamily="var(--sans)"
            weights={[400, 500, 600]}
          />
          <FontCard
            kind="Serif"
            face="IBM Plex Serif"
            fallback='ui-serif, "Iowan Old Style", Charter, Georgia, serif'
            role="Agent-produced prose, hero text, page-level headings, blockquotes, QuestionThread quotes. The agent's voice — humanist proportions blend with the sans."
            sampleFamily="var(--serif)"
            weights={[400, 500, 600]}
          />
        </div>

        <div style={{
          marginTop: 18,
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--r-3)',
          background: 'var(--bg-1)',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-1)', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--fg-0)', fontWeight: 600 }}>Type scale</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>13px body · 1.45 line-height</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '120px 90px 1fr', borderTop: '1px solid var(--border-1)' }}>
            {[
              ['Display',  '28 / 600',  'A calm, dense observability surface', 'var(--sans)'],
              ['Title',    '20 / 600',  'Section heading',                     'var(--sans)'],
              ['Body lg',  '14 / 400',  'Default reading size for body prose', 'var(--sans)'],
              ['Body',     '13 / 400',  'Run topic, last-turn summary',         'var(--sans)'],
              ['Meta',     '12 / 400',  'Disagreement positions, agent output', 'var(--mono)'],
              ['Caption',  '11 / 500',  'Metric values, run IDs',               'var(--mono)'],
              ['Label',    '10 / 500',  'Uppercase labels, column headers',     'var(--sans)'],
            ].map(([name, spec, sample, family], i) => (
              <React.Fragment key={i}>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--border-1)', color: 'var(--fg-1)', fontSize: 12 }}>{name}</div>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--border-1)', color: 'var(--fg-3)', fontSize: 11, fontFamily: 'var(--mono)' }}>{spec}</div>
                <div style={{ padding: '10px 14px', borderTop: i === 0 ? 'none' : '1px solid var(--border-1)', fontFamily: family, fontSize: Number(spec.split(' /')[0]), fontWeight: Number(spec.split('/ ')[1]), color: 'var(--fg-0)', letterSpacing: name === 'Display' ? '-0.02em' : 0 }}>{sample}</div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </Section>

      {/* Spacing */}
      <Section title="03 — Spacing & shape" subtitle="A 4px scale. Generous outside, dense inside — there are five tabular numbers per row and they should still breathe.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          <div style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-1)' }}>
              <span style={{ fontSize: 12, color: 'var(--fg-0)', fontWeight: 600 }}>Spacing scale (4px base)</span>
            </div>
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[2, 4, 6, 8, 10, 12, 14, 18, 24, 32, 48].map(s => (
                <div key={s} style={{ display: 'grid', gridTemplateColumns: '40px 60px 1fr', alignItems: 'center', gap: 12 }}>
                  <span className="mono num" style={{ fontSize: 11, color: 'var(--fg-2)' }}>{s}px</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>s-{s}</span>
                  <div style={{ height: 4, width: s * 3, background: 'var(--agent-a)', borderRadius: 999, opacity: 0.6 }} />
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-1)' }}>
              <span style={{ fontSize: 12, color: 'var(--fg-0)', fontWeight: 600 }}>Radii & borders</span>
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
                  <div style={{ height: 60, background: 'var(--bg-3)', borderRadius: val, border: '1px solid var(--border-2)' }} />
                  <div className="mono" style={{ fontSize: 10, color: 'var(--fg-2)', marginTop: 6 }}>{name} · {val}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--fg-3)', lineHeight: 1.4 }}>{role}</div>
                </div>
              ))}
            </div>
            <div style={{ borderTop: '1px solid var(--border-1)', padding: 14 }}>
              <div className="mono" style={{ fontSize: 11, color: 'var(--fg-2)', marginBottom: 6 }}>Hairlines</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ height: 1, background: 'var(--border-1)' }} />
                <div style={{ height: 1, background: 'var(--border-2)' }} />
                <div style={{ height: 1, background: 'var(--border-3)' }} />
              </div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--fg-3)', marginTop: 6 }}>
                border-1 (#1c1f24) hairline · border-2 medium · border-3 strong
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
          <b>What we don't do.</b> No scroll-into-view (it jolts the layout next to a terminal). No spinners (the live caret and pulsing dot do that job). No success animations on convergence — the document just renders. No toast notifications; this is a read-only surface.
        </Note>
      </Section>

      {/* Component vocabulary */}
      <Section title="05 — Component vocabulary" subtitle="Six primitives compose the entire surface.">
        <div style={{
          background: 'var(--bg-1)',
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--r-3)',
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
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={2} status="running" /><span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>P2 running</span></div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={5} status="completed" /><span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>done</span></div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}><PhaseMini phase={2} status="deadlocked" /><span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>deadlock</span></div>
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Streaming box" role="Bordered well that hosts streaming agent output. Agent-tinted border, never agent-tinted fill.">
            <div style={{
              background: 'var(--bg-0)',
              border: '1px solid var(--agent-a-border)',
              borderRadius: 'var(--r-3)',
              padding: 10,
              fontFamily: 'var(--mono)',
              fontSize: 11.5,
              color: 'var(--fg-0)',
            }}>
              Tokens stream here <span className="caret" style={{ color: 'var(--agent-a)' }} />
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Cap bar" role="Round counter against soft + hard caps. Soft mark is a tick, hard cap is the end.">
            <div style={{ padding: '6px 0' }}>
              <div className="cap-bar"><i style={{ width: '66%', background: COLORS.info }} /><span className="soft-mark" style={{ left: '50%' }} /></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--fg-3)', marginTop: 4 }}>
                <span>0</span><span>up soft (6)</span><span>hard (12)</span>
              </div>
            </div>
          </PrimitiveCard>

          <PrimitiveCard name="Disagreement row" role="Three columns: contested point | claude position | gpt position. 2px left border per agent.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, fontSize: 11 }}>
              <div style={{ color: 'var(--fg-1)' }}>"temperate" scope</div>
              <div className="mono" style={{ paddingLeft: 6, borderLeft: `2px solid ${COLORS.agentA}`, color: 'var(--fg-1)' }}>Cfa + Cfb</div>
              <div className="mono" style={{ paddingLeft: 6, borderLeft: `2px solid ${COLORS.agentB}`, color: 'var(--fg-1)' }}>Cfa only</div>
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
              background: 'var(--bg-1)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--r-3)',
            }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>{String(i + 1).padStart(2, '0')}</span>
                <span style={{ color: 'var(--fg-0)', fontWeight: 600, fontSize: 13 }}>{t}</span>
              </div>
              <p style={{ margin: 0, color: 'var(--fg-2)', fontSize: 12, lineHeight: 1.55 }}>{d}</p>
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
      <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--border-1)' }}>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--fg-0)', letterSpacing: '-0.01em' }}>{title}</div>
        {subtitle && <div style={{ marginTop: 4, fontSize: 12.5, color: 'var(--fg-2)' }}>{subtitle}</div>}
      </div>
      {children}
    </section>
  );
}

function AgentSwatch({ name, hex, role, dim, alpha, border, isFirst }) {
  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
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
          <span style={{ fontSize: 13, color: 'var(--fg-0)', fontWeight: 600, whiteSpace: 'nowrap' }}>{name}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-1)', whiteSpace: 'nowrap' }}>{hex.toUpperCase()}</span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--fg-2)', marginTop: 4 }}>{role}</div>
        <div style={{ display: 'flex', gap: 10, marginTop: 8, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--fg-3)' }}>
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
            background: 'var(--bg-1)',
            border: '1px solid var(--border-1)',
            borderRadius: 'var(--r-3)',
            overflow: 'hidden',
          }}>
            <div style={{ height: 44, background: s.hex, borderBottom: '1px solid var(--border-1)' }} />
            <div style={{ padding: '8px 10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--fg-1)' }}>{s.name}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--fg-3)' }}>{s.hex.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--fg-3)', marginTop: 2, lineHeight: 1.4 }}>{s.role}</div>
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
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
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
      <div style={{ fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.55, marginBottom: 8 }}>
        Used everywhere the {name} agent is identified — list rows, run-detail headers, timeline cards, error rows, and the disagreement explorer.
      </div>
      <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{sourceNote}</div>
    </div>
  );
}

function BrandSwatch({ brandName, agent, size, variant, caption }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <BrandMark name={brandName} size={size} variant={variant} aria-hidden="true" />
      <span className="mono" style={{ fontSize: 9.5, color: 'var(--fg-3)' }}>{caption}</span>
    </div>
  );
}

function FontCard({ kind, face, fallback, role, sampleFamily, weights, mono }) {
  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
      padding: 18,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="uppercase-label">{kind}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>weights {weights.join(', ')}</span>
      </div>
      <div style={{ fontFamily: sampleFamily, fontSize: 36, color: 'var(--fg-0)', letterSpacing: mono ? 0 : '-0.02em', lineHeight: 1.05, marginBottom: 4 }}>
        {face}
      </div>
      <div style={{ fontFamily: sampleFamily, fontSize: 14, color: 'var(--fg-2)', marginBottom: 12 }}>
        {mono ? 'Aa Bb Cc · 0123 · ()<>{}/' : 'AaBbCc 0123 — Aa Bb Cc 0 1 2 3'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.55, marginBottom: 8 }}>{role}</div>
      <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>
        fallback: {fallback}
      </div>
    </div>
  );
}

function MotionCard({ title, spec, detail, demo }) {
  return (
    <div style={{
      background: 'var(--bg-1)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-3)',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-1)', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 13, color: 'var(--fg-0)', fontWeight: 600 }}>{title}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)' }}>{spec}</span>
      </div>
      <div style={{ padding: 14, background: 'var(--bg-0)', borderBottom: '1px solid var(--border-1)' }}>
        {demo}
      </div>
      <div style={{ padding: '12px 14px', fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.55 }}>
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
      background: 'var(--bg-0)',
      border: '1px solid var(--agent-a-border)',
      borderRadius: 'var(--r-2)',
      padding: 10,
      overflow: 'hidden',
    }}>
      <StreamingText key={k} content={sample} speed={45} color="var(--fg-0)" />
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
        <span style={{ fontSize: 12.5, color: 'var(--fg-0)', fontWeight: 600 }}>{name}</span>
      </div>
      <div style={{
        background: 'var(--bg-0)',
        border: '1px solid var(--border-1)',
        borderRadius: 'var(--r-3)',
        padding: 12,
        minHeight: 80,
        marginBottom: 8,
      }}>{children}</div>
      <div style={{ fontSize: 11, color: 'var(--fg-3)', lineHeight: 1.5 }}>{role}</div>
    </div>
  );
}

function Note({ children }) {
  return (
    <div style={{
      marginTop: 18,
      padding: '12px 14px',
      background: 'var(--bg-1)',
      borderLeft: '2px solid var(--agent-b)',
      borderRadius: '0 var(--r-3) var(--r-3) 0',
      fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6,
    }}>
      {children}
    </div>
  );
}

Object.assign(window, { DesignLanguageView });
