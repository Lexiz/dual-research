// design-language.jsx — palette / type / spacing / motion writeup

function DesignLanguageView() {
  return (
    <div style={{
      height: '100vh', overflow: 'auto',
      background: 'var(--bg-0)',
    }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '36px 32px 72px' }}>
        {/* Title */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 32 }}>
          <div>
            <div className="mono" style={{ fontSize: 11, color: 'var(--fg-3)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
              dual-research · design language
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
            v0.1 · {new Date().toLocaleDateString('en-CA')}
          </div>
        </div>

        {/* Top: palette */}
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

        {/* Typography */}
        <Section title="02 — Typography" subtitle="One sans for UI chrome, one mono for everything an agent produced or anything that's a number.">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
            <FontCard
              kind="Sans-serif"
              face="Geist"
              fallback="ui-sans-serif, system-ui, -apple-system, sans-serif"
              role="UI chrome only — panel titles, labels, body prose. Never used for streaming output or numbers."
              sampleFamily="var(--sans)"
              weights={[400, 500, 600]}
            />
            <FontCard
              kind="Monospace"
              face="Geist Mono"
              fallback='ui-monospace, "JetBrains Mono", "SF Mono", Menlo'
              role="Agent output, all numbers, run ids, phase ids, status pills, code-shaped labels. Same family as the sans means metrics line up cleanly."
              sampleFamily="var(--mono)"
              weights={[400, 500]}
              mono
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
              spec="60–90 chars/sec · per-frame batch · no per-char layout thrash"
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
                <Pill color={COLORS.agentA}>→ claude</Pill>
                <Pill color={COLORS.agentB}>→ gpt</Pill>
                <Pill color={COLORS.ok}>aligned</Pill>
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
                  <span>0</span><span>↑ soft (6)</span><span>hard (12)</span>
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
    </div>
  );
}

// ─────────────────── helper components ───────────────────

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
          <span><span style={{ display: 'inline-block', width: 6, height: 6, background: alpha, marginRight: 4, borderRadius: 1, border: `1px solid ${border}` }} />α/16</span>
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
  // looping streaming text
  const sample = `> phase 2 / round 4 / claude
appending to position vector…
agreed: §2 vintage taxonomy
contested: §4 financing split`;
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
        state → {t.label}
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
