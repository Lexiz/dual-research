// how-it-works.jsx — user-facing explanation of the dual-research protocol
// plus release notes (spec 0023). Static content, no API calls. The release
// notes block lives in VERSION_NOTES at the bottom; CONTRIBUTING.md asks
// that future specs touching user-visible behaviour append a new entry here.

(function () {
  const VERSION_NOTES = [
    {
      version: '0.23.0',
      date: '2026-05-16',
      summary: 'Visualisation foundations — summary cards, modal pattern, preflight tabs, attachment ingest.',
      items: [
        'Timeline cards no longer expand inline. Each card shows a one-line TL;DR + "View full" button; clicking opens a big centred modal over a dimmed overlay.',
        'Preflight (Input) opens a tabbed modal: Content · Sources · Files. Images render as thumbnails, links list with host + caption.',
        'Brief ingest now captures attachments: inline markdown images / links, Notion image / pdf / bookmark blocks, plus a new repeatable `--attach VALUE` CLI flag (local file or URL).',
        'Hosted runs get a new `attachment_blobs` table; `--push` uploads binary attachments alongside the existing transcript and session files.',
        'TL;DR cards come from each agent\'s existing `## Summary` section — no prompt changes; the UI just stopped ignoring it.',
        'Foundation for the upcoming side-by-side inline-comments view: markdown rendering now emits a stable `id="b-…"` on every block, so future specs can anchor critic comments to specific paragraphs.',
      ],
    },
    {
      version: '0.22.1',
      date: '2026-05-16',
      summary: 'Run-detail header pass 2 + compact theme toggle.',
      items: [
        'Run-detail header trimmed further: icon-only back arrow, no brand pill, no copy-id chip, no "PHASE N Done" or "converged in …" duplicates.',
        'Topic carries a "TOPIC" caps tag and reads as the visual centre.',
        'Status badge composes with the errors count when present — `completed | ⚠ 3 errors`, right half clickable to open the errors view.',
        'Cost and total tokens fold into one badge.',
        'Chrome bar light/dark segmented toggle replaced by a single compact pill with sun and moon icon buttons inside.',
      ],
    },
    {
      version: '0.22.0',
      date: '2026-05-16',
      summary: 'Compact run-detail header, "How it works" page, release notes.',
      items: [
        'Run-detail header collapsed from four rows into two — one card-height of timeline recovered.',
        'New "How it works" page in the chrome bar — explains the protocol end-to-end.',
        'Release notes (this list). New entries land here whenever a spec changes user-visible behaviour.',
      ],
    },
    {
      version: '0.21.0',
      date: '2026-05-15',
      summary: 'Admin allowlist UI, profile menu, landing-page redesign.',
      items: [
        'Top-right avatar menu with Design language, Settings (admin only), and Sign out — replaces the standalone "Design" link.',
        'New #/settings page for admins: table of allowlisted emails, inline add, remove. Protected against self-delete and removing the only admin.',
        'Landing page redesigned: centered hero, two-agent SVG visual, official-looking Google sign-in button.',
      ],
    },
    {
      version: '0.20.0',
      date: '2026-05-15',
      summary: 'Google OAuth + email allowlist.',
      items: [
        'Sign-in via Google through Supabase Auth replaces the HTTP Basic stopgap.',
        'New `approved_emails` table gates every /api/* request by signed-in email.',
        '/api/health and /api/config remain public so the bundle can bootstrap.',
      ],
    },
    {
      version: '0.19.0',
      date: '2026-05-15',
      summary: 'Fly.io deployment of the UI server.',
      items: [
        'Hosted UI at https://dual-research-alex.fly.dev/, single small machine, auto-stops when idle.',
        'New RUNS_BACKEND=fs|supabase toggle: hosted reads runs from Supabase, local still reads from `runs/`.',
        'Detail view materializes a tmp directory from Supabase per request, then hands it to the existing aggregator unchanged.',
      ],
    },
    {
      version: '0.18.0',
      date: '2026-05-15',
      summary: 'Supabase schema + `--push` CLI.',
      items: [
        'New Postgres tables (runs, events, session_files) mirror the on-disk session-dir layout.',
        '`dual-research --push runs/<session-dir>` bulk-uploads a completed run. Idempotent on re-run.',
        'Orchestrator behaviour unchanged — push is a manual step after a run finishes.',
      ],
    },
  ];

  // ─── Small SVG building blocks ─────────────────────────────────────────

  function AgentDisc({ cx, cy, r, letter, color, bg, border }) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={r} fill={bg} stroke={border} strokeWidth="1.25" />
        <text x={cx} y={cy + r * 0.32} textAnchor="middle"
              fontFamily="Geist, system-ui, sans-serif" fontWeight="600"
              fontSize={r * 0.95} fill={color}>{letter}</text>
      </g>
    );
  }

  function ClaudeDisc(props) {
    return <AgentDisc letter="C"
                      color="var(--agent-a)" bg="var(--agent-a-bg-strong)"
                      border="var(--agent-a-border)" {...props} />;
  }
  function GptDisc(props) {
    return <AgentDisc letter="G"
                      color="var(--agent-b)" bg="var(--agent-b-bg-strong)"
                      border="var(--agent-b-border)" {...props} />;
  }

  function Arrow({ x1, y1, x2, y2, dashed, color = 'var(--border-3)' }) {
    return (
      <line x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={color} strokeWidth="1.5"
            strokeDasharray={dashed ? '4 6' : null}
            markerEnd="url(#arrowhead)" />
    );
  }

  function ArrowDefs() {
    return (
      <defs>
        <marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--border-3)" />
        </marker>
      </defs>
    );
  }

  // ─── Diagram: 5-phase flow at a glance ────────────────────────────────

  function PhaseFlowDiagram() {
    const phases = [
      { id: 0, label: 'P0',  hint: 'parallel',     desc: 'preflight' },
      { id: 1, label: 'P1',  hint: 'parallel',     desc: 'research' },
      { id: 2, label: 'P2',  hint: 'turn-based',   desc: 'negotiate' },
      { id: 3, label: 'P3',  hint: 'single-shot',  desc: 'draft' },
      { id: 4, label: 'P4',  hint: 'turn-based',   desc: 'review' },
      { id: 'F', label: '✓', hint: 'output',       desc: 'final.md' },
    ];
    return (
      <svg viewBox="0 0 720 130" style={{ display: 'block', width: '100%', maxWidth: 720 }}>
        <ArrowDefs />
        {phases.map((p, i) => {
          const x = 50 + i * 130;
          const isFinal = p.id === 'F';
          return (
            <g key={p.id}>
              <rect x={x - 36} y={42} width={72} height={44} rx={10}
                    fill="var(--bg-1)" stroke="var(--border-2)" />
              <text x={x} y={62} textAnchor="middle"
                    fontFamily="Geist, system-ui, sans-serif" fontWeight={600}
                    fontSize={isFinal ? 18 : 13} fill="var(--fg-0)">{p.label}</text>
              <text x={x} y={78} textAnchor="middle"
                    fontFamily="JetBrains Mono, monospace" fontSize={9}
                    fill="var(--fg-2)">{p.desc}</text>
              <text x={x} y={32} textAnchor="middle"
                    fontFamily="JetBrains Mono, monospace" fontSize={9}
                    fill={p.hint === 'parallel' ? 'var(--agent-b)'
                          : p.hint === 'turn-based' ? 'var(--agent-a)'
                          : p.hint === 'single-shot' ? 'var(--fg-2)'
                          : 'var(--ok)'}>
                {p.hint}
              </text>
              {i < phases.length - 1 && <Arrow x1={x + 36} y1={64} x2={x + 130 - 36} y2={64} />}
            </g>
          );
        })}
      </svg>
    );
  }

  // ─── Diagram: parallel-fire pattern (used by P0/P1/P2/P4) ─────────────

  function ParallelDiagram({ inputLabel = 'brief', leftOut = 'draft-claude.md', rightOut = 'draft-openai.md' }) {
    return (
      <svg viewBox="0 0 480 220" style={{ display: 'block', width: '100%', maxWidth: 480 }}>
        <ArrowDefs />
        {/* input */}
        <rect x={180} y={10} width={120} height={30} rx={6}
              fill="var(--bg-1)" stroke="var(--border-2)" />
        <text x={240} y={29} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={11}
              fill="var(--fg-1)">{inputLabel}</text>
        {/* arrows to agents */}
        <Arrow x1={210} y1={40} x2={120} y2={95} />
        <Arrow x1={270} y1={40} x2={360} y2={95} />
        {/* agents */}
        <ClaudeDisc cx={120} cy={120} r={28} />
        <GptDisc cx={360} cy={120} r={28} />
        <text x={120} y={170} textAnchor="middle"
              fontSize={11} fill="var(--fg-2)" fontFamily="JetBrains Mono, monospace">claude</text>
        <text x={360} y={170} textAnchor="middle"
              fontSize={11} fill="var(--fg-2)" fontFamily="JetBrains Mono, monospace">openai</text>
        {/* asyncio.gather hint */}
        <text x={240} y={120} textAnchor="middle"
              fontSize={10} fill="var(--fg-3)" fontFamily="JetBrains Mono, monospace">
          asyncio.gather
        </text>
        <text x={240} y={134} textAnchor="middle"
              fontSize={9} fill="var(--fg-3)" fontFamily="JetBrains Mono, monospace">
          (both fire at once)
        </text>
        {/* outputs */}
        <Arrow x1={120} y1={148} x2={120} y2={188} />
        <Arrow x1={360} y1={148} x2={360} y2={188} />
        <rect x={20} y={188} width={200} height={26} rx={5}
              fill="var(--agent-a-bg)" stroke="var(--agent-a-border)" />
        <text x={120} y={206} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10.5}
              fill="var(--agent-a)">{leftOut}</text>
        <rect x={260} y={188} width={200} height={26} rx={5}
              fill="var(--agent-b-bg)" stroke="var(--agent-b-border)" />
        <text x={360} y={206} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10.5}
              fill="var(--agent-b)">{rightOut}</text>
      </svg>
    );
  }

  // ─── Diagram: one Phase 2 round ───────────────────────────────────────

  function NegotiationRoundDiagram() {
    return (
      <svg viewBox="0 0 600 280" style={{ display: 'block', width: '100%', maxWidth: 600 }}>
        <ArrowDefs />
        {/* prior turns */}
        <rect x={20} y={20} width={160} height={56} rx={6}
              fill="var(--bg-1)" stroke="var(--border-2)" />
        <text x={100} y={40} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10.5}
              fill="var(--fg-2)">prior turns inlined</text>
        <text x={100} y={56} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={9.5}
              fill="var(--fg-3)">round 1..N-1, both agents</text>
        <text x={100} y={70} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={9.5}
              fill="var(--fg-3)">+ brief + phase-1 drafts</text>

        {/* fresh prompt assembly note */}
        <text x={300} y={50} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10}
              fill="var(--fg-2)">
          orchestrator builds a fresh prompt
        </text>
        <text x={300} y={64} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={9}
              fill="var(--fg-3)">
          (no persistent chat — see § Fresh chats)
        </text>

        <Arrow x1={180} y1={48} x2={420} y2={48} />

        {/* parallel call */}
        <rect x={420} y={20} width={160} height={56} rx={6}
              fill="var(--bg-1)" stroke="var(--border-2)" />
        <text x={500} y={40} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10.5}
              fill="var(--fg-2)">round N prompt</text>
        <text x={500} y={56} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={9.5}
              fill="var(--fg-3)">identical to both, except</text>
        <text x={500} y={70} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={9.5}
              fill="var(--fg-3)">agent_name substitution</text>

        {/* agents */}
        <Arrow x1={460} y1={84} x2={180} y2={140} />
        <Arrow x1={540} y1={84} x2={420} y2={140} />
        <ClaudeDisc cx={150} cy={160} r={26} />
        <GptDisc cx={450} cy={160} r={26} />

        {/* parallel hint */}
        <text x={300} y={160} textAnchor="middle"
              fontSize={10.5} fill="var(--fg-3)" fontFamily="JetBrains Mono, monospace">
          asyncio.gather
        </text>

        {/* outputs */}
        <Arrow x1={150} y1={186} x2={150} y2={218} />
        <Arrow x1={450} y1={186} x2={450} y2={218} />
        <rect x={50} y={218} width={200} height={26} rx={5}
              fill="var(--agent-a-bg)" stroke="var(--agent-a-border)" />
        <text x={150} y={236} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10}
              fill="var(--agent-a)">phase2/round-NN-claude.md</text>
        <rect x={350} y={218} width={200} height={26} rx={5}
              fill="var(--agent-b-bg)" stroke="var(--agent-b-border)" />
        <text x={450} y={236} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10}
              fill="var(--agent-b)">phase2/round-NN-openai.md</text>

        {/* check */}
        <rect x={200} y={252} width={200} height={22} rx={6}
              fill="var(--bg-2)" stroke="var(--border-2)" />
        <text x={300} y={267} textAnchor="middle"
              fontFamily="JetBrains Mono, monospace" fontSize={10}
              fill="var(--fg-1)">both AGREED + plan-hash match?</text>
      </svg>
    );
  }

  // ─── Page primitives ──────────────────────────────────────────────────

  function Section({ title, children }) {
    return (
      <section style={{ marginBottom: 36 }}>
        <h2 style={{
          fontSize: 16, fontWeight: 600, color: 'var(--fg-0)',
          margin: '0 0 12px 0', letterSpacing: '-0.005em',
        }}>{title}</h2>
        <div style={{ fontSize: 13.5, color: 'var(--fg-1)', lineHeight: 1.65 }}>
          {children}
        </div>
      </section>
    );
  }

  function FAQ({ q, children }) {
    return (
      <div style={{
        padding: '12px 14px', marginBottom: 8,
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 8,
      }}>
        <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--fg-0)', marginBottom: 4 }}>
          {q}
        </div>
        <div style={{ fontSize: 13, color: 'var(--fg-1)', lineHeight: 1.6 }}>
          {children}
        </div>
      </div>
    );
  }

  function PhaseRow({ phase, name, hint, hintColor, children }) {
    return (
      <div style={{
        display: 'flex', gap: 18, padding: '14px 0',
        borderTop: '1px solid var(--border-1)',
      }}>
        <div style={{ flexShrink: 0, width: 88 }}>
          <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.05em' }}>
            PHASE {phase}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-0)', marginTop: 2 }}>
            {name}
          </div>
          <div className="mono" style={{ fontSize: 10, color: hintColor, marginTop: 4 }}>{hint}</div>
        </div>
        <div style={{ flex: 1, fontSize: 13, color: 'var(--fg-1)', lineHeight: 1.65 }}>
          {children}
        </div>
      </div>
    );
  }

  // ─── Page ─────────────────────────────────────────────────────────────

  function HowItWorks() {
    return (
      <div style={{
        height: '100%', overflow: 'auto', padding: '32px 32px 80px',
        background: 'var(--bg-0)', color: 'var(--fg-0)',
      }}>
        <div style={{ maxWidth: 820, margin: '0 auto' }}>

          {/* Hero */}
          <div style={{ marginBottom: 36 }}>
            <h1 style={{
              fontSize: 28, fontWeight: 600, margin: 0,
              letterSpacing: '-0.02em',
            }}>How dual-research works</h1>
            <p style={{
              fontSize: 14, color: 'var(--fg-2)', maxWidth: 600,
              marginTop: 8, marginBottom: 24, lineHeight: 1.6,
            }}>
              Two language models start from the same brief, work independently,
              then negotiate until they agree on a single document. The
              orchestrator is deterministic; the agents are not. This page is
              what they actually do, in order.
            </p>
            <PhaseFlowDiagram />
          </div>

          {/* Brief ingestion */}
          <Section title="It starts with one brief">
            <p>
              You provide a prompt, a markdown file, or a Notion page. The orchestrator
              ingests it once and serialises it as <code>brief.md</code> in the run's
              session directory. <strong>That exact text is the only input both agents
              ever see for the topic.</strong> Their prompts are otherwise identical
              — the only thing that changes is whether the agent is told it's playing the
              "claude" or "openai" role.
            </p>
          </Section>

          {/* Phase walkthrough */}
          <Section title="The five phases">
            <PhaseRow phase={0} name="Preflight" hint="parallel" hintColor="var(--agent-b)">
              Both agents read the brief and write a short critique — what's underspecified,
              what's ambiguous, what's missing. The two API calls fire <code>asyncio.gather</code>-style,
              so they run at the same moment without seeing each other's critique. In
              autonomous mode their feedback is logged but doesn't gate the run.
            </PhaseRow>

            <PhaseRow phase={1} name="Independent research" hint="parallel" hintColor="var(--agent-b)">
              Each agent writes a complete first-pass research draft, alone. Same brief
              going in, same prompt structure, but each draft is the agent's own thinking
              — they cannot see each other yet. This is the only phase where you actually
              get to see how each model interprets the brief without negotiation pressure.
              Outputs: <code>phase1/draft-claude.md</code> and <code>phase1/draft-openai.md</code>.
            </PhaseRow>

            <PhaseRow phase={2} name="Plan negotiation" hint="turn-based" hintColor="var(--agent-a)">
              The agents start reading each other's work. Each round, both agents fire
              <em> in parallel</em> with the brief, both Phase 1 drafts, and every prior
              negotiation turn from both sides as input. Round 1 is structurally required
              to be a "first read" — neither agent can mark AGREED yet. From round 2 on,
              they exchange counter-proposals, mark disagreements with stable D-N
              identifiers, and try to converge on an <code>AGREED_PLAN</code> block whose
              SHA-256 hash matches the other agent's. Convergence detection is mechanical:
              same <code>STATUS: AGREED</code>, same drafter choice, same plan hash, zero
              open questions, zero blocking disagreements, matching final-surfaced
              disagreements — all in the same round.
            </PhaseRow>

            <PhaseRow phase={3} name="Drafting" hint="single-shot" hintColor="var(--fg-2)">
              One agent — the drafter, picked by the tiebreak below — writes the converged
              document in a single call. They receive: the brief, both Phase 1 drafts, the
              hash-verified canonical agreed plan, and the entire Phase 2 conversation as
              context. The other agent is silent in this phase.
            </PhaseRow>

            <PhaseRow phase={4} name="Cross-review" hint="turn-based" hintColor="var(--agent-a)">
              Same shape as Phase 2: both agents fire in parallel each round. The drafter
              can include a <code>## Revised draft</code> section in their turn, which the
              orchestrator detects, writes as <code>phase4/draft-vN+1.md</code>, and shows
              to both agents in the next round. The reviewer can comment but not edit.
              Convergence here means both agents emit <code>STATUS: APPROVED</code> with
              zero open issues in the same round.
            </PhaseRow>
          </Section>

          {/* Negotiation pattern */}
          <Section title="A round, up close">
            <p style={{ marginBottom: 16 }}>
              In each Phase 2 (and Phase 4) round, the orchestrator builds one prompt
              per agent that bundles all the prior history, fires both calls in parallel,
              writes the two responses to disk, then checks whether the convergence
              criteria are met. If yes, advance phase. If no, repeat with the new turn
              files appended to the history.
            </p>
            <NegotiationRoundDiagram />
          </Section>

          {/* FAQ */}
          <Section title="What gets decided when">
            <FAQ q="Do they read each other's work?">
              Not in Phases 0 and 1. From Phase 2 onward yes — each agent's prompt
              inlines the brief, both Phase 1 drafts, and every prior round's turn
              from both sides. They build context fully transparently.
            </FAQ>

            <FAQ q="Who goes first in a round? Random? Fixed?">
              Neither. <strong>Both agents fire at the same moment</strong> via
              <code>asyncio.gather</code>. There's no "speaker" in the way humans
              would imagine. Each agent is independently producing a turn that
              references all prior history — they aren't reading the round-N turn
              of the other agent while they're writing round N.
            </FAQ>

            <FAQ q="Fresh chats per turn, or one long chat?">
              <strong>Fresh API call every turn.</strong> The agents have no
              persistent conversation handle; the orchestrator re-inlines the full
              prior-turn history into every new prompt. The CACHE_BREAKPOINT marker
              lets Anthropic cache the stable prefix (brief + Phase 1 drafts) so
              the marginal cost of long history is small, but that's prefix caching
              — not a session. From the agent's perspective every turn is a single
              question with all context provided up front.
            </FAQ>

            <FAQ q="How is the drafter picked?">
              A four-step cascade in <code>tiebreak.pick_drafter</code>:
              <ol style={{ paddingLeft: 22, margin: '6px 0' }}>
                <li>If both agents independently recommend the same drafter in their AGREED turns — that wins.</li>
                <li>Otherwise, sum each agent's self-rated <code>DOMAIN_FIT_SELF</code> plus the other's rating of them. Higher total drafts.</li>
                <li>Tiebreak by plan-alignment: word-set overlap between the agreed plan and each agent's Phase 1 draft.</li>
                <li>Last-resort: <code>SHA-256(brief)</code>'s first byte parity. Even = claude, odd = openai. Deterministic, no concession asymmetry.</li>
              </ol>
            </FAQ>

            <FAQ q="What if they never converge?">
              Two caps. <strong>Soft cap</strong> (default 6 rounds) logs a warning and
              keeps going. <strong>Hard cap</strong> (default 12 rounds) stops the
              run, exits with code 51, and emits a <code>final.md</code> containing
              the last draft plus both agents' last review turns as an
              "unresolved disagreements" appendix. Confidence tag is forced to
              <code>LOW</code>.
            </FAQ>

            <FAQ q="What if an agent emits something the parser can't read?">
              Each agent has one repair attempt per phase. The orchestrator saves
              the malformed turn (as <code>round-NN-agent.malformed-N.md</code>),
              spends the budget, and re-prompts the agent with the specific
              missing fields surfaced. If the agent fails again on the next round,
              the run exits with code 52. Two consecutive parse failures kill it.
            </FAQ>

            <FAQ q="Which models are used?">
              By default the production tier: Claude Sonnet 4.6 (with the 1M-context beta) +
              GPT-5.5. There's a faster <code>test</code> tier (Haiku 4.5 + GPT-5-mini)
              for verifying changes without spending much. The agent labels stay
              <code>claude</code> and <code>openai</code>; the actual model id is
              recorded in the run's metrics file.
            </FAQ>

            <FAQ q="Where does the cost come from?">
              Every call records its token usage and a per-call USD cost
              computed from the model's published pricing. The number you see in
              the header is the sum of every call in the run. Anthropic prompt
              caching gives ~75% off cached prefix reads — long Phase 2 runs are
              cheaper than their input-token count suggests.
            </FAQ>
          </Section>

          {/* Release notes */}
          <Section title="Release notes">
            <p style={{ color: 'var(--fg-2)', fontSize: 12.5, marginBottom: 16 }}>
              Each entry corresponds to a merged spec. Newest first.
            </p>
            {VERSION_NOTES.map(entry => (
              <div key={entry.version} style={{
                padding: '14px 16px', marginBottom: 10,
                background: 'var(--bg-1)', border: '1px solid var(--border-1)',
                borderRadius: 8,
              }}>
                <div style={{
                  display: 'flex', alignItems: 'baseline', gap: 12,
                  marginBottom: 6,
                }}>
                  <span className="mono" style={{
                    fontSize: 13, fontWeight: 600, color: 'var(--fg-0)',
                  }}>{entry.version}</span>
                  <span className="mono" style={{
                    fontSize: 11, color: 'var(--fg-3)',
                  }}>{entry.date}</span>
                  <span style={{
                    fontSize: 12.5, color: 'var(--fg-2)',
                  }}>{entry.summary}</span>
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6 }}>
                  {entry.items.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            ))}
          </Section>

        </div>
      </div>
    );
  }

  window.HowItWorks = HowItWorks;
})();
